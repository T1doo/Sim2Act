"""Existing P-A Worker/InternModel wiring, explicit synthetic transport only."""

import base64
import hashlib
import json
import threading
import time
from dataclasses import replace

import httpx
import pytest
import test_natural_spec_apps as apps
from sqlalchemy import select, update
from test_natural_live_admission import frozen
from test_natural_spec_apps import setup, wire

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as budget
from sim2act import pa_trial_dispatch as trial
from sim2act import pb_natural_uses as use
from sim2act import production_trial_admission as production
from sim2act.db import (
    attempts,
    delivery_graph_requests,
    events,
    fingerprint,
    grants,
    reservations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


@pytest.fixture
def prepared_trial(env):
    data = setup(env)
    subject = production.canonical_quota_subject("offline-pa-account")
    settings = replace(data[1], quota_subject=subject)
    data = (data[0], settings, *data[2:])
    data[0].initialize(quota_subject=subject)
    contract, approval = frozen(data, ttl=1200.0)
    contract = contract.model_copy(update=dict(quota_subject=subject))
    approval = approval.model_copy(
        update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump()))
    )

    gate.approve(data[0], data[3], contract, approval)
    account = production.AccountEvidence(
        principal_id=data[3],
        project_id=data[4],
        trial_key=contract.trial_key,
        contract_fingerprint=fingerprint(contract.model_dump()),
        account_id="offline-pa-account",
        quota_subject=subject,
        evidence_sha256="a" * 64,
        checked_at=time.time() - 1,
        expires_at=contract.expires_at,
        legal_free_entitlement=True,
        enforced_non_chargeable=True,
    )
    binding = trial.PATrialBinding(
        contract,
        approval.request_key,
        production.OfflineRegistry((account,), production.OfflineSender()),
    )
    yield data, binding
    data[2].close()


