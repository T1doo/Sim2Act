"""Real SQLite contention and controlled scheduler failure handoff boundaries."""
import sqlite3
import threading
from types import SimpleNamespace

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from test_foundation import enqueue

from sim2act import db
from sim2act import text_workflows as flow
from sim2act.db import runs
from sim2act.errors import DomainError


def error(code):
    original = sqlite3.OperationalError("synthetic lock failure")
    original.sqlite_errorcode = code
    return OperationalError("BEGIN IMMEDIATE", {}, original)


@pytest.mark.parametrize("code,expected", [(5, True), (6, True), (517, True), (10, False)])
def test_driver_allowlist_is_specific(code, expected):
    assert flow._sqlite_heartbeat_contention(SimpleNamespace(sqlite=True), error(code)) is expected
    assert not flow._sqlite_heartbeat_contention(SimpleNamespace(sqlite=False), error(code))
    assert not flow._sqlite_heartbeat_contention(SimpleNamespace(sqlite=True), RuntimeError("unknown"))
    foreign = OperationalError("query", {}, SimpleNamespace(sqlite_errorcode=5))
    assert not flow._sqlite_heartbeat_contention(SimpleNamespace(sqlite=True), foreign)


def setup(env, monkeypatch):
    store, settings = env[:2]
    rid = enqueue(env, "heartbeat-controller")
    run = store.claim("original-worker", 30)
    assert run["id"] == rid
    done = threading.Event()
    observed = threading.Event()

    class ScheduledEvent(threading.Event):
        def wait(self, timeout=None):
            # Shorten only the test scheduler; the real lease remains 30 seconds.
            return super().wait(0.001 if timeout == 10 else timeout)

    class ObservedThread(threading.Thread):
        def run(self):
            try:
                return super().run()
            finally:
                done.set()

    monkeypatch.setattr(flow, "threading", SimpleNamespace(
        Event=ScheduledEvent, Thread=ObservedThread, Lock=threading.Lock))
    worker = SimpleNamespace(store=store, s=settings, id="original-worker", stop=threading.Event())
    state = dict(lock=threading.Lock(), lease_until=run["lease_until"],
        deadline=run["created_at"] + settings.run_seconds)
    return worker, run, state, done, observed


def test_real_sqlite_busy_recovers_without_new_claim(env, monkeypatch):
    worker, run, state, done, observed = setup(env, monkeypatch)
    ready, release = threading.Event(), threading.Event()
    original = worker.store.heartbeat
    calls, codes = [], []

    def hold():
        with worker.store.tx():
            ready.set()
            assert release.wait(5)

    holder = threading.Thread(target=hold)
    holder.start()
    assert ready.wait(2)

    def monitored(*args, **kwargs):
        calls.append(1)
        kwargs["_wait_seconds"] = 0.01  # Only lower the synthetic driver wait.
        try:
            result = original(*args, **kwargs)
        except OperationalError as exc:
            codes.append(exc.orig.sqlite_errorcode)
            release.set()
            holder.join(timeout=2)
            raise
        observed.set()
        return result

    monkeypatch.setattr(worker.store, "heartbeat", monitored)
    def advance(*_):
        assert observed.wait(3)
        return False
    try:
        flow.process_job(worker, run, advance, _heartbeat_state=state)
    finally:
        release.set()
        holder.join(timeout=2)
    assert codes == [sqlite3.SQLITE_BUSY] and len(calls) == 2 and done.is_set()
    with worker.store.tx() as c:
        row = c.execute(select(runs.c.fence, runs.c.worker_id, runs.c.lease_until)
            .where(runs.c.id == run["id"])).mappings().one()
    assert row["fence"] == run["fence"] and row["worker_id"] == worker.id
    assert row["lease_until"] == state["lease_until"] > run["lease_until"]


