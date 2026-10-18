"""Cold P-B recovery through actual HTTP/JSDOM; synthetic transports only.

One module seed uses the existing generation oracle and one normal source Worker.
Every page case starts from an exact physical copy of its closed SQLite database.
The browser adapter supplies Storage/Web Locks; this is not native-browser proof.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import select
from test_natural_spec_apps import COLD, SOURCE, enqueue, material, ready, transport
from test_pa_natural_spec_ui import _PageObserver
from test_spec_app_operations import snapshot

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, events, internal_run_bindings, runs
from sim2act.worker import Worker

SCENARIOS = [("flow", None), ("navigation", None), ("boundary", "source"),
             ("boundary", "target"), ("platform", None)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_inputs(root):
    paths = sorted(path for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"})
    paths += [Path(__file__).resolve(), Path(__file__).with_name("pb_cold_recovery_ui.cjs").resolve(),
        root / "tests/durable_browser.cjs"]
    paths += [root / "tests" / name for name in ["test_natural_spec_apps.py", "test_pa_spec_apps.py",
        "test_goal_text_applications.py", "test_pa_natural_spec_ui.py", "test_spec_app_operations.py",
        "sql_private_barrier.py"]]
    return {str(path.relative_to(root)) if path.is_relative_to(root) else str(path):
        dict(bytes=path.stat().st_size, sha256=sha(path)) for path in paths}


def ok(reply, status=200):
    assert reply.status_code == status, reply.text
    return reply.json()


def observe_http(client, observer):
    def trace(reply):
        reply.read()
        request = reply.request
        raw = request.content
        body = json.loads(raw) if raw else None
        observer.http_response(dict(method=request.method,
            path=request.url.raw_path.decode("ascii"), body=body), reply)
        raw_name = f"http/{observer.http_serial:06d}-request.body"
        (observer.folder / raw_name).write_bytes(raw)
        observer.save(f"http/{observer.http_serial:06d}-request-bytes.json", dict(
            file=raw_name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    client.event_hooks["response"].append(trace)


def run_header(store, rid):
    with store.tx() as connection:
        header = dict(connection.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        clock = connection.execute(select(internal_run_bindings.c.snapshot["natural_spec_clock"])
            .where(internal_run_bindings.c.run_id == rid)).scalar_one()
        claims = [dict(row) for row in connection.execute(select(events).where(
            events.c.run_id == rid, events.c.kind == "CLAIMED")).mappings()]
    return dict(header=header, clock=clock, claims=claims)


@pytest.fixture(scope="module")
def pb_cold_seed(tmp_path_factory):
    """Normal API creation/execution, then close before byte-identical copies."""
    folder = tmp_path_factory.mktemp("pb-cold-successful-source-seed")
    database = folder / "fixture.db"
    sealed = folder / "sealed-source.db"
    root = Path.cwd().resolve()
    settings = Settings("sqlite:///" + str(database), folder, mode="mock", goal_planner_provider="intern-s2")
    store = Store(settings.database_url, test_only=True)
    client = None
    seed = None
    with _PageObserver(folder, "FRESH_SOURCE_SEED_GEN3_WORKER1") as observer:
        sources = source_inputs(root)
        observer.save("source-before.json", sources)
        try:
            store.initialize()
            owner = store.user("cold recovery fixture A", "synthetic-test-A")
            store.user("cold recovery fixture B", "synthetic-test-B")
            client = TestClient(create_app(store, settings))
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            observe_http(client, observer)
            project = ok(client.post("/api/projects", json=dict(name="Cold recovery actual source")), 201)["id"]
            resource, card = material(client, project, SOURCE)
            data = store, settings, client, owner, project, resource, card
            # Preserve the original fixture's oracle and capture each request before
            # it enters that oracle, including failures before ready() returns.
            import test_natural_spec_apps as original_fixture
            original_transport = original_fixture.httpx.MockTransport

            def observed_transport(handler):
                def request_callback(request):
                    observer.sent.append(json.loads(request.content))
                    return handler(request)
                return original_transport(request_callback)

            fixture_httpx = SimpleNamespace(MockTransport=observed_transport,
                Response=original_fixture.httpx.Response)
            with observer.phase("normal_generation_and_explicit_release_instance"):
                # Replace only this fixture module's reference. The real httpx
                # class and Worker's isinstance transport guard stay untouched.
                with patch.object(original_fixture, "httpx", fixture_httpx):
                    generation_run, app, release, instance, returned_wire = ready(data, "single")
            assert returned_wire == observer.sent and len(observer.sent) == 3
            source_run = enqueue(data, release, instance, key="pb-cold-source-once")
            before = run_header(store, source_run)
            observer.save("source-worker-before.json", before)
            assert before["header"]["status"] == "QUEUED" and not before["claims"]
            with observer.phase("normal_source_worker_once", run_id=source_run):
                claimed = Worker(store, settings,
                    goal_planner_transport=transport(observer.runtime_sent, SOURCE)).once()
            after = run_header(store, source_run)
            observer.save("source-worker-claims.json", dict(before=before, after=after,
                once_returned=claimed, worker_calls=1, lease_or_clock_mutations=0))
            assert claimed and after["header"]["status"] == "SUCCEEDED"
            assert len(after["claims"]) == 1 and len(observer.runtime_sent) == 1
            assert before["clock"] == after["clock"]
            assert before["header"]["created_at"] == after["header"]["created_at"]

            target_resource, target_card = material(client, project, COLD, "Independent cold recovery target")
            other = ok(client.post("/api/projects", json=dict(name="Other cold recovery owned project")), 201)["id"]
            other_instance = ok(client.post(f"/api/internal/releases/{release['id']}/instances", json=dict(
                expected_release_fingerprint=release["fingerprint"], request_key="cold-recovery-other-instance")), 201)
            # A real different Run for navigation, with no extra Worker/model call.
            other_run = enqueue(data, release, instance, key="pb-cold-navigation-cancelled")
            control_path = f"/api/internal/instances/{instance['id']}/runs/{other_run}"
            control = ok(client.get(control_path + "/control-status"))
            assert ok(client.post(control_path + "/commands", json=dict(
                command="cancel", version=control["version"])))["status"] == "CANCELLED"
            app_value = ok(client.get("/api/apps/" + app))
            path = f"/api/projects/{project}/natural-spec-task-runs/{source_run}"
            options = ok(client.get(path + "/extraction-options"))
            source_proof = options["source_proof"]
            artifact = ok(client.get(f"/api/internal/app-run-jobs/{source_run}/spec-artifact"))
            rows = snapshot(store)
            seed = dict(settings=settings, rows=rows, seed_folder=folder, sealed=sealed,
                info=dict(project=project, principal=owner, source_app=app, source_name=app_value["name"],
                    source_instance=instance["id"], source_release=release["id"], source_run=source_run,
                    source_app_run=source_proof["app_run_id"], source_release_fingerprint=release["fingerprint"],
                    source_result_version=source_proof["result_version"], source_resource=resource,
                    source_artifact=artifact["resource"]["resource_id"], target_card=target_card["id"],
                    source_content=SOURCE, target_content=COLD,
                    target_resource=target_resource, target_hash=hashlib.sha256(COLD.encode()).hexdigest(),
                    other=other, other_instance=other_instance["id"], other_run=other_run),
                source_app=app_value, options=options, artifact=artifact, generation_run=generation_run,
                generation_requests=3, source_worker_requests=1, worker_calls=1)
            observer.save("seed-rows.json", rows)
            observer.save("seed-source-proof.json", dict(info=seed["info"], options=options,
                artifact=artifact, generation_run=generation_run, generation_model_requests=3,
                source_model_requests=1, source_worker_calls=1, extra_run_status="CANCELLED",
                extra_run_worker_calls=0, real_model_requests=0, fabricated_rows=0))
            assert source_inputs(root) == sources, "Product or test inputs changed while building the seed"
        finally:
            observer.save("source-after.json", source_inputs(root))
            if client is not None:
                client.close()
            store.engine.dispose()
        assert seed is not None
        # SQLite's default rollback journal is used. If a WAL unexpectedly exists,
        # copying only the main file would not be accepted as a sealed seed.
        assert not Path(str(database) + "-wal").exists()
        shutil.copy2(database, sealed)
        assert sha(database) == sha(sealed)
        seed["seed_sha256"] = sha(sealed)
        observer.save("seed-copy-provenance.json", dict(original=str(database), sealed=str(sealed),
            original_sha256=sha(database), sealed_sha256=seed["seed_sha256"],
            bytes=sealed.stat().st_size, all_owned_connections_closed=True,
            copy_method="SHUTIL_COPY2_CLOSED_SQLITE_MAIN_FILE", row_changes_for_copy=0))
    return seed


def assert_one_extraction(initial, current, info):
    """Exact append-only effects; no implicit release/instance/execution."""
    allowed = {"app_drafts", "principals", "grants", "task_extractions", "delivery_graph_requests"}
    assert current.keys() == initial.keys()
    for table in current:
        assert all(row in current[table] for row in initial[table]), table
        if table not in allowed:
            assert current[table] == initial[table], table
    fresh = {table: [row for row in current[table] if row not in initial[table]] for table in allowed}
    assert len(fresh["app_drafts"]) == len(fresh["principals"]) == len(fresh["task_extractions"]) == 1
    app = fresh["app_drafts"][0]
    assert app["runtime_id"] == fresh["principals"][0]["id"]
    assert fresh["task_extractions"][0]["app_id"] == app["id"]
    assert fresh["task_extractions"][0]["task_id"] == info["source_run"]
    assert len(fresh["grants"]) == 2
    assert {(row["principal_id"], row["resource_id"], row["tool_ref"], row["revoked"])
        for row in fresh["grants"]} == {(app["runtime_id"], info["target_resource"], "resource.read", False),
                                       (app["runtime_id"], info["project"], "artifact.save_text", False)}
    # Every journal row is the existing extractor's dual-sealed metadata, bounded
    # to this one new app; no new family, permission or executor is introduced.
    assert len(fresh["delivery_graph_requests"]) == 4
    assert all(row["app_id"] == app["id"] for row in fresh["delivery_graph_requests"])
    key = fresh["task_extractions"][0]["request_key"]
    assert {(row["kind"], row["request_key"]) for row in fresh["delivery_graph_requests"]} == {
        ("pb_natural_spec_metadata", "scope"), ("pb_natural_spec_metadata_seal", "scope"),
        ("pb_natural_spec_extract", key), ("pb_natural_spec_extract_seal", key)}
    return dict(app=app, marker=fresh["task_extractions"][0], appended=fresh)


def assert_assets(root, page):
    expected = {"/", "/app.css", *re.findall(r'<script[^>]+src="([^"]+)"',
        (root / "src/sim2act/web/index.html").read_text(encoding="utf-8"))}
    assets = page["static_resource_loads"]
    assert assets and page["boots"] >= 2
    assert {row["boot"] for row in assets} == set(range(1, page["boots"] + 1))
    for boot in range(1, page["boots"] + 1):
        assert {row["path"] for row in assets if row["boot"] == boot} == expected
    for asset in assets:
        assert asset["status"] == 200
        assert asset["sha256"] == sha(root / "src/sim2act/web" / (asset["path"].lstrip("/") or "index.html"))


@pytest.mark.parametrize("scenario,revoke_kind", SCENARIOS,
    ids=["cold-original-key", "late-scope-navigation", "source-revoke-and-poison",
         "target-revoke", "storage-lock-and-two-pages"])
def test_pb_cold_original_extraction_recovery_actual_http(pb_cold_seed, tmp_path, scenario, revoke_kind):
    seed = pb_cold_seed
    root = Path.cwd().resolve()
    database = tmp_path / "fixture.db"
    shutil.copy2(seed["sealed"], database)
    clone_sha = sha(database)
    assert clone_sha == seed["seed_sha256"], "Each case must begin as the sealed DB's exact bytes"
    settings = replace(seed["settings"], database_url="sqlite:///" + str(database), data_dir=tmp_path)
    store = Store(settings.database_url, test_only=True)
    client = None
    with _PageObserver(tmp_path, scenario + ("-" + revoke_kind if revoke_kind else "")) as observer:
        sources = source_inputs(root)
        observer.save("source-before.json", sources)
        proof = dict(status="NOT_COMPLETED", scenario=scenario, revoke_kind=revoke_kind,
            shared_seed=str(seed["seed_folder"]), source_generation_requests=3,
            source_worker_requests=1, source_worker_calls=1, page_worker_calls=0,
            provider_request_scope="ONE_MODULE_SHARED_SEED_NOT_REPEATED_PER_CASE",
            real_model_requests=0, native_browser="NOT_RUN", real_semantic_acceptance="NOT_RUN",
            windows="NOT_RUN", pg="NOT_RUN", remote_ci="NOT_RUN")
        checkpoints, revocations, ipc, barriers = [], [], [], []
        accepted = None
        readonly = seed["rows"]
        try:
            assert snapshot(store) == seed["rows"], "Opening the copied Store must not alter seed rows"
            observer.save("clone-provenance.json", dict(source=str(seed["sealed"]), target=str(database),
                source_sha256=seed["seed_sha256"], target_sha256_before_open=clone_sha,
                byte_identical=True, row_identical=True, copy_method="SHUTIL_COPY2", fixture_row_mutations=0))
            client = TestClient(create_app(store, settings))
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            observe_http(client, observer)
            info = dict(seed["info"], scenario=scenario, revoke_kind=revoke_kind,
                output=str(tmp_path / "page-result.json"), storage_path=str(tmp_path / "durable-storage.json"))
            observer.save("info.json", info)
            process = subprocess.Popen(["node", str(Path(__file__).with_name("pb_cold_recovery_ui.cjs")),
                str(tmp_path / "info.json")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=observer.driver, text=True, env={**os.environ,
                    "NODE_PATH": str(root / "scripts/engineering-ci/node_modules")})
            observer.own_node(process)
            for line in process.stdout:
                observer.event("node_stdout", raw_line=line)
                request = json.loads(line)
                ipc.append(dict(direction="NODE_TO_PYTHON", value=request))
                if request.get("done"):
                    break
                command = request.get("command")
                with observer.phase("rpc", rpc_id=request["id"], command=command):
                    if command == "extraction-accepted-checkpoint":
                        assert accepted is None, "One accepted extraction per cloned case"
                        current = snapshot(store)
                        accepted = assert_one_extraction(seed["rows"], current, info)
                        assert request["app_id"] == accepted["app"]["id"]
                        assert request["request_key"] == accepted["marker"]["request_key"]
                        readonly = current
                        checkpoints.append(dict(phase=request.get("phase", "accepted"),
                            one_extraction=True, no_automatic_release_instance_or_run=True))
                        answer = dict(status=200, text="{}")
                    elif command == "readonly-checkpoint":
                        assert snapshot(store) == readonly
                        checkpoints.append(dict(phase=request["phase"], all_rows_identical=True))
                        answer = dict(status=200, text="{}")
                    elif command in {"revoke-read", "revoke-source-read", "revoke-target-read"}:
                        kind = request.get("kind", "target" if command == "revoke-target-read" else "source")
                        assert scenario == "boundary" and kind == revoke_kind and not revocations and accepted
                        resource = info["source_resource"] if kind == "source" else info["target_resource"]
                        runtime = seed["source_app"]["runtime_id"] if kind == "source" else accepted["app"]["runtime_id"]
                        listed = ok(client.get(f"/api/projects/{info['project']}/grants"))
                        matching = [row for row in listed if row["principal_id"] == runtime
                            and row["resource_id"] == resource and row["tool_ref"] == "resource.read" and not row["revoked"]]
                        assert len(matching) == 1, matching
                        selected = matching[0]
                        path = f"/api/grants/{selected['id']}/revoke"
                        body = dict(command="revoke", version=selected["revision"])
                        receipt = ok(client.post(path, json=body))
                        after = snapshot(store)
                        assert after.keys() == readonly.keys()
                        for table in after:
                            expected = [({**row, "revoked": True, "revision": row["revision"] + 1}
                                if row["id"] == selected["id"] else row) for row in readonly[table]] if table == "grants" else readonly[table]
                            assert sorted(after[table], key=lambda row: json.dumps(row, sort_keys=True)) == sorted(
                                expected, key=lambda row: json.dumps(row, sort_keys=True)), table
                        readonly = after
                        value = dict(kind=kind, selected_grant=selected, path=path, request=body, receipt=receipt)
                        revocations.append(value)
                        answer = dict(status=200, text=json.dumps(value))
                    else:
                        assert command is None, "No page Worker, arbitrary fixture mutation or unknown RPC is allowed"
                        if accepted:
                            assert request["method"] == "GET", "Cold recovery must only read original key and fresh app"
                        if revocations and "/extractions/by-key/" in request["path"]:
                            protected_runs = {info["source_run"]} if revoke_kind == "source" else set()
                            protected_resources = ({info["source_resource"], info["source_artifact"]}
                                if revoke_kind == "source" else {info["target_resource"]})
                            with PrivateReadBarrier(store, protected_runs, protected_resources) as barrier:
                                reply = client.request(request["method"], request["path"],
                                    json=request.get("body"), headers=request.get("headers"))
                                assert reply.status_code == 403, reply.text
                                assert not barrier.blocked
                                barriers.append(dict(kind=revoke_kind, path=request["path"],
                                    status=reply.status_code, blocked=barrier.blocked,
                                    evaluated=barrier.evaluated, statements=barrier.statements))
                        else:
                            reply = client.request(request["method"], request["path"],
                                json=request.get("body"), headers=request.get("headers"))
                        answer = dict(status=reply.status_code, text=reply.text,
                            content_type=reply.headers.get("content-type"))
                    answer["id"] = request["id"]
                    ipc.append(dict(direction="PYTHON_TO_NODE", value=answer))
                    process.stdin.write(json.dumps(answer) + "\n")
                    process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
            proof["node_exit_code"] = code
            assert code == 0, observer.stderr_text()
            page = json.loads((tmp_path / "page-result.json").read_text(encoding="utf-8"))
            assert page["status"] == "PASS" and page["checks"] and page["actions"], page
            assert page["classification"] == "ACTUAL_HTTP_JSDOM_PB_COLD_RECOVERY"
            assert accepted is not None and checkpoints and snapshot(store) == readonly
            assert len(revocations) == (1 if scenario == "boundary" else 0)
            assert len(barriers) == (1 if scenario == "boundary" else 0)
            assert_assets(root, page)
            # Observing effects independently of DOM means a forged success label
            # cannot qualify a missing, duplicated or automatic business action.
            extracted = [row for row in snapshot(store)["task_extractions"]
                if row not in seed["rows"]["task_extractions"]]
            assert len(extracted) == 1 and extracted[0] == accepted["marker"]
            assert source_inputs(root) == sources, "Product/test inputs changed during the page case"
            proof.update(status="PASS", extracted_app=accepted["app"]["id"],
                extracted_runtime=accepted["app"]["runtime_id"], request_key=accepted["marker"]["request_key"],
                accepted_extractions=1, no_automatic_release_instance_or_run=True,
                source_and_result_rows_preserved=True, readonly_get_rows_preserved=True)
        finally:
            observer.save("proof.json", proof)
            observer.save("ipc.json", ipc)
            observer.save("checkpoints.json", checkpoints)
            observer.save("revocations.json", revocations)
            observer.save("authorization-barriers.json", barriers)
            observer.save("source-after.json", source_inputs(root))
            observer.save("final-rows.json", snapshot(store))
            if client is not None:
                client.close()
            store.engine.dispose()
