"""Closed four-step TXT/MD task, actual receipts and exact-source extraction.

This adapter does not register an operator or extend the global workflow DSL.
Only read -> two independent literal lookups -> conditional citation report is
accepted. Goal, authorization, bytes, budget and ownership remain live gates.
"""

import copy
import json
import threading
import time
from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select, update

from . import delivery_graph_apps as graph
from . import text_logic_reuse as seals
from .apps import object_schema
from .contracts import ActionSpec, AppManifest, Limits, Strict, schema_check, validate_value
from .csv_dag import decision, resolve, skip_receipt
from .db import (
    app_drafts,
    delivery_graph_requests,
    events,
    fingerprint,
    goal_card_versions,
    goal_cards,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_run_bindings,
    new_id,
    operation_intents,
    operations,
    principals,
    run_contracts,
    runs,
    task_extractions,
)
from .errors import DomainError
from .goals import GoalCardInput
from .tools import authorized_read

VERSION = "closed-text-four-step.v1"
ORIGIN = "text_four_step_origin"
META = "text_four_step_scope"
CREATE = "text_four_step_create"
KIND = "text_four_step_source.v1"
PROOF = "completed_text_four_step.v1"
REPORT = "text.citation_report"
CHECK = "text.four_step_readback.v1"
STEPS = ["read", "lookup_a", "lookup_b", "report"]
BOUND = dict(max_bytes=1536, max_lines=32, max_citations=8, max_term_length=80)


class CreateInput(Strict):
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_goal_version: int = Field(strict=True, ge=1)
    expected_goal_fingerprint: str = Field(pattern=graph.HASH)
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=graph.HASH)
    source_run_id: str | None = Field(default=None, pattern=r"^run_[a-f0-9]{32}$")
    expected_proof_fingerprint: str | None = Field(default=None, pattern=graph.HASH)
    name: str = Field(min_length=1, max_length=200)
    consent: Literal["CREATE_THIS_EXACT_FOUR_STEP_TEXT_APP_WITH_THIS_CURRENT_GOAL"]
    request_key: str = Field(pattern=seals.KEY)


class ScopeInput(Strict):
    app_id: str
    principal_id: str
    project_id: str
    runtime_id: str
    resource_id: str


