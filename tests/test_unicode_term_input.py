"""Served JSDOM event adapters and actual synthetic HTTP, never native IME."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_goal_text_applications import confirm, generate, release_instance, setup
from test_literal_directory import rows
from test_persistent_app_runs import NoModel

from sim2act.db import Store, internal_instance_data
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["events", "use"])
def test_unicode_term_input_actual_http(env, tmp_path, scenario):
    store, settings, client, owner, _, project, _ = env
    mock_calls, app, release, instance = [], None, None, None
    if scenario == "use":
        data = setup(env)
        store, settings, client, owner, project, _, _ = data
        generation, result, mock_calls = generate(data)
        assert len(mock_calls) == 2
        app, _ = confirm(data, generation, result)
        release, instance = release_instance(data, app)
    csv_app = client.post(f"/api/projects/{project}/apps/csv-preview", json={
        "name": "CSV inactive term check", "resource_id": env[6], "goal": "Synthetic sum",
    }).json()["id"] if scenario == "use" else None
    baseline = rows(store)
    authority = {name: baseline[name] for name in ["principals", "grants"]}
    info = dict(scenario=scenario, app=app, csv_app=csv_app, project=project,
                instance=instance["id"] if instance else None, output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    worked, checkpoints, process = 0, 0, None
    stderr = tmp_path / "node.stderr"

    def cold_worker():
        cold = Store(settings.database_url, test_only=True)
        try:
            assert Worker(cold, settings, NoModel()).once()
        finally:
            cold.engine.dispose()

    try:
        with stderr.open("w") as errors:
            process = subprocess.Popen(["node", "tests/unicode_term_input.cjs", str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command in ["worker", "checkpoint", "readonly"]:
                    if command == "worker":
                        cold_worker()
                        worked += 1
                    current = rows(store)
                    assert all(current[name] == expected for name, expected in authority.items())
                    if command == "readonly":
                        assert current == baseline
                    else:
                        assert scenario == "use"
                        baseline = current
                    checkpoints += 1
                    answer = dict(status=200, text="{}")
                else:
                    response = client.request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=response.status_code, text=response.text,
                                  content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, stderr.read_text()
        proof = json.loads((tmp_path / "result.json").read_text())
        assert proof["status"] == "PASS" and worked == (3 if scenario == "use" else 0)
        assert rows(store) == baseline and checkpoints >= 2
        for asset in proof["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        server_rejection = None
        if scenario == "use":
            for run, term in zip(proof["run_ids"], ["中" * 80, "😀" * 80, "中😀" * 40], strict=True):
                response = client.get(f"/api/internal/instances/{instance['id']}/runs/{run}")
                assert response.status_code == 200
                actual = response.json()
                assert actual["status"] == "SUCCEEDED" and actual["result"]["term"] == term
                assert actual["result"]["citations"] == []
            assert rows(store) == baseline
            accepted = client.post(f"/api/internal/instances/{instance['id']}/runs", json={
                "expected_revision": instance["revision"], "expected_release_fingerprint": release["fingerprint"],
                "input": {"term": "😀" * 81}, "request_key": "explicit-server-boundary-81",
            })
            assert accepted.status_code == 202, accepted.text
            cold_worker()
            rejected = client.get(f"/api/internal/instances/{instance['id']}/runs/{accepted.json()['run_id']}")
            assert rejected.status_code == 200
            server_rejection = rejected.json()
            assert server_rejection["status"] == "FAILED" and server_rejection["error"]["code"] == "INVALID_INPUT"
            assert server_rejection["result"] is None and server_rejection["result_version"] is None
            with store.tx() as connection:
                versions = list(connection.execute(select(internal_instance_data.c.version).where(
                    internal_instance_data.c.instance_id == instance["id"]
                ).order_by(internal_instance_data.c.version)).scalars())
            assert versions == [1, 2, 3]
            assert all(rows(store)[name] == expected for name, expected in authority.items())
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "backend": "SQLite synthetic", "tables": len(baseline), "checkpoints": checkpoints,
            "authority_unchanged": True, "cold_worker_runs_from_page": worked,
            "server81_bypass_worker_runs": int(scenario == "use"), "server81_actual_result": server_rejection,
            "generation_mock_transport_calls": len(mock_calls), "runtime_model_calls": 0,
            "native_ime_and_clipboard": "NOT_RUN", "native_browser": "NOT_RUN", "pg": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if scenario == "use":
            client.close()
