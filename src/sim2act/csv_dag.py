"""Fixed offline three-step adapter on the existing Run/Operation/Worker ledger.

Immutable engineering plans extend an existing CSV draft without replacing it.
No generic interpreter, model-generated plan, identity, Grant, Release or artifact.
"""

import copy
import csv
import io
import json
import threading
import time
from fractions import Fraction
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import insert, select, update

from . import csv_reports as report
from . import delivery_graph_apps as graph
from .app_jobs import lock_live, stop_state
from .column_patches import read_pair, require_capacity
from .contracts import (
    FrozenRunContract,
    GoalSpec,
    Limits,
    ResourceSnapshot,
    Strict,
    validate_action_input,
    validate_value,
)
from .db import (
    delivery_graph_requests,
    events,
    fingerprint,
    new_id,
    operation_intents,
    operations,
    run_contracts,
    runs,
)
from .errors import DomainError
from .preflight import preflight
from .tools import aggregate_csv_content, authorized_read, csv_column_options

KIND = "FIXED_CSV_DAG"
PLAN = "fixed-csv-dag.v1"
STEPS = ("preview", "aggregate", "report")
READ_OUTPUT = report.obj({"resource_id": {"type": "string"}, "content": {"type": "string"},
                          "hash": {"type": "string"}, "format": {"type": "string"}})


class PlanInput(Strict):
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    column: str = Field(min_length=1, max_length=200)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


