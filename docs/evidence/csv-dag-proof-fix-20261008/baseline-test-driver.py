"""Adversarial final-commit and JSON proof type regressions, offline owned fixtures."""

import copy
import json
import time
from dataclasses import replace

import pytest
from sqlalchemy import select, update
from test_csv_dag import NoModel, read_row, setup, step_ids
from test_delivery_graph_apps import snapshot

from sim2act import csv_dag as dag
from sim2act.db import delivery_graph_requests, events, fingerprint, operations, runs
from sim2act.errors import DomainError

ONE = "item,amount,quantity\nA,10,7\n"


def ready(env):
    _, base, plan, body, w, job = setup(env, ONE)
    w.model = NoModel()
    for _ in range(3):
        assert dag.advance(w, job)
    assert read_row(env, job)["status"] == "RUNNING"
    return base, plan, body, w, job


@pytest.mark.parametrize("boundary", ["deadline", "exact_deadline", "lease", "budget"])
def test_final_readback_crosses_boundary_and_cannot_commit_success(env, monkeypatch, boundary):
    _, _, _, w, job = ready(env)
    before = snapshot(env)
    real = dag.receipts
    with env[0].engine.connect() as c:
        saved = dict(c.execute(select(runs).where(runs.c.id == job["id"])).mappings().one())
    clock = [max(saved["created_at"], saved["lease_until"] - env[1].lease_seconds)]

    def time_now():
        return clock[0]

    def cross(*args):
        outputs, proof = real(*args)
        if boundary in {"deadline", "exact_deadline"}:
            clock[0] = (
                saved["created_at"] + env[1].run_seconds + (1 if boundary == "deadline" else 0)
            )
            # Keep the lease valid, isolating the deadline defect.
            args[1].execute(
                update(runs).where(runs.c.id == job["id"]).values(lease_until=clock[0] + 30)
            )
        elif boundary == "lease":
            clock[0] = saved["lease_until"] + 1
        else:
            w.s = replace(w.s, max_tools=2)
        return outputs, proof

    monkeypatch.setattr(dag.time, "time", time_now)
    monkeypatch.setattr(dag, "receipts", cross)
    with pytest.raises(DomainError) as refused:
        dag.advance(w, job)
    assert refused.value.code == ("VERSION_CONFLICT" if boundary == "lease" else "BUDGET_EXHAUSTED")
    assert snapshot(env) == before  # Even the owned in-transaction lease change rolls back.
    assert read_row(env, job)["result"] is None and step_ids(env, job) == set(dag.STEPS)


@pytest.mark.parametrize("step", ["aggregate", "report"])
@pytest.mark.parametrize("wrong", [True, 1.0, "1"])
def test_persisted_count_wrong_json_type_rejected_without_resigning(env, step, wrong):
    _, _, _, w, job = ready(env)
    assert not dag.advance(w, job)
    with env[0].tx() as c:
        op = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == job["id"], operations.c.call_id == step
                )
            )
            .mappings()
            .one()
        )
        receipt = copy.deepcopy(op["receipt"])
        receipt["data"]["count"] = wrong
        c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
    before = snapshot(env)
    reply = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert reply.status_code in {400, 409}, reply.text
    assert snapshot(env) == before


@pytest.mark.parametrize(
    "target",
    [
        "action_revision",
        "final_count",
        "model_requests",
        "business_writes",
        "accepted_budget",
        "accepted_revision",
        "accepted_envelope",
        "cached_version",
        "plan_revision",
    ],
)
def test_equal_python_values_are_not_equal_persisted_json_proofs(env, target):
    base, plan, body, w, job = ready(env)
    assert not dag.advance(w, job)
    with env[0].tx() as c:
        if target == "action_revision":
            op = (
                c.execute(
                    select(operations).where(
                        operations.c.run_id == job["id"], operations.c.call_id == "report"
                    )
                )
                .mappings()
                .one()
            )
            value = copy.deepcopy(op["receipt"])
            value["action_revision"] = float(value["action_revision"])
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=value))
        elif target in {"final_count", "model_requests", "business_writes"}:
            value = copy.deepcopy(read_row(env, job)["result"])
            if target == "final_count":
                value["output"]["count"] = True
            else:
                value[target] = False
            c.execute(update(runs).where(runs.c.id == job["id"]).values(result=value))
        elif target.startswith("accepted_"):
            event = (
                c.execute(
                    select(events).where(
                        events.c.run_id == job["id"], events.c.kind == "CSV_DAG_ACCEPTED"
                    )
                )
                .mappings()
                .one()
            )
            value = copy.deepcopy(event["data"])
            if target == "accepted_budget":
                value["plan"]["definition"]["manifest"]["runtime_limits"]["max_repairs"] = False
            elif target == "accepted_revision":
                value["plan"]["definition"]["actions"][0]["revision"] = float(
                    value["plan"]["definition"]["actions"][0]["revision"]
                )
            else:
                value["plan"]["preflight"]["budget_envelope"]["max_tools"] = float(
                    value["plan"]["preflight"]["budget_envelope"]["max_tools"]
                )
            c.execute(update(events).where(events.c.id == event["id"]).values(data=value))
            c.execute(
                update(runs).where(runs.c.id == job["id"]).values(fingerprint=fingerprint(value))
            )
        else:
            kind = "csv_dag_run" if target == "cached_version" else "csv_dag_plan"
            key = "run" if kind == "csv_dag_run" else "plan"
            saved = (
                c.execute(
                    select(delivery_graph_requests).where(
                        delivery_graph_requests.c.app_id == plan["app_id"],
                        delivery_graph_requests.c.kind == kind,
                        delivery_graph_requests.c.request_key == key,
                    )
                )
                .mappings()
                .one()
            )
            value = copy.deepcopy(saved["snapshot"])
            if target == "cached_version":
                value["response"]["version"] = True
            else:
                value["response"]["definition"]["manifest"]["revision"] = float(
                    value["response"]["definition"]["manifest"]["revision"]
                )
            c.execute(
                update(delivery_graph_requests)
                .where(
                    delivery_graph_requests.c.app_id == plan["app_id"],
                    delivery_graph_requests.c.kind.in_([kind, kind + "_seal"]),
                    delivery_graph_requests.c.request_key == key,
                )
                .values(snapshot=value, fingerprint=fingerprint(value))
            )
    before = snapshot(env)
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {400, 409}
    if target == "cached_version":
        assert env[2].post(base + "/plan/runs", json=body).status_code == 409
    assert snapshot(env) == before


