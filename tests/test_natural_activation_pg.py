"""Real PG overlapping transactions; no SQLite inference or provider networking."""

import contextvars
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from test_natural_activation_flow import approved, confirmation, setup, submit, wire
from test_natural_goal_planning import authority, response, rows

from sim2act import natural_activations as activation
from sim2act.db import Store, attempts, events, natural_activations, operations, reservations, runs
from sim2act.worker import Worker


def require_pg(env):
    if env[0].sqlite:
        pytest.skip("Distinct PostgreSQL connections required; SQLite is not evidence")


def evidence(value, name, data):
    (value[1].data_dir / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")


def waiting(env):
    value = setup(env)
    session, _ = approved(value)
    rid = submit(value, session).json()["run_id"]
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value)))
    worker = Worker(value[0], value[1], goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    body = confirmation(value[2], rid)
    assert not rows(value[0], operations)
    return value, session, rid, sent, worker, body


def test_pg_two_workers_same_kind_charge_once(env, monkeypatch):
    require_pg(env)
    value = setup(env)
    store, settings, client, *_ = value
    session, _ = approved(value)
    accepted = [submit(value, session, key="race-" + str(i)).json()["run_id"] for i in range(2)]
    before = authority(store)
    sent = []
    def handler(request):
        sent.append(request.content)
        return httpx.Response(200, json=response(wire(value)))
    workers = [Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
               for _ in range(2)]
    barrier = threading.Barrier(2)
    backend_ids = []
    original = store.claim
    def claim(worker_id, lease):
        # Both real claim transactions are live before either takes the Run lock.
        with store.engine.connect() as c:
            backend_ids.append(c.execute(text("SELECT pg_backend_pid()")).scalar_one())
            barrier.wait(10)
            return original(worker_id, lease)
    monkeypatch.setattr(store, "claim", claim)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(pool.map(lambda w: w.once(), workers))
    monkeypatch.setattr(store, "claim", original)
    assert len(set(backend_ids)) == 2
    assert len(sent) == len(rows(store, attempts)) == len(rows(store, reservations)) == 1
    assert not rows(store, operations)
    info = client.get(f"/api/natural-activations/{session['id']}").json()
    assert info["charged_requests"] == 1 and 0 < info["reserved_tokens"] <= 11000
    states = [client.get(f"/api/runs/{rid}").json() for rid in accepted]
    assert sorted(s["status"] for s in states) == ["FAILED", "WAITING_APPROVAL"]
    assert all(r["lease_until"] == 0 for r in rows(store, runs))
    assert authority(store) == before
    evidence(value, "pg-two-workers", {"backend_ids": backend_ids, "wires": len(sent),
             "attempts": 1, "reservations": 1, "operations": 0,
             "charged_requests": 1, "statuses": [s["status"] for s in states]})


@pytest.mark.parametrize("control", ["cancel", "revoke", "expire", "confirm-again"])
def test_pg_confirmation_control_transactions_are_linearized(env, monkeypatch, control):
    require_pg(env)
    value, session, rid, sent, worker, body = waiting(env)
    store, _, client, *_ = value
    before = authority(store)
    clock = [activation.now()]
    monkeypatch.setattr(activation, "now", lambda: clock[0])
    actor = contextvars.ContextVar("activation_pg_actor", default=None)
    barrier = threading.Barrier(2)
    backend_ids = {}
    original = store.lock_project
    def project_lock(c, user, pid):
        name = actor.get()
        assert name in {"confirm", "control"}
        backend_ids[name] = c.execute(text("SELECT pg_backend_pid()")).scalar_one()
        barrier.wait(10)
        result = original(c, user, pid)
        if name == "control" and control == "expire":
            clock[0] = session["approval"]["expires_at"]
        return result
    monkeypatch.setattr(store, "lock_project", project_lock)
    def invoke(name):
        token = actor.set(name)
        try:
            if name == "confirm" or control == "confirm-again":
                return client.post(f"/api/runs/{rid}/confirm-natural-plan", json=body)
            if control == "cancel":
                return client.post(f"/api/runs/{rid}/commands",
                                   json={"command": "cancel", "version": body["expected_version"]})
            if control == "revoke":
                return client.post(f"/api/natural-activations/{session['id']}/revoke", json={
                    "expected_version": session["version"],
                    "expected_scope_fingerprint": session["scope_fingerprint"],
                    "request_key": "race-revoke"})
            return client.post(f"/api/natural-activations/{session['id']}/close-expired", json={})
        finally:
            actor.reset(token)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(invoke, ("confirm", "control")))
    monkeypatch.setattr(store, "lock_project", original)
    assert len(set(backend_ids.values())) == 2
    confirmed = [r for r in rows(store, events) if r["kind"] == "NL_PLAN_CONFIRMED"]
    statuses = [r.status_code for r in replies]
    if control == "confirm-again":
        assert statuses == [200, 200] and replies[0].json() == replies[1].json()
        assert len(confirmed) == 1
        assert worker.once()
        assert len(sent) == 1 and len(rows(store, operations)) == 1
        assert client.get(f"/api/runs/{rid}").json()["result"]["receipts"][0]["data"]["sum"] == "19"
    else:
        if control == "cancel":
            assert sorted(statuses) == [200, 409]
            # A stale cancellation is rejected; explicit fresh cancel closes the winner.
            view = client.get(f"/api/runs/{rid}").json()
            if view["status"] == "QUEUED":
                cancelled = client.post(f"/api/runs/{rid}/commands",
                                        json={"command": "cancel", "version": view["version"]})
                assert cancelled.status_code == 200, cancelled.text
            assert client.get(f"/api/runs/{rid}").json()["status"] == "CANCELLED"
        else:
            assert statuses[1] == 200 and statuses[0] in {200, 403}
            assert client.get(f"/api/natural-activations/{session['id']}").json()["status"] == (
                "REVOKED" if control == "revoke" else "EXPIRED")
        assert len(confirmed) == (1 if statuses[0] == 200 else 0)
        worker.once()
        assert not rows(store, operations) and len(sent) == 1
        assert client.get(f"/api/runs/{rid}").json()["result"] is None
    assert len(rows(store, attempts)) == len(rows(store, reservations)) == 1
    assert all(r["lease_until"] == 0 for r in rows(store, runs))
    assert authority(store) == before
    evidence(value, "pg-control-race", {"control": control, "backend_ids": backend_ids,
             "http_statuses": statuses, "confirmation_events": len(confirmed), "wires": len(sent),
             "attempts": 1, "reservations": 1, "operations": len(rows(store, operations)),
             "leases_released": True, "authority_unchanged": True})


