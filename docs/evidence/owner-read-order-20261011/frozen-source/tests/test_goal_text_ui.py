"""Offline JSDOM via IPC/in-process HTTP; normal Workers, no socket/browser."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest
from test_goal_text_applications import fixture_candidate, setup, wire

from sim2act.worker import Worker


@pytest.mark.parametrize(
    "scenario",
    [
        "valid",
        "lost-generation",
        "lost-confirm",
        "late-generation",
        "poison-accepted-id",
        "poison-accepted-shape",
        "poison-accepted-fields",
        "late-confirm-navigation",
        "late-confirm-edit",
        "late-confirm-edit-undo",
        "late-confirm-read-edit-undo",
        "late-confirm-app",
        "late-confirm-goal",
        "late-app-read",
        "late-internal-read",
        "owner-accept",
        "owner-reject",
        "owner-lost-prepare",
        "owner-lost-decision",
        "owner-late-prepare-undo",
        "owner-late-decision-undo",
        "owner-late-read-undo",
        "owner-late-navigation-undo",
        "owner-cancel",
        "owner-revoke",
        "owner-read-order-revoke",
        "owner-read-order-prepare",
        "owner-read-order-error",
        "owner-read-order-invalid",
    ],
)
def test_goal_text_offline_page_actual_worker(env, tmp_path, scenario):
    store, settings, client, user, pid, text, card = setup(env)
    other_app = None
    if scenario == "late-confirm-app":
        other = client.post(
            f"/api/projects/{pid}/apps/csv-preview",
            json={"resource_id": env[6], "name": "Other app", "goal": "Fixed CSV fixture"},
        )
        assert other.status_code == 201, other.text
        other_app = other.json()["id"]
    info = tmp_path / "info.json"
    info.write_text(
        json.dumps(
            {
                "project": pid,
                "card": card["id"],
                "scenario": scenario,
                "other": store.project(user, "Other selection"),
                "other_app": other_app,
                "output": str(tmp_path / "results.json"),
            }
        )
    )
    wires = []

    def handler(request):
        payload = json.loads(request.content)
        wires.append(payload)
        if len(wires) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "page-read",
                        "type": "function",
                        "function": {
                            "name": "resource.read",
                            "arguments": json.dumps({"resource_id": text}),
                        },
                    }
                ],
            }
            result = wire(message, "tool_calls")
        else:
            initial = json.loads(payload["messages"][1]["content"])
            value = fixture_candidate(initial)
            if len(wires) == 2:
                value["manifest"]["workflow"][0]["inputs"].pop("term")
            result = wire(
                {
                    "role": "assistant",
                    "content": json.dumps(value, ensure_ascii=False, separators=(",", ":")),
                }
            )
        return httpx.Response(200, json=result)

    process = subprocess.Popen(
        ["node", "tests/goal_text_ui.cjs", str(info)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            **os.environ,
            "NODE_PATH": os.environ.get("NODE_PATH", "/workspace/node-tools/node_modules"),
        },
    )
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "worker":
                worker = Worker(
                    store, settings, goal_planner_transport=httpx.MockTransport(handler)
                )
                assert worker.once()
                answer = {"id": request["id"], "status": 200, "text": "{}"}
            else:
                r = client.request(
                    request["method"],
                    request["path"],
                    json=request.get("body"),
                    headers=request.get("headers"),
                )
                answer = {
                    "id": request["id"],
                    "status": r.status_code,
                    "text": r.text,
                    "content_type": r.headers.get("content-type"),
                }
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        errors = process.stderr.read()
        code = process.wait(timeout=20)
        (tmp_path / "driver.log").write_text(errors)
        output = os.environ.get("SIM2ACT_PA_EVIDENCE_DIR")
        if output:
            target = Path(output)
            target.mkdir(parents=True, exist_ok=True)
            (target / (scenario + ".log")).write_text(errors)
            result_path = tmp_path / "results.json"
            if result_path.exists():
                (target / (scenario + ".json")).write_bytes(result_path.read_bytes())
        assert code == 0, errors
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 15
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {
            name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]
        }
        assert len(wires) == 3
        output = os.environ.get("SIM2ACT_PA_EVIDENCE_DIR")
        if output:
            target = Path(output)
            target.mkdir(parents=True, exist_ok=True)
            (target / (scenario + ".json")).write_text(
                json.dumps(proof, ensure_ascii=False, indent=2) + "\n"
            )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        client.close()
