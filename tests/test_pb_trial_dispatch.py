"""Explicit isolated P-B controller trials; no private SQL/UDF diagnostics."""

import base64
import hashlib
import json
import sqlite3
import sys
import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import conftest
import httpx
import pytest
import test_natural_spec_apps as apps
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from test_natural_live_admission import frozen
from test_natural_source_archives import snapshot

from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_specs as natural
from sim2act import pa_trial_dispatch as trial
from sim2act import pb_natural_specs as pb
from sim2act import production_trial_admission as production
from sim2act.api import create_app
from sim2act.db import Store, attempts, delivery_graph_requests, fingerprint, grants, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def approve_stage(data, binding, stage, rid):
    reviewed = gate.stage_review(
        data[0], data[3], binding.contract, binding.approval_key, stage, rid
    )
    consent = gate.StageApproveInput(
        authority=gate.StageAuthority.model_validate(reviewed["authority"]),
        expected_authority_fingerprint=reviewed["authority_fingerprint"],
        approval_key=binding.approval_key,
        request_key=stage + "-pb-stage-consent",
        consent="BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL",
    )
    gate.approve_stage(data[0], data[3], binding.contract, consent)
    return consent


@pytest.fixture(scope="module")
def prefix(tmp_path_factory):
    root = tmp_path_factory.mktemp("actual-pb-prefix")
    environment = conftest.env.__wrapped__(root)
    env = next(environment)
    data = apps.setup(env)
    subject = production.canonical_quota_subject("offline-pb-account")
    data = (data[0], replace(data[1], quota_subject=subject), *data[2:])
    data[0].initialize(quota_subject=subject)
    pa, approval = frozen(data, ttl=1800.0)
    contract = gate.PBTrialContract(
        **{**pa.model_dump(), "quota_subject": subject},
        path="P-B",
        extraction_request_key="original-pb-trial-extraction",
        extraction_recipe=apps.recipe("ordered"),
    )
    approval = approval.model_copy(
        update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump()))
    )
    gate.approve(data[0], data[3], contract, approval)
    account = production.AccountEvidence(
        principal_id=data[3],
        project_id=data[4],
        trial_key=contract.trial_key,
        contract_fingerprint=fingerprint(contract.model_dump()),
        account_id="offline-pb-account",
        quota_subject=subject,
        evidence_sha256="b" * 64,
        checked_at=time.time(),
        expires_at=contract.expires_at,
        legal_free_entitlement=True,
        enforced_non_chargeable=True,
    )
    binding = trial.PATrialBinding(
        contract,
        approval.request_key,
        production.OfflineRegistry((account,), production.OfflineSender()),
    )
    workers, refresh_errors = [], []
    stopped = threading.Event()

    def fresh_binding():
        fresh = account.model_copy(update=dict(checked_at=time.time()))
        return replace(binding, registry=replace(binding.registry, accounts=(fresh,)))

    def make_worker(data, transport):
        worker = Worker(
            data[0], data[1], goal_planner_transport=transport, pa_trial=fresh_binding()
        )
        workers.append(worker)
        return worker

    def refresh():
        try:
            while not stopped.wait(0.25):
                for worker in tuple(workers):
                    # Revocation injected by a test must remain revoked.
                    old = worker.pa_trial.registry.accounts[0]
                    fresh = old.model_copy(update=dict(checked_at=time.time()))
                    worker.pa_trial = replace(
                        worker.pa_trial,
                        registry=replace(worker.pa_trial.registry, accounts=(fresh,)),
                    )
        except BaseException as error:
            refresh_errors.append(error)

    refresher = threading.Thread(target=refresh, daemon=True)
    refresher.start()
    original_async = httpx.MockTransport.handle_async_request
    original_sync = httpx.MockTransport.handle_request
    captured = []
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                apps, "Worker", lambda *a, **k: make_worker(data, k["goal_planner_transport"])
            )
            generation, _, release, inst, generated = apps.ready(data, style="ordered")
        assert len(generated) == 3
        source_id = apps.enqueue(data, release, inst)
        approve_stage(data, binding, "source", source_id)
        normal = apps.transport([], apps.SOURCE)

        def source_handler(request):
            raw = normal.handle_request(request).json()
            raw["archive_note"] = "实际离线原体"
            payload = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode()
            captured.append((request.content, payload))
            return httpx.Response(200, content=payload)

        assert make_worker(data, httpx.MockTransport(source_handler)).once()
        assert data[2].get("/api/runs/" + source_id).json()["status"] == "SUCCEEDED"
        assert len(captured) == 2
        route = f"/api/projects/{data[4]}/natural-spec-task-runs/{source_id}"
        options = data[2].get(route + "/extraction-options")
        assert options.status_code == 200, options.text
        cold = contract.bindings[1]
        review = dict(
            source_run_id=source_id,
            expected_source_proof_fingerprint=options.json()["source_proof_fingerprint"],
            expected_source_recipe_fingerprint=options.json()["recipe_fingerprint"],
            card_id=cold.card_id,
            expected_goal_version=cold.goal_version,
            expected_goal_fingerprint=cold.goal_fingerprint,
            expected_source_hash=cold.source_hash,
            recipe=contract.extraction_recipe.model_dump(exclude_none=True),
            name="Trial source reuse",
            request_key=contract.extraction_request_key,
        )
        preview = data[2].post(route + "/extraction-reviews", json=review)
        assert preview.status_code == 200, preview.text
        body = pb.ExtractInput(
            review=review,
            expected_review_fingerprint=preview.json()["review_fingerprint"],
            consent=pb.CONSENT,
            artifact_write_consent=natural.CONSENT,
        )
        saved = root / "verified-five-slot-prefix.db"
        with sqlite3.connect(data[0].engine.url.database) as origin, sqlite3.connect(saved) as copy:
            origin.backup(copy)
        ledger = production.recover(data[0], data[3], contract, binding.approval_key)["ledger"]
        assert len(ledger["slots"]) == 5 and all(s["accepted"] for s in ledger["slots"])
        assert httpx.MockTransport.handle_async_request is original_async
        assert httpx.MockTransport.handle_request is original_sync
        (root / "actual-prefix.json").write_text(
            json.dumps(
                dict(
                    generation=generation,
                    source=source_id,
                    actual_dispatches=5,
                    source_raw_bodies=2,
                    ledger=ledger,
                    expires_at=contract.expires_at,
                    initial_fixture_ttl=1800,
                    run_seconds=data[1].run_seconds,
                    lease_seconds=data[1].lease_seconds,
                    synthetic_account_refresh=True,
                    real_models=0,
                ),
                indent=2,
            )
        )
        yield SimpleNamespace(
            data=data,
            binding=binding,
            body=body,
            source_id=source_id,
            saved=saved,
            make_worker=make_worker,
            refresh_errors=refresh_errors,
            original_async=original_async,
            original_sync=original_sync,
        )
        assert not refresh_errors
    finally:
        stopped.set()
        refresher.join(timeout=2)
        data[2].close()
        environment.close()


