"""Fixed offline three-step adapter on the existing Run/Operation/Worker ledger.

Immutable engineering plans extend an existing CSV draft without replacing it.
No generic interpreter, model-generated plan, identity, Grant, Release or artifact.
"""

import copy
import csv
import io
import json
import math
import threading
import time
from fractions import Fraction
from typing import Literal

from fastapi import Depends
from pydantic import Field, field_validator
from sqlalchemy import insert, select, update

from . import csv_reports as report
from . import delivery_graph_apps as graph
from .app_jobs import lock_live, stop_state
from .column_patches import KeyInput, read_pair, require_capacity
from .contracts import (
    BranchCondition,
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
WIRING_VERSION = "csv.wiring.v1"
# Semantic ports, not a string-to-string casting rule. Everything else is pinned.
PORTS = {
    ("aggregate", "resource_id"): ("resource_id", [
        dict(source="step", ref="preview", field="resource_id"),
        dict(source="data", ref="source", field="resource_id")]),
    ("report", "resource_id"): ("resource_id", [
        dict(source="step", ref="aggregate", field="resource_id"),
        dict(source="step", ref="preview", field="resource_id")]),
    ("report", "source_hash"): ("source_hash", [
        dict(source="step", ref="aggregate", field="source_hash"),
        dict(source="step", ref="preview", field="hash")]),
}


class SafeWire(Strict):
    @field_validator("*", mode="before")
    @classmethod
    def valid_unicode(cls, value):
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise DomainError("INVALID_INPUT", "Invalid wiring Unicode") from None
        return value


class PortSource(SafeWire):
    source: Literal["step", "data"]
    ref: Literal["source", "preview", "aggregate"]
    field: Literal["resource_id", "hash", "source_hash"]


class WirePatch(SafeWire):
    step_id: Literal["aggregate", "report"]
    port: Literal["resource_id", "source_hash"]
    source: PortSource


def allowed_ports():
    return [dict(step_id=step, port=port, semantic_type=role, sources=copy.deepcopy(sources))
            for (step, port), (role, sources) in PORTS.items()]


def apply_wiring(manifest, patches):
    seen = set()
    steps = {s["step_id"]: s for s in manifest["workflow"]}
    for patch in patches or []:
        key = (patch.step_id, patch.port)
        value = patch.source.model_dump()
        if key in seen or key not in PORTS or value not in PORTS[key][1]:
            raise DomainError("INVALID_INPUT", "Unknown, duplicate or wrong semantic wiring port")
        seen.add(key)
        steps[patch.step_id]["inputs"][patch.port] = value
    # Always keep the preview validation barrier, even with a direct data binding.
    steps["aggregate"]["depends_on"] = ["preview"]
    required = {"aggregate"} | {v["ref"] for v in steps["report"]["inputs"].values()
                              if v["source"] == "step"}
    steps["report"]["depends_on"] = [s for s in STEPS if s in required]
    return dict(version=WIRING_VERSION,
                inputs={s: copy.deepcopy(steps[s]["inputs"]) for s in STEPS},
                depends_on={s: steps[s]["depends_on"][:] for s in STEPS})


class BranchPatch(Strict):
    step_id: Literal["aggregate", "report"]
    when: BranchCondition


class BranchInputs(Strict):
    include_report: bool | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("include_report", mode="before")
    @classmethod
    def strict_optional_bool(cls, value):
        if type(value) is not bool:
            raise DomainError("INVALID_INPUT", "include_report must be a JSON boolean or omitted")
        return value


class PlanInput(KeyInput):
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    column: str = Field(min_length=1, max_length=200)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    branch_patch: list[BranchPatch] | None = Field(default=None, min_length=1, max_length=2,
        exclude_if=lambda value: value is None)
    # Keep legacy request dumps byte-compatible when the field was absent.
    wiring_patch: list[WirePatch] | None = Field(default=None, max_length=3,
                                               exclude_if=lambda value: value is None)


class RunInput(KeyInput):
    branch_inputs: BranchInputs | None = Field(default=None, exclude_if=lambda value: value is None)
    expected_plan_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["CONFIRM_EXACT_OFFLINE_CSV_DAG"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


def canonical(candidate, column, limits, patches=None, branches=None):
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
    apply_wiring(manifest, patches)
    if branches is not None:
        manifest["input_schema"]["properties"]["include_report"] = {"type": "boolean"}
        seen = set()
        for branch in branches:
            if branch.step_id in seen:
                raise DomainError("INVALID_INPUT", "Duplicate branch target")
            seen.add(branch.step_id)
            next(s for s in manifest["workflow"] if s["step_id"] == branch.step_id)["when"] = branch.when.model_dump(exclude_none=True)
    return dict(manifest=manifest, actions=actions)


def compile_plan(candidate, column, limits, patches=None, branches=None):
    expected = canonical(candidate, column, limits, patches, branches)
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
    template, _, checked = compile_plan(draft["candidate"], body.column, limits, body.wiring_patch, body.branch_patch)
    value = dict(namespace=PLAN, project_id=pid, app_id=aid, runtime_id=draft["runtime_id"],
                 request_key=body.request_key, candidate_fingerprint=draft["fingerprint"],
                 graph_fingerprint=saved["graph"]["graph_fingerprint"],
                 graph_revision=saved["graph_revision"], authorization_fingerprint=saved["authorization_fingerprint"],
                 source_hash=draft["candidate"]["source_hash"], input={"column": body.column},
                 definition=template, preflight=checked, state="DRAFT_PLAN", model_generated=False,
                 model_requests=0, business_writes=0, publishable=False, formal_publication_enabled=False,
                 semantic_status="UNKNOWN", owner_acceptance="PENDING")
    if body.branch_patch is not None:
        value["branch_semantics"] = "typed-conditions.v1"
    if body.wiring_patch is not None:
        value["wiring"] = apply_wiring(copy.deepcopy(template["manifest"]), body.wiring_patch)
    return {**value, "plan_fingerprint": fingerprint(value)}


def load_plan(store, c, user, pid, aid, key, limits):
    store.lock_project(c, user, pid)
    body, answer = read_pair(c, user, aid, "csv_dag_plan", key, PlanInput)
    if fingerprint(build(store, c, user, pid, aid, body, limits)) != fingerprint(answer):
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
        inputs = execution_inputs(plan, body)
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
        if "branch_semantics" in plan:
            accepted["inputs"] = inputs
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


def check_quantities(job, *, context=True):
    if (any(type(job[k]) is not int or job[k] < low for k, low in (("version", 1), ("fence", 0)))
            or any(type(job[k]) not in {int, float} or not math.isfinite(job[k])
                   for k in ("created_at", "lease_until"))):
        graph.conflict("Invalid persisted Run quantity or time")
    if not context:
        return
    ctx = job["context"]
    if (not isinstance(ctx, dict)
            or set(ctx) != {"kind", "messages", "requests", "tools", "repairs", "reserved_tokens"}
            or ctx["messages"] != [] or any(type(ctx[k]) is not int for k in ("requests", "tools", "repairs", "reserved_tokens"))
            or any(ctx[k] != 0 for k in ("requests", "repairs", "reserved_tokens"))
            or not 0 <= ctx["tools"] <= 3):
        graph.conflict("Fixed DAG has only three local operations and zero model usage")


def row(c, user, rid):
    job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user).with_for_update()).mappings().first()
    if not job:
        raise DomainError("PERMISSION_DENIED")
    check_quantities(job, context=False)
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
    check_quantities(job)
    if (job["context"].get("kind") != KIND or value["run_id"] != job["id"]
            or value["principal_id"] != job["principal_id"] or value["project_id"] != job["project_id"]
            or value["runtime_id"] != job["runtime_id"]):
        graph.conflict("DAG Run identity changed")
    confirmation = RunInput.model_validate(value["confirmation"])
    req, receipt = read_pair(c, job["principal_id"], value["app_id"], "csv_dag_run", confirmation.request_key, RunInput)
    expected_receipt = dict(namespace=PLAN, run_id=job["id"], plan_key=value["plan_key"],
                            plan_fingerprint=value["plan"]["plan_fingerprint"], status="QUEUED", version=1)
    if req != confirmation or fingerprint(receipt) != fingerprint(expected_receipt):
        graph.conflict("DAG accepted request link changed")
    if authorize:
        frozen = store.frozen_contract(c, job)
        if fingerprint(frozen.model_dump()) != value["contract_fingerprint"]:
            graph.conflict("DAG Run contract changed")
        current = load_plan(store, c, job["principal_id"], job["project_id"], value["app_id"], value["plan_key"], limits)
        if fingerprint(current) != fingerprint(value["plan"]) or current["plan_fingerprint"] != confirmation.expected_plan_fingerprint:
            graph.conflict("DAG plan changed after confirmation")
    if "branch_semantics" in value["plan"]:
        if fingerprint(value.get("inputs")) != fingerprint(execution_inputs(value["plan"], confirmation)):
            graph.conflict("Frozen branch inputs changed")
    elif confirmation.branch_inputs is not None or "inputs" in value:
        graph.conflict("Unexpected legacy branch inputs")
    return value