class RunInput(Strict):
    expected_plan_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["CONFIRM_EXACT_OFFLINE_CSV_DAG"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


def canonical(candidate, column, limits):
    """An exact fixed template, not a caller-supplied or model-produced DAG."""
    original = candidate["manifest"]
    rid = original["data_bindings"][0]["resource_ref"]
    node_limits = limits.model_dump()
    for key in ("max_requests", "max_tools", "max_total_tokens", "run_seconds"):
        node_limits[key] //= 3
        if node_limits[key] < 1:
            raise DomainError("BUDGET_EXHAUSTED", "Three-node conservative envelope required")
    node_limits["max_repairs"] = 0
    actions = []
    manifest = copy.deepcopy(original)
    manifest["revision"] += 1
    manifest["runtime_limits"] = limits.model_dump()
    manifest["input_schema"] = report.obj({"column": {"type": "string", "enum": [column]}})
    manifest["output_schema"] = copy.deepcopy(report.OUTPUT)
    manifest["outputs"] = {k: dict(source="step", ref="report", field=k) for k in report.OUTPUT["properties"]}
    manifest["views"] = [dict(component_ref="text", output_field="text")]
    manifest["workflow"], manifest["action_bindings"] = [], []
    for step, ref, inputs, output in (
        ("preview", "resource.read", report.obj({"resource_id": {"type": "string"}}), READ_OUTPUT),
        ("aggregate", "data.aggregate_csv", report.obj({"resource_id": {"type": "string"},
         "column": {"type": "string", "enum": [column]}}), report.INPUT),
        ("report", report.REF, report.INPUT, report.OUTPUT),
    ):
        action = copy.deepcopy(candidate["actions"][0])
        action["action_id"] = "action_" + fingerprint([PLAN, original["app_id"], step])[:32]
        action["revision"] = manifest["revision"]
        action["executor"] = dict(kind="registered_tool", ref=ref, version="1")
        action["input_schema"], action["output_schema"] = copy.deepcopy(inputs), copy.deepcopy(output)
        action["limits"] = copy.deepcopy(node_limits)
        action["permission_requirements"] = (
            [] if step == "report" else [p for p in action["permission_requirements"]
                                        if step == "aggregate" or p["tool_ref"] == "resource.read"]
        )
        action["dependencies"] = [] if step == "report" else [dict(kind="resource", ref=rid, version="1")]
        actions.append(action)
        manifest["action_bindings"].append(dict(binding_id=step, action_id=action["action_id"], revision=action["revision"]))
        wires = (
            {"resource_id": dict(source="data", ref="source", field="resource_id")}
            if step == "preview" else
            {"resource_id": dict(source="step", ref="preview", field="resource_id"),
             "column": dict(source="input", field="column")}
            if step == "aggregate" else
            {k: dict(source="step", ref="aggregate", field=k) for k in report.FIELDS}
        )
        manifest["workflow"].append(dict(step_id=step, binding_id=step,
                                            depends_on=[] if step == "preview" else [STEPS[STEPS.index(step) - 1]],
                                            inputs=wires))
    manifest["dependency_lock"] = [
        dict(kind="resource", ref=rid, version="1"),
        *[dict(kind="tool", ref=ref, version="1") for ref in ("resource.read", "data.aggregate_csv", report.REF)],
        dict(kind="check", ref="receipt.readback.v1", version="1"),
    ]
    return dict(manifest=manifest, actions=actions)


def compile_plan(candidate, column, limits):
    expected = canonical(candidate, column, limits)
    manifest, checked = preflight(json.dumps(expected["manifest"]), expected["actions"], limits)
    if checked["topological_order"] != list(STEPS):
        graph.conflict("Fixed DAG topology changed")
    return expected, manifest, checked


def build(store, c, user, pid, aid, body, limits):
    saved = graph.current(store, c, user, pid, aid, limits)
    draft, _, action, _, _, _ = graph.load_family(store, c, user, pid, aid, limits)
    if action.executor.kind != "registered_tool" or action.executor.ref != "data.aggregate_csv":
        raise DomainError("UNSUPPORTED_CAPABILITY", "Only the existing fixed CSV application is supported")
    if (body.expected_candidate_fingerprint != draft["fingerprint"]
            or body.expected_graph_fingerprint != saved["graph"]["graph_fingerprint"]):
        graph.conflict("DAG candidate/graph version changed")
    if saved["context"]["locked_nodes"]:
        raise DomainError("LOCK_CONFLICT", "Locked original objects require explicit resolution")
    if (any(x["scope"] == "PROJECT" for x in saved["graph"]["unknown_dependencies"])
            or any(e["provenance"] == "MODEL_CANDIDATE" or e["type"] == "SEMANTIC" for e in saved["graph"]["edges"])):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Unknown project/semantic dependencies are outside the fixed adapter")
    template, _, checked = compile_plan(draft["candidate"], body.column, limits)
    value = dict(namespace=PLAN, project_id=pid, app_id=aid, runtime_id=draft["runtime_id"],
                 request_key=body.request_key, candidate_fingerprint=draft["fingerprint"],
                 graph_fingerprint=saved["graph"]["graph_fingerprint"],
                 graph_revision=saved["graph_revision"], authorization_fingerprint=saved["authorization_fingerprint"],
                 source_hash=draft["candidate"]["source_hash"], input={"column": body.column},
                 definition=template, preflight=checked, state="DRAFT_PLAN", model_generated=False,
                 model_requests=0, business_writes=0, publishable=False, formal_publication_enabled=False,
                 semantic_status="UNKNOWN", owner_acceptance="PENDING")
    return {**value, "plan_fingerprint": fingerprint(value)}


def load_plan(store, c, user, pid, aid, key, limits):
    body, answer = read_pair(c, user, aid, "csv_dag_plan", key, PlanInput)
    if build(store, c, user, pid, aid, body, limits) != answer:
        graph.conflict("DAG frozen definition/authority/source changed")
    return answer


@graph.controlled
def propose(store, user, pid, aid, body, limits):
    with store.tx() as c:
        answer = build(store, c, user, pid, aid, body, limits)
        old = graph.lookup(c, user, aid, "csv_dag_plan", body.request_key)
        if old:
            if load_plan(store, c, user, pid, aid, body.request_key, limits) != answer:
                graph.conflict("DAG request key changed")
        else:
            require_capacity(c, user, aid, "csv_dag_plan")
            for kind in ("csv_dag_plan", "csv_dag_plan_seal"):
                graph.remember(c, user, aid, kind, body.request_key, body, answer)
        return {**answer, "cached": bool(old)}


@graph.controlled
def enqueue(store, user, pid, aid, plan_key, body, limits):
    with store.tx() as c:
        plan = load_plan(store, c, user, pid, aid, plan_key, limits)
        if plan["plan_fingerprint"] != body.expected_plan_fingerprint:
            graph.conflict("Exact DAG confirmation required")
        old = graph.lookup(c, user, aid, "csv_dag_run", body.request_key)
        if old:
            request, answer = read_pair(c, user, aid, "csv_dag_run", body.request_key, RunInput)
            if request != body or answer["plan_key"] != plan_key:
                graph.conflict("Run request key changed")
            job = row(c, user, answer["run_id"])
            binding(store, c, job, limits)
            return {**answer, "cached": True}
        require_capacity(c, user, aid, "csv_dag_run")
        rid = new_id("run")
        source_id = plan["definition"]["manifest"]["data_bindings"][0]["resource_ref"]
        goal = "Fixed offline CSV preview, sum and deterministic report"
        contract = FrozenRunContract(
            run_id=rid, runtime_id=plan["runtime_id"], contract_version="F1.3",
            goal=GoalSpec(goal_id=new_id("goal"), project_id=pid, owner_id=user, goal=goal,
                          constraints=[], acceptance_version="F1-tool-chain.v1", resource_refs=[source_id],
                          unresolved=["Engineering candidate; semantic UNKNOWN; owner PENDING"]),
            resources=[ResourceSnapshot(resource_id=source_id, revision=1,
                                        content_hash=plan["source_hash"], format="csv")],
            limits=limits, mode="mock", request_model="intern-s2",
        ).model_dump()
        accepted = dict(run_id=rid, plan_key=plan_key, app_id=aid, project_id=pid,
                        principal_id=user, runtime_id=plan["runtime_id"], plan=plan,
                        confirmation=body.model_dump(), contract_fingerprint=fingerprint(contract))
        c.execute(insert(run_contracts).values(run_id=rid, snapshot=contract, fingerprint=fingerprint(contract)))
        c.execute(insert(runs).values(
            id=rid, project_id=pid, principal_id=user, runtime_id=plan["runtime_id"], goal=goal,
            resource_refs=[source_id], request_key="csv-dag:" + rid, fingerprint=fingerprint(accepted),
            status="QUEUED", created_at=time.time(), lease_until=0, fence=0,
            context=dict(kind=KIND, messages=[], requests=0, tools=0, repairs=0, reserved_tokens=0),
            version=1, cancel_intent=False,
        ))
        store.event(c, rid, "CSV_DAG_ACCEPTED", accepted)
        answer = dict(namespace=PLAN, run_id=rid, plan_key=plan_key, plan_fingerprint=plan["plan_fingerprint"], status="QUEUED", version=1)
        for kind in ("csv_dag_run", "csv_dag_run_seal"):
            graph.remember(c, user, aid, kind, body.request_key, body, answer)
        return {**answer, "cached": False}


def is_job(store, rid):
    with store.engine.connect() as c:
        ctx = c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar()
        marked = c.execute(select(events.c.id).where(events.c.run_id == rid, events.c.kind == "CSV_DAG_ACCEPTED")).first()
        return bool(marked or isinstance(ctx, dict) and ctx.get("kind") == KIND)


def row(c, user, rid):
    job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user).with_for_update()).mappings().first()
    if not job:
        raise DomainError("PERMISSION_DENIED")
    return dict(job)