def require(ok, message="Four-step text contract changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def is_candidate(candidate):
    return isinstance(candidate, dict) and candidate.get("namespace") == VERSION


def schemas():
    text = {"type": "string"}
    term = dict(type="string", maxLength=80)
    source = object_schema(dict(resource_id=text, content=dict(type="string", maxLength=1536),
                                hash=text, format=dict(type="string", enum=["txt", "md"])))
    quote = object_schema(dict(start_line=dict(type="integer", minimum=1, maximum=32),
        end_line=dict(type="integer", minimum=1, maximum=32), quote=dict(type="string", maxLength=1536)))
    lookup = object_schema(dict(resource_id=text, revision=dict(type="integer", enum=[1]),
        source_hash=text, term=term, citations=dict(type="array", items=quote, maxItems=8),
        semantic_status=dict(type="string", enum=["UNKNOWN"])))
    report = object_schema(dict(resource_id=text, source_hash=text, term_a=term, term_b=term,
        citations_a=lookup["properties"]["citations"], citations_b=lookup["properties"]["citations"],
        text=dict(type="string", maxLength=6000), semantic_status=dict(type="string", enum=["UNKNOWN"])))
    return source, lookup, report


def canonical(rid, source_hash, goal, proof, limits, ids=None):
    ids = ids or [new_id("app"), *[new_id("action") for _ in STEPS]]
    source_schema, lookup_schema, output = schemas()
    text = {"type": "string"}
    term = dict(type="string", maxLength=80)
    inputs = object_schema(dict(term_a=term, term_b=term, emit_report={"type": "boolean"}))
    permission = [dict(tool_ref="resource.read", resource_ref=rid)]
    action_inputs = [object_schema(dict(resource_id=text)),
        object_schema(dict(resource_id=text, term=term)), object_schema(dict(resource_id=text, term=term)),
        object_schema(dict(resource_id=text, source_hash=text, term_a=term, term_b=term,
            citations_a=lookup_schema["properties"]["citations"], citations_b=lookup_schema["properties"]["citations"]))]
    refs = ["resource.read", "text.literal_evidence", "text.literal_evidence", REPORT]
    action_limit = Limits(max_requests=1, max_tools=1, max_repairs=0, max_total_tokens=1,
                          max_output_tokens=1, run_seconds=limits.run_seconds).model_dump()
    actions = [dict(schema_version="1.0-draft", action_id=ids[n + 1], revision=1,
        input_schema=action_inputs[n], output_schema=[source_schema, lookup_schema, lookup_schema, output][n],
        executor=dict(kind="registered_tool", ref=ref, version="1"), allowed_tool_refs=[],
        dependencies=[dict(kind="resource", ref=rid, version="1")], permission_requirements=permission,
        effect="read", preconditions=[], postcheck_refs=[CHECK], limits=action_limit,
        idempotency="read_only", reconcile_ref="operation.lookup.v1",
        error_contract=["INVALID_INPUT", "PERMISSION_DENIED", "GRANT_REVOKED", "VERIFICATION_FAILED"])
        for n, ref in enumerate(refs)]
    workflow = [dict(step_id="read", binding_id="read", depends_on=[],
        inputs=dict(resource_id=dict(source="data", ref="source", field="resource_id")))]
    for side in ("a", "b"):
        workflow.append(dict(step_id="lookup_" + side, binding_id="lookup_" + side, depends_on=["read"],
            inputs=dict(resource_id=dict(source="step", ref="read", field="resource_id"),
                        term=dict(source="input", field="term_" + side))))
    workflow.append(dict(step_id="report", binding_id="report", depends_on=["lookup_a", "lookup_b"],
        inputs={**{key: dict(source="step", ref="lookup_a", field=key) for key in ("resource_id", "source_hash")},
            **{key + "_" + side: dict(source="step", ref="lookup_" + side, field=key)
               for side in ("a", "b") for key in ("term", "citations")}},
        when=dict(op="eq", source=dict(source="input", field="emit_report"), value=True)))
    manifest = dict(schema_version="1.0-draft", app_id=ids[0], revision=1,
        origin="task_run" if proof["source_run_id"] else "goal", goal_ref=proof["card_id"],
        source_run_ref=proof["source_run_id"], input_schema=inputs, output_schema=output,
        outputs={k: dict(source="step", ref="report", field=k) for k in output["properties"]},
        views=[dict(component_ref="text", output_field="text")], workflow=workflow,
        action_bindings=[dict(binding_id=sid, action_id=ids[n + 1], revision=1) for n, sid in enumerate(STEPS)],
        data_bindings=[dict(binding_id="source", resource_ref=rid)],
        runtime_identity_requirements=dict(mode="user_and_app_intersection"),
        permission_requirements=permission,
        dependency_lock=[dict(kind="resource", ref=rid, version="1"),
                         *[dict(kind="tool", ref=ref, version="1") for ref in dict.fromkeys(refs)],
                         dict(kind="check", ref=CHECK, version="1")],
        validation_suite_ref=CHECK, runtime_limits=limits.model_dump(), data_schema_version=1)
    return dict(namespace=VERSION, manifest=manifest, actions=actions, source_hash=source_hash,
                goal=goal, task_proof=dict(proof=proof))


@graph.controlled
def compile_candidate(candidate, platform_limits):
    require(is_candidate(candidate))
    manifest = AppManifest.model_validate(candidate["manifest"])
    actions = [ActionSpec.model_validate(a) for a in candidate["actions"]]
    require(len(actions) == 4 and len(manifest.data_bindings) == 1)
    goal = GoalCardInput.model_validate(candidate["goal"])
    proof = candidate["task_proof"]["proof"]
    require(set(proof) == {"kind", "card_id", "goal_version", "goal_fingerprint", "source_run_id", "source_proof_fingerprint"}
        and proof["kind"] == PROOF and type(proof["goal_version"]) is int
        and proof["goal_version"] >= 1 and goal.resource_refs == [manifest.data_bindings[0].resource_ref])
    require((proof["source_run_id"] is None) == (proof["source_proof_fingerprint"] is None))
    require(goal.constraints and goal.acceptance_checks and len(goal.unresolved) <= 15
        and len(json.dumps(goal.model_dump(), ensure_ascii=False).encode()) <= 6000,
        "Explicit bounded GoalCard with constraints and acceptance checks required")
    require(manifest.runtime_limits.max_tools == 4 and manifest.runtime_limits.max_requests == 1
        and manifest.runtime_limits.max_repairs == 0 and manifest.runtime_limits.max_total_tokens == 1
        and manifest.runtime_limits.max_output_tokens == 1)
    require(all(getattr(manifest.runtime_limits, k) <= getattr(platform_limits, k) for k in Limits.model_fields))
    ids = [manifest.app_id, *[a.action_id for a in actions]]
    require(len(set(ids)) == 5)
    expected = canonical(manifest.data_bindings[0].resource_ref, candidate["source_hash"],
                         goal.model_dump(), proof, manifest.runtime_limits, ids)
    require(fingerprint(candidate) == fingerprint(expected), "Only the complete canonical four-node text graph is supported")
    for schema in [manifest.input_schema, manifest.output_schema,
                   *[s for a in actions for s in (a.input_schema, a.output_schema)]]:
        schema_check(schema)
    return manifest, actions[0], dict(namespace=VERSION, order=STEPS, max_tools=4, model_requests=0,
        state="VALID", execution_performed=False, publishable=False, topological_order=STEPS,
        source_hash=candidate["source_hash"], plan_fingerprint=fingerprint(candidate),
        branch_semantics="typed-input-boolean.v1", bound=BOUND, semantic_status="UNKNOWN",
        formal_publication_enabled=False)


def bounded_source(source):
    if source["format"] not in {"txt", "md"} or len(source["content"].encode()) > 1536 or len(source["content"].splitlines()) > 32:
        raise DomainError("UNSUPPORTED_CAPABILITY", "TXT/MD <=1536 UTF-8 bytes and 32 lines required")
    return source


def current_goal(store, c, user, pid, body, source):
    # Caller has authorized the selected material before any GoalCard body read.
    head = c.execute(select(goal_cards).where(goal_cards.c.id == body.card_id,
        goal_cards.c.project_id == pid)).mappings().first()
    require(head is not None and head["version"] == body.expected_goal_version
            and head["fingerprint"] == body.expected_goal_fingerprint, "Current GoalCard version changed")
    row = c.execute(select(goal_card_versions).where(goal_card_versions.c.card_id == body.card_id,
        goal_card_versions.c.version == body.expected_goal_version)).mappings().first()
    require(row is not None and fingerprint(row["snapshot"]) == row["fingerprint"] == body.expected_goal_fingerprint)
    value = row["snapshot"]
    goal = GoalCardInput.model_validate(value["content"])
    require(goal.resource_refs == [body.resource_id]
        and value["resource_snapshots"] == [dict(resource_id=body.resource_id, hash=source["hash"], format=source["format"])]
        and head["title"] == goal.title and source["hash"] == body.expected_source_hash)
    return dict(card_id=body.card_id, version=body.expected_goal_version,
                fingerprint=body.expected_goal_fingerprint, snapshot=copy.deepcopy(value))


def scope_gate(store, c, user, aid):
    marker = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.app_id == aid,
        task_extractions.c.snapshot["kind"].as_string() == KIND)).first()
    namespace = c.execute(select(app_drafts.c.candidate["namespace"].as_string()).where(app_drafts.c.id == aid)).scalar()
    if marker is None and namespace != VERSION:
        return
    row = c.execute(select(app_drafts.c.project_id, app_drafts.c.runtime_id).where(app_drafts.c.id == aid)).mappings().first()
    require(row is not None)
    store.own_project(c, user, row["project_id"])
    # Independent scope projection precedes protected draft, goal, request and result bodies.
    meta = c.execute(select(delivery_graph_requests.c.snapshot["request"]["resource_id"].as_string().label("rid"),
        delivery_graph_requests.c.snapshot["request"]["runtime_id"].as_string().label("runtime"),
        delivery_graph_requests.c.snapshot["request"]["project_id"].as_string().label("pid"))
        .where(delivery_graph_requests.c.app_id == aid, delivery_graph_requests.c.principal_id == user,
               delivery_graph_requests.c.kind == META, delivery_graph_requests.c.request_key == "origin")).mappings().first()
    require(meta is not None and meta["runtime"] == row["runtime_id"] and meta["pid"] == row["project_id"])
    store.authorize(c, user, row["runtime_id"], row["project_id"], meta["rid"], "resource.read")


