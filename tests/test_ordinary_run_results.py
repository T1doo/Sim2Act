"""Ordinary goal to real registered-tool artifact; scripted mock, not semantic acceptance."""

import csv
import hashlib
import io
import json
import os
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from test_literal_directory import rows

from sim2act.db import Store, grants, operation_intents, operations, run_contracts, runs
from sim2act.model import MockModel
from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["deliver", "navigation", "revocation", "workspace-return"])
def test_ordinary_goal_results_actual_tools_and_page(env, tmp_path, case):
    store, settings, client, owner, other_owner, project, material = env
    assert store.sqlite and store.test_only and settings.mode == "mock" and not settings.live_enabled
    other = store.project(owner, "Other owned project")
    store.project(other_owner, "Other identity project")
    source = client.get(f"/api/resources/{material}").json()
    table = list(csv.DictReader(io.StringIO(source["content"])))
    expected_sum = str(sum((Decimal(row["amount"]) for row in table), Decimal(0)))
    assert expected_sum == "4.00" and len(table) == 2
    marker = '<script>window.artifactExecuted=true</script>'
    report = f"# 合成金额汇总😀\r\n金额合计：{expected_sum}\r\n记录数：{len(table)}\r\n{marker}\r\n"
    final_answer = f'合成工程结果：合计{expected_sum}，共{len(table)}条，报告已保存。<img src=x onerror="window.answerExecuted=true">'
    client.post(f"/api/projects/{project}/resources", json={
        "name": "Run artifact", "format": "md", "content": "UNSELECTED_SAME_NAME_NOT_THE_RESULT",
    }).raise_for_status()
    initial = rows(store)
    info = dict(case=case, project=project, other=other, material=material,
                answer=final_answer, report=report, output=str(tmp_path / "result.json"))
    (tmp_path / "info.json").write_text(json.dumps(info))
    process = None
    worker_runs = mock_requests = readonly_checks = 0
    proof = {}
    after_work = None
    revoked = []
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/ordinary_run_results.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "worker":
                    class ScriptedFixture(MockModel):
                        def request(self, messages, tools):
                            nonlocal mock_requests
                            mock_requests += 1
                            feedback = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
                            calls = [("resource.read", {"resource_id": material}),
                                     ("data.aggregate_csv", {"resource_id": material, "column": "amount"})]
                            if len(feedback) == 2:
                                data = feedback[-1]["data"]
                                assert data["sum"] == expected_sum and data["count"] == len(table)
                                calls.append(("artifact.save_text", {"text": report}))
                            if len(feedback) < 3:
                                name, arguments = calls[len(feedback)]
                                message = {"role": "assistant", "content": "SCRIPTED_MOCK_ENGINEERING_ONLY",
                                    "tool_calls": [{"id": f"fixture-{len(feedback)}", "type": "function",
                                        "function": {"name": name, "arguments": json.dumps(arguments)}}]}
                                reason = "tool_calls"
                            else:
                                message = {"role": "assistant", "content": final_answer}
                                reason = "stop"
                            return {"model": "MOCK-intern-contract", "usage": None,
                                    "choices": [{"finish_reason": reason, "message": message}]}

                    cold = Store(settings.database_url, test_only=True)
                    try:
                        assert Worker(cold, settings, ScriptedFixture()).once()
                    finally:
                        cold.engine.dispose()
                    worker_runs += 1
                    actual = client.get(f"/api/runs/{request['run']}")
                    assert actual.status_code == 200
                    actual = actual.json()
                    assert actual["status"] == "PARTIAL" and actual["result"]["answer"] == final_answer
                    assert actual["result"]["mode"] == "MOCK" and actual["result"]["goal_acceptance"] == "NOT_RUN"
                    with store.tx() as c:
                        run = dict(c.execute(select(runs).where(runs.c.id == request["run"])).mappings().one())
                        contract = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == run["id"])).scalar_one()
                        ops = [dict(r) for r in c.execute(select(operations).where(operations.c.run_id == run["id"])).mappings()]
                        intents = [c.execute(select(operation_intents.c.request).where(
                            operation_intents.c.operation_id == op["id"])).scalar_one() for op in ops]
                    assert run["resource_refs"] == contract["goal"]["resource_refs"] == [material]
                    assert sorted(op["tool_ref"] for op in ops) == ["artifact.save_text", "data.aggregate_csv", "resource.read"]
                    assert all(op["status"] == "VERIFIED" for op in ops)
                    saved = next(op["receipt"] for op in ops if op["tool_ref"] == "artifact.save_text")
                    artifact = saved["data"]["resource_id"]
                    data = client.get(f"/api/resources/{artifact}").json()
                    assert data["content"] == report and data["hash"] == hashlib.sha256(report.encode()).hexdigest()
                    assert data["format"] == "md" and data["project_id"] == project
                    assert mock_requests == 4
                    after = rows(store)
                    assert after["principals"] == initial["principals"]
                    assert len(after["resources"]) == len(initial["resources"]) + 1
                    assert set(initial["grants"]).issubset(after["grants"])
                    second = client.post(f"/api/projects/{project}/runs", json={
                        "goal": "Another explicitly queued fixture, never executed", "resource_refs": [], "request_key": "other-queued",
                    })
                    assert second.status_code == 202
                    after_work = rows(store)
                    proof = dict(run=run, contract=contract, operations=ops, intents=intents,
                        actual_run=actual, artifact=data, independent_oracle={"sum": expected_sum, "count": len(table)},
                        setup_other_run=second.json()["run_id"], fixture_save_policy="Original artifact.save_text derived resource.read Grants")
                    answer = dict(status=200, text=json.dumps({"run": actual, "artifact": data, "other_run": second.json()["run_id"]}))
                elif command == "revoke-artifact":
                    assert after_work is not None and not revoked
                    with store.tx() as c:
                        grant = dict(c.execute(select(grants).where(grants.c.principal_id == owner,
                            grants.c.resource_id == proof["artifact"]["id"], grants.c.tool_ref == "resource.read")).mappings().one())
                    reply = client.post(f"/api/grants/{grant['id']}/revoke", json={"command": "revoke", "version": grant["revision"]})
                    assert reply.status_code == 200
                    revoked.append(rows(store))
                    assert all(revoked[0][name] == values for name, values in after_work.items() if name != "grants")
                    answer = dict(status=200, text=reply.text)
                elif command == "verify-readonly":
                    assert rows(store) == (revoked[0] if revoked else after_work)
                    assert worker_runs == 1 and mock_requests == 4
                    readonly_checks += 1
                    answer = dict(status=200, text="{}")
                else:
                    reply = client.request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=reply.status_code, text=reply.text, content_type=reply.headers.get("content-type"))
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS" and readonly_checks == 1
        for asset in result["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "case": case, "tables": len(initial), "worker_runs": worker_runs, "synthetic_model_requests": mock_requests,
            "real_model_requests": 0, "readonly_checks": readonly_checks, "actual_fixture_revocations": len(revoked),
            "proof": proof, "semantic_goal_acceptance": "NOT_RUN", "pg": "NOT_RUN", "native_browser": "NOT_RUN",
        }, indent=2) + "\n")
