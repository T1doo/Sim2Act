"""Actual thirty-second ownership expiry, offline Worker and public cancellation."""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx
import pytest
from sqlalchemy import select, tuple_, update
from test_natural_spec_apps import transport
from test_project_check_cancel import accepted, original_objects, status
from test_spec_app_operations import snapshot

from sim2act import natural_specs as codec
from sim2act import project_natural_revalidation as project
from sim2act.app_jobs import lock_live
from sim2act.db import (
    Store,
    attempts,
    delivery_graph_requests,
    events,
    grants,
    internal_app_runs,
    internal_run_bindings,
    operations,
    runs,
)
from sim2act.errors import DomainError
from sim2act.project_check_recovery import recover_cancelled_checks
from sim2act.worker import Worker


def expired_return(env):
    data, _, _, _, _, _, started, path, command = accepted(env)
    sent, original = [], []

    def delayed(raw, payload):
        before = status(data[2], path)
        with data[0].tx() as c:
            original.append(dict(c.execute(select(runs).where(
                runs.c.id == started["run_id"])).mappings().one()))
        assert data[1].lease_seconds == 30
        pause = data[2].post(command, json={"command": "pause", "version": before["run_version"]})
        assert pause.status_code == 200, pause.text
        current = status(data[2], path)
        cancel = data[2].post(command, json={"command": "cancel", "version": current["run_version"]})
        assert cancel.status_code == 200 and cancel.json()["status"] == "RECONCILING"
        assert not recover_cancelled_checks(data[0])  # Still unknown, and active owner.
        # Real elapsed ownership interval, never rewrite clocks/leases or budgets.
        while time.time() <= original[0]["lease_until"]:
            time.sleep(min(1, max(.01, original[0]["lease_until"] - time.time() + .01)))

    worker = Worker(data[0], data[1], goal_planner_transport=transport(sent, mutate=delayed))
    assert worker.once()
    value = status(data[2], path)
    assert value["run_status"] == "RECONCILING" and value["cancel_intent"]
    assert value["effect_known"] and not value["unresolved_operations"]
    assert value["model_usage"][0]["status"] == "REJECTED_KNOWN"
    return data, started, path, command, sent, original[0], value


def test_expired_known_cancel_recovery_failclosed_matrix_rollback_revocation_and_two_stores(
    env, monkeypatch, tmp_path
):
    data, started, path, command, sent, old, before = expired_return(env)
    store = data[0]
    original = original_objects(store, started["check_instance_id"])
    # Every damaged fixture is restored exactly before the next independent guard.
    faults = [
        (runs, runs.c.id, old["id"], "cancel_intent", False),
        (runs, runs.c.id, old["id"], "lease_until", time.time() + 30),
    ]
    with store.tx() as c:
        attempt = dict(c.execute(select(attempts).where(attempts.c.run_id == old["id"])).mappings().one())
        op = dict(c.execute(select(operations).where(operations.c.id == attempt["parameters"]["natural_spec"]["operation_id"])).mappings().one())
        binding = dict(c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == old["id"])).mappings().one())
        seal = dict(c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind == project.JOB + "_seal",
            delivery_graph_requests.c.app_id == old["id"])).mappings().one())
    foreign = copy.deepcopy(binding["snapshot"])
    foreign["project_check"]["plan_key"] = "another-project-key"
    removed = copy.deepcopy(binding["snapshot"])
    removed.pop("project_check")
    faults += [
        (internal_app_runs, internal_app_runs.c.id, binding["app_run_id"], "status", "RUNNING"),
        (attempts, attempts.c.id, attempt["id"], "usage", {"status": "unknown"}),
        (attempts, attempts.c.id, attempt["id"], "reserved_tokens", attempt["reserved_tokens"] + 1),
        (operations, operations.c.id, op["id"], "status", "OUTCOME_UNKNOWN"),
        (internal_run_bindings, internal_run_bindings.c.run_id, old["id"], "snapshot", foreign),
        (internal_run_bindings, internal_run_bindings.c.run_id, old["id"], "snapshot", removed),
        (delivery_graph_requests, tuple_(delivery_graph_requests.c.app_id, delivery_graph_requests.c.principal_id,
            delivery_graph_requests.c.kind, delivery_graph_requests.c.request_key),
            (seal["app_id"], seal["principal_id"], seal["kind"], seal["request_key"]), "fingerprint", "invalid"),
    ]
    for table, identity, key, field, wrong in faults:
        with store.tx() as c:
            saved = c.execute(select(table.c[field]).where(identity == key)).scalar_one()
            c.execute(update(table).where(identity == key).values({field: wrong}))
        damaged = snapshot(store)
        assert not recover_cancelled_checks(store), (table.name, field)
        assert snapshot(store) == damaged
        with store.tx() as c:
            c.execute(update(table).where(identity == key).values({field: saved}))
    own_event = store.event

    def failed_receipt(c, rid, kind, value):
        own_event(c, rid, kind, value)
        if kind == "PROJECT_CHECK_CANCEL_RECOVERED":
            raise RuntimeError("synthetic receipt transaction failure")

    monkeypatch.setattr(store, "event", failed_receipt)
    saved = snapshot(store)
    with pytest.raises(RuntimeError, match="synthetic receipt"):
        recover_cancelled_checks(store)
    assert snapshot(store) == saved
    monkeypatch.setattr(store, "event", own_event)
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
    assert data[2].get(path + "/run-status").status_code == 403
    pre = snapshot(store)
    peer = Store(data[1].database_url, test_only=True)
    barrier = Barrier(2)

    def recover(other):
        barrier.wait(timeout=30)
        return Worker(other, data[1], goal_planner_transport=transport(sent)).once()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, b = pool.submit(recover, store), pool.submit(recover, peer)
            assert sorted([a.result(timeout=60), b.result(timeout=60)]) == [False, True]
    finally:
        peer.engine.dispose()
    final = status(data[2], path, True)
    assert final["run_status"] == "CANCELLED" and final["cancel_intent"]
    assert final["run_version"] == before["run_version"] + 1
    after = snapshot(store)
    assert {k: v for k, v in pre.items() if k not in {"runs", "internal_app_runs", "events", "heartbeats"}} == {
        k: v for k, v in after.items() if k not in {"runs", "internal_app_runs", "events", "heartbeats"}}
    assert original_objects(store, started["check_instance_id"]) == original
    assert len(sent) == 1
    with store.tx() as c:
        recovered = dict(c.execute(select(runs).where(runs.c.id == old["id"])).mappings().one())
        assert recovered["fence"] == old["fence"] + 1
        receipts = c.execute(select(events.c.data).where(events.c.run_id == old["id"],
            events.c.kind == "PROJECT_CHECK_CANCEL_RECOVERED")).scalars().all()
        assert len(receipts) == 1 and receipts[0]["effect_known"]
        assert not c.execute(select(operations).where(operations.c.run_id == old["id"],
            operations.c.tool_ref == codec.SAVE)).first()
        with pytest.raises(DomainError):
            lock_live(store, c, old)
    assert not recover_cancelled_checks(store)
    assert data[2].post(command, json={"command": "cancel", "version": before["run_version"]}).status_code == 409
    (tmp_path / "known-expired-recovery.json").write_text(json.dumps(dict(before=before, after=final,
        receipt=receipts[0], real_lease_seconds=30, requests=len(sent)), indent=2))


