"""Actual finite multi-app patch checks, atomic acceptance and preservation."""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_column_patches import setup as source_setup
from test_csv_dag import NoModel
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
from test_run_dispatch_owner import assert_no_ledger_read, statements

from sim2act import csv_dag as dag
from sim2act import project_column_patches as patches
from sim2act.api import create_app
from sim2act.db import (
    Store,
    delivery_graph_requests,
    fingerprint,
    grants,
    operations,
    resources,
    runs,
)
from sim2act.delivery_graph_apps import set_lock
from sim2act.errors import DomainError
from sim2act.worker import Worker


def setup(env):
    client, pid = env[2], env[5]
    aid, rid, anchor, _, _ = source_setup(env)
    peer = client.post(f"/api/projects/{pid}/apps/csv-preview", json=dict(
        name="shared peer", goal="fixed CSV peer", resource_id=rid)).json()
    assert "id" in peer, peer
    peer = client.get(f"/api/apps/{peer['id']}").json()
    derived = client.post(f"/api/projects/{pid}/apps/{peer['id']}/delivery-graph/derive", json=dict(
        expected_candidate_fingerprint=peer["fingerprint"], request_key="peer-anchor"))
    assert derived.status_code == 201, derived.text
    unrelated, _, unrelated_graph, _, old_preview = source_setup(env)
    node = next(n for n in unrelated_graph["graph"]["nodes"] if n["kind"] == "VIEW")
    lock = set_lock(env[0], env[3], pid, unrelated, dict(
        expected_graph_fingerprint=unrelated_graph["graph_fingerprint"], request_key="human-view",
        change=dict(node_id=node["id"], expected_revision=node["revision"],
                    expected_content_fingerprint=node["content_fingerprint"]), locked=True), limits(env))
    assert lock["lock"]["locked"]
    # Grant additions and manual locks invalidate old anchors. Re-derive all.
    for app in (aid, peer["id"], unrelated):
        candidate = client.get(f"/api/apps/{app}").json()
        response = client.post(f"/api/projects/{pid}/apps/{app}/delivery-graph/derive", json=dict(
            expected_candidate_fingerprint=candidate["fingerprint"], request_key="fresh-" + app))
        assert response.status_code == 201, response.text
        if app == aid:
            anchor = response.json()
    base = f"/api/projects/{pid}/apps/{aid}/project-column-patches"
    body = dict(expected_candidate_fingerprint=anchor["candidate_fingerprint"],
                expected_graph_fingerprint=anchor["graph_fingerprint"], baseline_column="amount",
                column="quantity", request_key="project-binding")
    return base, body, aid, peer["id"], unrelated, rid, old_preview


def preview(env):
    values = setup(env)
    response = env[2].post(values[0], json=values[1])
    assert response.status_code == 201, response.text
    patch = response.json()
    confirmation = dict(expected_patch_fingerprint=patch["patch_fingerprint"],
                        consent="CONFIRM_EXACT_FINITE_PROJECT_COLUMN_PATCH", request_key=values[1]["request_key"])
    return values, patch, confirmation


def start(env):
    values, patch, confirmation = preview(env)
    response = env[2].post(values[0] + "/project-binding/runs", json=confirmation)
    assert response.status_code == 202, response.text
    return values, patch, confirmation, response.json()


def work(env, acceptance):
    worker = Worker(env[0], env[1], NoModel())
    jobs = []
    for _ in acceptance["jobs"]:
        job = env[0].claim(worker.id, env[1].lease_seconds)
        assert job and job["id"] in {v["run_id"] for v in acceptance["jobs"]}
        worker.process(job)
        jobs.append(job)
    return jobs


def assert_domain(before, after):
    allowed = {"delivery_graph_requests", "runs", "run_contracts", "events", "operations", "operation_intents"}
    for table in before:
        if table not in allowed:
            assert before[table] == after[table], table


