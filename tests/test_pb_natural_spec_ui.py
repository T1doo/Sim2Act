"""Visible P-B gestures through real HTTP, SQLite and cold Worker; synthetic only."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_natural_spec_apps import COLD, transport
from test_pb_natural_specs import prepare

from sim2act.api import create_app
from sim2act.db import Store
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["valid", "lost", "review-late-edit", "commit-late-navigation", "receipt-poison"])
def test_successful_task_visible_extraction_and_cold_reuse(env, tmp_path, scenario):
    prepared = prepare(env, edit=False)
    data, aid, rid, target_resource, goal, _, _, options = prepared
    info = tmp_path / "info.json"
    info.write_text(json.dumps(dict(project=data[4], app=aid, run=rid,
        instance=options["source_proof"]["instance_id"], source_name="Model chosen checklist", target=goal["id"],
        target_resource=target_resource, scenario=scenario, output=str(tmp_path / "results.json"))))
    process = subprocess.Popen(["node", "tests/pb_natural_spec_ui.cjs", str(info)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
    cold = cold_client = None
    sent = []
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command"):
                assert request["command"] == "cold-worker"
                cold = Store(data[1].database_url, test_only=True)
                cold_client = TestClient(create_app(cold, data[1]))
                cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                assert Worker(cold, data[1], goal_planner_transport=transport(sent, COLD)).once()
                answer = dict(id=request["id"], status=200, text="{}")
            else:
                reply = (cold_client or data[2]).request(request["method"], request["path"],
                    json=request.get("body"), headers=request.get("headers"))
                answer = dict(id=request["id"], status=reply.status_code, text=reply.text,
                              content_type=reply.headers.get("content-type"))
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        errors = process.stderr.read()
        code = process.wait(timeout=20)
        (tmp_path / "driver.log").write_text(errors)
        (tmp_path / "runtime-wire.json").write_text(json.dumps(sent, ensure_ascii=False, indent=2))
        assert code == 0, errors
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 12
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]}
        assert len(proof["loaded_source_sha256"]) == 20 and len(sent) == 1
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if cold_client:
            cold_client.close()
        if cold:
            cold.engine.dispose()