def execution_inputs(plan, confirmation):
    inputs = copy.deepcopy(plan["input"])
    if confirmation.branch_inputs is not None:
        if "branch_semantics" not in plan:
            raise DomainError("INVALID_INPUT", "Branch inputs require a conditional plan")
        inputs.update(confirmation.branch_inputs.model_dump())
    validate_value(plan["definition"]["manifest"]["input_schema"], inputs)
    return inputs


def decision(plan, step, inputs, outputs, proved):
    if "branch_semantics" not in plan:
        return {}
    parents = [p for p in proved if p["step_id"] in step["depends_on"]]
    skipped = [p["step_id"] for p in parents if p["status"] == "SKIPPED"]
    reason, passed, observed = "UNCONDITIONAL", True, {"evaluated": False}
    condition = step.get("when")
    if skipped:
        reason, passed = "DEPENDENCY_SKIPPED", False
    elif condition is not None:
        src = condition["source"]
        values = inputs if src["source"] == "input" else outputs[src["ref"]]
        present = src["field"] in values
        actual = values.get(src["field"])
        observed = dict(evaluated=True, present=present)
        if present:
            observed["value"] = actual
        if condition["op"] == "exists":
            passed = present
        else:
            if not present:
                raise DomainError("INVALID_INPUT", "Condition value is missing")
            choices = condition["value"] if condition["op"] == "in" else [condition["value"]]
            passed = any(type(actual) is type(value) and fingerprint(actual) == fingerprint(value) for value in choices)
        reason = "CONDITION_TRUE" if passed else "CONDITION_FALSE"
    return dict(branch_decision=dict(version="typed-conditions.v1", condition=copy.deepcopy(condition),
        observation=observed, passed=passed, reason=reason, skipped_predecessors=skipped,
        inputs_fingerprint=fingerprint(inputs)))


