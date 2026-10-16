"""First natural application creation: actual API, mock-only generation and Worker."""

import hashlib
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_goal_text_applications import wire
from test_natural_spec_apps import SOURCE, facts, material, recipe, transport
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act.api import create_app
from sim2act.db import Store, app_drafts, attempts, internal_instances, internal_releases
from sim2act.worker import Worker


def generation_transport(sent, resource_id, content=SOURCE):
    """Private synthetic response recipe; actual resource feedback is mandatory."""
    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        initial = json.loads(payload["messages"][1]["content"])
        feedback = [json.loads(item["content"]) for item in payload["messages"] if item["role"] == "tool"]
        graph = recipe("single")
        candidate = dict(
            recipe=graph,
            sample_nodes=[dict(step_id=step["step_id"], items=[
                item for item in facts(content) if item["kind"] in natural.MODEL_KINDS[step["operator"]]
            ]) for step in graph["steps"] if step["operator"] in natural.MODEL_KINDS],
            source_hash=hashlib.sha256(content.encode()).hexdigest(),
            goal=initial["saved_goal"]["snapshot"]["content"],
        )
        if len(sent) == 1:
            name, arguments = "resource.read", dict(resource_id=resource_id)
        else:
            assert feedback[0]["status"] == "VERIFIED" and feedback[0]["data"]["content"] == content
            if len(sent) == 2:
                name, arguments = "spec.check_candidate", dict(candidate=candidate)
            else:
                assert len(sent) == 3 and feedback[-1]["data"]["status"] == "PASS"
                return httpx.Response(200, json=wire(dict(role="assistant", content=json.dumps(candidate)), "stop"))
        message = dict(role="assistant", content="", tool_calls=[dict(
            id="first-create-" + str(len(sent)), type="function",
            function=dict(name=name, arguments=json.dumps(arguments)),
        )])
        return httpx.Response(200, json=wire(message, "tool_calls"))

    return httpx.MockTransport(handler)