def verify_origin(store, c, user, draft, limits):
    scope_gate(store, c, user, draft["id"])
    manifest, _, report = compile_candidate(draft["candidate"], limits)
    body, value = seals.pair(c, user, draft["id"], ORIGIN, "origin", CreateInput)
    meta, meta_value = seals.pair(c, user, draft["id"], META, "origin", ScopeInput)
    require(meta.model_dump() == meta_value and meta.app_id == draft["id"] and meta.principal_id == user
        and meta.project_id == draft["project_id"] and meta.runtime_id == draft["runtime_id"]
        and meta.resource_id == body.resource_id == manifest.data_bindings[0].resource_ref)
    marker = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"],
        task_extractions.c.principal_id == user)).mappings().first()
    require(marker is not None and marker["snapshot"] == value and marker["request_fingerprint"] == fingerprint(body.model_dump())
        and marker["task_id"] == (body.source_run_id or body.card_id)
        and value["kind"] == KIND and value["candidate_fingerprint"] == draft["fingerprint"])
    source = bounded_source(authorized_read(store, c, user, draft["runtime_id"], draft["project_id"],
        "resource.read", dict(resource_id=body.resource_id)))
    goal = current_goal(store, c, user, draft["project_id"], body, source)
    proof = dict(kind=PROOF, card_id=body.card_id, goal_version=body.expected_goal_version,
        goal_fingerprint=body.expected_goal_fingerprint, source_run_id=body.source_run_id,
        source_proof_fingerprint=body.expected_proof_fingerprint)
    require(value["goal"] == goal and draft["candidate"]["goal"] == goal["snapshot"]["content"]
        and draft["candidate"]["task_proof"]["proof"] == proof)
    if body.source_run_id:
        source_proof = verified_source(store, c, user, body.source_run_id, limits)
        require(fingerprint(source_proof) == body.expected_proof_fingerprint
            and source_proof == value["source_proof"] and source_proof["project_id"] == draft["project_id"]
            and source_proof["resource_id"] != body.resource_id and source_proof["source_hash"] != source["hash"],
            "Extraction requires the exact complete task and fresh material")
    else:
        require(value["source_proof"] is None)
    return manifest, report, source, goal


def expected_lookup(source, term):
    term = term.strip()
    if not term or len(term) > 80 or "\n" in term or "\r" in term:
        raise DomainError("INVALID_INPUT", "Nonblank single-line literal terms required")
    citations = [dict(start_line=n, end_line=n, quote=line) for n, line in enumerate(source["content"].splitlines(), 1) if term in line]
    if len(citations) > 8:
        raise DomainError("BUDGET_EXHAUSTED", "At most eight complete citations per lookup")
    return dict(resource_id=source["resource_id"], revision=1, source_hash=source["hash"], term=term,
                citations=citations, semantic_status="UNKNOWN")


def render(a, b):
    require(a["resource_id"] == b["resource_id"] and a["source_hash"] == b["source_hash"])
    chunks = []
    for side, value in (("A", a), ("B", b)):
        chunks.append(side + ": " + value["term"])
        chunks.extend("L" + str(q["start_line"]) + ": " + q["quote"] for q in value["citations"])
        if not value["citations"]:
            chunks.append("No literal matches")
    return dict(resource_id=a["resource_id"], source_hash=a["source_hash"], term_a=a["term"], term_b=b["term"],
        citations_a=a["citations"], citations_b=b["citations"], text="\n".join(chunks), semantic_status="UNKNOWN")


def arguments(step, plan, outputs):
    return resolve(step, plan, outputs)


def compute_step(step, args, source):
    if step == "read":
        return copy.deepcopy(source)
    if step in {"lookup_a", "lookup_b"}:
        from .text_apps import compute
        output = compute(source, args)
        validate_value(schemas()[1], output)
        return output
    a, b = [dict(resource_id=args["resource_id"], source_hash=args["source_hash"],
        term=args["term_" + side], citations=args["citations_" + side]) for side in ("a", "b")]
    return render(a, b)


