"""Actual PostgreSQL lock ordering across expired recovery and active reservation."""

import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from test_protocol_http import NoProvider, body
from test_protocol_recovery import env as env
from test_protocol_reviews import MATERIAL

from sim2act import protocol_pool, protocol_recovery
from sim2act.db import attempts, protocol_request_slots, runs
from sim2act.tools import definitions
from sim2act.worker import Worker


class RecoveryContext:
    def __init__(self, fixture):
        self.fixture = fixture
        self.store, self.settings, self.client, self.owner, _, self.project, self.resource = fixture

    def __repr__(self):
        # Private database settings must not appear in failure argument repr.
        return "<isolated PostgreSQL recovery context>"


@pytest.fixture
def recovery_context(env):
    if env[0].sqlite:
        pytest.skip("Actual recovery lock ordering requires isolated PostgreSQL")
    return RecoveryContext(env)


def test_expired_scan_releases_pool_before_next_project_and_generic_claim(
    recovery_context, monkeypatch
):
    ctx = recovery_context
    store = ctx.store
    response = ctx.client.post(
        f"/api/projects/{ctx.project}/protocol/source", json=body(ctx.fixture)
    )
    assert response.status_code == 202
    expired_a = response.json()["run_id"]
    project_b = ctx.client.post("/api/projects", json={"name": "other lock project"}).json()["id"]
    resource_b = ctx.client.post(
        f"/api/projects/{project_b}/resources",
        json={"name": "lock-policy", "format": "txt", "content": MATERIAL.read_text()},
    ).json()["id"]
    fixture_b = (*ctx.fixture[:5], project_b, resource_b)
    response = ctx.client.post(f"/api/projects/{project_b}/protocol/source", json=body(fixture_b))
    assert response.status_code == 202
    expired_b = response.json()["run_id"]
    # Recovery sorts projects. Put the active reservation in its second project
    # regardless of random IDs, so the first recovery can actually hold the pool.
    active_fixture = fixture_b if project_b > ctx.project else ctx.fixture
    active_project = active_fixture[5]
    response = ctx.client.post(
        f"/api/projects/{active_project}/protocol/source",
        json=body(active_fixture, request_key="active-reservation"),
    )
    assert response.status_code == 202
    active_id = response.json()["run_id"]
    owned = [store.claim("worker-" + str(i), 60) for i in range(3)]
    active = next(value for value in owned if value["id"] == active_id)
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id.in_([expired_a, expired_b])).values(lease_until=0))

    worker = Worker(store, ctx.settings, NoProvider())
    reached = threading.Event()
    proceed = threading.Event()
    backend_pid = []
    trace = []
    gated = False
    original_reserve = protocol_pool.reserve_slot
    original_audit = protocol_recovery._pool_state

    def reserve(*args):
        connection = args[1]
        backend_pid.append(connection.execute(text("select pg_backend_pid()")).scalar_one())
        trace.append("reserve holds project B / active Run / quota")
        reached.set()
        assert proceed.wait(10), "Recovery did not reach pool lock"
        return original_reserve(*args)

    def audit(*args):
        nonlocal gated
        value = original_audit(*args)
        if gated:
            return value
        gated = True
        trace.append("expired A recovery holds pool")
        proceed.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with store.engine.connect() as observer:
                wait = observer.execute(
                    text("select wait_event_type from pg_stat_activity where pid=:pid"),
                    {"pid": backend_pid[0]},
                ).scalar()
            if wait == "Lock":
                trace.append("reservation waits on pool")
                break
            time.sleep(0.01)
        else:
            pytest.fail("Actual reservation did not contend on recovery's pool lock")
        return value

    monkeypatch.setattr(protocol_pool, "reserve_slot", reserve)
    monkeypatch.setattr(protocol_recovery, "_pool_state", audit)
    context = copy.deepcopy(active["context"])
    context["messages"] = [{"role": "user", "content": "offline lock probe"}]
    read_tools = [tool for tool in definitions() if tool["function"]["name"] == "resource.read"]

    def sender():
        try:
            worker.reserve(active_id, active["fence"], context, request_tools=read_tools)
            return "RESERVED"
        except DBAPIError as exc:
            return ("DATABASE_ERROR", getattr(exc.orig, "sqlstate", None))

    def scanner():
        try:
            assert store.claim("expired-scanner", 30) is None
            return "SCAN_FINISHED"
        except DBAPIError as exc:
            return ("DATABASE_ERROR", getattr(exc.orig, "sqlstate", None))

    with ThreadPoolExecutor(max_workers=2) as pool:
        sent = pool.submit(sender)
        assert reached.wait(10), "Reservation did not reach project/Run/quota locks"
        scanned = pool.submit(scanner)
        outcomes = [sent.result(timeout=20), scanned.result(timeout=20)]
    assert outcomes == ["RESERVED", "SCAN_FINISHED"], (trace, outcomes)
    assert trace == [
        "reserve holds project B / active Run / quota",
        "expired A recovery holds pool",
        "reservation waits on pool",
    ]
    with store.tx() as c:
        saved = {r["id"]: dict(r) for r in c.execute(select(runs)).mappings()}
        assert saved[expired_a]["status"] == saved[expired_b]["status"] == "PAUSED"
        assert saved[active_id]["status"] == "RUNNING"
        assert all(value["result"] is None for value in saved.values())
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 1
        assert c.execute(select(func.count()).select_from(protocol_request_slots)).scalar_one() == 1
        assert c.execute(select(attempts.c.status)).scalar_one() == "STARTED"
    # This test reserves exactly once; it never invokes any provider or retry.
