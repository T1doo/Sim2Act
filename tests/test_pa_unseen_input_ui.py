"""Synthetic P-A page: explicit human declarations, bounded preview, unseen input.

No close/P-B fixture is used. One normal generated app/Release/instance produces
v1, then the page explicitly accepts its items and runs saved THIRD as v2.
"""

import base64
import copy
import json
import os
import re
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from test_natural_result_navigation_ui import header, once, sha_bytes, trace_http
from test_natural_spec_apps import SOURCE, enqueue, material, ready
from test_pa_natural_spec_ui import _PageObserver
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_uses as use
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, fingerprint

BAD = "A" * 2049
OWNER_REASON_PREFIX = "SIMULATED_TEST_ONLY: automated fixture gesture, NOT a real human semantic judgment; criterion "


def sources(root):
    paths = sorted(path for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"})
    paths += [Path(__file__).resolve(), Path(__file__).with_name("pa_unseen_input_ui.cjs").resolve()]
    paths += [root / "tests" / name for name in ["durable_browser.cjs", "test_natural_result_navigation_ui.py",
        "test_natural_spec_apps.py", "test_pa_spec_apps.py", "test_goal_text_applications.py",
        "test_pa_natural_spec_ui.py", "test_pb_natural_uses.py", "test_spec_app_operations.py"]]
    return {str(path.relative_to(root)) if path.is_relative_to(root) else str(path):
        dict(bytes=path.stat().st_size, sha256=sha_bytes(path.read_bytes())) for path in paths}


def ok(reply, status=200):
    assert reply.status_code == status, reply.text
    return reply.json()


def assert_owner_delta(before, after, info, requests, records, contract):
    for table in before:
        if table not in {"natural_owner_records", "natural_owner_seals"}:
            assert after[table] == before[table], table
    added = appended(before, after, "natural_owner_records")
    seals = appended(before, after, "natural_owner_seals")
    assert len(added) == len(seals) == 2
    assert [row["kind"] for row in sorted(added, key=lambda row: row["sequence"])] == ["PREPARE", "DECIDE"]
    previous = ""
    for sequence, command, status in [(1, "PREPARE", "PENDING"), (2, "DECIDE", "ACCEPTED")]:
        row = one(added, lambda row, seq=sequence: row["sequence"] == seq, "One exact owner row")
        assert row["run_id"] == info["v1_run"] and row["instance_id"] == info["instance"]
        assert row["principal_id"] == info["principal"] and row["project_id"] == info["project"]
        assert row["kind"] == command and row["status"] == status and row["previous_fingerprint"] == previous
        assert row["request_fingerprint"] == fingerprint(requests[command])
        assert row["request_key"] == requests[command]["request_key"]
        assert row["id"] == records[command]["id"] and row["fingerprint"] == records[command]["fingerprint"]
        value = row["payload"]
        assert value["request"] == requests[command] and value["contract"] == contract
        assert value["metadata"] == {key: item for key, item in row.items() if key not in {"payload", "fingerprint"}}
        assert row["fingerprint"] == fingerprint(value)
        sealed = one(seals, lambda item, record_id=row["id"]: item["record_id"] == record_id, "One exact owner seal")
        assert sealed["run_id"] == info["v1_run"]
        assert sealed["metadata_fingerprint"] == fingerprint({key: item for key, item in row.items() if key != "payload"})
        assert sealed["payload_fingerprint"] == row["fingerprint"]
        previous = row["fingerprint"]
    assert one(added, lambda row: row["kind"] == "DECIDE", "One decision")["payload"]["choices"] == requests["DECIDE"]["choices"]
    return dict(records=added, seals=seals)


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
    assert binding[0]["snapshot"]["pa_use"]["review"]["resource_id"] == info["v2_resource"]
    assert binding[0]["snapshot"]["spec_goal"]["card_id"] == info["v2_goal"]
    assert binding[0]["snapshot"]["pa_base_data_version"] == 1
    assert len(appended(before, after, "run_contracts")) == 1
    permissions = appended(before, after, "grants")
    assert len(permissions) == 1
    assert {(row["principal_id"], row["project_id"], row["resource_id"], row["tool_ref"], row["revoked"])
        for row in permissions} == {(info["runtime"], info["project"], info["v2_resource"], "resource.read", False)}
    journal = appended(before, after, "delivery_graph_requests")
    assert len(journal) == 6
    assert {(row["app_id"], row["kind"], row["request_key"]) for row in journal} == {
        (rid, spec.RUN_META, "accepted"), (rid, spec.RUN_META + "_seal", "accepted"),
        (rid, use.PA.meta, "accepted"), (rid, use.PA.meta + "_seal", "accepted"),
        (info["instance"], use.PA.use, key), (info["instance"], use.PA.use + "_seal", key)}
    assert all(row["fingerprint"] == fingerprint(row["snapshot"]) for row in journal)
    assert all(row["run_id"] == rid for row in appended(before, after, "events"))
    return app_run[0]["id"]


def completed_delta(before, after, info, rid, key, worker, model_request):
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
    journal = appended(before, after, "delivery_graph_requests")
    attempt = appended(before, after, "attempts")[0]
    attempt_id = attempt["id"]
    archive_kinds = {"natural_source_request_body.v1", "natural_source_response_body.v1"}
    assert len(journal) == 10
    assert {(row["app_id"], row["kind"], row["request_key"]) for row in journal} == {
        (rid, spec.RUN_META, "accepted"), (rid, spec.RUN_META + "_seal", "accepted"),
        (rid, use.PA.meta, "accepted"), (rid, use.PA.meta + "_seal", "accepted"),
        (info["instance"], use.PA.use, key), (info["instance"], use.PA.use + "_seal", key),
        *((rid, kind + suffix, attempt_id) for kind in archive_kinds for suffix in ["", "_seal"])}
    assert all(row["principal_id"] == info["principal"] and row["fingerprint"] == fingerprint(row["snapshot"])
        and row["request_fingerprint"] == fingerprint(row["snapshot"]["request"]) for row in journal)
    for kind in archive_kinds:
        original = one(journal, lambda row, kind=kind: row["kind"] == kind, "One original offline body archive")
        sealed = one(journal, lambda row, kind=kind: row["kind"] == kind + "_seal", "One matching offline body seal")
        assert original["snapshot"] == sealed["snapshot"]
        body = original["snapshot"]["request"]
        assert body == original["snapshot"]["response"]
        assert body["version"] == "natural-source-body-archive.v1"
        assert body["phase"] == ("RESERVED_REQUEST" if kind == "natural_source_request_body.v1" else "RECEIVED_DECODED_BODY")
        assert body["run_id"] == rid and body["attempt_id"] == attempt_id
        assert body["principal_id"] == info["principal"] and body["project_id"] == info["project"]
        assert body["runtime_id"] == info["runtime"] and body["provenance"] == "OFFLINE_MOCKTRANSPORT"
        assert body["received_complete"] and body["extent"] == "COMPLETE_BODY" and body["omission"] == "NONE"
        raw = base64.b64decode(body["body_b64"], validate=True)
        assert body["byte_count"] == len(raw) and body["sha256"] == sha_bytes(raw)
        assert original["request_fingerprint"] == sealed["request_fingerprint"] == fingerprint(body)
        if kind == "natural_source_request_body.v1":
            wire = attempt["parameters"]["natural_spec_wire"]
            assert body["sha256"] == wire["sha256"] and len(raw) == wire["bytes"]
            assert json.loads(raw) == model_request and body["canonical_sha256"] is None
        else:
            response = attempt["response"]
            canonical = json.dumps(json.loads(raw), ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("ascii")
            assert canonical == response["received_raw"].encode("ascii")
            assert response["raw_evidence"] == dict(status="COMPLETE", bytes=len(canonical), sha256=sha_bytes(canonical))
            assert body["canonical_sha256"] == sha_bytes(canonical)
    assert all(row["run_id"] == rid for row in appended(before, after, "events"))
    return dict(app_run=app_run[0], typed=typed[0], artifact=resource[0], derived_read_grants=permissions)


def test_pa_saved_unseen_input_after_explicit_simulated_owner_acceptance(tmp_path):
    root = Path.cwd().resolve()
    settings = Settings("sqlite:///" + str(tmp_path / "fixture.db"), tmp_path, mode="mock", goal_planner_provider="intern-s2")
    store = Store(settings.database_url, test_only=True)
    clients, cold_stores, workers, http, ipc, checkpoints = [], [], [], [], [], []
    stage, wires = dict(name="generation"), {name: [] for name in ["generation", "pa-v1", "pa-v2"]}
    v1_run = v2_run = process = None
    proof = dict(status="NOT_COMPLETED", real_model_requests=0, native_browser="NOT_RUN", windows="NOT_RUN",
        pg="NOT_RUN", remote_ci="NOT_RUN", real_human_semantic_acceptance="NOT_RUN",
        qualification_scope="ONE_SYNTHETIC_PA_UNSEEN_INPUT_PAGE_NOT_COMPLETE_PA")
    with _PageObserver(tmp_path, "PA_EXPLICIT_OWNER_THEN_SAVED_UNSEEN_INPUT") as observer:
        before_sources = sources(root)
        observer.save("source-before.json", before_sources)
        try:
            store.initialize()
            user = store.user("PA unseen fixture A", "synthetic-test-A")
            client = TestClient(create_app(store, settings))
            clients.append(client)
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            wire_lock = threading.Lock()
            trace_http(client, observer, wire_lock)
            project = ok(client.post("/api/projects", json=dict(name="P-A saved unseen material")), 201)["id"]
            source_resource, source_goal = material(client, project, SOURCE)
            data = store, settings, client, user, project, source_resource, source_goal
            observer.save("fixture-before-generation.json", snapshot(store))
            import test_natural_spec_apps as original_fixture
            original_transport = original_fixture.httpx.MockTransport

            def observed_transport(handler):
                name = handler.__qualname__
                assert name in {"generate.<locals>.handler", "transport.<locals>.handler"}, name
                def capture(request):
                    payload = json.loads(request.content)
                    phase = "generation" if name == "generate.<locals>.handler" else stage["name"]
                    assert phase in wires
                    wires[phase].append(payload)
                    (observer.sent if phase == "generation" else observer.runtime_sent).append(payload)
                    observer.save(phase + "-wire.json", wires[phase])
                    return handler(request)
                return original_transport(capture)

            fixture_httpx = SimpleNamespace(MockTransport=observed_transport, Response=original_fixture.httpx.Response)
            with patch.object(original_fixture, "httpx", fixture_httpx):
                with observer.phase("normal_pa_generation_release_instance"):
                    _, app_id, release, instance, returned_wire = ready(data, "single")
                assert len(returned_wire) == 3 and returned_wire == wires["generation"]
                app = ok(client.get("/api/apps/" + app_id))
                assert "spec_task" not in app["candidate"]
                v1_run = enqueue(data, release, instance, key="pa-unseen-v1")
                once(store, settings, v1_run, SOURCE, "pa-v1", observer, stage, wires, workers)
                v1_artifact = ok(client.get(f"/api/internal/app-run-jobs/{v1_run}/spec-artifact"))
                assert v1_artifact["result_version"] == 1
                assert json.loads(v1_artifact["resource"]["content"])["source_content"] == SOURCE
                observer.save("v1-before-target-fixtures.json", snapshot(store))
                third_resource, third_goal = material(client, project, THIRD, "P-A saved unseen THIRD Goal")
                bad_resource, bad_goal = material(client, project, BAD, "P-A exact oversized source Goal")
                assert len(BAD.encode("utf-8")) == 2049
                initial = snapshot(store)
                assert initial["natural_owner_records"] == [] and initial["natural_owner_seals"] == []
                readonly, accepted_rows = initial, None
                observer.save("page-initial-rows.json", initial)
                info = dict(project=project, principal=user, app=app_id, app_name=app["name"], name=app["name"],
                    runtime=app["runtime_id"], release=release["id"], instance=instance["id"],
                    v1_run=v1_run, v1_goal=source_goal["id"], v1_resource=source_resource, v1_content=SOURCE,
                    v2_goal=third_goal["id"], v2_resource=third_resource, v2_content=THIRD, v2_hash=sha_bytes(THIRD.encode()),
                    bad_goal=bad_goal["id"], bad_resource=bad_resource, bad_content=BAD, bad_bytes=2049,
                    bad_hash=sha_bytes(BAD.encode()), output=str(tmp_path / "page-result.json"),
                    storage_path=str(tmp_path / "durable-storage.json"))
                observer.save("info.json", info)
                owner_path = f"/api/internal/instances/{instance['id']}/runs/{v1_run}/spec-owner-review"
                owner_state = owner_contract = checked_review = accepted_body = delivered = None
                owner_requests, owner_records = {}, {}
                bridge = TestClient(create_app(store, settings))
                clients.append(bridge)
                trace_http(bridge, observer, wire_lock)
                process = subprocess.Popen(["node", str(Path(__file__).with_name("pa_unseen_input_ui.cjs")),
                    str(tmp_path / "info.json")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=observer.driver, text=True, env={**os.environ,
                        "NODE_PATH": str(root / "scripts/engineering-ci/node_modules")})
                observer.own_node(process)
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
                                assert v2_run and request["run_id"] == v2_run and accepted_body and checked_review
                                assert not [row for row in workers if row["phase"] == "pa-v2"]
                                before_worker = snapshot(store)
                                queued_delta(accepted_rows, before_worker, info, v2_run, accepted_body["review"]["request_key"])
                                observer.save("v2-before-worker.json", before_worker)
                                cold = Store(settings.database_url, test_only=True)
                                cold_stores.append(cold)
                                entry = once(cold, settings, v2_run, THIRD, "pa-v2", observer, stage, wires, workers)
                                after_worker = snapshot(cold)
                                for table in ["delivery_graph_requests", "internal_run_bindings", "run_contracts", "grants"]:
                                    assert all(row in after_worker[table] for row in before_worker[table]), table
                                delivered = completed_delta(accepted_rows, after_worker, info, v2_run,
                                    accepted_body["review"]["request_key"], entry, wires["pa-v2"][0])
                                readonly = after_worker
                                observer.save("v2-after-worker.json", after_worker)
                                observer.save("v2-delivery.json", delivered)
                                answer = dict(status=200, text=json.dumps(dict(run_id=v2_run, status="SUCCEEDED", result_version=2)))
                            elif command == "checkpoint":
                                phase = request["phase"]
                                assert phase in {"seed-readonly", "v1-simulated-owner-accepted", "oversized-preview-rejected",
                                    "v2-queued-before-worker", "v2-complete-after-manual-refresh", "cold-two-versions-readonly", "final-readonly"}
                                current = snapshot(store)
                                if phase == "v1-simulated-owner-accepted":
                                    assert accepted_rows is None and owner_contract and set(owner_requests) == {"PREPARE", "DECIDE"}
                                    assert owner_state["owner_acceptance"] == "ACCEPTED" and owner_state["sequence"] == 2
                                    owner_delta = assert_owner_delta(initial, current, info, owner_requests, owner_records, owner_contract)
                                    accepted_rows = readonly = current
                                    observer.save("v1-accepted-rows.json", current)
                                    observer.save("simulated-owner-evidence.json", dict(requests=owner_requests, records=owner_records,
                                        contract=owner_contract, delta=owner_delta, history=owner_state["history"],
                                        simulated=True, real_human_semantic_acceptance="NOT_RUN"))
                                elif phase == "v2-queued-before-worker":
                                    assert accepted_rows and accepted_body and v2_run and not delivered
                                    queued_delta(accepted_rows, current, info, v2_run, accepted_body["review"]["request_key"])
                                    readonly = current
                                else:
                                    assert current == readonly
                                    if phase == "oversized-preview-rejected":
                                        assert accepted_rows and checked_review is None and v2_run is None
                                        assert len(wires["pa-v2"]) == 0 and len(observer.runtime_sent) == 1
                                    elif phase not in {"seed-readonly"}:
                                        assert delivered is not None
                                checkpoints.append(dict(phase=phase, all_expected_rows_verified=True))
                                answer = dict(status=200, text="{}")
                            else:
                                assert command is None, "Only one exact Worker command and read-only checkpoints are supported"
                                method, path, headers = request["method"], request["path"], request.get("headers", {})
                                clean_path = path.split("?", 1)[0]
                                if path.startswith("/api/"):
                                    assert {key.lower(): value for key, value in headers.items()}.get("authorization") == "Bearer synthetic-test-A"
                                args, raw = dict(headers=headers), b""
                                if "body_text" in request:
                                    raw = request["body_text"].encode("utf-8")
                                    assert json.loads(raw) == request["body"]
                                    args["content"] = raw
                                else:
                                    assert method == "GET" and request.get("body") is None
                                allowed_posts = {owner_path + "-requests", f"/api/internal/instances/{instance['id']}/pa-use-reviews",
                                    f"/api/internal/instances/{instance['id']}/pa-use-runs"}
                                assert method == "GET" or (method == "POST" and clean_path in allowed_posts)
                                if method == "POST" and clean_path == owner_path + "-requests":
                                    body = request["body"]
                                    action = body["command"]
                                    assert action in {"PREPARE", "DECIDE"} and action not in owner_requests
                                    assert owner_state and owner_state["content_access"] and owner_state["current"]["run_id"] == v1_run
                                    if action == "PREPARE":
                                        assert not owner_requests and body["expected_sequence"] == 0
                                        assert body["expected_contract_fingerprint"] == fingerprint(owner_state["current"])
                                        owner_contract = copy.deepcopy(owner_state["current"])
                                        assert owner_contract["source_goal"]["card_id"] == source_goal["id"]
                                        assert owner_contract["output"]["checklist"]["source_content"] == SOURCE
                                    else:
                                        assert set(owner_requests) == {"PREPARE"} and body["expected_sequence"] == 1
                                        assert fingerprint(owner_state["current"]) == fingerprint(owner_contract)
                                        record = owner_state["record"]
                                        assert record["kind"] == "PREPARE" and record["fingerprint"] == fingerprint(record["payload"])
                                        assert body["review_id"] == record["id"] and body["review_fingerprint"] == record["fingerprint"]
                                        assert [choice["item_id"] for choice in body["choices"]] == [item["id"] for item in owner_contract["items"]]
                                        assert all(choice["decision"] == "ACCEPT" and
                                            choice["reason"] == OWNER_REASON_PREFIX + choice["item_id"] for choice in body["choices"])
                                    owner_requests[action] = copy.deepcopy(body)
                                reply = bridge.request(method, path, **args)
                                assert reply.request.content == raw
                                try:
                                    value = reply.json()
                                except ValueError:
                                    value = None
                                http.append(dict(rpc_id=request["id"], method=method, path=path, body=request.get("body"),
                                    body_text=request.get("body_text"), body_bytes=len(raw), body_sha256=sha_bytes(raw),
                                    status=reply.status_code, response=value, response_text=reply.text,
                                    response_sha256=sha_bytes(reply.content), after_page_worker=delivered is not None))
                                observer.save("page-http.json", http)
                                if method == "GET" and clean_path == owner_path and reply.status_code == 200:
                                    owner_state = copy.deepcopy(value)
                                if method == "POST" and clean_path == owner_path + "-requests":
                                    assert reply.status_code == 201 and value["formal_publication_enabled"] is False
                                    record = value["record"]
                                    action = request["body"]["command"]
                                    assert record["kind"] == action and record["request_fingerprint"] == fingerprint(request["body"])
                                    assert record["status"] == ("PENDING" if action == "PREPARE" else "ACCEPTED")
                                    owner_records[action] = copy.deepcopy(record)
                                if method == "POST" and clean_path.endswith("/pa-use-reviews"):
                                    body = request["body"]
                                    assert accepted_rows is not None and snapshot(store) == accepted_rows
                                    if body["resource_id"] == bad_resource:
                                        assert body["card_id"] == bad_goal["id"] and body["expected_source_hash"] == info["bad_hash"]
                                        assert body["expected_goal_version"] == bad_goal["version"] and body["expected_goal_fingerprint"] == bad_goal["fingerprint"]
                                        assert reply.status_code == 400 and value["error"]["code"] == "INVALID_INPUT"
                                        assert not wires["pa-v2"] and v2_run is None
                                        observer.save("oversized-preview-proof.json", dict(request=body, response=value,
                                            status=reply.status_code, actual_bytes=2049, source_bound_bytes=2048,
                                            matching_saved_goal=True, all_tables_unchanged=True, new_mock_requests=0))
                                    else:
                                        assert body["resource_id"] == third_resource and body["card_id"] == third_goal["id"]
                                        assert checked_review is None and reply.status_code == 200
                                        checked_review = value
                                        assert value["request"] == body and body["expected_source_hash"] == info["v2_hash"]
                                        assert value["namespace"] == use.PA.namespace and value["instance_data_version"] == 1
                                        assert value["review_fingerprint"] == fingerprint({key: val for key, val in value.items() if key != "review_fingerprint"})
                                if method == "POST" and clean_path.endswith("/pa-use-runs"):
                                    assert accepted_rows is not None and v2_run is None and reply.status_code == 202 and checked_review
                                    accepted_body = request["body"]
                                    assert accepted_body == dict(review=checked_review["request"],
                                        expected_review_fingerprint=checked_review["review_fingerprint"], consent=use.PA_CONSENT)
                                    v2_run = value["run_id"]
                                    assert v2_run != v1_run
                                    readonly = snapshot(store)
                                    queued_delta(accepted_rows, readonly, info, v2_run, accepted_body["review"]["request_key"])
                                answer = dict(status=reply.status_code, text=reply.text, content_type=reply.headers.get("content-type"))
                            answer["id"] = request["id"]
                            ipc.append(dict(direction="PYTHON_TO_NODE", value=answer))
                            process.stdin.write(json.dumps(answer) + "\n")
                            process.stdin.flush()
                process.stdin.close()
                assert process.wait(timeout=20) == 0, observer.stderr_text()
                page = json.loads((tmp_path / "page-result.json").read_text(encoding="utf-8"))
                assert page["status"] == "PASS" and page["checks"] and page["actions"], page
                assert page["classification"] == "ACTUAL_HTTP_JSDOM_PA_UNSEEN_INPUT_FULL_PAGE"
                assert page["worker_calls"] == 1 and page["app_id"] == app_id and page["instance_id"] == instance["id"]
                assert page["run_ids"] == [v1_run, v2_run] and delivered
                assert snapshot(store) == readonly and accepted_rows
                assert [len(wires[name]) for name in ["generation", "pa-v1", "pa-v2"]] == [3, 1, 1]
                assert len(observer.sent) == 3 and len(observer.runtime_sent) == 2 and len(workers) == 2
                assert all(row["claims"] == 1 for row in workers)
                v2_wire = json.dumps(wires["pa-v2"], ensure_ascii=False)
                assert THIRD in v2_wire and SOURCE not in v2_wire and BAD not in v2_wire
                owner1 = [row["response"] for row in http if row["path"].split("?", 1)[0] == owner_path
                    and row["status"] == 200 and row["after_page_worker"]]
                owner2_path = f"/api/internal/instances/{instance['id']}/runs/{v2_run}/spec-owner-review"
                owner2 = [row["response"] for row in http if row["path"].split("?", 1)[0] == owner2_path
                    and row["status"] == 200 and row["after_page_worker"]]
                assert owner1 and owner2
                old_metadata = [{key: value for key, value in row.items() if key != "payload"}
                    for row in sorted(accepted_rows["natural_owner_records"], key=lambda row: row["sequence"])]
                assert all(value["owner_acceptance"] == "STALE" and not value["content_access"]
                    and not value.get("current") and not value.get("record") and value["history"] == old_metadata for value in owner1)
                assert all(value["owner_acceptance"] == "PENDING" and value["content_access"] and value["sequence"] == 0
                    and value["history"] == [] and value["current"]["run_id"] == v2_run for value in owner2)
                for table in ["natural_owner_records", "natural_owner_seals"]:
                    assert readonly[table] == accepted_rows[table]
                assert page["v1_accepted_history"] == old_metadata
                assert page["simulated_owner_choices"] == owner_requests["DECIDE"]["choices"]
                bad_view = page["bad_preview"]
                bad_http = one(http, lambda row: row["rpc_id"] == bad_view["rpc_id"], "One actual oversized preview")
                assert bad_http["status"] == bad_view["status"] == 400 and bad_view["utf8_bytes"] == 2049
                assert bad_http["response"]["error"] == bad_view["error"] and bad_view["error"]["code"] == "INVALID_INPUT"
                assert bad_http["response_sha256"] == bad_view["actual_response_sha256"]
                viewed = page["viewed_results"]
                assert len(viewed) == 2 and {(row["run_id"], row["result_version"]) for row in viewed} == {(v1_run, 1), (v2_run, 2)}
                for view in viewed:
                    request_row = page["requests"][view["artifact_request_index"]]
                    actual = one(http, lambda row, rpc_id=view["artifact_rpc_id"]: row["rpc_id"] == rpc_id, "One cold artifact GET")
                    assert request_row["rpc_id"] == actual["rpc_id"] and actual["method"] == "GET" and actual["status"] == 200
                    assert actual["path"] == f"/api/internal/app-run-jobs/{view['run_id']}/spec-artifact"
                    saved = actual["response"]
                    assert actual["response_sha256"] == view["artifact_get_sha256"]
                    assert saved["result_version"] == view["result_version"] and saved["run_id"] == view["run_id"]
                    record = one(readonly["internal_instance_data"], lambda row, version=view["result_version"]:
                        row["instance_id"] == instance["id"] and row["version"] == version, "One exact typed version")
                    output = record["data"]["result"]
                    assert saved["resource"]["resource_id"] == view["resource_id"] == output["resource_id"]
                    assert saved["output_fingerprint"] == view["output_fingerprint"] == fingerprint(output)
                    assert saved["resource"]["content"] == json.dumps(output["checklist"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    assert saved["resource"]["hash"] == view["resource_content_sha256"] == sha_bytes(saved["resource"]["content"].encode())
                    expected_source = SOURCE if view["result_version"] == 1 else THIRD
                    expected_resource = source_resource if view["result_version"] == 1 else third_resource
                    assert output["checklist"]["source_content"] == expected_source
                    assert output["checklist"]["source"]["resource_id"] == view["source_resource_id"] == expected_resource
                expected = {"/", "/app.css", *re.findall(r'<script[^>]+src="([^"]+)"',
                    (root / "src/sim2act/web/index.html").read_text())}
                assert len(expected) == 27 and page["boots"] >= 2
                assets = page["static_resource_loads"]
                for boot in range(1, page["boots"] + 1):
                    rows = [row for row in assets if row["boot"] == boot]
                    assert len(rows) == 27 and {row["path"] for row in rows} == expected
                for asset in assets:
                    path = root / "src/sim2act/web" / (asset["path"].lstrip("/") or "index.html")
                    assert asset["status"] == 200 and asset["sha256"] == sha_bytes(path.read_bytes())
                assert sources(root) == before_sources
                proof.update(status="PASS", app_id=app_id, instance_id=instance["id"], release_id=release["id"],
                    v1_run=v1_run, v2_run=v2_run, total_mock_requests=5, generation_mock_requests=3,
                    v1_mock_requests=1, v2_mock_requests=1, business_worker_calls=2, generation_worker_calls=1,
                    page_worker_calls=1, simulated_owner_records=2, simulated_owner_seals=2,
                    oversized_preview_status=400, oversized_preview_new_run_or_grant_or_model=0,
                    page_derived_read_grants=3, page_new_save_grants=0, queued_journal_rows=6, completed_journal_rows=10,
                    new_app_runtime_release_instance=0, preserved_v1_owner_and_typed_artifact=True)
        finally:
            if process is not None:
                observer.kill_owned_node("PA_UNSEEN_PAGE_FINALLY")
                if process.poll() is None:
                    process.wait(timeout=10)
            observer.save("proof.json", proof)
            observer.save("page-http.json", http)
            observer.save("ipc.json", ipc)
            observer.save("checkpoints.json", checkpoints)
            observer.save("stage-wires.json", wires)
            observer.save("business-workers.json", workers)
            observer.save("source-after.json", sources(root))
            try:
                observer.save("final-rows.json", snapshot(store))
                for label, rid in [("pa-v1", v1_run), ("pa-v2", v2_run)]:
                    if rid:
                        observer.save(label + "-claims-finally.json", header(store, rid))
            finally:
                for client in clients:
                    client.close()
                for cold in cold_stores:
                    cold.engine.dispose()
                store.engine.dispose()

