"""Synthetic provider protocols only; LIVE-shaped rows are NOT real Intern calls."""

import copy
import json
import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_goal_text_applications import (
    CONTENT,
    confirm,
    fixture_candidate,
    release_instance,
    run_input,
    setup,
    wire,
)

from sim2act import generation_approvals as approval
from sim2act.api import create_app
from sim2act.db import (
    Store,
    attempts,
    delivery_graph_requests,
    goal_application_candidates,
    grants,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


class SimulatedProductionPolicyStore:
    """Test façade only: real SQLite transactions, simulated production eligibility.

    It does not mutate the Store's test_only flag or bypass production initialization.
    PostgreSQL and a real provider remain NOT_RUN.
    """

    test_only = False

    def __init__(self, actual):
        self.actual = actual

    def __getattr__(self, name):
        return getattr(self.actual, name)


def configured(env, monkeypatch, *, production=False):
    data = setup(env)
    store, settings, _, user, pid, text, card = data
    clock = {"at": time.time()}
    monkeypatch.setattr(approval, "now", lambda: clock["at"])
    if production:
        store = SimulatedProductionPolicyStore(store)
    settings = replace(settings, application_generation_activation_enabled=True,
        mode="live" if production else "mock", live_enabled=production,
        token="synthetic-never-external-token" if production else "")
    client = TestClient(create_app(store, settings))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    return (store, settings, client, user, pid, text, card), clock


def prepared(data, *, key="scope", generation_key="exact-generation"):
    _, _, client, _, pid, _, card = data
    body = dict(card_id=card["id"], expected_version=card["version"],
        expected_fingerprint=card["fingerprint"], generation_request_key=generation_key,
        request_key=key)
    response = client.post(f"/api/projects/{pid}/application-provider-scopes", json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def approved(data):
    scope, _ = prepared(data)
    body = dict(expected_scope_fingerprint=scope["scope_fingerprint"], consent=approval.CONSENT,
        budget_note="SIMULATED protocol test; zero real sends or fees; token caps are not a monetary cap",
        request_key="simulated-approval")
    response = data[2].post(f"/api/application-provider-scopes/{scope['approval_id']}/approve", json=body)
    assert response.status_code == 200, response.text
    return scope, response.json(), body


def accepted(data, activation, key="exact-generation"):
    response = data[2].post(f"/api/projects/{data[4]}/goal-cards/{data[6]['id']}/application-runs",
        json=dict(expected_version=data[6]["version"], expected_fingerprint=data[6]["fingerprint"],
            request_key=key, activation=activation))
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def provider(data, clock, *, repair=False, mutate=None):
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        initial = json.loads(payload["messages"][1]["content"])
        assert payload["model"] == "intern-s2" and payload["stream"] is False
        assert len(request.content) <= 32768 and payload["max_tokens"] <= 1024
        if len(sent) == 1:
            assert "content" not in initial["source"], "actual material waits for the provider's tool request"
            raw = wire({"role": "assistant", "content": "", "tool_calls": [{"id": "chosen-read",
                "type": "function", "function": {"name": "resource.read", "arguments": json.dumps({"resource_id": data[5]})}}]}, "tool_calls")
        else:
            actual = json.loads(next(m["content"] for m in payload["messages"] if m["role"] == "tool"))
            assert actual["data"]["content"] == CONTENT and actual["status"] == "VERIFIED"
            assert payload["tools"] == []
            value = fixture_candidate(initial)
            # A model-selected stable label survives; production must validate, not reconstruct a template.
            step = value["manifest"]["workflow"][0]
            step["step_id"] = "provider_chosen_literal_report"
            for output in value["manifest"]["outputs"].values():
                output["ref"] = step["step_id"]
            if repair and len(sent) == 2:
                step["inputs"].pop("term")
            raw = wire({"role": "assistant", "content": json.dumps(value, ensure_ascii=False, separators=(",", ":"))})
        raw["model"] = "Intern-S2"
        if mutate:
            mutate(raw, len(sent), payload)
        clock["at"] += 61  # Synthetic clock; no rate-limit sleep or real provider time claim.
        return httpx.Response(200, json=raw)

    return httpx.MockTransport(handler), sent


def production_http(monkeypatch, transport):
    original = httpx.AsyncClient

    def synthetic_client(*args, **kwargs):
        assert kwargs.get("transport") is None
        return original(*args, **{**kwargs, "transport": transport})

    monkeypatch.setattr(httpx, "AsyncClient", synthetic_client)


@pytest.mark.parametrize("production,repair", [(False, False), (False, True), (True, False), (True, True)])
def test_exact_approved_provider_actual_feedback_candidate_and_cold_worker(env, monkeypatch, production, repair):
    data, clock = configured(env, monkeypatch, production=production)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock, repair=repair)
    settings = replace(data[1], application_generation_live_id=scope["approval_id"] if production else "")
    if production:
        production_http(monkeypatch, transport)
    worker = Worker(data[0], settings, goal_planner_transport=None if production else transport)
    assert worker.once()
    reply = data[2].get(f"/api/runs/{rid}")
    assert reply.status_code == 200, reply.text
    result = reply.json()
    assert result["status"] == "PARTIAL", result
    assert len(sent) == (3 if repair else 2)
    assert result["result"]["candidate"]["manifest"]["workflow"][0]["step_id"] == "provider_chosen_literal_report"
    with data[0].tx() as c:
        rows = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        charges, sending, settlements = approval.audit(data[0], c, data[3], scope["approval_id"])
        assert len(charges) == len(sending) == len(settlements) == len(sent)
        assert all(r["mode"] == ("LIVE" if production else "MOCK") for r in rows)
        assert all(r["parameters"]["model_identity"]["enforced"] is production for r in rows)
    aid, _ = confirm(data, rid, result)
    # Completed proof still works after all sending configuration is off.
    offline = replace(settings, mode="mock", live_enabled=False, token="",
        application_generation_activation_enabled=False, application_generation_live_id="")
    cold = Store(data[1].database_url, test_only=True)
    cold_client = TestClient(create_app(cold, offline))
    cold_client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    cold_data = (cold, offline, cold_client, *data[3:])
    release, instance = release_instance(cold_data, aid)
    fresh = run_input(cold_data, release, instance, {"term": "Beta"}, "unseen-input")
    assert fresh["status"] == "SUCCEEDED" and fresh["result"]["citations"] == [
        {"start_line": 2, "end_line": 2, "quote": "Beta due tomorrow"},
        {"start_line": 4, "end_line": 4, "quote": "<em>Beta literal</em>"}]
    cold_client.close()
    cold.engine.dispose()
    data[2].close()
    if production:
        data[0].engine.dispose()


def test_default_scope_is_closed_and_plain_live_flags_never_grant_calls(env, monkeypatch):
    data = setup(env)
    calls = []
    response = data[2].post(f"/api/projects/{data[4]}/application-provider-scopes",
        json=dict(card_id=data[6]["id"], expected_version=data[6]["version"],
            expected_fingerprint=data[6]["fingerprint"], generation_request_key="not-approved", request_key="scope"))
    assert response.status_code == 400 and response.json()["error"]["code"] == "RESOURCE_UNAVAILABLE"
    reply = data[2].post(f"/api/projects/{data[4]}/goal-cards/{data[6]['id']}/application-runs",
        json=dict(expected_version=data[6]["version"], expected_fingerprint=data[6]["fingerprint"], request_key="ordinary"))
    rid = reply.json()["run_id"]
    from sim2act.model import InternModel

    def forbidden_send(*args, **kwargs):
        calls.append("FORBIDDEN SEND")
        raise AssertionError("Plain flags must not reach the provider adapter")

    monkeypatch.setattr(InternModel, "request_serialized", forbidden_send)
    selected = replace(data[1], live_enabled=True, token="synthetic-not-permission",
        application_generation_activation_enabled=True, application_generation_live_id="gaapproval_" + "a" * 32)
    assert Worker(data[0], selected).once()
    with data[0].tx() as c:
        assert not c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()
    assert calls == []


@pytest.mark.parametrize("change", ["key", "goal", "approval-fp", "scope-fp"])
def test_exact_intent_submission_rejects_coordinated_different_request(env, monkeypatch, change):
    data, _ = configured(env, monkeypatch)
    _, grant, _ = approved(data)
    activation = copy.deepcopy(grant["activation"])
    request = dict(expected_version=data[6]["version"], expected_fingerprint=data[6]["fingerprint"],
        request_key="exact-generation", activation=activation)
    if change == "key":
        request["request_key"] = "another-generation"
    elif change == "goal":
        request["expected_version"] += 1
    else:
        activation["approval_fingerprint" if change == "approval-fp" else "scope_fingerprint"] = "a" * 64
    response = data[2].post(f"/api/projects/{data[4]}/goal-cards/{data[6]['id']}/application-runs", json=request)
    assert response.status_code == 409, response.text
    with data[0].tx() as c:
        assert not c.execute(select(runs.c.id).where(runs.c.request_key.in_(["exact-generation", "another-generation"]))).first()


@pytest.mark.parametrize("kind", ["unknown-usage", "wrong-model", "extra-tool", "truncated", "oversized"])
def test_actual_response_fault_never_forms_candidate_or_resends(env, monkeypatch, kind):
    data, clock = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])

    def mutate(raw, index, payload):
        if kind == "unknown-usage":
            raw.pop("usage")
        elif kind == "wrong-model":
            raw["model"] = "gpt-unapproved"
        elif kind == "extra-tool":
            raw["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "arbitrary.code"
        elif kind == "truncated":
            raw["choices"][0]["finish_reason"] = "length"
        else:
            raw["private_oversized"] = "x" * 32769

    transport, sent = provider(data, clock, mutate=mutate)
    assert Worker(data[0], data[1], goal_planner_transport=transport).once()
    with data[0].tx() as c:
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert run["result"] is None and run["status"] != "PARTIAL"
        assert not c.execute(select(goal_application_candidates.c.app_id)).first()
        charge, sending, settled = approval.audit(data[0], c, data[3], scope["approval_id"])
        assert len(charge) == len(sending) == len(settled) == 1
    assert len(sent) == 1


def test_revoke_stops_generation_without_recovering_old_goal_body(env, monkeypatch):
    data, _ = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True, revision=2))
    response = data[2].post(f"/api/application-provider-scopes/{scope['approval_id']}/revoke",
        json=dict(expected_scope_fingerprint=scope["scope_fingerprint"], request_key="stop", reason="SIMULATED explicit withdrawal"))
    assert response.status_code == 200 and response.json()["status"] == "REVOKED", response.text
    assert Worker(data[0], data[1]).once() is False  # Rejected before private queue payload load.
    with data[0].tx() as c:
        assert not c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()
        assert c.execute(select(delivery_graph_requests.c.kind).where(delivery_graph_requests.c.app_id == scope["approval_id"],
            delivery_graph_requests.c.kind == approval.REVOKE)).first()


