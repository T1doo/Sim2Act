"""Actual three-operation DAG reuse, node-keyed inputs and independent arithmetic."""

import copy
import csv
import hashlib
import io
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create, work
from test_delivery_graph_apps import path, snapshot
from test_internal_lifecycle import limits

from sim2act import csv_dag as dag
from sim2act import csv_dag_instances as instances
from sim2act.api import create_app
from sim2act.db import (
    Store,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_releases,
    internal_run_bindings,
    operations,
    resources,
    runs,
)
from sim2act.worker import Worker

INTEGER = "item,amount,quantity\nA,10,7\nB,20,8\n"
DECIMAL = "item,amount,quantity\nA,0.1,-2.125\nB,0.2,4.375\n"
STEPS = ["total_a", "total_b"]


def composition():
    return dict(version="csv.composition.v1", nodes=[
        dict(step_id="read", action="resource.read", depends_on=[],
             inputs=dict(resource_id=dict(source="data", ref="source", field="resource_id"))),
        *[dict(step_id=sid, action="data.aggregate_csv", column=col, depends_on=["read"],
               inputs=dict(resource_id=dict(source="step", ref="read", field="resource_id"),
                           column=dict(source="input", field=sid + "_column")))
          for sid, col in zip(STEPS, ["amount", "quantity"], strict=True)],
    ])


def setup(env, content=INTEGER):
    client, pid = env[2], env[5]
    reply = client.post(f"/api/projects/{pid}/resources", json=dict(
        name="dual-source.csv", format="csv", content=content))
    assert reply.status_code == 201, reply.text
    rid = reply.json()["id"]
    reply = client.post(f"/api/projects/{pid}/apps/csv-preview", json=dict(
        name="two sums", goal="two bounded sums", resource_id=rid))
    assert reply.status_code == 201, reply.text
    aid = reply.json()["id"]
    draft = client.get(f"/api/apps/{aid}").json()
    reply = client.post(path(env, aid) + "/derive", json=dict(
        expected_candidate_fingerprint=draft["fingerprint"], request_key="baseline"))
    assert reply.status_code == 201, reply.text
    anchor = reply.json()
    return aid, rid, anchor


def source(env, content=INTEGER):
    aid, rid, anchor = setup(env, content)
    base = f"/api/projects/{env[5]}/apps/{aid}/csv-dag"
    reply = env[2].post(base, json=dict(expected_candidate_fingerprint=anchor["candidate_fingerprint"],
        expected_graph_fingerprint=anchor["graph_fingerprint"], column="amount",
        request_key="dual", composition=composition()))
    assert reply.status_code == 201, reply.text
    plan = reply.json()
    reply = env[2].post(base + "/dual/runs", json=dict(
        expected_plan_fingerprint=plan["plan_fingerprint"], consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="source"))
    assert reply.status_code == 202, reply.text
    job = work(env, reply.json())
    assert dag.inspect_job(env[0], env[3], job["id"], limits(env))["status"] == "SUCCEEDED"
    return aid, rid, plan, job