def oracle(step, args, source, output):
    if step == "read":
        wanted = source
    elif step in {"lookup_a", "lookup_b"}:
        wanted = expected_lookup(source, args["term"])
    else:
        # Independently derive both evidence sets from the actual source bytes.
        a, b = expected_lookup(source, args["term_a"]), expected_lookup(source, args["term_b"])
        require(args["resource_id"] == source["resource_id"] and args["source_hash"] == source["hash"]
            and fingerprint(a["citations"]) == fingerprint(args["citations_a"])
            and fingerprint(b["citations"]) == fingerprint(args["citations_b"]),
                "Report predecessor citations changed")
        lines = []
        for side, value in (("A", a), ("B", b)):
            lines.append(f"{side}: {value['term']}")
            lines += [f"L{q['start_line']}: {q['quote']}" for q in value["citations"]] or ["No literal matches"]
        wanted = dict(resource_id=source["resource_id"], source_hash=source["hash"],
            term_a=a["term"], term_b=b["term"], citations_a=a["citations"], citations_b=b["citations"],
            text="\n".join(lines), semantic_status="UNKNOWN")
    if fingerprint(output) != fingerprint(wanted):
        raise DomainError("VERIFICATION_FAILED", "Independent four-step source/citation oracle failed")
    return wanted


def plan_for(candidate, input_value):
    return dict(definition=candidate, input=input_value, source_hash=candidate["source_hash"],
        plan_fingerprint=fingerprint(candidate), branch_semantics="typed-input-boolean.v1")


def preview(source, candidate, input_value):
    validate_value(candidate["manifest"]["input_schema"], input_value)
    outputs, proved = {}, []
    plan = plan_for(candidate, input_value)
    for step, action in zip(candidate["manifest"]["workflow"], candidate["actions"], strict=True):
        choice = decision(plan, step, input_value, outputs, proved)
        if not choice["branch_decision"]["passed"]:
            continue
        args = arguments(step, plan, outputs)
        validate_value(action["input_schema"], args)
        output = compute_step(step["step_id"], args, source)
        validate_value(action["output_schema"], output)
        oracle(step["step_id"], args, source, output)
        outputs[step["step_id"]] = output
    if "report" not in outputs:
        raise DomainError("INVALID_INPUT", "Release sample must exercise the report branch")
    return outputs["report"]


@graph.controlled
def options(store, user, pid, card_id, limits, source_run_id=None):
    with store.tx() as c:
        project = store.own_project(c, user, pid)
        head = c.execute(select(goal_cards).where(goal_cards.c.id == card_id,
            goal_cards.c.project_id == pid)).mappings().first()
        require(head is not None)
        refs = c.execute(select(goal_card_versions.c.snapshot["content"]["resource_refs"]).where(
            goal_card_versions.c.card_id == card_id, goal_card_versions.c.version == head["version"])).scalar()
        require(isinstance(refs, list) and len(refs) == 1)
        source = bounded_source(authorized_read(store, c, user, project["runtime_id"], pid,
            "resource.read", dict(resource_id=refs[0])))
        body = CreateInput(card_id=card_id, expected_goal_version=head["version"],
            expected_goal_fingerprint=head["fingerprint"], resource_id=refs[0], expected_source_hash=source["hash"],
            source_run_id=source_run_id, name="Text citation task", request_key="preview",
            consent="CREATE_THIS_EXACT_FOUR_STEP_TEXT_APP_WITH_THIS_CURRENT_GOAL")
        goal = current_goal(store, c, user, pid, body, source)
        proof = verified_source(store, c, user, source_run_id, limits) if source_run_id else None
        if proof:
            require(proof["project_id"] == pid and proof["resource_id"] != refs[0] and proof["source_hash"] != source["hash"])
            require(proof["extraction_depth"] == 0, "Only one explicit extraction hop is supported")
        return dict(namespace=VERSION, project_id=pid, card_id=card_id, goal_version=head["version"],
            goal_fingerprint=head["fingerprint"], goal=goal["snapshot"]["content"],
            resource_id=refs[0], source_hash=source["hash"], source_run_id=source_run_id,
            source_proof=proof, source_proof_fingerprint=fingerprint(proof) if proof else None,
            steps=STEPS, inputs=["term_a", "term_b", "emit_report"], bound=BOUND,
            false_branch="SKIPPED_REPORT_PARTIAL_NO_SUCCESS_RECORD", owner_acceptance="PENDING",
            model_requests=0, semantic_status="UNKNOWN", formal_publication_enabled=False)


