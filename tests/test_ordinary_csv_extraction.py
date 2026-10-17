"""Ordinary complete CSV contract -> explicit sum-only application; synthetic only."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update
from test_internal_lifecycle import create, release
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_report import NoModel, prepare
from test_persistent_app_runs import enqueue

from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    fingerprint,
    grants,
    internal_run_bindings,
    operations,
    runs,
)
from sim2act.worker import Worker


def setup(env):
    store, settings, client, _, _, project, source = env
    accepted = prepare(client, project, source)
    assert accepted.status_code == 202, accepted.text
    rid = accepted.json()["run_id"]
    frozen = client.get(f"/api/runs/{rid}").json()
    confirmed = client.post(f"/api/runs/{rid}/confirm-csv-report", json=dict(
        version=frozen["version"], contract_fingerprint=frozen["contract"]["fingerprint"],
        request_key="confirm-original-report",
    ))
    assert confirmed.status_code == 200, confirmed.text
    assert Worker(store, settings, NoModel()).once()
    original = client.get(f"/api/runs/{rid}").json()
    assert original["status"] == "SUCCEEDED"
    target_resource = client.post(f"/api/projects/{project}/resources", json=dict(
        name="unseen.csv", format="csv", content="amount,quantity,bad\n30,6,x\n50,9,y\n",
    )).json()["id"]
    target = client.post(f"/api/projects/{project}/apps/csv-preview", json=dict(
        name="already authorized target", resource_id=target_resource, goal="new CSV",
    )).json()["id"]
    return rid, original, target, target_resource


def options_body(env, rid, target, key="sum-only"):
    response = env[2].get(f"/api/runs/{rid}/csv-sum-candidate-options")
    assert response.status_code == 200, response.text
    options = response.json()
    target = next(t for t in options["targets"] if t["id"] == target)
    return options, dict(
        expected_proof_fingerprint=options["source_proof_fingerprint"],
        target_app_id=target["id"], expected_target_draft_fingerprint=target["fingerprint"],
        name="Explicit sum only", request_key=key,
        consent="EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT",
    )


def test_ordinary_success_to_sum_only_new_input_version_instance_and_fresh_run(env, tmp_path):
    rid, original, target, material = setup(env)
    before = table_snapshot(env[0])
    options, body = options_body(env, rid, target)
    assert options["proof"]["contract_fingerprint"] == original["contract"]["fingerprint"]
    assert options["proof"]["result_fingerprint"] == fingerprint(original["result"])
    assert options["proof"]["source_task_acceptance"] == original["result"]["task_acceptance"]
    assert table_snapshot(env[0]) == before
    response = env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=body)
    assert response.status_code == 201, response.text
    made = response.json()
    assert made["state"] == "CANDIDATE_ONLY" and made["full_md_report_included"] is False
    assert made["source_task_accepted"] is True and made["candidate_task_acceptance"] == "NOT_RUN"
    after = table_snapshot(env[0])
    assert all(before[k] == after[k] for k in before if k not in {"app_drafts", "task_extractions"})
    assert len(after["app_drafts"]) == len(before["app_drafts"]) + 1
    assert len(after["task_extractions"]) == len(before["task_extractions"]) + 1
    draft = env[2].get(f"/api/apps/{made['id']}")
    assert draft.status_code == 200, draft.text
    draft = draft.json()
    assert draft["candidate"]["manifest"]["source_run_ref"] == rid
    assert draft["candidate"]["manifest"]["goal_ref"] == original["contract"]["snapshot"]["goal"]["goal_id"]
    assert draft["candidate"]["actions"][0]["effect"] == "read"
    assert "artifact.save_text" not in str(draft["candidate"]["manifest"]["permission_requirements"])
    cold = Store(env[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, env[1])) as reopened:
            reopened.headers["Authorization"] = "Bearer synthetic-test-A"
            recovered = reopened.get(f"/api/runs/{rid}/csv-sum-requests/{body['request_key']}")
            assert recovered.status_code == 200 and recovered.json()["id"] == made["id"]
            preview = reopened.post(f"/api/apps/{made['id']}/previews", json=dict(
                input={"column": "quantity"}, request_key="unseen-independent-check",
            )).json()
            bad = reopened.post(f"/api/apps/{made['id']}/previews", json=dict(
                input={"column": "bad"}, request_key="new-invalid-input",
            )).json()
            assert bad["status"] == "FAILED" and bad["output"] is None
    finally:
        cold.engine.dispose()
    assert preview["status"] == "SUCCEEDED" and preview["output"]["sum"] == "15"
    assert preview["output"]["resource_id"] == material
    assert preview["output"]["sum"] != original["contract"]["snapshot"]["ordinary_csv_report"]["sum"]
    rel, _, _ = release(env, made["id"], made["candidate_fingerprint"])
    instance = create(env, rel)
    queued = enqueue(env, instance, rel, column="quantity")
    assert Worker(env[0], env[1], NoModel()).once()
    result = env[2].get(f"/api/runs/{queued['run_id']}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "15"
    assert result["result_version"] == 1 and result["id"] != rid
    assert env[2].get(f"/api/runs/{rid}").json() == original
    with env[0].tx() as c:
        assert not c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid)).first()
        assert len(c.execute(select(runs)).all()) == 2
    (tmp_path / "sum-only-delivery.json").write_text(json.dumps(dict(
        source=original, options=options, request=body, candidate=draft,
        preview=preview, release=rel, instance=instance, accepted=queued, result=result,
        real_model_requests=0,
    ), ensure_ascii=False, indent=2))


def test_exact_consent_concurrent_request_and_readonly_original_key_recovery(env, tmp_path):
    rid, original, target, _ = setup(env)
    options, body = options_body(env, rid, target)
    before = table_snapshot(env[0])
    missing = {k: v for k, v in body.items() if k != "consent"}
    assert env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=missing).status_code == 422
    assert env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json={**body, "consent": "INCLUDE_MD"}).status_code == 422
    assert table_snapshot(env[0]) == before
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(lambda _: env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=body), range(2)))
    assert all(r.status_code == 201 for r in replies), [r.text for r in replies]
    assert len({r.json()["id"] for r in replies}) == 1
    after = table_snapshot(env[0])
    assert len(after["app_drafts"]) == len(before["app_drafts"]) + 1
    assert len(after["task_extractions"]) == len(before["task_extractions"]) + 1
    assert env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json={**body, "name": "changed"}).status_code == 409
    recovered = env[2].get(f"/api/runs/{rid}/csv-sum-requests/{body['request_key']}")
    assert recovered.status_code == 200 and recovered.json()["id"] == replies[0].json()["id"]
    assert recovered.headers["cache-control"] == "no-store"
    assert table_snapshot(env[0]) == after
    assert env[2].get(f"/api/runs/{rid}").json() == original
    (tmp_path / "idempotency.json").write_text(json.dumps(dict(options=options, body=body,
        replies=[r.json() for r in replies], recovered=recovered.json(), real_model_requests=0), indent=2))


@pytest.mark.parametrize("scope", ["material", "saved-report", "target-runtime", "result"])
def test_source_and_target_rechecked_before_cached_candidate_or_receipt(env, tmp_path, scope):
    rid, original, target, target_resource = setup(env)
    _, body = options_body(env, rid, target)
    made = env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=body).json()
    with env[0].tx() as c:
        if scope == "result":
            changed = dict(original["result"])
            changed["answer"] = "unverified replacement"
            c.execute(update(runs).where(runs.c.id == rid).values(result=changed))
        else:
            resource = (original["contract"]["snapshot"]["ordinary_csv_report"]["resource_id"]
                if scope == "material" else original["result"]["receipts"][-1]["data"]["resource_id"]
                if scope == "saved-report" else target_resource)
            principal = (c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id == target)).scalar_one()
                if scope == "target-runtime" else env[3])
            c.execute(update(grants).where(grants.c.resource_id == resource,
                grants.c.principal_id == principal, grants.c.tool_ref == "resource.read")
                .values(revoked=True, revision=grants.c.revision + 1))
            if scope == "saved-report":
                op = c.execute(select(operations).where(operations.c.run_id == rid,
                    operations.c.tool_ref == "artifact.save_text")).mappings().one()
                c.execute(update(operations).where(operations.c.id == op["id"])
                    .values(receipt={**op["receipt"], "artifact_refs": []}))
    before = table_snapshot(env[0])
    sql = []

    def trace(conn, cursor, statement, parameters, context, executemany):
        sql.append(statement)

    event.listen(env[0].engine, "before_cursor_execute", trace)
    try:
        responses = [env[2].get(f"/api/apps/{made['id']}"),
            env[2].get(f"/api/runs/{rid}/csv-sum-requests/{body['request_key']}"),
            env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=body)]
    finally:
        event.remove(env[0].engine, "before_cursor_execute", trace)
    expected = 409 if scope == "result" else 403
    assert [r.status_code for r in responses] == [expected] * 3, [r.text for r in responses]
    assert table_snapshot(env[0]) == before
    if scope in {"material", "saved-report"}:
        assert not any(s.startswith("SELECT runs.id, runs.project_id, runs.runtime_id, runs.principal_id, runs.request_key") for s in sql)
        assert not any(s.startswith("SELECT app_drafts.id, app_drafts.project_id, app_drafts.runtime_id, app_drafts.name") for s in sql)
    (tmp_path / "scope-proof.json").write_text(json.dumps(dict(scope=scope, statuses=[r.status_code for r in responses], sql=sql, real_model_requests=0), indent=2))


def test_manual_accepted_partial_md_is_not_successful_csv_source(env):
    from test_ordinary_goal_md import execute
    from test_ordinary_owner_review import decision, review
    from test_ordinary_owner_review import prepare as prepare_owner

    _, _, accepted, _, original = execute(env)
    rid = accepted["run_id"]
    prepare_owner(env, rid)
    declared = review(env, rid, "post", decision(env, rid))
    assert declared.status_code == 201 and declared.json()["record"]["status"] == "ACCEPTED"
    assert original["status"] == "PARTIAL"
    before = table_snapshot(env[0])
    response = env[2].get(f"/api/runs/{rid}/csv-sum-candidate-options")
    assert response.status_code == 400 and response.json()["error"]["code"] == "VERIFICATION_FAILED"
    assert table_snapshot(env[0]) == before


def test_completed_source_deadline_is_not_reapplied_to_later_extraction(env, monkeypatch):
    from types import SimpleNamespace

    rid, original, target, _ = setup(env)
    monkeypatch.setattr("sim2act.ordinary_csv.time", SimpleNamespace(time=lambda: original["created_at"] + 3600))
    _, body = options_body(env, rid, target)
    made = env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=body)
    assert made.status_code == 201, made.text
    assert env[2].get(f"/api/apps/{made.json()['id']}").status_code == 200


def test_queued_sum_rechecks_original_source_before_effect(env, tmp_path):
    rid, _, target, _ = setup(env)
    _, body = options_body(env, rid, target)
    made = env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=body).json()
    rel, _, _ = release(env, made["id"], made["candidate_fingerprint"])
    instance = create(env, rel)
    queued = enqueue(env, instance, rel, column="quantity")
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == env[6],
            grants.c.principal_id == env[3], grants.c.tool_ref == "resource.read")
            .values(revoked=True, revision=grants.c.revision + 1))
    before = table_snapshot(env[0])
    worked = Worker(env[0], env[1], NoModel()).once()
    after = table_snapshot(env[0])
    assert all(before[k] == after[k] for k in ["operations", "operation_intents", "local_effects", "resources", "grants", "attempts", "reservations"])
    with env[0].tx() as c:
        row = dict(c.execute(select(runs).where(runs.c.id == queued["run_id"])).mappings().one())
    assert row["status"] == "WAITING_RESOURCE" and row["result"] is None
    assert row["error"]["code"] == "GRANT_REVOKED"
    assert Worker(env[0], env[1], NoModel()).once() is False
    (tmp_path / "queued-source-recheck.json").write_text(json.dumps(dict(worker_return=worked, run=row, real_model_requests=0), indent=2))


@pytest.mark.parametrize("case", ["deliver", "lost", "navigation"])
def test_visible_sum_extraction_through_existing_version_directory_and_use(env, tmp_path, case):
    import hashlib
    import os
    import subprocess
    import threading
    from pathlib import Path

    from sim2act.db import Store, attempts, reservations

    rid, original, target, target_resource = setup(env)
    other = env[0].project(env[3], "Other project")
    env[0].project(env[4], "Other account project")
    before = table_snapshot(env[0])
    info = dict(case=case, run=rid, project=env[5], other=other, target=target,
        target_resource=target_resource, output=str(tmp_path / "page-result.json"))
    (tmp_path / "info.json").write_text(json.dumps(info))
    process = None
    watchdog = None
    worker_runs = []
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/ordinary_csv_extraction.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            watchdog = threading.Timer(90, process.kill)
            watchdog.start()
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    cold = Store(env[1].database_url, test_only=True)
                    try:
                        assert Worker(cold, env[1], NoModel()).once()
                    finally:
                        cold.engine.dispose()
                    actual = env[2].get(f"/api/runs/{request['run']}")
                    assert actual.status_code == 200, actual.text
                    worker_runs.append(actual.json())
                    answer = dict(status=200, text="{}")
                else:
                    response = env[2].request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=response.status_code, text=response.text,
                        content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps(dict(id=request["id"], **answer)) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=15)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        page = json.loads((tmp_path / "page-result.json").read_text())
        assert page["status"] == "PASS"
        for asset in page["assets"]:
            path = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
        after = table_snapshot(env[0])
        assert before["grants"] == after["grants"] and before["principals"] == after["principals"]
        assert before["resources"] == after["resources"]
        assert len(after["task_extractions"]) == 1
        assert env[2].get(f"/api/runs/{rid}").json() == original
        with env[0].tx() as c:
            assert not c.execute(select(attempts)).first() and not c.execute(select(reservations)).first()
            assert not c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid)).first()
        assert len(worker_runs) == (0 if case == "navigation" else 1)
    finally:
        if watchdog is not None:
            watchdog.cancel()
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "page-worker-proof.json").write_text(json.dumps(dict(
            original=original, worker_runs=worker_runs, real_model_requests=0,
        ), ensure_ascii=False, indent=2))
