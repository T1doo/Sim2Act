"""Actual fixed DAG runs; frozen independent answers, no provider or business effects."""

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import select, update

from sim2act import csv_dag as dag
from sim2act.db import attempts, grants, operations, resources, runs
from sim2act.worker import Worker

CSV = Path(__file__).with_name("fixtures") / "column-binding.csv"


def setup(env, content=None, column="quantity"):
    store, settings, client, user, _, pid, _ = env
    rid = client.post(f"/api/projects/{pid}/resources", json=dict(name="dag.csv", format="csv", content=content or CSV.read_text())).json()["id"]
    app = client.post(f"/api/projects/{pid}/apps/csv-preview", json=dict(name="DAG source", goal="Engineering only", resource_id=rid)).json()
    app = client.get(f"/api/apps/{app['id']}").json()
    graph = client.post(f"/api/projects/{pid}/apps/{app['id']}/delivery-graph/derive", json=dict(expected_candidate_fingerprint=app["fingerprint"], request_key="dag-source")).json()
    base = f"/api/projects/{pid}/apps/{app['id']}/csv-dag"
    body = dict(expected_candidate_fingerprint=app["fingerprint"], expected_graph_fingerprint=graph["graph_fingerprint"], column=column, request_key="plan")
    response = client.post(base, json=body)
    assert response.status_code == 201, response.text
    plan = response.json()
    confirmation = dict(expected_plan_fingerprint=plan["plan_fingerprint"], consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="run")
    response = client.post(base + "/plan/runs", json=confirmation)
    assert response.status_code == 202, response.text
    accepted = response.json()
    worker = Worker(store, settings)
    job = store.claim(worker.id, settings.lease_seconds)
    assert job["id"] == accepted["run_id"]
    return rid, base, plan, confirmation, worker, job


def read_row(env, job):
    with env[0].engine.connect() as c:
        return dict(c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one())


def step_ids(env, job):
    with env[0].engine.connect() as c:
        return set(c.execute(select(operations.c.call_id).where(operations.c.run_id == job["id"])).scalars())


def test_three_actual_receipts_exact_report_and_old_request_recovery(env):
    rid, base, plan, body, worker, job = setup(env)
    worker.process(job)
    response = env[2].get(f"/api/runs/{job['id']}")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "SUCCEEDED"
    assert result["result"]["output"] == dict(resource_id=rid, column="quantity", count=2, sum="15",
        source_hash=hashlib.sha256(CSV.read_bytes()).hexdigest(), text="列 quantity；行数 2；合计 15")
    assert [r["step_id"] for r in result["steps"]] == ["preview", "aggregate", "report"]
    assert result["steps"][0]["predecessor_receipts"] == []
    assert len(result["steps"][1]["predecessor_receipts"]) == 1
    assert result["steps"][2]["actual_reads"] == []
    assert all(r["artifact_refs"] == [] for r in result["steps"])
    assert result["model_requests"] == result["business_writes"] == 0
    recovered = env[2].post(base + "/plan/runs", json=body)
    assert recovered.status_code == 202 and recovered.json()["cached"]
    assert recovered.json()["run_id"] == job["id"]
    with env[0].engine.connect() as c:
        assert not c.execute(select(attempts.c.id)).first()
    assert step_ids(env, job) == set(dag.STEPS)
    assert plan["model_generated"] is False


@pytest.mark.parametrize("content,column,failed,kept", [
    ("item,amount,amount\nA,10,7\n", "amount", "preview", set()),
    (CSV.read_text(), "missing", "aggregate", {"preview"}),
])
def test_preview_or_sum_failure_blocks_downstream(env, content, column, failed, kept):
    _, _, _, _, worker, job = setup(env, content, column)
    worker.process(job)
    saved = read_row(env, job)
    assert saved["status"] == "FAILED" and saved["result"] is None
    assert step_ids(env, job) == kept
    result = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert result.status_code == 200, result.text
    assert result.json()["pending_steps"][0] == failed


@pytest.mark.parametrize("kind", ["source", "grant"])
def test_invalidation_between_preview_and_sum_preserves_only_preview(env, kind):
    rid, base, _, body, worker, job = setup(env)
    assert dag.advance(worker, job)
    with env[0].tx() as c:
        if kind == "source":
            changed = "item,amount,quantity\nC,10,99\n"
            c.execute(update(resources).where(resources.c.id == rid).values(content=changed, hash=hashlib.sha256(changed.encode()).hexdigest()))
        else:
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
    worker.process(job)
    saved = read_row(env, job)
    assert saved["status"] == "WAITING_RESOURCE" and saved["result"] is None
    assert step_ids(env, job) == {"preview"}
    assert env[2].post(base + "/plan/runs", json=body).status_code in {403, 409}
    assert env[2].post(f"/api/runs/{job['id']}/commands", json=dict(command="resume", version=saved["version"])).status_code in {403, 409}
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {403, 409}