@graph.controlled
def create(store, user, pid, body, limits):
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        source = bounded_source(authorized_read(store, c, user, project["runtime_id"], pid,
            "resource.read", dict(resource_id=body.resource_id)))
        goal = current_goal(store, c, user, pid, body, source)
        require((body.source_run_id is None) == (body.expected_proof_fingerprint is None))
        proof = verified_source(store, c, user, body.source_run_id, limits) if body.source_run_id else None
        if proof:
            require(fingerprint(proof) == body.expected_proof_fingerprint and proof["project_id"] == pid
                and proof["resource_id"] != body.resource_id and proof["source_hash"] != source["hash"]
                and proof["extraction_depth"] == 0)
        old = graph.lookup(c, user, pid, CREATE, body.request_key)
        if old or graph.lookup(c, user, pid, CREATE + "_seal", body.request_key):
            prior, value = seals.pair(c, user, pid, CREATE, body.request_key, CreateInput)
            require(fingerprint(prior.model_dump()) == fingerprint(body.model_dump()))
            from .apps import load_draft
            load_draft(store, c, user, value["id"], limits)
            return dict(**value, cached=True)
        effective = Limits(max_requests=1, max_tools=4, max_repairs=0, max_total_tokens=1,
                           max_output_tokens=1, run_seconds=min(60, limits.run_seconds))
        declaration = dict(kind=PROOF, card_id=body.card_id, goal_version=body.expected_goal_version,
            goal_fingerprint=body.expected_goal_fingerprint, source_run_id=body.source_run_id,
            source_proof_fingerprint=body.expected_proof_fingerprint)
        candidate = canonical(body.resource_id, source["hash"], goal["snapshot"]["content"], declaration, effective)
        compile_candidate(candidate, limits)
        aid, runtime = candidate["manifest"]["app_id"], new_id("appruntime")
        c.execute(insert(principals).values(id=runtime, name="read-only four-step text app"))
        c.execute(insert(grants).values(id=new_id("grant"), principal_id=runtime, project_id=pid,
            resource_id=body.resource_id, tool_ref="resource.read", expires_at=time.time() + 86400,
            revision=1, revoked=False))
        c.execute(insert(app_drafts).values(id=aid, project_id=pid, runtime_id=runtime, name=body.name,
            candidate=candidate, fingerprint=fingerprint(candidate), created_at=time.time()))
        value = dict(kind=KIND, candidate_fingerprint=fingerprint(candidate), goal=goal, source_proof=proof)
        c.execute(insert(task_extractions).values(task_id=body.source_run_id or body.card_id, principal_id=user,
            request_key=body.request_key, request_fingerprint=fingerprint(body.model_dump()), app_id=aid, snapshot=value))
        seals.remember(c, user, aid, ORIGIN, "origin", body, value)
        meta = ScopeInput(app_id=aid, principal_id=user, project_id=pid, runtime_id=runtime, resource_id=body.resource_id)
        seals.remember(c, user, aid, META, "origin", meta, meta.model_dump())
        result = dict(id=aid, state="PREVIEW_ONLY", namespace=VERSION, candidate_fingerprint=fingerprint(candidate),
            owner_acceptance="PENDING", semantic_status="UNKNOWN", model_requests=0, formal_publication_enabled=False)
        seals.remember(c, user, pid, CREATE, body.request_key, body, result)
        verify_origin(store, c, user, dict(id=aid, project_id=pid, runtime_id=runtime,
            candidate=candidate, fingerprint=fingerprint(candidate)), limits)
        return dict(**result, cached=False)


@graph.controlled
def recover(store, user, pid, key, limits):
    with store.tx() as c:
        store.own_project(c, user, pid)
        # Read only the original key; never recreates an unknown request.
        meta = c.execute(select(delivery_graph_requests.c.snapshot["request"]["resource_id"].as_string())
            .where(delivery_graph_requests.c.app_id == pid, delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind == CREATE, delivery_graph_requests.c.request_key == key)).scalar()
        if meta is None:
            raise DomainError("OUTCOME_UNKNOWN", "No result for this original text task key")
        project = store.own_project(c, user, pid)
        store.authorize(c, user, project["runtime_id"], pid, meta, "resource.read")
        _, value = seals.pair(c, user, pid, CREATE, key, CreateInput)
        from .apps import load_draft
        load_draft(store, c, user, value["id"], limits)
        return dict(**value, cached=True)


def bound(store, c, user, job, limits):
    from . import app_jobs, lifecycle
    snapshot, app_run = app_jobs.load_binding(store, c, user, job, limits)
    release = lifecycle.read_release(store, c, user, snapshot["release_id"], limits)
    draft = release["snapshot"]["draft"]
    require(is_candidate(draft["candidate"]))
    manifest, report, source, goal = verify_origin(store, c, user, draft, limits)
    contract = store.frozen_contract(c, job)
    require(contract.source_goal_card is None
        and contract.goal.goal_id == goal["card_id"] and contract.goal.project_id == draft["project_id"]
        and contract.goal.owner_id == user and contract.goal.goal == goal["snapshot"]["content"]["goal"]
        and contract.goal.constraints == goal["snapshot"]["content"]["constraints"]
        and contract.goal.unresolved == goal_unresolved(goal)
        and contract.goal.resource_refs == [source["resource_id"]]
        and snapshot.get("text_goal") == goal and job["resource_refs"] == [source["resource_id"]]
        and len(contract.resources) == 1 and contract.resources[0].content_hash == source["hash"]
        and contract.resources[0].resource_id == source["resource_id"] and contract.resources[0].format == source["format"]
        and contract.mode == "mock" and contract.natural_planning is None and contract.application_generation is None,
        "Frozen current GoalCard or material binding changed")
    require(all(type(job["context"].get(k)) is int and job["context"][k] == 0
                for k in ("requests", "repairs", "reserved_tokens"))
        and type(job["context"].get("tools")) is int and 0 <= job["context"]["tools"] <= 4)
    validate_value(manifest.input_schema, snapshot["input"])
    return dict(snapshot=snapshot, app_run=app_run, release=release, draft=draft,
                source=source, goal=goal, plan=plan_for(draft["candidate"], snapshot["input"]), report=report)


def goal_unresolved(goal):
    """GoalSpec's closed existing field freezes this adapter's exact native anchor.

    source_goal_card belongs to ordinary GoalRun acceptance, not AppRun. The full
    card lives in the independently fingerprinted accepted AppRun binding.
    """
    return [*goal["snapshot"]["content"]["unresolved"],
        f"{VERSION}:card={goal['card_id']};version={goal['version']};fingerprint={goal['fingerprint']}"]


