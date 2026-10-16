"""Known SQLite contention recovery needs a newer real same-owner renewal."""

import json
import threading
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from test_workflow_heartbeat_failure import error, setup

from sim2act import text_workflows as flow
from sim2act.db import runs


@pytest.mark.parametrize("case", ["real-lock", "numeric-only", "old-marker", "wrong-scope",
                                  "deadline", "non-busy", "repeat-failure"])
def test_new_committed_sync_renewal_and_restarted_sender(env, monkeypatch, tmp_path, caplog, case):
    worker, run, state, first_done, observed = setup(env, monkeypatch)
    state.update(deadline=None, sync_contention_recovery=True)
    caplog.set_level("INFO", logger=flow.__name__)
    original = worker.store.heartbeat
    calls, advances, exits = [], [], []
    second_done = threading.Event()
    base_thread = flow.threading.Thread

    class TrackedThread(base_thread):
        def run(self):
            try:
                return super().run()
            finally:
                exits.append(threading.get_ident())
                if len(exits) == 2:
                    second_done.set()

    monkeypatch.setattr(flow, "threading", SimpleNamespace(
        Event=flow.threading.Event, Thread=TrackedThread, Lock=threading.Lock))
    if case == "old-marker":
        renewed = original(worker.id, run["id"], run["fence"], worker.s.lease_seconds)
        flow.publish_sync_renewal(worker, run, state, renewed)

    background_calls = [0]

    def heartbeat(*args, **kwargs):
        row = dict(thread=threading.current_thread().name, start=time.monotonic(), options=kwargs)
        calls.append(row)
        if threading.current_thread() is not threading.main_thread():
            background_calls[0] += 1
            if case != "real-lock" and (background_calls[0] == 1 or case == "repeat-failure"):
                row.update(error_code=10 if case == "non-busy" or
                           (case == "repeat-failure" and background_calls[0] > 1) else 5, synthetic=True)
                raise error(row["error_code"])
        try:
            renewed = original(*args, **kwargs)
        except OperationalError as exc:
            row.update(end=time.monotonic(), error_code=exc.orig.sqlite_errorcode,
                       statement=exc.statement, synthetic=False)
            raise
        row.update(end=time.monotonic(), committed_lease_until=renewed)
        if threading.current_thread() is not threading.main_thread():
            observed.set()
        return renewed

    monkeypatch.setattr(worker.store, "heartbeat", heartbeat)
    held = worker.store.tx()
    connection = held.__enter__()
    closed = False
    current = worker.store.guard(connection, run["id"], run["fence"])
    contract = worker.store.frozen_contract(connection, current)
    timeout = connection.connection.driver_connection.execute("PRAGMA busy_timeout").fetchone()[0]
    assert timeout == 5000 and worker.s.lease_seconds == 30 and worker.s.run_seconds == 300

    def advance(*_):
        nonlocal closed
        advances.append(time.monotonic())
        if len(advances) == 1:
            assert first_done.wait(8), "Original sender did not stop within its original driver wait"
            assert len(calls) == 1 and calls[0]["error_code"] == (10 if case == "non-busy" else 5)
            held.__exit__(None, None, None)
            closed = True
            renewed = worker.store.heartbeat(worker.id, run["id"], run["fence"], worker.s.lease_seconds)
            state["deadline"] = run["created_at"] + contract.limits.run_seconds
            if case in {"numeric-only", "old-marker"}:
                with state["lock"]:
                    state["lease_until"] = renewed
            else:
                flow.publish_sync_renewal(worker, run, state, renewed)
                if case == "wrong-scope":
                    state["sync_renewal"]["run_id"] = "another-run"
                elif case == "deadline":
                    state["deadline"] = time.time() - 1
            return True
        assert len(advances) == 2
        if case == "repeat-failure":
            assert second_done.wait(3), "Restarted sender did not report its new failure"
            return True
        assert case == "real-lock" and observed.wait(3), "No actual restarted background renewal"
        return False

    try:
        if case in {"non-busy", "repeat-failure"}:
            with pytest.raises(OperationalError):
                flow.process_job(worker, run, advance, _heartbeat_state=state)
        else:
            flow.process_job(worker, run, advance, _heartbeat_state=state)
        with worker.store.engine.connect() as read:
            after = dict(read.execute(select(runs).where(runs.c.id == run["id"])).mappings().one())
        recovered = [r for r in caplog.records if r.msg == "heartbeat_contention_recovered"]
        if case == "real-lock":
            assert len(advances) == 2 and len(recovered) == 1 and observed.is_set()
            assert after["status"] == "RUNNING" and after["error"] is None
            assert calls[0]["synthetic"] is False and calls[0]["statement"] == "BEGIN IMMEDIATE"
            assert calls[0]["end"] - calls[0]["start"] >= 4.5
            assert background_calls[0] >= 2
        elif case == "repeat-failure":
            assert len(advances) == 2 and len(recovered) == 1
            assert after["status"] == "RUNNING" and after["error"] is None
            assert calls[-1]["error_code"] == 10
        elif case == "non-busy":
            assert len(advances) == 1 and not recovered and after["status"] == "RUNNING"
        else:
            assert len(advances) == 1 and not recovered and after["status"] == "WAITING_RESOURCE"
        for name in ["worker_id", "fence", "created_at", "request_key", "context"]:
            assert after[name] == run[name], name
        assert exits and len(exits) == (2 if recovered else 1)
        (tmp_path / "proof.json").write_text(json.dumps(dict(
            case=case, classification="ACTUAL_CONTROLLER_BASIC_RUN; real-lock uses real SQLite default wait; other faults synthetic",
            scheduling="Only Event.wait(10) shortened to .001; no lease/deadline/driver-budget increase",
            original_lease_seconds=30, original_run_seconds=300, driver_busy_timeout_ms=timeout,
            calls=calls, advances=len(advances), recovered_logs=len(recovered), final_run=after,
            natural_business_flow="NOT_RUN", real_model_requests=0,
        ), indent=2), encoding="utf-8")
    finally:
        if not closed:
            held.__exit__(None, None, None)


def test_failed_sync_renewal_does_not_publish_recovery_marker(env, monkeypatch):
    from sim2act.errors import DomainError
    from sim2act.natural_spec_runtime import renew

    worker, run, state, _, _ = setup(env, monkeypatch)
    worker.id = "another-worker"
    with pytest.raises(DomainError):
        renew(worker, run, run["created_at"] + worker.s.run_seconds, _heartbeat_state=state)
    assert "sync_renewal" not in state and state["lease_until"] == run["lease_until"]
