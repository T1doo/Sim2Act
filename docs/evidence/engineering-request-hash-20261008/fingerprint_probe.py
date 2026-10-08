"""Observe only pure snapshot hashes; never reuse a product validation result."""

import json
import os
import sys
import threading
import time
from pathlib import Path

import hotspots_probe

ROOT = Path(os.environ["SIM2ACT_DIAG_ROOT"])
LOCK = threading.Lock()
ROWS = {}
INPUTS = {}
ORIGINAL = None


def pytest_configure(config):
    from sim2act import protocol_jobs

    global ORIGINAL
    ORIGINAL = protocol_jobs.fingerprint

    def observed(value):
        caller = sys._getframe(1)
        selected = (
            caller.f_code.co_name == "verified_pending"
            and isinstance(value, dict)
            and "namespace" in value
            and "run_id" in value
            and "phase" in value
        )
        start = time.perf_counter_ns()
        result = ORIGINAL(value)
        elapsed = time.perf_counter_ns() - start
        if selected:
            key = (hotspots_probe.NODE, hotspots_probe.REQUEST.get(), caller.f_lineno)
            with LOCK:
                row = ROWS.setdefault(key, {"count": 0, "nanoseconds": 0})
                row["count"] += 1
                row["nanoseconds"] += elapsed
                if result not in INPUTS:
                    # Only generated test snapshots, no runtime credentials.
                    INPUTS[result] = json.loads(json.dumps(value, allow_nan=False))
        return result

    protocol_jobs.fingerprint = observed


def pytest_sessionfinish(session, exitstatus):
    (ROOT / "snapshot-hashes.json").write_text(
        json.dumps(
            {
                "exitstatus": int(exitstatus),
                "rows": [
                    {"node": k[0], "request": k[1], "line": k[2], **v}
                    for k, v in ROWS.items()
                ],
                "inputs": INPUTS,
                "scope": "fingerprint only; elapsed excludes observer recording",
            },
            indent=2,
        )
        + "\n"
    )


def pytest_unconfigure(config):
    from sim2act import protocol_jobs

    protocol_jobs.fingerprint = ORIGINAL