@pytest.mark.parametrize("fault", ["unknown", "other-sqlite", "revoked", "unverified", "expired", "exhausted"])
def test_fatal_failure_is_seen_before_next_step(env, monkeypatch, fault):
    worker, run, state, done, observed = setup(env, monkeypatch)
    calls, advances = [], []
    exc = (DomainError("GRANT_REVOKED") if fault == "revoked" else RuntimeError("synthetic unknown")
        if fault == "unknown" else error(10 if fault == "other-sqlite" else 5))
    if fault == "unverified":
        state["deadline"] = None
    def failing(*_, **__):
        calls.append(1)
        if fault == "expired":
            state["lease_until"] = 0
            # The captured retry cutoff must also have elapsed.
            monkeypatch.setattr(flow, "time", SimpleNamespace(time=lambda: run["lease_until"] + 1))
        raise exc
    monkeypatch.setattr(worker.store, "heartbeat", failing)
    def advance(*_):
        advances.append(1)
        assert done.wait(3)
        return True
    if fault == "revoked":
        flow.process_job(worker, run, advance, _heartbeat_state=state)
        with worker.store.tx() as c:
            assert c.execute(select(runs.c.status).where(runs.c.id == run["id"])).scalar_one() == "WAITING_RESOURCE"
    else:
        with pytest.raises(type(exc)):
            flow.process_job(worker, run, advance, _heartbeat_state=state)
    assert len(advances) == 1 and len(calls) == (3 if fault == "exhausted" else 1)


def test_terminal_return_is_not_overwritten_by_late_background_error(env, monkeypatch):
    worker, run, state, done, observed = setup(env, monkeypatch)
    def failing(*_, **__):
        raise DomainError("VERSION_CONFLICT")
    monkeypatch.setattr(worker.store, "heartbeat", failing)
    def committed(*_):
        assert done.wait(3)
        return False
    # A fatal error after a terminal transaction must not call fail_job.
    monkeypatch.setattr("sim2act.app_jobs.fail_job", lambda *_: pytest.fail("terminal overwritten"))
    flow.process_job(worker, run, committed, _heartbeat_state=state)


def test_deadline_after_guard_rolls_back_all_heartbeat_writes(env, monkeypatch):
    store = env[0]
    rid = enqueue(env, "heartbeat-deadline")
    run = store.claim("original-worker", 30)
    clock = [run["lease_until"] - 5]
    deadline = clock[0] + 1
    monkeypatch.setattr(db, "time", SimpleNamespace(time=lambda: clock[0]))
    original = store.guard
    def delayed(*args):
        current = original(*args)
        clock[0] = deadline
        return current
    monkeypatch.setattr(store, "guard", delayed)
    with pytest.raises(DomainError, match="Original heartbeat interval"):
        store.heartbeat("original-worker", rid, run["fence"], _deadline=deadline)
    with store.tx() as c:
        assert c.execute(select(runs.c.lease_until).where(runs.c.id == rid)).scalar_one() == run["lease_until"]
        assert c.execute(select(db.heartbeats.c.id).where(db.heartbeats.c.id == "original-worker")).first() is None


def test_capped_transaction_wait_never_increases_configured_timeout(env):
    store = env[0]
    with store.engine.connect() as c:
        raw = c.connection.driver_connection
        original = raw.execute("PRAGMA busy_timeout").fetchone()[0]
        raw.execute("PRAGMA busy_timeout = 7")
    try:
        with store.tx(wait_seconds=1, _cap_wait=True) as c:
            assert c.connection.driver_connection.execute("PRAGMA busy_timeout").fetchone()[0] == 7
        with store.engine.connect() as c:
            assert c.connection.driver_connection.execute("PRAGMA busy_timeout").fetchone()[0] == 7
    finally:
        with store.engine.connect() as c:
            c.connection.driver_connection.execute(f"PRAGMA busy_timeout = {original}")


def test_background_renewal_rejects_cancel_intent(env):
    store = env[0]
    rid = enqueue(env, "heartbeat-cancel")
    run = store.claim("original-worker", 30)
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True, status="CANCEL_REQUESTED"))
    with pytest.raises(DomainError, match="Heartbeat Run stopped"):
        store.heartbeat("original-worker", rid, run["fence"], _running_only=True)
    with store.tx() as c:
        assert c.execute(select(runs.c.lease_until).where(runs.c.id == rid)).scalar_one() == run["lease_until"]