def owner_lock(store, c, user, rid):
    pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)).scalar()
    store.lock_project(c, user, pid)


def binding(store, c, job, limits, *, authorize=True):
    store.lock_project(c, job["principal_id"], job["project_id"])
    accepted = c.execute(select(events.c.data).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_ACCEPTED")).scalars().all()
    if len(accepted) != 1 or fingerprint(accepted[0]) != job["fingerprint"]:
        graph.conflict("Missing immutable DAG acceptance")
    value = accepted[0]
    ctx = job["context"]
    if (set(ctx) != {"kind", "messages", "requests", "tools", "repairs", "reserved_tokens"}
            or ctx["messages"] != [] or any(type(ctx[k]) is not int for k in ("requests", "tools", "repairs", "reserved_tokens"))
            or any(ctx[k] != 0 for k in ("requests", "repairs", "reserved_tokens"))
            or not 0 <= ctx["tools"] <= 3):
        graph.conflict("Fixed DAG has only three local operations and zero model usage")
    if (job["context"].get("kind") != KIND or value["run_id"] != job["id"]
            or value["principal_id"] != job["principal_id"] or value["project_id"] != job["project_id"]
            or value["runtime_id"] != job["runtime_id"]):
        graph.conflict("DAG Run identity changed")
    confirmation = RunInput.model_validate(value["confirmation"])
    req, receipt = read_pair(c, job["principal_id"], value["app_id"], "csv_dag_run", confirmation.request_key, RunInput)
    if req != confirmation or receipt["run_id"] != job["id"] or receipt["plan_key"] != value["plan_key"]:
        graph.conflict("DAG accepted request link changed")
    if authorize:
        frozen = store.frozen_contract(c, job)
        if fingerprint(frozen.model_dump()) != value["contract_fingerprint"]:
            graph.conflict("DAG Run contract changed")
        current = load_plan(store, c, job["principal_id"], job["project_id"], value["app_id"], value["plan_key"], limits)
        if current != value["plan"] or current["plan_fingerprint"] != confirmation.expected_plan_fingerprint:
            graph.conflict("DAG plan changed after confirmation")
    return value


def resolve(step, plan, outputs):
    args = {}
    data = {x["binding_id"]: x["resource_ref"] for x in plan["definition"]["manifest"]["data_bindings"]}
    for key, source in step["inputs"].items():
        args[key] = (plan["input"][source["field"]] if source["source"] == "input" else
                     data[source["ref"]] if source["source"] == "data" else
                     outputs[source["ref"]][source["field"]])
    return args


def oracle(content, value):
    """Independent reader and rational arithmetic; never uses the product aggregator."""
    try:
        rows = list(csv.reader(io.StringIO(content)))
        index = rows[0].index(value["column"])
        total = sum((Fraction(r[index]) for r in rows[1:]), Fraction())
        valid = len(rows) - 1 == value["count"] and Fraction(value["sum"]) == total
    except (ValueError, IndexError, ZeroDivisionError):
        valid = False
    if not valid:
        raise DomainError("VERIFICATION_FAILED", "Independent exact CSV sum failed")


def expected(step, args, source):
    if step == "preview":
        guide = csv_column_options(source["content"])
        if source["format"] != "csv" or guide["error"]:
            raise DomainError("INVALID_INPUT", "Bounded valid CSV preview required")
        return source
    if step == "aggregate":
        value = aggregate_csv_content(source["content"], args["resource_id"], args["column"])
        oracle(source["content"], value)
        return value
    return report.render(args)


def receipts(store, c, job, plan, source):
    ops = c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings().all()
    by_step = {op["call_id"]: op for op in ops}
    if len(by_step) != len(ops) or set(by_step) - set(STEPS):
        graph.conflict("Unknown/duplicate DAG operation")
    outputs: dict[str, dict] = {}
    proved: list[dict] = []
    for step, action in zip(plan["definition"]["manifest"]["workflow"], plan["definition"]["actions"], strict=True):
        op = by_step.get(step["step_id"])
        if not op:
            if any(s in by_step for s in STEPS[len(proved) + 1:]):
                graph.conflict("Missing predecessor receipt")
            break
        args = resolve(step, plan, outputs)
        intent = dict(tool=action["executor"]["ref"], args=args, plan_fingerprint=plan["plan_fingerprint"],
                      predecessor_receipts=[fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]])
        saved = c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])).scalar()
        if saved != intent or op["fingerprint"] != fingerprint(intent) or op["tool_ref"] != intent["tool"]:
            graph.conflict("DAG operation input binding changed")
        if op["status"] != "VERIFIED":
            raise DomainError("OUTCOME_UNKNOWN", "Unknown DAG operation requires reconciliation")
        receipt = op["receipt"]
        wanted = expected(step["step_id"], args, source)
        validate_value(action["output_schema"], wanted)
        check = dict(operation_id=op["id"], step_id=step["step_id"], status="VERIFIED", data=wanted,
                     plan_fingerprint=plan["plan_fingerprint"], action_revision=action["revision"],
                     input_fingerprint=fingerprint(args), output_fingerprint=fingerprint(wanted),
                     predecessor_receipts=intent["predecessor_receipts"], source_hash=plan["source_hash"],
                     artifact_refs=[], check_results=[dict(check="receipt.readback.v1", status="PASS")],
                     actual_reads=[] if step["step_id"] == "report" else [dict(resource_id=source["resource_id"],
                                 source_hash=source["hash"], tool_ref=intent["tool"])])
        if receipt != check:
            raise DomainError("VERIFICATION_FAILED", "Actual DAG receipt differs from independent readback")
        outputs[step["step_id"]] = wanted
        proved.append(check)
    return outputs, proved


