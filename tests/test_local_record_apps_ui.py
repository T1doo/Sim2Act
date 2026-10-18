"""Actual local record page flow; ASGI HTTP and normal NoModel Worker.

Flow covers explicit app/release/instance creation and three business writes.
Navigation has one real fixture seed and zero page Worker calls, qualified apart.
"""

import hashlib
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import pytest
from local_record_control_assertions import assert_control_changes
from sqlalchemy import select, update
from test_local_record_apps import (
    DETAILS_A,
    DETAILS_B,
    DONE_REASON,
    TITLE_A,
    TITLE_B,
    NoModel,
    assert_saved,
    commit,
    create_body,
    current,
    execute,
    ok,
    preview,
    ready,
    saved_rows,
    snapshot,
    write_json,
)

from sim2act.db import Store, attempts, fingerprint, grants, reservations, runs
from sim2act.worker import Worker


def source_inputs(root):
    paths = sorted(path for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"})
    paths.extend([Path(__file__).resolve(), *(Path(__file__).with_name(name).resolve() for name in
        ["local_record_apps_ui.cjs", "local_record_control_assertions.py"])])
    return {str(path.relative_to(root)) if path.is_relative_to(root) else str(path):
        dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths}


def states(store):
    with store.tx() as c:
        return {row["id"]: dict(row) for row in c.execute(select(runs)).mappings()}


def final_flow_readback(env, page, worker_log, before_identities):
    app = ok(env[2].get(f"/api/apps/{page['app_id']}"))
    delivery = ok(env[2].get(f"/api/apps/{page['app_id']}/record-delivery"))
    release = next(row for row in delivery["releases"] if row["id"] == page["release_id"])
    path = "/api/internal/record-instances/" + page["instance_id"]
    state = ok(env[2].get(path))
    data = dict(app=app, release=release, instance=state, path=path, project=env[5])
    assert state["source_app_id"] == app["id"] and state["release_id"] == release["id"]
    assert state["data_version"] == 3 and state["revision"] == 1
    assert len(state["records"]) == 2 and len(state["history"]) == 3
    records = {record["title"]: record for record in state["records"]}
    assert set(records) == {TITLE_A, TITLE_B}
    assert (records[TITLE_A]["state"], records[TITLE_A]["record_revision"], records[TITLE_A]["details"]) == ("DONE", 2, DETAILS_A)
    assert (records[TITLE_B]["state"], records[TITLE_B]["record_revision"], records[TITLE_B]["details"]) == ("OPEN", 1, DETAILS_B)
    assert state["history"][0] == page["first_history"]
    assert [row["run_id"] for row in state["history"]] == page["run_ids"]
    assert [row["run_id"] for row in worker_log] == page["run_ids"]
    assert len(page["request_keys"]) == 3 and len(set(page["request_keys"])) == 3
    completed = []
    for version, (rid, key) in enumerate(zip(page["run_ids"], page["request_keys"], strict=True), 1):
        prepared = ok(env[2].get(path + "/record-requests/" + key))
        run = ok(env[2].get(path + "/runs/" + rid))
        assert run["status"] == "SUCCEEDED" and run["id"] == prepared["run"]["run_id"]
        value = dict(prepared=prepared, run=run)
        assert_saved(env, data, value, version)
        completed.append(value)
    with env[0].tx() as c:
        assert not c.execute(select(attempts.c.id)).first()
        assert not c.execute(select(reservations.c.id)).first()
    after = snapshot(env[0], {"grants", "principals"})
    assert after["principals"] == before_identities["principals"]
    old_grants = {row["id"]: row for row in before_identities["grants"]}
    new_grants = [row for row in after["grants"] if row["id"] not in old_grants]
    assert len(new_grants) == 6 and {row["tool_ref"] for row in new_grants} == {"resource.read"}
    assert all(row == old_grants[row["id"]] for row in after["grants"] if row["id"] in old_grants)
    return dict(app=app, release=release, current=state, completed=completed,
        exact_saved_rows=saved_rows(env[0], completed), derived_read_grants=new_grants,
        page_worker_calls=3, fixture_worker_calls=0, real_model_requests=0,
        native_browser="NOT_RUN", real_semantic_acceptance="NOT_RUN")


@pytest.mark.parametrize("scenario", ["flow-recovery", "navigation", "revocation", "project-history", "controls"])
def test_local_record_page_explicit_flow_and_fenced_navigation_actual_http(env, tmp_path, scenario):
    root = Path.cwd().resolve()
    raw_http, ipc, worker_log = [], [], []
    process = watchdog = None
    stores = []
    revocation_log, revocation_grant = [], None
    proof = dict(scenario=scenario, status="NOT_COMPLETED", real_model_requests=0,
        native_browser="NOT_RUN", pg="NOT_RUN", real_semantic_acceptance="NOT_RUN")

    def trace(response):
        response.read()
        request = response.request
        body = request.content.decode("utf-8") if request.content else None
        raw_http.append(dict(method=request.method, url=str(request.url),
            request=json.loads(body) if body else None,
            status=response.status_code, response=response.text,
            content_type=response.headers.get("content-type")))

    before_sources = source_inputs(root)
    env[2].event_hooks["response"].append(trace)
    write_json(tmp_path / "source-before.json", before_sources)
    try:
        other = ok(env[2].post("/api/projects", json=dict(name="Other owned local record navigation project")), 201)["id"]
        info = dict(scenario=scenario, project=env[5], other=other,
            app_name="Actual page local records", goal="Collect independent work items and explicitly mark only A DONE",
            title_a=TITLE_A, details_a=DETAILS_A, title_b=TITLE_B, details_b=DETAILS_B,
            done_reason=DONE_REASON, output=str(tmp_path / "page-result.json"))
        if scenario in {"navigation", "revocation", "project-history"}:
            data = ready(env)
            first = execute(env, data, create_body(current(env, data)))
            info.update(app=data["app"]["id"], instance=data["instance"]["id"],
                iid=data["instance"]["id"], release=data["release"]["id"],
                seed_run=first["run"]["id"], seed_request_key=first["prepared"]["request_key"])
            if scenario in {"navigation", "project-history"}:
                second = ok(env[2].post(f"/api/internal/record-releases/{data['release']['id']}/instances", json=dict(
                    expected_release_fingerprint=data["release"]["fingerprint"], request_key="page-navigation-empty-instance")), 201)["instance"]
                info["second_instance"] = second["id"]
            if scenario in {"revocation", "project-history"}:
                info["seed_artifact"] = first["run"]["output"]["resource_id"]
                with env[0].tx() as connection:
                    matching = connection.execute(select(grants).where(
                        grants.c.principal_id == env[3], grants.c.project_id == env[5],
                        grants.c.resource_id == info["seed_artifact"], grants.c.tool_ref == "resource.read",
                        grants.c.revoked.is_(False))).mappings().all()
                    assert len(matching) == 1, "Exactly one known owner-read grant for the synthetic seed artifact"
                    revocation_grant = dict(matching[0])
        if scenario == "controls":
            data = ready(env)
            prepared = preview(env, data, create_body(current(env, data), "control-one-queued-write"))
            accepted, _ = commit(env, data, prepared)
            assert accepted["run"]["status"] == "QUEUED"
            second = ok(env[2].post(f"/api/internal/record-releases/{data['release']['id']}/instances", json=dict(
                expected_release_fingerprint=data["release"]["fingerprint"], request_key="control-empty-instance")), 201)["instance"]
            info.update(app=data["app"]["id"], instance=data["instance"]["id"], iid=data["instance"]["id"],
                release=data["release"]["id"], seed_run=accepted["run"]["run_id"],
                seed_request_key=prepared["request_key"], second_instance=second["id"])
        before_identity = snapshot(env[0], {"grants", "principals"})
        before_page = snapshot(env[0])
        if scenario == "controls":
            write_json(tmp_path / "database-before-page.json", before_page)
        write_json(tmp_path / "info.json", info)
        with (tmp_path / "node.stderr").open("w", encoding="utf-8") as errors:
            process = subprocess.Popen(["node", str(Path(__file__).with_name("local_record_apps_ui.cjs")),
                str(tmp_path / "info.json")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=errors, text=True, env={**os.environ,
                    "NODE_PATH": os.environ.get("NODE_PATH") or str(root / "scripts/engineering-ci/node_modules")})
            watchdog = threading.Timer(600, process.kill)
            watchdog.start()
            for line in process.stdout:
                request = json.loads(line)
                ipc.append(dict(direction="NODE_TO_PYTHON", value=request))
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    assert scenario == "flow-recovery", "Read-only page scenarios cannot invoke Worker"
                    cold = Store(env[1].database_url, test_only=True)
                    stores.append(cold)
                    before = states(cold)
                    assert Worker(cold, env[1], NoModel()).once()
                    after = states(cold)
                    changed = [rid for rid, row in after.items() if row["status"] in {"SUCCEEDED", "FAILED", "PARTIAL"}
                        and before.get(rid, {}).get("status") not in {"SUCCEEDED", "FAILED", "PARTIAL"}]
                    assert len(changed) == 1, changed
                    rid = changed[0]
                    assert request.get("run", request.get("run_id")) in (None, rid)
                    worker_log.append(dict(run_id=rid, status=after[rid]["status"],
                        implementation="NORMAL_WORKER_ONCE", cold_store=True, model="NoModel"))
                    answer = dict(status=200, text=json.dumps(worker_log[-1]))
                elif request.get("command") == "revoke_seed_artifact_read":
                    # Fixture-only authority mutation. The page cannot select a Grant,
                    # principal, project or arbitrary resource through this bridge.
                    assert scenario in {"revocation", "project-history"} and revocation_grant is not None and not revocation_log
                    assert set(request) == {"id", "command", "run", "resource"}
                    assert request["run"] == info["seed_run"] and request["resource"] == info["seed_artifact"]
                    with env[0].tx() as connection:
                        actual = dict(connection.execute(select(grants).where(
                            grants.c.id == revocation_grant["id"], grants.c.principal_id == env[3],
                            grants.c.project_id == env[5], grants.c.resource_id == info["seed_artifact"],
                            grants.c.tool_ref == "resource.read")).mappings().one())
                        assert actual == revocation_grant and not actual["revoked"]
                        changed = connection.execute(update(grants).where(
                            grants.c.id == actual["id"], grants.c.principal_id == env[3],
                            grants.c.project_id == env[5], grants.c.resource_id == info["seed_artifact"],
                            grants.c.tool_ref == "resource.read", grants.c.revoked.is_(False),
                            grants.c.revision == actual["revision"]).values(
                                revoked=True, revision=actual["revision"] + 1)).rowcount
                        assert changed == 1
                        after_grant = dict(connection.execute(select(grants).where(
                            grants.c.id == actual["id"])).mappings().one())
                    revocation_log.append(dict(before=actual, after=after_grant,
                        run_id=info["seed_run"], resource_id=info["seed_artifact"],
                        classification="EXPLICIT_SYNTHETIC_FIXTURE_GRANT_REVOCATION"))
                    answer = dict(status=200, text=json.dumps(dict(
                        revoked=True, resource_id=info["seed_artifact"], run_id=info["seed_run"])))
                else:
                    assert "command" not in request, request
                    if scenario in {"revocation", "project-history"}:
                        assert request["method"] == "GET", "Read-only page scenario must never POST"
                    response = env[2].request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=response.status_code, text=response.text,
                        content_type=response.headers.get("content-type"))
                answer["id"] = request["id"]
                ipc.append(dict(direction="PYTHON_TO_NODE", value=answer))
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
            errors.flush()
        proof["node_exit_code"] = code
        assert code == 0, (tmp_path / "node.stderr").read_text(encoding="utf-8")
        page = json.loads((tmp_path / "page-result.json").read_text(encoding="utf-8"))
        assert page["status"] == "PASS" and page["checks"] and page["actions"], page
        expected_assets = {"/", "/app.css", *re.findall(r'<script[^>]+src="([^"]+)"',
            (root / "src/sim2act/web/index.html").read_text(encoding="utf-8"))}
        assets = page["static_resource_loads"]
        assert assets and {row["boot"] for row in assets} == set(range(1, page["boots"] + 1))
        for boot in range(1, page["boots"] + 1):
            assert {row["path"] for row in assets if row["boot"] == boot} == expected_assets
        for asset in assets:
            path = asset["path"].lstrip("/") or "index.html"
            assert asset["status"] == 200
            assert hashlib.sha256((root / "src/sim2act/web" / path).read_bytes()).hexdigest() == asset["sha256"]
        if scenario == "flow-recovery":
            assert page["classification"] == "ACTUAL_HTTP_JSDOM_LOCAL_RECORD_FLOW"
            assert len(worker_log) == 3 and all(row["status"] == "SUCCEEDED" for row in worker_log)
            delivered = final_flow_readback(env, page, worker_log, before_identity)
            write_json(tmp_path / "actual-page-delivery.json", delivered)
            proof.update(page_worker_calls=3, fixture_worker_calls=0, actual_no_model_runs=3,
                page_creation_release_instance_covered=True)
        elif scenario == "controls":
            assert page["classification"] == "ACTUAL_HTTP_JSDOM_LOCAL_RECORD_SAME_RUN_CONTROLS"
            assert worker_log == []
            commands = [row for row in page["actions"] if row["method"] == "POST"]
            assert [row["body"] for row in commands] == [dict(command=command, version=version)
                for version, command in enumerate(["pause", "resume", "cancel"], 1)]
            assert all(row["path"] == data["path"] + "/runs/" + info["seed_run"] + "/commands"
                and row["status"] == 200 for row in commands)
            probe = Worker(env[0], env[1], NoModel())
            probe_started = time.time()
            assert not probe.once(), "Cancelled Run cannot be claimed"
            probe_ended = time.time()
            after_page = snapshot(env[0])
            write_json(tmp_path / "database-after-page.json", after_page)
            control_proof = assert_control_changes(before_page, after_page, info["seed_run"],
                probe_worker_id=probe.id, time_bounds=(probe_started, probe_ended))
            write_json(tmp_path / "actual-control-proof.json", control_proof)
            proof.update(page_worker_calls=0, fixture_worker_calls=0, worker_probes=1, worker_claims=0,
                actual_no_model_runs=0, page_post_count=3, page_creation_release_instance_covered=False)
        elif scenario in {"revocation", "project-history"}:
            expected_classification = ("ACTUAL_HTTP_JSDOM_LOCAL_RECORD_PROJECT_HISTORY_NO_PAGE_WORKER"
                if scenario == "project-history" else "ACTUAL_HTTP_JSDOM_LOCAL_RECORD_REVOCATION_NO_WORKER")
            assert page["classification"] == expected_classification
            assert worker_log == [] and len(revocation_log) == 1
            assert all(row["method"] == "GET" for row in page["actions"])
            after_page = snapshot(env[0])
            assert before_page.keys() == after_page.keys()
            for table in before_page:
                if table != "grants":
                    assert before_page[table] == after_page[table], table
            expected = {row["id"]: row for row in before_page["grants"]}
            actual = {row["id"]: row for row in after_page["grants"]}
            assert expected.keys() == actual.keys()
            grant_id = revocation_grant["id"]
            expected[grant_id] = {**revocation_grant, "revoked": True, "revision": revocation_grant["revision"] + 1}
            assert actual == expected
            assert before_page["runs"] == after_page["runs"], "Original accepted Run must remain unchanged"
            write_json(tmp_path / "actual-revocation-proof.json", dict(
                scenario=scenario, fixture_grant_mutations=revocation_log,
                changed_tables=[name for name in before_page if before_page[name] != after_page[name]],
                database_before_fingerprint=fingerprint(before_page),
                database_after_fingerprint=fingerprint(after_page),
                only_exact_known_grant_changed=True, all_other_rows_unchanged=True,
                original_run_rows_unchanged=True, page_worker_calls=0, page_post_count=0))
            proof.update(page_worker_calls=0, fixture_worker_calls=1, actual_no_model_runs=1,
                fixture_grant_mutations=1, page_post_count=0, original_run_rows_unchanged=True,
                page_creation_release_instance_covered=False)
        else:
            assert page["classification"] == "ACTUAL_HTTP_JSDOM_LOCAL_RECORD_NAVIGATION_NO_WORKER"
            assert worker_log == [] and snapshot(env[0]) == before_page
            proof.update(page_worker_calls=0, fixture_worker_calls=1, actual_no_model_runs=1,
                page_creation_release_instance_covered=False)
        proof.update(status="PASS", classification=page["classification"],
            observed_production_assets=len(assets))
    finally:
        if watchdog:
            watchdog.cancel()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for store in stores:
            store.engine.dispose()
        env[2].event_hooks["response"].remove(trace)
        after_sources = source_inputs(root)
        changes = {key: dict(before=before_sources.get(key), after=after_sources.get(key))
            for key in sorted(before_sources.keys() | after_sources.keys())
            if before_sources.get(key) != after_sources.get(key)}
        write_json(tmp_path / "source-after.json", after_sources)
        write_json(tmp_path / "source-changes.json", changes)
        write_json(tmp_path / "http-trace.json", raw_http)
        write_json(tmp_path / "ipc.json", ipc)
        write_json(tmp_path / "worker-log.json", worker_log)
        write_json(tmp_path / "fixture-revocation-log.json", revocation_log)
        write_json(tmp_path / "run-summary.json", proof)
        destination = os.environ.get("SIM2ACT_LOCAL_RECORD_UI_EVIDENCE_DIR")
        if destination:
            folder = Path(destination) / (scenario + "-" + str(time.time_ns()))
            folder.mkdir(parents=True, exist_ok=False)
            for name in ("info.json", "node.stderr", "page-result.json", "actual-page-delivery.json",
                    "source-before.json", "source-after.json", "source-changes.json", "http-trace.json",
                    "ipc.json", "worker-log.json", "run-summary.json", "actual-revocation-proof.json",
                    "fixture-revocation-log.json"):
                path = tmp_path / name
                if path.exists():
                    (folder / name).write_bytes(path.read_bytes())
        assert changes == {}, changes
