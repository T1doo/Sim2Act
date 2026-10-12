"""Offline JSDOM fetches via IPC to actual in-process HTTP; no browser/socket."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_csv_dag import NoModel
from test_project_column_patches import setup

from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["lost-version-preview", "lost-version-commit", "late-identity-preview", "late-project-commit"])
def test_executable_versions_offline_cold_actual_worker_and_aba(env, tmp_path, scenario):
    values = setup(env)
    other = env[0].project(env[3], "Other project")
    web = Path(__file__).parents[1] / "src/sim2act/web"
    info = tmp_path / "info.json"
    info.write_text(json.dumps(dict(project=env[5], app=values[2], other=other,
                                   scenario=scenario, web=str(web), output=str(tmp_path / "results.json"))))
    process = subprocess.Popen(["node", "tests/project_column_versions_ui.cjs", str(info)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env=os.environ.copy())
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "worker":
                worker = Worker(env[0], env[1], NoModel())
                count = 0
                while job := env[0].claim(worker.id, env[1].lease_seconds):
                    worker.process(job)
                    count += 1
                assert count in (1, 4)
                answer = dict(id=request["id"], status=200, text="{}")
            else:
                response = env[2].request(request["method"], request["path"],
                                          json=request.get("body"), headers=request.get("headers"))
                answer = dict(id=request["id"], status=response.status_code, text=response.text,
                              content_type=response.headers.get("content-type"))
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        code = process.wait(timeout=20)
        error = process.stderr.read()
        (tmp_path / "driver.log").write_text(error)
        assert code == 0, error
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 25
        assert proof["loaded_source_sha256"] == {
            name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]
        }
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
