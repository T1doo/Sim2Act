"""Actual in-process HTTP bridge and offline page gestures; no native browser."""

import hashlib
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from test_goal_text_applications import wire
from test_natural_spec_apps import COLD, SOURCE, facts, material, recipe, setup, transport

from sim2act import natural_specs as natural
from sim2act.api import create_app
from sim2act.db import Store
from sim2act.worker import Worker


@pytest.mark.parametrize(
    "scenario",
    ["valid", "binding-lost", "binding-late", "sample-tampered", "sample-nodes-tampered",
     "run-lost", "run-late", "run-receipt-poison", "artifact-poison", "artifact-late"],
)
def test_natural_spec_page_actual_nodes_and_cold_material(env, tmp_path, scenario):
    data = setup(env)
    store, settings, client, _, pid, resource, card = data
    target_resource, target_card = material(client, pid, COLD, "Cold operating notes")
    info = tmp_path / "info.json"
    info.write_text(
        json.dumps(
            dict(
                project=pid,
                card=card["id"],
                target_card=target_card["id"],
                target_resource=target_resource,
                scenario=scenario,
                output=str(tmp_path / "results.json"),
            )
        )
    )
    sent = []
    runtime_sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        initial = json.loads(payload["messages"][1]["content"])
        feedback = [json.loads(m["content"]) for m in payload["messages"] if m["role"] == "tool"]
        if len(sent) == 1:
            message = dict(
                role="assistant",
                content="",
                tool_calls=[
                    dict(
                        id="model-read",
                        type="function",
                        function=dict(
                            name="resource.read", arguments=json.dumps(dict(resource_id=resource))
                        ),
                    )
                ],
            )
        else:
            assert feedback[0]["data"]["content"] == SOURCE
            value = dict(
                recipe=recipe("sequential"),
                sample_nodes=[
                    dict(
                        step_id=step["step_id"],
                        items=[
                            i
                            for i in facts(SOURCE)
                            if i["kind"] in natural.MODEL_KINDS[step["operator"]]
                        ],
                    )
                    for step in recipe("sequential")["steps"]
                    if step["operator"] in natural.MODEL_KINDS
                ],
                source_hash=feedback[0]["data"]["hash"],
                goal=initial["saved_goal"]["snapshot"]["content"],
            )
            if len(sent) == 2:
                message = dict(
                    role="assistant",
                    content="",
                    tool_calls=[
                        dict(
                            id="model-check",
                            type="function",
                            function=dict(
                                name="spec.check_candidate",
                                arguments=json.dumps(dict(candidate=value)),
                            ),
                        )
                    ],
                )
            else:
                assert feedback[-1]["data"]["status"] == "PASS"
                message = dict(role="assistant", content=json.dumps(value))
        return httpx.Response(
            200, json=wire(message, "tool_calls" if "tool_calls" in message else "stop")
        )

    process = subprocess.Popen(
        ["node", "tests/pa_natural_spec_ui.cjs", str(info)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
    )
    cold = cold_client = None
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command"):
                if request["command"] == "provider-worker":
                    assert Worker(
                        store, settings, goal_planner_transport=httpx.MockTransport(handler)
                    ).once()
                else:
                    assert request["command"] == "cold-worker"
                    cold = Store(settings.database_url, test_only=True)
                    cold_settings = replace(
                        settings, goal_planner_provider="intern-s2", live_enabled=False, token=""
                    )
                    cold_client = TestClient(create_app(cold, cold_settings))
                    cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                    assert Worker(
                        cold, cold_settings, goal_planner_transport=transport(runtime_sent, COLD)
                    ).once()
                answer = dict(id=request["id"], status=200, text="{}")
            else:
                reply = (cold_client or client).request(
                    request["method"],
                    request["path"],
                    json=request.get("body"),
                    headers=request.get("headers"),
                )
                answer = dict(
                    id=request["id"],
                    status=reply.status_code,
                    text=reply.text,
                    content_type=reply.headers.get("content-type"),
                )
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        errors = process.stderr.read()
        code = process.wait(timeout=20)
        (tmp_path / "driver.log").write_text(errors)
        (tmp_path / "model-wire.json").write_text(json.dumps(sent, ensure_ascii=False, indent=2))
        assert code == 0, errors
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= (
            4 if scenario.startswith("sample-") else 22
        )
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert len(proof["loaded_source_sha256"]) == 20
        assert proof["loaded_source_sha256"] == {
            name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]
        }
        assert len(sent) == 3 and len(runtime_sent) == (0 if scenario.startswith("sample-") else 2)
        (tmp_path / "runtime-wire.json").write_text(
            json.dumps(runtime_sent, ensure_ascii=False, indent=2)
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if cold_client:
            cold_client.close()
        if cold:
            cold.engine.dispose()
        client.close()
