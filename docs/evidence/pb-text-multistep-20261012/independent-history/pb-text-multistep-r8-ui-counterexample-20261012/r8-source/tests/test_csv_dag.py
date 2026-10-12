"""Actual fixed DAG runs; frozen independent answers, no provider or business effects."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select, update

from sim2act import csv_dag as dag
from sim2act.db import Store, attempts, fingerprint, grants, operations, resources, runs
from sim2act.errors import DomainError
from sim2act.preflight import preflight
from sim2act.tools import definitions
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
    content = CSV.read_text(encoding="utf-8")
    rid, base, plan, body, worker, job = setup(env, content)
    worker.process(job)
    response = env[2].get(f"/api/runs/{job['id']}")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "SUCCEEDED"
    assert result["result"]["output"] == dict(resource_id=rid, column="quantity", count=2, sum="15",
        source_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(), text="列 quantity；行数 2；合计 15")
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
    metadata = env[2].get(f"/api/csv-dag/runs/{job['id']}/status")
    assert metadata.status_code == 200 and metadata.json()["result"] is None
    assert metadata.json()["steps"] == [] and metadata.json()["proof_status"] == "NOT_VALIDATED"
    stopped = env[2].post(f"/api/runs/{job['id']}/commands", json=dict(command="cancel", version=saved["version"]))
    assert stopped.status_code == 200 and stopped.json()["status"] == "CANCELLED"


class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError("Fixed CSV DAG must never call any model")

    def complete(self, *args, **kwargs):
        raise AssertionError("Fixed CSV DAG must never call any model")


@pytest.mark.parametrize("count", [1, 2, 3])
def test_cold_worker_lease_recovery_retains_committed_receipt_ids(env, count):
    _, _, _, _, worker, job = setup(env)
    for _ in range(count):
        assert dag.advance(worker, job)
    with env[0].tx() as c:
        original = {r["call_id"]: r["id"] for r in c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings()}
        c.execute(update(runs).where(runs.c.id == job["id"]).values(lease_until=0))
    cold = Store(env[1].database_url, test_only=True)
    if not cold.sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        recovered = Worker(cold, env[1], NoModel())
        claimed = cold.claim(recovered.id, env[1].lease_seconds)
        assert claimed["id"] == job["id"] and claimed["fence"] > job["fence"]
        with pytest.raises(DomainError):
            dag.advance(worker, job)
        recovered.process(claimed)
        result = cold.inspect(env[3], job["id"])
        assert result["status"] == "SUCCEEDED"
        assert all(next(r for r in result["steps"] if r["step_id"] == s)["operation_id"] == oid for s, oid in original.items())
        assert step_ids(env, job) == set(dag.STEPS)
    finally:
        cold.engine.dispose()


def test_uncommitted_step_rolls_back_and_retries_without_duplicate_operation(env, monkeypatch):
    _, _, _, _, worker, job = setup(env)
    event = env[0].event

    def crash(c, rid, kind, data=None):
        if kind == "CSV_DAG_STEP_VERIFIED":
            raise RuntimeError("owned crash before local receipt commit")
        return event(c, rid, kind, data)

    with monkeypatch.context() as m:
        m.setattr(env[0], "event", crash)
        with pytest.raises(RuntimeError):
            dag.advance(worker, job)
    assert step_ids(env, job) == set() and read_row(env, job)["context"]["tools"] == 0
    Worker(env[0], env[1], NoModel()).process(job)
    assert read_row(env, job)["status"] == "SUCCEEDED" and step_ids(env, job) == set(dag.STEPS)


def test_pause_at_step_boundary_and_explicit_resume_preserves_receipt(env):
    _, _, _, _, worker, job = setup(env)
    dag.advance(worker, job)
    saved = read_row(env, job)
    assert env[0].command(env[3], job["id"], "pause", saved["version"]) == "PAUSE_REQUESTED"
    worker.process(job)
    saved = read_row(env, job)
    assert saved["status"] == "PAUSED" and step_ids(env, job) == {"preview"}
    assert env[0].command(env[3], job["id"], "resume", saved["version"]) == "QUEUED"
    next_worker = Worker(env[0], env[1], NoModel())
    next_worker.process(env[0].claim(next_worker.id, env[1].lease_seconds))
    assert read_row(env, job)["status"] == "SUCCEEDED"


@pytest.mark.parametrize("column,content,total", [
    ("amount", CSV.read_text(), "30"),
    ("amount", "item,amount,quantity\nC,1.25,2\nD,2.75,3\n", "4.00"),
    ("quantity", "item,amount,quantity\nC,1.25,2\nD,2.75,3\n", "5"),
    ("amount", "item,amount,quantity\nE,-2.5,0\nF,2,0\n", "-0.5"),
    ("amount", "item,amount,quantity\nG,0.1,1\nH,0.2,2\n", "0.3"),
])
def test_frozen_independent_arithmetic_cases(env, column, content, total):
    _, _, _, _, worker, job = setup(env, content, column)
    worker.model = NoModel()
    worker.process(job)
    result = env[0].inspect(env[3], job["id"])
    assert result["result"]["output"]["sum"] == total
    assert result["result"]["output"]["text"] == f"列 {column}；行数 2；合计 {total}"


@pytest.mark.parametrize("mutation", ["cycle", "hidden_edge", "type", "read_permission", "write", "model_tool"])
def test_static_contract_rejects_bad_edges_and_preserves_other_permission_checks(env, mutation):
    _, _, plan, _, _, _ = setup(env)
    draft = copy.deepcopy(plan["definition"])
    if mutation == "cycle":
        draft["manifest"]["workflow"][0]["depends_on"] = ["report"]
    elif mutation == "hidden_edge":
        draft["manifest"]["workflow"][1]["depends_on"] = []
    elif mutation == "type":
        draft["actions"][2]["input_schema"]["properties"]["count"] = {"type": "number"}
    elif mutation == "read_permission":
        draft["actions"][1]["permission_requirements"] = []
    elif mutation == "write":
        draft["actions"][2]["effect"] = "project_write"
    else:
        draft["actions"][2]["allowed_tool_refs"] = ["resource.read"]
    with pytest.raises(DomainError):
        preflight(json.dumps(draft["manifest"]), draft["actions"], dag.Limits(**plan["definition"]["manifest"]["runtime_limits"]))
    assert "intern.csv_report.v1" not in {d["function"]["name"] for d in definitions()}


@pytest.mark.parametrize("mutation", ["fingerprint", "consent", "key", "definition", "run_key"])
def test_closed_api_confirmation_and_request_key_conflicts(env, mutation):
    _, base, plan, body, _, job = setup(env)
    if mutation == "definition":
        reply = env[2].post(base, json=dict(expected_candidate_fingerprint=plan["candidate_fingerprint"], expected_graph_fingerprint=plan["graph_fingerprint"], request_key="evil", column="amount", definition=plan["definition"]))
    else:
        changed = dict(body)
        if mutation == "fingerprint":
            changed["expected_plan_fingerprint"] = "0" * 64
        elif mutation == "consent":
            changed["consent"] = "approve anything"
        elif mutation == "key":
            changed["request_key"] = "bad/key\0"
        else:
            changed["expected_plan_fingerprint"] = "f" * 64
        reply = env[2].post(base + "/plan/runs", json=changed)
    assert reply.status_code in {400, 409, 422}
    assert step_ids(env, job) == set()


def test_coordinated_receipt_and_output_resigning_cannot_replace_actual_sum(env):
    _, _, _, _, worker, job = setup(env)
    worker.process(job)
    with env[0].tx() as c:
        op = c.execute(select(operations).where(operations.c.run_id == job["id"], operations.c.call_id == "aggregate")).mappings().one()
        receipt = copy.deepcopy(op["receipt"])
        receipt["data"]["sum"] = "999"
        receipt["output_fingerprint"] = fingerprint(receipt["data"])
        c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
    reply = env[2].get(f"/api/runs/{job['id']}")
    assert reply.status_code == 400 and reply.json()["error"]["code"] == "VERIFICATION_FAILED"


def test_failed_report_preserves_upstream_receipts_and_is_not_success(env, monkeypatch):
    _, _, _, _, worker, job = setup(env)
    dag.advance(worker, job)
    dag.advance(worker, job)
    with monkeypatch.context() as m:
        def fail(value):
            raise DomainError("VERIFICATION_FAILED", "owned formatter fault")
        m.setattr(dag.report, "render", fail)
        worker.process(job)
    assert read_row(env, job)["status"] == "FAILED" and step_ids(env, job) == {"preview", "aggregate"}
    result = env[2].get(f"/api/runs/{job['id']}").json()
    assert result["result"] is None and result["pending_steps"] == ["report"]


def test_completed_result_becomes_inaccessible_after_revoke_and_foreign_user_denied(env):
    rid, _, _, _, worker, job = setup(env)
    worker.process(job)
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
    assert env[2].get(f"/api/runs/{job['id']}").status_code == 403
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}/status").status_code == 403