def test_actual_seven_slots_use_existing_worker_and_adapter(prepared_trial, monkeypatch, tmp_path):
    data, binding = prepared_trial
    workers = []
    stopped = threading.Event()
    refresh_errors = []
    original_async = httpx.MockTransport.handle_async_request

    def fresh_binding():
        account = binding.registry.accounts[0].model_copy(update=dict(checked_at=time.time()))
        return replace(binding, registry=replace(binding.registry, accounts=(account,)))

    def worker_factory(*args, **kwargs):
        worker = Worker(*args, **kwargs, pa_trial=fresh_binding())
        workers.append(worker)
        return worker

    def refresh_offline_fixture():
        try:
            while not stopped.wait(0.25):
                for worker in tuple(workers):
                    worker.pa_trial = fresh_binding()
        except BaseException as error:
            refresh_errors.append(error)

    # Only fixture construction is adapted. The actual adapter/transport methods
    # and accounting boundaries run product code without class send patches.
    monkeypatch.setattr(apps, "Worker", worker_factory)
    refresher = threading.Thread(target=refresh_offline_fixture, daemon=True)
    refresher.start()
    try:
        generation, _, release, inst, sent = apps.ready(data, style="ordered")
        assert len(sent) == 3
        source = apps.enqueue(data, release, inst)

        def approve_stage(stage, rid):
            reviewed = gate.stage_review(
                data[0], data[3], binding.contract, binding.approval_key, stage, rid
            )
            consent = gate.StageApproveInput(
                authority=gate.StageAuthority.model_validate(reviewed["authority"]),
                expected_authority_fingerprint=reviewed["authority_fingerprint"],
                approval_key=binding.approval_key,
                request_key=stage + "-stage-consent",
                consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL",
            )
            gate.approve_stage(data[0], data[3], binding.contract, consent)
            return reviewed, consent

        reviewed, _ = approve_stage("source", source)
        source_sent = []
        assert worker_factory(
            data[0], data[1], goal_planner_transport=apps.transport(source_sent)
        ).once()
        assert data[2].get("/api/runs/" + source).json()["status"] == "SUCCEEDED"
        target = binding.contract.bindings[1]
        current = data[2].get("/api/internal/instances/" + inst["id"]).json()
        review = dict(
            expected_revision=current["revision"],
            expected_release_fingerprint=release["fingerprint"],
            expected_app_fingerprint=reviewed["authority"]["candidate_fingerprint"],
            expected_recipe_fingerprint=reviewed["authority"]["recipe_fingerprint"],
            resource_id=target.resource_id,
            card_id=target.card_id,
            expected_goal_version=target.goal_version,
            expected_goal_fingerprint=target.goal_fingerprint,
            expected_source_hash=target.source_hash,
            request_key=binding.contract.stage_keys.cold,
        )
        route = "/api/internal/instances/" + inst["id"]
        preview = data[2].post(route + "/pa-use-reviews", json=review)
        assert preview.status_code == 200, preview.text
        queued = data[2].post(
            route + "/pa-use-runs",
            json=dict(
                review=review,
                expected_review_fingerprint=preview.json()["review_fingerprint"],
                consent=use.PA_CONSENT,
            ),
        )
        assert queued.status_code == 202, queued.text
        cold = queued.json()["run_id"]
        _, consent = approve_stage("cold", cold)
        cold_sent = []
        assert worker_factory(
            data[0], data[1], goal_planner_transport=apps.transport(cold_sent, apps.COLD)
        ).once()
        assert data[2].get("/api/runs/" + cold).json()["status"] == "SUCCEEDED"
        assert len(source_sent) == len(cold_sent) == 2
        assert httpx.MockTransport.handle_async_request is original_async
        assert not refresh_errors
        scope = budget.scope_for(binding.contract, binding.approval_key)
        accounting = budget.read(data[0], data[3], scope.model_dump())
        assert accounting["reserved_requests"] == 7 and accounting["usage_status"] == "KNOWN"
        ledger = accounting["ledger"]
        assert ledger["stage_runs"] == dict(generate=generation, source=source, cold=cold)
        assert all(slot["accepted"] for slot in ledger["slots"])
        times = [slot["reserved_at"] for slot in ledger["slots"]]
        assert all(b - a >= 60 for a, b in zip(times, times[1:], strict=False))
        with data[0].tx() as c:
            bodies = (
                c.execute(
                    select(delivery_graph_requests).where(
                        delivery_graph_requests.c.kind.in_([trial.REQUEST, trial.RESPONSE]),
                        delivery_graph_requests.c.app_id.in_([generation, source, cold]),
                    )
                )
                .mappings()
                .all()
            )
            assert len(bodies) == 14
            for row in bodies:
                body = row["snapshot"]["response"]
                payload = base64.b64decode(body["body_b64"], validate=True)
                assert len(payload) == body["byte_count"]
                assert hashlib.sha256(payload).hexdigest() == body["sha256"]
                assert body["provenance"] == "OFFLINE_MOCKTRANSPORT"
        before = production.recover(data[0], data[3], binding.contract, binding.approval_key)
        history = gate.recover_stage(
            data[0], data[3], binding.contract, binding.approval_key, "cold", consent.request_key
        )
        assert history["dispatch_authorized"] is False
        assert (
            production.recover(data[0], data[3], binding.contract, binding.approval_key) == before
        )
        (tmp_path / "actual-seven-slots.json").write_text(
            json.dumps(
                dict(
                    accounting=accounting,
                    gaps=[b - a for a, b in zip(times, times[1:], strict=False)],
                    actual_sends=7,
                    body_archives=14,
                    real_models=0,
                    live_allowed=False,
                    synthetic_evidence_refresh=True,
                    transport_class_unmodified=True,
                ),
                indent=2,
            )
            + "\n"
        )
    finally:
        stopped.set()
        refresher.join(timeout=2)


def enqueue_generation(data, binding):
    card = data[6]
    response = data[2].post(
        f"/api/projects/{data[4]}/goal-cards/{card['id']}/application-runs",
        json=dict(
            expected_version=card["version"],
            expected_fingerprint=card["fingerprint"],
            request_key=binding.contract.stage_keys.generate,
            family="natural_spec",
        ),
    )
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def first_response(data):
    return wire(
        dict(
            role="assistant",
            content="",
            tool_calls=[
                dict(
                    id="actual-first-read",
                    type="function",
                    function=dict(
                        name="resource.read", arguments=json.dumps(dict(resource_id=data[5]))
                    ),
                )
            ],
        ),
        "tool_calls",
    )


