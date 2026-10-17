"""Saved closed text directory through actual ASGI/JSDOM and cold NoModel Worker."""

import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import insert, select
from test_literal_directory import rows
from test_text_workflows import NoModel, draft, instance

from sim2act.db import (
    Store,
    app_drafts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    new_id,
)
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["use", "guards"])
def test_saved_closed_text_directory_actual_http(env, tmp_path, scenario):
    store, settings, client, owner, _, project, resource = env
    assert store.sqlite and store.test_only and settings.mode == "mock"
    made, body = draft(env)
    aid = made["id"]
    release, saved = instance(env, aid)
    second = client.post(f"/api/internal/releases/{release['id']}/instances", json={
        "expected_release_fingerprint": release["fingerprint"], "request_key": "second-directory-instance",
    })
    assert second.status_code == 201, second.text
    csv_reply = client.post(f"/api/projects/{project}/apps/csv-preview", json={
        "name": "Different CSV type", "resource_id": resource, "goal": "Synthetic sum",
    })
    assert csv_reply.status_code == 201
    other = store.project(owner, "Other owned project")
    # Deliberately invalid, synthetic catalog rows: never inspected/opened or executed.
    unsupported = []
    with store.tx() as c:
        original = dict(c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one())
        for field in ("namespace", "check"):
            row = copy.deepcopy(original)
            row["id"] = new_id("app")
            row["name"] = "Unsupported synthetic " + field
            if field == "namespace":
                row["candidate"]["namespace"] = "closed-text-four-step.v999"
            else:
                row["candidate"]["manifest"]["validation_suite_ref"] = "unknown.text.check.v1"
            row["fingerprint"] = fingerprint(row["candidate"])
            c.execute(insert(app_drafts).values(**row))
            unsupported.append(row["id"])
    baseline = rows(store)
    authority = {name: baseline[name] for name in ("principals", "grants")}
    catalog = client.get("/api/apps?metadata_only=true")
    assert catalog.status_code == 200
    items = {item["id"]: item for item in catalog.json()["items"]}
    assert items[aid] == dict(id=aid, name="Actual two-search task", project_id=project,
                             csv_instance_candidate=False, use_family="CLOSED_TEXT_WORKFLOW")
    assert all(items[i]["use_family"] == "OTHER" and items[i]["csv_instance_candidate"] is False
               for i in unsupported)
    assert all("candidate" not in item and "goal" not in item for item in items.values())
    foreign = client.get("/api/apps?metadata_only=true", headers={"Authorization": "Bearer synthetic-test-B"})
    assert foreign.status_code == 200 and all(item["id"] != aid for item in foreign.json()["items"])
    assert client.get(f"/api/apps/{aid}", headers={"Authorization": "Bearer synthetic-test-B"}).status_code == 403
    assert rows(store) == baseline
    info = dict(project=project, other=other, app=aid, csv_app=csv_reply.json()["id"],
                unsupported=unsupported, instance=saved["id"], second_instance=second.json()["id"],
                release=release["id"], scenario=scenario, output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    worked, checkpoints, revocations = 0, 0, 0
    stderr = tmp_path / "node.stderr"
    process = None
    try:
        with stderr.open("w") as errors:
            process = subprocess.Popen(["node", "tests/closed_text_directory.cjs", str(path)],
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
                    with store.tx() as c:
                        grant = c.execute(select(grants).where(grants.c.principal_id == owner,
                            grants.c.resource_id == body["resource_id"],
                            grants.c.tool_ref == "resource.read")).mappings().one()
                    response = client.post(f"/api/grants/{grant['id']}/revoke", json={
                        "command": "revoke", "version": grant["revision"],
                    })
                    assert response.status_code == 200
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
        assert proof["status"] == "PASS" and worked == (2 if scenario == "use" else 0)
        assert checkpoints >= 2 and revocations == int(scenario == "guards") and rows(store) == baseline
        with store.tx() as c:
            typed = c.execute(select(internal_app_runs).where(
                internal_app_runs.c.instance_id == saved["id"])).mappings().all()
            records = c.execute(select(internal_instance_data).where(
                internal_instance_data.c.instance_id == saved["id"])).mappings().all()
        assert len(typed) == worked and len(records) == int(worked > 0)
        if worked:
            assert sorted(row["status"] for row in typed) == ["PARTIAL", "SUCCEEDED"]
            result = records[0]["data"]["result"]
            assert records[0]["version"] == 1 and result["term_a"] == "Violet" and result["term_b"] == "Amber"
            assert [q["quote"] for q in result["citations_a"]] == ["Violet due Friday"]
            assert [q["quote"] for q in result["citations_b"]] == ["Amber assigned to Lee", "Amber review pending"]
        for asset in proof["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "backend": "SQLite synthetic", "tables": len(baseline), "read_checkpoints": checkpoints,
            "all_get_rows_unchanged": True, "cold_worker_runs": worked,
            "typed_run_statuses": sorted(row["status"] for row in typed),
            "new_result_versions": [row["version"] for row in records],
            "authority_unchanged_except_explicit_revoke": True, "controlled_revocations": revocations,
            "generation_model_calls": 0, "runtime_model_calls": 0,
            "real_model": "NOT_RUN", "pg": "NOT_RUN", "native_browser": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
