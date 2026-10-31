"""Real SQLite contention and controlled scheduler failure handoff boundaries."""
import sqlite3
import threading
from types import SimpleNamespace

import pytest
from sqlalchemy import insert, select, update
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


@pytest.mark.parametrize("publication", ["known", "late"])
def test_real_sqlite_busy_recovers_without_new_claim(env, monkeypatch, publication):
    worker, run, state, done, observed = setup(env, monkeypatch)
    if publication == "late":
        state["deadline"] = None
    ready, release = threading.Event(), threading.Event()
    original = worker.store.heartbeat
    calls, codes, renewals = [], [], []

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
            with state["lock"]:
                state["deadline"] = run["created_at"] + worker.s.run_seconds
            release.set()
            holder.join(timeout=2)
            raise
        renewals.append(result)
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
    # The accelerated scheduler may commit another heartbeat before the main
    # thread observes success. Every call beyond the one BUSY must have committed.
    assert codes == [sqlite3.SQLITE_BUSY] and renewals and done.is_set()
    assert len(calls) == 1 + len(renewals)
    with worker.store.tx() as c:
        row = c.execute(select(runs.c.fence, runs.c.worker_id, runs.c.lease_until)
            .where(runs.c.id == run["id"])).mappings().one()
    assert row["fence"] == run["fence"] and row["worker_id"] == worker.id
    assert row["lease_until"] == state["lease_until"] == max(renewals) > run["lease_until"]


@pytest.mark.parametrize("fault", ["unknown", "other-sqlite", "revoked", "unverified", "expired", "exhausted", "unverified-progress", "deadline-progress", "foreign-progress", "expired-progress"])
def test_fatal_failure_is_seen_before_next_step(env, monkeypatch, fault):
    worker, run, state, done, observed = setup(env, monkeypatch)
    calls, advances = [], []
    exc = (DomainError("GRANT_REVOKED") if fault == "revoked" else RuntimeError("synthetic unknown")
        if fault in {"unknown", "foreign-progress"} else error(10 if fault == "other-sqlite" else 5))
    if fault == "expired-progress":
        renewed = worker.store.heartbeat(worker.id, run["id"], run["fence"], 30)
        state["lease_until"] = renewed
    if fault in {"unverified", "unverified-progress"}:
        state["deadline"] = None
    def failing(*_, **__):
        calls.append(1)
        if fault in {"unverified-progress", "deadline-progress", "foreign-progress"}:
            with state["lock"]:
                state["lease_until"] = run["lease_until"] + 1
                if fault == "deadline-progress":
                    state["deadline"] = 0
        if fault in {"expired", "expired-progress"}:
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
    elif fault in {"unknown", "other-sqlite", "foreign-progress"}:
        with pytest.raises(type(exc)):
            flow.process_job(worker, run, advance, _heartbeat_state=state)
    else:
        flow.process_job(worker, run, advance, _heartbeat_state=state)
        with worker.store.tx() as c:
            row = c.execute(select(runs.c.status, runs.c.error).where(
                runs.c.id == run["id"])).mappings().one()
        assert row["status"] == "WAITING_RESOURCE"
        assert row["error"]["code"] == "RESOURCE_UNAVAILABLE"
    assert len(advances) == 1 and len(calls) == (3 if fault == "exhausted" else 1)


@pytest.mark.parametrize("progress", ["during-batch", "before-batch"])
def test_exhausted_batch_defers_only_with_committed_owned_progress(env, monkeypatch, caplog, progress):
    worker, run, state, done, observed = setup(env, monkeypatch)
    original = worker.store.heartbeat
    calls = []
    caplog.set_level("INFO", logger=flow.__name__)
    if progress == "before-batch":
        state["lease_until"] = original(worker.id, run["id"], run["fence"], 30)
    def contended(*args, **kwargs):
        calls.append(1)
        if len(calls) <= 3:
            # Schedule a separately committed same-owner synchronous renewal
            # between synthetic background driver failures.
            if progress == "during-batch":
                renewed = original(worker.id, run["id"], run["fence"], 30)
                with state["lock"]:
                    state["lease_until"] = max(state["lease_until"], renewed)
            raise error(5)
        renewed = original(*args, **kwargs)  # Next batch performs real fresh gates.
        observed.set()
        return renewed
    monkeypatch.setattr(worker.store, "heartbeat", contended)
    def completed(*_):
        assert observed.wait(3)
        return False
    flow.process_job(worker, run, completed, _heartbeat_state=state)
    deferred = [r for r in caplog.records if r.msg == "heartbeat_contention_deferred"]
    assert len(calls) == 4 and len(deferred) == 1 and deferred[0].attempts == 3
    assert deferred[0].fence == run["fence"] and done.is_set()


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