def release(env, content=INTEGER):
    aid, rid, plan, job = source(env, content)
    reply = env[2].post(f"/api/csv-dag/runs/{job['id']}/release-approvals", json=dict(
        expected_plan_fingerprint=plan["plan_fingerprint"], request_key="prepare-dual"))
    assert reply.status_code == 201, reply.text
    a = reply.json()
    assert env[2].get(f"/api/internal/approvals/{a['id']}").status_code == 200
    reply = env[2].post(f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"]))
    assert reply.status_code == 200, reply.text
    return aid, rid, plan, job, reply.json()


def enqueue(env, i, rel, columns=None, key="dual-instance"):
    body = dict(expected_revision=i["revision"], expected_release_fingerprint=rel["fingerprint"],
        input={"columns": columns or dict(total_a="quantity", total_b="amount")}, request_key=key)
    reply = env[2].post(f"/api/internal/instances/{i['id']}/runs", json=body)
    assert reply.status_code == 202, reply.text
    return reply.json(), body


def expected(content, column, rid):
    rows = list(csv.DictReader(io.StringIO(content)))
    return dict(resource_id=rid, column=column, count=len(rows),
        source_hash=hashlib.sha256(content.encode()).hexdigest(),
        rational=sum((Fraction(row[column]) for row in rows), Fraction()))


def check_output(output, content, rid, columns):
    assert set(output) == set(STEPS)
    for sid, column in columns.items():
        wanted = expected(content, column, rid)
        rational = wanted.pop("rational")
        actual = dict(output[sid])
        assert Fraction(actual.pop("sum")) == rational
        assert actual == wanted


@pytest.mark.parametrize("content", [INTEGER, DECIMAL])
def test_actual_worker_independent_instances_swapped_columns_cold_store_and_idempotency(env, content):
    aid, rid, plan, original, rel = release(env, content)
    e = rel["snapshot"]["execution_source"]
    assert e["version"] == instances.TWO_SUM_VERSION and e["aggregate_steps"] == STEPS
    assert all(e["aggregate_nodes"][sid]["columns"] == ["amount", "quantity"] for sid in STEPS)
    assert all(e["aggregate_nodes"][sid]["limits"]["max_tools"] == 1 for sid in STEPS)
    i, other = create(env, rel), create(env, rel, "other-instance")
    run_ids = []
    for instance, columns, key in [
        (i, dict(total_a="quantity", total_b="amount"), "swap"),
        (i, dict(total_a="amount", total_b="quantity"), "original-columns"),
        (other, dict(total_a="quantity", total_b="quantity"), "swap"),
    ]:
        accepted, body = enqueue(env, instance, rel, columns, key)
        run_ids.append(accepted["run_id"])
        url = f"/api/internal/instances/{instance['id']}/runs"
        assert env[2].post(url, json=body).json()["run_id"] == accepted["run_id"]
        before = fingerprint(snapshot(env))
        changed = copy.deepcopy(body)
        changed["input"]["columns"]["total_b"] = "amount" if columns["total_b"] == "quantity" else "quantity"
        assert env[2].post(url, json=changed).status_code == 409
        assert fingerprint(snapshot(env)) == before
        work(env, accepted)
        result = instances.inspect_job(env[0], env[3], accepted["run_id"], limits(env))
        assert result["status"] == "SUCCEEDED" and len(result["proof"]["steps"]) == 3
        check_output(result["output"], content, rid, columns)
        with env[0].engine.connect() as c:
            args = c.execute(select(operations.c.receipt).where(operations.c.run_id == accepted["run_id"])).scalars().all()
            assert len(args) == 3
    assert len(set(run_ids + [original["id"]])) == 4
    frozen = fingerprint(snapshot(env))
    cold = Store(env[1].database_url, test_only=True)
    try:
        client = TestClient(create_app(cold, env[1]))
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        detail = client.get(f"/api/internal/instances/{i['id']}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["data_version"] == 2
        for record in detail.json()["data"]:
            assert record["data"]["result"] == next(r["output"] for r in detail.json()["runs"] if r["app_run_id"] == record["run_id"])
        assert len(client.get(f"/api/internal/apps/{aid}/dag-instances").json()["items"]) == 2
        client.close()
    finally:
        cold.engine.dispose()
    assert fingerprint(snapshot(env)) == frozen


@pytest.mark.parametrize("value", [
    {}, {"column": "amount"}, {"columns": {}}, {"columns": {"total_a": "amount"}},
    {"columns": {"total_a": "amount", "total_b": "quantity", "extra": "amount"}},
    {"columns": {"total_a": "item", "total_b": "quantity"}},
    {"columns": {"total_a": True, "total_b": "quantity"}},
    {"columns": {"total_a": {"column": "amount"}, "total_b": "quantity"}},
    {"columns": {"total_a": "amount", "total_b": "quantity"}, "resource_id": "other"},
    {"columns": {"total_a": "amount", "total_b": "quantity"}, "composition": {}},
])
def test_input_closed_and_rejection_atomic(env, value):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    before = fingerprint(snapshot(env))
    reply = env[2].post(f"/api/internal/instances/{i['id']}/runs", json=dict(
        expected_revision=1, expected_release_fingerprint=rel["fingerprint"], input=value, request_key="invalid"))
    assert reply.status_code == 409, reply.text
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize("attack", ["grant", "source", "binding-input", "missing-sink", "wrong-sum", "budget"])
def test_failure_does_not_append_partial_or_cached_result(env, attack):
    _, rid, _, _, rel = release(env)
    i = create(env, rel)
    accepted, _ = enqueue(env, i, rel)
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert dag.advance(worker, job)
    if attack in {"missing-sink", "wrong-sum"}:
        assert dag.advance(worker, job) and dag.advance(worker, job)
    with env[0].tx() as c:
        if attack == "grant":
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
        elif attack == "source":
            c.execute(update(resources).where(resources.c.id == rid).values(content="changed", hash=hashlib.sha256(b"changed").hexdigest()))
        elif attack == "binding-input":
            b = c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"])).mappings().one()
            s = copy.deepcopy(b["snapshot"])
            s["input"]["columns"]["total_b"] = "quantity"
            c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"]).values(snapshot=s, fingerprint=fingerprint(s)))
        elif attack == "budget":
            worker.s = type(env[1])(**{**vars(env[1]), "max_tools": 2})
        else:
            row = c.execute(select(operations).where(operations.c.run_id == job["id"],
                operations.c.receipt["step_id"].as_string() == "total_b")).mappings().one()
            if attack == "missing-sink":
                c.execute(delete(operations).where(operations.c.id == row["id"]))
            else:
                receipt = copy.deepcopy(row["receipt"])
                receipt["data"]["sum"] = "999"
                c.execute(update(operations).where(operations.c.id == row["id"]).values(receipt=receipt))
    worker.process(job)
    with env[0].engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one()
        assert saved["status"] in {"FAILED", "WAITING_RESOURCE"} and saved["result"] is None
        assert not c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])).first()