@pytest.fixture
def cloned(prefix, tmp_path):
    target = tmp_path / "isolated-prefix-copy.db"
    with sqlite3.connect(prefix.saved) as origin, sqlite3.connect(target) as copy:
        origin.backup(copy)
    store = Store("sqlite:///" + str(target), test_only=True)
    settings = replace(prefix.data[1], database_url=str(store.engine.url))
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    data = (store, settings, client, *prefix.data[3:])
    try:
        yield data
    finally:
        client.close()
        store.engine.dispose()


def no_send(request):
    raise AssertionError("Extraction must not send a model request")


def extracted(prefix, data):
    worker = prefix.make_worker(data, httpx.MockTransport(no_send))
    made = trial.extract_pb(worker, data[3], prefix.source_id, prefix.body)
    release, inst = apps.instance(data, made["id"])
    return worker, made, release, inst


def test_pb_full_actual_worker_extraction_and_cold(prefix, cloned, tmp_path):
    data = cloned
    worker, made, release, inst = extracted(prefix, data)
    before = snapshot(data[0])
    path = (f"/api/projects/{data[4]}/natural-spec-task-runs/{prefix.source_id}"
        f"/extractions/by-key/{prefix.binding.contract.extraction_request_key}")
    recovered = data[2].get(path)
    assert recovered.status_code == 200 and recovered.json() == made
    assert snapshot(data[0]) == before  # Original-key recovery after a lost return.
    resolved = archive.resolve_trial_source(
        data[0], data[3], prefix.binding.contract, prefix.binding.approval_key
    )
    assert resolved.public_receipt["source_run_id"] == prefix.source_id
    assert all(
        a["decoded_body_sha256"] != a["canonical_ascii_sha256"]
        for a in resolved.public_receipt["attempts"]
    )
    cold = apps.enqueue(data, release, inst, key=prefix.binding.contract.stage_keys.cold)
    approve_stage(data, prefix.binding, "cold", cold)
    sent = []
    assert prefix.make_worker(data, apps.transport(sent, apps.COLD)).once()
    state = data[2].get("/api/runs/" + cold).json()
    assert state["status"] == "SUCCEEDED", state
    assert len(sent) == 2 and apps.SOURCE not in json.dumps(sent)
    history = production.recover(
        data[0], data[3], prefix.binding.contract, prefix.binding.approval_key
    )
    assert history["reserved_requests"] == 7 and history["total_tokens"] == 7000
    assert all(s["accepted"] for s in history["ledger"]["slots"])
    gaps = [
        b["reserved_at"] - a["reserved_at"]
        for a, b in zip(history["ledger"]["slots"], history["ledger"]["slots"][1:], strict=False)
    ]
    assert len(gaps) == 6 and min(gaps) >= 60
    with data[0].tx() as c:
        bodies = (
            c.execute(
                select(delivery_graph_requests.c.snapshot).where(
                    delivery_graph_requests.c.kind.in_([trial.REQUEST, trial.RESPONSE])
                )
            )
            .scalars()
            .all()
        )
        assert len(bodies) == 14
        for saved in bodies:
            body = saved["response"]
            payload = base64.b64decode(body["body_b64"], validate=True)
            assert hashlib.sha256(payload).hexdigest() == body["sha256"]
    assert httpx.MockTransport.handle_async_request is prefix.original_async
    assert httpx.MockTransport.handle_request is prefix.original_sync
    assert not prefix.refresh_errors
    (tmp_path / "actual-pb-seven-slots.json").write_text(
        json.dumps(
            dict(
                accounting=history,
                source_receipt=resolved.public_receipt,
                actual_cold_sends=2,
                original_prefix_dispatches=5,
                body_archives=14,
                gaps=gaps,
                transport_class_unmodified=True,
                real_models=0,
                live_allowed=False,
            ),
            indent=2,
        )
    )


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_key",
        "wrong_recipe",
        "wrong_goal",
        "missing_ns_body",
        "missing_trial_body",
        "missing_marker",
        "source_version",
        "after_write_failure",
        "revoke_after_write",
    ],
)
def test_pb_trial_extraction_refusals_and_atomic_rollback(
    prefix, cloned, monkeypatch, tmp_path, fault
):
    data = cloned
    worker = prefix.make_worker(data, httpx.MockTransport(no_send))
    body = prefix.body
    injected = []
    if fault.startswith("wrong_"):
        changes = (
            dict(request_key="unapproved-extraction")
            if fault == "wrong_key"
            else (
                dict(recipe=natural.Recipe.model_validate(apps.recipe("single")))
                if fault == "wrong_recipe"
                else dict(expected_goal_fingerprint="0" * 64)
            )
        )
        body = body.model_copy(update=dict(review=body.review.model_copy(update=changes)))
        injected.append(fault)
    elif fault in ("missing_ns_body", "missing_trial_body", "missing_marker", "source_version"):
        with data[0].tx() as c:
            if fault == "source_version":
                old = c.execute(
                    select(runs.c.version).where(runs.c.id == prefix.source_id)
                ).scalar_one()
                c.execute(update(runs).where(runs.c.id == prefix.source_id).values(version=old + 1))
            else:
                kind = {
                    "missing_ns_body": archive.RESPONSE,
                    "missing_trial_body": trial.RESPONSE,
                    "missing_marker": trial.SENT,
                }[fault]
                aid = (
                    c.execute(
                        select(attempts.c.id)
                        .where(attempts.c.run_id == prefix.source_id)
                        .order_by(attempts.c.id)
                    )
                    .scalars()
                    .first()
                )
                c.execute(
                    delete(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == prefix.source_id,
                        delivery_graph_requests.c.request_key == aid,
                        delivery_graph_requests.c.kind.in_([kind, kind + "_seal"]),
                    )
                )
        injected.append(fault)
    else:
        original = pb._extract

        def after_write(store, c, *args):
            result = original(store, c, *args)
            injected.append(fault)
            if fault == "after_write_failure":
                raise DomainError("VERIFICATION_FAILED", "After original extraction write group")
            c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
            return result

        monkeypatch.setattr(pb, "_extract", after_write)
    before = snapshot(data[0])
    with pytest.raises(DomainError) as denied:
        trial.extract_pb(worker, data[3], prefix.source_id, body)
    assert injected == [fault]
    assert snapshot(data[0]) == before
    history = production.recover(
        data[0], data[3], prefix.binding.contract, prefix.binding.approval_key
    )
    assert history["reserved_requests"] == 5
    (tmp_path / "actual-extraction-refusal.json").write_text(
        json.dumps(
            dict(
                fault=fault,
                injected=injected,
                error=denied.value.code,
                all_tables_unchanged=True,
                new_sends=0,
                slots=5,
                real_models=0,
            ),
            indent=2,
        )
    )


