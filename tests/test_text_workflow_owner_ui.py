"""Actual HTTP/JSDOM closed-text result and owner flow; synthetic NoModel only.

The navigation case has separate qualification. Neither case is a native browser
or real semantic owner acceptance, and neither requests a real model.
"""

import hashlib
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from sqlalchemy import select
from test_text_workflow_owner import SOURCE, assert_actual_contract, owner_rows
from test_text_workflows import NoModel, draft, enqueue, inspect, instance, material, once

from sim2act.db import (
    Store,
    attempts,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_run_bindings,
    natural_owner_records,
    operations,
    principals,
    reservations,
    run_contracts,
    runs,
)
from sim2act.worker import Worker


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def source_inputs(root):
    files = sorted(path for path in (root / "src/sim2act").rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".html"})
    files.extend([Path(__file__).resolve(), Path(__file__).with_name("text_workflow_owner_ui.cjs").resolve()])
    return {str(path.relative_to(root)) if path.is_relative_to(root) else str(path):
        dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        for path in files}


def identity_rows(store):
    with store.tx() as c:
        return {table.name: [dict(row) for row in c.execute(select(table).order_by(table.c.id)).mappings()]
            for table in (grants, principals)}


def run_states(store):
    with store.tx() as c:
        return {row["id"]: dict(row) for row in c.execute(select(runs)).mappings()}


def case_fixture(env):
    resource, card = material(env, SOURCE, "md")
    app, creation = draft(env, resource, card)
    release, inst = instance(env, app["id"])
    full_app = env[2].get(f"/api/apps/{app['id']}")
    assert full_app.status_code == 200, full_app.text
    full_goal = env[2].get(f"/api/goal-cards/{card['id']}")
    assert full_goal.status_code == 200, full_goal.text
    other = env[2].post("/api/projects", json=dict(name="Other owned text navigation project"))
    assert other.status_code == 201, other.text
    second = env[2].post(f"/api/internal/releases/{release['id']}/instances", json=dict(
        expected_release_fingerprint=release["fingerprint"], request_key="text-owner-navigation-instance"))
    assert second.status_code == 201, second.text
    # A genuine completed historical task is fixture setup, distinct from the
    # three explicit page inputs and page-requested Worker invocations.
    seed_input = dict(term_a="Amber", term_b="Amber", emit_report=True)
    seed_run = enqueue(env, release, inst, seed_input, "text-owner-page-seed")
    once(env)
    seed = inspect(env, inst, seed_run)
    assert seed.status_code == 200 and seed.json()["status"] == "SUCCEEDED", seed.text
    assert seed.json()["result_version"] == 1
    return dict(resource=resource, card=card, goal=full_goal.json(), app=app,
        full_app=full_app.json(), creation=creation,
        release=release, instance=inst, other=other.json()["id"],
        second_instance=second.json()["id"], seed_input=seed_input,
        seed_run=seed_run, seed=seed.json())