def skip_receipt(plan, step, action, proof, parents):
    return dict(step_id=step["step_id"], status="SKIPPED", data=None,
        plan_fingerprint=plan["plan_fingerprint"], source_hash=plan["source_hash"],
        action_revision=action["revision"], predecessor_receipts=parents,
        artifact_refs=[], actual_reads=[], **proof)


def final_result(plan, outputs, proved):
    result = dict(namespace=PLAN, output=outputs.get("report"), plan_fingerprint=plan["plan_fingerprint"],
        steps=proved, model_requests=0, business_writes=0, semantic_status="UNKNOWN", owner_acceptance="PENDING")
    if "branch_semantics" in plan:
        result["output_status"] = "PRODUCED" if "report" in outputs else "SKIPPED"
    return result


def executed_count(proved):
    return sum(p["status"] == "VERIFIED" for p in proved)


def resolve(step, plan, outputs):
    args = {}
    data = {x["binding_id"]: x["resource_ref"] for x in plan["definition"]["manifest"]["data_bindings"]}
    for key, source in step["inputs"].items():
        args[key] = (plan["input"][source["field"]] if source["source"] == "input" else
                     data[source["ref"]] if source["source"] == "data" else
                     outputs[source["ref"]][source["field"]])
    return args


def wire_proof(plan, step):
    return {"input_sources": copy.deepcopy(step["inputs"])} if "wiring" in plan else {}


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