def test_actual_shared_workers_atomic_checked_overlay_cold_read_preserves_locks(env, tmp_path):
    values, patch, confirmation, acceptance = start(env)
    base, _, aid, peer, unrelated, rid, _ = values
    assert {x["app_id"] for x in patch["affected"]} == {aid, peer}
    assert [x["app_id"] for x in patch["preserved"]] == [unrelated]
    assert patch["budget"]["worker_tools"] == 12
    preserved = patch["preserved"][0]["nodes"]
    assert any(n["locked"] and n["kind"] == "VIEW" for n in preserved)
    for item in patch["affected"]:
        modified = item["patch"]["modified_objects"]
        assert {n["kind"] for n in modified} == {"ACTION", "ARTIFACT", "VIEW", "CHECK", "MANIFEST"}
        assert {n["kind"] for n in item["patch"]["preserved_objects"]} == {"SOURCE", "GOAL", "REQUIREMENT"}
    before = snapshot(env)
    early = env[2].post(base + "/project-binding/finalize", json=confirmation)
    assert early.status_code == 400 and early.json()["error"]["code"] == "VERIFICATION_FAILED", early.text
    assert snapshot(env) == before
    work(env, acceptance)
    after_worker = snapshot(env)
    read = env[2].get(base + "/project-binding")
    assert read.status_code == 200, read.text
    assert read.json()["checks_status"] == "PASS" and read.json()["state"] == "CHECKS_COMPLETE"
    assert snapshot(env) == after_worker  # GET never dispatches or saves anything.
    for job in read.json()["jobs"]:
        assert len(job["proof"]["steps"]) == 3
        output = job["proof"]["result"]["output"]
        assert output["sum"] == ("30" if job["phase"] == "baseline" else "15")
        assert output["resource_id"] == rid and job["proof"]["status"] == "SUCCEEDED"
    response = env[2].post(base + "/project-binding/finalize", json=confirmation)
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["finite_revalidation_completed"] and receipt["draft_patch_executed"]
    assert receipt["state"] == "CHECKED_PROJECT_CANDIDATE" and receipt["preserved"] == patch["preserved"]
    assert receipt["canonical_patch_executed"] is False and receipt["semantic_status"] == "UNKNOWN"
    assert receipt["owner_acceptance"] == "PENDING" and receipt["publishable"] is False
    after = snapshot(env)
    assert_domain(before, after)
    assert len(after["delivery_graph_requests"]) == len(after_worker["delivery_graph_requests"]) + 2
    store = Store(env[1].database_url, test_only=True)
    cold = TestClient(create_app(store, env[1]))
    cold.headers["Authorization"] = "Bearer synthetic-test-A"
    try:
        result = cold.get(base + "/project-binding")
        assert result.status_code == 200 and result.json()["receipt_fingerprint"] == receipt["receipt_fingerprint"], result.text
        assert cold.post(base + "/project-binding/runs", json=confirmation).json()["cached"]
        assert cold.post(base + "/project-binding/finalize", json=confirmation).json()["cached"]
        assert snapshot(env) == after
        (tmp_path / "actual-project-proof.json").write_text(json.dumps(receipt, indent=2))
    finally:
        cold.close()
        store.engine.dispose()


@pytest.mark.parametrize("attack", ["column", "same_column", "candidate", "graph", "unicode", "scope", "gold"])
def test_invalid_proposal_zero_write(env, attack):
    base, body, *_ = setup(env)
    if attack == "column":
        body["column"] = "item"
    elif attack == "same_column":
        body["column"] = body["baseline_column"]
    elif attack in {"candidate", "graph"}:
        body["expected_" + attack + "_fingerprint"] = "0" * 64
    elif attack == "unicode":
        body["column"] = "bad\ud800"
    else:
        body[attack] = "bypass"
    before = snapshot(env)
    result = env[2].post(base, content=json.dumps(body), headers={"Content-Type": "application/json"})
    assert result.status_code in {400, 409, 422}, result.text
    assert snapshot(env) == before


