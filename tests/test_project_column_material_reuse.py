"""Modified fixed versions reuse only independently authorized target CSV bytes."""

import csv
import io
import json
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create
from test_csv_logic_reuse import authorize, retire_old
from test_delivery_graph_apps import snapshot
from test_project_column_patches import setup as project_setup
from test_project_column_patches import work as project_work

from sim2act import csv_dag as dag
from sim2act import csv_dag_instances as instances
from sim2act import csv_logic_reuse as logic
from sim2act.api import create_app
from sim2act.db import Store, app_drafts, grants, internal_instance_data, operations, runs
from sim2act.worker import Worker

DIRECT = "label,amount,quantity\nfresh-A,-4.5,20\nfresh-B,12,30\nfresh-C,1.25,40\n"
FREE = "label,units,net\nnew-A,2,-4.5\nnew-B,7,12\nnew-C,4,1.25\n"


def register(env, content):
    client, pid = env[2], env[5]
    r = client.post(f"/api/projects/{pid}/resources", json=dict(name="independent.csv", format="csv", content=content))
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    r = client.post(f"/api/projects/{pid}/apps/csv-preview", json=dict(name="Independent target", goal="New CSV", resource_id=rid))
    assert r.status_code == 201, r.text
    return r.json()["id"], rid


def binding(env, aid, rid, rel=None, obj=None, column="quantity", key="target-anchor"):
    app = env[2].get(f"/api/apps/{aid}").json()
    anchor = env[2].post(f"/api/projects/{env[5]}/apps/{aid}/delivery-graph/derive", json=dict(
        expected_candidate_fingerprint=app["fingerprint"], request_key=key))
    assert anchor.status_code == 201, anchor.text
    body = dict(target_app_id=aid, expected_candidate_fingerprint=app["fingerprint"],
        expected_graph_fingerprint=anchor.json()["graph_fingerprint"], expected_resource_id=rid,
        expected_source_hash=app["candidate"]["source_hash"], column=column, request_key="target-binding")
    body["expected_logic_fingerprint" if obj else "expected_release_fingerprint"] = (obj or rel)["fingerprint"]
    return body


def source(env):
    values = project_setup(env)
    with env[0].tx() as c:
        ids = c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == env[5])).scalars().all()
    for aid in ids:
        if aid in values[2:5]:
            continue
        app = env[2].get(f"/api/apps/{aid}").json()
        r = env[2].post(f"/api/projects/{env[5]}/apps/{aid}/delivery-graph/derive", json=dict(
            expected_candidate_fingerprint=app["fingerprint"], request_key="before-group-" + aid))
        assert r.status_code == 201, r.text
    r = env[2].post(values[0], json=values[1])
    assert r.status_code == 201, r.text
    confirm = dict(expected_patch_fingerprint=r.json()["patch_fingerprint"],
        consent="CONFIRM_EXACT_FINITE_PROJECT_COLUMN_PATCH", request_key="project-binding")
    base = values[0] + "/project-binding"
    r = env[2].post(base + "/runs", json=confirm)
    assert r.status_code == 202, r.text
    project_work(env, r.json())
    r = env[2].post(base + "/finalize", json=confirm)
    assert r.status_code == 201, r.text
    r = env[2].post(base + "/internal-versions", json=dict(
        expected_receipt_fingerprint=r.json()["receipt_fingerprint"], request_key="project-binding"))
    assert r.status_code == 201, r.text
    r = env[2].post(base + "/internal-versions/commit", json=dict(
        expected_preview_fingerprint=r.json()["preview_fingerprint"],
        consent="CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS", request_key="project-binding"))
    assert r.status_code == 201, r.text
    group = r.json()
    entry = next(e for e in group["entries"] if e["app_id"] == values[2])
    r = env[2].get(f"/api/internal/releases/{entry['release_id']}")
    assert r.status_code == 200, r.text
    return r.json(), values[5], group


def setup(env, free=False, content=None):
    if free:
        rel, old_rid, group = source(env)
        obj, _ = authorize(env, rel)
        aid, rid = register(env, content or FREE)
    else:
        aid, rid = register(env, content or DIRECT)
        rel, old_rid, group = source(env)
        obj = None
    body = binding(env, aid, rid, rel, obj, "net" if free else "quantity")
    path = f"/api/internal/csv-logics/{obj['id']}/material-plans" if free else f"/api/internal/releases/{rel['id']}/csv-material-plans"
    return rel, old_rid, group, obj, body, path


def accept(env, path, body, key="target-run"):
    r = env[2].post(path, json=body)
    assert r.status_code == 201, r.text
    value = r.json()
    plan = value["plan"]
    url = f"/api/projects/{env[5]}/apps/{body['target_app_id']}/csv-dag/{plan['request_key']}/runs"
    confirm = dict(expected_plan_fingerprint=plan["plan_fingerprint"], consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key=key)
    r = env[2].post(url, json=confirm)
    assert r.status_code == 202, r.text
    return value, r.json(), url, confirm