def final_delivery(env, data, page, worker_log):
    """Independent actual storage/readback checks after the visible page flow."""
    iid = data["instance"]["id"]
    with env[0].tx() as c:
        bound_ids = list(c.execute(select(internal_run_bindings.c.run_id)
            .join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
            .where(internal_app_runs.c.instance_id == iid)).scalars())
        actual = [dict(row) for row in c.execute(select(runs).where(
            runs.c.id.in_(bound_ids), runs.c.id != data["seed_run"])).mappings()]
        actual.sort(key=lambda row: row["created_at"])
        assert len(actual) == 3
        assert [row["status"] for row in actual] == ["SUCCEEDED", "SUCCEEDED", "PARTIAL"]
        ids = [row["id"] for row in actual]
        assert page["run_ids"] == ids
        assert [row["run_id"] for row in worker_log] == ids
        assert all(row["runtime_id"] == data["instance"]["runtime_id"] for row in actual)
        assert not c.execute(select(attempts.c.id)).first()
        assert not c.execute(select(reservations.c.id)).first()
        current = dict(c.execute(select(internal_instances).where(
            internal_instances.c.id == iid)).mappings().one())
        assert current["revision"] == data["instance"]["revision"]
        assert current["release_id"] == data["release"]["id"]
        assert current["data_version"] == 3
        full_rows = {table.name: [dict(row) for row in c.execute(select(table)).mappings()]
            for table in (runs, internal_app_runs, internal_run_bindings,
                internal_instance_data, operations, run_contracts, natural_owner_records)}
    delivered = []
    for n, (rid, value) in enumerate(zip(ids, [
        dict(term_a="Amber", term_b="Violet", emit_report=True),
        dict(term_a="Violet", term_b="Amber", emit_report=True),
        dict(term_a="Amber", term_b="Violet", emit_report=False),
    ], strict=True)):
        response = inspect(env, data["instance"], rid)
        assert response.status_code == 200, response.text
        result = response.json()
        path = f"/api/internal/instances/{iid}/runs/{rid}/text-owner-review"
        owner = env[2].get(path)
        assert owner.status_code == 200, owner.text
        state = owner.json()
        rows = owner_rows(env[0], rid)
        if n == 0:
            assert result["result_version"] == 2
            assert state["owner_acceptance"] == "STALE" and not state["content_access"]
            assert state["history"] == page["first_owner_history"]
            assert [row["kind"] for row in state["history"]] == ["PREPARE", "DECIDE"]
            records = sorted(rows["natural_owner_records"], key=lambda row: row["sequence"])
            assert len(records) == 2 and records[-1]["status"] == "ACCEPTED"
            assert_actual_contract(env, {**data, "run_id": rid, "input": value, "result": result},
                records[-1]["payload"]["contract"], version=2)
        elif n == 1:
            assert result["result_version"] == 3 and state["owner_acceptance"] == "PENDING"
            assert state["sequence"] == 0 and state["history"] == []
            assert_actual_contract(env, {**data, "run_id": rid, "input": value, "result": result},
                state["current"], version=3)
            assert rows == {"natural_owner_records": [], "natural_owner_seals": []}
        else:
            assert result["status"] == "PARTIAL" and result["result"] is None
            assert result["result_version"] is None
            assert [step["status"] for step in result["steps"]] == ["VERIFIED"] * 3 + ["SKIPPED"]
            assert state["owner_acceptance"] == "PENDING" and not state["content_access"]
            assert "current" not in state and state["sequence"] == 0
            assert rows == {"natural_owner_records": [], "natural_owner_seals": []}
        delivered.append(dict(run=result, owner=state, owner_rows=rows))
    return dict(actual_page_runs=delivered, current_instance=current, stored_rows=full_rows,
        page_worker_calls=3, fixture_worker_calls=1, actual_no_model_runs=4,
        real_model_requests=0, semantic_acceptance="NOT_RUN", native_browser="NOT_RUN")


