"""Finite conjunction/disjunction on actual persisted CSV DAG effects; LIVE=0."""

import copy

import pytest
from sqlalchemy import select, update
from test_controlled_branches import condition, proof, setup, start
from test_csv_composition import composition
from test_csv_composition import setup as composition_setup
from test_csv_composition import start as composition_start
from test_csv_dag import NoModel, step_ids
from test_delivery_graph_apps import snapshot

from sim2act import csv_dag as dag
from sim2act.db import Store, events, fingerprint, grants, operations, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def group(op="all", count=2):
    return dict(op=op, conditions=[condition(),
        condition(source="step", ref="aggregate", field="count", value=count)])


@pytest.mark.parametrize("op", ["all", "any"])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("count", [2, 3])
def test_actual_two_conditions_truth_table_cold_resume_and_exact_key(env, op, enabled, count):
    _, base, plan, _ = setup(env, group(op, count))
    assert plan["branch_semantics"] == "typed-conditions.v2"
    before = snapshot(env)
    worker, job, body = start(env, base, plan, {"include_report": enabled})
    assert dag.advance(worker, job) and dag.advance(worker, job)
    with env[0].tx() as c:
        prefix = {r["call_id"]: r["id"] for r in c.execute(
            select(operations).where(operations.c.run_id == job["id"])).mappings()}
        c.execute(update(runs).where(runs.c.id == job["id"]).values(lease_until=0))
    cold = Store(env[1].database_url, test_only=True)
    cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        resumed = Worker(cold, env[1], NoModel())
        claimed = cold.claim(resumed.id, env[1].lease_seconds)
        assert claimed["id"] == job["id"] and claimed["fence"] > job["fence"]
        with pytest.raises(DomainError):
            dag.advance(worker, job)
        resumed.process(claimed)
        saved = proof(env, job)
        expected = (enabled and count == 2) if op == "all" else (enabled or count == 2)
        assert saved["status"] == ("SUCCEEDED" if expected else "PARTIAL")
        branch = saved["steps"][2]["branch_decision"]
        assert branch["version"] == "typed-conditions.v2"
        assert branch["passed"] is expected
        assert all(next(r for r in saved["steps"] if r["step_id"] == sid)["operation_id"] == oid
                   for sid, oid in prefix.items())
        assert branch["observation"]["conditions"] == [
            dict(evaluated=True, present=True, value=enabled, passed=enabled),
            dict(evaluated=True, present=True, value=2, passed=count == 2)]
        assert step_ids(env, job) == ({"preview", "aggregate", "report"} if expected else {"preview", "aggregate"})
        assert saved["result"]["output"]["sum"] == "15" if expected else saved["result"]["output"] is None
        replay = env[2].post(base + "/branches/runs", json=body)
        assert replay.status_code == 202 and replay.json()["cached"] is True
        assert replay.json()["run_id"] == job["id"]
        assert saved["model_requests"] == saved["business_writes"] == 0
        assert saved["publishable"] is False and saved["owner_acceptance"] == "PENDING"
    finally:
        cold.engine.dispose()
    after = snapshot(env)
    for name in before:
        if name not in {"runs", "run_contracts", "events", "operations", "operation_intents", "delivery_graph_requests"}:
            assert fingerprint(before[name]) == fingerprint(after[name]), name


@pytest.mark.parametrize("op", ["all", "any"])
def test_group_does_not_short_circuit_missing_required_comparison(env, op):
    expression = group(op)
    expression["conditions"].reverse()  # any's first predicate true; all's first false.
    expression["conditions"][0]["value"] = 2 if op == "any" else 3
    _, base, plan, _ = setup(env, expression)
    worker, job, _ = start(env, base, plan, {})
    worker.process(job)
    saved = proof(env, job)
    assert saved["status"] == "FAILED" and saved["error"]["code"] == "INVALID_INPUT"
    assert len(saved["steps"]) == 2 and saved["result"] is None


