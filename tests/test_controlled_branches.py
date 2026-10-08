"""Real frozen conditional plans and durable branch oracles, never model calls."""

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, update
from test_column_patches import setup as source_setup
from test_csv_dag import NoModel, read_row, step_ids
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits

from sim2act import csv_dag as dag
from sim2act.db import Store, events, fingerprint, grants, resources, runs
from sim2act.errors import DomainError
from sim2act.preflight import preflight
from sim2act.worker import Worker


def condition(op="eq", source="input", ref=None, field="include_report", value=True):
    source_value = dict(source=source, field=field)
    if ref is not None:
        source_value["ref"] = ref
    result = dict(op=op, source=source_value)
    if op != "exists":
        result["value"] = value
    return result


def setup(env, when=None, target="report"):
    aid, rid, anchor, _, _ = source_setup(env)
    base = f"/api/projects/{env[5]}/apps/{aid}/csv-dag"
    body = dict(expected_candidate_fingerprint=anchor["candidate_fingerprint"],
        expected_graph_fingerprint=anchor["graph_fingerprint"], column="quantity", request_key="branches",
        branch_patch=[dict(step_id=target, when=when or condition())])
    reply = env[2].post(base, json=body)
    assert reply.status_code == 201, reply.text
    return rid, base, reply.json(), body


