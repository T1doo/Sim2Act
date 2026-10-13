"""Actual saved P-A: visible third material confirmation, Worker, new owner."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_natural_spec_apps import transport
from test_pa_natural_uses import prepared_pa
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD

from sim2act.api import create_app
from sim2act.db import Store


@pytest.mark.parametrize("scenario", ["normal", "lost"])
def test_visible_same_pa_third_material_and_fresh_owner(env, tmp_path, scenario):
    data, app, release, inst, original, resource, goal, body, route = prepared_pa(env, history=True)
    info = dict(
        project=data[4],
        app=app["id"],
        name=app["name"],
        release=release["id"],
        instance=inst["id"],
        original=original,
        resource=resource,
        goal=goal["id"],
        content=THIRD,
        scenario=scenario,
        output=str(tmp_path / "result.json"),
    )
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    stderr = tmp_path / "node.stderr"
    sent = []
    cold = cold_client = None
    with stderr.open("w") as err:
        process = subprocess.Popen(
            ["node", "tests/pa_natural_uses_ui.cjs", str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=err,
            text=True,
            env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
        )
        try:
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    cold = Store(data[1].database_url, test_only=True)
                    cold_client = TestClient(create_app(cold, data[1]))
                    cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                    drive_to_success(
                        (cold, data[1], cold_client, *data[3:]),
                        request["rid"],
                        transport(sent, THIRD),
                    )
                    answer = dict(id=request["id"], status=200, text="{}")
                else:
                    response = (cold_client or data[2]).request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers"),
                    )
                    answer = dict(
                        id=request["id"],
                        status=response.status_code,
                        text=response.text,
                        content_type=response.headers.get("content-type"),
                    )
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
            assert code == 0, stderr.read_text()
            result = json.loads((tmp_path / "result.json").read_text())
            assert result["status"] == "PASS" and len(result["checks"]) > 20
            web = Path(__file__).parents[1] / "src/sim2act/web"
            assert len(result["static_resource_loads"]) == 20
            for row in result["static_resource_loads"]:
                name = "index.html" if row["path"] == "/" else row["path"][1:]
                assert row["sha256"] == hashlib.sha256((web / name).read_bytes()).hexdigest()
            assert len(sent) == 1
            (tmp_path / "runtime-wire.json").write_text(json.dumps(sent, indent=2))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if cold_client:
                cold_client.close()
            if cold:
                cold.engine.dispose()