def intent_for(step, action, plan, outputs, proved):
    args = arguments(step, plan, outputs)
    validate_value(action["input_schema"], args)
    return dict(tool=action["executor"]["ref"], args=args,
        plan_fingerprint=plan["plan_fingerprint"], input_sources=copy.deepcopy(step["inputs"]),
        predecessor_receipts=[fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]],
        **decision(plan, step, plan["input"], outputs, proved))


def receipt_for(oid, step, action, plan, source, intent, value):
    return dict(operation_id=oid, step_id=step["step_id"], status="VERIFIED", data=value,
        plan_fingerprint=plan["plan_fingerprint"], source_hash=plan["source_hash"],
        action_revision=action["revision"], input_fingerprint=fingerprint(intent["args"]),
        output_fingerprint=fingerprint(value), predecessor_receipts=intent["predecessor_receipts"],
        input_sources=intent["input_sources"], branch_decision=intent["branch_decision"], artifact_refs=[],
        check_results=[dict(check=CHECK, status="PASS")],
        # Pure lookups/report consume the verified read snapshot. Each transaction
        # additionally reloads bytes through authorization; record that guard read.
        actual_reads=[dict(resource_id=source["resource_id"], source_hash=source["hash"],
                          purpose="BUSINESS_READ")] if step["step_id"] == "read" else [],
        authorization_guard_reads=[dict(resource_id=source["resource_id"], source_hash=source["hash"],
                                        tool_ref="resource.read", purpose="LIVE_SOURCE_VERIFICATION")])


def receipts(store, c, job, binding):
    plan, source = binding["plan"], binding["source"]
    ops = c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings().all()
    skips = c.execute(select(events.c.data).where(events.c.run_id == job["id"],
        events.c.kind == "TEXT_WORKFLOW_SKIPPED")).scalars().all()
    by_step, by_skip = {op["call_id"]: op for op in ops}, {r["step_id"]: r for r in skips}
    require(len(by_step) == len(ops) and len(by_skip) == len(skips)
        and not (set(by_step) - set(STEPS)) and not (set(by_skip) - {"report"}) and not (set(by_step) & set(by_skip)),
        "Unknown, duplicate or mixed text node receipts")
    outputs, proved = {}, []
    for index, (step, action) in enumerate(zip(plan["definition"]["manifest"]["workflow"], plan["definition"]["actions"], strict=True)):
        sid = step["step_id"]
        if sid not in by_step and sid not in by_skip:
            require(not (set(STEPS[index + 1:]) & (set(by_step) | set(by_skip))), "Missing predecessor receipt")
            break
        choice = decision(plan, step, plan["input"], outputs, proved)
        parents = [fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]]
        if not choice["branch_decision"]["passed"]:
            wanted = skip_receipt(plan, step, action, choice, parents)
            require(sid not in by_step and fingerprint(by_skip.get(sid)) == fingerprint(wanted), "Skipped report decision changed")
            proved.append(wanted)
            continue
        require(sid in by_step and sid not in by_skip)
        op = by_step[sid]
        intent = intent_for(step, action, plan, outputs, proved)
        saved = c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])).scalar()
        require(fingerprint(saved) == fingerprint(intent) == op["fingerprint"] and op["tool_ref"] == intent["tool"])
        if op["status"] != "VERIFIED":
            raise DomainError("OUTCOME_UNKNOWN", "Unverified text node requires reconciliation")
        receipt = op["receipt"]
        validate_value(action["output_schema"], receipt["data"])
        value = oracle(sid, intent["args"], source, receipt["data"])
        wanted = receipt_for(op["id"], step, action, plan, source, intent, value)
        if fingerprint(receipt) != fingerprint(wanted):
            raise DomainError("VERIFICATION_FAILED", "Persisted text receipt failed complete readback")
        outputs[sid] = value
        proved.append(wanted)
    require(job["context"]["tools"] == sum(p["status"] == "VERIFIED" for p in proved), "Tool counter and actual nodes differ")
    return outputs, proved


def result_ref(binding, outputs, proved, result_version):
    snapshot = binding["snapshot"]
    return dict(namespace=VERSION, app_run_id=snapshot["app_run_id"], instance_id=snapshot["instance_id"],
        release_id=snapshot["release_id"], result_version=result_version,
        plan_fingerprint=binding["plan"]["plan_fingerprint"],
        receipt_refs=[p["operation_id"] for p in proved if p["status"] == "VERIFIED"],
        steps=[dict(step_id=p["step_id"], status=p["status"], fingerprint=fingerprint(p)) for p in proved],
        output_status="PRODUCED" if "report" in outputs else "SKIPPED",
        model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)


def verify_job(store, c, user, job, limits, binding=None, *, require_success=False):
    binding = binding or bound(store, c, user, job, limits)
    outputs, proved = receipts(store, c, job, binding)
    a, s = binding["app_run"], binding["snapshot"]
    rows = c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == s["instance_id"],
        internal_instance_data.c.run_id == a["id"])).mappings().all()
    complete = len(proved) == 4
    terminal = job["status"] in {"SUCCEEDED", "PARTIAL"}
    residue = bool(rows or a["output"] is not None or a["result_version"] is not None or job["result"] is not None)
    if terminal or residue:
        require(complete and terminal and a["status"] == job["status"] and job["error"] is None
            and a["error"] is None and not job["cancel_intent"] and not store.has_unknown(c, job["id"]),
            "Terminal output lacks a complete successful/partial text execution")
        if "report" in outputs:
            require(job["status"] == "SUCCEEDED" and len(rows) == 1 and a["output"] == outputs["report"])
            row = rows[0]
            data = dict(result=outputs["report"])
            if "release_ref" in binding["release"]["snapshot"]["data_schema"]["properties"]:
                data["release_ref"] = s["release_id"]
            validate_value(binding["release"]["snapshot"]["data_schema"], row["data"])
            require(fingerprint(row["data"]) == fingerprint(data) == row["fingerprint"]
                and row["release_id"] == s["release_id"] and row["version"] == a["result_version"]
                and row["schema_version"] == binding["release"]["snapshot"]["data_schema_version"])
        else:
            require(job["status"] == "PARTIAL" and not rows and a["output"] is None and a["result_version"] is None)
        require(fingerprint(job["result"]) == fingerprint(result_ref(binding, outputs, proved, a["result_version"])))
    else:
        require(a["status"] == job["status"] or job["status"] == "RUNNING", "AppRun state differs from its accepted job")
    if require_success:
        require(job["status"] == "SUCCEEDED" and complete and "report" in outputs,
                "Only an actual complete successful four-step task can be extracted")
    return binding, outputs, proved


