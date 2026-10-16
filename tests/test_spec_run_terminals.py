"""SQLite authenticated API/actual Worker proof, no real model or private diagnostics."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from test_pa_spec_apps import confirm, generate, instance, setup

from sim2act.api import create_app
from sim2act.db import (
    Store,
    fingerprint,
    internal_app_runs,
    internal_run_bindings,
    internal_spec_run_terminals,
    runs,
)
from sim2act.worker import Worker


def test_rejection_terminal_page_protocol(tmp_path):
    result = tmp_path / "terminal-protocol.json"
    process = subprocess.run(["node", "tests/rejection_terminal_protocol.cjs", str(result)],
        cwd=Path(__file__).parents[1], env={**os.environ,
            "NODE_PATH": "/workspace/node-tools/node_modules"},
        capture_output=True, text=True, timeout=40)
    (tmp_path / "protocol.stdout").write_text(process.stdout)
    (tmp_path / "protocol.stderr").write_text(process.stderr)
    assert process.returncode == 0, process.stderr
    proof = json.loads(result.read_text())
    assert proof["status"] == "PASS" and len(proof["checks"]) >= 24


def test_original_key_permanent_terminal(env, monkeypatch):
    data = setup(env)
    store, settings, client, user, pid, *_ = data
    rid, result, sent = generate(data)
    made = confirm(data, rid, result)
    assert made.status_code == 200, made.text
    release, inst = instance(data, made.json()["id"])
    prefix = f"/api/internal/instances/{inst['id']}"

    def request(key, revision=None):
        return dict(expected_revision=inst["revision"] if revision is None else revision,
            expected_release_fingerprint=release["fingerprint"], input={}, request_key=key)

    def close(body, actor=client):
        return actor.post(prefix + f"/spec-run-requests/{body['request_key']}/close",
            json=dict(release_id=release["id"], request=body))

    def read(key, actor=client):
        return actor.get(prefix + f"/spec-run-requests/{key}")

    def counts():
        with store.engine.connect() as c:
            return [c.execute(select(func.count()).select_from(t)).scalar_one()
                for t in (runs, internal_app_runs, internal_run_bindings)]

    baseline = counts()
    for key, revision, phase in [("rolled-back", 999, "TX_ROLLED_BACK"),
            ("validation", 0, "VALIDATION_NOT_STARTED")]:
        body = request(key, revision)
        rejected = client.post(prefix + "/runs", json=body)
        proof = rejected.json().get("submission_rejection") or rejected.json()["error"]["submission_rejection"]
        assert proof["phase"] == phase and proof["request_fingerprint"] == fingerprint(body)
        assert read(key).json()["error"]["code"] == "OUTCOME_UNKNOWN"
        response = close(body)
        assert response.status_code == 200, response.text
        receipt = read(key).json()
        assert receipt == response.json() and receipt["status"] == "CLOSED_NOT_ACCEPTED"
        assert receipt["request"] == body and receipt["wire_request_fingerprint"] == fingerprint(body)
        assert receipt["app_id"] == made.json()["id"] and receipt["principal_id"] == user
        assert close(body).json() == receipt
        assert client.post(prefix + "/runs", json=request(key)).status_code == 409
        assert close(request(key, 2)).status_code == 409
    assert counts() == baseline
    assert len(sent) == 3  # Only fixture generation uses the explicit mock transport.

    with TestClient(create_app(store, settings)) as foreign:
        foreign.headers["Authorization"] = "Bearer synthetic-test-B"
        assert close(request("wrong-owner"), foreign).status_code == 403
        assert read("rolled-back", foreign).status_code == 403
    invalid = request("unsupported")
    invalid["input"] = {"x": "not empty"}
    assert close(invalid).status_code == 400
    malformed = request("bad-wire")
    malformed["expected_revision"] = "invalid"
    assert close(malformed).status_code == 422
    assert read("bad-wire").json()["error"]["code"] == "OUTCOME_UNKNOWN"

    # Failure after insert must roll back the terminal; no partial success.
    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO internal_spec_run_terminals"):
            raise RuntimeError("synthetic terminal insert failure")
    event.listen(store.engine, "after_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic terminal insert failure"):
            close(request("failed-close"))
    finally:
        event.remove(store.engine, "after_cursor_execute", fail_insert)
    assert read("failed-close").json()["error"]["code"] == "OUTCOME_UNKNOWN" and counts() == baseline

    # Actual two-thread transactions, forced lock order in each direction. Each
    # second transaction enters while the winner still owns its project lock.
    for winner in ("close", "enqueue"):
        body = request("race-" + winner)
        entered, release_lock, second_started = Event(), Event(), Event()
        original_lock = store.lock_project
        first = [True]

        def gate(c, principal, project, _lock=original_lock, _first=first,
                _entered=entered, _release=release_lock):
            value = _lock(c, principal, project)
            if _first[0]:
                _first[0] = False
                _entered.set()
                assert _release.wait(10)
            return value

        def action(kind, body=body):
            if kind == "close":
                return close(body)
            return client.post(prefix + "/runs", json=body)

        monkeypatch.setattr(store, "lock_project", gate)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(action, winner)
                assert entered.wait(10)
                def second(_started=second_started, _winner=winner, _action=action):
                    _started.set()
                    return _action("enqueue" if _winner == "close" else "close")
                b = pool.submit(second)
                assert second_started.wait(10)
                release_lock.set()
                result_a, result_b = a.result(timeout=20), b.result(timeout=20)
        finally:
            release_lock.set()
            monkeypatch.setattr(store, "lock_project", original_lock)
        assert result_a.status_code == (200 if winner == "close" else 202), result_a.text
        assert result_b.status_code == (409 if winner == "close" else 400), result_b.text
        receipt = read(body["request_key"])
        assert receipt.status_code == 200, receipt.text
        if winner == "enqueue":
            assert receipt.json()["namespace"] == "spec-run-request.v1"
            assert Worker(store, settings).once()
            assert read(body["request_key"]).json()["status"] == "SUCCEEDED"
        else:
            assert receipt.json()["namespace"] == "spec-run-terminal.v1"

    # A new Store/app over the same committed SQLite DB recovers metadata without
    # initialization, old revision execution, or model calls.
    restarted = Store(str(store.engine.url), test_only=True)
    try:
        with TestClient(create_app(restarted, settings)) as fresh:
            fresh.headers["Authorization"] = "Bearer synthetic-test-A"
            assert read("rolled-back", fresh).json()["status"] == "CLOSED_NOT_ACCEPTED"
            assert fresh.post(prefix + "/runs", json=request("rolled-back")).status_code == 409
    finally:
        restarted.engine.dispose()
    # Fresh OS process: no parent Store, engine, app or Python module cache.
    child = subprocess.run([sys.executable, "-c", """
