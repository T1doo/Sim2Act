"""Server-owned semantic port choices; real execution, explicit lineage and cold recovery."""

import copy
import csv
import hashlib
import io
import json
import time
from fractions import Fraction

import pytest
from sqlalchemy import select, update
from test_csv_dag import CSV, NoModel, read_row, setup, step_ids
from test_delivery_graph_apps import snapshot

from sim2act import csv_dag as dag
from sim2act.db import (
    Store,
    delivery_graph_requests,
    fingerprint,
    grants,
    operation_intents,
    operations,
    resources,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker

PATCH = [
    dict(
        step_id="aggregate",
        port="resource_id",
        source=dict(source="data", ref="source", field="resource_id"),
    ),
    dict(
        step_id="report",
        port="resource_id",
        source=dict(source="step", ref="preview", field="resource_id"),
    ),
    dict(
        step_id="report",
        port="source_hash",
        source=dict(source="step", ref="preview", field="hash"),
    ),
]


def propose(env, base, anchor, patch, key):
    return env[2].post(
        base,
        content=json.dumps(dict(
            expected_candidate_fingerprint=anchor["candidate_fingerprint"],
            expected_graph_fingerprint=anchor["graph_fingerprint"],
            column="quantity",
            request_key=key,
            wiring_patch=patch,
        ), ensure_ascii=True),
        headers={"Content-Type": "application/json"},
    )


def start(env, base, plan, key):
    body = dict(
        expected_plan_fingerprint=plan["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG",
        request_key=key,
    )
    reply = env[2].post(base + "/" + plan["request_key"] + "/runs", json=body)
    assert reply.status_code == 202, reply.text
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job["id"] == reply.json()["run_id"]
    return worker, job, body


def wired(env, content=None):
    rid, base, anchor, _, worker, old = setup(env, content) if content else setup(env)
    worker.model = NoModel()
    worker.process(old)
    reply = propose(env, base, anchor, PATCH, "wired")
    assert reply.status_code == 201, reply.text
    plan = reply.json()
    w, job, body = start(env, base, plan, "wired-run")
    return rid, base, anchor, plan, w, job, body


def test_server_options_authority_seal_exact_ports_and_no_write(env):
    _, base, anchor, _, _, _ = setup(env)
    before = snapshot(env)
    reply = env[2].get(base + "/options/wiring")
    assert reply.status_code == 200, reply.text
    answer = reply.json()
    assert answer["ports"] == dag.allowed_ports()
    assert [(p["step_id"], p["port"], p["semantic_type"]) for p in answer["ports"]] == [
        ("aggregate", "resource_id", "resource_id"),
        ("report", "resource_id", "resource_id"),
        ("report", "source_hash", "source_hash"),
    ]
    fp = answer.pop("options_fingerprint")
    assert fingerprint(answer) == fp and answer["barrier"] == ["preview", "aggregate"]
    assert answer["graph_fingerprint"] == anchor["graph_fingerprint"]
    assert answer["editable_dependencies"] is False and snapshot(env) == before
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].get(base + "/options/wiring").status_code == 403


def test_old_legal_wiring_options_request_key_remains_readable(env):
    _, base, anchor, _, _, _ = setup(env)
    body = dict(expected_candidate_fingerprint=anchor["candidate_fingerprint"],
                expected_graph_fingerprint=anchor["graph_fingerprint"],
                column="quantity", request_key="wiring-options")
    made = env[2].post(base, json=body)
    assert made.status_code == 201, made.text
    assert "wiring" not in made.json()
    saved = env[2].get(base + "/wiring-options")
    assert saved.status_code == 200
    assert saved.json() == {k: v for k, v in made.json().items() if k != "cached"}
    assert env[2].get(base + "/options/wiring").json()["ports"] == dag.allowed_ports()


@pytest.mark.parametrize("kind", ["lock", "unknown"])
def test_wired_new_definition_and_exact_replay_respect_existing_blockers(env, monkeypatch, kind):
    _, base, anchor, _, _, _, body = wired(env)
    real = dag.graph.current

    def blocked(*args, **kwargs):
        saved = copy.deepcopy(real(*args, **kwargs))
        if kind == "lock":
            saved["context"]["locked_nodes"] = ["owned-original-node"]
        else:
            saved["graph"]["unknown_dependencies"] = [{"scope": "PROJECT"}]
        return saved

    monkeypatch.setattr(dag.graph, "current", blocked)
    before = snapshot(env)
    new = propose(env, base, anchor, PATCH, "blocked")
    replay = env[2].post(base + "/wired/runs", json=body)
    assert new.status_code == replay.status_code == 400
    assert new.json()["error"]["code"] == ("LOCK_CONFLICT" if kind == "lock" else "UNSUPPORTED_CAPABILITY")
    assert snapshot(env) == before


def test_different_legal_wires_same_independent_answer_and_unchanged_objects(env, tmp_path):
    rid, base, anchor, _, worker, old = setup(env)
    worker.model = NoModel()
    worker.process(old)
    before = snapshot(env)
    baseline = propose(env, base, anchor, [], "baseline-wire").json()
    reply = propose(env, base, anchor, PATCH, "different-wire")
    assert reply.status_code == 201, reply.text
    plan = reply.json()
    after = snapshot(env)
    assert all(before[n] == after[n] for n in before if n != "delivery_graph_requests")
    assert plan["plan_fingerprint"] != baseline["plan_fingerprint"]
    assert fingerprint(plan["definition"]) != fingerprint(baseline["definition"])
    assert plan["definition"]["actions"] == baseline["definition"]["actions"]
    left, right = [copy.deepcopy(p["definition"]["manifest"]) for p in [plan, baseline]]
    left.pop("workflow")
    right.pop("workflow")
    assert left == right
    assert plan["definition"]["manifest"]["workflow"][1]["depends_on"] == ["preview"]
    assert plan["definition"]["manifest"]["workflow"][2]["depends_on"] == ["preview", "aggregate"]
    results = []
    for index, p in enumerate([baseline, plan]):
        w, job, _ = start(env, base, p, "actual-" + str(index))
        w.process(job)
        proved = env[0].inspect(env[3], job["id"])
        assert proved["status"] == "SUCCEEDED"
        results.append(proved)
    rows = list(csv.DictReader(io.StringIO(CSV.read_text())))
    totals = {
        key: str(sum((Fraction(r[key]) for r in rows), Fraction()))
        for key in ["amount", "quantity"]
    }
    assert totals == dict(amount="30", quantity="15")
    assert results[0]["result"]["output"] == results[1]["result"]["output"]
    assert results[1]["result"]["output"]["sum"] == totals["quantity"]
    proof = results[1]["steps"]
    assert proof[2]["input_sources"]["source_hash"] == PATCH[2]["source"]
    assert proof[2]["predecessor_receipts"] == [fingerprint(proof[0]), fingerprint(proof[1])]
    assert proof[1]["input_sources"]["resource_id"] == PATCH[0]["source"]
    with env[0].engine.connect() as c:
        op = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == results[1]["id"], operations.c.call_id == "report"
                )
            )
            .mappings()
            .one()
        )
        intent = c.execute(
            select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])
        ).scalar_one()
        assert intent["input_sources"] == proof[2]["input_sources"]
    assert all(p["model_requests"] == p["business_writes"] == 0 for p in results)
    (tmp_path / "wiring-proof.json").write_text(
        json.dumps(
            dict(
                expected=totals,
                source_hash=hashlib.sha256(CSV.read_text().encode()).hexdigest(),
                baseline=baseline,
                wired=plan,
                results=results,
                unchanged_tables=sorted(n for n in before if n != "delivery_graph_requests"),
            ),
            indent=2,
        )
    )