def verified_source(store, c, user, rid, limits):
    # Independent owned instance/release metadata gates before source job bodies.
    from .text_continuations import job_gate
    pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)).scalar()
    if pid is None:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, pid)
    job_gate(store, c, user, rid)
    job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
        runs.c.project_id == pid)).mappings().one()
    binding, outputs, proved = verify_job(store, c, user, job, limits, require_success=True)
    s = binding["snapshot"]
    contract_fp = c.execute(select(run_contracts.c.fingerprint).where(run_contracts.c.run_id == rid)).scalar()
    record = c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == s["instance_id"],
        internal_instance_data.c.run_id == s["app_run_id"])).mappings().one()
    return dict(kind=PROOF, run_id=rid, project_id=pid, principal_id=user, runtime_id=job["runtime_id"],
        extraction_depth=1 if binding["draft"]["candidate"]["manifest"]["source_run_ref"] else 0,
        resource_id=binding["source"]["resource_id"], source_hash=binding["source"]["hash"],
        goal_fingerprint=binding["goal"]["fingerprint"], contract_fingerprint=contract_fp,
        binding_fingerprint=fingerprint(s), release_id=s["release_id"], release_fingerprint=s["expected_release_fp"],
        plan_fingerprint=binding["plan"]["plan_fingerprint"], input_fingerprint=fingerprint(s["input"]),
        steps=[dict(step_id=p["step_id"], operation_id=p["operation_id"], receipt_fingerprint=fingerprint(p)) for p in proved],
        output_fingerprint=fingerprint(outputs["report"]), result_record_fingerprint=fingerprint(dict(record)),
        model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)


def verify_instance_records(store, c, user, instance, records, limits):
    jobs = c.execute(select(runs.c.id).join(internal_run_bindings, internal_run_bindings.c.run_id == runs.c.id)
        .join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
        .where(internal_app_runs.c.instance_id == instance["id"], internal_app_runs.c.principal_id == user,
            runs.c.principal_id == user, runs.c.project_id == instance["project_id"])).scalars().all()
    verified_ids = set()
    for rid in jobs:
        job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
            runs.c.project_id == instance["project_id"])).mappings().one()
        binding, _, _ = verify_job(store, c, user, job, limits)
        if job["status"] == "SUCCEEDED":
            verified_ids.add(binding["app_run"]["id"])
    require({r["run_id"] for r in records} == verified_ids, "Typed records and successful text tasks differ")


def commit_guard(worker, c, run, binding, delta=0):
    from .app_jobs import lock_live
    job = lock_live(worker.store, c, run)
    require(job["status"] == "RUNNING" and not job["cancel_intent"] and not worker.stop.is_set(),
            "Text task stopped before commit")
    limits = Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields})
    fresh = bound(worker.store, c, job["principal_id"], job, limits)
    require(fingerprint(fresh["snapshot"]) == fingerprint(binding["snapshot"]))
    s = fresh["snapshot"]
    instance = c.execute(select(internal_instances.c.revision, internal_instances.c.release_id,
        internal_instances.c.runtime_id, internal_instances.c.project_id, internal_instances.c.source_app_id)
        .where(internal_instances.c.id == s["instance_id"], internal_instances.c.principal_id == job["principal_id"])).mappings().first()
    require(instance is not None and instance["revision"] == s["expected_revision"]
        and instance["release_id"] == s["release_id"] and instance["runtime_id"] == job["runtime_id"]
        and instance["project_id"] == job["project_id"] and instance["source_app_id"] == fresh["draft"]["id"],
        "Accepted instance version changed before text node commit")
    declared = Limits(**fresh["draft"]["candidate"]["manifest"]["runtime_limits"])
    frozen = worker.store.frozen_contract(c, job).limits
    if (time.time() >= job["created_at"] + min(limits.run_seconds, declared.run_seconds, frozen.run_seconds)
        or job["context"]["tools"] + delta > min(limits.max_tools, declared.max_tools, frozen.max_tools)):
        raise DomainError("BUDGET_EXHAUSTED", "Effective four-step budget expired before commit")
    return job