def test_atomic_start_later_peer_failure_leaves_no_partial_jobs(env, monkeypatch):
    values, _, body = preview(env)
    before = snapshot(env)
    original = dag.enqueue_tx
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        if len(calls) == 3:
            raise DomainError("BUDGET_EXHAUSTED", "Injected later peer failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(dag, "enqueue_tx", fail)
    result = env[2].post(values[0] + "/project-binding/runs", json=body)
    assert result.status_code == 400, result.text
    assert len(calls) == 3 and snapshot(env) == before


@pytest.mark.parametrize("attack", ["grant", "source", "membership", "lock", "budget", "identity", "confirmation"])
def test_stale_confirmation_never_accepts_partial_runs(env, attack):
    values, _, body = preview(env)
    base, _, aid, _, unrelated, rid, _ = values
    if attack == "membership":
        env[2].post(f"/api/projects/{env[5]}/apps/csv-preview", json=dict(name="late", goal="late", resource_id=rid))
    elif attack == "lock":
        anchor = env[2].get(f"/api/projects/{env[5]}/apps/{unrelated}/delivery-graph").json()
        node = next(n for n in anchor["graph"]["nodes"] if n["kind"] == "GOAL")
        reply = set_lock(env[0], env[3], env[5], unrelated, dict(
            expected_graph_fingerprint=anchor["graph_fingerprint"], request_key="late-lock",
            change=dict(node_id=node["id"], expected_revision=node["revision"], expected_content_fingerprint=node["content_fingerprint"]), locked=True), limits(env))
        assert reply["lock"]["locked"]
    elif attack in {"source", "grant"}:
        with env[0].tx() as c:
            if attack == "source":
                c.execute(update(resources).where(resources.c.id == rid).values(content="changed"))
            else:
                c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
    elif attack == "identity":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif attack == "confirmation":
        body["expected_patch_fingerprint"] = "0" * 64
    before = snapshot(env)
    if attack == "budget":
        smaller = limits(env).model_copy(update={"run_seconds": 299})
        with pytest.raises(DomainError):
            patches.start(env[0], env[3], env[5], aid, "project-binding", patches.Confirmation(**body), smaller)
    else:
        result = env[2].post(base + "/project-binding/runs", json=body)
        assert result.status_code in {400, 403, 409}, result.text
    assert snapshot(env) == before


@pytest.mark.parametrize("attack", ["cancel", "failed", "late", "future", "grant", "forged_receipt"])
def test_failed_cancelled_revoked_late_or_forged_jobs_cannot_finalize(env, attack):
    values, _, body, acceptance = start(env)
    base = values[0]
    work(env, acceptance)
    with env[0].tx() as c:
        rid = acceptance["jobs"][0]["run_id"]
        if attack == "grant":
            c.execute(update(grants).where(grants.c.resource_id == values[5]).values(revoked=True))
        elif attack == "forged_receipt":
            row = c.execute(select(operations).where(operations.c.run_id == rid, operations.c.call_id == "aggregate")).mappings().one()
            value = copy.deepcopy(row["receipt"])
            value["data"]["sum"] = "999"
            value["output_fingerprint"] = fingerprint(value["data"])
            c.execute(update(operations).where(operations.c.id == row["id"]).values(receipt=value))
        else:
            c.execute(update(runs).where(runs.c.id == rid).values(**(
                {"cancel_intent": True} if attack == "cancel" else
                {"status": "FAILED", "result": None} if attack == "failed" else
                {"created_at": time.time() + 301} if attack == "future" else
                {"created_at": time.time() - 301})))
    before = snapshot(env)
    result = env[2].post(base + "/project-binding/finalize", json=body)
    assert result.status_code in {400, 403, 409}, result.text
    assert snapshot(env) == before
    assert not [r for r in before["delivery_graph_requests"] if r["kind"] == patches.FINISH]


def test_concurrent_original_confirmation_accepts_one_job_set(env):
    values, patch, body = preview(env)
    args = (env[0], env[3], env[5], values[2], "project-binding", patches.Confirmation(**body), limits(env))
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(lambda _: patches.start(*args), range(2)))
    assert answers[0]["jobs"] == answers[1]["jobs"]
    assert sorted(v["cached"] for v in answers) == [False, True]
    with env[0].tx() as c:
        assert len(c.execute(select(runs.c.id)).scalars().all()) == 4