@pytest.mark.parametrize(
    "aggregate,resource,source_hash", [(a, r, h) for a in [0, 1] for r in [0, 1] for h in [0, 1]]
)
def test_all_eight_allowed_port_combinations_actual_execution(
    env, aggregate, resource, source_hash
):
    _, base, anchor, _, w, old = setup(env)
    w.model = NoModel()
    w.process(old)
    patches = [
        dict(step_id=p["step_id"], port=p["port"], source=p["sources"][i])
        for p, i in zip(dag.allowed_ports(), [aggregate, resource, source_hash], strict=True)
    ]
    p = propose(env, base, anchor, patches, "ports").json()
    w, job, _ = start(env, base, p, "ports-run")
    w.process(job)
    result = env[0].inspect(env[3], job["id"])
    assert result["result"]["output"]["sum"] == "15"
    assert len(result["steps"][2]["predecessor_receipts"]) == (2 if resource or source_hash else 1)
    assert result["steps"][2]["input_sources"] == p["wiring"]["inputs"]["report"]


@pytest.mark.parametrize(
    "attack",
    [
        "resource_from_hash",
        "hash_from_resource",
        "aggregate_hash_port",
        "resource_ref",
        "unknown_step",
        "unknown_port",
        "unknown_source",
        "unknown_dependency",
        "cycle",
        "executor",
        "schema",
        "nodes",
        "duplicate",
        "oversize",
        "surrogate",
    ],
)
def test_closed_wire_payload_rejects_semantic_string_confusion_and_unknowns_before_write(
    env, attack
):
    _, base, anchor, _, _, _ = setup(env)
    patch = copy.deepcopy(PATCH)
    if attack == "resource_from_hash":
        patch[1]["source"]["field"] = "hash"
    elif attack == "hash_from_resource":
        patch[2]["source"]["field"] = "resource_id"
    elif attack == "aggregate_hash_port":
        patch[0]["port"] = "source_hash"
    elif attack == "resource_ref":
        patch[0]["source"]["ref"] = "aggregate"
    elif attack == "unknown_step":
        patch[0]["step_id"] = "other"
    elif attack == "unknown_port":
        patch[0]["port"] = "sum"
    elif attack == "unknown_source":
        patch[0]["source"]["ref"] = "foreign"
    elif attack == "unknown_dependency":
        patch[0]["depends_on"] = ["foreign"]
    elif attack == "cycle":
        patch[0]["source"]["ref"] = "report"
    elif attack in {"executor", "schema", "nodes"}:
        patch[0][attack] = {"ref": "arbitrary"}
    elif attack == "duplicate":
        patch[1] = copy.deepcopy(patch[0])
    elif attack == "oversize":
        patch.append(copy.deepcopy(patch[0]))
    else:
        patch[0]["source"]["ref"] = "\ud800"
    before = snapshot(env)
    reply = propose(env, base, anchor, patch, "bad")
    assert reply.status_code in {400, 422}, reply.text
    assert snapshot(env) == before


