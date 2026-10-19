"""Directed original production Generate heartbeat/SQLite contention regression.

One real Mock exchange, an owned test writer and real wall-clock lease expiry.
The foreground is held outside transactions before its second reserve. This is
an isolated scheduler experiment, not a completed generation or P-B acceptance.
"""

import itertools
import json
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager
from types import CodeType

import test_natural_spec_apps as apps
from sqlalchemy import select
from test_pb_spec_production_controller import prepare_pb
from test_spec_production_controller import configured
from test_spec_production_controller import no_real_http as no_real_http

from sim2act import db
from sim2act import goal_applications as generation
from sim2act.db import Store, attempts, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def test_generate_recovers_one_bounded_sqlite_busy_without_losing_original_lease(env, tmp_path, monkeypatch):
    data, binding, fixture, factory = configured(env, tmp_path, monkeypatch, prepare_case=prepare_pb)
    store = data[0]
    events, io_errors = [], []
    event_lock, numbers = threading.Lock(), itertools.count()
    active = {}
    foreground_held, release_foreground = threading.Event(), threading.Event()
    request_lock, lock_acquired, release_lock = threading.Event(), threading.Event(), threading.Event()
    busy, recovered = threading.Event(), threading.Event()
    claim, selected, reserve_calls, failure = {}, {}, [], []
    original_tx, original_heartbeat, original_claim = Store.tx, Store.heartbeat, Store.claim
    original_reserve, original_guard, original_time = Worker.reserve, Store.guard, db.time
    beat_code = next(c for c in generation.process.__code__.co_consts
                     if isinstance(c, CodeType) and c.co_name == "beat")

    def record(kind, **values):
        item = dict(sequence=next(numbers), kind=kind, wall=time.time(),
                    monotonic=time.monotonic(), thread=threading.get_ident(), **values)
        with event_lock:
            events.append(item)
        return item

    def stack():
        frame, result = sys._getframe(2), []
        while frame is not None and len(result) < 18:
            result.append(dict(file=frame.f_code.co_filename, function=frame.f_code.co_name,
                               line=frame.f_lineno))
            frame = frame.f_back
        return result

    @contextmanager
    def traced_tx(self, *args, **kwargs):
        if self is not store:
            with original_tx(self, *args, **kwargs) as c:
                yield c
            return
        token = next(numbers)
        record("tx_attempt", transaction=token, options=kwargs, stack=stack())
        try:
            with original_tx(self, *args, **kwargs) as c:
                active[threading.get_ident()] = token
                record("tx_acquired", transaction=token, connection=id(c),
                       driver=id(c.connection.driver_connection))
                try:
                    yield c
                finally:
                    record("tx_body_end", transaction=token)
            record("tx_committed", transaction=token)
        except Exception as error:
            record("tx_error", transaction=token, error=type(error).__name__,
                   sqlite_errorcode=getattr(getattr(error, "orig", None), "sqlite_errorcode", None))
            raise
        finally:
            active.pop(threading.get_ident(), None)

    def traced_claim(self, *args, **kwargs):
        result = original_claim(self, *args, **kwargs)
        if self is store and result:
            claim.update(result)
            selected["lease"] = result["lease_until"]
            record("claimed", run_id=result["id"], lease_until=result["lease_until"],
                   fence=result["fence"], created_at=result["created_at"])
        return result

    class ExactClockProbe:
        def __getattr__(self, name):
            return getattr(original_time, name)

        def time(self):
            value = original_time.time()
            frame = sys._getframe(1)
            if frame.f_code is original_guard.__code__ and frame.f_locals.get("run_id") == claim.get("id"):
                row = frame.f_locals.get("r")
                record("original_guard_comparison", compared_at=value,
                       lease_until=row["lease_until"], status=row["status"],
                       row_fence=row["fence"], expected_fence=frame.f_locals["fence"], stack=stack())
            return value

    def traced_reserve(worker, *args, **kwargs):
        if worker.store is store and kwargs.get("generation_request"):
            reserve_calls.append(len(reserve_calls) + 1)
            record("foreground_reserve_boundary", ordinal=len(reserve_calls),
                   active_transaction=active.get(threading.get_ident()))
            if len(reserve_calls) == 2:
                assert threading.get_ident() not in active
                foreground_held.set()
                if not release_foreground.wait(55):
                    raise AssertionError("Directed scheduler hold exceeded its bound")
        return original_reserve(worker, *args, **kwargs)

    def returned_beat(frame, event, arg):
        if frame.f_code is beat_code and event == "return":
            record("original_beat_return", stopped=frame.f_locals["stopped"].is_set())
            sys.setprofile(None)

    def traced_heartbeat(self, worker_id, run_id=None, *args, **kwargs):
        caller = sys._getframe(1)
        in_beat = False
        for _ in range(5):
            if caller is None:
                break
            in_beat = in_beat or caller.f_code is beat_code
            caller = caller.f_back
        targeted = self is store and run_id is not None and in_beat
        if targeted and foreground_held.is_set() and not request_lock.is_set():
            selected["old_lease"] = selected["lease"]
            record("inject_writer_requested", run_id=run_id, original_lease=selected["old_lease"])
            request_lock.set()
            if not lock_acquired.wait(3):
                raise AssertionError("Owned writer did not acquire within its test bound")
        record("heartbeat_enter", run_id=run_id, options=kwargs)
        try:
            result = original_heartbeat(self, worker_id, run_id, *args, **kwargs)
        except Exception as error:
            record("heartbeat_error", run_id=run_id, error=type(error).__name__,
                   sqlite_errorcode=getattr(getattr(error, "orig", None), "sqlite_errorcode", None), stack=stack())
            if targeted and getattr(getattr(error, "orig", None), "sqlite_errorcode", None) == 5:
                busy.set()
                release_lock.set()
                sys.setprofile(returned_beat)
            raise
        record("heartbeat_committed_return", run_id=run_id, lease_until=result)
        if self is store and run_id is not None and result is not None:
            selected["lease"] = result
            if busy.is_set():
                recovered.set()
                sys.setprofile(None)
        return result

    monkeypatch.setattr(Store, "tx", traced_tx)
    monkeypatch.setattr(Store, "claim", traced_claim)
    monkeypatch.setattr(Store, "heartbeat", traced_heartbeat)
    monkeypatch.setattr(Worker, "reserve", traced_reserve)
    monkeypatch.setattr(db, "time", ExactClockProbe())

    def owned_writer():
        if not request_lock.wait(50):
            io_errors.append("Writer was never requested")
            return
        try:
            with sqlite3.connect(store.engine.url.database, timeout=2) as c:
                record("owned_writer_begin_attempt")
                c.execute("BEGIN IMMEDIATE")
                record("owned_writer_acquired")
                lock_acquired.set()
                assert release_lock.wait(7), "Owned writer hold exceeded7 seconds"
                c.rollback()
                record("owned_writer_released")
        except Exception as error:
            io_errors.append(type(error).__name__ + ":" + str(error))
            release_lock.set()

    sent, transport = apps.generation_transport(data, "ordered", False)
    made = data[2].post(f"/api/projects/{data[4]}/goal-cards/{data[6]['id']}/application-runs",
        json=dict(expected_version=data[6]["version"], expected_fingerprint=data[6]["fingerprint"],
                  request_key=binding.contract.stage_keys.generate, family="natural_spec"))
    assert made.status_code == 202, made.text
    worker = factory(store, data[1], goal_planner_transport=transport)

    def foreground():
        try:
            record("foreground_start")
            worker.once()
            record("foreground_return")
        except Exception as error:
            failure.append(type(error).__name__ + ":" + str(error))
            record("foreground_error", error=type(error).__name__)

    holder = threading.Thread(target=owned_writer, daemon=True)
    running = threading.Thread(target=foreground, daemon=True)
    holder.start()
    running.start()
    guard_error, counters = None, None
    try:
        assert foreground_held.wait(50), "Second reserve boundary not reached"
        assert busy.wait(22), "Known writer did not produce one actual SQLite BUSY"
        assert release_lock.is_set() and holder.join(timeout=3) is None and not holder.is_alive()
        # Use the actual previous committed lease and the actual wall clock.
        # The foreground owns no transaction throughout this scheduler hold.
        remaining = selected["old_lease"] + 0.05 - time.time()
        if remaining > 0:
            assert remaining < 30
            threading.Event().wait(remaining)
        with store.tx() as c:
            row = c.execute(select(runs.c.context, runs.c.status, runs.c.lease_until)
                            .where(runs.c.id == claim["id"])).mappings().one()
            counters = dict(requests=row["context"]["requests"], status=row["status"],
                            lease_until=row["lease_until"], attempts=len(c.execute(select(attempts.c.id)
                            .where(attempts.c.run_id == claim["id"])).all()))
            try:
                store.guard(c, claim["id"], claim["fence"])
            except DomainError as error:
                guard_error = error.public()
        record("original_interval_probe", recovered=recovered.is_set(), counters=counters, error=guard_error)
    finally:
        worker.stop.set()
        release_foreground.set()
        release_lock.set()
        running.join(timeout=15)
        holder.join(timeout=3)
        record("test_teardown", foreground_alive=running.is_alive(), writer_alive=holder.is_alive())
        (tmp_path / "directed-lease-proof.json").write_text(json.dumps(dict(
            scope="DIRECTED_SCHEDULER_AND_OWNED_SQLITE_WRITER_NOT_COMPLETE_PB_ACCEPTANCE",
            real_models=0, mock_exchanges=len(fixture["sends"]), foreground_reserve_calls=len(reserve_calls),
            original_lease=selected.get("old_lease"), recovered=recovered.is_set(), guard_error=guard_error,
            counters=counters, observation_errors=io_errors, foreground_errors=failure, events=events), indent=2))
        data[2].close()
    assert not running.is_alive() and not holder.is_alive() and io_errors == [] and failure == []
    assert len(sent) == len(fixture["sends"]) == 1 and len(reserve_calls) == 2
    assert counters["requests"] == counters["attempts"] == 1 and counters["status"] == "RUNNING"
    assert recovered.is_set() and guard_error is None, "A single bounded BUSY permanently stopped the original Generate heartbeat"