@pytest.mark.parametrize("change", ["live_enabled", "token", "token_replaced", "live_id", "mode"])
def test_provider_is_rechecked_at_actual_wire_guard(env, monkeypatch, change):
    data, clock = configured(env, monkeypatch, production=True)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock)
    production_http(monkeypatch, transport)
    selected = replace(data[1], application_generation_live_id=scope["approval_id"])
    worker = Worker(data[0], selected)
    build = httpx.Client.build_request

    def after_construction(client, *args, **kwargs):
        request = build(client, *args, **kwargs)
        updates = {"live_enabled": False} if change == "live_enabled" else {"token": ""} if change == "token" else {"token": "other-synthetic-token"} if change == "token_replaced" else {"application_generation_live_id": "gaapproval_" + "a" * 32} if change == "live_id" else {"mode": "mock"}
        worker.s = replace(worker.s, **updates)
        return request

    monkeypatch.setattr(httpx.Client, "build_request", after_construction)
    assert worker.once()
    assert sent == [], "settings captured before the actual wire guard must not authorize a later revoked send"
    with data[0].tx() as c:
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert run["result"] is None


def test_post_settlement_finalization_failure_keeps_original_attempt_and_failure_event(env, monkeypatch):
    data, clock = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock)
    original = Worker.finish

    def injected_finalizer(worker, run_id, fence, state, *args, **kwargs):
        if state == "PARTIAL":
            raise DomainError("BUDGET_EXHAUSTED", "Synthetic final commit failure after settled response")
        return original(worker, run_id, fence, state, *args, **kwargs)

    monkeypatch.setattr(Worker, "finish", injected_finalizer)
    assert Worker(data[0], data[1], goal_planner_transport=transport).once()
    with data[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["result"] is None and row["status"] == "FAILED"
        assert row["error"]["code"] == "BUDGET_EXHAUSTED", "a completed immutable response must not hide the final commit failure"
        charges, _, settled = approval.audit(data[0], c, data[3], scope["approval_id"])
        assert len(charges) == len(settled) == len(sent) == 2
        assert all(c.execute(select(attempts.c.error).where(attempts.c.id == r.attempt_id)).scalar() is None for r in charges)
        from sim2act.db import events
        event = c.execute(select(events.c.data).where(events.c.run_id == rid,
            events.c.kind == "GA_POST_SETTLEMENT_REJECTION")).scalar_one()
        assert event["error"] == "BUDGET_EXHAUSTED" and event["attempt_id"] == charges[-1].attempt_id


@pytest.mark.parametrize("kind", ["lease", "approval"])
def test_last_state_write_rolls_back_after_original_time_limit(env, monkeypatch, kind):
    from types import SimpleNamespace

    from sim2act import worker as worker_module
    from sim2act.db import events
    data, clock = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock)
    original = data[0].event
    actual_time = time.time
    def expire(c, run_id, event_kind, value):
        original(c, run_id, event_kind, value)
        if run_id == rid and event_kind == "STATE" and value["status"] == "PARTIAL":
            if kind == "approval":
                clock["at"] = grant["deadline"] + 1
            else:
                monkeypatch.setattr(worker_module, "time", SimpleNamespace(time=lambda: actual_time() + 100))
    monkeypatch.setattr(data[0], "event", expire)
    assert Worker(data[0], data[1], goal_planner_transport=transport).once()
    with data[0].tx() as c:
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert run["status"] == "FAILED" and run["result"] is None
        assert run["error"]["code"] == "VERSION_CONFLICT"
        values = c.execute(select(events.c.data).where(events.c.run_id == rid, events.c.kind == "STATE")).scalars().all()
        assert all(value["status"] != "PARTIAL" for value in values)
        charges, _, settled = approval.audit(data[0], c, data[3], scope["approval_id"])
        assert len(charges) == len(settled) == len(sent) == 2