def test_same_key_changed_wires_and_old_fingerprint_confirmation_are_rejected(env):
    _, base, anchor, plan, _, job, _ = wired(env)
    before = snapshot(env)
    reply = propose(env, base, anchor, [], "wired")
    assert reply.status_code == 409
    body = dict(
        expected_plan_fingerprint=anchor["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG",
        request_key="old-confirm",
    )
    assert env[2].post(base + "/wired/runs", json=body).status_code == 409
    assert snapshot(env) == before and step_ids(env, job) == set()
    assert plan["plan_fingerprint"] != anchor["plan_fingerprint"]


@pytest.mark.parametrize("count", [1, 2, 3])
def test_cold_recovery_verifies_wires_and_both_predecessors_without_reexecution(env, count):
    _, base, _, plan, w, job, body = wired(env)
    for _ in range(count):
        assert dag.advance(w, job)
    with env[0].tx() as c:
        saved = {
            r["call_id"]: r["id"]
            for r in c.execute(
                select(operations).where(operations.c.run_id == job["id"])
            ).mappings()
        }
        c.execute(update(runs).where(runs.c.id == job["id"]).values(lease_until=0))
    cold = Store(env[1].database_url, test_only=True)
    if not cold.sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        fresh = Worker(cold, env[1], NoModel())
        claim = cold.claim(fresh.id, env[1].lease_seconds)
        with pytest.raises(DomainError):
            dag.advance(w, job)
        fresh.process(claim)
        result = cold.inspect(env[3], job["id"])
        assert (
            result["status"] == "SUCCEEDED"
            and result["steps"][2]["input_sources"] == plan["wiring"]["inputs"]["report"]
        )
        assert len(result["steps"][2]["predecessor_receipts"]) == 2
        assert all(
            next(r for r in result["steps"] if r["step_id"] == s)["operation_id"] == oid
            for s, oid in saved.items()
        )
        assert env[2].post(base + "/wired/runs", json=body).json()["run_id"] == job["id"]
    finally:
        cold.engine.dispose()


@pytest.mark.parametrize(
    "attack", ["receipt_sources", "intent_sources", "parents", "plan_sources", "final"]
)
def test_lineage_tamper_rejected_even_when_ordinary_scalar_values_still_match(env, attack):
    _, _, _, plan, w, job, _ = wired(env)
    w.process(job)
    with env[0].tx() as c:
        op = (
            c.execute(
                select(operations).where(
                    operations.c.run_id == job["id"], operations.c.call_id == "report"
                )
            )
            .mappings()
            .one()
        )
        if attack in {"receipt_sources", "parents"}:
            value = copy.deepcopy(op["receipt"])
            if attack == "receipt_sources":
                value["input_sources"]["resource_id"] = dict(
                    source="step", ref="aggregate", field="resource_id"
                )
            else:
                value["predecessor_receipts"] = value["predecessor_receipts"][1:]
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=value))
        elif attack == "intent_sources":
            value = copy.deepcopy(
                c.execute(
                    select(operation_intents.c.request).where(
                        operation_intents.c.operation_id == op["id"]
                    )
                ).scalar_one()
            )
            value["input_sources"]["source_hash"] = dict(
                source="step", ref="aggregate", field="source_hash"
            )
            c.execute(
                update(operation_intents)
                .where(operation_intents.c.operation_id == op["id"])
                .values(request=value)
            )
        elif attack == "plan_sources":
            row = c.execute(select(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == plan["app_id"],
                delivery_graph_requests.c.kind == "csv_dag_plan",
                delivery_graph_requests.c.request_key == "wired")).mappings().one()
            value = copy.deepcopy(row["snapshot"])
            response = value["response"]
            changed = dict(source="step", ref="aggregate", field="source_hash")
            response["definition"]["manifest"]["workflow"][2]["inputs"]["source_hash"] = changed
            response["wiring"]["inputs"]["report"]["source_hash"] = changed
            response["plan_fingerprint"] = fingerprint({k: v for k, v in response.items() if k != "plan_fingerprint"})
            c.execute(update(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == plan["app_id"],
                delivery_graph_requests.c.kind.in_(["csv_dag_plan", "csv_dag_plan_seal"]),
                delivery_graph_requests.c.request_key == "wired").values(snapshot=value, fingerprint=fingerprint(value)))
        else:
            value = copy.deepcopy(read_row(env, job)["result"])
            value["steps"][2]["input_sources"]["source_hash"] = dict(
                source="step", ref="aggregate", field="source_hash"
            )
            c.execute(update(runs).where(runs.c.id == job["id"]).values(result=value))
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {400, 409}