@pytest.mark.parametrize(
    "change",
    [
        dict(principal_id="user_" + "0" * 32),
        dict(legal_free_entitlement=False),
        dict(enforced_non_chargeable=False),
        dict(revoked=True),
        dict(checked_at=1.0),
        dict(expires_at=1.0),
        dict(quota_subject="alias-account"),
        dict(scope="LIVE"),
        dict(legal_free_entitlement="yes"),
    ],
)
def test_missing_real_or_invalid_offline_account_cannot_claim_or_reserve(prepared_trial, change):
    data, binding = prepared_trial
    rid = enqueue_generation(data, binding)
    registry = replace(
        binding.registry, accounts=(binding.registry.accounts[0].model_copy(update=change),)
    )
    sent = []
    with pytest.raises(DomainError):
        Worker(
            data[0],
            data[1],
            pa_trial=replace(binding, registry=registry),
            goal_planner_transport=httpx.MockTransport(lambda r: sent.append(r)),
        )
    with data[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == "QUEUED"
        assert c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first() is None
        assert (
            c.execute(select(reservations.c.id).where(reservations.c.run_id == rid)).first() is None
        )
    assert sent == []


def test_default_production_selection_never_resolves_credentials_or_sends(prepared_trial):
    data, binding = prepared_trial
    with pytest.raises(DomainError) as denied:
        Worker(data[0], data[1], pa_trial=replace(binding, registry=None))
    assert denied.value.code == "LIVE_BLOCKED"


@pytest.mark.parametrize(
    "fault", ["key", "body_event", "cancel", "revoke", "version", "fence", "lease", "account"]
)
def test_changed_authority_or_request_before_marker_never_sends(prepared_trial, monkeypatch, fault):
    import copy

    data, binding = prepared_trial
    rid = enqueue_generation(data, binding)
    sent = []
    original = trial._sent

    def changed(worker, run, aid, request_wire):
        if fault == "account":
            account = binding.registry.accounts[0].model_copy(update=dict(revoked=True))
            worker.pa_trial = replace(
                binding, registry=replace(binding.registry, accounts=(account,))
            )
        else:
            with data[0].tx() as c:
                if fault in ("key", "body_event"):
                    records = (
                        c.execute(
                            select(delivery_graph_requests).where(
                                delivery_graph_requests.c.app_id == rid,
                                delivery_graph_requests.c.kind.in_(
                                    [trial.REQUEST, trial.REQUEST + "_seal"]
                                ),
                            )
                        )
                        .mappings()
                        .all()
                    )
                    for row in records:
                        snapshot = copy.deepcopy(row["snapshot"])
                        if fault == "key":
                            snapshot["request"]["trial"]["approval_key"] = "different-approval"
                        else:
                            snapshot["response"]["extent"] = "RECEIVED_PREFIX"
                        c.execute(
                            update(delivery_graph_requests)
                            .where(
                                delivery_graph_requests.c.app_id == rid,
                                delivery_graph_requests.c.kind == row["kind"],
                                delivery_graph_requests.c.request_key == aid,
                            )
                            .values(
                                snapshot=snapshot,
                                request_fingerprint=fingerprint(snapshot["request"]),
                                fingerprint=fingerprint(snapshot),
                            )
                        )
                elif fault == "revoke":
                    c.execute(
                        update(grants).where(grants.c.resource_id == data[5]).values(revoked=True)
                    )
                else:
                    values = (
                        {"cancel_intent": True}
                        if fault == "cancel"
                        else {"version": run["version"] + 1}
                        if fault == "version"
                        else {"fence": run["fence"] + 1}
                        if fault == "fence"
                        else {"lease_until": time.time() - 1}
                    )
                    c.execute(update(runs).where(runs.c.id == rid).values(**values))
        return original(worker, run, aid, request_wire)

    monkeypatch.setattr(trial, "_sent", changed)
    worker = Worker(
        data[0],
        data[1],
        goal_planner_transport=httpx.MockTransport(
            lambda r: sent.append(r) or httpx.Response(200, json=first_response(data))
        ),
        pa_trial=binding,
    )
    try:
        assert worker.once()
    except DomainError:
        pass
    assert sent == []
    with data[0].tx() as c:
        assert (
            c.execute(
                select(delivery_graph_requests.c.request_key).where(
                    delivery_graph_requests.c.app_id == rid,
                    delivery_graph_requests.c.kind == trial.SENT,
                )
            ).first()
            is None
        )
        ledger = budget._ledger(c, budget.scope_for(binding.contract, binding.approval_key))
        assert len(ledger["slots"]) == 1 and not ledger["slots"][0]["accepted"]


@pytest.mark.parametrize(
    "fault",
    [
        "timeout",
        "response_lost",
        "empty",
        "invalid_json",
        "wrong_model",
        "bad_usage",
        "revoke",
        "cancel",
        "request_archive",
        "response_archive",
    ],
)
def test_actual_adapter_failure_keeps_nonrefundable_slot_and_never_retries(
    prepared_trial, monkeypatch, tmp_path, fault
):
    data, binding = prepared_trial
    rid = enqueue_generation(data, binding)
    sent = []
    archived = []
    original_archive = trial._archive

    def archive(*args, **kwargs):
        kind = args[-1]
        archived.append(kind)
        result = original_archive(*args, **kwargs)
        if (fault == "request_archive" and kind == trial.REQUEST) or (
            fault == "response_archive" and kind == trial.RESPONSE
        ):
            raise DomainError("OUTCOME_UNKNOWN", "Injected archive transaction failure")
        return result

    monkeypatch.setattr(trial, "_archive", archive)

    def handler(request):
        sent.append(request.content)
        assert str(request.url) == "https://chat.intern-ai.org.cn/api/v1/chat/completions"
        if fault == "timeout":
            raise httpx.ReadTimeout("offline timeout", request=request)
        if fault == "response_lost":
            raise RuntimeError("offline response lost after send")
        if fault == "empty":
            return httpx.Response(200, content=b"")
        if fault == "invalid_json":
            return httpx.Response(200, content=b'{"broken":')
        raw = first_response(data)
        if fault == "wrong_model":
            raw["model"] = "different-model"
        if fault == "bad_usage":
            raw["usage"]["total_tokens"] = 1000000
        if fault in ("cancel", "revoke"):
            with data[0].tx() as c:
                if fault == "cancel":
                    c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))
                else:
                    c.execute(
                        update(grants).where(grants.c.resource_id == data[5]).values(revoked=True)
                    )
        return httpx.Response(200, json=raw)

    worker = Worker(
        data[0], data[1], goal_planner_transport=httpx.MockTransport(handler), pa_trial=binding
    )
    try:
        assert worker.once()
    except (DomainError, RuntimeError) as error:
        if isinstance(error, RuntimeError):
            assert fault == "response_lost" and str(error) == "offline response lost after send"
        # A simulated process loss leaves the durable send unresolved, never success.
    scope = budget.scope_for(binding.contract, binding.approval_key)
    with data[0].tx() as c:
        rows = list(c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings())
        ledger = budget._ledger(c, scope)
        state = (
            c.execute(select(runs.c.status, runs.c.result).where(runs.c.id == rid)).mappings().one()
        )
        marks = (
            c.execute(
                select(delivery_graph_requests.c.request_key).where(
                    delivery_graph_requests.c.app_id == rid,
                    delivery_graph_requests.c.kind == trial.SENT,
                )
            )
            .scalars()
            .all()
        )
        response_events = c.execute(
            select(events.c.id).where(
                events.c.run_id == rid,
                events.c.kind == "PA_TRIAL_BODY",
                events.c.data["family"].as_string() == trial.RESPONSE,
            )
        ).all()
        assert state["status"] not in ("SUCCEEDED", "PARTIAL") and state["result"] is None
        if fault == "request_archive":
            assert sent == [] and rows == [] and ledger["slots"] == [] and marks == []
        else:
            assert len(sent) == len(rows) == len(ledger["slots"]) == len(marks) == 1
            assert not ledger["slots"][0]["accepted"]
            if fault == "response_archive":
                assert response_events == [] and archived.count(trial.RESPONSE) == 1
    before = len(sent)
    # Recovery calls the original read-only ledger; no adapter or authority callback.
    if fault == "request_archive":
        with pytest.raises(DomainError):
            production.recover(data[0], data[3], binding.contract, binding.approval_key)
    else:
        history = production.recover(data[0], data[3], binding.contract, binding.approval_key)
        assert history["dispatch_authorized"] is False
    assert len(sent) == before
    (tmp_path / "actual-failure.json").write_text(
        json.dumps(
            dict(
                fault=fault,
                actual_sends=len(sent),
                attempts=len(rows),
                reserved_slots=len(ledger["slots"]),
                send_markers=len(marks),
                raw_receipt="NOT_PERSISTED_IN_EXPLICIT_WRITE_FAILURE"
                if fault == "response_archive"
                else "SEE_BODY_FACTS",
                archive_calls=archived,
                run_status=state["status"],
                real_models=0,
            ),
            indent=2,
        )
        + "\n"
    )
