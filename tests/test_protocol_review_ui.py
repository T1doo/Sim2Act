"""Registered-review entry: sealed Source facts, zero new Worker/provider requests.

Controller VM + real loopback HTTP/SQLite, not native DOM/PG/G0 qualification.
The explicit synthetic business clock does not change product clocks or limits.
"""

import gzip
import hashlib
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, grants, meta, protocol_jobs, protocol_reviews, runs
from sim2act.db import fingerprint as digest
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider
from sim2act.worker import Worker

REPO = Path(__file__).parents[1]
SEALED = REPO / "docs/evidence/protocol-source-process-recovery-20261022"


def snapshot(store):
    with store.engine.connect() as c:
        return {
            table.name: sorted(digest(dict(row)) for row in c.execute(select(table)).mappings())
            for table in meta.sorted_tables
        }


@pytest.fixture
def sealed(tmp_path, monkeypatch):
    original = json.loads((SEALED / "original.json").read_text())
    database = tmp_path / "review.sqlite"
    with gzip.open(SEALED / "after.sqlite.gz", "rb") as src, database.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    sidecar = tmp_path / (original["run"] + ".json")
    shutil.copyfile(SEALED / "original-received-sidecar.json", sidecar)
    sidecar.with_suffix(".lock").write_bytes(b"")
    store = Store("sqlite:///" + str(database), test_only=True)  # Never initialize/reset.
    settings = Settings(
        **dict(original["settings"], database_url=str(store.engine.url), data_dir=tmp_path)
    )
    monkeypatch.setattr(time, "time", lambda: original["resume_at"])
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("send/reserve/accept/claim")
        raise AssertionError("Review must not send, reserve, accept a candidate or claim a Worker")

    for owner, name in (
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (BudgetedProvider, "call"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "reserve"),
        (Store, "claim"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    try:
        yield store, settings, original, sidecar, calls
    finally:
        store.engine.dispose()
        assert calls == []


def driver(root, mode):
    result = subprocess.run(
        ["node", "tests/protocol_review_ui.cjs", str(root), mode],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    (root / (mode + "-driver.log")).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((root / (mode + "-result.json")).read_text())
    assert report["status"] == "PASS" and report["model_requests"] == 0
    assert (
        report["source_sha256"]
        == hashlib.sha256((REPO / "src/sim2act/web/protocol.js").read_bytes()).hexdigest()
    )
    return report


def test_review_controller_binding_uncertainty_and_context(tmp_path):
    driver(tmp_path, "logic")


def test_source_review_actual_http_original_key_and_no_new_requests(sealed, tmp_path):
    store, settings, original, sidecar, calls = sealed
    before, side = snapshot(store), sidecar.read_bytes()
    with store.engine.connect() as c:
        run_before = dict(c.execute(select(runs)).mappings().one())
        result_before = c.execute(select(protocol_jobs.c.result_snapshot)).scalar_one()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(32)
    (tmp_path / "http-info.json").write_text(
        json.dumps(
            dict(
                base=f"http://127.0.0.1:{listener.getsockname()[1]}",
                project=original["project"],
                run=original["run"],
            )
        )
    )
    server = uvicorn.Server(
        uvicorn.Config(create_app(store, settings), log_level="error", access_log=False)
    )
    initial_threads = set(threading.enumerate())
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=False)
    thread.start()
    cleanup = {}
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        report = driver(tmp_path, "http")
        after = snapshot(store)
        assert {name for name in before if before[name] != after[name]} == {
            "runs",
            "events",
            "protocol_reviews",
        }
        assert len(after["protocol_reviews"]) == 1
        assert len(after["events"]) == len(before["events"]) + 1
        with store.engine.connect() as c:
            run_after = dict(c.execute(select(runs)).mappings().one())
            assert {key for key in run_before if run_before[key] != run_after[key]} == {
                "status",
                "version",
            }
            assert c.execute(select(protocol_jobs.c.result_snapshot)).scalar_one() == result_before
        assert sidecar.read_bytes() == side and not calls
        (tmp_path / "accounting.json").write_text(
            json.dumps(
                dict(
                    status="PASS",
                    model_calls=calls,
                    new_mock=0,
                    new_worker=0,
                    accounting_tables_unchanged=True,
                    original_sidecar_unchanged=True,
                    original_result_unchanged=True,
                    original_deadlines_unchanged=True,
                    changed_tables=["runs", "events", "protocol_reviews"],
                    checks=report["checks"],
                    clock="synthetic business time; not G0/real-clock qualification",
                ),
                indent=2,
            )
        )
    finally:
        deadline = time.monotonic() + 10
        server.should_exit = True
        thread.join(max(0, deadline - time.monotonic()))
        for worker in set(threading.enumerate()) - initial_threads:
            if worker.name == "AnyIO worker thread":
                worker.join(max(0, deadline - time.monotonic()))
        listener.close()
        cleanup = dict(
            api_stopped=not thread.is_alive(),
            remaining_threads=[
                worker.name
                for worker in set(threading.enumerate()) - initial_threads
                if worker.is_alive()
            ],
        )
        (tmp_path / "cleanup.json").write_text(json.dumps(cleanup, indent=2))
        assert cleanup == dict(api_stopped=True, remaining_threads=[])


@pytest.mark.parametrize("change", ["version", "contract", "fingerprint", "revoke"])
def test_review_entry_real_backend_rejection_has_no_writes(sealed, change):
    store, settings, original, sidecar, calls = sealed
    headers = {"Authorization": "Bearer secret test token"}
    path = f"/api/projects/{original['project']}/protocol/runs/{original['run']}"
    with TestClient(create_app(store, settings)) as client:
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        run = response.json()
        assert run["contract_id"] == "protocol.synthetic.a-source.v1"
        assert "gold_sha256" not in run and "rubric_sha256" not in run
        body = dict(
            contract_id=run["contract_id"],
            expected_version=run["version"],
            expected_fence=run["fence"],
            expected_result_fingerprint=run["result_fingerprint"],
            request_key="review-ui-reject",
        )
        if change == "version":
            body["expected_version"] += 1
        elif change == "contract":
            body["contract_id"] = "protocol.synthetic.b-source.v1"
        elif change == "fingerprint":
            body["expected_result_fingerprint"] = "0" * 64
        else:
            with store.tx() as c:
                c.execute(
                    update(grants)
                    .where(grants.c.project_id == original["project"])
                    .values(revoked=True)
                )
        before, raw = snapshot(store), sidecar.read_bytes()
        response = client.post(
            f"/api/internal/protocol/runs/{original['run']}/reviews", headers=headers, json=body
        )
        assert 400 <= response.status_code < 500
        assert snapshot(store) == before and sidecar.read_bytes() == raw and not calls
        with store.engine.connect() as c:
            assert c.execute(select(protocol_reviews)).first() is None