def test_cancel_and_cross_owner_project_and_single_input_reuse_gates(env):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    a, body = enqueue(env, i, rel)
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].post(f"/api/internal/instances/{i['id']}/runs", json={**body, "request_key": "other"}).status_code == 403
    assert env[2].get(f"/api/internal/instances/{i['id']}").status_code == 403
    env[2].headers["Authorization"] = "Bearer synthetic-test-A"
    reply = env[2].post(f"/api/internal/instances/{i['id']}/runs/{a['run_id']}/commands", json=dict(command="cancel", version=a["version"]))
    assert reply.status_code == 200, reply.text
    detail = env[2].get(f"/api/internal/instances/{i['id']}")
    assert detail.status_code == 200 and detail.json()["data_version"] == 0
    assert detail.json()["runs"][0]["status"] == "CANCELLED"
    before = fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/releases/{rel['id']}/csv-materials").status_code == 400
    assert fingerprint(snapshot(env)) == before


def test_other_project_run_cannot_be_read_under_this_instance_and_no_new_grants(env):
    from sim2act.db import principals

    _, _, _, _, rel = release(env)
    i = create(env, rel)
    before = snapshot(env)
    a, _ = enqueue(env, i, rel)
    work(env, a)
    after = snapshot(env)
    assert before[grants.name] == after[grants.name]
    assert before[principals.name] == after[principals.name]
    pid = env[2].post("/api/projects", json={"name": "other project"}).json()["id"]
    other_env = (*env[:5], pid, env[6])
    _, _, _, _, other_rel = release(other_env)
    other_i = create(other_env, other_rel)
    other_a, _ = enqueue(other_env, other_i, other_rel)
    reply = env[2].get(f"/api/internal/instances/{i['id']}/runs/{other_a['run_id']}")
    assert reply.status_code == 403, reply.text
    assert env[2].get(f"/api/internal/instances/{i['id']}").json()["data_version"] == 1


@pytest.mark.parametrize("field", ["aggregate_steps", "aggregate_nodes", "columns", "limits", "version"])
def test_frozen_execution_contract_tamper_rejected(env, field):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    with env[0].tx() as c:
        bad = copy.deepcopy(rel["snapshot"])
        e = bad["execution_source"]
        if field == "aggregate_steps":
            e[field].reverse()
        elif field == "aggregate_nodes":
            e[field]["total_b"]["depends_on"] = ["total_a"]
        elif field == "columns":
            e["aggregate_nodes"]["total_b"]["columns"].append("item")
        elif field == "limits":
            e["aggregate_nodes"]["total_b"]["limits"]["max_tools"] = 4
        else:
            e[field] = instances.REPORT_VERSION
        c.execute(update(internal_releases).where(internal_releases.c.id == rel["id"]).values(snapshot=bad, fingerprint=fingerprint(bad)))
    before = fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/releases/{rel['id']}").status_code == 409
    reply = env[2].post(f"/api/internal/instances/{i['id']}/runs", json=dict(
        expected_revision=1, expected_release_fingerprint=fingerprint(bad),
        input={"columns": dict(total_a="amount", total_b="quantity")}, request_key="tampered"))
    assert reply.status_code == 409
    assert fingerprint(snapshot(env)) == before


def test_complete_typed_result_tamper_rejected_even_with_updated_hash(env):
    _, _, _, _, rel = release(env)
    i = create(env, rel)
    a, _ = enqueue(env, i, rel)
    work(env, a)
    with env[0].tx() as c:
        ar = c.execute(select(internal_app_runs).where(internal_app_runs.c.id == a["app_run_id"])).mappings().one()
        output = copy.deepcopy(ar["output"])
        output["total_b"]["sum"] = "123"
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id == ar["id"]).values(output=output))
        c.execute(update(internal_instance_data).where(internal_instance_data.c.run_id == ar["id"]).values(data={"result": output}, fingerprint=fingerprint({"result": output})))
    assert env[2].get(f"/api/internal/instances/{i['id']}").status_code == 409