def start(env, base, plan, inputs=None, key="conditional-run"):
    body = dict(expected_plan_fingerprint=plan["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key=key)
    if inputs is not None:
        body["branch_inputs"] = inputs
    reply = env[2].post(base + "/branches/runs", json=body)
    assert reply.status_code == 202, reply.text
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job["id"] == reply.json()["run_id"]
    return worker, job, body


def proof(env, job):
    reply = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert reply.status_code == 200, reply.text
    return reply.json()


def test_same_exact_plan_distinct_inputs_actual_paths_and_cold_key_recovery(env):
    _, base, plan, _ = setup(env)
    frozen_before = snapshot(env)
    for enabled in (False, True):
        worker, job, body = start(env, base, plan, {"include_report": enabled}, str(enabled))
        worker.process(job)
        saved = proof(env, job)
        assert saved["status"] == ("SUCCEEDED" if enabled else "PARTIAL")
        assert step_ids(env, job) == ({"preview", "aggregate", "report"} if enabled else {"preview", "aggregate"})
        assert saved["steps"][2]["status"] == ("VERIFIED" if enabled else "SKIPPED")
        decision = saved["steps"][2]["branch_decision"]
        assert decision["passed"] is enabled
        assert decision["reason"] == ("CONDITION_TRUE" if enabled else "CONDITION_FALSE")
        assert decision["observation"] == {"evaluated": True, "present": True, "value": enabled}
        assert saved["result"]["output_status"] == ("PRODUCED" if enabled else "SKIPPED")
        if enabled:
            assert saved["result"]["output"]["sum"] == "15"
        else:
            assert saved["result"]["output"] is None
        cold = Store(env[1].database_url, test_only=True)
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
        try:
            same = dag.inspect_job(cold, env[3], job["id"], limits(env))
            assert fingerprint(same) == fingerprint(saved)
            accepted = dag.enqueue(cold, env[3], env[5], plan["app_id"], "branches", dag.RunInput(**body), limits(env))
            assert accepted["cached"] and accepted["run_id"] == job["id"]
        finally:
            cold.engine.dispose()
    after = snapshot(env)
    for name in frozen_before:
        if name not in {"runs", "run_contracts", "events", "operations", "operation_intents", "delivery_graph_requests"}:
            assert fingerprint(after[name]) == fingerprint(frozen_before[name]), name


@pytest.mark.parametrize("op,inputs,expected", [
    ("eq", {}, "FAILED"), ("in", {}, "FAILED"), ("exists", {}, "SKIPPED"),
    ("exists", {"include_report": False}, "VERIFIED"),
    ("in", {"include_report": False}, "SKIPPED"), ("in", {"include_report": True}, "VERIFIED")])
def test_missing_and_boolean_membership_semantics(env, op, inputs, expected):
    _, base, plan, _ = setup(env, condition(op=op, value=[True] if op == "in" else True))
    worker, job, _ = start(env, base, plan, inputs)
    worker.process(job)
    saved = proof(env, job)
    if expected == "FAILED":
        assert saved["status"] == "FAILED" and saved["error"]["code"] == "INVALID_INPUT"
        assert len(saved["steps"]) == 2 and saved["result"] is None
    else:
        assert saved["status"] == ("PARTIAL" if expected == "SKIPPED" else "SUCCEEDED") and saved["steps"][2]["status"] == expected


@pytest.mark.parametrize("value", [0, 1, 1.0, "true", None, [], {}])
def test_run_boolean_type_rejects_before_writes(env, value):
    _, base, plan, _ = setup(env)
    before = snapshot(env)
    reply = env[2].post(base + "/branches/runs", json=dict(expected_plan_fingerprint=plan["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="bad-input", branch_inputs={"include_report": value}))
    assert reply.status_code in {400, 422}
    assert fingerprint(snapshot(env)) == fingerprint(before)


@pytest.mark.parametrize("attack", ["future", "self", "data", "unknown", "numeric_bool", "float_int", "null",
    "empty_in", "big_in", "exists_value", "expression", "duplicate", "preview"])
def test_condition_plan_rejects_unsafe_or_mistyped_references(env, attack):
    _, base, _, body = setup(env)
    bad = copy.deepcopy(body)
    bad["request_key"] = "bad-branch"
    branch = bad["branch_patch"][0]
    if attack in {"future", "self"}:
        branch["step_id"] = "aggregate"
        branch["when"] = condition(source="step", ref="report" if attack == "future" else "aggregate", field="count", value=2)
    elif attack == "data":
        branch["when"] = condition(source="data", ref="source", field="resource_id", value="x")
    elif attack == "unknown":
        branch["when"]["source"]["field"] = "not_declared"
    elif attack == "numeric_bool":
        branch["when"]["value"] = 1
    elif attack == "float_int":
        branch["when"] = condition(source="step", ref="aggregate", field="count", value=2.0)
    elif attack == "null":
        branch["when"]["value"] = None
    elif attack in {"empty_in", "big_in"}:
        branch["when"] = condition(op="in", value=[] if attack == "empty_in" else [True] * 21)
    elif attack == "exists_value":
        branch["when"] = condition(op="exists")
        branch["when"]["value"] = None
    elif attack == "expression":
        branch["when"]["expression"] = "eval(1)"
    elif attack == "duplicate":
        bad["branch_patch"].append(copy.deepcopy(branch))
    else:
        branch["step_id"] = "preview"
    before = snapshot(env)
    reply = env[2].post(base, json=bad)
    assert reply.status_code in {400, 409, 422}, reply.text
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_skipped_parent_cascades_without_resolving_missing_outputs(env):
    _, base, plan, _ = setup(env, target="aggregate")
    worker, job, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, job)
    assert dag.advance(worker, job)
    # Cold worker resumes after a durable skip, not an in-memory branch choice.
    cold = Worker(env[0], env[1], NoModel())
    cold.process(job)
    saved = proof(env, job)
    assert [s["status"] for s in saved["steps"]] == ["VERIFIED", "SKIPPED", "SKIPPED"]
    assert saved["steps"][2]["branch_decision"]["reason"] == "DEPENDENCY_SKIPPED"
    assert saved["steps"][2]["branch_decision"]["observation"] == {"evaluated": False}
    assert step_ids(env, job) == {"preview"}
    assert read_row(env, job)["context"]["tools"] == 1
    assert saved["result"]["output"] is None


@pytest.mark.parametrize("op,value,status", [("eq", 2, "VERIFIED"), ("in", [3], "SKIPPED"), ("exists", None, "VERIFIED")])
def test_verified_predecessor_value_drives_actual_branch(env, op, value, status):
    _, base, plan, _ = setup(env, condition(op=op, source="step", ref="aggregate", field="count", value=value))
    worker, job, _ = start(env, base, plan)
    worker.process(job)
    saved = proof(env, job)
    assert saved["steps"][2]["status"] == status
    assert saved["steps"][2]["branch_decision"]["observation"]["value"] == 2


@pytest.mark.parametrize("attack", ["grant", "source", "input", "skip", "duplicate_skip"])
def test_invalidation_or_decision_tamper_preserves_existing_prefix(env, attack):
    rid, base, plan, _ = setup(env, target="aggregate")
    worker, job, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, job)
    assert dag.advance(worker, job)
    with env[0].tx() as c:
        if attack == "grant":
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
        elif attack == "source":
            value = "item,amount,quantity\nX,1,9\n"
            c.execute(update(resources).where(resources.c.id == rid).values(content=value, hash=hashlib.sha256(value.encode()).hexdigest()))
        elif attack == "input":
            event = c.execute(select(events).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_ACCEPTED")).mappings().one()
            value = copy.deepcopy(event["data"])
            value["inputs"]["include_report"] = True
            c.execute(update(events).where(events.c.id == event["id"]).values(data=value))
            c.execute(update(runs).where(runs.c.id == job["id"]).values(fingerprint=fingerprint(value)))
        else:
            event = c.execute(select(events).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).mappings().one()
            if attack == "skip":
                value = copy.deepcopy(event["data"])
                value["branch_decision"]["passed"] = True
                c.execute(update(events).where(events.c.id == event["id"]).values(data=value))
            else:
                env[0].event(c, job["id"], "CSV_DAG_STEP_SKIPPED", event["data"])
    before = snapshot(env)
    reply = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert reply.status_code in {400, 403, 409}, reply.text
    assert fingerprint(snapshot(env)) == fingerprint(before)
    worker.process(job)
    assert read_row(env, job)["status"] == "WAITING_RESOURCE"
    assert step_ids(env, job) == {"preview"}


@pytest.mark.parametrize("boundary", ["lease", "deadline", "budget"])
def test_skip_commit_rechecks_fence_deadline_and_effective_budget(env, monkeypatch, boundary):
    _, base, plan, _ = setup(env, target="aggregate")
    worker, job, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, job)
    original = dag.decision
    def expire(*args, **kwargs):
        result = original(*args, **kwargs)
        if boundary == "lease":
            monkeypatch.setattr(dag.time, "time", lambda: job["lease_until"] + 1)
        elif boundary == "deadline":
            monkeypatch.setattr(dag.time, "time", lambda: job["created_at"] + worker.s.run_seconds + 1)
        else:
            worker.s = worker.s.__class__(**{**worker.s.__dict__, "max_tools": 1})
        return result
    monkeypatch.setattr(dag, "decision", expire)
    # A zero-tool skip still cannot commit under an expired lease/deadline.
    if boundary == "budget":
        # Existing one tool remains within max_tools=1; no additional tool is charged.
        assert dag.advance(worker, job)
        assert read_row(env, job)["context"]["tools"] == 1
    else:
        with pytest.raises(DomainError):
            dag.advance(worker, job)
        with env[0].engine.connect() as c:
            assert not c.execute(select(events.c.id).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).first()


def test_concurrent_workers_do_not_duplicate_skip_or_operations(env):
    _, base, plan, _ = setup(env, target="aggregate")
    worker, job, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, job)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: dag.advance(worker, job), range(2)))
    assert outcomes == [True, True]
    worker.process(job)
    saved = proof(env, job)
    assert saved["status"] == "PARTIAL"
    assert step_ids(env, job) == {"preview"}
    with env[0].engine.connect() as c:
        assert len(c.execute(select(events.c.id).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).all()) == 2


