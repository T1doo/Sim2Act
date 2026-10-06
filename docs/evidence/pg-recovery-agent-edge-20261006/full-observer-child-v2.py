"""Bounded synthetic recovery observer; preserves original fixture execution and guards."""

import hashlib
import json
import os
import runpy
import sys
import threading
import time
from pathlib import Path

from sim2act.db import Store
from sim2act.worker import Worker

root = Path(os.environ["SIM2ACT_SYNTHETIC_FAULT_DIR"])
trace = root / f"diagnostic-child-{os.environ['SIM2ACT_SYNTHETIC_FAULT']}-{os.getpid()}.jsonl"
mutex = threading.Lock()
count = 0


def emit(stage, **data):
    global count
    try:
        with mutex:
            if count >= 200:
                return
            count += 1
            row = dict(
                stage=stage, pid=os.getpid(), wall=time.time(), mono=time.monotonic(), **data
            )
            with trace.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, sort_keys=True) + "\n")
    except Exception:
        # Diagnostic I/O must never alter the original call's return or exception.
        return


def state(row):
    return {k: row[k] for k in ("id", "status", "fence", "lease_until", "worker_id")}


for method in ("claim", "heartbeat", "guard"):
    original = getattr(Store, method)

    def wrap(self, *args, _method=method, _original=original, **kwargs):
        extra = {}
        if _method == "guard":
            try:
                extra["backend_pid"] = args[0].connection.driver_connection.info.backend_pid
            except Exception:
                extra["backend_pid_unavailable"] = True
        emit(_method + "_start", **extra)
        try:
            value = _original(self, *args, **kwargs)
        except BaseException as e:
            detail = {"error_class": type(e).__name__, "error_code": getattr(e, "code", None)}
            emit(_method + "_error", **detail)
            raise
        try:
            observed_value = state(value) if isinstance(value, dict) else value
        except Exception:
            observed_value = {"metadata_unavailable": True}
        emit(_method + "_end", returned=observed_value)
        return value

    setattr(Store, method, wrap)

original_once = Worker.once


def once(self):
    emit("once_start")
    value = original_once(self)
    emit("once_end", returned=value)
    return value


Worker.once = once
emit(
    "import",
    store_file=sys.modules[Store.__module__].__file__,
    db_sha256=hashlib.sha256(Path(sys.modules[Store.__module__].__file__).read_bytes()).hexdigest(),
    app_jobs_sha256=hashlib.sha256(
        (Path(sys.modules[Store.__module__].__file__).parent / "app_jobs.py").read_bytes()
    ).hexdigest(),
)
if sys.argv[1] == "--self-check":
    # No DB/worker/Run requests. Force diagnostic I/O failure and preserve identity/one call.
    trace = root  # opening an existing directory must fail, best effort only
    calls = []
    error = RuntimeError("synthetic observer identity")

    def fail(_self, *_args, **_kwargs):
        calls.append(1)
        raise error

    try:
        Store.guard(None, object(), "synthetic", 1, _original=fail)
    except RuntimeError as caught:
        assert caught is error and len(calls) == 1
    else:
        raise AssertionError("Original failure was suppressed")
    value = {
        "id": "synthetic",
        "status": "RUNNING",
        "fence": 1,
        "lease_until": 1,
        "worker_id": "synthetic",
    }
    assert Store.guard(None, object(), "synthetic", 1, _original=lambda *_: value) is value
    print(
        "PASS observer I/O failure cannot replace original return or exception; no SQL observation"
    )
else:
    runpy.run_path(sys.argv[1], run_name="__main__")
