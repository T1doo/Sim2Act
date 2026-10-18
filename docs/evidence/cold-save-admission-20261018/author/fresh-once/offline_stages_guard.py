"""Session-wide guard starts before the module-scoped fresh prefix fixture."""
import json
import sys
import os
import socket
import threading
import time
import traceback
from pathlib import Path

import httpx
import pytest

from sim2act.config import Settings
from sim2act.model import InternModel, MockModel
from sim2act.db import Store

attempts = []
adapter_methods = []
heartbeats = []
controller_checks = []
patch = None
commit_guards = []
transaction_spans = []
sql_observer = threading.local()
engine_listeners = []


def pytest_sessionstart(session):
    global patch
    patch = pytest.MonkeyPatch()

    def blocked(*args, **kwargs):
        attempts.append("FORBIDDEN_REAL_IO_OR_ENV_DISCOVERY_OR_MOCK_FALLBACK")
        raise AssertionError("Fresh stages qualification permits only exact synthetic InternModel")

    patch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    patch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked)
    patch.setattr(socket.socket, "connect", blocked)
    patch.setattr(socket.socket, "connect_ex", blocked)
    patch.setattr(socket, "create_connection", blocked)
    patch.setattr(Settings, "from_env", blocked)
    patch.setattr(MockModel, "request", blocked)
    original_heartbeat = Store.heartbeat

    def observed_heartbeat(self, worker_id, run_id=None, fence=None, lease_seconds=30, **kwargs):
        if run_id is not None and not 0 < lease_seconds <= 30:
            blocked()
        started = time.time()
        renewed = original_heartbeat(self, worker_id, run_id, fence, lease_seconds, **kwargs)
        if run_id is not None:
            heartbeats.append(dict(run_id=run_id, fence=fence, lease_seconds=lease_seconds,
                deadline=kwargs.get("_deadline"), running_only=kwargs.get("_running_only",False),
                thread=threading.current_thread().name, started_at=started,
                committed_at=time.time(), renewed_until=renewed))
        return renewed
    patch.setattr(Store, "heartbeat", observed_heartbeat)
    from sim2act import production_trial_journal as journal
    from sim2act import production_trial_policy as policy
    for module, name in ((journal, "_apply_in_transaction"), (policy, "check_run")):
        original = getattr(module, name)

        def observed(*args, _original=original, _name=name, **kwargs):
            started = time.monotonic()
            value = args[5] if len(args) > 5 else kwargs.get(
                "stage" if _name == "check_run" else "identity")
            stage = value if _name == "check_run" else getattr(value, "stage", None)
            row = dict(function=_name, stage=stage, started_at=time.time())
            if _name == "_apply_in_transaction":
                row["operation"] = args[9] if len(args) > 9 else kwargs.get("operation")
            try:
                return _original(*args, **kwargs)
            except BaseException as exc:
                row.update(error=getattr(exc, "code", type(exc).__name__), traceback=[dict(file=Path(f.filename).name,
                    line=f.lineno, function=f.name) for f in traceback.extract_tb(exc.__traceback__)])
                raise
            finally:
                row.update(seconds=time.monotonic()-started, ended_at=time.time())
                controller_checks.append(row)
        patch.setattr(module, name, observed)
    # Passive observer only: no SQL, clock changes, heartbeat, return or error changes.
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    from sim2act import pa_spec_apps as spec
    original_guard = spec.commit_guard
    serial = [0]

    def began(c):
        serial[0] += 1
        c.info["cold_save_observer_tx"] = dict(id=serial[0], started_at=time.time(),
            monotonic=time.monotonic(), cpu=time.thread_time(), sql_count=0,
            sql_seconds=0.0, thread=threading.get_ident())

    def closed(c, outcome):
        row = c.info.pop("cold_save_observer_tx", None)
        if row is not None:
            row.update(ended_at=time.time(), seconds=time.monotonic()-row.pop("monotonic"),
                       cpu_seconds=time.thread_time()-row.pop("cpu"), outcome=outcome)
            transaction_spans.append(row)

    def committed(c):
        closed(c, "commit_event_before_driver_commit")

    def rolled_back(c):
        closed(c, "rollback")

    def sql_before(c, cursor, statement, parameters, context, many):
        stack = getattr(sql_observer, "stack", ())
        row = stack[-1] if stack else None
        tx = c.info.get("cold_save_observer_tx")
        context.cold_save_observer = (time.monotonic(), row, tx)
        if row is not None:
            row["sql_count"] += 1
        if tx is not None:
            tx["sql_count"] += 1

    def sql_after(c, cursor, statement, parameters, context, many):
        started, row, tx = context.cold_save_observer
        elapsed = time.monotonic()-started
        if row is not None:
            row["sql_seconds"] += elapsed
        if tx is not None:
            tx["sql_seconds"] += elapsed
            if statement == "BEGIN IMMEDIATE":
                tx["begin_immediate_seconds"] = elapsed

    for name, observer in (("begin", began), ("commit", committed), ("rollback", rolled_back),
                           ("before_cursor_execute", sql_before), ("after_cursor_execute", sql_after)):
        event.listen(Engine, name, observer)
        engine_listeners.append((Engine, name, observer))

    def observed_guard(worker, c, run, binding, delta=0):
        started, cpu, at = time.monotonic(), time.thread_time(), time.time()
        caller = sys._getframe(1)
        heartbeat = next((h for h in reversed(heartbeats) if h["run_id"] == run["id"]), None)
        lease = heartbeat["renewed_until"] if heartbeat is not None else run["lease_until"]
        row = dict(run_id=run["id"], caller=dict(file=Path(caller.f_code.co_filename).name,
            line=caller.f_lineno, function=caller.f_code.co_name), delta=delta,
            started_at=at, input_lease_until=run["lease_until"], last_committed_lease_until=lease,
            lease_remaining_at_start=lease-at, connection_id=id(c),
            transaction_id=id(c.get_transaction()), thread=threading.get_ident(),
            transaction_observer_id=c.info.get("cold_save_observer_tx", {}).get("id"),
            read_segment_at_start=c.info.get("pb_source_reads") is not None,
            write_epoch_at_start=c.info.get("source_proof_write_epoch", 0),
            sql_count=0, sql_seconds=0.0)
        stack = getattr(sql_observer, "stack", None)
        if stack is None:
            stack = sql_observer.stack = []
        stack.append(row)
        try:
            result = original_guard(worker, c, run, binding, delta)
            row["returned_lease_until"] = result["lease_until"]
            return result
        except BaseException as exc:
            row.update(error=getattr(exc,"code",type(exc).__name__),
                traceback=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name)
                           for f in traceback.extract_tb(exc.__traceback__)])
            raise
        finally:
            ended = time.time()
            row.update(ended_at=ended, seconds=time.monotonic()-started,
                cpu_seconds=time.thread_time()-cpu, lease_remaining_at_end=lease-ended,
                read_segment_at_end=c.info.get("pb_source_reads") is not None,
                write_epoch_at_end=c.info.get("source_proof_write_epoch", 0))
            stack.pop()
            commit_guards.append(row)
    patch.setattr(spec, "commit_guard", observed_guard)
    for name in ("request", "request_serialized", "request_serialized_captured",
                 "_request_serialized", "_deadline_request"):
        original = getattr(InternModel, name)

        def guarded(self, *args, _original=original, _name=name, **kwargs):
            if (type(self) is not InternModel or type(self.transport) is not httpx.MockTransport
                    or type(self.settings) is not Settings or self.settings.mode != "mock"
                    or self.settings.token not in ("synthetic-offline-planner", "synthetic-offline-natural-spec")):
                blocked()
            adapter_methods.append(dict(method=_name, family=self.settings.token))
            if _name == "request_serialized_captured":
                print("OFFLINE_CAPTURE_ENTRY", len([m for m in adapter_methods if m["method"] == _name]), self.settings.token, time.time(), flush=True)
            return _original(self, *args, **kwargs)
        patch.setattr(InternModel, name, guarded)


def pytest_sessionfinish(session, exitstatus):
    Path(os.environ["STAGES_GUARD_PROOF"]).write_text(json.dumps(dict(
        attempts=attempts, adapter_methods=adapter_methods, heartbeats=heartbeats,
        passive_original_controller_checks=controller_checks,
        passive_commit_guards=commit_guards, passive_transactions=transaction_spans,
        passive_cpu_clock="time.thread_time", transaction_end_marker="SQLAlchemy commit/rollback event before driver completion",
        pytest_exitstatus=exitstatus,
        guard_starts_before_module_fixture=True,
        scope="Exact original InternModel with synthetic tokens and MockTransport only"), indent=2) + "\n")
    from sqlalchemy import event
    for target, name, observer in engine_listeners:
        event.remove(target, name, observer)
    patch.undo()
