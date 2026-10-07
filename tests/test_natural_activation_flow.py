"""Actual owner API, ordinary Worker, persistent slots and isolated provider wire."""

import copy
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from test_natural_goal_planning import authority, response, rows

from sim2act import goal_planner
from sim2act import natural_activations as activation
from sim2act.api import create_app
from sim2act.db import attempts, events, natural_activations, operations, reservations, runs
from sim2act.worker import Worker


def setup(env, *, enabled=True):
    store, settings, _, user, other, pid, _ = env
    settings = replace(settings, goal_planner_provider="intern-s2", natural_activation_enabled=enabled)
    client = TestClient(create_app(store, settings))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    resource = client.post(f"/api/projects/{pid}/resources", json={
        "name": "fixed.csv", "format": "csv", "content": activation.CSV,
    }).json()["id"]
    cards = {}
    for kind in activation.KINDS:
        created = client.post(f"/api/projects/{pid}/goal-cards",
                              json=activation.synthetic_goal(resource, kind))
        assert created.status_code == 201, created.text
        card = client.get(f"/api/goal-cards/{created.json()['id']}").json()
        cards[kind] = card
    return store, settings, client, user, other, pid, resource, cards


def draft(value):
    _, _, client, _, _, pid, _, cards = value
    return client.post(f"/api/projects/{pid}/natural-activations", json={
        "goal_bindings": [{"kind": kind, "card_id": card["id"],
                           "expected_version": card["version"],
                           "expected_fingerprint": card["fingerprint"]}
                          for kind, card in cards.items()],
        "request_key": "explicit-fixed-session",
    })


def approved(value):
    result = draft(value)
    assert result.status_code == 201, result.text
    current = result.json()
    body = {"expected_version": current["version"],
            "expected_scope_fingerprint": current["scope_fingerprint"],
            "request_key": "approve-once", "consent": activation.CONSENT}
    result = value[2].post(f"/api/natural-activations/{current['id']}/approve", json=body)
    assert result.status_code == 200, result.text
    return result.json(), body


def submit(value, session, kind="sum_quantity_z", key="activated-run"):
    card = value[-1][kind]
    return value[2].post(
        f"/api/natural-activations/{session['id']}/goal-cards/{card['id']}/planned-runs",
        json={"expected_version": card["version"], "expected_fingerprint": card["fingerprint"],
              "request_key": key},
    )


def wire(value, kind="sum_quantity_z"):
    card = value[-1][kind]
    return {"version": "natural-goal-plan.v1", "source_goal_fingerprint": card["fingerprint"],
            "interpretation": {"objective": card["content"]["goal"],
                               "assumptions": [], "unresolved": []},
            "steps": [{"id": "only", "tool_ref": "resource.read" if kind == "read_preview"
                       else "data.aggregate_csv", "resource_id": value[-2], "depends_on": [],
                       **({"column": "quantity_z"} if kind == "sum_quantity_z" else {})}]}


def revoke(value, session):
    result = value[2].post(f"/api/natural-activations/{session['id']}/revoke", json={
        "expected_version": session["version"],
        "expected_scope_fingerprint": session["scope_fingerprint"], "request_key": "revoke-once",
    })
    assert result.status_code == 200, result.text
    return result.json()


def confirmation(client, rid):
    view = client.get(f"/api/runs/{rid}")
    assert view.status_code == 200, view.text
    view = view.json()
    return {"expected_version": view["version"],
            "expected_plan_fingerprint": view["natural_plan"]["fingerprint"],
            "request_key": "confirm-exact-plan"}


def test_disabled_activation_has_zero_dml_and_network(env):
    value = setup(env, enabled=False)
    store, _, _, *_ = value
    before = rows(store, events), rows(store, runs), authority(store)
    assert draft(value).status_code == 503
    assert not rows(store, natural_activations) and not rows(store, attempts)
    assert (rows(store, events), rows(store, runs), authority(store)) == before