def test_pg_actual_worker_reservation_failure_is_not_half_committed(env, monkeypatch):
    require_pg(env)
    value = setup(env)
    store, settings, client, *_ = value
    session, _ = approved(value)
    rid = submit(value, session).json()["run_id"]
    original = activation.reserve_slot
    def fail_after_charge(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("controlled PG post-charge rollback")
    monkeypatch.setattr(activation, "reserve_slot", fail_after_charge)
    run = store.claim("rollback-worker", 30)
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(
        lambda request: pytest.fail("Rollback must precede provider call")))
    with pytest.raises(RuntimeError, match="controlled PG"):
        worker.process(run)
    assert not rows(store, attempts) and not rows(store, reservations) and not rows(store, operations)
    assert rows(store, natural_activations)[0]["ledger"] == []
    assert rows(store, runs)[0]["context"]["requests"] == 0
    assert not any(e["kind"] == "NL_ACTIVATION_SLOT_RESERVED" for e in rows(store, events))
    # Original outer loop does not catch unexpected pre-provider bugs: explicit owned cleanup.
    worker.finish(rid, run["fence"], "FAILED", error={"code": "TEST_ABORTED"}, verify_goal_source=True)
    assert rows(store, runs)[0]["lease_until"] == 0
    evidence(value, "pg-rollback", {"attempts": 0, "reservations": 0, "operations": 0,
             "ledger": [], "context_requests": 0, "lease_released": True})


def test_pg_application_role_activation_crud_without_ddl(env, runtime_role):
    require_pg(env)
    value = setup(env)
    owner_store, settings, _, user, _, pid, _, cards = value
    app_store = Store(runtime_role, test_only=True)
    app_settings = replace(settings, database_url=runtime_role)
    queries = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)
    event.listen(app_store.engine, "before_cursor_execute", capture)
    try:
        with app_store.engine.connect() as c:
            role = c.execute(text("SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user")).one()
            assert tuple(role) == (False, False, False)
        with pytest.raises(DBAPIError):
            with app_store.tx() as c:
                c.execute(text("CREATE TABLE must_not_create(value int)"))
        queries.clear()
        created = activation.create(app_store, user, pid, {
            "goal_bindings": [{"kind": kind, "card_id": card["id"],
                               "expected_version": card["version"],
                               "expected_fingerprint": card["fingerprint"]}
                              for kind, card in cards.items()], "request_key": "runtime-crud"}, app_settings)
        approved_row = activation.approve(app_store, user, created["id"], {
            "expected_version": created["version"], "expected_scope_fingerprint": created["scope_fingerprint"],
            "request_key": "runtime-approval", "consent": activation.CONSENT}, app_settings)
        activation.revoke(app_store, user, created["id"], {
            "expected_version": approved_row["version"], "expected_scope_fingerprint": created["scope_fingerprint"],
            "request_key": "runtime-revoke"}, app_settings)
        assert activation.inspect(app_store, user, created["id"])["status"] == "REVOKED"
        assert not any(q.lstrip().upper().startswith(("CREATE", "ALTER", "DROP")) for q in queries)
        assert len(rows(owner_store, natural_activations)) == 1
        evidence(value, "pg-runtime-role", {"superuser": False, "createdb": False, "createrole": False,
                 "ddl_denied": True, "crud_status": "REVOKED", "crud_ddl_statements": 0})
    finally:
        app_store.engine.dispose()