@pytest.mark.parametrize("attack", ["PROJECT", "APP_UNKNOWN", "SEMANTIC", "MODEL_CANDIDATE"])
def test_semantic_and_unknown_dependencies_are_rejected(env, monkeypatch, attack):
    values = setup(env)
    original = patches.graph.current

    def opaque(*args, **kwargs):
        saved = copy.deepcopy(original(*args, **kwargs))
        if attack == "PROJECT":
            saved["graph"]["unknown_dependencies"][0]["scope"] = "PROJECT"
        elif attack == "APP_UNKNOWN":
            saved["graph"]["unknown_dependencies"][0]["reason"] = "An opaque dynamic dependency"
        else:
            saved["graph"]["edges"][0]["type" if attack == "SEMANTIC" else "provenance"] = attack
        return saved

    monkeypatch.setattr(patches.graph, "current", opaque)
    before = snapshot(env)
    response = env[2].post(values[0], json=values[1])
    assert response.status_code == 400 and response.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY", response.text
    assert snapshot(env) == before


def test_resigned_finish_pair_cannot_accept_bool_integer_equivalence(env):
    values, _, body, acceptance = start(env)
    work(env, acceptance)
    result = env[2].post(values[0] + "/project-binding/finalize", json=body)
    assert result.status_code == 201, result.text
    with env[0].tx() as c:
        for kind in (patches.FINISH, patches.FINISH + "_seal"):
            row = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind == kind)).mappings().one()
            value = copy.deepcopy(row["snapshot"])
            value["response"]["finite_revalidation_completed"] = 1
            c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.kind == kind)
                      .values(snapshot=value, fingerprint=fingerprint(value)))
    before = snapshot(env)
    for method in ("get", "post"):
        result = (env[2].get(values[0] + "/project-binding") if method == "get" else
                  env[2].post(values[0] + "/project-binding/finalize", json=body))
        assert result.status_code == 409, result.text
        assert snapshot(env) == before


def test_finalize_expiry_after_receipt_insert_rolls_back_pair(env, monkeypatch):
    values, _, body, acceptance = start(env)
    work(env, acceptance)
    original = patches.save_pair
    clock = time.time()

    def expire(*args, **kwargs):
        original(*args, **kwargs)
        monkeypatch.setattr(patches.time, "time", lambda: clock + 400)

    monkeypatch.setattr(patches, "save_pair", expire)
    before = snapshot(env)
    result = env[2].post(values[0] + "/project-binding/finalize", json=body)
    assert result.status_code == 400 and result.json()["error"]["code"] == "BUDGET_EXHAUSTED", result.text
    assert snapshot(env) == before


def test_actual_worker_bad_sum_keeps_failure_history_and_no_checked_patch(env, monkeypatch):
    values, _, body, acceptance = start(env)
    original = dag.authorized_read

    def bad_sum(*args, **kwargs):
        value = original(*args, **kwargs)
        if args[-2] == "data.aggregate_csv" and args[-1]["column"] == "quantity":
            return {**value, "sum": "999"}
        return value

    monkeypatch.setattr(dag, "authorized_read", bad_sum)
    work(env, acceptance)
    before = snapshot(env)
    read = env[2].get(values[0] + "/project-binding")
    assert read.status_code == 200 and read.json()["checks_status"] == "FAIL", read.text
    assert [j["proof"]["status"] for j in read.json()["jobs"]].count("FAILED") == 2
    assert env[2].post(values[0] + "/project-binding/finalize", json=body).status_code == 400
    assert snapshot(env) == before
    assert any(r["kind"] == "STATE" and r["data"]["status"] == "FAILED" for r in before["events"])


def test_actual_cancel_at_worker_boundary_blocks_late_worker_and_group_commit(env):
    values, _, body, acceptance = start(env)
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert dag.advance(worker, job)
    with env[0].tx() as c:
        live = dag.row(c, env[3], job["id"])
    response = env[2].post(f"/api/runs/{job['id']}/commands", json=dict(command="cancel", version=live["version"]))
    assert response.status_code == 200, response.text
    worker.process(job)
    with env[0].tx() as c:
        assert dag.row(c, env[3], job["id"])["status"] == "CANCELLED"
        assert c.execute(select(operations.c.call_id).where(operations.c.run_id == job["id"])).scalars().all() == ["preview"]
    before = snapshot(env)
    with pytest.raises(DomainError):
        dag.advance(worker, job)
    assert snapshot(env) == before
    result = env[2].post(values[0] + "/project-binding/finalize", json=body)
    assert result.status_code == 400, result.text
    assert snapshot(env) == before