def test_manifest_dependency_cycle_is_rejected(env):
    _, _, plan, _ = setup(env)
    manifest = copy.deepcopy(plan["definition"]["manifest"])
    manifest["workflow"][0]["depends_on"] = ["report"]
    with pytest.raises(DomainError):
        preflight(json.dumps(manifest), plan["definition"]["actions"], limits(env))


@pytest.mark.parametrize("attack", ["promote_success", "invent_output", "reason_type", "input_type"])
def test_completed_skip_cannot_be_promoted_or_retyped(env, attack):
    _, base, plan, _ = setup(env)
    worker, job, _ = start(env, base, plan, {"include_report": False})
    worker.process(job)
    saved = proof(env, job)
    assert saved["status"] == "PARTIAL"
    with env[0].tx() as c:
        if attack in {"promote_success", "invent_output"}:
            value = copy.deepcopy(saved["result"])
            if attack == "invent_output":
                value["output"] = {"sum": "15"}
            c.execute(update(runs).where(runs.c.id == job["id"]).values(
                result=value, status="SUCCEEDED" if attack == "promote_success" else "PARTIAL"))
        else:
            event = c.execute(select(events).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).mappings().one()
            value = copy.deepcopy(event["data"])
            if attack == "reason_type":
                value["branch_decision"]["passed"] = 0
            else:
                value["branch_decision"]["observation"]["value"] = 0
            c.execute(update(events).where(events.c.id == event["id"]).values(data=value))
    before = snapshot(env)
    reply = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert reply.status_code in {400, 409}
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_branch_confirmation_wrong_exact_fingerprint_and_key_change_zero_write(env):
    _, base, plan, _ = setup(env)
    before = snapshot(env)
    body = dict(expected_plan_fingerprint="0" * 64, consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="bad")
    assert env[2].post(base + "/branches/runs", json=body).status_code == 409
    assert fingerprint(snapshot(env)) == fingerprint(before)
    _, _, accepted = start(env, base, plan, {"include_report": False})
    changed = copy.deepcopy(accepted)
    changed["branch_inputs"]["include_report"] = True
    before = snapshot(env)
    assert env[2].post(base + "/branches/runs", json=changed).status_code == 409
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_conditional_manifest_is_not_silently_ignored_by_agent_preview(env):
    from test_bounded_agent_apps import candidate

    from sim2act.agent_apps import compile_agent
    from sim2act.contracts import validate_action, validate_manifest

    value = candidate(env[6], "synthetic")
    value["manifest"]["workflow"][0]["when"] = condition(field="term", value="x")
    manifest = validate_manifest(json.dumps(value["manifest"]))
    actions = [validate_action(json.dumps(a)) for a in value["actions"]]
    with pytest.raises(DomainError) as error:
        compile_agent(value, manifest, actions, {})
    assert error.value.code == "UNSUPPORTED_CAPABILITY"


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_pg_crud_role_conditional_plan_run_and_cold_proof(env, runtime_role, enabled):
    from dataclasses import replace

    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    _, _, source, body = setup(env)
    body["request_key"] = "role-plan"
    store = Store(runtime_role, test_only=True)
    before = snapshot(env)
    try:
        plan = dag.propose(store, env[3], env[5], source["app_id"], dag.PlanInput(**body), limits(env))
        confirmation = dag.RunInput(expected_plan_fingerprint=plan["plan_fingerprint"],
            consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="role-run", branch_inputs={"include_report": enabled})
        accepted = dag.enqueue(store, env[3], env[5], plan["app_id"], "role-plan", confirmation, limits(env))
        settings = replace(env[1], database_url=runtime_role)
        worker = Worker(store, settings, NoModel())
        job = store.claim(worker.id, settings.lease_seconds)
        assert job["id"] == accepted["run_id"]
        assert dag.advance(worker, job)
        cold = Store(runtime_role, test_only=True)
        try:
            Worker(cold, settings, NoModel()).process(job)
            saved = dag.inspect_job(cold, env[3], job["id"], limits(env))
            assert saved["status"] == ("SUCCEEDED" if enabled else "PARTIAL")
            assert dag.enqueue(cold, env[3], env[5], plan["app_id"], "role-plan", confirmation, limits(env))["cached"]
        finally:
            cold.engine.dispose()
        with store.engine.connect() as c:
            assert c.execute(text('select rolsuper from pg_roles where rolname=current_user')).scalar() is False
        with pytest.raises(ProgrammingError), store.tx() as c:
            c.execute(text("CREATE TABLE forbidden_branch_ddl (id integer)"))
        after = snapshot(env)
        for name in ["grants", "principals", "app_drafts", "resources"]:
            assert fingerprint(after[name]) == fingerprint(before[name]), name
    finally:
        store.engine.dispose()