def work(env, accepted):
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert job and job["id"] == accepted["run_id"]
    w.process(job)
    return job


@pytest.mark.parametrize("free", [False, True])
def test_modified_version_new_bytes_or_data_free_deleted_source_cold_default_and_unseen(env, tmp_path, free):
    rel, old_rid, group, obj, body, path = setup(env, free)
    if free:
        public = json.dumps(obj)
        for forbidden in ("amount", "quantity", "column_overlay", "default_column", old_rid,
                          rel["snapshot"]["execution_source"]["source_hash"], rel["id"], rel["snapshot"]["execution_source"]["run_id"]):
            assert forbidden not in public
        assert obj["recipe"] == logic.canonical(instances.FIXED_REPORT_VERSION)
        retire_old(env, old_rid)
        assert env[2].get(f"/api/internal/releases/{rel['id']}").status_code != 200
        body = binding(env, body["target_app_id"], body["expected_resource_id"], rel, obj, "net", key="retired-target" )
    before = snapshot(env)
    value, accepted, url, confirm = accept(env, path, body)
    assert value["plan"]["input"] == {"aggregate_column": body["column"]}
    assert env[2].post(path, json=body).json()["plan"]["plan_fingerprint"] == value["plan"]["plan_fingerprint"]
    assert env[2].post(url, json=confirm).json()["run_id"] == accepted["run_id"]
    unchanged = snapshot(env)
    r = env[2].post(path, json={**body, "column": "units" if free else "amount"})
    assert r.status_code in (400, 409), r.text
    assert snapshot(env) == unchanged
    job = work(env, accepted)
    r = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert r.status_code == 200, r.text
    proof = r.json()
    actual = proof["result"]["output_by_step"]["report"]
    content = FREE if free else DIRECT
    oracle = sum((Fraction(row[body["column"]]) for row in csv.DictReader(io.StringIO(content))), Fraction())
    assert Fraction(actual["sum"]) == oracle and actual["count"] == 3
    assert actual["sum"] == ("8.75" if free else "90")
    assert actual["resource_id"] == body["expected_resource_id"] != old_rid
    assert proof["status"] == "SUCCEEDED" and len(proof["steps"]) == 3
    with env[0].tx() as c:
        ops = [dict(v) for v in c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings()]
        assert len(ops) == 3 and all(old_rid not in json.dumps(v) for v in ops)
        frozen = env[0].frozen_contract(c, dag.row(c, env[3], job["id"]))
        assert [v.resource_id for v in frozen.resources] == [body["expected_resource_id"]]
    a = env[2].post(f"/api/csv-dag/runs/{job['id']}/release-approvals", json=dict(
        expected_plan_fingerprint=value["plan"]["plan_fingerprint"], request_key="new-release"))
    assert a.status_code == 201, a.text
    r = env[2].post(f"/api/internal/approvals/{a.json()['id']}/commit", json=dict(fingerprint=a.json()["fingerprint"]))
    assert r.status_code == 200, r.text
    new = r.json()
    assert new["snapshot"]["execution_source"]["version"] == instances.REPORT_VERSION
    assert new["snapshot"]["execution_source"]["default_column"] == body["column"]
    i = create(env, new)
    cold_store = Store(env[1].database_url, test_only=True)
    cold = TestClient(create_app(cold_store, env[1]))
    cold.headers["Authorization"] = "Bearer synthetic-test-A"
    try:
        default = cold.get(f"/api/internal/releases/{new['id']}")
        assert default.status_code == 200, default.text
        assert default.json()["snapshot"]["execution_source"]["default_column"] == body["column"]
        for column in (body["column"], "units" if free else "amount"):
            r = cold.post(f"/api/internal/instances/{i['id']}/runs", json=dict(
                expected_revision=i["revision"], expected_release_fingerprint=new["fingerprint"], input={"column": column}, request_key="cold-" + column))
            assert r.status_code == 202, r.text
            work(env, r.json())
        detail = cold.get(f"/api/internal/instances/{i['id']}")
        assert detail.status_code == 200, detail.text
        got = detail.json()
        assert got["data_version"] == 2 and len({v["run_id"] for v in got["runs"]}) == 2
        assert {v["data"]["result"]["sum"] for v in got["data"]} == ({"8.75", "13"} if free else {"90", "8.75"})
        invalid = cold.post(f"/api/internal/instances/{i['id']}/runs", json=dict(expected_revision=i["revision"],
            expected_release_fingerprint=new["fingerprint"], input={"column": "missing"}, request_key="bad-input"))
        assert invalid.status_code == 409
        assert cold.get(f"/api/internal/instances/{i['id']}").json() == got
        (tmp_path / "actual-proof.json").write_text(json.dumps(dict(source=rel, target_plan=value, target_proof=proof, target_release=new, cold_instance=got, logic=obj), indent=2))
    finally:
        cold.close()
        cold_store.engine.dispose()
    after = snapshot(env)
    for table in ("resources", "principals", "grants", "app_drafts", "delivery_graph_locks"):
        if table in before:
            assert before[table] == after[table], table
    for table in ("internal_releases", "internal_instances", "internal_instance_data"):
        assert all(row in after[table] for row in before[table]), table
    assert rel["snapshot"]["execution_source"]["default_column"] == "quantity"
    assert len(group["entries"]) == 2