@pytest.mark.parametrize(
    "fault", ["source_revoke", "source_version", "lost_response", "bad_result", "response_archive"]
)
def test_pb_cold_actual_failure_never_accepts_or_retries(
    prefix, cloned, monkeypatch, tmp_path, fault
):
    from sim2act import app_jobs

    data = cloned
    public_errors = []
    original_failure = app_jobs.fail_job

    def failure(worker, run, error):
        public_errors.append(error.public())
        return original_failure(worker, run, error)

    monkeypatch.setattr(app_jobs, "fail_job", failure)
    _, _, release, inst = extracted(prefix, data)
    cold = apps.enqueue(data, release, inst, key=prefix.binding.contract.stage_keys.cold)
    approve_stage(data, prefix.binding, "cold", cold)
    injected, sent = [], []
    normal = apps.transport([], apps.COLD)
    original_archive = trial._archive

    def fail_archive(*args):
        result = original_archive(*args)
        if fault == "response_archive" and args[-1] == trial.RESPONSE:
            injected.append(fault)
            raise DomainError("OUTCOME_UNKNOWN", "Explicit trial response archive rollback")
        return result

    monkeypatch.setattr(trial, "_archive", fail_archive)

    def handler(request):
        sent.append(request.content)
        if fault == "lost_response":
            injected.append(fault)
            raise RuntimeError("Explicit lost P-B response")
        if fault in ("source_revoke", "source_version"):
            with data[0].tx() as c:
                if fault == "source_revoke":
                    c.execute(
                        update(grants).where(grants.c.resource_id == data[5]).values(revoked=True)
                    )
                else:
                    version = c.execute(
                        select(runs.c.version).where(runs.c.id == prefix.source_id)
                    ).scalar_one()
                    c.execute(
                        update(runs)
                        .where(runs.c.id == prefix.source_id)
                        .values(version=version + 1)
                    )
            injected.append(fault)
        response = normal.handle_request(request)
        if fault == "bad_result":
            raw = response.json()
            items = json.loads(raw["choices"][0]["message"]["content"])
            items["items"][0]["citations"][0]["quote"] = "Wrong quote"
            raw["choices"][0]["message"]["content"] = json.dumps(items)
            injected.append(fault)
            return httpx.Response(200, json=raw)
        return response

    worker = prefix.make_worker(data, httpx.MockTransport(handler))
    once_result = None
    escaped_domain_error = None
    original_once = worker.once

    def once():
        nonlocal once_result
        once_result = original_once()
        return once_result

    monkeypatch.setattr(worker, "once", once)
    try:
        assert worker.once()
    except DomainError as error:
        escaped_domain_error = error.public()
    except RuntimeError as error:
        assert fault == "lost_response" and str(error) == "Explicit lost P-B response"
    finally:
        pending_error = sys.exception()
        try:
            (tmp_path / "actual-dispatch-boundary.json").write_text(json.dumps(dict(
                fault=fault, injected=injected, actual_sends=len(sent),
                worker_once_return=once_result, escaped_domain_error=escaped_domain_error,
                worker_public_errors=public_errors), indent=2))
        except (OSError, TypeError, ValueError) as receipt_error:
            if pending_error is None:
                raise
            pending_error.add_note(
                f"Dispatch receipt write failed: {type(receipt_error).__name__}"
            )
    assert injected == [fault] and len(sent) == 1, public_errors
    response = data[2].get("/api/runs/" + cold)
    if fault == "source_revoke" or (fault == "source_version" and response.status_code != 200):
        # Source scope still gates HTTP readback after the injected invalidation.
        expected = 403 if fault == "source_revoke" else 409
        assert response.status_code == expected
        assert response.json()["error"]["code"] in (
            {"PERMISSION_DENIED", "GRANT_REVOKED"} if expected == 403 else {"VERSION_CONFLICT"})
        with data[0].tx() as c:
            state = dict(c.execute(select(runs.c.status, runs.c.result)
                .where(runs.c.id == cold)).mappings().one())
    else:
        assert response.status_code == 200
        state = response.json()
    assert state["status"] != "SUCCEEDED" and state["result"] is None
    history = production.recover(
        data[0], data[3], prefix.binding.contract, prefix.binding.approval_key
    )
    slots = [s for s in history["ledger"]["slots"] if s["reservation"]["stage"] == "cold"]
    assert len(slots) == 1 and not slots[0]["accepted"]
    restarted = Store(data[1].database_url, test_only=True)
    try:
        assert (
            production.recover(
                restarted, data[3], prefix.binding.contract, prefix.binding.approval_key
            )
            == history
        )
        if fault == "lost_response":
            current = (restarted, *data[1:])
            prefix.make_worker(current, httpx.MockTransport(no_send)).once()
            assert production.recover(restarted, data[3], prefix.binding.contract,
                prefix.binding.approval_key) == history
    finally:
        restarted.engine.dispose()
    assert len(sent) == 1
    (tmp_path / "actual-cold-refusal.json").write_text(
        json.dumps(
            dict(
                fault=fault,
                injected=injected,
                actual_new_sends=1,
                original_prefix_slots=5,
                original_key_history=history,
                status=state["status"],
                http_readback_status=response.status_code,
                http_readback_error=response.json().get("error"),
                real_models=0,
                raw_receipt="NOT_PERSISTED" if fault == "response_archive" else "SEE_BODY_FACTS",
            ),
            indent=2,
        )
    )



