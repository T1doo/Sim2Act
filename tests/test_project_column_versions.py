"""Real worker reuse of accepted overlays, atomic groups and cold new inputs."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_csv_dag import NoModel
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
from test_project_column_patches import start, work
from test_run_dispatch_owner import assert_no_ledger_read, statements

from sim2act import csv_dag as dag
from sim2act import lifecycle
from sim2act import project_column_versions as versions
from sim2act.api import create_app
from sim2act.db import Store, grants, internal_instances, internal_releases, resources
from sim2act.errors import DomainError
from sim2act.worker import Worker


def ready(env):
    values, patch, confirmation, acceptance = start(env)
    work(env, acceptance)
    r = env[2].post(values[0] + "/project-binding/finalize", json=confirmation)
    assert r.status_code == 201, r.text
    base = values[0] + "/project-binding/internal-versions"
    body = dict(expected_receipt_fingerprint=r.json()["receipt_fingerprint"], request_key="project-binding")
    return values, patch, base, body


def preview(env):
    values, patch, base, body = ready(env)
    r = env[2].post(base, json=body)
    assert r.status_code == 201, r.text
    p = r.json()
    confirm = dict(expected_preview_fingerprint=p["preview_fingerprint"],
                   consent="CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS", request_key="project-binding")
    return values, patch, base, body, p, confirm


def created(env):
    values, patch, base, body, p, confirm = preview(env)
    r = env[2].post(base + "/commit", json=confirm)
    assert r.status_code == 201, r.text
    return values, patch, base, body, p, confirm, r.json()


def run_job(env, client, i, rel, column, key):
    r = client.post(f"/api/internal/instances/{i['id']}/runs", json=dict(
        expected_revision=i["revision"], expected_release_fingerprint=rel["fingerprint"],
        input={"column": column}, request_key=key))
    assert r.status_code == 202, r.text
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job and job["id"] == r.json()["run_id"]
    worker.process(job)
    proof = client.get(f"/api/internal/instances/{i['id']}")
    assert proof.status_code == 200, proof.text
    actual = next(v for v in proof.json()["runs"] if v["run_id"] == job["id"])
    assert actual["status"] == "SUCCEEDED", actual
    assert len(actual["proof"]["steps"]) == 3 and actual["proof"]["business_writes"] == 1
    assert actual["output"]["column"] == column and actual["output"]["sum"] == ("15" if column == "quantity" else "30")
    return actual


def test_group_cold_new_inputs_true_worker_old_version_preserved(env):
    values, patch, base, body = ready(env)
    # A genuine older immutable canonical version and its data survive group creation.
    approval = lifecycle.prepare_release(env[0], env[3], values[2], next(a["patch"]["candidate_fingerprint"] for a in patch["affected"] if a["app_id"] == values[2]),
                                         limits(env), {"column": "amount"})
    old = lifecycle.commit_release(env[0], env[3], approval["id"], approval["fingerprint"], limits(env))
    old_i = lifecycle.create_instance(env[0], env[3], old["id"], old["fingerprint"], limits(env))
    before = snapshot(env)
    p = env[2].post(base, json=body)
    assert p.status_code == 201, p.text
    confirm = dict(expected_preview_fingerprint=p.json()["preview_fingerprint"],
                   consent="CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS", request_key=body["request_key"])
    response = env[2].post(base + "/commit", json=confirm)
    assert response.status_code == 201, response.text
    group = response.json()
    assert len(group["entries"]) == 2 and group["state"] == "EXECUTABLE_INTERNAL_VERSIONS"
    after = snapshot(env)
    for table in before:
        if table not in {"delivery_graph_requests", "internal_approvals", "internal_releases", "internal_instances"}:
            assert before[table] == after[table], table
    assert all(r in after["internal_releases"] for r in before["internal_releases"])
    assert all(r in after["internal_instances"] for r in before["internal_instances"])
    cold_store = Store(env[1].database_url, test_only=True)
    cold = TestClient(create_app(cold_store, env[1]))
    cold.headers["Authorization"] = "Bearer synthetic-test-A"
    try:
        assert cold.get(base).json() == {k: v for k, v in group.items() if k != "cached"}
        for entry in group["entries"]:
            rel = cold.get(f"/api/internal/releases/{entry['release_id']}").json()
            i = cold.get(f"/api/internal/instances/{entry['instance_id']}").json()
            e = rel["snapshot"]["execution_source"]
            assert e["default_column"] == "quantity" and set(e["columns"]) == {"amount", "quantity"}
            assert rel["snapshot"]["column_overlay"]["column_binding"]["value"] == "quantity"
            assert rel["snapshot"]["publishable"] is False and group["canonical_patch_executed"] is False
            a = run_job(env, cold, i, rel, e["default_column"], "cold-new-column")
            b = run_job(env, cold, i, rel, "amount", "cold-unseen-input")
            assert a["run_id"] != b["run_id"] != e["run_id"]
        old_result = lifecycle.run_instance(env[0], env[3], old_i["id"], 1, old["fingerprint"],
                                            {"column": "amount"}, "old-still-runs", limits(env))
        assert old_result["output"]["sum"] == "30"
        before_read = snapshot(env)
        assert cold.get(base).status_code == 200
        assert cold.post(base + "/commit", json=confirm).json()["cached"] is True
        assert snapshot(env) == before_read
    finally:
        cold.close()
        cold_store.engine.dispose()


@pytest.mark.parametrize("point", ["release", "instance", "final_revoke", "final_expiry"])
def test_entire_group_rolls_back_later_failure(env, monkeypatch, point):
    _, _, base, _, p, confirm = preview(env)
    before = snapshot(env)
    if point in {"release", "instance"}:
        name = "commit_release_tx" if point == "release" else "create_instance_tx"
        original = getattr(lifecycle, name)
        calls = []

        def fail(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise DomainError("BUDGET_EXHAUSTED", "Injected second application failure")
            return original(*args, **kwargs)

        monkeypatch.setattr(lifecycle, name, fail)
    else:
        original = versions.patches.save_pair

        def fail(c, user, aid, kind, *args):
            original(c, user, aid, kind, *args)
            if kind == versions.COMMIT:
                if point == "final_revoke":
                    c.execute(update(grants).values(revoked=True))
                else:
                    monkeypatch.setattr(versions.time, "time", lambda: p["expires_at"])

        monkeypatch.setattr(versions.patches, "save_pair", fail)
    r = env[2].post(base + "/commit", json=confirm)
    assert r.status_code in {400, 403, 409}, r.text
    assert snapshot(env) == before
    assert not before["internal_releases"] and not before["internal_instances"]
    if point in {"release", "instance"}:
        assert len(calls) == 2


def test_single_approval_cannot_bypass_whole_group(env):
    _, _, _, _, p, _ = preview(env)
    before = snapshot(env)
    for entry in p["entries"]:
        a = entry["approval"]
        r = env[2].post(f"/api/internal/approvals/{a['id']}/commit", json={"fingerprint": a["fingerprint"]})
        assert r.status_code == 403, r.text
    assert snapshot(env) == before


def test_approval_source_evidence_actual_run_read_only_and_authorized(env):
    values, _, base, _, p, confirm = preview(env)
    before = snapshot(env)
    for entry in p["entries"]:
        endpoint = f"/api/internal/approvals/{entry['approval']['id']}/project-column-origin"
        r = env[2].get(endpoint)
        assert r.status_code == 200, r.text
        actual = r.json()
        assert set(actual) == {"namespace", "approval_id", "approval_fingerprint", "origin", "execution_source"}
        assert actual["execution_source"] == entry["snapshot"]["execution_source"]
        assert actual["origin"] == entry["snapshot"]["project_column_origin"]
        with env[0].tx() as c:
            source = dag.row(c, env[3], actual["execution_source"]["run_id"])
            assert actual["execution_source"]["accepted_fingerprint"] == source["fingerprint"]
        assert snapshot(env) == before
    group = env[2].post(base + "/commit", json=confirm)
    assert group.status_code == 201, group.text
    entry = group.json()["entries"][0]
    release_path = f"/api/internal/releases/{entry['release_id']}"
    endpoints = [endpoint, release_path, release_path + "/project-column-origin"]
    before = snapshot(env)
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    for path in endpoints:
        with statements(env[0]) as seen:
            assert env[2].get(path).status_code == 403
        assert_no_ledger_read(seen)
        assert snapshot(env) == before
    env[2].headers["Authorization"] = "Bearer synthetic-test-A"
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == values[5]).values(revoked=True))
    before = snapshot(env)
    for path in endpoints:
        with statements(env[0]) as seen:
            assert env[2].get(path).status_code == 403
        assert_no_ledger_read(seen)
        assert snapshot(env) == before


@pytest.mark.parametrize("attack", ["grant", "source", "expiry", "confirmation", "key", "budget"])
def test_frozen_group_rejects_current_change_zero_writes(env, monkeypatch, attack):
    values, _, base, _, p, confirm = preview(env)
    if attack in {"grant", "source"}:
        with env[0].tx() as c:
            if attack == "grant":
                c.execute(update(grants).where(grants.c.resource_id == values[5]).values(revoked=True))
            else:
                c.execute(update(resources).where(resources.c.id == values[5]).values(content="changed"))
    elif attack == "expiry":
        monkeypatch.setattr(versions.time, "time", lambda: p["expires_at"])
    elif attack == "budget":
        object.__setattr__(env[1], "max_tools", env[1].max_tools - 1)
    else:
        confirm["request_key" if attack == "key" else "expected_preview_fingerprint"] = "other" if attack == "key" else "0" * 64
    before = snapshot(env)
    r = env[2].post(base + "/commit", json=confirm)
    assert r.status_code in {400, 403, 409}, r.text
    assert snapshot(env) == before


def test_cancel_original_group_and_late_commit(env):
    _, _, base, body, p, confirm = preview(env)
    cancel = {**confirm, "consent": "CANCEL_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS"}
    r = env[2].post(base + "/cancel", json=cancel)
    assert r.status_code == 200 and r.json()["state"] == "CANCELLED", r.text
    before = snapshot(env)
    assert env[2].get(base).json()["state"] == "CANCELLED"
    assert env[2].post(base + "/commit", json=confirm).status_code == 409
    assert env[2].post(base + "/cancel", json=cancel).status_code == 200
    assert env[2].post(base, json=body).json()["preview_fingerprint"] == p["preview_fingerprint"]
    assert snapshot(env) == before


def test_concurrent_exact_confirmation_single_group(env):
    values, _, base, _, _, confirm = preview(env)
    args = (env[0], env[3], env[5], values[2], "project-binding", versions.Confirmation(**confirm), limits(env))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: versions.commit(*args), range(2)))
    assert sorted(r["cached"] for r in results) == [False, True]
    assert results[0]["entries"] == results[1]["entries"]
    with env[0].tx() as c:
        assert len(c.execute(select(internal_releases)).all()) == len(c.execute(select(internal_instances)).all()) == 2
    assert env[2].get(base).status_code == 200


@pytest.mark.parametrize("entry", ["read", "definition", "preview", "commit", "cancel"])
@pytest.mark.parametrize("scope", ["identity", "project"])
def test_foreign_scope_before_protected_receipt_read(env, entry, scope):
    _, _, base, body, _, confirm = preview(env)
    if scope == "identity":
        env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    else:
        other = env[0].project(env[3], "Other owned project")
        base = base.replace(env[5], other)
    before = snapshot(env)
    with statements(env[0]) as seen:
        r = (env[2].get(base + ("/definition" if entry == "definition" else "")) if entry in {"read", "definition"}
             else env[2].post(base + ("" if entry == "preview" else "/" + entry),
                json=body if entry == "preview" else {**confirm, "consent": "CANCEL_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS"} if entry == "cancel" else confirm))
    assert r.status_code == 403, r.text
    assert_no_ledger_read(seen)
    assert snapshot(env) == before


def test_original_group_get_after_actual_inputs_and_approved_a_b_a(env):
    from test_csv_dag_version_switch import switch

    values, _, base, _, _, confirm, group = created(env)
    peer = values[2]
    old_entry = next(e for e in group["entries"] if e["app_id"] == peer)
    i = env[2].get(f"/api/internal/instances/{old_entry['instance_id']}").json()
    old = env[2].get(f"/api/internal/releases/{old_entry['release_id']}").json()
    run_job(env, env[2], i, old, "quantity", "before-switch")
    # Same finite source and ports, different accepted column default; no hand-built workflow.
    proposal = {**values[1], "baseline_column": "quantity", "column": "amount", "request_key": "second-group"}
    p = env[2].post(values[0], json=proposal)
    assert p.status_code == 201, p.text
    exact = dict(expected_patch_fingerprint=p.json()["patch_fingerprint"],
                 consent="CONFIRM_EXACT_FINITE_PROJECT_COLUMN_PATCH", request_key="second-group")
    acceptance = env[2].post(values[0] + "/second-group/runs", json=exact)
    assert acceptance.status_code == 202, acceptance.text
    work(env, acceptance.json())
    receipt = env[2].post(values[0] + "/second-group/finalize", json=exact)
    assert receipt.status_code == 201, receipt.text
    second_base = values[0] + "/second-group/internal-versions"
    p = env[2].post(second_base, json=dict(expected_receipt_fingerprint=receipt.json()["receipt_fingerprint"], request_key="second-group"))
    assert p.status_code == 201, p.text
    r = env[2].post(second_base + "/commit", json=dict(expected_preview_fingerprint=p.json()["preview_fingerprint"],
        consent="CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS", request_key="second-group"))
    assert r.status_code == 201, r.text
    target_entry = next(e for e in r.json()["entries"] if e["app_id"] == peer)
    target = env[2].get(f"/api/internal/releases/{target_entry['release_id']}").json()
    i = env[2].get(f"/api/internal/instances/{i['id']}").json()
    i, _ = switch(env, i, target)
    run_job(env, env[2], i, target, "amount", "after-switch")
    # GET must work while the current pointer differs from the original group.
    before = snapshot(env)
    assert env[2].get(base).status_code == 200
    assert env[2].post(base + "/commit", json=confirm).json()["cached"] is True
    assert snapshot(env) == before
    i = env[2].get(f"/api/internal/instances/{i['id']}").json()
    i, _ = switch(env, i, old)
    assert i["revision"] == 3 and i["data_version"] == 2
    assert [r["data"]["result"]["sum"] for r in i["data"]] == ["15", "30"]
    before = snapshot(env)
    assert env[2].get(base).status_code == 200
    assert snapshot(env) == before


@pytest.mark.parametrize("fault", ["cancel", "bad_sum"])
def test_new_actual_worker_failure_history_never_writes_typed_success(env, monkeypatch, fault):
    _, _, _, _, _, _, group = created(env)
    e = group["entries"][0]
    i = env[2].get(f"/api/internal/instances/{e['instance_id']}").json()
    r = env[2].post(f"/api/internal/instances/{i['id']}/runs", json=dict(
        expected_revision=1, expected_release_fingerprint=e["release_fingerprint"], input={"column": "quantity"}, request_key="failure-history"))
    assert r.status_code == 202, r.text
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    if fault == "cancel":
        assert dag.advance(worker, job)
        with env[0].tx() as c:
            version = dag.row(c, env[3], job["id"])["version"]
        cancelled = env[2].post(f"/api/internal/instances/{i['id']}/runs/{job['id']}/commands", json=dict(command="cancel", version=version))
        assert cancelled.status_code == 200, cancelled.text
    else:
        original = dag.authorized_read

        def wrong(*args, **kwargs):
            result = original(*args, **kwargs)
            return {**result, "sum": "999"} if args[-2] == "data.aggregate_csv" else result

        monkeypatch.setattr(dag, "authorized_read", wrong)
    worker.process(job)
    result = env[2].get(f"/api/internal/instances/{i['id']}")
    assert result.status_code == 200, result.text
    detail = result.json()
    assert detail["data"] == [] and detail["data_version"] == 0
    actual = detail["runs"][0]
    assert actual["status"] == ("CANCELLED" if fault == "cancel" else "FAILED")
    assert actual["proof"]["business_writes"] == 0 and actual["result_version"] is None


def test_unrelated_project_growth_does_not_block_peer_cold_execution(env):
    values, _, base, _, _, _, group = created(env)
    entry = next(e for e in group["entries"] if e["app_id"] == values[2])
    new_app = env[2].post(f"/api/projects/{env[5]}/apps/csv-preview", json=dict(
        name="new unrelated instance", goal="later independent draft", resource_id=values[5]))
    assert new_app.status_code == 201, new_app.text
    before = snapshot(env)
    # Original group no longer proves current project membership, but existing
    # immutable peer version remains authorized and independently executable.
    assert env[2].get(base).status_code == 409
    origin = env[2].get(f"/api/internal/releases/{entry['release_id']}/project-column-origin")
    assert origin.status_code == 200, origin.text
    assert set(origin.json()) == {"namespace", "release_id", "release_fingerprint", "origin", "affected", "source", "execution_source"}
    assert origin.json()["affected"]["app_id"] == values[2]
    assert snapshot(env) == before
    rel = env[2].get(f"/api/internal/releases/{entry['release_id']}").json()
    i = env[2].get(f"/api/internal/instances/{entry['instance_id']}").json()
    run_job(env, env[2], i, rel, "quantity", "after-project-growth")
