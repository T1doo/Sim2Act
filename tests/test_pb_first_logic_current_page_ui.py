"""One current-page first local P-B logic change; all inference is offline Mock.

Fresh parallel source and original P-B COLD v1 are fixtures. The page checks the
changed dependency in isolation, confirms a new Release and uses THIRD once.
"""

import base64
import copy
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from test_natural_result_navigation_ui import header, sha_bytes, trace_http
from test_natural_spec_apps import COLD, SOURCE, enqueue, material, ready, transport
from test_pa_natural_spec_ui import _PageObserver
from test_pa_spec_apps import instance as release_instance
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import natural_logic_patches as logic
from sim2act import natural_specs as natural
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, fingerprint
from sim2act.worker import Worker


def sources(root):
    paths = sorted(path for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"})
    paths += [Path(__file__).resolve(), Path(__file__).with_name("pb_first_logic_current_page_ui.cjs").resolve()]
    paths += [root / "tests" / name for name in ["durable_browser.cjs", "test_natural_result_navigation_ui.py",
        "test_natural_spec_apps.py", "test_pa_spec_apps.py", "test_goal_text_applications.py",
        "test_pa_natural_spec_ui.py", "test_pb_natural_uses.py", "test_spec_app_operations.py"]]
    return {str(path.relative_to(root)) if path.is_relative_to(root) else str(path):
        dict(bytes=path.stat().st_size, sha256=sha_bytes(path.read_bytes())) for path in paths}


def ok(reply, status=200):
    assert reply.status_code == status, reply.text
    return reply.json()


def one(rows, predicate, label):
    values = [row for row in rows if predicate(row)]
    assert len(values) == 1, (label, values)
    return values[0]


def added(before, after, table):
    assert all(row in after[table] for row in before[table]), table
    return [row for row in after[table] if row not in before[table]]


def only_tables(before, after, allowed):
    assert before.keys() == after.keys()
    for table in before:
        if table not in allowed:
            assert before[table] == after[table], table


def journal_pairs(before, after, expected):
    rows = added(before, after, "delivery_graph_requests")
    assert len(rows) == 2 * len(expected)
    assert {(row["app_id"], row["kind"], row["request_key"]) for row in rows} == {
        (app, kind + suffix, key) for app, kind, key in expected for suffix in ["", "_seal"]}
    for app, kind, key in expected:
        left = one(rows, lambda row, a=app, k=kind, q=key:
            (row["app_id"], row["kind"], row["request_key"]) == (a, k, q), "Original metadata")
        right = one(rows, lambda row, a=app, k=kind, q=key:
            (row["app_id"], row["kind"], row["request_key"]) == (a, k + "_seal", q), "Independent seal")
        assert left["snapshot"] == right["snapshot"]
        assert left["request_fingerprint"] == right["request_fingerprint"] == fingerprint(left["snapshot"]["request"])
        assert left["fingerprint"] == right["fingerprint"] == fingerprint(left["snapshot"])
    return rows


def normal_worker(store, settings, rid, content, phase, observer, stage, wires, workers):
    accepted = header(store, rid)
    assert accepted["job"]["status"] == "QUEUED" and not accepted["claims"]
    stage["name"] = phase
    count = len(wires[phase])
    worker = Worker(store, settings, goal_planner_transport=transport([], content))
    original = accepted["job"]["created_at"]
    deadline = min(accepted["clock"]["deadline"], original + settings.run_seconds)
    claims = []
    observer.save(phase + "-before.json", accepted)
    try:
        current = accepted
        for index in range(3):
            before = current
            if index:
                assert before["job"]["status"] == "RUNNING" and not before["job"]["cancel_intent"]
                assert time.time() >= before["job"]["lease_until"] and time.time() < deadline
                with store.tx() as connection:
                    assert not store.has_unknown(connection, rid)
            wire_before = len(wires[phase])
            with observer.phase("normal_worker_claim", phase=phase, run_id=rid, worker_id=worker.id, index=index):
                claimed = worker.once()
            current = header(store, rid)
            claims.append(dict(index=index, before=before, after=current, claimed=claimed,
                wire_before=wire_before, wire_after=len(wires[phase])))
            observer.save(phase + "-claims.json", claims)
            assert claimed and current["job"]["created_at"] == original and current["clock"] == accepted["clock"]
            assert current["job"]["fence"] > before["job"]["fence"]
            assert len([row for row in current["claims"] if row["data"]["fence"] == current["job"]["fence"]]) == 1
            if current["job"]["status"] == "SUCCEEDED":
                assert len(wires[phase]) - count == 2
                entry = dict(phase=phase, run_id=rid, worker_id=worker.id, worker_calls=len(claims),
                    mock_requests=len(wires[phase]) - count, claims=len(current["claims"]), status="SUCCEEDED",
                    accepted_clock_unchanged=True, test_clock_lease_deadline_mutations=0)
                workers.append(entry)
                return entry
        raise AssertionError("Normal bounded worker claims did not succeed")
    finally:
        observer.save(phase + "-finally.json", header(store, rid))
        observer.save(phase + "-claims.json", claims)
        observer.save("business-workers.json", workers)


def validate_preview(value, request, old_candidate, info):
    assert request["consume_prior_feedback"] is True
    assert value["namespace"] == logic.VERSION and value["request_key"] == request["request_key"]
    assert value["preview_fingerprint"] == fingerprint({key: item for key, item in value.items() if key != "preview_fingerprint"})
    candidate = value["effective_candidate"]
    assert value["effective_fingerprint"] == fingerprint(candidate)
    assert candidate["manifest"]["revision"] == 2 and candidate["actions"][2]["revision"] == 2
    assert [row["action_id"] for row in candidate["actions"]] == [row["action_id"] for row in old_candidate["actions"]]
    assert len(candidate["actions"]) == 6 and len(value["preserved_action_definitions"]) == 5
    assert all(candidate["actions"][i] == old_candidate["actions"][i] for i in [0, 1, 3, 4, 5])
    before = copy.deepcopy(old_candidate["spec_recipe"])
    after = copy.deepcopy(candidate["spec_recipe"])
    prior, changed = after["steps"][1:3]
    assert "prior_items" not in before["steps"][2]["inputs"]
    assert changed["inputs"]["prior_items"] == dict(source="step", ref=prior["step_id"], field="items")
    assert changed["inputs"]["prior_feedback"] == dict(source="step", ref=prior["step_id"], field="feedback")
    changed["inputs"].pop("prior_items")
    changed["inputs"].pop("prior_feedback")
    changed["depends_on"] = before["steps"][2]["depends_on"]
    assert after == before
    assert value["context"]["instance_id"] == info["old_instance"]
    assert value["context"]["release_id"] == info["old_release"] and value["context"]["data_version"] == 1
    assert value["impact"]["revalidation_scope"] == "APP"
    assert value["semantic_status"] == "UNKNOWN" and value["owner_acceptance"] == "PENDING"


def queue_delta(before, after, info, accepted, body, *, kind, origin_key):
    rid, iid = accepted["run_id"], accepted["check_instance_id"] if kind == "check" else info["new_instance"]
    release = info["old_release"] if kind == "check" else info["new_release"]
    allowed = {"runs", "internal_app_runs", "internal_run_bindings", "run_contracts", "events", "delivery_graph_requests"}
    if kind == "check":
        allowed.add("internal_instances")
    else:
        allowed.add("grants")
    only_tables(before, after, allowed)
    jobs, apps = added(before, after, "runs"), added(before, after, "internal_app_runs")
    bindings, contracts = added(before, after, "internal_run_bindings"), added(before, after, "run_contracts")
    assert len(jobs) == len(apps) == len(bindings) == len(contracts) == 1
    assert jobs[0]["id"] == rid and jobs[0]["status"] == "QUEUED" and jobs[0]["runtime_id"] == info["runtime"]
    assert apps[0]["id"] == accepted["app_run_id"] and apps[0]["status"] == "QUEUED"
    assert apps[0]["instance_id"] == iid and apps[0]["release_id"] == release
    assert bindings[0]["run_id"] == rid and bindings[0]["app_run_id"] == apps[0]["id"]
    if kind == "check":
        instances = added(before, after, "internal_instances")
        assert len(instances) == 1 and instances[0]["id"] == iid and instances[0]["release_id"] == release
        assert instances[0]["data_version"] == 0 and instances[0]["revision"] == 1 and iid != info["old_instance"]
        assert bindings[0]["snapshot"]["logic_check"]["instance_id"] == info["old_instance"]
        expected = {(rid, spec.RUN_META, "accepted"), (rid, logic.JOB, "accepted"),
            (info["old_instance"], logic.CHECK, origin_key)}
    else:
        reads = added(before, after, "grants")
        assert len(reads) == 1 and reads[0]["principal_id"] == info["runtime"]
        assert reads[0]["resource_id"] == info["target_resource"] and reads[0]["tool_ref"] == "resource.read" and not reads[0]["revoked"]
        assert bindings[0]["snapshot"]["pb_use"]["review"] == body["review"]
        expected = {(rid, spec.RUN_META, "accepted"), (rid, use.META, "accepted"), (iid, use.USE, origin_key)}
    journal_pairs(before, after, expected)
    assert all(row["run_id"] == rid for row in added(before, after, "events"))
    return iid, release, expected


def result_delta(before, after, info, accepted, worker, wires, *, kind, content, source_resource, queue_expected):
    rid = accepted["run_id"]
    iid = accepted["check_instance_id"] if kind == "check" else info["new_instance"]
    release = info["old_release"] if kind == "check" else info["new_release"]
    allowed = {"runs", "internal_app_runs", "internal_run_bindings", "run_contracts", "events", "delivery_graph_requests",
        "internal_instances", "internal_instance_data", "resources", "grants", "operations", "operation_intents",
        "local_effects", "attempts", "reservations", "heartbeats"}
    only_tables(before, after, allowed)
    for table in allowed - {"internal_instances"}:
        added(before, after, table)
    bindings, contracts = added(before, after, "internal_run_bindings"), added(before, after, "run_contracts")
    assert len(bindings) == len(contracts) == 1 and bindings[0]["run_id"] == rid
    jobs, apps = added(before, after, "runs"), added(before, after, "internal_app_runs")
    assert len(jobs) == len(apps) == 1 and jobs[0]["id"] == rid and jobs[0]["status"] == "SUCCEEDED"
    assert apps[0]["id"] == accepted["app_run_id"] and apps[0]["instance_id"] == iid and apps[0]["release_id"] == release
    assert apps[0]["status"] == "SUCCEEDED" and apps[0]["result_version"] == 1
    prior_instances = {row["id"]: row for row in before["internal_instances"]}
    if kind == "check":
        instances = added(before, after, "internal_instances")
        assert len(instances) == 1 and instances[0]["id"] == iid and instances[0]["data_version"] == 1
    else:
        assert len(after["internal_instances"]) == len(prior_instances)
        assert all(row == ({**prior_instances[row["id"]], "data_version": 1} if row["id"] == iid
            else prior_instances[row["id"]]) for row in after["internal_instances"])
    typed = added(before, after, "internal_instance_data")
    assert len(typed) == 1 and typed[0]["instance_id"] == iid and typed[0]["version"] == 1
    assert typed[0]["run_id"] == apps[0]["id"] and typed[0]["release_id"] == release
    assert typed[0]["fingerprint"] == fingerprint(typed[0]["data"])
    output = typed[0]["data"]["result"]
    assert output == apps[0]["output"] and output["checklist"]["source_content"] == content
    assert output["checklist"]["source"]["resource_id"] == source_resource
    resources = added(before, after, "resources")
    assert len(resources) == 1 and resources[0]["id"] == output["resource_id"] and resources[0]["format"] == "json"
    assert resources[0]["content"] == json.dumps(output["checklist"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert resources[0]["hash"] == output["hash"] == sha_bytes(resources[0]["content"].encode())
    permissions = added(before, after, "grants")
    expected_permissions = {(info["runtime"], output["resource_id"], "resource.read"),
        (info["principal"], output["resource_id"], "resource.read")}
    if kind == "use":
        expected_permissions.add((info["runtime"], source_resource, "resource.read"))
    assert len(permissions) == len(expected_permissions)
    assert {(row["principal_id"], row["resource_id"], row["tool_ref"]) for row in permissions} == expected_permissions
    operations = added(before, after, "operations")
    assert len(operations) == 6 and all(row["run_id"] == rid and row["status"] == "VERIFIED" for row in operations)
    ids = {row["id"] for row in operations}
    assert {row["operation_id"] for row in added(before, after, "operation_intents")} == ids
    effects = added(before, after, "local_effects")
    assert len(effects) == 1 and effects[0]["operation_id"] in ids and effects[0]["resource_id"] == output["resource_id"]
    attempts = sorted(added(before, after, "attempts"), key=lambda row: row["parameters"]["natural_spec"]["ordinal"])
    assert len(attempts) == len(wires) == 2 and all(row["run_id"] == rid and row["status"] == "VERIFIED" for row in attempts)
    reservations = added(before, after, "reservations")
    assert len(reservations) == 2 and all(row["run_id"] == rid for row in reservations)
    heartbeat = added(before, after, "heartbeats")
    assert len(heartbeat) == 1 and heartbeat[0]["id"] == worker["worker_id"]
    archives = {"natural_source_request_body.v1", "natural_source_response_body.v1"}
    expected_journal = set(queue_expected) | {(rid, name, attempt["id"]) for name in archives for attempt in attempts}
    rows = journal_pairs(before, after, expected_journal)
    assert len(rows) == 14
    for index, attempt in enumerate(attempts):
        for name in archives:
            row = one(rows, lambda row, a=attempt["id"], n=name: row["kind"] == n and row["request_key"] == a, "One complete offline archive")
            body = row["snapshot"]["request"]
            assert body == row["snapshot"]["response"] and body["version"] == "natural-source-body-archive.v1"
            assert body["run_id"] == rid and body["attempt_id"] == attempt["id"] and body["provenance"] == "OFFLINE_MOCKTRANSPORT"
            assert body["received_complete"] and body["extent"] == "COMPLETE_BODY" and body["omission"] == "NONE"
            raw = base64.b64decode(body["body_b64"], validate=True)
            assert body["sha256"] == sha_bytes(raw) and body["byte_count"] == len(raw)
            if name == "natural_source_request_body.v1":
                assert json.loads(raw) == wires[index] and body["phase"] == "RESERVED_REQUEST"
                assert body["sha256"] == attempt["parameters"]["natural_spec_wire"]["sha256"]
                assert len(raw) == attempt["parameters"]["natural_spec_wire"]["bytes"]
            else:
                assert body["phase"] == "RECEIVED_DECODED_BODY"
                canonical = json.dumps(json.loads(raw), ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("ascii")
                assert canonical == attempt["response"]["received_raw"].encode("ascii")
                assert body["canonical_sha256"] == sha_bytes(canonical)
    current = json.loads(wires[1]["messages"][1]["content"])["current_inputs"]
    requirements = one(operations, lambda row: row["tool_ref"] == "model.spec.requirements", "Prior actual requirements operation")
    assert current["prior_items"] == requirements["receipt"]["data"]["items"]
    assert current["prior_feedback"] == requirements["receipt"]["data"]["feedback"]
    assert current["content"] == content
    return dict(instance_id=iid, release_id=release, app_run=apps[0], typed=typed[0], artifact=resources[0], grants=permissions)


def test_first_pb_local_logic_change_checks_then_versions_and_uses_third_on_current_page(tmp_path):
    root = Path.cwd().resolve()
    settings = Settings("sqlite:///" + str(tmp_path / "fixture.db"), tmp_path, mode="mock", goal_planner_provider="intern-s2")
    store = Store(settings.database_url, test_only=True)
    clients, cold_stores, workers, wire_http, ipc, checkpoints = [], [], [], [], [], []
    stage = dict(name="generation")
    wires = {name: [] for name in ["generation", "source-original", "pb-original", "logic-check", "logic-use"]}
    source_run = old_run = None
    process = None
    info, state = {}, {}
    proof = dict(status="NOT_COMPLETED", real_model_requests=0, native_browser="NOT_RUN", windows="NOT_RUN",
        pg="NOT_RUN", remote_ci="NOT_RUN", real_semantic_acceptance="NOT_RUN", owner_human_acceptance="NOT_RUN",
        fixture_scope="FRESH_PARALLEL_GEN3_SOURCE2_PB_COLD2_THEN_PAGE_CHECK2_AND_THIRD2",
        product_clock_lease_deadline_budget_mutations=0)
    with _PageObserver(tmp_path, "PB_FIRST_LOGIC_CURRENT_PAGE") as observer:
        before_sources = sources(root)
        observer.save("source-before.json", before_sources)
        lock = threading.Lock()
        try:
            store.initialize()
            principal = store.user("P-B first logic fixture A", "synthetic-test-A")
            client = TestClient(create_app(store, settings))
            clients.append(client)
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            trace_http(client, observer, lock)
            project = ok(client.post("/api/projects", json=dict(name="P-B first local logic current page")), 201)["id"]
            source_resource, source_goal = material(client, project, SOURCE)
            data = store, settings, client, principal, project, source_resource, source_goal
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
                with observer.phase("normal_parallel_generation_release_instance"):
                    _, source_app, source_release, source_instance, generation_wire = ready(data, "parallel")
                assert generation_wire == wires["generation"] and len(generation_wire) == 3
                source_run = enqueue(data, source_release, source_instance, key="first-logic-source")
                normal_worker(store, settings, source_run, SOURCE, "source-original", observer, stage, wires, workers)
                observer.save("source-success-before-pb.json", snapshot(store))
                cold_resource, cold_goal = material(client, project, COLD, "P-B original independent COLD Goal")
                source_path = f"/api/projects/{project}/natural-spec-task-runs/{source_run}"
                options = ok(client.get(source_path + "/extraction-options"))
                extraction_request = dict(source_run_id=source_run,
                    expected_source_proof_fingerprint=options["source_proof_fingerprint"],
                    expected_source_recipe_fingerprint=options["recipe_fingerprint"], card_id=cold_goal["id"],
                    expected_goal_version=cold_goal["version"], expected_goal_fingerprint=cold_goal["fingerprint"],
                    expected_source_hash=sha_bytes(COLD.encode()), recipe=copy.deepcopy(options["recipe"]),
                    name="P-B first local logic", request_key="first-logic-original-pb")
                assert "prior_items" not in extraction_request["recipe"]["steps"][2]["inputs"]
                before_review = snapshot(store)
                reviewed = ok(client.post(source_path + "/extraction-reviews", json=extraction_request))
                assert snapshot(store) == before_review and reviewed["edited_recipe"] == options["recipe"]
                extracted = ok(client.post(source_path + "/extractions", json=dict(review=extraction_request,
                    expected_review_fingerprint=reviewed["review_fingerprint"], consent=pb.CONSENT,
                    artifact_write_consent=natural.CONSENT)), 201)
                app = ok(client.get("/api/apps/" + extracted["id"]))
                old_release, old_instance = release_instance(data, app["id"])
                old_run = enqueue(data, old_release, old_instance, key="first-logic-original-cold")
                observer.save("pb-original-before-worker.json", snapshot(store))
                normal_worker(store, settings, old_run, COLD, "pb-original", observer, stage, wires, workers)
                old_artifact = ok(client.get(f"/api/internal/app-run-jobs/{old_run}/spec-artifact"))
                assert old_artifact["result_version"] == 1
                assert json.loads(old_artifact["resource"]["content"])["source_content"] == COLD
                third_resource, third_goal = material(client, project, THIRD, "P-B new local logic explicit THIRD Goal")
                # All fixture material/Goal Grants precede the graph and page approval chain.
                graph = ok(client.post(f"/api/projects/{project}/apps/{app['id']}/delivery-graph/derive", json=dict(
                    request_key="first-logic-fixture-baseline", expected_candidate_fingerprint=app["fingerprint"])), 201)
                initial = snapshot(store)
                original_typed = one(initial["internal_instance_data"], lambda row:
                    row["instance_id"] == old_instance["id"] and row["version"] == 1, "Original P-B typed v1")
                assert original_typed["release_id"] == old_release["id"]
                assert [len(wires[name]) for name in ["generation", "source-original", "pb-original"]] == [3, 2, 2]
                for phase in ["source-original", "pb-original"]:
                    inputs = json.loads(wires[phase][1]["messages"][1]["content"])["current_inputs"]
                    assert "prior_items" not in inputs and "prior_feedback" not in inputs
                info = dict(project=project, principal=principal, app=app["id"], name=app["name"], app_name=app["name"],
                    runtime=app["runtime_id"], old_release=old_release["id"], old_instance=old_instance["id"],
                    old_run=old_run, old_result_version=1, old_content=COLD, old_resource=cold_resource, old_goal=cold_goal["id"],
                    target_goal=third_goal["id"], target_resource=third_resource, target_content=THIRD,
                    target_hash=sha_bytes(THIRD.encode()), original_candidate=app["candidate"],
                    original_release_value=old_release, original_typed=original_typed, graph=graph,
                    source_run=source_run, source_app=source_app, source_release=source_release["id"],
                    source_instance=source_instance["id"], output=str(tmp_path / "page-result.json"),
                    storage_path=str(tmp_path / "durable-storage.json"))
                observer.save("info.json", info)
                observer.save("page-seed-baseline.json", initial)
                state["readonly"] = initial
                base = f"/api/internal/instances/{old_instance['id']}/logic-patches"
                bridge = TestClient(create_app(store, settings))
                clients.append(bridge)
                trace_http(bridge, observer, lock)
                process = subprocess.Popen(["node", str(Path(__file__).with_name("pb_first_logic_current_page_ui.cjs")),
                    str(tmp_path / "info.json")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=observer.driver, text=True, env={**os.environ,
                        "NODE_PATH": str(root / "scripts/engineering-ci/node_modules")})
                observer.own_node(process)
                phases = ["seed-readonly", "logic-preview-and-check-queued", "check-pass-before-version",
                    "new-release-and-instance-created", "use-queued-before-worker",
                    "use-complete-after-manual-refresh", "cold-old-new-readonly"]

                def originals_preserved(current):
                    for table, rows in initial.items():
                        assert all(row in current[table] for row in rows), "Original fixture row changed: " + table

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
                                kind = request["kind"]
                                assert kind in {"check", "use"} and kind + "_worker" not in state
                                accepted = state[kind + "_accepted"]
                                assert request["run_id"] == accepted["run_id"]
                                queued = snapshot(store)
                                assert queued == state["readonly"]
                                queue_delta(state[kind + "_before"], queued, info, accepted, state[kind + "_body"],
                                    kind=kind, origin_key=state["logic_key"] if kind == "check" else state["use_key"])
                                cold = Store(settings.database_url, test_only=True)
                                cold_stores.append(cold)
                                content = COLD if kind == "check" else THIRD
                                phase = "logic-" + kind
                                entry = normal_worker(cold, settings, accepted["run_id"], content,
                                    phase, observer, stage, wires, workers)
                                completed = snapshot(cold)
                                delivered = result_delta(state[kind + "_before"], completed, info, accepted, entry,
                                    wires[phase], kind=kind, content=content,
                                    source_resource=cold_resource if kind == "check" else third_resource,
                                    queue_expected=state[kind + "_queue_expected"])
                                state[kind + "_worker"] = entry
                                state[kind + "_delivered"] = delivered
                                state["readonly"] = completed
                                originals_preserved(completed)
                                observer.save(kind + "-after-worker.json", completed)
                                observer.save(kind + "-delivery.json", delivered)
                                answer = dict(status=200, text=json.dumps(dict(run_id=accepted["run_id"], status="SUCCEEDED",
                                    instance_id=delivered["instance_id"], release_id=delivered["release_id"], result_version=1)))
                            elif command == "checkpoint":
                                phase = request["phase"]
                                assert phase == phases[len(checkpoints)], (phase, checkpoints)
                                current = snapshot(store)
                                assert current == state["readonly"]
                                originals_preserved(current)
                                if phase == "seed-readonly":
                                    assert current == initial
                                elif phase == "logic-preview-and-check-queued":
                                    assert state.get("preview") and state.get("check_accepted") and not state.get("check_worker")
                                elif phase == "check-pass-before-version":
                                    assert state.get("checked") and not state.get("approval")
                                    assert current["internal_releases"] == initial["internal_releases"]
                                elif phase == "new-release-and-instance-created":
                                    assert state.get("new_release") and state.get("new_instance") and not state.get("use_accepted")
                                elif phase == "use-queued-before-worker":
                                    assert state.get("use_accepted") and not state.get("use_worker")
                                else:
                                    assert state.get("use_delivered")
                                checkpoint = dict(request=request, phase=phase, all_expected_rows_verified=True,
                                    full_table_fingerprint=fingerprint(current))
                                checkpoints.append(checkpoint)
                                if phase == "use-complete-after-manual-refresh":
                                    state["cold_readonly"] = True
                                observer.save("checkpoint-" + phase + "-rows.json", current)
                                answer = dict(status=200, text="{}")
                            else:
                                assert command is None, "Only two ordinary business Worker commands are supported"
                                method, path, headers = request["method"], request["path"], request.get("headers", {})
                                if state.get("cold_readonly"):
                                    assert method == "GET"
                                if path.startswith("/api/"):
                                    assert {key.lower(): value for key, value in headers.items()}.get("authorization") == "Bearer synthetic-test-A"
                                args, raw = dict(headers=headers), b""
                                if "body_text" in request:
                                    raw = request["body_text"].encode("utf-8")
                                    assert json.loads(raw) == request["body"]
                                    args["content"] = raw
                                else:
                                    assert method == "GET" and request.get("body") is None
                                allowed = {base + suffix for suffix in ["/previews", "/checks", "/version-approvals"]}
                                if state.get("approval"):
                                    allowed.add(f"/api/internal/approvals/{state['approval']['id']}/commit")
                                if state.get("new_release"):
                                    allowed.add(f"/api/internal/releases/{info['new_release']}/instances")
                                if state.get("new_instance"):
                                    allowed.update({f"/api/internal/instances/{info['new_instance']}/pb-use-reviews",
                                        f"/api/internal/instances/{info['new_instance']}/pb-use-runs"})
                                assert method == "GET" or (method == "POST" and path in allowed), (method, path)
                                before = snapshot(store) if method == "POST" or path.startswith(base + "/checks/") else None
                                reply = bridge.request(method, path, **args)
                                assert reply.request.content == raw
                                try:
                                    value = reply.json()
                                except ValueError:
                                    value = None
                                wire_http.append(dict(rpc_id=request["id"], method=method, path=path, body=request.get("body"),
                                    body_text=request.get("body_text"), body_bytes=len(raw), body_sha256=sha_bytes(raw),
                                    status=reply.status_code, response=value, response_text=reply.text,
                                    response_bytes=len(reply.content), response_sha256=sha_bytes(reply.content), headers=dict(reply.request.headers),
                                    after_check_worker=bool(state.get("check_worker")), after_use_worker=bool(state.get("use_worker")),
                                    cold_readonly=bool(state.get("cold_readonly"))))
                                observer.save("page-http.json", wire_http)
                                body = request.get("body")
                                if method == "POST":
                                    after = snapshot(store)
                                    assert before == state["readonly"]
                                    if path == base + "/previews":
                                        assert not state.get("preview") and reply.status_code == 201
                                        assert body == dict(request_key=body["request_key"], expected_revision=old_instance["revision"],
                                            expected_release_fingerprint=old_release["fingerprint"],
                                            expected_graph_fingerprint=graph["graph_fingerprint"], consume_prior_feedback=True)
                                        validate_preview(value, body, app["candidate"], info)
                                        only_tables(before, after, {"delivery_graph_requests"})
                                        journal_pairs(before, after, {(old_instance["id"], logic.PREVIEW, body["request_key"])})
                                        state.update(preview=value, logic_key=body["request_key"])
                                    elif path == base + "/checks":
                                        assert not state.get("check_accepted") and reply.status_code == 202
                                        assert body == dict(request_key=state["logic_key"],
                                            expected_preview_fingerprint=state["preview"]["preview_fingerprint"], consent=logic.CHECK_CONSENT)
                                        state.update(check_before=before, check_accepted=value, check_body=body)
                                        iid, _, expected = queue_delta(before, after, info, value, body,
                                            kind="check", origin_key=state["logic_key"])
                                        info["check_instance"] = iid
                                        state["check_queue_expected"] = sorted(expected)
                                    elif path == base + "/version-approvals":
                                        assert not state.get("approval") and state.get("checked") and reply.status_code == 201
                                        assert body == dict(request_key=state["logic_key"],
                                            expected_check_fingerprint=state["checked"]["check_fingerprint"], consent=logic.VERSION_CONSENT)
                                        only_tables(before, after, {"internal_approvals", "delivery_graph_requests"})
                                        approval_rows = added(before, after, "internal_approvals")
                                        assert len(approval_rows) == 1 and approval_rows[0]["id"] == value["id"] and not approval_rows[0]["consumed"]
                                        assert value["snapshot_fingerprint"] == fingerprint(value["snapshot"])
                                        assert value["snapshot"]["draft"] == old_release["snapshot"]["draft"]
                                        origin = value["snapshot"]["natural_logic_source"]
                                        assert origin == dict(namespace=logic.VERSION, instance_id=old_instance["id"],
                                            preview_key=state["logic_key"], preview_fingerprint=state["preview"]["preview_fingerprint"],
                                            check_fingerprint=state["checked"]["check_fingerprint"], execution_digest=origin["execution_digest"])
                                        assert len(origin["execution_digest"]) == 64
                                        journal_pairs(before, after, {(old_instance["id"], logic.APPROVAL, state["logic_key"])})
                                        state["approval"] = value
                                    elif path.endswith("/commit"):
                                        assert not state.get("new_release") and reply.status_code == 200
                                        assert body == dict(fingerprint=state["approval"]["fingerprint"])
                                        only_tables(before, after, {"internal_releases", "internal_approvals"})
                                        releases = added(before, after, "internal_releases")
                                        assert len(releases) == 1 and releases[0]["id"] == value["id"]
                                        assert value["snapshot"] == state["approval"]["snapshot"] and value["fingerprint"] == fingerprint(value["snapshot"])
                                        expected_approvals = [{**row, "consumed": True} if row["id"] == state["approval"]["id"] else row
                                            for row in before["internal_approvals"]]
                                        assert sorted(after["internal_approvals"], key=lambda row: row["id"]) == sorted(expected_approvals, key=lambda row: row["id"])
                                        state["new_release"] = value
                                        info["new_release"] = value["id"]
                                        assert value["id"] != old_release["id"]
                                    elif path.endswith("/instances"):
                                        assert not state.get("new_instance") and reply.status_code == 201
                                        assert body["expected_release_fingerprint"] == state["new_release"]["fingerprint"]
                                        only_tables(before, after, {"internal_instances"})
                                        instances = added(before, after, "internal_instances")
                                        assert len(instances) == 1 and instances[0]["id"] == value["id"]
                                        assert value["release_id"] == info["new_release"] and value["data_version"] == 0 and value["revision"] == 1
                                        assert value["id"] not in {old_instance["id"], info["check_instance"]}
                                        state["new_instance"] = value
                                        info["new_instance"] = value["id"]
                                    elif path.endswith("/pb-use-reviews"):
                                        assert not state.get("use_review") and reply.status_code == 200 and after == before
                                        assert value["request"] == body and body["resource_id"] == third_resource and body["card_id"] == third_goal["id"]
                                        assert body["expected_source_hash"] == info["target_hash"]
                                        assert body["expected_release_fingerprint"] == state["new_release"]["fingerprint"]
                                        assert body["expected_app_fingerprint"] == app["fingerprint"]
                                        assert body["expected_recipe_fingerprint"] == fingerprint(state["preview"]["effective_candidate"]["spec_recipe"])
                                        assert value["review_fingerprint"] == fingerprint({key: item for key, item in value.items() if key != "review_fingerprint"})
                                        assert value["effective_candidate"]["spec_recipe"] == state["preview"]["effective_candidate"]["spec_recipe"]
                                        assert value["saved_logic_source"]["origin"] == state["new_release"]["snapshot"]["natural_logic_source"]
                                        state["use_review"] = value
                                    elif path.endswith("/pb-use-runs"):
                                        assert not state.get("use_accepted") and reply.status_code == 202
                                        assert body == dict(review=state["use_review"]["request"],
                                            expected_review_fingerprint=state["use_review"]["review_fingerprint"], consent=use.CONSENT)
                                        state.update(use_before=before, use_accepted=value, use_body=body, use_key=body["review"]["request_key"])
                                        _, _, expected = queue_delta(before, after, info, value, body, kind="use", origin_key=state["use_key"])
                                        state["use_queue_expected"] = sorted(expected)
                                    else:
                                        raise AssertionError("Unexpected page mutation " + path)
                                    state["readonly"] = after
                                    observer.save("after-page-post-" + str(request["id"]) + ".json", after)
                                    originals_preserved(after)
                                elif path.startswith(base + "/checks/"):
                                    after = snapshot(store)
                                    if reply.status_code == 200 and value.get("status") == "PASS":
                                        assert state.get("check_delivered")
                                        assert value["run_id"] == state["check_accepted"]["run_id"]
                                        assert value["check_instance_id"] == info["check_instance"]
                                        assert value["check_fingerprint"] == fingerprint({key: item for key, item in value.items() if key != "check_fingerprint"})
                                        assert value["semantic_status"] == "UNKNOWN" and value["owner_acceptance"] == "PENDING"
                                        if state.get("checked"):
                                            assert value == state["checked"] and after == before
                                        else:
                                            only_tables(before, after, {"delivery_graph_requests"})
                                            journal_pairs(before, after, {(old_instance["id"], logic.CHECKED, state["logic_key"])})
                                            state["checked"] = value
                                        state["readonly"] = after
                                    else:
                                        assert after == before
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
                assert page["worker_calls"] == 2 and page["app_id"] == app["id"]
                assert [row["phase"] for row in checkpoints] == phases
                assert state.get("use_delivered") and snapshot(store) == state["readonly"]
                originals_preserved(snapshot(store))
                assert [len(wires[name]) for name in wires] == [3, 2, 2, 2, 2]
                assert len(observer.sent) == 3 and len(observer.runtime_sent) == 8 and len(workers) == 4
                assert {row["phase"] for row in workers} == {"source-original", "pb-original", "logic-check", "logic-use"}
                third_wire = json.dumps(wires["logic-use"], ensure_ascii=False)
                assert THIRD in third_wire and SOURCE not in third_wire and COLD not in third_wire
                assert all(row["test_clock_lease_deadline_mutations"] == 0 for row in workers)
                assert len({old_instance["id"], info["check_instance"], info["new_instance"]}) == 3
                assert len({old_run, state["check_accepted"]["run_id"], state["use_accepted"]["run_id"]}) == 3
                assert state["check_delivered"]["typed"]["version"] == state["use_delivered"]["typed"]["version"] == 1
                assert state["check_delivered"]["release_id"] == old_release["id"]
                assert state["use_delivered"]["release_id"] == info["new_release"]
                # No artificial owner decision or inherited acceptance: page owners remain pending.
                owner_rows = [row for row in wire_http if row["path"].endswith("/spec-owner-review") and row["status"] == 200]
                assert owner_rows and all(row["response"]["owner_acceptance"] == "PENDING"
                    and row["response"]["sequence"] == 0 and row["response"]["history"] == [] for row in owner_rows)
                cold_http = [row for row in wire_http if row["cold_readonly"]]
                assert cold_http and all(row["method"] == "GET" for row in cold_http)
                assert page["classification"] == "ACTUAL_HTTP_JSDOM_PB_FIRST_LOGIC_CURRENT_PAGE"
                assert page["logic_revision"] == 2 and page["logic_key"] == state["logic_key"]
                assert page["preview"] == state["preview"] and page["check_proof"] == state["checked"]
                assert page["new_release"] == state["new_release"] and page["new_instance"] == info["new_instance"]
                assert page["check_run"] == state["check_accepted"]["run_id"] and page["check_instance"] == info["check_instance"]
                assert page["use_run"] == state["use_accepted"]["run_id"]
                assert page["run_dimensions"] == dict(
                    original_business=dict(instance_id=old_instance["id"], run_id=old_run, release_id=old_release["id"], result_version=1),
                    isolated_check=dict(instance_id=info["check_instance"], run_id=state["check_accepted"]["run_id"], release_id=old_release["id"], result_version=1),
                    new_logic_business=dict(instance_id=info["new_instance"], run_id=state["use_accepted"]["run_id"], release_id=info["new_release"], result_version=1))
                assert len(page["viewed_results"]) == 2
                assert {(row["instance_id"], row["run_id"], row["release_id"], row["result_version"]) for row in page["viewed_results"]} == {
                    (old_instance["id"], old_run, old_release["id"], 1),
                    (info["new_instance"], state["use_accepted"]["run_id"], info["new_release"], 1)}
                for viewed in page["viewed_results"]:
                    actual = one(wire_http, lambda row, rpc_id=viewed["artifact_rpc_id"]: row["rpc_id"] == rpc_id,
                        "One exact actual cold artifact GET")
                    page_request = page["requests"][viewed["artifact_request_index"]]
                    assert page_request["rpc_id"] == actual["rpc_id"] and actual["cold_readonly"]
                    assert actual["method"] == "GET" and actual["status"] == 200
                    assert actual["path"] == f"/api/internal/app-run-jobs/{viewed['run_id']}/spec-artifact"
                    value = actual["response"]
                    assert value["instance_id"] == viewed["instance_id"] and value["run_id"] == viewed["run_id"]
                    assert value["release_id"] == viewed["release_id"] and value["result_version"] == 1
                    assert value["output_fingerprint"] == viewed["output_fingerprint"]
                    assert value["resource"]["resource_id"] == viewed["resource_id"]
                    assert actual["response_sha256"] == viewed["artifact_get_sha256"]
                    assert sha_bytes(value["resource"]["content"].encode()) == viewed["resource_content_sha256"]
                    checklist = json.loads(value["resource"]["content"])
                    assert checklist["source"]["resource_id"] == viewed["source_resource_id"]
                    assert checklist["source_content"] == (COLD if viewed["run_id"] == old_run else THIRD)
                assets = page["static_resource_loads"]
                expected_assets = {"/", "/app.css", *re.findall(r'<script[^>]+src="([^"]+)"',
                    (root / "src/sim2act/web/index.html").read_text())}
                assert len(expected_assets) == 27 and page["boots"] >= 2
                for boot in range(1, page["boots"] + 1):
                    rows = [row for row in assets if row["boot"] == boot]
                    assert len(rows) == 27 and {row["path"] for row in rows} == expected_assets
                for asset in assets:
                    path = root / "src/sim2act/web" / (asset["path"].lstrip("/") or "index.html")
                    assert asset["status"] == 200 and asset["sha256"] == sha_bytes(path.read_bytes())
                assert sources(root) == before_sources
                proof.update(status="PASS", app_id=app["id"], old_release=old_release["id"], old_instance=old_instance["id"],
                    old_run=old_run, check_run=state["check_accepted"]["run_id"], check_instance=info["check_instance"],
                    new_release=info["new_release"], new_instance=info["new_instance"], use_run=state["use_accepted"]["run_id"],
                    typed_versions=dict(original=1, isolated_check=1, new_instance=1), generation_mock_requests=len(wires["generation"]),
                    business_mock_requests={name: len(wires[name]) for name in wires if name != "generation"},
                    total_mock_requests=sum(map(len, wires.values())), generation_worker_calls=1, business_execution_stages=len(workers),
                    business_worker_calls=sum(row["worker_calls"] for row in workers), page_worker_commands=2,
                    actual_claim_counts={row["phase"]: row["claims"] for row in workers},
                    original_fixture_rows_unchanged=True, first_check_pass_read_added_sealed_metadata_rows=2,
                    page_new_runtime_or_app=0, page_new_releases=1, page_new_instances=2,
                    page_derived_read_grants=5, page_new_save_grants=0, asset_hashes_per_boot=27,
                    dependency_evidence="ACTUAL_SECOND_MODEL_INPUT_EQUALS_ACTUAL_REQUIREMENTS_RECEIPT")
        finally:
            if process is not None:
                observer.kill_owned_node("PB_FIRST_LOGIC_FINALLY")
                if process.poll() is None:
                    process.wait(timeout=10)
            observer.save("proof.json", proof)
            observer.save("page-http.json", wire_http)
            observer.save("ipc.json", ipc)
            observer.save("checkpoints.json", checkpoints)
            observer.save("business-workers.json", workers)
            observer.save("stage-wires.json", wires)
            observer.save("source-after.json", sources(root))
            observer.save("bridge-state.json", state)
            try:
                observer.save("final-rows.json", snapshot(store))
                runs = [("source-original", source_run), ("pb-original", old_run),
                    ("logic-check", state.get("check_accepted", {}).get("run_id")),
                    ("logic-use", state.get("use_accepted", {}).get("run_id"))]
                for label, rid in runs:
                    if rid:
                        observer.save(label + "-claims-finally.json", header(store, rid))
            finally:
                for item in clients:
                    item.close()
                for cold in cold_stores:
                    cold.engine.dispose()
                store.engine.dispose()