@pytest.mark.parametrize("fault", ["none", "source_version", "authority", "instance", "input", "limits"])
def test_pb_source_stage_single_proof_and_read_boundaries(prefix, cloned, monkeypatch, fault):
    """An actual successful source is reproved each call; stale continuations fail."""
    from sim2act import pa_spec_apps as spec
    from sim2act.db import internal_instances

    data = cloned
    store, user = data[0], data[3]
    contract, key = prefix.binding.contract, prefix.binding.approval_key
    original_source, original_bound, original_origin = pb.source, spec.bound, spec.verify_origin
    sources, bounds, origins, injected = [], [], [], []
    bound_depth = [0]

    def counted_bound(*args, **kwargs):
        bounds.append(True)
        bound_depth[0] += 1
        try:
            return original_bound(*args, **kwargs)
        finally:
            bound_depth[0] -= 1

    def counted_origin(*args, **kwargs):
        # Count origin validation inside the actual binding proof; separate
        # stage generation-source validation still executes independently.
        if bound_depth[0]:
            origins.append(args[3]["id"])
        return original_origin(*args, **kwargs)

    def source(*args, **kwargs):
        result = original_source(*args, **kwargs)
        sources.append(True)
        if fault == "none":
            return result
        c = args[1]
        injected.append(fault)
        if fault == "source_version":
            c.execute(update(runs).where(runs.c.id == prefix.source_id)
                .values(version=runs.c.version + 1))
        elif fault == "authority":
            c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
        elif fault == "instance":
            c.execute(update(internal_instances).where(
                internal_instances.c.id == result[0]["snapshot"]["instance_id"])
                .values(revision=internal_instances.c.revision + 1))
        elif fault == "input":
            result[0]["snapshot"]["input"]["unapproved_source_stage_field"] = True
        elif fault == "limits":
            args[5].max_requests += 1
        return result

    monkeypatch.setattr(pb, "source", source)
    monkeypatch.setattr(spec, "bound", counted_bound)
    monkeypatch.setattr(spec, "verify_origin", counted_origin)
    before = snapshot(store)
    if fault == "none":
        with store.tx() as c:
            first = archive._source_prefix(store, c, user, contract, key)
            assert len(sources) == len(bounds) == 1
            assert origins.count(first[4]["source_app_id"]) == 1
            second = archive._source_prefix(store, c, user, contract, key)
            assert len(sources) == len(bounds) == 2  # No proof retained between roots.
            assert origins.count(first[4]["source_app_id"]) == 2
            reference, job = gate._stage_current(store, c, user, contract, "source", prefix.source_id)
            assert first[2] == second[2] == reference
            assert dict(first[3]) == dict(second[3]) == dict(job)
            assert first[4] == second[4]
            _, complete = original_source(store, c, user, data[4], prefix.source_id, gate._limits(contract))
            assert complete == first[4]
        assert not injected
    else:
        with pytest.raises(DomainError):
            with store.tx() as c:
                archive._source_prefix(store, c, user, contract, key)
        assert sources == [True] and injected == [fault]
    assert snapshot(store) == before