@pytest.mark.parametrize("kind", ["source", "owner", "runtime"])
def test_wired_report_rechecks_source_and_authority_and_keeps_upstream(env, kind):
    rid, base, _, _, w, job, body = wired(env)
    assert dag.advance(w, job) and dag.advance(w, job)
    with env[0].tx() as c:
        if kind == "source":
            data = CSV.read_text().replace("20,8", "20,9")
            c.execute(
                update(resources)
                .where(resources.c.id == rid)
                .values(content=data, hash=hashlib.sha256(data.encode()).hexdigest())
            )
        else:
            c.execute(
                update(grants)
                .where(
                    grants.c.resource_id == rid,
                    grants.c.principal_id == (env[3] if kind == "owner" else job["runtime_id"]),
                )
                .values(revoked=True)
            )
    w.process(job)
    assert read_row(env, job)["status"] == "WAITING_RESOURCE" and step_ids(env, job) == {
        "preview",
        "aggregate",
    }
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {403, 409}
    assert env[2].post(base + "/wired/runs", json=body).status_code in {403, 409}
    assert env[2].get(base + "/options/wiring").status_code in {403, 409}


@pytest.mark.parametrize("step", ["aggregate", "report"])
@pytest.mark.parametrize("wrong", [True, 1.0])
def test_wired_actual_count_type_tamper_keeps_fingerprint_but_is_denied(env, step, wrong):
    _, _, _, _, w, job, _ = wired(env, "item,amount,quantity\nA,10,7\n")
    w.process(job)
    with env[0].tx() as c:
        op = c.execute(select(operations).where(
            operations.c.run_id == job["id"], operations.c.call_id == step)).mappings().one()
        value = copy.deepcopy(op["receipt"])
        assert type(value["data"]["count"]) is int and value["data"]["count"] == 1
        value["data"]["count"] = wrong
        c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=value))
    before = snapshot(env)
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {400, 409}
    assert snapshot(env) == before


def test_wired_actual_wall_deadline_cannot_commit_after_readback(env, monkeypatch):
    _, _, _, _, w, job, _ = wired(env)
    for _ in range(3):
        assert dag.advance(w, job)
    now = time.time()
    deadline = now + 1
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == job["id"]).values(
            created_at=deadline - env[1].run_seconds, lease_until=now + 30))
    before = snapshot(env)
    real = dag.receipts
    crossed = []

    def slow_read(*args):
        entered = time.time()
        value = real(*args)
        time.sleep(1.25)
        crossed.append((entered, time.time()))
        return value

    monkeypatch.setattr(dag, "receipts", slow_read)
    with pytest.raises(DomainError) as denied:
        dag.advance(w, job)
    assert denied.value.code == "BUDGET_EXHAUSTED"
    assert len(crossed) == 1 and crossed[0][0] < deadline <= crossed[0][1]
    assert snapshot(env) == before and read_row(env, job)["result"] is None


def test_wired_unknown_outcome_never_executes_report_or_reconciles_as_generic(env):
    _, _, _, _, w, job, _ = wired(env)
    assert dag.advance(w, job)
    with env[0].tx() as c:
        op = c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings().one()
        c.execute(update(operations).where(operations.c.id == op["id"]).values(status="OUTCOME_UNKNOWN"))
    w.process(job)
    state = read_row(env, job)
    assert state["status"] == "WAITING_RESOURCE" and step_ids(env, job) == {"preview"}
    with pytest.raises(DomainError) as denied:
        env[0].command(env[3], job["id"], "resume", state["version"])
    assert denied.value.code == "OUTCOME_UNKNOWN"
    with pytest.raises(DomainError) as denied:
        env[0].reconcile_operation(env[3], job["id"], op["id"], state["version"], fingerprint({}), {})
    assert denied.value.code == "UNSUPPORTED_CAPABILITY"