def test_revoked_approval_rejects_unconfirmed_candidate_with_no_partial_app(env, monkeypatch):
    from sim2act.db import app_drafts, principals
    data, clock = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, _ = provider(data, clock)
    assert Worker(data[0], data[1], goal_planner_transport=transport).once()
    result = data[2].get(f"/api/runs/{rid}").json()
    with data[0].tx() as c:
        before = {table.name: c.execute(select(table)).mappings().all() for table in (app_drafts, principals, grants)}
    assert data[2].post(f"/api/application-provider-scopes/{scope['approval_id']}/revoke", json=dict(
        expected_scope_fingerprint=scope["scope_fingerprint"], request_key="stop", reason="Synthetic revoke before confirmation")).status_code == 200
    response = data[2].post(f"/api/runs/{rid}/confirm-application-candidate", json=dict(expected_version=result["version"],
        candidate_fingerprint=result["result"]["candidate_fingerprint"], name="No app", request_key="confirm"))
    assert response.status_code == 409, response.text
    with data[0].tx() as c:
        assert before == {table.name: c.execute(select(table)).mappings().all() for table in (app_drafts, principals, grants)}


def test_approved_scope_list_requires_explicit_existing_approval(env, monkeypatch):
    data, _ = configured(env, monkeypatch)
    path = f"/api/projects/{data[4]}/goal-cards/{data[6]['id']}/application-provider-scopes"
    assert data[2].get(path).json()["options"] == []
    scope, grant, _ = approved(data)
    response = data[2].get(path)
    assert response.status_code == 200, response.text
    value = response.json()
    assert len(value["options"]) == 1 and value["default_request_budget"] == 0
    assert value["options"][0]["activation"] == grant["activation"]
    assert value["options"][0]["request_key"] == "exact-generation"
    assert data[2].get(path).json() == value
    with data[0].tx() as c:
        assert not c.execute(select(attempts.c.id)).first() and not c.execute(select(runs.c.id)).first()
