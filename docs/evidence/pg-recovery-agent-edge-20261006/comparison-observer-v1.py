"""Bounded synthetic recovery observer; preserves original fixture execution and guards."""

import hashlib
import json
import os
import runpy
import sys
import threading
import time
from pathlib import Path

from sqlalchemy import select

from sim2act.db import Store, runs
from sim2act.worker import Worker

root = Path(os.environ["SIM2ACT_SYNTHETIC_FAULT_DIR"])
trace = root / f"diagnostic-child-{os.environ['SIM2ACT_SYNTHETIC_FAULT']}-{os.getpid()}.jsonl"
mutex = threading.Lock()
count = 0


def emit(stage, **data):
    global count
    with mutex:
        if count >= 200:
            return
        count += 1
        row = dict(stage=stage, pid=os.getpid(), wall=time.time(), mono=time.monotonic(), **data)
        # One bounded line, closed before os._exit; no fsync or SQL diagnostics in successful guards.
        with trace.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def state(row):
    return {k: row[k] for k in ("id", "status", "fence", "lease_until", "worker_id")}


for method in ("claim", "heartbeat", "guard"):
    original = getattr(Store, method)

    def wrap(self, *args, _method=method, _original=original, **kwargs):
        extra = {}
        if _method == "guard":
            extra["backend_pid"] = args[0].connection.driver_connection.info.backend_pid
        emit(_method + "_start", **extra)
        try:
            value = _original(self, *args, **kwargs)
        except BaseException as e:
            detail = {"error_class": type(e).__name__, "error_code": getattr(e, "code", None)}
            if _method == "guard":
                row = args[0].execute(select(runs).where(runs.c.id == args[1])).mappings().one()
                detail["state"] = state(row)
            emit(_method + "_error", **detail)
            raise
        emit(_method + "_end", returned=state(value) if isinstance(value, dict) else value)
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
runpy.run_path(sys.argv[1], run_name="__main__")