def test_natural_creation_default_gate_has_zero_model_attempts(env, tmp_path):
    store, settings, client, _, _, project, _ = env
    assert store.test_only and settings.mode == "mock" and settings.goal_planner_provider == "disabled"
    _, goal = material(client, project, SOURCE, "Default-off natural creation Goal")
    before = client.get("/api/apps?metadata_only=true")
    assert before.status_code == 200 and before.json()["items"] == []
    accepted = client.post(f"/api/projects/{project}/goal-cards/{goal['id']}/application-runs", json=dict(
        expected_version=goal["version"], expected_fingerprint=goal["fingerprint"],
        request_key="first-natural-default-disabled", family="natural_spec",
    ))
    assert accepted.status_code == 202, accepted.text
    rid = accepted.json()["run_id"]
    sent = []

    def forbidden(request):
        sent.append(str(request.url))
        raise AssertionError("Default-disabled natural creation must never reach even the mock adapter")

    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(forbidden)).once()
    result = client.get(f"/api/runs/{rid}")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "WAITING_RESOURCE"
    assert result.json()["error"]["code"] == "RESOURCE_UNAVAILABLE"
    assert sent == []
    with store.tx() as connection:
        for table in [app_drafts, attempts, internal_releases, internal_instances]:
            assert connection.execute(select(table)).first() is None, table.name
    after = client.get("/api/apps?metadata_only=true")
    assert after.status_code == 200 and after.json()["items"] == []
    (tmp_path / "default-gate-receipt.json").write_text(json.dumps(dict(
        catalog_before=dict(status=before.status_code, body=before.json()),
        accepted=dict(status=accepted.status_code, body=accepted.json()),
        actual_run=dict(status=result.status_code, body=result.json()),
        catalog_after=dict(status=after.status_code, body=after.json()),
        mock_adapter_calls=sent, model_attempts=0, applications_created=0,
        releases_created=0, instances_created=0, real_model_requests=0,
    ), ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize("available", [True, False], ids=["offline-create", "blocked-no-generation"])
def test_empty_directory_natural_creation_and_second_input(env, tmp_path, available):
    store, original_settings, _, owner, _, project, _ = env
    settings = replace(original_settings, goal_planner_provider="intern-s2" if available else "disabled")
    assert store.test_only and settings.mode == "mock" and not settings.live_enabled and not settings.token
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    initial_catalog = client.get("/api/apps?metadata_only=true")
    assert initial_catalog.status_code == 200 and initial_catalog.json()["items"] == []
    initial = snapshot(store)
    assert all(initial[table] == [] for table in ["app_drafts", "internal_releases", "internal_instances", "runs", "attempts"])
    readonly_baseline = initial
    info = dict(project=project, available=available, source=SOURCE, second=THIRD,
        output=str(tmp_path / "result.json"))
    info_path = tmp_path / "info.json"
    info_path.write_text(json.dumps(info), encoding="utf-8")
    generation_sent, runtime_sent, checkpoints = [], [], []
    cold = cold_client = None
    stderr = tmp_path / "node.stderr"
    with stderr.open("w", encoding="utf-8") as err:
        process = subprocess.Popen(
            ["node", str(Path(__file__).with_name("natural_first_creation.cjs")), str(info_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True,
            env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")},
        )
        try:
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "readonly-checkpoint":
                    assert snapshot(cold or store) == readonly_baseline
                    checkpoints.append(dict(phase=request["phase"], readonly=True))
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "freeze-readonly-baseline":
                    readonly_baseline = snapshot(cold or store)
                    checkpoints.append(dict(phase=request["phase"], frozen=True))
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "source-saved-checkpoint":
                    current = snapshot(store)
                    assert all(current[table] == [] for table in ["app_drafts", "internal_releases", "internal_instances", "runs", "attempts"])
                    assert len(current["resources"]) == len(initial["resources"]) + 1
                    assert len(current["goal_cards"]) == len(initial["goal_cards"]) + 1
                    readonly_baseline = current
                    checkpoints.append(dict(phase="source-and-Goal-saved", no_automatic_generation=True))
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "generation-worker":
                    assert available and not generation_sent
                    assert Worker(store, settings, goal_planner_transport=generation_transport(
                        generation_sent, request["resource_id"], SOURCE)).once()
                    actual = client.get(f"/api/runs/{request['run_id']}")
                    assert actual.status_code == 200 and actual.json()["status"] == "PARTIAL", actual.text
                    assert len(generation_sent) == 3 and not snapshot(store)["app_drafts"]
                    readonly_baseline = snapshot(store)
                    answer = dict(id=request["id"], status=200, text=json.dumps(actual.json()))
                elif command == "instance-saved-checkpoint":
                    current = snapshot(store)
                    assert len(current["app_drafts"]) == len(current["internal_releases"]) == len(current["internal_instances"]) == 1
                    assert not current["internal_app_runs"] and not current["internal_instance_data"]
                    assert current["internal_instances"][0]["id"] == request["instance_id"]
                    readonly_baseline = current
                    checkpoints.append(dict(phase="instance-created", no_instance_execution=True,
                        app=request["app_id"], release=request["release_id"], instance=request["instance_id"]))
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "runtime-worker":
                    assert available and not runtime_sent
                    cold = Store(settings.database_url, test_only=True)
                    cold_client = TestClient(create_app(cold, settings))
                    cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                    drive_to_success((cold, settings, cold_client, owner, project), request["run_id"], transport(runtime_sent, THIRD))
                    assert len(runtime_sent) == 1
                    readonly_baseline = snapshot(cold)
                    answer = dict(id=request["id"], status=200, text="{}")
                else:
                    assert command is None, request
                    reply = (cold_client or client).request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(id=request["id"], status=reply.status_code,
                        text=reply.text, content_type=reply.headers.get("content-type"))
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            assert process.wait(timeout=20) == 0, stderr.read_text(encoding="utf-8")
            proof = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
            assert proof["status"] == "PASS", proof
            final = snapshot(cold or store)
            if available:
                assert len(generation_sent) == 3 and len(runtime_sent) == 1
                assert len(final["app_drafts"]) == len(final["internal_releases"]) == len(final["internal_instances"]) == 1
                assert len(final["internal_app_runs"]) == len(final["internal_instance_data"]) == 1
                assert final["internal_instance_data"][0]["instance_id"] == proof["instance_id"]
                assert final["internal_instance_data"][0]["version"] == 1
                assert len(final["goal_cards"]) == len(initial["goal_cards"]) + 2
                assert len(final["runs"]) == 2
                assert final["natural_owner_records"] == initial["natural_owner_records"]
                assert all(row in final["grants"] for row in initial["grants"])
            else:
                assert generation_sent == runtime_sent == []
                assert all(final[table] == [] for table in ["app_drafts", "internal_releases", "internal_instances", "runs", "attempts"])
                assert len(final["goal_cards"]) == len(initial["goal_cards"]) + 1
            web = Path.cwd() / "src/sim2act/web"
            assert proof["static_resource_loads"]
            for row in proof["static_resource_loads"]:
                name = "index.html" if row["path"] == "/" else row["path"][1:]
                assert row["sha256"] == hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name, value in [("generation-wire.json", generation_sent), ("runtime-wire.json", runtime_sent), ("checkpoints.json", checkpoints)]:
                (tmp_path / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if cold_client:
                cold_client.close()
            if cold:
                cold.engine.dispose()
            client.close()


def test_natural_first_creation_navigation_synthesized_api(tmp_path):
    output = tmp_path / "navigation.json"
    outcome = subprocess.run(
        ["node", str(Path(__file__).with_name("natural_first_creation_navigation.cjs")), str(output)],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")},
    )
    (tmp_path / "driver.log").write_text(outcome.stdout + outcome.stderr, encoding="utf-8")
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr
    proof = json.loads(output.read_text(encoding="utf-8"))
    assert proof["status"] == "PASS" and len(proof["checks"]) >= 25, proof
    web = Path.cwd() / "src/sim2act/web"
    assert proof["assets"] == {
        name: hashlib.sha256((web / name).read_bytes()).hexdigest()
        for name in proof["assets"]
    }
