"""Real create/select/material-save through served JS and authenticated ASGI, models=0."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_literal_directory import rows

from sim2act.db import projects, resources


@pytest.mark.parametrize("case", ["create-save", "late-manual", "late-identity"])
def test_project_create_selection_actual_http(env, tmp_path, case):
    store, settings, client, owner, other_owner, project, _ = env
    assert store.sqlite and store.test_only and settings.mode == "mock"
    other = store.project(owner, "Other owned project")
    foreign = store.project(other_owner, "Other identity project")
    with store.tx() as c:
        project_name = c.execute(select(projects.c.name).where(projects.c.id == project)).scalar_one()
    before = rows(store)
    info = dict(case=case, project=project, project_name=project_name, other=other,
                foreign=foreign, output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    process = None
    verified = 0
    proof = []
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/project_create_selection.cjs", str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "verify":
                    after = rows(store)
                    assert all(set(v).issubset(after[k]) for k, v in before.items())
                    changed = {k for k in after if before[k] != after[k]}
                    expected = {"projects", "principals", "grants"}
                    if case == "create-save":
                        expected.add("resources")
                    assert changed == expected
                    with store.tx() as c:
                        created = c.execute(select(projects).where(projects.c.id == request["created"])).mappings().one()
                        assert created["owner_id"] == owner and created["name"] == "新建 B 合成项目"
                        if case == "create-save":
                            material = c.execute(select(resources).where(resources.c.id == request["resource"])).mappings().one()
                            assert material["project_id"] == created["id"]
                            assert material["content"] == "city,amount\r\n杭州,9.25\r\n"
                    proof.append(dict(changed_tables=sorted(changed), original_rows_all_unchanged=True,
                        created_project=dict(created), project_a=project,
                        project_a_resources=[json.loads(r) for r in after["resources"] if json.loads(r)["project_id"] == project]))
                    verified += 1
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
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS" and verified == 1
        assert result["real_model_calls"] == result["worker_calls"] == 0
        for asset in result["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "backend": "synthetic SQLite", "case": case, "tables": len(before), "proof": proof,
            "existing_creation_grant_policy": "Unchanged server policy creates project runtime and own artifact.save_text grants; resource Save uses original authorization policy.",
            "real_model_calls": 0, "worker_calls": 0,
            "native_browser": "NOT_RUN", "pg": "NOT_RUN", "windows": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