def test_actual_unknown_cancel_is_never_recovered_or_resent(env, tmp_path):
    data, _, _, _, _, _, started, path, command = accepted(env)
    sent = []

    def unknown(request):
        sent.append(request.content)
        raise httpx.ReadTimeout("synthetic unknown late result")

    worker = Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(unknown))
    assert worker.once()
    current = status(data[2], path)
    reply = data[2].post(command, json={"command": "cancel", "version": current["run_version"]})
    assert reply.status_code == 200
    before = snapshot(data[0])
    assert not recover_cancelled_checks(data[0])
    assert snapshot(data[0]) == before
    assert not worker.once() and len(sent) == 1
    final = status(data[2], path)
    assert final["run_status"] == "RECONCILING" and final["cancel_intent"] and not final["effect_known"]
    assert final["model_usage"] == current["model_usage"]
    (tmp_path / "unknown-not-recovered.json").write_text(json.dumps(final, indent=2))


def test_project_queued_pause_resume_uses_original_limits_and_rejects_stale_revoked_cancelled(env):
    data, _, _, _, _, _, started, path, command = accepted(env)
    first = status(data[2], path)
    assert first["run_status"] == "QUEUED"
    assert data[2].post(command, json={"command": "pause", "version": first["run_version"]}).status_code == 200
    paused = status(data[2], path)
    assert paused["run_status"] == "PAUSED"
    before = snapshot(data[0])
    assert data[2].post(command, json={"command": "resume", "version": first["run_version"]}).status_code == 409
    assert snapshot(data[0]) == before
    assert data[2].post(command, json={"command": "resume", "version": paused["run_version"]}).status_code == 200
    resumed = status(data[2], path)
    assert resumed["run_status"] == "QUEUED" and resumed["run_id"] == started["run_id"]
    assert resumed["executed_model_requests"] == 0
    assert data[2].post(command, json={"command": "pause", "version": resumed["run_version"]}).status_code == 200
    paused = status(data[2], path)
    with data[0].tx() as c:
        rows = c.execute(select(grants).where(grants.c.resource_id == data[5])).mappings().all()
        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
    before = snapshot(data[0])
    assert data[2].post(command, json={"command": "resume", "version": paused["run_version"]}).status_code == 403
    assert snapshot(data[0]) == before
    for row in rows:
        with data[0].tx() as c:
            c.execute(update(grants).where(grants.c.id == row["id"]).values(revoked=row["revoked"]))
    assert data[2].post(command, json={"command": "cancel", "version": paused["run_version"]}).status_code == 200
    cancelled = status(data[2], path)
    before = snapshot(data[0])
    assert data[2].post(command, json={"command": "resume", "version": cancelled["run_version"]}).status_code == 409
    assert snapshot(data[0]) == before and cancelled["run_status"] == "CANCELLED"
