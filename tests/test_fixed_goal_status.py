"""Project canvas projection of the existing prospective fixed goal evaluator, not a new oracle."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_fixed_goal_acceptance import prepared
from test_literal_directory import rows


@pytest.mark.parametrize("kind", ["read_preview", "sum_quantity_z"])
def test_existing_fixed_contract_status_visible_without_contradiction(env, tmp_path, kind):
    value, session, rid, sent, _, _, _ = prepared(env, kind=kind)
    store, settings, client, *_ = value
    assert store.test_only and store.sqlite and settings.mode == "mock" and not settings.live_enabled
    run = client.get(f"/api/runs/{rid}")
    assert run.status_code == 200
    run = run.json()
    assert run["status"] == "SUCCEEDED" and run["result"]["goal_acceptance"] == "PASS_FIXED_CONTRACT"
    report = run["result"]["task_acceptance"]
    assert report["scope"] == "EXACT_FIXED_SYNTHETIC_GOAL_ONLY" and report["whole_task_accepted"] is True
    assert report["general_semantic_acceptance"] == "NOT_RUN" and report["owner_acceptance"] == "PENDING"
    assert len(sent) == 1 and len(run["result"]["receipts"]) == 1
    before = rows(store)
    proof = dict(kind=kind, actual_run=run, session=session, synthetic_provider_requests=1,
                 real_model_requests=0, normal_worker_claims=2, actual_verified_tools=1,
                 scoped_fixed_goal_acceptance="PASS_FIXED_CONTRACT", general_semantics="NOT_RUN",
                 owner="PENDING", native_browser="NOT_RUN", pg="NOT_RUN")
    (tmp_path / "worker-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    info = dict(project=value[5], run=rid, kind=kind, output=str(tmp_path / "result.json"))
    (tmp_path / "info.json").write_text(json.dumps(info))
    process = None
    verified = 0
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/fixed_goal_status.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "verify-readonly":
                    assert rows(store) == before
                    verified += 1
                    answer = dict(status=200, text="{}")
                else:
                    assert request["method"] == "GET"
                    reply = client.get(request["path"], headers=request.get("headers"))
                    answer = dict(status=reply.status_code, text=reply.text,
                                  content_type=reply.headers.get("content-type"))
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS" and verified == 1
        for asset in result["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        assert rows(store) == before
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "kind": kind, "all_tables": len(before), "all_rows_unchanged_by_page": True,
            "readonly_checks": verified, "synthetic_provider_requests": len(sent),
            "real_model_requests": 0, "schema_or_permission_policy_changes": False,
        }, indent=2) + "\n")
        client.close()