def receipts(store, c, job, plan, source, inputs=None):
    ops = c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings().all()
    by_step = {op["call_id"]: op for op in ops}
    if len(by_step) != len(ops) or set(by_step) - set(STEPS):
        graph.conflict("Unknown/duplicate DAG operation")
    skips = c.execute(select(events.c.data).where(events.c.run_id == job["id"], events.c.kind == "CSV_DAG_STEP_SKIPPED")).scalars().all()
    by_skip = {s["step_id"]: s for s in skips}
    if len(by_skip) != len(skips) or set(by_skip) - set(STEPS) or set(by_skip) & set(by_step) or (by_skip and "branch_semantics" not in plan):
        graph.conflict("Unknown or duplicate branch decision")
    inputs = inputs if inputs is not None else plan["input"]
    actual_plan = {**plan, "input": inputs}
    outputs: dict[str, dict] = {}
    proved: list[dict] = []
    for step, action in zip(plan["definition"]["manifest"]["workflow"], plan["definition"]["actions"], strict=True):
        op = by_step.get(step["step_id"])
        if not op and step["step_id"] not in by_skip:
            if any(s in set(by_step) | set(by_skip) for s in STEPS[len(proved) + 1:]):
                graph.conflict("Missing predecessor receipt")
            break
        proof = decision(plan, step, inputs, outputs, proved)
        parents = [fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]]
        if proof and not proof["branch_decision"]["passed"]:
            check = skip_receipt(plan, step, action, proof, parents)
            if op or fingerprint(by_skip.get(step["step_id"])) != fingerprint(check):
                graph.conflict("Persisted skipped branch changed")
            proved.append(check)
            continue
        if step["step_id"] in by_skip:
            graph.conflict("Executed branch replaced by skip")
        args = resolve(step, actual_plan, outputs)
        intent = dict(tool=action["executor"]["ref"], args=args, plan_fingerprint=plan["plan_fingerprint"],
                      predecessor_receipts=[fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]],
                      **wire_proof(plan, step), **proof)
        if op is None:
            graph.conflict("Missing executed branch operation")
        saved = c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])).scalar()
        if fingerprint(saved) != fingerprint(intent) or op["fingerprint"] != fingerprint(intent) or op["tool_ref"] != intent["tool"]:
            graph.conflict("DAG operation input binding changed")
        if op["status"] != "VERIFIED":
            raise DomainError("OUTCOME_UNKNOWN", "Unknown DAG operation requires reconciliation")
        receipt = op["receipt"]
        # Validate the persisted output, not merely its recomputed counterpart.
        # Python equality would otherwise accept True==1 and 1.0==1.
        validate_value(action["output_schema"], receipt["data"])
        wanted = expected(step["step_id"], args, source)
        validate_value(action["output_schema"], wanted)
        check = dict(operation_id=op["id"], step_id=step["step_id"], status="VERIFIED", data=wanted,
                     plan_fingerprint=plan["plan_fingerprint"], action_revision=action["revision"],
                     input_fingerprint=fingerprint(args), output_fingerprint=fingerprint(wanted),
                     predecessor_receipts=intent["predecessor_receipts"], source_hash=plan["source_hash"],
                     artifact_refs=[], check_results=[dict(check="receipt.readback.v1", status="PASS")],
                     actual_reads=[] if step["step_id"] == "report" else [dict(resource_id=source["resource_id"],
                                 source_hash=source["hash"], tool_ref=intent["tool"])],
                     **wire_proof(plan, step), **proof)
        if fingerprint(receipt) != fingerprint(check):
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