@pytest.mark.parametrize("boundary", ["fence", "cancel", "budget"])
def test_skip_cannot_commit_after_ownership_or_effective_capacity_changes(env, monkeypatch, boundary):
    from dataclasses import replace

    _, base, plan, _ = setup(env)
    worker, job, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, job)
    assert dag.advance(worker, job)
    assert step_ids(env, job) == {"preview", "aggregate"}
    original = dag.decision
    def change(*args, **kwargs):
        value = original(*args, **kwargs)
        if boundary == "budget":
            worker.s = replace(worker.s, max_tools=1)
        return value
    if boundary == "budget":
        monkeypatch.setattr(dag, "decision", change)
        before = snapshot(env)
        with pytest.raises(DomainError) as rejected:
            dag.advance(worker, job)
        assert rejected.value.code == "BUDGET_EXHAUSTED"
        assert fingerprint(snapshot(env)) == fingerprint(before)
    else:
        with env[0].tx() as c:
            changed = {"fence": job["fence"] + 1} if boundary == "fence" else {"status": "CANCEL_REQUESTED", "cancel_intent": True}
            c.execute(update(runs).where(runs.c.id == job["id"]).values(**changed))
        if boundary == "fence":
            before = snapshot(env)
            with pytest.raises(DomainError):
                dag.advance(worker, job)
            assert fingerprint(snapshot(env)) == fingerprint(before)
        else:
            assert dag.advance(worker, job) is False
            assert read_row(env, job)["status"] == "CANCELLED"
        with env[0].engine.connect() as c:
            assert not c.execute(select(events.c.id).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).first()


def test_conditional_candidate_cross_owner_denied_zero_write(env):
    _, base, plan, _ = setup(env)
    worker, job, _ = start(env, base, plan, {"include_report": False})
    assert dag.advance(worker, job)
    before = snapshot(env)
    original = env[2].headers["Authorization"]
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    try:
        assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code == 403
        assert env[2].post(base + "/branches/runs", json=dict(expected_plan_fingerprint=plan["plan_fingerprint"],
            consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="foreign", branch_inputs={"include_report": True})).status_code == 403
    finally:
        env[2].headers["Authorization"] = original
    assert fingerprint(snapshot(env)) == fingerprint(before)
