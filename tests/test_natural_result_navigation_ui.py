"""One continuous P-B v1/v2 page, Run navigation and exact JSON/MD downloads.

Fresh normal SOURCE generation, extraction, Release/instance and COLD v1 are
fixture setup. The actual page explicitly runs THIRD once. All models are Mock.
"""

import copy
import hashlib
import json
import os
import re
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_natural_spec_apps import COLD, SOURCE, enqueue, material, ready, transport
from test_natural_spec_owner_acceptance import preview as owner_prepare
from test_pa_natural_spec_ui import _PageObserver
from test_pa_spec_apps import instance as release_instance
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, events, fingerprint, internal_run_bindings, runs
from sim2act.worker import Worker


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sources(root):
    paths = sorted(path for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"})
    paths += [Path(__file__).resolve(), Path(__file__).with_name("natural_result_navigation_ui.cjs").resolve()]
    paths += [root / "tests" / name for name in ["durable_browser.cjs", "test_natural_spec_apps.py",
        "test_pa_spec_apps.py", "test_goal_text_applications.py", "test_pa_natural_spec_ui.py",
        "test_natural_spec_owner_acceptance.py", "test_pb_natural_uses.py", "test_spec_app_operations.py"]]
    return {str(path.relative_to(root)) if path.is_relative_to(root) else str(path):
        dict(bytes=path.stat().st_size, sha256=sha_bytes(path.read_bytes())) for path in paths}


def ok(reply, status=200):
    assert reply.status_code == status, reply.text
    return reply.json()


def trace_http(client, observer, lock):
    def capture(reply):
        reply.read()
        request = reply.request
        with lock:
            raw = request.content
            observer.http_response(dict(method=request.method, path=request.url.raw_path.decode("ascii"),
                body=json.loads(raw) if raw else None), reply)
            path = f"http/{observer.http_serial:06d}-request.body"
            (observer.folder / path).write_bytes(raw)
            observer.save(f"http/{observer.http_serial:06d}-request-bytes.json", dict(path=path,
                bytes=len(raw), sha256=sha_bytes(raw), headers=dict(request.headers)))
    client.event_hooks["response"].append(capture)


def header(store, rid):
    with store.tx() as connection:
        job = dict(connection.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        binding = dict(connection.execute(select(internal_run_bindings).where(
            internal_run_bindings.c.run_id == rid)).mappings().one())
        claims = [dict(row) for row in connection.execute(select(events).where(
            events.c.run_id == rid, events.c.kind == "CLAIMED")).mappings()]
    return dict(job=job, binding=binding, clock=binding["snapshot"]["natural_spec_clock"], claims=claims)


def once(store, settings, rid, content, phase, observer, stage, wires, workers):
    before = header(store, rid)
    assert before["job"]["status"] == "QUEUED" and not before["claims"]
    stage["name"] = phase
    count = len(wires[phase])
    worker = Worker(store, settings, goal_planner_transport=transport([], content))
    observer.save(phase + "-before.json", before)
    try:
        with observer.phase("normal_worker_once", phase=phase, run_id=rid, worker_id=worker.id):
            claimed = worker.once()
        after = header(store, rid)
        assert claimed and after["job"]["status"] == "SUCCEEDED"
        assert len(after["claims"]) == 1 and len(wires[phase]) == count + 1
        assert after["job"]["created_at"] == before["job"]["created_at"]
        assert after["clock"] == before["clock"]
        assert after["job"]["fence"] > before["job"]["fence"]
        entry = dict(phase=phase, run_id=rid, worker_id=worker.id, worker_calls=1,
            mock_requests=len(wires[phase]) - count, status=after["job"]["status"],
            claims=len(after["claims"]), accepted_clock_unchanged=True, test_clock_or_lease_mutations=0)
        workers.append(entry)
        return entry
    finally:
        observer.save(phase + "-finally.json", header(store, rid))
        observer.save("business-workers.json", workers)


def one(rows, predicate, label):
    matches = [row for row in rows if predicate(row)]
    assert len(matches) == 1, (label, matches)
    return matches[0]


def appended(before, after, table):
    assert all(row in after[table] for row in before[table]), table
    return [row for row in after[table] if row not in before[table]]


def queued_delta(before, after, info, rid, key):
    allowed = {"runs", "run_contracts", "internal_app_runs", "internal_run_bindings",
        "delivery_graph_requests", "events", "grants"}
    for table in before:
        if table not in allowed:
            assert after[table] == before[table], table
    jobs = appended(before, after, "runs")
    assert len(jobs) == 1
    job = one(jobs, lambda row: row["id"] == rid, "One new queued Run")
    assert job["status"] == "QUEUED" and job["runtime_id"] == info["runtime"]
    assert job["principal_id"] == info["principal"] and job["project_id"] == info["project"]
    app_run = appended(before, after, "internal_app_runs")
    assert len(app_run) == 1 and app_run[0]["status"] == "QUEUED"
    assert app_run[0]["instance_id"] == info["instance"] and app_run[0]["request_key"] == key
    assert app_run[0]["release_id"] == info["release"]
    binding = appended(before, after, "internal_run_bindings")
    assert len(binding) == 1 and binding[0]["run_id"] == rid and binding[0]["app_run_id"] == app_run[0]["id"]
    assert binding[0]["snapshot"]["pb_use"]["review"]["resource_id"] == info["v2_resource"]
    assert binding[0]["snapshot"]["spec_goal"]["card_id"] == info["v2_goal"]
    assert len(appended(before, after, "run_contracts")) == 1
    permissions = appended(before, after, "grants")
    assert len(permissions) == 1
    assert {(row["principal_id"], row["project_id"], row["resource_id"], row["tool_ref"], row["revoked"])
        for row in permissions} == {(info["runtime"], info["project"], info["v2_resource"], "resource.read", False)}
    journal = appended(before, after, "delivery_graph_requests")
    assert len(journal) == 6
    assert {(row["app_id"], row["kind"], row["request_key"]) for row in journal} == {
        (rid, spec.RUN_META, "accepted"), (rid, spec.RUN_META + "_seal", "accepted"),
        (rid, use.META, "accepted"), (rid, use.META + "_seal", "accepted"),
        (info["instance"], use.USE, key), (info["instance"], use.USE + "_seal", key)}
    assert all(row["fingerprint"] == fingerprint(row["snapshot"]) for row in journal)
    assert all(row["run_id"] == rid for row in appended(before, after, "events"))
    return app_run[0]["id"]


def completed_delta(before, after, info, rid, key, worker):
    allowed = {"runs", "run_contracts", "internal_app_runs", "internal_run_bindings", "delivery_graph_requests",
        "events", "grants", "resources", "internal_instances", "internal_instance_data", "operations",
        "operation_intents", "local_effects", "attempts", "reservations", "heartbeats"}
    for table in before:
        if table not in allowed:
            assert after[table] == before[table], table
    for table in allowed - {"internal_instances"}:
        appended(before, after, table)
    job = appended(before, after, "runs")
    assert len(job) == 1 and job[0]["id"] == rid and job[0]["status"] == "SUCCEEDED"
    app_run = appended(before, after, "internal_app_runs")
    assert len(app_run) == 1 and app_run[0]["instance_id"] == info["instance"]
    assert app_run[0]["status"] == "SUCCEEDED" and app_run[0]["result_version"] == 2
    assert app_run[0]["request_key"] == key and app_run[0]["release_id"] == info["release"]
    typed = appended(before, after, "internal_instance_data")
    assert len(typed) == 1 and typed[0]["instance_id"] == info["instance"] and typed[0]["version"] == 2
    assert typed[0]["run_id"] == app_run[0]["id"] and typed[0]["release_id"] == info["release"]
    assert typed[0]["fingerprint"] == fingerprint(typed[0]["data"])
    result = typed[0]["data"]["result"]
    assert result["checklist"]["source_content"] == THIRD and result["checklist"]["source"]["resource_id"] == info["v2_resource"]
    assert result["checklist"]["owner_acceptance"] == "PENDING" and result["checklist"]["semantic_goal_acceptance"] == "NOT_RUN"
    assert app_run[0]["output"] == result
    previous = {row["id"]: row for row in before["internal_instances"]}
    assert len(after["internal_instances"]) == len(previous)
    for row in after["internal_instances"]:
        assert row == ({**previous[row["id"]], "data_version": 2} if row["id"] == info["instance"] else previous[row["id"]])
    resource = appended(before, after, "resources")
    assert len(resource) == 1 and resource[0]["id"] == result["resource_id"] and resource[0]["format"] == "json"
    assert resource[0]["content"] == json.dumps(result["checklist"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert resource[0]["hash"] == result["hash"] == sha_bytes(resource[0]["content"].encode("utf-8"))
    permissions = appended(before, after, "grants")
    assert len(permissions) == 3
    assert {(row["principal_id"], row["resource_id"], row["tool_ref"], row["revoked"]) for row in permissions} == {
        (info["runtime"], info["v2_resource"], "resource.read", False),
        (info["runtime"], result["resource_id"], "resource.read", False),
        (info["principal"], result["resource_id"], "resource.read", False)}
    operation_rows = appended(before, after, "operations")
    assert len(operation_rows) == 4 and all(row["run_id"] == rid and row["status"] == "VERIFIED" for row in operation_rows)
    operation_ids = {row["id"] for row in operation_rows}
    assert {row["operation_id"] for row in appended(before, after, "operation_intents")} == operation_ids
    effects = appended(before, after, "local_effects")
    assert len(effects) == 1 and effects[0]["operation_id"] in operation_ids and effects[0]["resource_id"] == result["resource_id"]
    for table in ["attempts", "reservations"]:
        rows = appended(before, after, table)
        assert len(rows) == 1 and rows[0]["run_id"] == rid
    assert appended(before, after, "attempts")[0]["status"] == "VERIFIED"
    heartbeat = appended(before, after, "heartbeats")
    assert len(heartbeat) == 1 and heartbeat[0]["id"] == worker["worker_id"]
    assert len(appended(before, after, "run_contracts")) == 1
    assert len(appended(before, after, "internal_run_bindings")) == 1
    assert len(appended(before, after, "delivery_graph_requests")) == 6
    assert all(row["run_id"] == rid for row in appended(before, after, "events"))
    return dict(app_run=app_run[0], typed=typed[0], artifact=resource[0], derived_read_grants=permissions)


def test_same_pb_instance_navigates_matching_owner_run_and_downloads_both_versions(tmp_path):
    root = Path.cwd().resolve()
    settings = Settings("sqlite:///" + str(tmp_path / "fixture.db"), tmp_path, mode="mock", goal_planner_provider="intern-s2")
    store = Store(settings.database_url, test_only=True)
    clients, cold_stores, workers, wire_http, ipc, checkpoints = [], [], [], [], [], []
    stage = dict(name="generation")
    wires = {name: [] for name in ["generation", "source", "pb-v1", "pb-v2"]}
    source_run = v1_run = v2_run = None
    process = None
    proof = dict(status="NOT_COMPLETED", real_model_requests=0, native_browser="NOT_RUN", windows="NOT_RUN",
        pg="NOT_RUN", remote_ci="NOT_RUN", real_semantic_acceptance="NOT_RUN",
        fixture_scope="SOURCE_GEN3_SOURCE_WORKER1_PB_V1_WORKER1_THEN_PAGE_PB_V2_WORKER1")
    with _PageObserver(tmp_path, "NATURAL_RESULT_RUN_NAVIGATION_AND_FOUR_DOWNLOADS") as observer:
        before_sources = sources(root)
        observer.save("source-before.json", before_sources)
        lock = threading.Lock()
        try:
            store.initialize()
            user = store.user("natural navigation fixture A", "synthetic-test-A")
            client = TestClient(create_app(store, settings))
            clients.append(client)
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            trace_http(client, observer, lock)
            project = ok(client.post("/api/projects", json=dict(name="Natural result Run navigation")), 201)["id"]
            source_resource, source_goal = material(client, project, SOURCE)
            data = store, settings, client, user, project, source_resource, source_goal
            observer.save("seed-before-generation.json", snapshot(store))
            import test_natural_spec_apps as original_fixture
            original_transport = original_fixture.httpx.MockTransport

            def observed_transport(handler):
                name = handler.__qualname__
                assert name in {"generate.<locals>.handler", "transport.<locals>.handler"}, name
                def capture(request):
                    payload = json.loads(request.content)
                    target = "generation" if name == "generate.<locals>.handler" else stage["name"]
                    assert target in wires
                    wires[target].append(payload)
                    (observer.sent if target == "generation" else observer.runtime_sent).append(payload)
                    observer.save(target + "-wire.json", wires[target])
                    return handler(request)
                return original_transport(capture)

            fixture_httpx = SimpleNamespace(MockTransport=observed_transport, Response=original_fixture.httpx.Response)
            with patch.object(original_fixture, "httpx", fixture_httpx):
                with observer.phase("normal_source_generation_release_instance"):
                    _, source_app, source_release, source_instance, generation_wire = ready(data, "single")
                assert generation_wire == wires["generation"] and len(generation_wire) == 3
                source_run = enqueue(data, source_release, source_instance, key="navigation-source")
                once(store, settings, source_run, SOURCE, "source", observer, stage, wires, workers)
                observer.save("source-success-before-pb.json", snapshot(store))
                cold_resource, cold_goal = material(client, project, COLD, "P-B v1 exact COLD Goal")
                source_path = f"/api/projects/{project}/natural-spec-task-runs/{source_run}"
                options = ok(client.get(source_path + "/extraction-options"))
                body = dict(source_run_id=source_run, expected_source_proof_fingerprint=options["source_proof_fingerprint"],
                    expected_source_recipe_fingerprint=options["recipe_fingerprint"], card_id=cold_goal["id"],
                    expected_goal_version=cold_goal["version"], expected_goal_fingerprint=cold_goal["fingerprint"],
                    expected_source_hash=sha_bytes(COLD.encode()), recipe=copy.deepcopy(options["recipe"]),
                    name="Natural P-B Run navigation", request_key="navigation-pb-extraction")
                reviewed = ok(client.post(source_path + "/extraction-reviews", json=body))
                extracted = ok(client.post(source_path + "/extractions", json=dict(review=body,
                    expected_review_fingerprint=reviewed["review_fingerprint"], consent=pb.CONSENT,
                    artifact_write_consent=natural.CONSENT)), 201)
                app = ok(client.get("/api/apps/" + extracted["id"]))
                release, instance = release_instance(data, app["id"])
                v1_run = enqueue(data, release, instance, key="navigation-pb-v1")
                observer.save("v1-before-worker.json", snapshot(store))
                once(store, settings, v1_run, COLD, "pb-v1", observer, stage, wires, workers)
                v1_artifact = ok(client.get(f"/api/internal/app-run-jobs/{v1_run}/spec-artifact"))
                assert v1_artifact["result_version"] == 1
                assert json.loads(v1_artifact["resource"]["content"])["source_content"] == COLD
                owner_path = f"/api/internal/instances/{instance['id']}/runs/{v1_run}/spec-owner-review"
                record, owner_request = owner_prepare(data, owner_path, key="navigation-fixture-v1-prepare")
                owner_state = ok(client.get(owner_path))
                assert owner_state["sequence"] == 1 and owner_state["latest"]["kind"] == "PREPARE"
                assert owner_state["owner_acceptance"] == "PENDING" and owner_state["content_access"]
                observer.save("v1-owner-fixture-prepare.json", dict(request=owner_request, record=record,
                    contract_fingerprint=fingerprint(record["payload"]["contract"]), state=owner_state,
                    classification="EXPLICIT_SYNTHETIC_FIXTURE_PREPARE_NO_DECIDE_NOT_HUMAN_SIGNOFF"))
                observer.save("v1-baseline-before-third-input.json", snapshot(store))
                third_resource, third_goal = material(client, project, THIRD, "P-B v2 explicit THIRD Goal")
                initial = snapshot(store)
                readonly = initial
                observer.save("v2-before-page.json", initial)
                assert len(observer.sent) == 3 and len(observer.runtime_sent) == 2
                info = dict(project=project, principal=user, app=app["id"], name=app["name"], app_name=app["name"],
                    instance=instance["id"], release=release["id"], runtime=app["runtime_id"],
                    v1_run=v1_run, v1_result_version=1, v1_goal=cold_goal["id"], v1_resource=cold_resource, v1_content=COLD,
                    v2_goal=third_goal["id"], v2_resource=third_resource, v2_content=THIRD, v2_hash=sha_bytes(THIRD.encode()),
                    v1_history=owner_state["history"], v1_owner_request=owner_request, v1_owner_record_id=record["id"],
                    v1_contract_fingerprint=fingerprint(record["payload"]["contract"]),
                    output=str(tmp_path / "page-result.json"), storage_path=str(tmp_path / "durable-storage.json"))
                observer.save("info.json", info)
                bridge = TestClient(create_app(store, settings))
                clients.append(bridge)
                trace_http(bridge, observer, lock)
                process = subprocess.Popen(["node", str(Path(__file__).with_name("natural_result_navigation_ui.cjs")),
                    str(tmp_path / "info.json")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=observer.driver, text=True, env={**os.environ,
                        "NODE_PATH": str(root / "scripts/engineering-ci/node_modules")})
                observer.own_node(process)
                checked_review = accepted_body = delivered = None
                with (tmp_path / "node.stdout").open("w", encoding="utf-8") as stdout:
                    for line in process.stdout:
                        stdout.write(line)
                        stdout.flush()
                        observer.event("node_stdout", raw_line=line)
                        request = json.loads(line)
                        ipc.append(dict(direction="NODE_TO_PYTHON", value=request))
                        if request.get("done"):
                            break
                        command = request.get("command")
                        with observer.phase("rpc", rpc_id=request["id"], command=command):
                            if command == "worker":
                                assert not [row for row in workers if row["phase"] == "pb-v2"]
                                assert v2_run and request["run_id"] == v2_run and accepted_body and checked_review
                                before_worker = snapshot(store)
                                queued_delta(initial, before_worker, info, v2_run, accepted_body["review"]["request_key"])
                                observer.save("v2-before-worker.json", before_worker)
                                cold = Store(settings.database_url, test_only=True)
                                cold_stores.append(cold)
                                entry = once(cold, settings, v2_run, THIRD, "pb-v2", observer, stage, wires, workers)
                                completed = snapshot(cold)
                                for table in ["delivery_graph_requests", "internal_run_bindings", "run_contracts", "grants"]:
                                    assert all(row in completed[table] for row in before_worker[table]), table
                                delivered = completed_delta(initial, completed, info, v2_run,
                                    accepted_body["review"]["request_key"], entry)
                                readonly = completed
                                observer.save("v2-after-worker.json", completed)
                                observer.save("v2-delivery.json", delivered)
                                answer = dict(status=200, text=json.dumps(dict(run_id=v2_run, status="SUCCEEDED", result_version=2)))
                            elif command == "checkpoint":
                                phase = request["phase"]
                                assert phase in {"seed-readonly", "v2-queued-before-worker", "v2-complete-after-manual-refresh",
                                    "run-navigation-late-old-get-ignored", "cold-four-downloads-and-navigation-readonly", "final-readonly"}
                                current = snapshot(store)
                                if phase == "v2-queued-before-worker":
                                    assert v2_run and not delivered and accepted_body
                                    queued_delta(initial, current, info, v2_run, accepted_body["review"]["request_key"])
                                    readonly = current
                                else:
                                    assert current == readonly
                                    if phase != "seed-readonly":
                                        assert delivered is not None
                                checkpoints.append(dict(phase=phase, run_id=request.get("run_id"), all_expected_rows_verified=True))
                                answer = dict(status=200, text="{}")
                            else:
                                assert command is None, "No other Worker/fixture mutation command is supported"
                                method, path, headers = request["method"], request["path"], request.get("headers", {})
                                if path.startswith("/api/"):
                                    assert {key.lower(): value for key, value in headers.items()}.get("authorization") == "Bearer synthetic-test-A"
                                args, raw = dict(headers=headers), b""
                                if "body_text" in request:
                                    raw = request["body_text"].encode("utf-8")
                                    assert json.loads(raw) == request["body"]
                                    args["content"] = raw
                                else:
                                    assert method == "GET" and request.get("body") is None
                                assert method == "GET" or path in {
                                    f"/api/internal/instances/{instance['id']}/pb-use-reviews",
                                    f"/api/internal/instances/{instance['id']}/pb-use-runs"}
                                reply = bridge.request(method, path, **args)
                                assert reply.request.content == raw
                                try:
                                    value = reply.json()
                                except ValueError:
                                    value = None
                                wire_http.append(dict(rpc_id=request["id"], method=method, path=path, body=request.get("body"),
                                    body_text=request.get("body_text"), body_bytes=len(raw), body_sha256=sha_bytes(raw),
                                    status=reply.status_code, response=value, response_text=reply.text,
                                    after_page_worker=delivered is not None,
                                    response_bytes=len(reply.content), response_sha256=sha_bytes(reply.content), headers=dict(reply.request.headers)))
                                observer.save("page-http.json", wire_http)
                                if method == "POST" and path.endswith("/pb-use-reviews"):
                                    assert checked_review is None and reply.status_code == 200
                                    checked_review = value
                                    assert value["request"] == request["body"]
                                    assert value["request"]["resource_id"] == third_resource and value["request"]["card_id"] == third_goal["id"]
                                    assert value["request"]["expected_source_hash"] == info["v2_hash"]
                                    assert value["review_fingerprint"] == fingerprint({key: val for key, val in value.items() if key != "review_fingerprint"})
                                    assert snapshot(store) == initial
                                if method == "POST" and path.endswith("/pb-use-runs"):
                                    assert v2_run is None and reply.status_code == 202 and checked_review
                                    accepted_body = request["body"]
                                    assert accepted_body == dict(review=checked_review["request"],
                                        expected_review_fingerprint=checked_review["review_fingerprint"], consent=use.CONSENT)
                                    v2_run = value["run_id"]
                                    assert v2_run != v1_run
                                    readonly = snapshot(store)
                                    queued_delta(initial, readonly, info, v2_run, accepted_body["review"]["request_key"])
                                answer = dict(status=reply.status_code, text=reply.text, content_type=reply.headers.get("content-type"))
                            answer["id"] = request["id"]
                            ipc.append(dict(direction="PYTHON_TO_NODE", value=answer))
                            process.stdin.write(json.dumps(answer) + "\n")
                            process.stdin.flush()
                process.stdin.close()
                code = process.wait(timeout=20)
                assert code == 0, observer.stderr_text()
                page = json.loads((tmp_path / "page-result.json").read_text(encoding="utf-8"))
                assert page["status"] == "PASS" and page["checks"] and page["actions"], page
                assert page["classification"] == "ACTUAL_HTTP_JSDOM_PB_V2_RUN_NAVIGATION_AND_FOUR_DOWNLOADS"
                assert page["worker_calls"] == 1 and page["app_id"] == app["id"] and page["instance_id"] == instance["id"]
                assert page["run_ids"] == [v1_run, v2_run] and delivered
                assert snapshot(store) == readonly
                assert len(observer.sent) == 3 and len(observer.runtime_sent) == 3
                assert [len(wires[name]) for name in ["generation", "source", "pb-v1", "pb-v2"]] == [3, 1, 1, 1]
                v2_wire = json.dumps(wires["pb-v2"], ensure_ascii=False)
                assert THIRD in v2_wire and SOURCE not in v2_wire and COLD not in v2_wire
                assert len(workers) == 3 and all(row["claims"] == 1 for row in workers)
                owner_v1 = [row["response"] for row in wire_http if row["path"] == owner_path
                    and row["status"] == 200 and row["after_page_worker"]]
                owner_v2 = [row["response"] for row in wire_http if row["path"] ==
                    f"/api/internal/instances/{instance['id']}/runs/{v2_run}/spec-owner-review"
                    and row["status"] == 200 and row["after_page_worker"]]
                assert owner_v1 and owner_v2
                assert all(value["owner_acceptance"] == "STALE" and not value["content_access"]
                    and not value.get("current") and not value.get("record") and value["history"] == info["v1_history"]
                    for value in owner_v1)
                assert all(value["owner_acceptance"] == "PENDING" and value["content_access"]
                    and value["sequence"] == 0 and value["history"] == [] and value["current"]["run_id"] == v2_run
                    and value["current"]["source_goal"]["card_id"] == third_goal["id"] for value in owner_v2)
                assert len(page["downloads"]) == 4
                assert {(row["run_id"], row["result_version"], row["format"]) for row in page["downloads"]} == {
                    (v1_run, 1, "json"), (v1_run, 1, "md"), (v2_run, 2, "json"), (v2_run, 2, "md")}
                for download in page["downloads"]:
                    request_row = page["requests"][download["artifact_request_index"]]
                    actual = one(wire_http, lambda row, rpc_id=download["artifact_rpc_id"]:
                        row["rpc_id"] == rpc_id, "One actual artifact GET")
                    assert request_row["rpc_id"] == actual["rpc_id"] and actual["method"] == "GET" and actual["status"] == 200
                    assert actual["path"] == download["artifact_path"] == f"/api/internal/app-run-jobs/{download['run_id']}/spec-artifact"
                    artifact = actual["response"]
                    assert artifact["result_version"] == download["result_version"] and artifact["run_id"] == download["run_id"]
                    assert artifact["resource"]["resource_id"] == download["resource_id"]
                    assert actual["response_sha256"] == download["artifact_get_sha256"]
                    content = artifact["resource"]["content"] if download["format"] == "json" else artifact["markdown_view"]
                    blob = content.encode("utf-8")
                    assert download["resource_content_sha256"] == sha_bytes(artifact["resource"]["content"].encode())
                    assert download["blob_utf8_sha256"] == sha_bytes(blob) and download["blob_bytes"] == len(blob)
                    assert download["blob_utf8_hex"] == blob.hex()
                assets = page["static_resource_loads"]
                expected = {"/", "/app.css", *re.findall(r'<script[^>]+src="([^"]+)"',
                    (root / "src/sim2act/web/index.html").read_text())}
                assert len(expected) == 27 and page["boots"] >= 2
                for boot in range(1, page["boots"] + 1):
                    rows = [row for row in assets if row["boot"] == boot]
                    assert len(rows) == 27 and {row["path"] for row in rows} == expected
                for asset in assets:
                    path = root / "src/sim2act/web" / (asset["path"].lstrip("/") or "index.html")
                    assert asset["status"] == 200 and asset["sha256"] == sha_bytes(path.read_bytes())
                assert sources(root) == before_sources
                proof.update(status="PASS", app_id=app["id"], release_id=release["id"], instance_id=instance["id"],
                    v1_run=v1_run, v2_run=v2_run, typed_versions=[1, 2], generation_mock_requests=3,
                    source_mock_requests=1, pb_v1_mock_requests=1, pb_v2_mock_requests=1, total_mock_requests=6,
                    generation_worker_calls=1, business_worker_calls=3, page_worker_calls=1, single_claim_per_business_run=True,
                    page_derived_read_grants=3, page_new_save_grants=0, page_new_runtime_or_app_or_release_or_instance=0,
                    v1_typed_artifact_and_owner_rows_unchanged=True, downloads=4, asset_hashes_per_boot=27)
        finally:
            if process is not None:
                observer.kill_owned_node("NATURAL_NAVIGATION_FINALLY")
                if process.poll() is None:
                    process.wait(timeout=10)
            observer.save("proof.json", proof)
            observer.save("page-http.json", wire_http)
            observer.save("ipc.json", ipc)
            observer.save("checkpoints.json", checkpoints)
            observer.save("business-workers.json", workers)
            observer.save("stage-wires.json", wires)
            observer.save("source-after.json", sources(root))
            try:
                observer.save("final-rows.json", snapshot(store))
                for label, rid in [("source", source_run), ("pb-v1", v1_run), ("pb-v2", v2_run)]:
                    if rid:
                        observer.save(label + "-claims-finally.json", header(store, rid))
            finally:
                for client in clients:
                    client.close()
                for cold in cold_stores:
                    cold.engine.dispose()
                store.engine.dispose()
