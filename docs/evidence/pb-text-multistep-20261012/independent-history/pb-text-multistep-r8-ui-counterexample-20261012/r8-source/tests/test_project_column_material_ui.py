"""Offline JSDOM over IPC/in-process HTTP; actual Worker, no browser or socket."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_csv_dag import NoModel
from test_csv_logic_reuse import retire_old
from test_project_column_material_reuse import DIRECT, FREE, binding, setup

from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["direct-lost", "logic-lost", "logic-mint-lost", "logic-late"])
def test_modified_fixed_family_new_material_offline_page(env, tmp_path, scenario):
    rel, old_rid, group, _, body, _ = setup(env, content=DIRECT if scenario == "direct-lost" else FREE)
    entry = next(e for e in group["entries"] if e["release_id"] == rel["id"])
    web = Path(__file__).parents[1] / "src/sim2act/web"
    info = tmp_path / "info.json"
    info.write_text(json.dumps(dict(project=env[5], app=entry["app_id"], release=rel["id"], instance=entry["instance_id"],
        old_resource=old_rid, target=body["target_app_id"], target_resource=body["expected_resource_id"],
        other=env[0].project(env[3], "Other"), scenario=scenario, web=str(web), output=str(tmp_path / "results.json"))))
    process = subprocess.Popen(["node", "tests/project_column_material_ui.cjs", str(info)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env={**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", "/workspace/node-tools/node_modules")})
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "worker":
                w = Worker(env[0], env[1], NoModel())
                count = 0
                while job := env[0].claim(w.id, env[1].lease_seconds):
                    w.process(job)
                    count += 1
                assert count == 1
                answer = dict(id=request["id"], status=200, text="{}")
            elif request.get("command") == "retire":
                retire_old(env, old_rid)
                binding(env, body["target_app_id"], body["expected_resource_id"], rel=rel, column="net", key="retired-target")
                answer = dict(id=request["id"], status=200, text="{}")
            else:
                r = env[2].request(request["method"], request["path"], json=request.get("body"), headers=request.get("headers"))
                answer = dict(id=request["id"], status=r.status_code, text=r.text, content_type=r.headers.get("content-type"))
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        error = process.stderr.read()
        code = process.wait(timeout=20)
        (tmp_path / "driver.log").write_text(error)
        assert code == 0, error
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 15
        assert proof["loaded_source_sha256"] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]}
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
