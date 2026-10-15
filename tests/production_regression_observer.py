"""Opt-in synthetic regression observation; no DB reads or execution decisions."""
import functools
import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from sim2act import natural_spec_runtime
from sim2act.db import Store
from sim2act.errors import DomainError


def _write(nodeid, suffix, value):
    directory = os.environ.get("SIM2ACT_REGRESSION_OBSERVER_DIR")
    if directory is None:
        return
    try:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(nodeid.encode()).hexdigest()
        with (root / (key + suffix)).open("a") as stream:
            stream.write(value + "\n")
    except OSError:
        pass  # Observation failure must never replace a product result.


@pytest.fixture(autouse=True)
def observe_public_rejection(request, monkeypatch):
    if os.environ.get("SIM2ACT_REGRESSION_OBSERVER_DIR") is not None:
        original = natural_spec_runtime.fail_owned

        @functools.wraps(original)
        def observed(worker, run, error):
            try:
                value = dict(nodeid=request.node.nodeid, at=time.time(),
                             run_id=run.get("id"), phase="error_settlement_requested",
                             error=error.public() if isinstance(error, DomainError) else None,
                             error_type=type(error).__name__)
                _write(request.node.nodeid, ".jsonl", json.dumps(value))
            except Exception:
                pass  # Includes observation formatting; original executes once below.
            return original(worker, run, error)

        monkeypatch.setattr(natural_spec_runtime, "fail_owned", observed)

        original_heartbeat = Store.heartbeat

        @functools.wraps(original_heartbeat)
        def heartbeat(store, worker_id, run_id=None, fence=None, lease_seconds=30, **options):
            try:
                started = time.monotonic()
            except Exception:
                started = None

            def emit(phase, *, result=None, error=None):
                try:
                    driver = getattr(error, "orig", None)
                    value = dict(nodeid=request.node.nodeid, phase=phase, at=time.time(),
                        thread=threading.get_ident(), thread_name=threading.current_thread().name,
                        worker_id=worker_id, run_id=run_id, fence=fence,
                        requested_lease_seconds=lease_seconds,
                        elapsed=None if started is None else time.monotonic()-started,
                        renewed_until=result,
                        error=error.public() if isinstance(error, DomainError) else None,
                        error_type=None if error is None else type(error).__name__,
                        sqlite_errorcode=(getattr(driver, "sqlite_errorcode", None)
                            if isinstance(driver, sqlite3.Error) else None))
                    _write(request.node.nodeid, ".heartbeat.jsonl", json.dumps(value))
                except Exception:
                    pass

            emit("begin")
            try:
                result = original_heartbeat(store, worker_id, run_id, fence, lease_seconds,
                    **options)
            except BaseException as error:
                emit("error", error=error)
                raise
            emit("return", result=result)
            return result

        monkeypatch.setattr(Store, "heartbeat", heartbeat)
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        try:
            _write(item.nodeid, ".failure.txt", report.longreprtext)
        except Exception:
            pass