def test_four_leaf_exists_missing_is_false_and_membership_is_typed(env):
    expression = dict(op="any", conditions=[condition(op="exists"),
        condition(source="step", ref="aggregate", field="count", value=3),
        condition(op="in", source="step", ref="aggregate", field="sum", value=["15", "30"]),
        condition(source="step", ref="aggregate", field="column", value="quantity")])
    _, base, plan, _ = setup(env, expression)
    worker, job, _ = start(env, base, plan, {})
    worker.process(job)
    saved = proof(env, job)
    assert saved["status"] == "SUCCEEDED"
    assert [c["passed"] for c in saved["steps"][2]["branch_decision"]["observation"]["conditions"]] == [False, False, True, True]


@pytest.mark.parametrize("damage", ["zero", "one", "five", "nested", "unknown_op", "expression",
    "extra_source", "extra_value", "numeric_bool", "float_int", "future", "undeclared", "data", "exists_value"])
def test_all_group_leaves_preflight_before_any_write(env, damage):
    _, base, _, body = setup(env)
    bad = copy.deepcopy(body)
    expression = group()
    bad["request_key"] = "invalid-group"
    bad["branch_patch"][0]["when"] = expression
    if damage in {"zero", "one", "five"}:
        expression["conditions"] = [condition()] * {"zero": 0, "one": 1, "five": 5}[damage]
    elif damage == "nested":
        expression["conditions"][0] = group("any")
    elif damage == "unknown_op":
        expression["op"] = "eval"
    elif damage in {"expression", "extra_source", "extra_value"}:
        expression[{"expression": "expression", "extra_source": "source", "extra_value": "value"}[damage]] = "untrusted"
    elif damage == "numeric_bool":
        expression["conditions"][0]["value"] = 1
    elif damage == "float_int":
        expression["conditions"][1]["value"] = 2.0
    elif damage in {"future", "undeclared", "data"}:
        expression["conditions"][1]["source"] = dict(source="data" if damage == "data" else "step",
            ref={"future": "report", "undeclared": "preview", "data": "source"}[damage], field="count")
    else:
        expression["conditions"][0] = condition(op="exists")
        expression["conditions"][0]["value"] = None
    before = snapshot(env)
    reply = env[2].post(base, json=bad)
    assert reply.status_code in {400, 409, 422}, reply.text
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_group_in_four_node_composition_retains_each_independent_output(env):
    value = composition()
    value["nodes"][1]["when"] = dict(op="all", conditions=[condition(),
        condition(source="step", ref="a", field="sum", value="30")])
    _, base, plan, _ = composition_setup(env, value=value)
    worker, job, _ = composition_start(env, base, plan, inputs={"include_report": False})
    worker.process(job)
    saved = proof(env, job)
    assert saved["status"] == "PARTIAL"
    assert saved["result"]["output_by_step"]["a_report"] is None
    assert saved["result"]["output_by_step"]["b_report"]["sum"] == "15"
    assert len(saved["steps"]) == 4 and len(step_ids(env, job)) == 3


@pytest.mark.parametrize("enabled", [False, True])
def test_persisted_group_leaf_decision_tampering_fails_closed(env, enabled):
    _, base, plan, _ = setup(env, group())
    worker, job, _ = start(env, base, plan, {"include_report": enabled})
    worker.process(job)
    with env[0].tx() as c:
        if enabled:
            row = c.execute(select(operations).where(operations.c.run_id == job["id"], operations.c.call_id == "report")).mappings().one()
            data = copy.deepcopy(row["receipt"])
            data["branch_decision"]["observation"]["conditions"][0]["passed"] = False
            c.execute(update(operations).where(operations.c.id == row["id"]).values(receipt=data))
        else:
            row = c.execute(select(events).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).mappings().one()
            data = copy.deepcopy(row["data"])
            data["branch_decision"]["observation"]["conditions"][0]["passed"] = True
            c.execute(update(events).where(events.c.id == row["id"]).values(data=data))
    before = snapshot(env)
    reply = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert reply.status_code == (400 if enabled else 409), reply.text
    assert reply.json()["error"]["code"] == ("VERIFICATION_FAILED" if enabled else "VERSION_CONFLICT")
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_group_skip_still_requires_current_authority(env):
    _, base, plan, _ = setup(env, group())
    worker, job, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, job) and dag.advance(worker, job)
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id.in_(job["resource_refs"])).values(revoked=True))
    worker.process(job)
    saved = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert saved.status_code in {403, 409}
    with env[0].tx() as c:
        assert not c.execute(select(events.c.id).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).first()
