"""One real successful source drives continuous P-B extraction and a fresh use."""

import hashlib
import json
import os
import subprocess
from contextlib import nullcontext
from pathlib import Path

from fastapi.testclient import TestClient
from test_natural_spec_apps import COLD, SOURCE, enqueue, ready, setup, transport
from test_pa_natural_spec_ui import _PageObserver
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act.api import create_app
from sim2act.db import Store


def test_successful_source_to_pb_directory_and_new_material(env, tmp_path):
    with _PageObserver(tmp_path, "test_successful_source_to_pb_directory_and_new_material") as observer:
        generation_wire = []
        generation_returned = False
        source_wire = observer.observed_list("source-worker")
        runtime_wire = observer.runtime_sent
        checkpoints = observer.observed_list("checkpoints")
        boundary_receipts = []
        try:
            with observer.phase("fixture_setup"):
                data = setup(env)
            store, settings, client, owner, project, source_resource, _ = data
            with observer.phase("fixture_generation_and_ready"):
                _, source_app, source_release, source_instance, generation_wire = ready(data, "single")
            generation_returned = True
            observer.sent = generation_wire
            observer.save("source-generation-wire.json", generation_wire)
            observer.event("fixture_generation_wire_exported", request_count=len(generation_wire))
            source_run = enqueue(data, source_release, source_instance)
            with observer.phase("worker", command="fixture-source-worker", run_id=source_run):
                drive_to_success(data, source_run, transport(source_wire, SOURCE))
            assert len(source_wire) == 1 and store.test_only and settings.mode == "mock"
            with observer.phase("http", method="GET", path="/api/apps/" + source_app):
                source_app_reply = client.get("/api/apps/" + source_app)
                observer.http_response(dict(method="GET", path="/api/apps/" + source_app), source_app_reply)
            assert source_app_reply.status_code == 200, source_app_reply.text
            source_app_value = source_app_reply.json()
            with observer.phase("http", method="GET", path=f"/api/internal/app-run-jobs/{source_run}/spec-artifact"):
                source_artifact = client.get(f"/api/internal/app-run-jobs/{source_run}/spec-artifact")
                observer.http_response(dict(method="GET", path=f"/api/internal/app-run-jobs/{source_run}/spec-artifact"), source_artifact)
            assert source_artifact.status_code == 200, source_artifact.text
            original_artifact = source_artifact.json()
            initial = snapshot(store)
            readonly_baseline = initial
            source_result_rows = [row for row in initial["internal_instance_data"] if row["instance_id"] == source_instance["id"]]
            assert len(source_result_rows) == 1 and source_result_rows[0]["version"] == 1
            artifact_row = next(row for row in initial["resources"] if row["id"] == original_artifact["resource"]["resource_id"])
            info = dict(project=project, source_app=source_app, source_name=source_app_value["name"],
                source_instance=source_instance["id"], source_release=source_release["id"], source_run=source_run,
                source_content=SOURCE, target_content=COLD, next_content=THIRD,
                output=str(tmp_path / "result.json"))
            info_path = tmp_path / "info.json"
            info_path.write_text(json.dumps(info), encoding="utf-8")
            cold = cold_client = None
            revoked_grant = None
            stderr = tmp_path / "node.stderr"
            observer.driver.close()
            observer.driver = stderr.open("w", encoding="utf-8")

            def source_unchanged(current):
                for table, column, key in [("app_drafts", "id", source_app),
                                          ("internal_releases", "id", source_release["id"]),
                                          ("internal_instances", "id", source_instance["id"])]:
                    assert next(row for row in current[table] if row[column] == key) == next(row for row in initial[table] if row[column] == key), table
                assert [row for row in current["internal_instance_data"] if row["instance_id"] == source_instance["id"]] == source_result_rows
                assert next(row for row in current["resources"] if row["id"] == artifact_row["id"]) == artifact_row
                for table in ["goal_cards", "goal_card_versions"]:
                    assert all(row in current[table] for row in initial[table]), table

            with nullcontext(observer.driver) as err:
                process = subprocess.Popen(
                    ["node", str(Path(__file__).with_name("pb_natural_product_flow.cjs")), str(info_path)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True,
                    env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")},
                )
                observer.own_node(process)
                try:
                    for line in process.stdout:
                        observer.event("node_stdout", raw_line=line)
                        request = json.loads(line)
                        with observer.phase("rpc", request=request):
                            if request.get("done"):
                                observer.event("rpc_done", rpc_id=request.get("id"))
                                break
                            command = request.get("command")
                            if command == "readonly-checkpoint":
                                assert snapshot(cold or store) == readonly_baseline
                                checkpoints.append(dict(phase=request["phase"], readonly=True))
                                answer = dict(id=request["id"], status=200, text="{}")
                            elif command == "freeze-readonly-baseline":
                                readonly_baseline = snapshot(cold or store)
                                source_unchanged(readonly_baseline)
                                checkpoints.append(dict(phase=request["phase"], source_unchanged=True))
                                answer = dict(id=request["id"], status=200, text="{}")
                            elif command == "input-saved-checkpoint":
                                current = snapshot(store)
                                source_unchanged(current)
                                assert current["app_drafts"] == initial["app_drafts"]
                                for table in ["internal_releases", "internal_instances", "runs", "attempts", "internal_app_runs", "internal_instance_data"]:
                                    assert current[table] == initial[table], table
                                assert len(current["goal_cards"]) == len(initial["goal_cards"]) + 1
                                assert len(current["resources"]) == len(initial["resources"]) + 1
                                readonly_baseline = current
                                checkpoints.append(dict(phase="extraction-target-saved", no_automatic_app_or_run=True))
                                answer = dict(id=request["id"], status=200, text="{}")
                            elif command == "extraction-accepted-checkpoint":
                                current = snapshot(store)
                                source_unchanged(current)
                                assert len(current["app_drafts"]) == len(initial["app_drafts"]) + 1
                                assert len(current["task_extractions"]) == len(initial["task_extractions"]) + 1
                                for table in ["internal_releases", "internal_instances", "runs", "attempts", "internal_app_runs", "internal_instance_data"]:
                                    assert current[table] == initial[table], table
                                readonly_baseline = current
                                checkpoints.append(dict(phase="one-extraction-accepted-unknown-ui", no_automatic_release_or_run=True))
                                answer = dict(id=request["id"], status=200, text="{}")
                            elif command == "instance-saved-checkpoint":
                                current = snapshot(store)
                                source_unchanged(current)
                                assert len(current["app_drafts"]) == len(initial["app_drafts"]) + 1
                                assert len(current["internal_releases"]) == len(initial["internal_releases"]) + 1
                                assert len(current["internal_instances"]) == len(initial["internal_instances"]) + 1
                                assert not [row for row in current["internal_instance_data"] if row["instance_id"] == request["instance_id"]]
                                assert current["runs"] == initial["runs"] and current["attempts"] == initial["attempts"]
                                readonly_baseline = current
                                checkpoints.append(dict(phase="pb-instance-saved", instance=request["instance_id"], no_execution=True))
                                answer = dict(id=request["id"], status=200, text="{}")
                            elif command == "worker":
                                with observer.phase("worker", rpc_id=request["id"], command=command, run_id=request["run_id"]):
                                    assert not runtime_wire
                                    cold = Store(settings.database_url, test_only=True)
                                    cold_client = TestClient(create_app(cold, settings))
                                    cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                                    drive_to_success((cold, settings, cold_client, owner, project), request["run_id"], transport(runtime_wire, THIRD))
                                    assert len(runtime_wire) == 1
                                    readonly_baseline = snapshot(cold)
                                    source_unchanged(readonly_baseline)
                                    answer = dict(id=request["id"], status=200, text="{}")
                            elif command == "revoke-source-read":
                                assert revoked_grant is None
                                active_client = cold_client or client
                                with observer.phase("http", rpc_id=request["id"], method="GET", path=f"/api/projects/{project}/grants"):
                                    listed = active_client.get(f"/api/projects/{project}/grants")
                                    observer.http_response(dict(id=request["id"], method="GET", path=f"/api/projects/{project}/grants"), listed)
                                assert listed.status_code == 200, listed.text
                                matches = [row for row in listed.json() if row["principal_id"] == source_app_value["runtime_id"]
                                           and row["resource_id"] == source_resource and row["tool_ref"] == "resource.read" and not row["revoked"]]
                                assert len(matches) == 1, matches
                                revoked_grant = matches[0]
                                revoke_path = f"/api/grants/{revoked_grant['id']}/revoke"
                                body = dict(command="revoke", version=revoked_grant["revision"])
                                with observer.phase("http", rpc_id=request["id"], method="POST", path=revoke_path):
                                    revoked = active_client.post(revoke_path, json=body)
                                    observer.http_response(dict(id=request["id"], method="POST", path=revoke_path, body=body), revoked)
                                assert revoked.status_code == 200, revoked.text
                                boundary_receipts.extend([
                                    dict(method="GET", path=f"/api/projects/{project}/grants", status=listed.status_code, body=listed.json()),
                                    dict(method="POST", path=revoke_path, request=body, status=revoked.status_code, body=revoked.json()),
                                ])
                                observer.save("boundary-receipts.json", boundary_receipts)
                                readonly_baseline = snapshot(cold or store)
                                source_unchanged(readonly_baseline)
                                answer = dict(id=request["id"], status=200, text=json.dumps(dict(selected_grant=revoked_grant, receipt=revoked.json())))
                            else:
                                assert command is None, request
                                with observer.phase("http", rpc_id=request["id"], method=request["method"], path=request["path"]):
                                    reply = (cold_client or client).request(request["method"], request["path"],
                                        json=request.get("body"), headers=request.get("headers"))
                                    observer.http_response(request, reply)
                                    answer = dict(id=request["id"], status=reply.status_code,
                                        text=reply.text, content_type=reply.headers.get("content-type"))
                            observer.event("rpc_reply", rpc_id=answer["id"], status=answer["status"],
                                text_sha256=hashlib.sha256(answer["text"].encode()).hexdigest())
                            process.stdin.write(json.dumps(answer) + "\n")
                            process.stdin.flush()
                    process.stdin.close()
                    assert process.wait(timeout=20) == 0, stderr.read_text(encoding="utf-8")
                    proof = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
                    assert proof["status"] == "PASS" and len(proof["checks"]) >= 25, proof
                    current = snapshot(cold or store)
                    source_unchanged(current)
                    pb_results = [row for row in current["internal_instance_data"] if row["instance_id"] == proof["instance_id"]]
                    assert len(pb_results) == 1 and pb_results[0]["version"] == 1
                    assert len(current["internal_app_runs"]) == len(initial["internal_app_runs"]) + 1
                    assert len(current["runs"]) == len(initial["runs"]) + 1
                    assert len(current["app_drafts"]) == len(initial["app_drafts"]) + 1
                    assert len(current["task_extractions"]) == len(initial["task_extractions"]) + 1
                    assert current["natural_owner_records"] == initial["natural_owner_records"]
                    for row in initial["grants"]:
                        expected = {**row, "revoked": True, "revision": row["revision"] + 1} if row["id"] == revoked_grant["id"] else row
                        assert expected in current["grants"]
                    web = Path.cwd() / "src/sim2act/web"
                    for row in proof["static_resource_loads"]:
                        name = "index.html" if row["path"] == "/" else row["path"][1:]
                        assert row["sha256"] == hashlib.sha256((web / name).read_bytes()).hexdigest()
                    for name, value in [("source-generation-wire.json", generation_wire), ("source-worker-wire.json", source_wire),
                                        ("runtime-wire.json", runtime_wire), ("checkpoints.json", checkpoints),
                                        ("boundary-receipts.json", boundary_receipts)]:
                        (tmp_path / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
                    (tmp_path / "source-preservation-proof.json").write_text(json.dumps(dict(
                        source_app=source_app, source_release=source_release["id"], source_instance=source_instance["id"], source_run=source_run,
                        original_result_versions=[1], original_result_rows_unchanged=True,
                        original_artifact=artifact_row["id"], original_artifact_bytes_sha256=hashlib.sha256(artifact_row["content"].encode()).hexdigest(),
                        original_artifact_row_unchanged=True, new_pb_instance=proof["instance_id"], new_pb_result_versions=[1],
                        extraction_count=1, new_runtime_count=1, real_model_requests=0,
                    ), indent=2), encoding="utf-8")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
                    if cold_client:
                        cold_client.close()
                    if cold:
                        cold.engine.dispose()

        finally:
            for name, value in [("source-generation-wire.json", generation_wire),
                                ("source-worker-wire.json", source_wire),
                                ("runtime-wire.json", runtime_wire), ("checkpoints.json", checkpoints),
                                ("boundary-receipts.json", boundary_receipts)]:
                observer.save(name, value)
            observer.save("fixture-generation-observation.json", dict(
                ready_returned=generation_returned, exported_requests=len(generation_wire),
                partial_wire_before_ready_return="NOT_EXPORTED_BY_ORIGINAL_HELPER",
                exported_count_is_not_attempt_count_if_ready_failed=not generation_returned))
            if not generation_returned:
                observer.event("fixture_generation_wire_unavailable",
                    reason="Original ready helper did not return; partial generation wire is not exported")


def test_pb_product_navigation_synthesized_api(tmp_path):
    """Actual controllers with synthetic API and staged saved view/review; no Worker."""
    output = tmp_path / "navigation.json"
    outcome = subprocess.run(
        ["node", str(Path(__file__).with_name("pb_natural_product_navigation.cjs")), str(output)],
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
