"""Actual controller VM plus one real HTTP connection; no browser/model claim."""

import gzip
import hashlib
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import uvicorn
from test_protocol_extract_completion import snapshot

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider
from sim2act.worker import Worker

REPO = Path(__file__).parents[1]
EVIDENCE = REPO / "docs/evidence/protocol-extract-process-recovery-20261022"


def driver(root, mode):
    result = subprocess.run(
        ["node", "tests/protocol_completion_ui.cjs", str(root), mode],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    (root / (mode + "-driver.log")).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads((root / (mode + "-result.json")).read_text())
    assert data["status"] == "PASS" and data["model_requests"] == 0
    assert (
        data["source_sha256"]
        == hashlib.sha256((REPO / "src/sim2act/web/protocol.js").read_bytes()).hexdigest()
    )
    return data


def test_completion_controller_selection_receipts_and_original_key(tmp_path):
    driver(tmp_path, "logic")


def test_protocol_material_batch_freshness_and_late_catalog(tmp_path):
    driver(tmp_path, "materials")


def test_completion_button_actual_http_without_new_model_requests(tmp_path, monkeypatch):
    """Reuse a sealed genuine received fact, not another Source/Worker/Mock prefix."""
    original = json.loads((EVIDENCE / "original.json").read_text())
    database = tmp_path / "ui.sqlite"
    with gzip.open(EVIDENCE / "before.sqlite.gz", "rb") as src, database.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    sidecar = tmp_path / (original["run"] + ".json")
    shutil.copyfile(EVIDENCE / "original-received-sidecar.json", sidecar)
    # An empty fixture-owned synchronization file carries no receipt evidence.
    sidecar.with_suffix(".lock").write_bytes(b"")
    original_sidecar = sidecar.read_bytes()
    store = Store("sqlite:///" + str(database), test_only=True)  # No initialization/reset.
    values = dict(original["settings"], database_url=str(store.engine.url), data_dir=tmp_path)
    settings = Settings(**values)
    monkeypatch.setattr(time, "time", lambda: original["resume_at"])
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("send/reserve/accept")
        raise AssertionError("Completion UI attempted a model request/reservation/acceptance")

    for owner, name in (
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (BudgetedProvider, "call"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "reserve"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    before = snapshot(store)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    (tmp_path / "http-info.json").write_text(
        json.dumps(
            dict(
                base=f"http://127.0.0.1:{port}",
                project=original["project"],
                run=original["run"],
                captured=original["captured"],
            )
        )
    )
    server = uvicorn.Server(
        uvicorn.Config(create_app(store, settings), log_level="error", access_log=False)
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=False)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        data = driver(tmp_path, "http")
        after = snapshot(store)
        assert {name for name in before if before[name] != after[name]} == {
            "runs",
            "protocol_jobs",
            "events",
        }
        assert set(before["events"]).issubset(after["events"])
        assert len(after["events"]) == len(before["events"]) + 4
        assert sidecar.read_bytes() == original_sidecar and not calls
        (tmp_path / "accounting.json").write_text(
            json.dumps(
                dict(
                    status="PASS",
                    model_calls=calls,
                    new_worker_claims=0,
                    new_mock_requests=0,
                    sidecar_unchanged=True,
                    accounting_tables_unchanged=True,
                    http_checks=data["checks"],
                    clock="explicit synthetic business clock; not real-clock/G0 qualification",
                    scope="Node VM minimal elements + real loopback HTTP; not DOM/native browser",
                ),
                indent=2,
            )
        )
    finally:
        deadline = time.monotonic() + 10
        server.should_exit = True
        thread.join(max(0, deadline - time.monotonic()))
        for worker in threading.enumerate():
            if worker.name == "AnyIO worker thread":
                worker.join(max(0, deadline - time.monotonic()))
        store.engine.dispose()
        assert not thread.is_alive()
