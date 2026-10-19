"""Ordinary Worker: actual SQLite lock, committed renewal and original ownership bounds."""

import json
import sqlite3
import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError
from test_foundation import enqueue
from test_ordinary_goal_md import ScriptedMd, card, start

from sim2act import worker as runtime
from sim2act.db import attempts, operations, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def lock_error(code=sqlite3.SQLITE_BUSY):
    original = sqlite3.OperationalError("synthetic immediate driver failure")
    original.sqlite_errorcode = code
    return OperationalError("BEGIN IMMEDIATE", {}, original)


def test_actual_md_tool_writer_contention_renews_same_run(env, monkeypatch, tmp_path):
    store, settings, client = env[:3]
    goal, source = card(env)
    rid = start(env, goal, "md-contended-heartbeat").json()["run_id"]
    model = ScriptedMd(source)
    worker = Worker(store, settings, model)
    clock = [time.time()]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    held, release, committed, renewed = (threading.Event() for _ in range(4))
    seen, failures, renewals, foreground = [], [], [], []
    original_heartbeat, original_dispatch = store.heartbeat, runtime.dispatch

    class ScheduledEvent(threading.Event):
        def wait(self, timeout=None):
            if not seen:
                assert held.wait(20), "actual tool transaction never acquired its writer lock"
                seen.append(True)
                clock[0] += 10
                return False
            return super().wait()  # This script has exactly one tick; stop wakes cleanup.

    def hold_tool(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO operations") and not held.is_set():
            held.set()  # Actual dispatch transaction holds SQLite's writer lock.
            assert release.wait(20), "heartbeat never observed actual writer contention"

    def heartbeat(*args, **kwargs):
        if len(args) < 2 or args[1] is None:
            return original_heartbeat(*args, **kwargs)  # Worker liveness is not a Run renewal.
        kwargs["_wait_seconds"] = 0.01  # Driver wait only; original lease is still 30s.
        try:
            result = original_heartbeat(*args, **kwargs)
        except OperationalError as error:
            failures.append(error.orig.sqlite_errorcode)
            (tmp_path / "driver-events.json").write_text(json.dumps(dict(
                driver_errors=failures, committed_run_renewals=renewals)))
            release.set()
            assert committed.wait(20), "tool transaction did not finish after lock release"
            raise
        if threading.current_thread() is threading.main_thread():
            foreground.append(result)
            return result
        renewals.append(dict(worker=args[0], run=args[1], fence=args[2], lease_until=result))
        (tmp_path / "driver-events.json").write_text(json.dumps(dict(
            driver_errors=failures, committed_run_renewals=renewals)))
        renewed.set()  # Only the return from the real committed Run heartbeat publishes success.
        return result

    def dispatch(*args, **kwargs):
        result = original_dispatch(*args, **kwargs)
        if not committed.is_set():
            committed.set()
            assert renewed.wait(20), "transient BUSY permanently stopped the Run heartbeat"
        return result

    monkeypatch.setattr(store, "heartbeat", heartbeat)
    monkeypatch.setattr(runtime, "dispatch", dispatch)
    monkeypatch.setattr(runtime, "threading", SimpleNamespace(
        Event=ScheduledEvent, Thread=threading.Thread, Lock=threading.Lock))
    event.listen(store.engine, "after_cursor_execute", hold_tool)
    try:
        assert worker.once()
    finally:
        release.set()
        event.remove(store.engine, "after_cursor_execute", hold_tool)
    result = client.get("/api/runs/" + rid).json()
    assert failures == [sqlite3.SQLITE_BUSY] and len(renewals) == 1
    assert renewals[0] == dict(worker=worker.id, run=rid, fence=1, lease_until=clock[0] + 30)
    assert result["status"] == "PARTIAL" and result["result"]["goal_acceptance"] == "NOT_RUN"
    assert result["artifact_delivery"]["status"] == "DELIVERED" and model.calls == 3
    with store.tx() as conn:
        row = conn.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        actual_attempts = conn.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().all()
        actual_ops = conn.execute(select(operations).where(operations.c.run_id == rid)).mappings().all()
    assert row["fence"] == 1 and row["worker_id"] == worker.id
    assert len(actual_attempts) == 3 and all(a["status"] == "RECEIVED" for a in actual_attempts)
    assert {o["tool_ref"] for o in actual_ops} == {"resource.read", "artifact.save_text"}
    assert len(actual_ops) == 2 and all(o["status"] == "VERIFIED" for o in actual_ops)
    (tmp_path / "actual-renewal.json").write_text(json.dumps(dict(
        run_id=rid, fence=row["fence"], worker=worker.id, lease_seconds=settings.lease_seconds,
        driver_errors=failures, committed_run_renewals=renewals, foreground_renewals=foreground,
        model_calls=model.calls,
        real_model_calls=0, result=result), indent=2))


@pytest.mark.parametrize("boundary", ["lease", "run-deadline"])
def test_busy_cannot_renew_past_original_boundary_or_replacement(env, monkeypatch, boundary):
    store, settings = env[:2]
    rid = enqueue(env, "ordinary-heartbeat-" + boundary)
    worker = Worker(store, settings)
    run = store.claim(worker.id, 30)
    if boundary == "run-deadline":
        worker.s = replace(settings, run_seconds=20)
    cutoff = min(run["lease_until"], run["created_at"] + worker.s.run_seconds)
    clock = [run["lease_until"] - 25]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    held, release = threading.Event(), threading.Event()
    calls, codes = [], []
    original = store.heartbeat

    def hold():
        with store.tx():
            held.set()
            assert release.wait(20)

    holder = threading.Thread(target=hold)
    holder.start()
    assert held.wait(5)

    class OneTick(threading.Event):
        def wait(self, timeout=None):
            return False

    def blocked(*args, **kwargs):
        calls.append(kwargs)
        kwargs["_wait_seconds"] = 0.01
        try:
            return original(*args, **kwargs)
        except OperationalError as error:
            codes.append(error.orig.sqlite_errorcode)
            clock[0] = cutoff
            release.set()
            holder.join(10)
            assert not holder.is_alive()
            raise

    monkeypatch.setattr(store, "heartbeat", blocked)
    try:
        error = worker._heartbeat_lease(run, OneTick())
    finally:
        release.set()
        holder.join(10)
    assert isinstance(error, OperationalError) and codes == [sqlite3.SQLITE_BUSY]
    assert len(calls) == 1 and calls[0]["_deadline"] == cutoff
    with store.tx() as conn:
        row = conn.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["lease_until"] == run["lease_until"] and row["fence"] == run["fence"]
        assert not conn.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()
    if boundary == "lease":
        replacement = store.claim("replacement-worker", 30)
        assert replacement["id"] == rid and replacement["fence"] > run["fence"]
        with pytest.raises(DomainError):
            original(worker.id, rid, run["fence"], 30)
        with store.tx() as conn:
            row = conn.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["worker_id"] == "replacement-worker" and row["fence"] == replacement["fence"]
        assert row["lease_until"] == replacement["lease_until"]


@pytest.mark.parametrize("failure,count", [(sqlite3.SQLITE_BUSY, 16), (sqlite3.SQLITE_IOERR, 1)])
def test_immediate_driver_errors_have_finite_specific_retry(env, monkeypatch, failure, count):
    store, settings = env[:2]
    enqueue(env, "ordinary-heartbeat-driver")
    worker = Worker(store, settings)
    run = store.claim(worker.id, 30)
    clock = run["lease_until"] - 20
    monkeypatch.setattr(time, "time", lambda: clock)
    calls = []

    class OneTick(threading.Event):
        def wait(self, timeout=None):
            return False

    def failing(*args, **kwargs):
        calls.append(kwargs)
        raise lock_error(failure)

    monkeypatch.setattr(store, "heartbeat", failing)
    error = worker._heartbeat_lease(run, OneTick())
    assert isinstance(error, OperationalError) and len(calls) == count
    assert all(c["_deadline"] == run["lease_until"] and c["_wait_seconds"] <= 5 for c in calls)


def test_fatal_heartbeat_preserves_received_reply_and_stops_before_tool(env, monkeypatch):
    store, settings, client = env[:3]
    goal, source = card(env)
    rid = start(env, goal, "md-fatal-heartbeat").json()["run_id"]
    started, completed = threading.Event(), threading.Event()

    class ObservedThread(threading.Thread):
        def run(self):
            try:
                super().run()
            finally:
                completed.set()

    class Responded(ScriptedMd):
        def request(self, messages, tools):
            started.set()
            assert completed.wait(20)
            return super().request(messages, tools)

    model = Responded(source)
    worker = Worker(store, settings, model)

    def fatal(run, stopped, committed):
        assert started.wait(20)
        return RuntimeError("synthetic non-lock driver failure")

    monkeypatch.setattr(worker, "_heartbeat_lease", fatal)
    monkeypatch.setattr(runtime, "threading", SimpleNamespace(
        Event=threading.Event, Thread=ObservedThread, Lock=threading.Lock))
    assert worker.once()
    result = client.get("/api/runs/" + rid).json()
    assert result["status"] == "WAITING_RESOURCE" and model.calls == 1
    assert result["error"]["code"] == "RESOURCE_UNAVAILABLE"
    with store.tx() as conn:
        actual = conn.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
        assert actual["status"] == "RECEIVED" and actual["response"]["tool_calls"][0]["id"] == "read"
        assert not conn.execute(select(operations.c.id).where(operations.c.run_id == rid)).first()


def test_committed_foreground_interval_is_read_atomically(env, monkeypatch):
    store, settings = env[:2]
    rid = enqueue(env, "heartbeat-published-interval")
    worker = Worker(store, settings)
    run = store.claim(worker.id, 30)
    clock = [run["lease_until"] - 10]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    actual_lock = threading.Lock()
    published = []
    state = dict(lease_until=run["lease_until"], failure=None)

    class InterleavedLock:
        def __enter__(self):
            actual_lock.acquire()

        def __exit__(self, *exc):
            actual_lock.release()
            if not published:
                # Exact scheduled interleaving after the background's first read.
                # The foreground uses the original guard and commits before L.
                published.append(None)
                clock[0] = run["lease_until"] - 1
                renewed = store.heartbeat(worker.id, rid, run["fence"], 30)
                with state["lock"]:
                    state["lease_until"] = renewed
                published[0] = renewed
                clock[0] = run["lease_until"] + 1

    state["lock"] = InterleavedLock()

    class OneTick(threading.Event):
        ticks = 0

        def wait(self, timeout=None):
            self.ticks += 1
            return self.ticks > 1

    assert worker._heartbeat_lease(run, OneTick(), state) is None
    assert state["failure"] is None and published == [run["lease_until"] + 29]
    with store.tx() as conn:
        current = conn.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert current["lease_until"] == published[0] > clock[0]
        assert current["worker_id"] == worker.id and current["fence"] == run["fence"]
        assert not conn.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()


def test_fatal_decision_publishes_before_foreground_metadata_admission(env, monkeypatch):
    store, settings, client = env[:3]
    goal, source = card(env)
    rid = start(env, goal, "heartbeat-atomic-fatal").json()["run_id"]
    model = ScriptedMd(source)
    worker = Worker(store, settings, model)
    decided, release_background = threading.Event(), threading.Event()
    original_heartbeat, original_loop = store.heartbeat, worker._heartbeat_lease
    foreground, captured = [], []
    failure = RuntimeError("synthetic fatal metadata failure")

    class MetadataLock:
        def __init__(self):
            self.actual = threading.Lock()

        def __enter__(self):
            if threading.current_thread() is threading.main_thread():
                assert decided.wait(20)
            self.actual.acquire()

        def __exit__(self, *exc):
            self.actual.release()
            if threading.current_thread() is threading.main_thread():
                release_background.set()

    class Tick(threading.Event):
        def wait(self, timeout=None):
            return False

    def heartbeat(*args, **kwargs):
        if len(args) < 2 or args[1] is None:
            return original_heartbeat(*args, **kwargs)
        if threading.current_thread() is threading.main_thread():
            foreground.append(args)
            return original_heartbeat(*args, **kwargs)
        raise failure

    def observed_loop(run, stopped, committed):
        result = original_loop(run, stopped, committed)
        captured.append(committed.get("failure"))
        decided.set()
        # Hold the wrapper before its fallback publication; the decision itself
        # must already exclude foreground renewal and any model/tool dispatch.
        assert release_background.wait(20)
        return result

    monkeypatch.setattr(store, "heartbeat", heartbeat)
    monkeypatch.setattr(worker, "_heartbeat_lease", observed_loop)
    monkeypatch.setattr(runtime, "threading", SimpleNamespace(
        Event=Tick, Thread=threading.Thread, Lock=MetadataLock))
    try:
        assert worker.once()
    finally:
        release_background.set()
    assert captured == [failure] and foreground == [] and model.calls == 0
    result = client.get("/api/runs/" + rid).json()
    assert result["status"] == "WAITING_RESOURCE"
    with store.tx() as conn:
        assert not conn.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).first()
        assert not conn.execute(select(operations.c.id).where(operations.c.run_id == rid)).first()
