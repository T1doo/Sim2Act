"""Desktop-owned EOF/STOP reaches the existing real service shutdown receipt."""

import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from sim2act.synthetic_workspace import DATABASE, _read_owned_control


def test_bound_stop_and_eof_only_request_original_shutdown():
    requested = []
    worker = "worker_" + "a" * 32
    _read_owned_control(
        io.StringIO(json.dumps(dict(command="stop", worker_id=worker)) + "\n"),
        worker,
        lambda: requested.append("stop"),
    )
    assert requested == ["stop"]
    requested.clear()
    _read_owned_control(io.StringIO(""), worker, lambda: requested.append("eof"))
    assert requested == ["eof"]


def test_wrong_worker_does_not_stop_until_pipe_eof():
    requested = []

    class Stream:
        def __init__(self):
            self.first = True

        def readline(self, limit):
            assert limit == 512 and requested == []
            if self.first:
                self.first = False
                return json.dumps(dict(command="stop", worker_id="worker_" + "b" * 32)) + "\n"
            return ""

    _read_owned_control(Stream(), "worker_" + "a" * 32, lambda: requested.append("eof"))
    assert requested == ["eof"]


def test_real_consoleless_child_eof_preserves_existing_shutdown_receipt(tmp_path):
    source = Path(__file__).resolve().parents[1] / "src"
    child = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-m",
            "sim2act.cli",
            "synthetic-workspace",
            "--data-dir",
            str(tmp_path / "workspace"),
            "--new",
            "--control-stdin",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "PYTHONPATH": str(source)},
        **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
    )
    lines, pending = [], queue.Queue()

    def drain():
        for line in child.stdout:
            lines.append(line)
            pending.put(line)
        pending.put(None)

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        end = time.monotonic() + 20
        worker = None
        while time.monotonic() < end:
            line = pending.get(timeout=max(0.01, end - time.monotonic()))
            assert line is not None, "".join(lines)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("event") == "SYNTHETIC_WORKSPACE_READY":
                assert event["control_stdin"] is True
                worker = event["worker_id"]
                break
        assert worker is not None, "".join(lines)
        child.stdin.close()
        assert child.wait(timeout=20) == 0
        reader.join(timeout=5)
        assert not reader.is_alive()
        receipts = [json.loads(line) for line in lines if line.startswith("{")]
        stopped = next(r for r in receipts if r.get("event") == "SYNTHETIC_WORKSPACE_STOPPED")
        assert stopped["worker_id"] == worker
        assert stopped["worker_stopped"] and stopped["clean"] and stopped["data_preserved"]
        assert (tmp_path / "workspace" / DATABASE).is_file()
    finally:
        if child.poll() is None:
            child.stdin.close()
            child.wait(timeout=20)
        child.stdout.close()