def commit_guard(worker, c, run, plan, *, tool_delta=0):
    """Fresh ownership and effective budget check immediately before a commit."""
    job = worker.store.guard(c, run["id"], run["fence"])
    check_quantities(job)
    current = Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields})
    frozen = worker.store.frozen_contract(c, job).limits
    declared = Limits(**plan["definition"]["manifest"]["runtime_limits"])
    seconds = min(current.run_seconds, frozen.run_seconds, declared.run_seconds)
    counts = {"max_requests": "requests", "max_tools": "tools", "max_repairs": "repairs",
              "max_total_tokens": "reserved_tokens"}
    if (time.time() >= job["created_at"] + seconds or any(
            job["context"][counter] + (tool_delta if counter == "tools" else 0) > min(getattr(current, cap), getattr(frozen, cap), getattr(declared, cap))
            for cap, counter in counts.items())):
        raise DomainError("BUDGET_EXHAUSTED", "Effective budget expired before commit")
    return job


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
        outputs, proved = receipts(store, c, job, plan, source, bound.get("inputs"))
        if job["context"]["tools"] != executed_count(proved):
            graph.conflict("Step counter differs from verified receipt ledger")
        if len(proved) == 3:
            result = final_result(plan, outputs, proved)
            live = commit_guard(worker, c, run, plan)
            if live["status"] != "RUNNING" or worker.stop.is_set():
                transition(store, c, live, stop_state(live, store.has_unknown(c, job["id"])))
            else:
                state = "PARTIAL" if result.get("output_status") == "SKIPPED" else "SUCCEEDED"
                transition(store, c, live, state, result=result)
            return False
        index = len(proved)
        step, action = plan["definition"]["manifest"]["workflow"][index], plan["definition"]["actions"][index]
        inputs = bound.get("inputs", plan["input"])
        proof = decision(plan, step, inputs, outputs, proved)
        if proof and not proof["branch_decision"]["passed"]:
            receipt = skip_receipt(plan, step, action, proof,
                [fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]])
            commit_guard(worker, c, run, plan)
            store.event(c, job["id"], "CSV_DAG_STEP_SKIPPED", receipt)
            return True
        if executed_count(proved) >= min(limits.max_tools, 3):
            raise DomainError("BUDGET_EXHAUSTED", "Executed tool budget exhausted")
        args = resolve(step, {**plan, "input": inputs}, outputs)
        from .contracts import validate_action

        validate_action_input(validate_action(json.dumps(action)), args)
        # Registered local implementations only. The bounded step is one short
        # transaction, just like existing local-tool dispatch; no in-flight I/O.
        oid = new_id("op")
        intent = dict(tool=action["executor"]["ref"], args=args, plan_fingerprint=plan["plan_fingerprint"],
                      predecessor_receipts=[fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]],
                      **wire_proof(plan, step), **proof)
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
        commit_guard(worker, c, run, plan, tool_delta=1)
        # Reconstruct/verify the exact receipt using the same cold readback contract.
        receipt = dict(operation_id=oid, step_id=step["step_id"], status="VERIFIED", data=value,
                       plan_fingerprint=plan["plan_fingerprint"], action_revision=action["revision"],
                       input_fingerprint=fingerprint(args), output_fingerprint=fingerprint(value),
                       predecessor_receipts=intent["predecessor_receipts"], source_hash=plan["source_hash"],
                       artifact_refs=[], check_results=[dict(check="receipt.readback.v1", status="PASS")],
                       actual_reads=[] if step["step_id"] == "report" else [dict(resource_id=source["resource_id"],
                                    source_hash=source["hash"], tool_ref=intent["tool"])],
                       **wire_proof(plan, step), **proof)
        c.execute(update(operations).where(operations.c.id == oid).values(status="VERIFIED", receipt=receipt))
        c.execute(update(runs).where(runs.c.id == job["id"]).values(context={**job["context"], "tools": executed_count(proved) + 1}))
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
        outputs, proved = receipts(store, c, job, bound["plan"], source, bound.get("inputs"))
        if job["context"]["tools"] != executed_count(proved):
            graph.conflict("Step counter no longer matches receipts")
        terminal = job["status"] == "SUCCEEDED" or ("branch_semantics" in bound["plan"] and job["status"] == "PARTIAL")
        wanted = final_result(bound["plan"], outputs, proved)
        if terminal and (len(proved) != 3 or fingerprint(job["result"]) != fingerprint(wanted)
                or job["status"] != ("PARTIAL" if wanted.get("output_status") == "SKIPPED" else "SUCCEEDED")):
            raise DomainError("VERIFICATION_FAILED", "Final result lacks all three checked receipts")
        answer = dict(namespace=PLAN, id=rid, app_id=bound["app_id"], project_id=job["project_id"],
                    status=job["status"], version=job["version"], result=job["result"], error=job["error"],
                    plan_fingerprint=bound["plan"]["plan_fingerprint"], steps=proved,
                    pending_steps=list(STEPS[len(proved):]), model_requests=0, business_writes=0,
                    publishable=False, formal_publication_enabled=False, semantic_status="UNKNOWN", owner_acceptance="PENDING")
        if "branch_semantics" in bound["plan"]:
            answer["inputs"] = bound["inputs"]
            answer["confirmation"] = bound["confirmation"]
        return answer


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
            receipts(store, c, job, bound["plan"], read_source(store, c, job), bound.get("inputs"))
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

    @app.get(base + "/options/wiring")
    def options(pid: str, aid: str, user=dependency):
        with store.tx() as c:
            saved = graph.current(store, c, user, pid, aid, limits)
            draft, _, action, _, _, _ = graph.load_family(store, c, user, pid, aid, limits)
            if action.executor.kind != "registered_tool" or action.executor.ref != "data.aggregate_csv":
                raise DomainError("UNSUPPORTED_CAPABILITY")
            value = dict(version=WIRING_VERSION, app_id=aid, project_id=pid,
                         candidate_fingerprint=draft["fingerprint"],
                         graph_fingerprint=saved["graph"]["graph_fingerprint"],
                         ports=allowed_ports(), fixed_steps=list(STEPS),
                         barrier=["preview", "aggregate"], editable_dependencies=False,
                         model_requests=0, business_writes=0, publishable=False)
            return {**value, "options_fingerprint": fingerprint(value)}

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
