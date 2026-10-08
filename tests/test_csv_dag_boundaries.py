"""Frozen typed DAG authority, budget, ownership and independent process boundaries."""

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import select, update
from test_csv_dag import NoModel, read_row, setup, step_ids
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits

from sim2act import csv_dag as dag
from sim2act import delivery_graph_apps as graph
from sim2act.db import fingerprint, grants, operations, resources, runs
from sim2act.errors import DomainError


@pytest.mark.parametrize("count", [2, 3])
@pytest.mark.parametrize("kind", ["source", "owner", "runtime"])
def test_source_authority_rechecked_before_report_and_finalization(env, count, kind):
    rid, _, _, _, worker, job = setup(env)
    worker.model = NoModel()
    for _ in range(count):
        assert dag.advance(worker, job)
    old = step_ids(env, job)
    with env[0].tx() as c:
        if kind == "source":
            changed = "item,amount,quantity\nA,10,99\n"
            c.execute(update(resources).where(resources.c.id == rid).values(content=changed, hash=hashlib.sha256(changed.encode()).hexdigest()))
        else:
            principal = env[3] if kind == "owner" else job["runtime_id"]
            c.execute(update(grants).where(grants.c.resource_id == rid, grants.c.principal_id == principal).values(revoked=True))
    worker.process(job)
    assert read_row(env, job)["status"] == "WAITING_RESOURCE"
    assert read_row(env, job)["result"] is None and step_ids(env, job) == old
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {403, 409}


@pytest.mark.parametrize("field,value", [("requests", 1), ("tools", True), ("tools", 3), ("repairs", 1), ("reserved_tokens", 1), ("kind", "OTHER")])
def test_counter_or_dispatch_tampering_never_executes_or_certifies(env, field, value):
    _, _, _, _, worker, job = setup(env)
    with env[0].tx() as c:
        ctx = dict(job["context"])
        ctx[field] = value
        c.execute(update(runs).where(runs.c.id == job["id"]).values(context=ctx))
    worker.model = NoModel()
    worker.process(job)
    assert read_row(env, job)["status"] == "WAITING_RESOURCE" and step_ids(env, job) == set()
    assert env[2].get(f"/api/runs/{job['id']}").status_code == 409


@pytest.mark.parametrize("kind", ["deadline", "lease"])
def test_expired_local_execution_rolls_back_receipt(env, monkeypatch, kind):
    _, _, _, _, worker, job = setup(env)
    real_expected = dag.expected

    def expire(*args):
        value = real_expected(*args)
        with env[0].engine.connect() as c:
            # Value read only; use the clock rather than mutating from a second DB transaction.
            until = c.execute(select(runs.c.lease_until).where(runs.c.id == job["id"])).scalar_one()
        monkeypatch.setattr(dag.time, "time", lambda: until + 1000 if kind == "lease" else job["created_at"] + 1000)
        return value

    monkeypatch.setattr(dag, "expected", expire)
    with pytest.raises(DomainError):
        dag.advance(worker, job)
    assert step_ids(env, job) == set() and read_row(env, job)["context"]["tools"] == 0


@pytest.mark.parametrize("budget", ["max_requests", "max_tools", "max_total_tokens", "run_seconds"])
def test_conservative_three_node_budget_fails_before_plan_write(env, budget):
    _, _, plan, _, _, _ = setup(env)
    aid = plan["app_id"]
    with env[0].tx() as c:
        candidate = graph.load_family(env[0], c, env[3], env[5], aid, limits(env))[0]["candidate"]
    before = snapshot(env)
    with pytest.raises(DomainError, match="Three-node"):
        dag.compile_plan(candidate, "quantity", limits(env).model_copy(update={budget: 2}))
    assert snapshot(env) == before