@pytest.mark.parametrize("scenario", ["flow-recovery", "navigation"])
def test_visible_text_report_and_exact_run_owner_actual_http(env, tmp_path, scenario):
    root = Path.cwd().resolve()
    http, ipc, worker_log = [], [], []
    process = watchdog = None
    cold_stores = []
    proof = dict(scenario=scenario, status="NOT_COMPLETED", real_model_requests=0,
        native_browser="NOT_RUN", semantic_acceptance="NOT_RUN")

    def trace(response):
        response.read()
        request = response.request
        raw = request.content.decode("utf-8") if request.content else None
        http.append(dict(method=request.method, path=str(request.url),
            request=json.loads(raw) if raw else None, status=response.status_code,
            response=response.text, content_type=response.headers.get("content-type")))

    env[2].event_hooks["response"].append(trace)
    initial_sources = source_inputs(root)
    write_json(tmp_path / "source-before.json", initial_sources)
    try:
        data = case_fixture(env)
        before_identities = identity_rows(env[0])
        before_runs = run_states(env[0])
        info = dict(project=env[5], app=data["app"]["id"], app_name=data["full_app"]["name"],
            instance=data["instance"]["id"], release=data["release"]["id"],
            resource=data["resource"], source_resource=data["resource"],
            card=data["card"]["id"], goal=data["goal"], source_content=SOURCE,
            source_run=data["seed_run"], seed_run=data["seed_run"], seed_input=data["seed_input"],
            input_a=dict(term_a="Amber", term_b="Violet", emit_report=True),
            input_b=dict(term_a="Violet", term_b="Amber", emit_report=True),
            other=data["other"], second_instance=data["second_instance"],
            scenario=scenario, output=str(tmp_path / "page-result.json"))
        write_json(tmp_path / "info.json", info)
        cjs = Path(__file__).with_name("text_workflow_owner_ui.cjs")
        with (tmp_path / "node.stderr").open("w", encoding="utf-8") as errors:
            process = subprocess.Popen(["node", str(cjs), str(tmp_path / "info.json")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
                text=True, env={**os.environ,
                    "NODE_PATH": "/workspace/Sim2Act/scripts/engineering-ci/node_modules"})
            watchdog = threading.Timer(600, process.kill)
            watchdog.start()
            for line in process.stdout:
                request = json.loads(line)
                ipc.append(dict(direction="NODE_TO_PYTHON", value=request))
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    cold = Store(env[1].database_url, test_only=True)
                    cold_stores.append(cold)
                    before = run_states(cold)
                    assert Worker(cold, env[1], NoModel()).once()
                    after = run_states(cold)
                    changed = [rid for rid, row in after.items()
                        if row["status"] in {"SUCCEEDED", "PARTIAL"}
                        and before.get(rid, {}).get("status") not in {"SUCCEEDED", "PARTIAL"}]
                    assert len(changed) == 1, changed
                    rid = changed[0]
                    expected = request.get("run") or request.get("run_id")
                    assert expected in (None, rid), (expected, rid)
                    worker_log.append(dict(run_id=rid, status=after[rid]["status"],
                        implementation="NORMAL_WORKER_ONCE", cold_store=True,
                        model="NoModel raises on any request"))
                    answer = dict(status=200, text=json.dumps(dict(run_id=rid, status=after[rid]["status"])))
                else:
                    assert "command" not in request, request
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
        assert page["status"] == "PASS", page
        assert page["checks"] and page["actions"]
        scripts = re.findall(r'<script[^>]+src="([^"]+)"',
            (root / "src/sim2act/web/index.html").read_text(encoding="utf-8"))
        expected_assets = {"/", "/app.css", *scripts}
        assets = page["static_resource_loads"]
        assert assets and {row["boot"] for row in assets} == set(range(1, page["boots"] + 1))
        for boot in range(1, page["boots"] + 1):
            assert {row["path"] for row in assets if row["boot"] == boot} == expected_assets
        for asset in assets:
            path = urlsplit(asset["path"]).path.lstrip("/") or "index.html"
            assert asset["status"] == 200
            assert asset["sha256"] == hashlib.sha256((root / "src/sim2act/web" / path).read_bytes()).hexdigest()
        assert identity_rows(env[0]) == before_identities
        if scenario == "flow-recovery":
            assert page["classification"] == "ACTUAL_HTTP_JSDOM_NO_MODEL_FLOW"
            assert len(worker_log) == 3
            delivery = final_delivery(env, data, page, worker_log)
            write_json(tmp_path / "actual-page-delivery.json", delivery)
            proof.update(page_worker_calls=3, fixture_worker_calls=1,
                actual_no_model_runs=4, owner_declaration="SIMULATED_PER_ITEM_ACCEPT")
        else:
            assert page["classification"] in {"ACTUAL_HTTP_JSDOM_NAVIGATION_NO_WORKER",
                "CONTROLLED_LOCAL_PRODUCTION_FUNCTION_JSDOM_NAVIGATION"}
            assert worker_log == [] and run_states(env[0]) == before_runs
            assert owner_rows(env[0], data["seed_run"]) == {
                "natural_owner_records": [], "natural_owner_seals": []}
            proof.update(page_worker_calls=0, fixture_worker_calls=1,
                actual_no_model_runs=1, owner_declaration="NOT_RUN")
        proof.update(status="PASS", classification=page["classification"],
            production_assets_observed=len(assets), grants_and_principals_unchanged=True)
    finally:
        if watchdog:
            watchdog.cancel()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for cold in cold_stores:
            cold.engine.dispose()
        env[2].event_hooks["response"].remove(trace)
        final_sources = source_inputs(root)
        changes = {key: dict(before=initial_sources.get(key), after=final_sources.get(key))
            for key in sorted(initial_sources.keys() | final_sources.keys())
            if initial_sources.get(key) != final_sources.get(key)}
        write_json(tmp_path / "source-after.json", final_sources)
        write_json(tmp_path / "source-changes.json", changes)
        write_json(tmp_path / "http-trace.json", http)
        write_json(tmp_path / "ipc.json", ipc)
        write_json(tmp_path / "worker-log.json", worker_log)
        write_json(tmp_path / "run-summary.json", proof)
        output = os.environ.get("SIM2ACT_TEXT_OWNER_UI_EVIDENCE_DIR")
        if output:
            folder = Path(output) / (scenario + "-" + str(time.time_ns()))
            folder.mkdir(parents=True, exist_ok=False)
            for name in ("info.json", "node.stderr", "page-result.json", "actual-page-delivery.json",
                    "source-before.json", "source-after.json", "source-changes.json", "http-trace.json",
                    "ipc.json", "worker-log.json", "run-summary.json"):
                path = tmp_path / name
                if path.exists():
                    (folder / name).write_bytes(path.read_bytes())
        assert changes == {}, changes
