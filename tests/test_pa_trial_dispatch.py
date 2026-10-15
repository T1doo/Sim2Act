"""Existing P-A Worker/InternModel wiring, explicit synthetic transport only."""

import json
import time
from dataclasses import replace

import httpx
import pytest
from sqlalchemy import select, update
from test_natural_live_admission import frozen
from test_natural_spec_apps import setup, wire

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as budget
from sim2act import pa_trial_dispatch as trial
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
    except DomainError:
        pass  # Stale/revoked finalization cannot invent success.
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
