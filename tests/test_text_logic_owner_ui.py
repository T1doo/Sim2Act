"""Visible own GoalCard/version -> exact NoModel Worker -> SIMULATED owner choices."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_persistent_app_runs import NoModel
from test_text_logic_owner import own_source_barrier, setup_owner
from test_text_logic_reuse import revoke_source

from sim2act.api import create_app
from sim2act.db import Store
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["accept", "reject", "goal-lost", "decision-lost"])
def test_own_goal_visible_cold_worker_and_owner(env, tmp_path, scenario):
    data, made, release, instance, _, old, resource = setup_owner(env)
    aid, oldrel, oldinst, run = old
    store, settings, _, *_ = data
    app = data[2].get("/api/apps/" + made["id"]).json()
    revoke_source(data)
    barrier = own_source_barrier(data, old)
    cold_api = Store(settings.database_url, test_only=True)
    barrier.attach(cold_api)
    client = TestClient(create_app(cold_api, settings))
    barrier.__enter__()
    info = dict(project=data[4], source=aid, app=made["id"], name=app["name"], instance=instance["id"],
                old_run=run, old_resource=data[5], resource=resource, scenario=scenario,
                output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    stderr_path = tmp_path / "node-stderr.log"
    stderr_file = stderr_path.open("w")
    process = subprocess.Popen(["node", "tests/text_logic_owner_ui.cjs", str(path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_file, text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
    worked = 0
    cold_stores = [cold_api]
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "worker":
                cold = Store(settings.database_url, test_only=True)
                cold_stores.append(cold)
                assert barrier is not None
                barrier.attach(cold)
                assert Worker(cold, settings, NoModel()).once()
                worked += 1
                answer = dict(id=request["id"], status=200, text="{}")
            else:
                response = client.request(request["method"], request["path"],
                    json=request.get("body"), headers=request.get("headers"))
                answer = dict(id=request["id"], status=response.status_code, text=response.text,
                              content_type=response.headers.get("content-type"))
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        process.stdin.close()
        code = process.wait(timeout=20)
        stderr_file.flush()
        error = stderr_path.read_text()
        output = os.environ.get("SIM2ACT_TEXT_OWNER_UI_EVIDENCE_DIR")
        if output:
            folder = Path(output)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (scenario + ".log")).write_text(error)
            if (tmp_path / "result.json").exists():
                (folder / (scenario + ".json")).write_bytes((tmp_path / "result.json").read_bytes())
        assert code == 0, error
        proof = json.loads((tmp_path / "result.json").read_text())
        assert proof["status"] == "PASS" and worked == 2
        assert barrier is not None and not barrier.blocked
        if output:
            (Path(output) / (scenario + "-sql.json")).write_text(json.dumps({
                "protected_private_evaluations": barrier.blocked, "evaluated_cells": barrier.evaluated,
                "statements": barrier.statements}, indent=2))
        assert len(proof["static_resource_loads"]) == 20 * proof["boots"]
        web = Path(__file__).parents[1] / "src/sim2act/web"
        for row in proof["static_resource_loads"]:
            asset = web / (row["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(asset.read_bytes()).hexdigest() == row["sha256"]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        stderr_file.close()
        output = os.environ.get("SIM2ACT_TEXT_OWNER_UI_EVIDENCE_DIR")
        if output:
            folder = Path(output)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (scenario + "-node-stderr.log")).write_bytes(stderr_path.read_bytes())
            (folder / (scenario + "-exit.json")).write_text(json.dumps({"exit_code": process.returncode,
                "worked": worked, "result_exists": (tmp_path / "result.json").exists(),
                "protected_private_evaluations": barrier.blocked if barrier else None}, indent=2))
            if barrier is not None:
                (folder / (scenario + "-sql.json")).write_text(json.dumps({
                    "protected_private_evaluations": barrier.blocked, "evaluated_cells": barrier.evaluated,
                    "statements": barrier.statements}, indent=2))
        if barrier is not None:
            barrier.__exit__(None, None, None)
        client.close()
        for cold in cold_stores:
            cold.engine.dispose()