def test_model_sync_renewal_publishes_committed_lease(env):
    from sim2act.natural_spec_runtime import renew

    store, settings = env[:2]
    rid = enqueue(env, "model-heartbeat-publication")
    run = store.claim("original-worker", 30)
    # Match process_job's actual initial publication state. An absent deadline
    # or zero (already expired) lease is not a live owner awaiting renewal.
    state = dict(lock=threading.Lock(), lease_until=run['lease_until'], deadline=None)
    worker = SimpleNamespace(store=store, s=settings, id="original-worker", stop=threading.Event())
    renew(worker, run, run["created_at"] + settings.run_seconds, _heartbeat_state=state)
    with store.tx() as c:
        current = c.execute(select(runs.c.lease_until, runs.c.fence).where(runs.c.id == rid)).mappings().one()
    assert state["lease_until"] == current["lease_until"]
    assert current["fence"] == run["fence"]
    # A stopped/expired model guard never publishes a fabricated renewal.
    previous = state["lease_until"]
    with pytest.raises(DomainError):
        renew(worker, run, 0, _heartbeat_state=state)
    assert state["lease_until"] == previous


@pytest.mark.parametrize("boundary,expected", [
    ("owned", "WAITING_RESOURCE"), ("unknown", "WAITING_RESOURCE"),
    ("unknown-cancel", "RECONCILING"),
    ("pause", "PAUSED"), ("cancel", "CANCELLED"),
    ("expired", "RUNNING"), ("new-owner", "RUNNING"),
    ("settlement-busy", "RUNNING"),
])
def test_exhausted_background_contention_keeps_worker_and_owned_boundaries(
    env, monkeypatch, boundary, expected,
):
    from sim2act.worker import Worker

    worker, run, state, done, _ = setup(env, monkeypatch)
    store = worker.store
    with store.tx() as c:
        changes = {}
        if boundary == "expired":
            changes["lease_until"] = 0
        elif boundary == "new-owner":
            changes.update(worker_id="replacement-worker", fence=run["fence"] + 2)
        elif boundary == "pause":
            changes["status"] = "PAUSE_REQUESTED"
        elif boundary in {"cancel", "unknown-cancel"}:
            changes.update(status="CANCEL_REQUESTED", cancel_intent=True)
        if changes:
            c.execute(update(runs).where(runs.c.id == run["id"]).values(**changes))
        if boundary in {"unknown", "unknown-cancel"}:
            c.execute(insert(db.operations).values(id="synthetic-unknown", run_id=run["id"],
                call_id="pending", status="OUTCOME_UNKNOWN", receipt={"known": False}))
        before = dict(c.execute(select(runs).where(runs.c.id == run["id"])).mappings().one())
    calls, steps = [], []
    original_heartbeat = store.heartbeat

    def contended(worker_id, run_id=None, *args, **kwargs):
        if run_id == run["id"]:
            calls.append(1)
            raise error(sqlite3.SQLITE_BUSY)
        return original_heartbeat(worker_id, run_id, *args, **kwargs)

    monkeypatch.setattr(store, "heartbeat", contended)
    if boundary == "settlement-busy":
        monkeypatch.setattr("sim2act.app_jobs.fail_job", lambda *_: (_ for _ in ()).throw(error(6)))

    def advance(*_):
        steps.append(1)
        assert done.wait(3)
        return True

    actual = Worker(store, worker.s)
    actual.id = worker.id
    monkeypatch.setattr(actual, "process", lambda claimed: flow.process_job(
        actual, claimed, advance, _heartbeat_state=state))
    # Exercise the real once() error boundary, using the already claimed original Run.
    original_claim = store.claim
    monkeypatch.setattr(store, "claim", lambda *_: run)
    assert actual.once() is True
    assert len(calls) == 3 and len(steps) == 1
    with store.tx() as c:
        current = dict(c.execute(select(runs).where(runs.c.id == run["id"])).mappings().one())
        assert current["status"] == expected
        for field in ("fence", "worker_id", "request_key", "context"):
            assert current[field] == before[field]
        assert current["lease_until"] == (before["lease_until"] if expected == "RUNNING" else 0)
        if boundary in {"unknown", "unknown-cancel"}:
            assert c.execute(select(db.operations.c.status).where(
                db.operations.c.id == "synthetic-unknown")).scalar_one() == "OUTCOME_UNKNOWN"
        if expected != "RUNNING":
            assert current["error"]["code"] == "RESOURCE_UNAVAILABLE"
    # The same Worker survives and can claim a distinct ordinary queued Run.
    monkeypatch.setattr(store, "claim", original_claim)
    next_id = enqueue(env, "after-heartbeat-contention")
    # Old expired/replacement claims are deliberately not replayed here.
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == run["id"]).values(lease_until=10**12))
    claimed = []
    monkeypatch.setattr(actual, "process", lambda new_run: claimed.append(new_run["id"]))
    assert actual.once() is True and claimed == [next_id]


@pytest.mark.parametrize("fault", [RuntimeError("unexpected settlement"), error(10)])
def test_unexpected_settlement_failure_still_propagates(env, monkeypatch, fault):
    worker, run, state, done, _ = setup(env, monkeypatch)
    monkeypatch.setattr(worker.store, "heartbeat", lambda *_args, **_kwargs:
        (_ for _ in ()).throw(error(5)))
    monkeypatch.setattr("sim2act.app_jobs.fail_job", lambda *_:
        (_ for _ in ()).throw(fault))
    def advance(*_):
        assert done.wait(3)
        return True
    with pytest.raises(type(fault)) as seen:
        flow.process_job(worker, run, advance, _heartbeat_state=state)
    assert seen.value is fault
