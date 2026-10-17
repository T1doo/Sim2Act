"""Actual synthetic ASGI HTTP and cold Worker; JSDOM captures Blob bytes only."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
import test_goal_text_applications as literal
from sqlalchemy import select
from test_literal_directory import rows
from test_persistent_app_runs import NoModel

from sim2act.db import Store, grants
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["bytes", "navigation", "revocation"])
def test_literal_result_download_actual_http(env, tmp_path, monkeypatch, scenario):
    monkeypatch.setattr(literal, "CONTENT", literal.CONTENT + "Alpha 中文完整引文 ✓\n")
    data = literal.setup(env)
    store, settings, client, owner, project, resource, _ = data
    assert store.sqlite and store.test_only and settings.mode == "mock"
    generation, result, mock_calls = literal.generate(data)
    assert len(mock_calls) == 2
    app, _ = literal.confirm(data, generation, result)
    release, instance = literal.release_instance(data, app)
    other_instance = client.post(f"/api/internal/releases/{release['id']}/instances", json={
        "expected_release_fingerprint": release["fingerprint"], "request_key": "other-instance",
    }).json()
    outputs = []
    for term in ("Alpha", "Beta", "Absent"):
        accepted = client.post(f"/api/internal/instances/{instance['id']}/runs", json={
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "input": {"term": term}, "request_key": term,
        })
        assert accepted.status_code == 202, accepted.text
        cold = Store(settings.database_url, test_only=True)
        try:
            assert Worker(cold, settings, NoModel()).once()
        finally:
            cold.engine.dispose()
        response = client.get(f"/api/internal/instances/{instance['id']}/runs/{accepted.json()['run_id']}")
        assert response.status_code == 200, response.text
        outputs.append(response.json())
    assert [r["status"] for r in outputs] == ["SUCCEEDED"] * 3
    assert [r["result_version"] for r in outputs] == [1, 2, 3]
    assert [c["quote"] for c in outputs[0]["result"]["citations"]] == [
        "Alpha obligation retained", "Alpha owner undecided", "Alpha 中文完整引文 ✓"]
    assert [c["quote"] for c in outputs[1]["result"]["citations"]] == [
        "Beta due tomorrow", "<em>Beta literal</em>"]
    assert outputs[2]["result"]["citations"] == []
    other = store.project(owner, "Other owned project")
    store.project(env[4], "Other identity project")
    baseline = rows(store)
    info = dict(project=project, other=other, app=app, instance=instance["id"],
                other_instance=other_instance["id"], scenario=scenario, outputs=outputs,
                output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    stderr = tmp_path / "node.stderr"
    process, checkpoints, revocations = None, 0, 0
    try:
        with stderr.open("w") as errors:
            process = subprocess.Popen(["node", "tests/literal_result_download.cjs", str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "readonly":
                    assert rows(store) == baseline
                    checkpoints += 1
                    answer = dict(status=200, text="{}")
                elif command == "revoke":
                    assert scenario == "revocation" and revocations == 0
                    with store.tx() as connection:
                        grant = connection.execute(select(grants).where(
                            grants.c.principal_id == owner, grants.c.resource_id == resource,
                            grants.c.tool_ref == "resource.read",
                        )).mappings().one()
                    response = client.post(f"/api/grants/{grant['id']}/revoke", json={
                        "command": "revoke", "version": grant["revision"],
                    })
                    assert response.status_code == 200, response.text
                    current = rows(store)
                    assert all(current[name] == value for name, value in baseline.items() if name != "grants")
                    baseline = current
                    revocations += 1
                    answer = dict(status=response.status_code, text=response.text)
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
        assert proof["status"] == "PASS"
        assert checkpoints >= 2 and revocations == int(scenario == "revocation")
        assert rows(store) == baseline
        for asset in proof["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        for captured in tmp_path.glob("captured-blob-*.json"):
            value = json.loads(captured.read_bytes())
            original = next(r for r in outputs if r["id"] == value["run_id"])
            assert value == {"instance_id": instance["id"], "run_id": original["id"],
                "release_id": release["id"], "result_version": original["result_version"],
                "result": original["result"]}
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "backend": "SQLite synthetic", "tables": len(baseline), "read_checkpoints": checkpoints,
            "download_get_rows_unchanged": True, "cold_worker_runs": 3,
            "result_versions": [1, 2, 3], "controlled_revocations": revocations,
            "authority_unchanged_except_explicit_revoke": True,
            "generation_mock_transport_calls": len(mock_calls), "runtime_model_calls": 0,
            "real_model": "NOT_RUN", "pg": "NOT_RUN", "native_browser": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        client.close()