def test_finalize_revoke_after_receipt_insert_rolls_back_pair(env, monkeypatch):
    values, _, body, acceptance = start(env)
    work(env, acceptance)
    original = patches.save_pair

    def revoke(c, *args, **kwargs):
        original(c, *args, **kwargs)
        c.execute(update(grants).where(grants.c.resource_id == values[5]).values(revoked=True))

    monkeypatch.setattr(patches, "save_pair", revoke)
    before = snapshot(env)
    result = env[2].post(values[0] + "/project-binding/finalize", json=body)
    assert result.status_code in {403, 409}, result.text
    assert snapshot(env) == before


def test_unrelated_lock_unlock_aba_expires_original_project_proof(env):
    values, _, confirmation = preview(env)
    unrelated = values[4]
    base = f"/api/projects/{env[5]}/apps/{unrelated}/delivery-graph"
    original = env[2].get(base).json()
    for index, locked in enumerate((False, True)):
        anchor = env[2].get(base).json()
        node = next(n for n in anchor["graph"]["nodes"] if n["kind"] == "VIEW")
        set_lock(env[0], env[3], env[5], unrelated, dict(
            expected_graph_fingerprint=anchor["graph_fingerprint"], request_key="aba-" + str(index),
            locked=locked, change=dict(node_id=node["id"], expected_revision=node["revision"],
                                      expected_content_fingerprint=node["content_fingerprint"])), limits(env))
        draft = env[2].get(f"/api/apps/{unrelated}").json()
        result = env[2].post(base + "/derive", json=dict(expected_candidate_fingerprint=draft["fingerprint"],
                                                       request_key="aba-derive-" + str(index)))
        assert result.status_code == 201, result.text
    assert env[2].get(base).json()["graph_fingerprint"] == original["graph_fingerprint"]
    before = snapshot(env)
    response = env[2].post(values[0] + "/project-binding/runs", json=confirmation)
    assert response.status_code == 409, response.text
    assert snapshot(env) == before


def test_affected_manual_lock_rejects_before_any_project_overlay(env):
    values = setup(env)
    peer = values[3]
    base = f"/api/projects/{env[5]}/apps/{peer}/delivery-graph"
    anchor = env[2].get(base).json()
    node = next(n for n in anchor["graph"]["nodes"] if n["key"] == "action:aggregate")
    set_lock(env[0], env[3], env[5], peer, dict(expected_graph_fingerprint=anchor["graph_fingerprint"],
        request_key="affected-lock", locked=True, change=dict(node_id=node["id"],
        expected_revision=node["revision"], expected_content_fingerprint=node["content_fingerprint"])), limits(env))
    response = env[2].post(base + "/derive", json=dict(expected_candidate_fingerprint=anchor["candidate_fingerprint"], request_key="affected-derived"))
    assert response.status_code == 201, response.text
    before = snapshot(env)
    response = env[2].post(values[0], json=values[1])
    assert response.status_code == 400 and response.json()["error"]["code"] == "LOCK_CONFLICT", response.text
    assert snapshot(env) == before


@pytest.mark.parametrize("entry", ["read", "definition", "start", "finalize"])
@pytest.mark.parametrize("principal", ["foreign", "other_owned_project"])
def test_foreign_scope_rejected_before_protected_receipt_reads(env, entry, principal):
    values, _, confirmation = preview(env)
    base = values[0] + "/project-binding"
    if principal == "foreign":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    else:
        other = env[0].project(env[3], "Different owned project")
        base = base.replace(env[5], other)
    before = snapshot(env)
    with statements(env[0]) as seen:
        response = (env[2].get(base + ("/definition" if entry == "definition" else ""))
                    if entry in {"read", "definition"} else
                    env[2].post(base + ("/runs" if entry == "start" else "/finalize"), json=confirmation))
    assert response.status_code == 403, response.text
    assert_no_ledger_read(seen)
    assert snapshot(env) == before
