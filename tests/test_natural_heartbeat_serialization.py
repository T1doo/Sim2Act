"""Actual committed intervals stay ordered across natural foreground/background renewal."""

import threading
import time
from types import SimpleNamespace

from sqlalchemy import select
from test_foundation import enqueue

from sim2act import natural_spec_runtime, text_workflows
from sim2act.db import runs


def test_sync_renewal_waits_for_background_commit_and_uses_its_interval(env, monkeypatch, tmp_path):
    store, settings = env[:2]
    rid = enqueue(env, "natural-heartbeat-serialization")
    run = store.claim("original-worker", 30)
    worker = SimpleNamespace(store=store, s=settings, id="original-worker", stop=threading.Event())
    clock = [run["created_at"] + 1]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    entered, foreground_waiting, committed = (threading.Event() for _ in range(3))
    actual, foreground = store.heartbeat, threading.main_thread()
    calls = []

    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()

        def __enter__(self):
            if threading.current_thread() is foreground and entered.is_set():
                foreground_waiting.set()
            self.lock.acquire()
            return self

        def __exit__(self, *_):
            self.lock.release()

    class OneTick(threading.Event):
        def wait(self, timeout=None):
            if timeout == settings.lease_seconds / 3 and not entered.is_set():
                return False
            return super().wait()  # One scheduled tick; actual stop ends the sender.

    state = dict(lock=threading.Lock(), renewal_lock=ObservedLock(),
                 lease_until=run["lease_until"], deadline=run["created_at"] + settings.run_seconds,
                 sync_contention_recovery=True)

    def heartbeat(*args, **options):
        is_foreground = threading.current_thread() is foreground
        if is_foreground:
            assert committed.is_set(), "sync renewal overtook the background transaction"
            assert options["_deadline"] == calls[0]["actual_lease_until"]
        else:
            entered.set()
            assert foreground_waiting.wait(5), "sync renewal did not coordinate its metadata boundary"
            assert not calls
        clock[0] += 10
        renewed = actual(*args, **options)
        calls.append(dict(foreground=is_foreground, cutoff=options["_deadline"],
                          actual_lease_until=renewed, worker=args[0], run=args[1], fence=args[2]))
        if not is_foreground:
            committed.set()
        return renewed

    def advance(*_):
        assert entered.wait(5)
        natural_spec_runtime.renew(worker, run, state["deadline"], _heartbeat_state=state)
        return False

    monkeypatch.setattr(store, "heartbeat", heartbeat)
    monkeypatch.setattr(text_workflows, "threading", SimpleNamespace(
        Event=OneTick, Thread=threading.Thread, Lock=threading.Lock))
    text_workflows.process_job(worker, run, advance, _heartbeat_state=state)
    assert [call["foreground"] for call in calls] == [False, True]
    assert state["sync_renewal"]["sequence"] == 1 and "fatal_heartbeat" not in state
    with store.tx() as connection:
        saved = connection.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    assert saved["status"] == "RUNNING" and saved["fence"] == run["fence"]
    assert saved["lease_until"] == state["lease_until"] == calls[-1]["actual_lease_until"]
    assert calls[0]["actual_lease_until"] < calls[1]["actual_lease_until"]
    import json
    (tmp_path / "actual-serialized-renewals.json").write_text(json.dumps(dict(
        calls=calls, original_lease_seconds=30, original_run_seconds=300,
        real_model_calls=0, terminal_recovery_performed=False), indent=2))
