"""Explicit ordinary Run material selection over real ASGI/JS and a mock Worker."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_literal_directory import rows

from sim2act.db import Store, operation_intents, operations, run_contracts, runs
from sim2act.model import MockModel
from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["use", "refresh", "frozen"])
def test_ordinary_run_explicit_materials_actual_http(env, tmp_path, case):
    store, settings, client, owner, other_owner, project, _ = env
    assert store.sqlite and store.test_only and settings.mode == "mock" and not settings.live_enabled
    other = store.project(owner, "Other owned project")
    store.project(other_owner, "Other identity project")
    catalog = client.get(f"/api/projects/{project}/resources").json()
    materials = [{**catalog[0], "content": client.get(f"/api/resources/{catalog[0]['id']}").json()["content"]}]
    for index in range(1, 9):
        content = f"合成独立材料 {index}：ONLY_MATERIAL_{index}"
        body = dict(name=f"material-{index}.txt", format="txt", content=content)
        reply = client.post(f"/api/projects/{project}/resources", json=body)
        assert reply.status_code == 201
        materials.append({**body, "id": reply.json()["id"]})
    before = rows(store)
    info = dict(case=case, project=project, other=other, materials=materials,
                output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    worked = mock_requests = fixture_writes = checkpoints = 0
    process = None
    proof = []
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/ordinary_run_materials.cjs", str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "rejected-readonly":
                    assert rows(store) == before
                    (tmp_path / "rejected-database-proof.json").write_text(json.dumps({
                        "tables": len(before), "all_rows_unchanged": True,
                        "nine_materials": [m["id"] for m in materials], "run_count": len(before["runs"]),
                    }, indent=2) + "\n")
                    answer = dict(status=200, text="{}")
                elif command == "new-material":
                    reply = client.post(f"/api/projects/{project}/resources", json={
                        "name": "new-tenth.txt", "format": "txt", "content": "NEW_TENTH_MUST_NOT_BE_SELECTED",
                    })
                    assert reply.status_code == 201 and fixture_writes == 0
                    fixture_writes += 1
                    answer = dict(status=200, text=reply.text)
                elif command == "worker":
                    class OnlyMock(MockModel):
                        def request(self, messages, tools):
                            nonlocal mock_requests
                            mock_requests += 1
                            return super().request(messages, tools)

                    cold = Store(settings.database_url, test_only=True)
                    try:
                        assert Worker(cold, settings, OnlyMock()).once()
                    finally:
                        cold.engine.dispose()
                    worked += 1
                    with store.tx() as c:
                        run = c.execute(select(runs).where(runs.c.id == request["run"])).mappings().one()
                        contract = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == run["id"])).scalar_one()
                        ops = c.execute(select(operations).where(operations.c.run_id == run["id"])).mappings().all()
                    assert run["resource_refs"] == contract["goal"]["resource_refs"] == [request["resource"]]
                    assert [r["resource_id"] for r in contract["resources"]] == [request["resource"]]
                    assert len(ops) == 1 and ops[0]["tool_ref"] == "resource.read" and ops[0]["status"] == "VERIFIED"
                    with store.tx() as c:
                        intent = c.execute(select(operation_intents.c.request).where(
                            operation_intents.c.operation_id == ops[0]["id"])).scalar_one()
                    assert intent["args"]["resource_id"] == request["resource"]
                    proof.append(dict(run_id=run["id"], status=run["status"], resource_refs=run["resource_refs"],
                        contract=contract, operations=[dict(op) for op in ops], operation_intent=intent))
                    answer = dict(status=200, text="{}")
                elif command == "verify":
                    after = rows(store)
                    assert after["principals"] == before["principals"]
                    if not fixture_writes:
                        assert after["grants"] == before["grants"] and after["resources"] == before["resources"]
                    else:
                        assert set(before["grants"]).issubset(after["grants"])
                        assert len(after["resources"]) == len(before["resources"]) + 1
                    assert len(after["runs"]) - len(before["runs"]) == (case != "refresh")
                    assert worked == (case == "use")
                    assert mock_requests == (2 if case == "use" else 0)
                    checkpoints += 1
                    answer = dict(status=200, text="{}")
                else:
                    reply = client.request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=reply.status_code, text=reply.text,
                        content_type=reply.headers.get("content-type"))
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS" and checkpoints == 1
        for asset in result["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "case": case, "tables": len(before), "source_materials": len(materials),
            "normal_cold_mock_worker_runs": worked, "synthetic_model_requests": mock_requests,
            "real_model_requests": 0, "fixture_resource_saves": fixture_writes,
            "fixture_save_grants": "Original resource Save policy; no new permission semantics.",
            "principals_unchanged": True, "proof": proof,
            "native_browser": "NOT_RUN", "pg": "NOT_RUN", "semantic_goal_acceptance": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