@pytest.mark.parametrize("point", ["partial", "complete"])
def test_bad_type_cold_recovery_never_reexecutes_or_commits_final_result(env, point):
    _, _, _, w, job = ready(env)
    if point == "complete":
        assert not dag.advance(w, job)
    with env[0].tx() as c:
        op = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == job["id"], operations.c.call_id == "aggregate"
                )
            )
            .mappings()
            .one()
        )
        value = copy.deepcopy(op["receipt"])
        value["data"]["count"] = True
        c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=value))
        if point == "partial":
            c.execute(update(runs).where(runs.c.id == job["id"]).values(lease_until=0))
    if point == "partial":
        from sim2act.db import Store
        from sim2act.worker import Worker

        store = Store(env[1].database_url, test_only=True)
        if not store.sqlite:
            store.engine = store.engine.execution_options(**env[0].engine.get_execution_options())
        try:
            fresh = Worker(store, env[1], NoModel())
            claimed = store.claim(fresh.id, env[1].lease_seconds)
            fresh.process(claimed)
            assert read_row(env, job)["status"] == "FAILED" and read_row(env, job)["result"] is None
        finally:
            store.engine.dispose()
    assert step_ids(env, job) == set(dag.STEPS)
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {400, 409}


def test_actual_wall_deadline_crossing_after_final_readback_rolls_back(env, monkeypatch):
    _, _, _, w, job = ready(env)
    now = time.time()
    with env[0].tx() as c:
        c.execute(
            update(runs)
            .where(runs.c.id == job["id"])
            .values(created_at=now - env[1].run_seconds + 0.5, lease_until=now + 30)
        )
    before = snapshot(env)
    real = dag.receipts

    def slow_read(*args):
        value = real(*args)
        time.sleep(0.75)
        return value

    monkeypatch.setattr(dag, "receipts", slow_read)
    with pytest.raises(DomainError) as denied:
        dag.advance(w, job)
    assert denied.value.code == "BUDGET_EXHAUSTED"
    assert snapshot(env) == before and read_row(env, job)["status"] == "RUNNING"
    assert read_row(env, job)["result"] is None


def test_mid_step_budget_tightening_counts_the_pending_operation_and_rolls_back(env, monkeypatch):
    _, _, _, _, w, job = setup(env, ONE)
    w.model = NoModel()
    assert dag.advance(w, job)
    before = snapshot(env)
    original = dag.authorized_read

    def tighten(*args):
        value = original(*args)
        if args[-2] == "data.aggregate_csv":
            w.s = replace(w.s, max_tools=1)
        return value

    monkeypatch.setattr(dag, "authorized_read", tighten)
    with pytest.raises(DomainError) as denied:
        dag.advance(w, job)
    assert denied.value.code == "BUDGET_EXHAUSTED"
    assert snapshot(env) == before and step_ids(env, job) == {"preview"}


def test_legal_old_receipts_and_cached_acceptance_unchanged(env, tmp_path):
    base, plan, body, w, job = ready(env)
    assert not dag.advance(w, job)
    before = snapshot(env)
    answer = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert answer.status_code == 200, answer.text
    assert answer.json()["result"]["output"]["count"] == 1
    assert env[2].post(base + "/plan/runs", json=body).json()["run_id"] == job["id"]
    assert snapshot(env) == before
    (tmp_path / "valid-proof.json").write_text(
        json.dumps(dict(plan=plan, proof=answer.json(), old_rows_preserved=True), indent=2)
    )