def test_two_fixed_goals_actual_slots_receipts_history_no_hidden_calls(env):
    value = setup(env)
    store, settings, client, *_ = value
    session, approval_body = approved(value)
    before = authority(store)
    sent = []
    for kind in activation.KINDS:
        accepted = submit(value, session, kind, kind)
        assert accepted.status_code == 202, accepted.text
        rid = accepted.json()["run_id"]

        def handler(request, kind=kind):
            actual = json.loads(request.content)
            assert actual["max_tokens"] == 512 and actual["tools"] == []
            sent.append(request.content)
            return httpx.Response(200, json=response(wire(value, kind)))

        worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
        assert worker.once()
        body = confirmation(client, rid)
        assert len(rows(store, operations)) == len(sent) - 1
        confirmed = client.post(f"/api/runs/{rid}/confirm-natural-plan", json=body)
        assert confirmed.status_code == 200, confirmed.text
        assert client.post(f"/api/runs/{rid}/confirm-natural-plan", json=body).json() == confirmed.json()
        assert worker.once()
        final = client.get(f"/api/runs/{rid}").json()
        assert final["status"] == "PARTIAL" and final["result"]["goal_acceptance"] == "NOT_RUN"
        if kind == "sum_quantity_z":
            assert final["result"]["receipts"][0]["data"]["sum"] == "19"
        assert not worker.once()
        assert client.get(f"/api/runs/{rid}").json() == final
    info = client.get(f"/api/natural-activations/{session['id']}").json()
    assert info["charged_requests"] == len(sent) == len(rows(store, attempts)) == 2
    assert 0 < info["reserved_tokens"] <= 22000 and len(rows(store, operations)) == 2
    retry = client.post(f"/api/natural-activations/{session['id']}/approve", json=approval_body)
    assert retry.status_code == 200 and retry.json()["approval"] == session["approval"]
    # Existing key replay is a readback; new key cannot reset the per-goal slot.
    rejected = submit(value, session, key="extra")
    assert rejected.status_code == 202, rejected.text
    assert worker.once()
    extra = client.get(f"/api/runs/{rejected.json()['run_id']}").json()
    assert extra["error"]["code"] == "BUDGET_EXHAUSTED"
    assert len(rows(store, attempts)) == len(rows(store, reservations)) == 2
    assert authority(store) == before and len(sent) == 2


@pytest.mark.parametrize("when", ["before_guard", "in_flight", "before_confirm", "before_dispatch"])
def test_revoke_cut_points_never_execute_new_tools(env, monkeypatch, when):
    value = setup(env)
    store, settings, client, *_ = value
    session, _ = approved(value)
    accepted = submit(value, session)
    assert accepted.status_code == 202, accepted.text
    rid = accepted.json()["run_id"]
    sent = []
    def handler(request):
        sent.append(request.content)
        if when == "in_flight":
            revoke(value, session)
        return httpx.Response(200, json=response(wire(value)))
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    if when == "before_guard":
        original = goal_planner.configured_provider
        def provider(current):
            actual = original(current)
            method = actual.request_serialized
            def request(body, guard):
                revoke(value, session)
                return method(body, guard)
            actual.request_serialized = request
            return actual
        monkeypatch.setattr(goal_planner, "configured_provider", provider)
    assert worker.once()
    if when in {"before_confirm", "before_dispatch"}:
        body = confirmation(client, rid)
        if when == "before_confirm":
            revoke(value, session)
            assert client.post(f"/api/runs/{rid}/confirm-natural-plan", json=body).status_code == 403
        else:
            assert client.post(f"/api/runs/{rid}/confirm-natural-plan", json=body).status_code == 200
            original_dispatch = goal_planner.dispatch
            def dispatch(*args, **kwargs):
                revoke(value, session)
                return original_dispatch(*args, **kwargs)
            monkeypatch.setattr(goal_planner, "dispatch", dispatch)
            assert worker.once()
    assert len(sent) == (0 if when == "before_guard" else 1)
    assert not rows(store, operations)
    state = client.get(f"/api/runs/{rid}")
    assert state.status_code == 200, state.text
    assert state.json()["result"] is None
    assert rows(store, runs)[0]["lease_until"] == 0
    if when == "in_flight":
        attempt = rows(store, attempts)[0]
        assert attempt["usage"]["status"] == "known" and attempt["usage"]["tokens"]["total_tokens"] == 30
        assert attempt["response"] is not None and attempt["response_model"] == "Intern-S2"


