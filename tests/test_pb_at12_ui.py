"""Visible P-B gestures through real HTTP, SQLite and cold Worker; synthetic only."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, insert, select
from test_natural_spec_apps import transport
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD, prepared_use

from sim2act.api import create_app
from sim2act.db import Store, grants, internal_instance_data, internal_run_bindings, new_id, runs


@pytest.mark.parametrize("scenario", ["invalid", "schema", "auth-change", "default-invalid", "lost", "commit-late-navigation", "receipt-poison", "late-invalid", "late-default-invalid"])
def test_at12_rejected_correction_and_original_key_recovery(env, tmp_path, scenario):
    data, app, release, inst, target_resource, goal, body, route = prepared_use(env, run_base=True)
    aid = app["id"]
    info = tmp_path / "info.json"
    info.write_text(json.dumps(dict(project=data[4], app=aid, name=app["name"],
        instance=inst["id"], target=goal["id"],
        target_resource=target_resource, scenario=scenario, output=str(tmp_path / "results.json"))))
    process = subprocess.Popen(["node", "tests/pb_at12_ui.cjs", str(info)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
    cold = cold_client = None
    sent = []
    auth_grant = None
    with data[0].tx() as c:
        old_rows = [dict(r) for r in c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])).mappings()]
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command"):
                if request["command"] in ("change-auth", "restore-auth"):
                    with data[0].tx() as c:
                        if request["command"] == "change-auth":
                            auth_grant = new_id("grant")
                            c.execute(insert(grants).values(id=auth_grant, principal_id=inst["runtime_id"], project_id=data[4], resource_id=target_resource, tool_ref="resource.read", expires_at=9999999999, revoked=False))
                        else:
                            c.execute(delete(grants).where(grants.c.id == auth_grant))
                    answer = dict(id=request["id"], status=200, text="{}")
                    process.stdin.write(json.dumps(answer) + "\n")
                    process.stdin.flush()
                    continue
                assert request["command"] == "cold-worker"
                cold = Store(data[1].database_url, test_only=True)
                cold_client = TestClient(create_app(cold, data[1]))
                cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                with cold.tx() as c:
                    own = c.execute(select(runs.c.principal_id, runs.c.project_id,
                        internal_run_bindings.c.snapshot["instance_id"].as_string().label("instance"))
                        .join(internal_run_bindings, internal_run_bindings.c.run_id == runs.c.id)
                        .where(runs.c.id == request["run_id"])).mappings().one()
                    assert own["principal_id"] == data[3] and own["project_id"] == data[4]
                    assert own["instance"] == request["instance_id"]
                current = (cold, data[1], cold_client, *data[3:])
                drive_to_success(current, request["run_id"], transport(sent, THIRD))
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
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 10
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]}
        assert len(proof["loaded_source_sha256"]) == 20 and len(sent) == 1
        with data[0].tx() as c:
            current_rows = [dict(r) for r in c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == inst["id"])).mappings()]
        assert all(r in current_rows for r in old_rows) and len(current_rows) == len(old_rows) + 1
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if cold_client:
            cold_client.close()
        if cold:
            cold.engine.dispose()
