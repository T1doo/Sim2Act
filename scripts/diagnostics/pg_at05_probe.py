"""Observe only existing AT05 manage subprocess returns; preserve calls/timeout/results."""

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def owned_lifecycle_probe(request, monkeypatch):
    if request.node.name != "test_AT05_real_process_stop_accept_restart_reopen":
        yield
        return
    data_dir = request.getfixturevalue("env")[1].data_dir
    original = subprocess.run
    records = []
    root = Path(request.node.fspath).parents[1]

    def observe(argv, *args, **kwargs):
        selected = (
            len(argv) > 2
            and argv[1] == "scripts/manage.py"
            and Path(kwargs.get("cwd", ".")).resolve() == root.resolve()
        )
        if not selected:
            return original(argv, *args, **kwargs)
        record = {
            "phase": argv[2],
            "wall_start": time.time(),
            "mono_start": time.monotonic(),
            "timeout": kwargs.get("timeout"),
        }
        try:
            argv = [
                argv[0],
                str(Path(__file__).with_name("manage_trace.py")),
                str(root / "scripts/manage.py"),
                *argv[2:],
            ]
            result = original(argv, *args, **kwargs)
        except BaseException as e:
            record["error_class"] = type(e).__name__
            records.append(record)
            raise
        try:
            record.update(
                wall_end=time.time(), mono_end=time.monotonic(), returncode=result.returncode
            )
            record["stderr_error_classes"] = re.findall(
                r"(?:^|\n)([A-Za-z_.]+(?:Error|Exception)):", result.stderr or ""
            )
            record["known_messages"] = [
                s
                for s in (
                    "API/worker exited; inspect local logs",
                    "Startup health timed out",
                    "Cannot verify owned process",
                    "Port occupied; no process started",
                    "Owned process already running",
                )
                if s in (result.stderr or "")
            ]
            try:
                output = json.loads(result.stdout)
                record["processes"] = [
                    {k: r[k] for k in ("kind", "pid", "created_at")}
                    for r in output.get("processes", [])
                ]
                record["health"] = output.get("health")
            except (ValueError, TypeError, KeyError, AttributeError):
                pass
            records.append(record)
        except Exception:
            pass
        return result

    monkeypatch.setattr(subprocess, "run", observe)
    yield
    try:
        out = Path(os.environ["SIM2ACT_RECOVERY_DIAG_DIR"])
        out.mkdir(parents=True, exist_ok=True)
        row = {
            "scope": "Only own AT05 manage return fields; no stdout/stderr/env values/SQL/data dump",
            "manage_sha256": hashlib.sha256((root / "scripts/manage.py").read_bytes()).hexdigest(),
            "root": str(root),
            "records": records[:20],
        }
        (out / "at05-manage.json").write_text(json.dumps(row, indent=2) + "\n")
        for path in data_dir.glob("manage-diagnostic-*.jsonl"):
            (out / path.name).write_bytes(path.read_bytes())
    except Exception as e:
        print("AT05 observer archive unavailable: " + type(e).__name__)
