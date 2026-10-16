"""User prepares new material and Goal through shared forms, then explicitly runs."""

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
from test_pb_natural_uses import THIRD, prepared_use
from test_spec_app_operations import snapshot

from sim2act.api import create_app
from sim2act.db import Store


@pytest.mark.parametrize("family", ["pa", "pb"])
def test_natural_app_prepare_material_goal_then_explicit_run(env, tmp_path, family):
    if family == "pa":
        data, app, release, instance, _, old_resource, old_goal, _, route = prepared_pa(env, history=False)
    else:
        data, app, release, instance, old_resource, old_goal, _, route = prepared_use(env, run_base=True)
    assert data[0].test_only and data[1].mode == "mock"
    original_reply = data[2].get(route)
    assert original_reply.status_code == 200, original_reply.text
    original = original_reply.json()
    assert [row["version"] for row in original["data"]] == [1]
    initial = snapshot(data[0])
    readonly_baseline = initial
    info = dict(
        family=family, project=data[4], app=app["id"], name=app["name"],
        release=release["id"], instance=instance["id"],
        original_resource=old_resource, original_goal=old_goal["id"],
        original_runs=[row["id"] for row in original["runs"]],
        content=THIRD, expected_version=2, output=str(tmp_path / "result.json"),
    )
    info_path = tmp_path / "info.json"
    info_path.write_text(json.dumps(info), encoding="utf-8")
    cold = cold_client = None
    sent = []
    checkpoints = []
    stderr = tmp_path / "node.stderr"

    def assert_old_state_unchanged(current, *, goal_saved=False):
        for table in ["app_drafts", "internal_releases", "principals", "runs", "internal_app_runs",
                      "internal_instance_data", "natural_owner_records", "natural_owner_seals"]:
            assert current[table] == initial[table], table
        for table in ["goal_cards", "goal_card_versions"]:
            assert all(row in current[table] for row in initial[table]), table
            assert len(current[table]) == len(initial[table]) + int(goal_saved), table

    with stderr.open("w", encoding="utf-8") as err:
        process = subprocess.Popen(
            ["node", str(Path(__file__).with_name("natural_input_preparation.cjs")), str(info_path)],
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
                    assert snapshot(cold or data[0]) == readonly_baseline
                    checkpoints.append(dict(phase=request["phase"], readonly=True))
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "saved-input-checkpoint":
                    current = snapshot(data[0])
                    goal_saved = "goal_id" in request
                    assert_old_state_unchanged(current, goal_saved=goal_saved)
                    material = next(row for row in current["resources"] if row["id"] == request["resource_id"])
                    assert material["project_id"] == data[4] and material["format"] == "txt"
                    assert material["content"] == THIRD and request["resource_id"] != old_resource
                    assert len(current["resources"]) == len(initial["resources"]) + 1
                    if goal_saved:
                        card = next(row for row in current["goal_cards"] if row["id"] == request["goal_id"])
                        assert card["project_id"] == data[4] and card["version"] == 1
                        version = next(row for row in current["goal_card_versions"]
                            if row["card_id"] == request["goal_id"] and row["version"] == 1)
                        assert version["snapshot"]["content"]["resource_refs"] == [request["resource_id"]]
                        assert [row["resource_id"] for row in version["snapshot"]["resource_snapshots"]] == [request["resource_id"]]
                        assert request["goal_id"] != old_goal["id"]
                    readonly_baseline = current
                    checkpoints.append(dict(phase="saved-goal" if goal_saved else "saved-material",
                        resource_id=request["resource_id"], goal_id=request.get("goal_id"),
                        no_automatic_run=True, original_state_retained=True))
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "worker":
                    assert request["run_id"] not in info["original_runs"]
                    cold = Store(data[1].database_url, test_only=True)
                    cold_client = TestClient(create_app(cold, data[1]))
                    cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                    drive_to_success((cold, data[1], cold_client, *data[3:]), request["run_id"], transport(sent, THIRD))
                    readonly_baseline = snapshot(cold)
                    answer = dict(id=request["id"], status=200, text="{}")
                else:
                    assert command is None, request
                    reply = (cold_client or data[2]).request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(id=request["id"], status=reply.status_code,
                        text=reply.text, content_type=reply.headers.get("content-type"))
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            assert process.wait(timeout=20) == 0, stderr.read_text(encoding="utf-8")
            proof = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
            assert proof["status"] == "PASS" and len(proof["checks"]) >= 25, proof
            assert len(sent) == 1 and proof["run_id"] not in info["original_runs"]
            web = Path.cwd() / "src/sim2act/web"
            for row in proof["static_resource_loads"]:
                name = "index.html" if row["path"] == "/" else row["path"][1:]
                assert row["sha256"] == hashlib.sha256((web / name).read_bytes()).hexdigest()
            final = snapshot(cold or data[0])
            for table in ["app_drafts", "internal_releases", "principals", "natural_owner_records", "natural_owner_seals"]:
                assert final[table] == initial[table], table
            for table in ["goal_cards", "goal_card_versions"]:
                assert all(row in final[table] for row in initial[table])
                assert len(final[table]) == len(initial[table]) + 1
            previous = [row for row in initial["internal_instance_data"] if row["instance_id"] == instance["id"]]
            current = [row for row in final["internal_instance_data"] if row["instance_id"] == instance["id"]]
            assert all(row in current for row in previous)
            assert sorted(row["version"] for row in current) == [1, 2]
            assert len(final["runs"]) == len(initial["runs"]) + 1
            assert all(row in final["grants"] for row in initial["grants"])
            (tmp_path / "runtime-wire.json").write_text(json.dumps(sent, ensure_ascii=False, indent=2), encoding="utf-8")
            (tmp_path / "persistence-proof.json").write_text(json.dumps(dict(
                family=family, checkpoints=checkpoints,
                old_result_preserved=True, result_versions=[1, 2], new_run_count=1,
                new_goal=proof["goal_id"], new_material=proof["resource_id"],
                original_apps_releases_principals_owner_records_unchanged=True,
                real_model_requests=0,
            ), ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if cold_client:
                cold_client.close()
            if cold:
                cold.engine.dispose()


def test_natural_preparation_navigation_synthesized_api(tmp_path):
    """Actual form scripts with synthetic API; no HTTP or Worker evidence."""
    output = tmp_path / "navigation.json"
    outcome = subprocess.run(
        ["node", str(Path(__file__).with_name("natural_input_preparation_navigation.cjs")), str(output)],
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
