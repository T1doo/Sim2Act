"""Observe owned lifecycle identity decisions without changing them or importing config."""

import json
import os
import runpy
import sys
import time
from pathlib import Path

script = Path(sys.argv[1]).resolve()
sys.argv = [str(script), *sys.argv[2:]]
namespace = runpy.run_path(str(script), run_name="diagnostic_manage")
globals_ = namespace["main"].__globals__
original_process = globals_["process"]
psutil_ = globals_["psutil"]
trace = Path(os.environ["SIM2ACT_DATA_DIR"]).parent / f"manage-diagnostic-{os.getpid()}.jsonl"
count = 0
active = None


def emit(stage, **data):
    global count
    try:
        if count >= 200:
            return
        count += 1
        with trace.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "stage": stage,
                        "wall": time.time(),
                        "mono": time.monotonic(),
                        "manager_pid": os.getpid(),
                        **data,
                    }
                )
                + "\n"
            )
    except Exception:
        pass


class Observed:
    def __init__(self, actual):
        self.actual = actual

    def __getattr__(self, name):
        method = getattr(self.actual, name)
        if name not in {"is_running", "status", "create_time", "cmdline"}:
            return method

        def observe(*args, **kwargs):
            value = method(*args, **kwargs)
            try:
                info = {
                    "pid": self.actual.pid,
                    "method": name,
                    "kind": active.get("kind") if active else None,
                }
                if name == "cmdline":
                    info.update(
                        argc=len(value),
                        empty=not value,
                        expected_match=value == active.get("command") if active else None,
                    )
                else:
                    info["value"] = value
                emit("identity_read", **info)
            except Exception:
                pass
            return value

        return observe


class Facade:
    def Process(self, pid):
        return Observed(psutil_.Process(pid))

    def __getattr__(self, name):
        return getattr(psutil_, name)


def process(record):
    global active
    active = record
    emit(
        "identity_start",
        pid=record["pid"],
        kind=record["kind"],
        recorded_created_at=record["created_at"],
    )
    try:
        value = original_process(record)
        emit("identity_end", pid=record["pid"], verified=value is not None)
        return value.actual if isinstance(value, Observed) else value
    finally:
        active = None


globals_["psutil"] = Facade()
globals_["process"] = process
globals_["main"]()