def test_unexpected_provider_failure_retains_unknown_slot_no_retry(env):
    value = setup(env)
    store, settings, client, *_ = value
    session, _ = approved(value)
    rid = submit(value, session).json()["run_id"]
    sent = []
    def handler(request):
        sent.append(request.content)
        raise RuntimeError("SYNTHETIC_SECRET_MUST_NOT_LEAK")
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    assert not worker.once()
    view = client.get(f"/api/runs/{rid}")
    assert view.status_code == 200, view.text
    assert view.json()["status"] == "WAITING_RESOURCE"
    assert rows(store, runs)[0]["lease_until"] == 0
    assert len(sent) == len(rows(store, attempts)) == len(rows(store, reservations)) == 1
    assert not rows(store, operations)
    assert "SYNTHETIC_SECRET_MUST_NOT_LEAK" not in str(rows(store, attempts) + rows(store, events))
    second = submit(value, session, "read_preview", "second-after-unknown")
    assert second.status_code == 409, second.text


def test_scope_caller_cannot_change_caps_clock_model_or_false_consent(env):
    value = setup(env)
    result = draft(value)
    assert result.status_code == 201, result.text
    current = result.json()
    body = {"expected_version": 1, "expected_scope_fingerprint": current["scope_fingerprint"],
            "request_key": "approve", "consent": activation.CONSENT}
    before = rows(value[0], natural_activations), rows(value[0], events)
    for field, val in [("caps", {"requests": 3}), ("expires_at", 99999999999),
                       ("model", "unapproved"), ("clock", 1), ("consent", False)]:
        changed = copy.deepcopy(body)
        changed[field] = val
        assert value[2].post(f"/api/natural-activations/{current['id']}/approve", json=changed).status_code == 422
    assert (rows(value[0], natural_activations), rows(value[0], events)) == before


def test_expiry_is_immediate_without_timer_and_cannot_renew(env, monkeypatch):
    value = setup(env)
    store, settings, client, *_ = value
    clock = [activation.now()]
    monkeypatch.setattr(activation, "now", lambda: clock[0])
    session, approval_body = approved(value)
    accepted = submit(value, session)
    rid = accepted.json()["run_id"]
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value)))
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    body = confirmation(client, rid)
    clock[0] = session["approval"]["expires_at"]
    assert client.post(f"/api/runs/{rid}/confirm-natural-plan", json=body).status_code == 403
    info = client.get(f"/api/natural-activations/{session['id']}").json()
    assert not info["approved_not_expired"]
    retry = client.post(f"/api/natural-activations/{session['id']}/approve", json=approval_body)
    assert retry.status_code == 200 and retry.json()["approval"] == session["approval"]
    assert client.get(f"/api/runs/{rid}").status_code == 200
    closed = client.post(f"/api/natural-activations/{session['id']}/close-expired")
    assert closed.status_code == 200 and closed.json()["status"] == "EXPIRED"
    assert submit(value, session, "read_preview", "after-expiry").status_code == 403
    assert len(sent) == len(rows(store, attempts)) == 1 and not rows(store, operations)


def test_duplicate_hidden_sender_guard_permits_exactly_one_offline_send(env, monkeypatch):
    value = setup(env)
    store, settings, client, *_ = value
    session, _ = approved(value)
    rid = submit(value, session).json()["run_id"]
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value)))
    original = goal_planner.configured_provider
    def provider(current):
        actual = original(current)
        method = actual.request_serialized
        def twice(body, guard):
            method(body, guard)
            return method(body, guard)
        actual.request_serialized = twice
        return actual
    monkeypatch.setattr(goal_planner, "configured_provider", provider)
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    assert len(sent) == len(rows(store, attempts)) == 1 and not rows(store, operations)
    assert client.get(f"/api/runs/{rid}").json()["status"] == "WAITING_RESOURCE"
    assert not worker.once()