def read_source(store, c, job):
    source = authorized_read(store, c, job["principal_id"], job["runtime_id"], job["project_id"],
                             "resource.read", {"resource_id": job["resource_refs"][0]})
    # Even a pure report depends on current authorization for its source lineage.
    store.authorize(c, job["principal_id"], job["runtime_id"], job["project_id"], source["resource_id"], "data.aggregate_csv")
    return source


def transition(store, c, job, state, error=None, result=None):
    c.execute(update(runs).where(runs.c.id == job["id"]).values(status=state, error=error,
               result=result, lease_until=0, version=job["version"] + 1))
    store.event(c, job["id"], "STATE", dict(status=state, error=error))


@graph.controlled
def advance(worker, run):
    """One bounded local step and its receipt commit atomically under existing fencing."""
    store = worker.store
    with store.tx() as c:
        job = lock_live(store, c, run)
        limits = Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields})
        bound = binding(store, c, job, limits)
        if job["status"] != "RUNNING" or worker.stop.is_set():
            transition(store, c, job, stop_state(job, store.has_unknown(c, job["id"])))
            return False
        if store.has_unknown(c, job["id"]):
            raise DomainError("OUTCOME_UNKNOWN")
        if time.time() - job["created_at"] > min(limits.run_seconds, bound["plan"]["definition"]["manifest"]["runtime_limits"]["run_seconds"]):
            raise DomainError("BUDGET_EXHAUSTED")
        source = read_source(store, c, job)
        plan = bound["plan"]
        if source["hash"] != plan["source_hash"]:
            graph.conflict("CSV changed between steps")
        outputs, proved = receipts(store, c, job, plan, source)
        if job["context"]["tools"] != len(proved):
            graph.conflict("Step counter differs from verified receipt ledger")
        if len(proved) == 3:
            result = dict(namespace=PLAN, output=outputs["report"], plan_fingerprint=plan["plan_fingerprint"],
                          steps=proved, model_requests=0, business_writes=0, semantic_status="UNKNOWN", owner_acceptance="PENDING")
            transition(store, c, job, "SUCCEEDED", result=result)
            return False
        if len(proved) >= min(limits.max_tools, 3):
            raise DomainError("BUDGET_EXHAUSTED", "Step budget/counter mismatch")
        index = len(proved)
        step, action = plan["definition"]["manifest"]["workflow"][index], plan["definition"]["actions"][index]
        args = resolve(step, plan, outputs)
        from .contracts import validate_action

        validate_action_input(validate_action(json.dumps(action)), args)
        # Registered local implementations only. The bounded step is one short
        # transaction, just like existing local-tool dispatch; no in-flight I/O.
        oid = new_id("op")
        intent = dict(tool=action["executor"]["ref"], args=args, plan_fingerprint=plan["plan_fingerprint"],
                      predecessor_receipts=[fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]])
        c.execute(insert(operations).values(id=oid, run_id=job["id"], call_id=step["step_id"],
                   fingerprint=fingerprint(intent), tool_ref=intent["tool"], status="PREPARED"))
        c.execute(insert(operation_intents).values(operation_id=oid, request=intent))
        if step["step_id"] == "aggregate":
            value = authorized_read(store, c, job["principal_id"], job["runtime_id"], job["project_id"],
                                    "data.aggregate_csv", args)
            oracle(source["content"], value)
        else:
            value = expected(step["step_id"], args, source)
        validate_value(action["output_schema"], value)
        # A lease/deadline can expire during local parsing; don't commit an old
        # ownership interval merely because it was valid at transaction entry.
        store.guard(c, job["id"], run["fence"])
        if time.time() - job["created_at"] > min(limits.run_seconds, plan["definition"]["manifest"]["runtime_limits"]["run_seconds"]):
            raise DomainError("BUDGET_EXHAUSTED")
        # Reconstruct/verify the exact receipt using the same cold readback contract.
        receipt = dict(operation_id=oid, step_id=step["step_id"], status="VERIFIED", data=value,
                       plan_fingerprint=plan["plan_fingerprint"], action_revision=action["revision"],
                       input_fingerprint=fingerprint(args), output_fingerprint=fingerprint(value),
                       predecessor_receipts=intent["predecessor_receipts"], source_hash=plan["source_hash"],
                       artifact_refs=[], check_results=[dict(check="receipt.readback.v1", status="PASS")],
                       actual_reads=[] if step["step_id"] == "report" else [dict(resource_id=source["resource_id"],
                                    source_hash=source["hash"], tool_ref=intent["tool"])])
        c.execute(update(operations).where(operations.c.id == oid).values(status="VERIFIED", receipt=receipt))
        c.execute(update(runs).where(runs.c.id == job["id"]).values(context={**job["context"], "tools": index + 1}))
        store.event(c, job["id"], "CSV_DAG_STEP_VERIFIED", dict(step_id=step["step_id"], operation_id=oid, fence=run["fence"], receipt_fingerprint=fingerprint(receipt)))
        return True


