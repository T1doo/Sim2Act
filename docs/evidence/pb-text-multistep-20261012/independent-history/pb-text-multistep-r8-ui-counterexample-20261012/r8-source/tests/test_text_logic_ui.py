"""Ordinary visible authority -> cold target -> Worker; no cancelled race probes."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_persistent_app_runs import NoModel
from test_registered_text_extraction import prepared
from test_text_logic_reuse import revoke_source, source_barrier

from sim2act.db import Store
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["valid", "authorization-lost", "binding-lost", "revoked-retained"])
def test_independent_text_logic_visible_cold_page(env, tmp_path, scenario):
    data, aid, release, instance, run, target, resource, _ = prepared(env)
    store, settings, client, *_ = data
    info = dict(project=data[4], source=aid, instance=instance["id"], run=run["id"],
                old_resource=data[5], target=target, resource=resource, scenario=scenario,
                output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    stderr_path = tmp_path / "node-stderr.log"
    stderr_file = stderr_path.open("w")
    process = subprocess.Popen(["node", "tests/text_logic_ui.cjs", str(path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_file, text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
    worked = retired = 0
    barrier = None
    cold_stores = []
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "retire-source":
                revoke_source(data, delete_content=scenario != "revoked-retained")
                barrier = source_barrier(data, aid, release, instance, run)
                barrier.__enter__()
                retired += 1
                answer = dict(id=request["id"], status=200, text="{}")
            elif request.get("command") == "worker":
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
        output = os.environ.get("SIM2ACT_TEXT_LOGIC_EVIDENCE_DIR")
        if output:
            folder = Path(output)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (scenario + ".log")).write_text(error)
            if (tmp_path / "result.json").exists():
                (folder / (scenario + ".json")).write_bytes((tmp_path / "result.json").read_bytes())
        assert code == 0, error
        proof = json.loads((tmp_path / "result.json").read_text())
        assert proof["status"] == "PASS" and worked == retired == 1
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
        output = os.environ.get("SIM2ACT_TEXT_LOGIC_EVIDENCE_DIR")
        if output:
            folder = Path(output)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (scenario + "-node-stderr.log")).write_bytes(stderr_path.read_bytes())
            (folder / (scenario + "-exit.json")).write_text(json.dumps({"exit_code": process.returncode,
                "worked": worked, "retired": retired, "result_exists": (tmp_path / "result.json").exists(),
                "protected_private_evaluations": barrier.blocked if barrier else None}, indent=2))
            if barrier is not None:
                (folder / (scenario + "-sql.json")).write_text(json.dumps({
                    "protected_private_evaluations": barrier.blocked, "evaluated_cells": barrier.evaluated,
                    "statements": barrier.statements}, indent=2))
        if barrier is not None:
            barrier.__exit__(None, None, None)
        for cold in cold_stores:
            cold.engine.dispose()