@pytest.mark.parametrize("content", ["label,amount\nA,1\n", "label,amount,quantity\nA,1,broken\n", "label,amount,quantity\nA,1,NaN\n"])
def test_direct_missing_or_bad_approved_column_no_fallback_zero_write(env, content):
    rel, _, _, _, body, path = setup(env, content=content)
    before = snapshot(env)
    options = env[2].get(f"/api/internal/releases/{rel['id']}/csv-materials")
    assert options.status_code == 200, options.text
    assert not any(t["target_app_id"] == body["target_app_id"] for t in options.json()["items"])
    assert env[2].post(path, json=body).status_code == 400
    assert snapshot(env) == before


@pytest.mark.parametrize("free", [False, True])
def test_exact_input_budget_identity_current_target_grant_zero_write(env, free):
    rel, _, _, obj, body, path = setup(env, free)
    for patch in ({"column": "missing"}, {"expected_source_hash": "0" * 64}, {"expected_graph_fingerprint": "0" * 64}, {"expected_candidate_fingerprint": "0" * 64}):
        before = snapshot(env)
        assert env[2].post(path, json={**body, **patch}).status_code in (400, 409)
        assert snapshot(env) == before
    old = env[1].max_tools
    object.__setattr__(env[1], "max_tools", old - 1)
    before = snapshot(env)
    # API freezes platform limits at construction; use an actual tightened restart.
    tightened = TestClient(create_app(env[0], env[1]))
    tightened.headers["Authorization"] = "Bearer synthetic-test-A"
    try:
        assert tightened.post(path, json=body).status_code in (400, 409)
    finally:
        tightened.close()
    assert snapshot(env) == before
    object.__setattr__(env[1], "max_tools", old)
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    before = snapshot(env)
    assert env[2].post(path, json=body).status_code == 403
    assert snapshot(env) == before
    env[2].headers["Authorization"] = "Bearer synthetic-test-A"
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == body["expected_resource_id"]).values(revoked=True))
    before = snapshot(env)
    assert env[2].post(path, json=body).status_code in (403, 409)
    assert snapshot(env) == before
    assert rel and (obj is not None) == free


@pytest.mark.parametrize("attack", ["cancel", "grant", "late", "logic-revoke"])
def test_real_worker_stop_or_late_no_false_success_or_typed_write(env, monkeypatch, attack):
    _, _, _, obj, body, path = setup(env, free=True)
    _, accepted, _, _ = accept(env, path, body)
    w = Worker(env[0], env[1], NoModel())
    job = env[0].claim(w.id, env[1].lease_seconds)
    assert job["id"] == accepted["run_id"]
    if attack == "cancel":
        r = env[2].post(f"/api/runs/{job['id']}/commands", json=dict(command="cancel", version=job["version"]))
        assert r.status_code == 200, r.text
    elif attack == "grant":
        assert dag.advance(w, job)
        with env[0].tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == body["expected_resource_id"]).values(revoked=True))
    elif attack == "logic-revoke":
        r = env[2].post(f"/api/internal/csv-logics/{obj['id']}/revoke", json=dict(
            expected_logic_fingerprint=obj["fingerprint"], consent="REVOKE_DATA_FREE_CSV_LOGIC", request_key="cancel-logic"))
        assert r.status_code == 200, r.text
    else:
        original = dag.aggregate_csv_content
        def delayed(*args, **kwargs):
            value = original(*args, **kwargs)
            monkeypatch.setattr(dag.time, "time", lambda: job["created_at"] + env[1].run_seconds + 1)
            return value
        monkeypatch.setattr(dag, "aggregate_csv_content", delayed)
    w.process(job)
    with env[0].tx() as c:
        saved = c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one()
        assert saved["status"] != "SUCCEEDED" and saved["result"] is None
        assert not c.execute(select(internal_instance_data)).first()
        assert not c.execute(select(operations).where(operations.c.run_id == job["id"], operations.c.tool_ref == "intern.csv_report.v1")).first()