@pytest.mark.parametrize("key", ["x\0y", "x\r\ny", "x\x7fy", "x\x85y", "x\ud800y"])
@pytest.mark.parametrize("kind", ["plan", "run"])
def test_new_dag_keys_share_control_validator_before_sql_and_framework_encoding(env, key, kind):
    _, base, plan, confirmation, _, _ = setup(env)
    body = dict(expected_candidate_fingerprint=plan["candidate_fingerprint"], expected_graph_fingerprint=plan["graph_fingerprint"], column="quantity", request_key=key) if kind == "plan" else {**confirmation, "request_key": key}
    before = snapshot(env)
    response = env[2].post(base if kind == "plan" else base + "/plan/runs", content=json.dumps(body), headers={"Content-Type": "application/json"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "INVALID_INPUT"
    assert snapshot(env) == before


def test_lock_and_unknown_project_dependencies_prevent_new_plan_and_old_replay(env, monkeypatch):
    _, base, plan, confirmation, _, _ = setup(env)
    real = graph.current

    for kind in ("lock", "unknown"):
        def blocked(*args, kind=kind, **kwargs):
            saved = copy.deepcopy(real(*args, **kwargs))
            if kind == "lock":
                saved["context"]["locked_nodes"] = ["owned-original-node"]
            else:
                saved["graph"]["unknown_dependencies"] = [{"scope": "PROJECT"}]
            return saved
        with monkeypatch.context() as m:
            m.setattr(graph, "current", blocked)
            before = snapshot(env)
            response = env[2].post(base, json=dict(expected_candidate_fingerprint=plan["candidate_fingerprint"], expected_graph_fingerprint=plan["graph_fingerprint"], column="quantity", request_key=kind))
            assert response.status_code == 400 and response.json()["error"]["code"] == ("LOCK_CONFLICT" if kind == "lock" else "UNSUPPORTED_CAPABILITY")
            assert env[2].post(base + "/plan/runs", json=confirmation).status_code == 400
            assert snapshot(env) == before


def test_unchanged_domain_objects_and_full_final_receipt_not_just_sum(env, tmp_path):
    _, base, plan, _, worker, job = setup(env)
    before = snapshot(env)
    worker.model = NoModel()
    worker.process(job)
    after = snapshot(env)
    allowed = {"runs", "operations", "operation_intents", "events"}
    for name in before:
        if name not in allowed:
            assert before[name] == after[name], name
    proof = env[0].inspect(env[3], job["id"])
    history = env[2].get(base).json()
    assert history["items"][0]["plan"] == {k: v for k, v in plan.items() if k != "cached"}
    assert history["items"][0]["runs"][0]["proof_status"] == "NOT_VALIDATED"
    (tmp_path / "dag-proof.json").write_text(json.dumps(dict(plan=plan, job=proof, unchanged_tables=sorted(set(before) - allowed)), indent=2))
    with env[0].tx() as c:
        forged = copy.deepcopy(read_row(env, job)["result"])
        forged["owner_acceptance"] = "ACCEPTED"
        c.execute(update(runs).where(runs.c.id == job["id"]).values(result=forged))
    assert env[2].get(f"/api/runs/{job['id']}").status_code == 400


def test_unknown_operation_blocks_resume_and_generic_reconciliation(env):
    _, _, _, _, worker, job = setup(env)
    dag.advance(worker, job)
    with env[0].tx() as c:
        op = dict(c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings().one())
        c.execute(update(operations).where(operations.c.id == op["id"]).values(status="OUTCOME_UNKNOWN"))
    worker.process(job)
    state = read_row(env, job)
    assert state["status"] == "WAITING_RESOURCE" and step_ids(env, job) == {"preview"}
    with pytest.raises(DomainError) as denied:
        env[0].command(env[3], job["id"], "resume", state["version"])
    assert denied.value.code == "OUTCOME_UNKNOWN"
    with pytest.raises(DomainError) as denied:
        env[0].reconcile_operation(env[3], job["id"], op["id"], state["version"], fingerprint({}), {})
    assert denied.value.code == "UNSUPPORTED_CAPABILITY"


@pytest.mark.parametrize("count", [1, 2, 3])
def test_actual_application_role_child_recovery_after_committed_step(env, runtime_role, tmp_path, count):
    _, _, _, _, _, job = setup(env)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == job["id"]).values(status="QUEUED", lease_until=0))
    root = Path(__file__).parents[1]
    context = dict(PATH=str(Path(sys.executable).parent), PYTHONPATH=str(root / "src"), PYTHONUTF8="1", LIVE="0", SIM2ACT_SYNTHETIC_APP_URL=runtime_role,
                   SIM2ACT_SYNTHETIC_RUN=job["id"], SIM2ACT_SYNTHETIC_DIR=str(tmp_path))
    if os.name == "nt":
        context.update({k: os.environ[k] for k in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP") if k in os.environ})
    def child(steps):
        result = subprocess.run([sys.executable, str(root / "tests/fixtures/csv_dag_worker.py")], cwd=root, env={**context, "SIM2ACT_SYNTHETIC_STEPS": str(steps)}, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
    child(count)
    with env[0].tx() as c:
        committed = {r["call_id"]: r["id"] for r in c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings()}
        c.execute(update(runs).where(runs.c.id == job["id"]).values(lease_until=0))
    child(0)
    proof = env[0].inspect(env[3], job["id"])
    assert proof["status"] == "SUCCEEDED" and len(proof["steps"]) == 3
    assert all(next(r for r in proof["steps"] if r["step_id"] == s)["operation_id"] == oid for s, oid in committed.items())
    assert proof["model_requests"] == proof["business_writes"] == 0