@graph.controlled
def advance(worker, run):
    from .app_jobs import load_binding, lock_live, state_write, stop_state
    store = worker.store
    with store.tx() as c:
        job = lock_live(store, c, run)
        # Stop is possible after authority revocation without reading protected bytes.
        if job["status"] != "RUNNING" or worker.stop.is_set():
            s, a = load_binding(store, c, job["principal_id"], job, None, authorize=False)
            state_write(store, c, job, a["id"], stop_state(job, store.has_unknown(c, job["id"])))
            return False
        limits = Limits(**{k: getattr(worker.s, k) for k in Limits.model_fields})
        binding = bound(store, c, job["principal_id"], job, limits)
        if store.has_unknown(c, job["id"]):
            raise DomainError("OUTCOME_UNKNOWN")
        outputs, proved = receipts(store, c, job, binding)
        plan, a, s = binding["plan"], binding["app_run"], binding["snapshot"]
        if len(proved) == 4:
            commit_guard(worker, c, run, binding)
            instance = c.execute(select(internal_instances).where(internal_instances.c.id == s["instance_id"],
                internal_instances.c.principal_id == job["principal_id"])).mappings().one()
            require(instance["revision"] == s["expected_revision"] and instance["release_id"] == s["release_id"])
            version = None
            if "report" in outputs:
                version = instance["data_version"] + 1
                data = dict(result=outputs["report"])
                if "release_ref" in binding["release"]["snapshot"]["data_schema"]["properties"]:
                    data["release_ref"] = s["release_id"]
                validate_value(binding["release"]["snapshot"]["data_schema"], data)
                c.execute(insert(internal_instance_data).values(instance_id=instance["id"], version=version,
                    run_id=a["id"], release_id=s["release_id"], schema_version=binding["release"]["snapshot"]["data_schema_version"],
                    data=data, fingerprint=fingerprint(data)))
                changed = c.execute(update(internal_instances).where(internal_instances.c.id == instance["id"],
                    internal_instances.c.revision == s["expected_revision"], internal_instances.c.data_version == instance["data_version"],
                    internal_instances.c.release_id == s["release_id"]).values(data_version=version)).rowcount
                require(changed == 1)
            state = "SUCCEEDED" if "report" in outputs else "PARTIAL"
            c.execute(update(internal_app_runs).where(internal_app_runs.c.id == a["id"]).values(
                output=outputs.get("report"), result_version=version, status=state, error=None))
            # Recheck before terminal write; expiry/late ownership rolls back append.
            live = commit_guard(worker, c, run, binding)
            state_write(store, c, live, a["id"], state, result=result_ref(binding, outputs, proved, version))
            store.event(c, job["id"], "TEXT_WORKFLOW_COMMITTED", dict(status=state, result_version=version))
            return False
        step = plan["definition"]["manifest"]["workflow"][len(proved)]
        action = plan["definition"]["actions"][len(proved)]
        choice = decision(plan, step, plan["input"], outputs, proved)
        if not choice["branch_decision"]["passed"]:
            value = skip_receipt(plan, step, action, choice,
                [fingerprint(p) for p in proved if p["step_id"] in step["depends_on"]])
            commit_guard(worker, c, run, binding)
            store.event(c, job["id"], "TEXT_WORKFLOW_SKIPPED", value)
            commit_guard(worker, c, run, binding)
            return True
        intent = intent_for(step, action, plan, outputs, proved)
        oid = new_id("op")
        commit_guard(worker, c, run, binding, 1)
        c.execute(insert(operations).values(id=oid, run_id=job["id"], call_id=step["step_id"],
            fingerprint=fingerprint(intent), tool_ref=intent["tool"], status="PREPARED"))
        c.execute(insert(operation_intents).values(operation_id=oid, request=intent))
        value = compute_step(step["step_id"], intent["args"], binding["source"])
        validate_value(action["output_schema"], value)
        oracle(step["step_id"], intent["args"], binding["source"], value)
        receipt = receipt_for(oid, step, action, plan, binding["source"], intent, value)
        live = commit_guard(worker, c, run, binding, 1)
        c.execute(update(operations).where(operations.c.id == oid).values(status="VERIFIED", receipt=receipt))
        context = copy.deepcopy(live["context"])
        context["tools"] += 1
        c.execute(update(runs).where(runs.c.id == job["id"]).values(context=context))
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id == a["id"]).values(status="RUNNING"))
        store.event(c, job["id"], "TEXT_WORKFLOW_STEP_VERIFIED", dict(step_id=step["step_id"], operation_id=oid))
        commit_guard(worker, c, run, binding)
        return True


def process_job(worker, run):
    from .app_jobs import fail_job
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
        fail_job(worker, run, exc)
    finally:
        stopped.set()
        thread.join(timeout=2)


def is_job(store, job):
    with store.engine.connect() as c:
        return c.execute(select(task_extractions.c.app_id)
            .join(internal_instances, internal_instances.c.source_app_id == task_extractions.c.app_id)
            .join(internal_app_runs, internal_app_runs.c.instance_id == internal_instances.c.id)
            .join(internal_run_bindings, internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
            .where(internal_run_bindings.c.run_id == job["id"], task_extractions.c.snapshot["kind"].as_string() == KIND)).first() is not None


def mount(app, store, limits, identity):
    from fastapi import Depends
    user_dependency = Depends(identity)

    @app.get("/api/projects/{pid}/text-workflow-options")
    def get_options(pid: str, card_id: str, source_run_id: str | None = None, user=user_dependency):
        return options(store, user, pid, card_id, limits, source_run_id)

    @app.post("/api/projects/{pid}/text-workflows", status_code=201)
    def post_create(pid: str, body: CreateInput, user=user_dependency):
        return create(store, user, pid, body, limits)

    @app.get("/api/projects/{pid}/text-workflow-requests/{key}")
    def get_recover(pid: str, key: str, user=user_dependency):
        return recover(store, user, pid, key, limits)

    @app.get("/api/internal/app-run-jobs/{rid}/text-workflow-proof")
    def get_proof(rid: str, user=user_dependency):
        with store.tx() as c:
            return verified_source(store, c, user, rid, limits)