def process_job(worker, run):
    stopped = threading.Event()

    def beat():
        while not stopped.wait(worker.s.lease_seconds / 3):
            try:
                worker.store.heartbeat(worker.id, run["id"], run["fence"], worker.s.lease_seconds)
            except Exception:
                stopped.set()

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        while advance(worker, run):
            pass
    except DomainError as exc:
        with worker.store.tx() as c:
            worker.store.lock_project(c, run["principal_id"], run["project_id"])
            job = row(c, run["principal_id"], run["id"])
            # Frozen source failure must be recordable, but never by a stale worker.
            if job["fence"] != run["fence"] or job["lease_until"] <= time.time() or job["status"] not in {"RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}:
                return
            state = (stop_state(job, worker.store.has_unknown(c, job["id"])) if job["status"] != "RUNNING" else
                     "WAITING_RESOURCE" if exc.code in {"GRANT_REVOKED", "PERMISSION_DENIED", "RESOURCE_UNAVAILABLE", "OUTCOME_UNKNOWN", "VERSION_CONFLICT"} else "FAILED")
            completed = set(c.execute(select(operations.c.call_id).where(
                operations.c.run_id == job["id"], operations.c.status == "VERIFIED")).scalars())
            failed = next((s for s in STEPS if s not in completed), "final_check")
            worker.store.event(c, job["id"], "CSV_DAG_STEP_BLOCKED", dict(step_id=failed, error=exc.public()))
            transition(worker.store, c, job, state, exc.public())
    finally:
        stopped.set()
        thread.join(timeout=2)


@graph.controlled
def inspect_job(store, user, rid, limits):
    with store.tx() as c:
        owner_lock(store, c, user, rid)
        job = row(c, user, rid)
        limits = limits or store.frozen_contract(c, job).limits
        bound = binding(store, c, job, limits)
        source = read_source(store, c, job)
        outputs, proved = receipts(store, c, job, bound["plan"], source)
        if job["context"]["tools"] != len(proved):
            graph.conflict("Step counter no longer matches receipts")
        if job["status"] == "SUCCEEDED" and (len(proved) != 3 or job["result"] != dict(
                namespace=PLAN, output=outputs["report"], plan_fingerprint=bound["plan"]["plan_fingerprint"],
                steps=proved, model_requests=0, business_writes=0, semantic_status="UNKNOWN", owner_acceptance="PENDING")):
            raise DomainError("VERIFICATION_FAILED", "Final result lacks all three checked receipts")
        return dict(namespace=PLAN, id=rid, app_id=bound["app_id"], project_id=job["project_id"],
                    status=job["status"], version=job["version"], result=job["result"], error=job["error"],
                    plan_fingerprint=bound["plan"]["plan_fingerprint"], steps=proved,
                    pending_steps=list(STEPS[len(proved):]), model_requests=0, business_writes=0,
                    publishable=False, formal_publication_enabled=False, semantic_status="UNKNOWN", owner_acceptance="PENDING")


@graph.controlled
def status(store, user, rid):
    """Own-run control metadata only; never returns protected/stale proof or cells."""
    with store.tx() as c:
        owner_lock(store, c, user, rid)
        job = row(c, user, rid)
        binding(store, c, job, None, authorize=False)
        return dict(namespace=PLAN, id=rid, status=job["status"], version=job["version"],
                    proof_status="NOT_VALIDATED", error=job["error"], result=None, steps=[])


@graph.controlled
def history(store, user, pid, aid, limits):
    with store.tx() as c:
        graph.current(store, c, user, pid, aid, limits)
        keys = c.execute(select(delivery_graph_requests.c.request_key).where(
            delivery_graph_requests.c.app_id == aid, delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.kind == "csv_dag_plan").order_by(delivery_graph_requests.c.request_key)).scalars().all()
        items, expired = [], []
        for key in keys:
            try:
                plan = load_plan(store, c, user, pid, aid, key, limits)
            except DomainError as exc:
                if exc.code != "VERSION_CONFLICT":
                    raise
                expired.append(dict(request_key=key, state="INVALIDATED"))
                continue
            accepted = []
            run_keys = c.execute(select(delivery_graph_requests.c.request_key).where(
                delivery_graph_requests.c.app_id == aid, delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind == "csv_dag_run").order_by(delivery_graph_requests.c.request_key)).scalars().all()
            for run_key in run_keys:
                _, receipt = read_pair(c, user, aid, "csv_dag_run", run_key, RunInput)
                if receipt["plan_key"] == key:
                    job = row(c, user, receipt["run_id"])
                    binding(store, c, job, limits)
                    accepted.append(dict(id=job["id"], status=job["status"], version=job["version"], proof_status="NOT_VALIDATED"))
            items.append(dict(plan=plan, runs=accepted))
        return dict(namespace=PLAN, app_id=aid, project_id=pid, items=items, invalidated=expired)


def command_job(store, user, rid, command, version):
    # Stop remains available after source/authority invalidation; resume requires
    # the exact frozen confirmation and all previously verified receipts.
    with store.tx() as c:
        owner_lock(store, c, user, rid)
        job = row(c, user, rid)
        bound = binding(store, c, job, None, authorize=False)
        if job["version"] != version:
            graph.conflict("DAG command version changed")
        state, unknown = job["status"], store.has_unknown(c, rid)
        if command == "resume":
            if state not in {"PAUSED", "WAITING_RESOURCE"} or job["cancel_intent"]:
                graph.conflict("Resume unavailable")
            if unknown:
                raise DomainError("OUTCOME_UNKNOWN")
            frozen = store.frozen_contract(c, job)
            binding(store, c, job, frozen.limits)
            receipts(store, c, job, bound["plan"], read_source(store, c, job))
            if time.time() - job["created_at"] > frozen.limits.run_seconds:
                raise DomainError("BUDGET_EXHAUSTED")
            state = "QUEUED"
        elif command == "pause" and state in {"QUEUED", "RUNNING"}:
            state = "PAUSED" if state == "QUEUED" else "PAUSE_REQUESTED"
        elif command == "cancel" and state in {"QUEUED", "RUNNING", "PAUSED", "PAUSE_REQUESTED", "WAITING_RESOURCE", "RECONCILING"}:
            state = "RECONCILING" if unknown else "CANCEL_REQUESTED" if state == "RUNNING" else "CANCELLED"
        else:
            graph.conflict("DAG command unavailable")
        c.execute(update(runs).where(runs.c.id == rid).values(status=state, version=version + 1,
                    cancel_intent=job["cancel_intent"] or command == "cancel"))
        store.event(c, rid, "COMMAND", dict(command=command, status=state))
        return state


def mount(app, store, settings, principal, limits):
    base = "/api/projects/{pid}/apps/{aid}/csv-dag"
    dependency = Depends(principal)

    @app.post(base, status_code=201)
    def save(pid: str, aid: str, body: PlanInput, user=dependency):
        if settings.mode != "mock" or settings.live_enabled:
            raise DomainError("PERMISSION_DENIED", "Offline CSV DAG only")
        return propose(store, user, pid, aid, body, limits)

    @app.get(base)
    def saved(pid: str, aid: str, user=dependency):
        return history(store, user, pid, aid, limits)

    @app.get(base + "/{key}")
    def get(pid: str, aid: str, key: str, user=dependency):
        with store.tx() as c:
            return load_plan(store, c, user, pid, aid, key, limits)

    @app.post(base + "/{key}/runs", status_code=202)
    def start(pid: str, aid: str, key: str, body: RunInput, user=dependency):
        if settings.mode != "mock" or settings.live_enabled:
            raise DomainError("PERMISSION_DENIED", "Offline CSV DAG only")
        return enqueue(store, user, pid, aid, key, body, limits)

    @app.get("/api/csv-dag/runs/{rid}")
    def inspect(rid: str, user=dependency):
        return inspect_job(store, user, rid, limits)

    @app.get("/api/csv-dag/runs/{rid}/status")
    def controls(rid: str, user=dependency):
        return status(store, user, rid)
