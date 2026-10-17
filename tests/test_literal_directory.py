"""Saved literal directory over real ASGI HTTP/JSDOM and cold NoModel Worker."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_goal_text_applications import CONTENT, confirm, generate, release_instance, setup
from test_persistent_app_runs import NoModel

from sim2act.db import Store, grants, internal_app_runs, internal_instance_data, meta
from sim2act.worker import Worker


def rows(store):
    with store.tx() as connection:
        return {table.name: sorted(json.dumps(dict(row), sort_keys=True, default=str)
                for row in connection.execute(select(table)).mappings())
                for table in meta.sorted_tables}


@pytest.mark.parametrize("scenario", ["use", "guards"])
def test_saved_literal_directory_actual_http(env, tmp_path, scenario):
    data = setup(env)
    store, settings, client, owner, project, resource, _ = data
    assert store.sqlite and store.test_only and settings.mode == "mock"
    generation, result, mock_calls = generate(data)
    assert len(mock_calls) == 2
    aid, _ = confirm(data, generation, result)
    release, instance = release_instance(data, aid)
    csv_app = env[2].post(f"/api/projects/{project}/apps/csv-preview", json={
        "name": "Different CSV type", "resource_id": env[6], "goal": "Synthetic sum",
    }).json()["id"]
    other = store.project(owner, "Other owned project")
    store.project(env[4], "Other identity project")
    baseline = rows(store)
    authority = {name: baseline[name] for name in ("principals", "grants")}
    catalog = client.get("/api/apps?metadata_only=true")
    assert catalog.status_code == 200
    summary = next(item for item in catalog.json()["items"] if item["id"] == aid)
    assert summary == dict(id=aid, name="Literal app", project_id=project,
                          csv_instance_candidate=False, use_family="LITERAL_TEXT")
    assert CONTENT not in catalog.text and "candidate" not in summary and "goal" not in summary
    foreign = client.get("/api/apps?metadata_only=true", headers={"Authorization": "Bearer synthetic-test-B"})
    assert foreign.status_code == 200 and all(item["id"] != aid for item in foreign.json()["items"])
    assert client.get(f"/api/apps/{aid}", headers={"Authorization": "Bearer synthetic-test-B"}).status_code == 403
    assert rows(store) == baseline
    info = dict(project=project, other=other, app=aid, csv_app=csv_app,
                instance=instance["id"], release=release["id"], scenario=scenario,
                output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    worked, checkpoints, revocations = 0, 0, 0
    stderr = tmp_path / "node.stderr"
    process = None
    try:
        with stderr.open("w") as errors:
            process = subprocess.Popen(["node", "tests/literal_directory.cjs", str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "worker":
                    cold = Store(settings.database_url, test_only=True)
                    try:
                        assert Worker(cold, settings, NoModel()).once()
                    finally:
                        cold.engine.dispose()
                    worked += 1
                    baseline = rows(store)
                    assert all(baseline[name] == expected for name, expected in authority.items())
                    answer = dict(status=200, text="{}")
                elif command == "readonly":
                    assert rows(store) == baseline
                    checkpoints += 1
                    answer = dict(status=200, text="{}")
                elif command == "revoke":
                    assert scenario == "guards" and revocations == 0
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
        assert worked == (2 if scenario == "use" else 0) and checkpoints >= 2
        assert revocations == int(scenario == "guards") and rows(store) == baseline
        with store.tx() as connection:
            typed = connection.execute(select(internal_app_runs).where(
                internal_app_runs.c.instance_id == instance["id"]
            ).order_by(internal_app_runs.c.result_version)).mappings().all()
            records = connection.execute(select(internal_instance_data).where(
                internal_instance_data.c.instance_id == instance["id"]
            ).order_by(internal_instance_data.c.version)).mappings().all()
        assert len(typed) == len(records) == worked
        if worked:
            assert [row["input"]["term"] for row in typed] == ["Alpha", "Beta"]
            assert [row["version"] for row in records] == [1, 2]
            assert [c["quote"] for c in records[0]["data"]["result"]["citations"]] == [
                "Alpha obligation retained", "Alpha owner undecided"]
            assert [c["quote"] for c in records[1]["data"]["result"]["citations"]] == [
                "Beta due tomorrow", "<em>Beta literal</em>"]
        for asset in proof["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "backend": "SQLite synthetic", "tables": len(baseline), "read_checkpoints": checkpoints,
            "all_get_rows_unchanged": True, "cold_worker_runs": worked,
            "new_result_versions": [row["version"] for row in records],
            "authority_unchanged_except_explicit_revoke": True, "controlled_revocations": revocations,
            "generation_mock_transport_calls": len(mock_calls), "runtime_model_calls": 0,
            "real_model": "NOT_RUN", "pg": "NOT_RUN", "native_browser": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        client.close()
