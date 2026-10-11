"""Visible DOM actions through actual HTTP assets/API and a cold ordinary Worker."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_persistent_app_runs import NoModel
from test_registered_text_extraction import make_app, prepared
from test_registered_text_extraction import request as extraction_request

from sim2act.db import Store
from sim2act.worker import Worker


@pytest.mark.parametrize(
    "scenario",
    [
        "valid",
        "lost",
        "poison",
        "late-options-edit-undo",
        "late-post-nav",
        "late-app-nav",
        "wrong-existing-app",
        "candidate-fp",
        "wrong-other-key-app",
    ],
)
def test_registered_text_actual_http_page(env, tmp_path, scenario):
    data, aid, _, instance, run, target, resource, _ = prepared(env)
    store, settings, client, *_ = data
    poison_app = poison_fingerprint = None
    if scenario == "wrong-other-key-app":
        url = f"/api/internal/instances/{instance['id']}/runs/{run['id']}"
        _, other_body = extraction_request(data, url, target)
        other_body.update(name="Extracted visible text", request_key="other-independent-key")
        other = client.post(url + "/extract", json=other_body)
        assert other.status_code == 201, other.text
        poison_app, poison_fingerprint = other.json()["id"], other.json()["candidate_fingerprint"]
    elif scenario == "wrong-existing-app":
        poison_app = make_app(data, "third-unrelated-authorized")
    info = tmp_path / "info.json"
    info.write_text(
        json.dumps(
            {
                "project": data[4],
                "source": aid,
                "instance": instance["id"],
                "run": run["id"],
                "target": target,
                "resource": resource,
                "scenario": scenario,
                "poison_app": poison_app,
                "poison_fingerprint": poison_fingerprint,
                "output": str(tmp_path / "result.json"),
            }
        )
    )
    process = subprocess.Popen(
        ["node", "tests/registered_text_ui.cjs", str(info)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
    )
    cold_runs = 0
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "worker":
                cold = Store(settings.database_url, test_only=True)
                try:
                    assert Worker(cold, settings, NoModel()).once()
                    cold_runs += 1
                finally:
                    cold.engine.dispose()
                answer = {"id": request["id"], "status": 200, "text": "{}"}
            else:
                response = client.request(
                    request["method"],
                    request["path"],
                    json=request.get("body"),
                    headers=request.get("headers"),
                )
                answer = {
                    "id": request["id"],
                    "status": response.status_code,
                    "text": response.text,
                    "content_type": response.headers.get("content-type"),
                }
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        process.stdin.close()
        error = process.stderr.read()
        exit_code = process.wait(timeout=20)
        output = os.environ.get("SIM2ACT_PB_EVIDENCE_DIR")
        if output:
            destination = Path(output)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / (scenario + ".log")).write_text(error)
            if (tmp_path / "result.json").exists():
                (destination / (scenario + ".json")).write_bytes(
                    (tmp_path / "result.json").read_bytes()
                )
        assert exit_code == 0, error
        proof = json.loads((tmp_path / "result.json").read_text())
        assert proof["status"] == "PASS" and cold_runs == 1
        web = Path(__file__).parents[1] / "src/sim2act/web"
        for name, digest in proof["loaded_source_sha256"].items():
            assert hashlib.sha256((web / name).read_bytes()).hexdigest() == digest
        assert all(row["visible"] and row["enabled"] for row in proof["actions"])
        assert len(proof["static_resource_loads"]) == 19 * proof["boots"]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