import json, sys
from pathlib import Path
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
payload = json.load(sys.stdin)
store = Store(payload['url'], test_only=True)
try:
    with TestClient(create_app(store, Settings(payload['url'], Path(payload['root']), mode='mock'))) as client:
        client.headers['Authorization'] = 'Bearer synthetic-test-A'
        receipt = client.get(payload['prefix'] + '/spec-run-requests/rolled-back')
        late = client.post(payload['prefix'] + '/runs', json=payload['request'])
        print(json.dumps(dict(read_status=receipt.status_code, receipt=receipt.json(), late_status=late.status_code)))
finally:
    store.engine.dispose()
"""], input=json.dumps(dict(url=str(store.engine.url), root=str(settings.data_dir),
        prefix=prefix, request=request("rolled-back"))), capture_output=True, text=True,
        cwd=Path(__file__).parents[1], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=30)
    (settings.data_dir / "restart-process.stdout").write_text(child.stdout)
    (settings.data_dir / "restart-process.stderr").write_text(child.stderr)
    assert child.returncode == 0, child.stderr
    restarted_receipt = json.loads(child.stdout)
    assert restarted_receipt["read_status"] == 200 and restarted_receipt["late_status"] == 409
    assert restarted_receipt["receipt"] == read("rolled-back").json()
    with store.engine.connect() as c:
        assert c.execute(select(func.count()).select_from(internal_spec_run_terminals)).scalar_one() == 3
