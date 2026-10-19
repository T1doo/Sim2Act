"""Closed four-step TXT/MD task, actual receipts and exact-source extraction.

This adapter does not register an operator or extend the global workflow DSL.
Only read -> two independent literal lookups -> conditional citation report is
accepted. Goal, authorization, bytes, budget and ownership remain live gates.
"""

import copy
import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager, nullcontext
from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select, update
from sqlalchemy.exc import OperationalError

from . import delivery_graph_apps as graph
from . import text_logic_reuse as seals
from .apps import object_schema
from .contracts import ActionSpec, AppManifest, Limits, Strict, schema_check, validate_value
from .csv_dag import decision, resolve, skip_receipt
from .db import (
    app_drafts,
    attempts,
    delivery_graph_requests,
    events,
    fingerprint,
    goal_card_versions,
    goal_cards,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
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
RUN_META = "text_four_step_run_scope"
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


class RunScopeInput(ScopeInput):
    run_id: str
    instance_id: str
    app_run_id: str
    release_id: str


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


@graph.controlled
def scope_gate(store, c, user, aid):
    marker = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.app_id == aid,
        task_extractions.c.snapshot["kind"].as_string() == KIND)).first()
    namespace = c.execute(select(app_drafts.c.candidate["namespace"].as_string()).where(app_drafts.c.id == aid)).scalar()
    if marker is None and namespace != VERSION:
        return False
    row = c.execute(select(app_drafts.c.project_id, app_drafts.c.runtime_id,
        app_drafts.c.candidate["manifest"]["data_bindings"][0]["resource_ref"].as_string().label("rid"))
        .where(app_drafts.c.id == aid)).mappings().first()
    require(row is not None)
    store.own_project(c, user, row["project_id"])
    # Independent scope projection precedes protected draft, goal, request and result bodies.
    # ScopeInput contains identifiers only. Validate both independent seals before
    # trusting its resource as an authorization gate; no Goal/draft body needed.
    meta, value = seals.pair(c, user, aid, META, "origin", ScopeInput)
    require(fingerprint(meta.model_dump()) == fingerprint(value) and meta.app_id == aid
        and meta.principal_id == user and meta.runtime_id == row["runtime_id"] and meta.project_id == row["project_id"]
        and meta.resource_id == row["rid"])
    store.authorize(c, user, row["runtime_id"], row["project_id"], meta.resource_id, "resource.read")
    return True


@graph.controlled
def job_scope_gate(store, c, user, rid):
    metadata = c.execute(select(runs.c.principal_id, runs.c.project_id,
        runs.c.runtime_id, runs.c.request_key).where(runs.c.id == rid)).mappings().first()
    if metadata is None or metadata["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, metadata["project_id"])
    accepted = c.execute(select(events.c.data["instance_id"].as_string().label("iid"),
        events.c.data["app_run_id"].as_string().label("aid"))
        .where(events.c.run_id == rid, events.c.kind == "ACCEPTED",
            events.c.data["namespace"].as_string() == "INTERNAL_APPRUN")).mappings().all()
    marker = graph.lookup(c, user, rid, RUN_META, "accepted")
    family = marker is not None or graph.lookup(c, user, rid, RUN_META + "_seal", "accepted") is not None
    if family:
        meta, value = seals.pair(c, user, rid, RUN_META, "accepted", RunScopeInput)
        require(fingerprint(meta.model_dump()) == fingerprint(value) and meta.run_id == rid
            and meta.principal_id == user and meta.project_id == metadata["project_id"]
            and meta.runtime_id == metadata["runtime_id"] and metadata["request_key"] == "internal:" + meta.app_run_id)
        i = c.execute(select(internal_instances.c.project_id, internal_instances.c.runtime_id,
            internal_instances.c.source_app_id).where(internal_instances.c.id == meta.instance_id,
            internal_instances.c.principal_id == user)).mappings().first()
        require(i is not None and i["project_id"] == meta.project_id and i["runtime_id"] == meta.runtime_id
            and i["source_app_id"] == meta.app_id)
        require(scope_gate(store, c, user, meta.app_id))
        require(len(accepted) == 1 and accepted[0]["iid"] == meta.instance_id and accepted[0]["aid"] == meta.app_run_id)
        return
    # Missing both seals/events must not downgrade a surviving four-step job.
    # Its fresh app runtime and internal:+AppRun.id are independent identifiers;
    # derive original material scope without full Run/binding/Goal/result reads.
    origins = set(c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == metadata["project_id"],
        app_drafts.c.runtime_id == metadata["runtime_id"])).scalars())
    if metadata["request_key"].startswith("internal:"):
        original = c.execute(select(internal_instances.c.source_app_id)
            .join(internal_app_runs, internal_app_runs.c.instance_id == internal_instances.c.id)
            .where(internal_app_runs.c.id == metadata["request_key"][9:], internal_app_runs.c.principal_id == user,
                internal_instances.c.project_id == metadata["project_id"], internal_instances.c.principal_id == user)).scalar()
        if original:
            origins.add(original)
    for aid in origins:
        require(not scope_gate(store, c, user, aid), "Independent four-step Run scope seals were removed")
    for row in accepted:
        instance = c.execute(select(internal_instances.c.source_app_id, internal_instances.c.project_id)
            .where(internal_instances.c.id == row["iid"], internal_instances.c.principal_id == user)).mappings().first()
        if instance and instance["project_id"] == metadata["project_id"]:
            actual = scope_gate(store, c, user, instance["source_app_id"])
            require(not actual or family, "Independent four-step Run marker was removed")
            if actual:
                require(len(accepted) == 1)
                return
    require(not family, "Four-step accepted instance scope is missing or changed")


def seal_job_scope(c, user, draft, snapshot):
    body = RunScopeInput(app_id=draft["id"], principal_id=user, project_id=draft["project_id"],
        runtime_id=draft["runtime_id"], resource_id=draft["candidate"]["manifest"]["data_bindings"][0]["resource_ref"],
        run_id=snapshot["run_id"], instance_id=snapshot["instance_id"], app_run_id=snapshot["app_run_id"],
        release_id=snapshot["release_id"])
    seals.remember(c, user, snapshot["run_id"], RUN_META, "accepted", body, body.model_dump())


def public_origin(c, user, draft):
    body, _ = seals.pair(c, user, draft["id"], ORIGIN, "origin", CreateInput)
    return dict(namespace=VERSION, app_id=draft["id"], project_id=draft["project_id"], runtime_id=draft["runtime_id"],
        request_key=body.request_key, request_fingerprint=fingerprint(body.model_dump()), request=body.model_dump())


def verify_origin(store, c, user, draft, limits):
    scope_gate(store, c, user, draft["id"])
    manifest, _, report = compile_candidate(draft["candidate"], limits)
    body, value = seals.pair(c, user, draft["id"], ORIGIN, "origin", CreateInput)
    meta, meta_value = seals.pair(c, user, draft["id"], META, "origin", ScopeInput)
    require(fingerprint(meta.model_dump()) == fingerprint(meta_value) and meta.app_id == draft["id"] and meta.principal_id == user
        and meta.project_id == draft["project_id"] and meta.runtime_id == draft["runtime_id"]
        and meta.resource_id == body.resource_id == manifest.data_bindings[0].resource_ref)
    marker = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"],
        task_extractions.c.principal_id == user)).mappings().first()
    require(marker is not None and fingerprint(marker["snapshot"]) == fingerprint(value) and marker["request_fingerprint"] == fingerprint(body.model_dump())
        and marker["task_id"] == (body.source_run_id or body.card_id)
        and value["kind"] == KIND and value["candidate_fingerprint"] == draft["fingerprint"])
    source = bounded_source(authorized_read(store, c, user, draft["runtime_id"], draft["project_id"],
        "resource.read", dict(resource_id=body.resource_id)))
    goal = current_goal(store, c, user, draft["project_id"], body, source)
    proof = dict(kind=PROOF, card_id=body.card_id, goal_version=body.expected_goal_version,
        goal_fingerprint=body.expected_goal_fingerprint, source_run_id=body.source_run_id,
        source_proof_fingerprint=body.expected_proof_fingerprint)
    require(fingerprint(value["goal"]) == fingerprint(goal) and fingerprint(draft["candidate"]["goal"]) == fingerprint(goal["snapshot"]["content"])
        and fingerprint(draft["candidate"]["task_proof"]["proof"]) == fingerprint(proof))
    if body.source_run_id:
        source_proof = verified_source(store, c, user, body.source_run_id, limits,
                                       expected_pid=draft["project_id"], initial_only=True)
        require(fingerprint(source_proof) == body.expected_proof_fingerprint
            and fingerprint(source_proof) == fingerprint(value["source_proof"]) and source_proof["project_id"] == draft["project_id"]
            and source_proof["resource_id"] != body.resource_id and source_proof["source_hash"] != source["hash"],
            "Extraction requires the exact complete task and fresh material")
    else:
        require(value["source_proof"] is None)
    return manifest, report, source, goal


def expected_lookup(source, term):
    if not term or term != term.strip() or len(term) > 80 or "\n" in term or "\r" in term:
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
    outputs: dict[str, dict] = {}
    proved: list[dict] = []
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
        proof = verified_source(store, c, user, source_run_id, limits, expected_pid=pid, initial_only=True) if source_run_id else None
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
        proof = verified_source(store, c, user, body.source_run_id, limits, expected_pid=pid, initial_only=True) if body.source_run_id else None
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
            request_key=body.request_key, request_fingerprint=fingerprint(body.model_dump()), request=body.model_dump(),
            runtime_id=runtime,
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


def bound(store, c, user, job, limits, *, validate_input=True):
    from . import app_jobs, lifecycle
    snapshot, app_run = app_jobs.load_binding(store, c, user, job, limits)
    accepted = c.execute(select(events.c.data).where(events.c.run_id == job["id"], events.c.kind == "ACCEPTED")).scalars().all()
    require(fingerprint(accepted) == fingerprint([dict(namespace=app_jobs.KIND,
        app_run_id=snapshot["app_run_id"], instance_id=snapshot["instance_id"],
        release_id=snapshot["release_id"], input_fingerprint=snapshot["request_fingerprint"])]),
        "Independent accepted header differs from the frozen exact input")
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
        and fingerprint(snapshot.get("text_goal")) == fingerprint(goal) and job["resource_refs"] == [source["resource_id"]]
        and len(contract.resources) == 1 and contract.resources[0].content_hash == source["hash"]
        and contract.resources[0].resource_id == source["resource_id"] and contract.resources[0].format == source["format"]
        and contract.mode == "mock" and contract.natural_planning is None and contract.application_generation is None,
        "Frozen current GoalCard or material binding changed")
    require(all(type(job["context"].get(k)) is int and job["context"][k] == 0
                for k in ("requests", "repairs", "reserved_tokens"))
        and type(job["context"].get("tools")) is int and 0 <= job["context"]["tools"] <= 4)
    require(c.execute(select(attempts.c.id).where(attempts.c.run_id == job["id"])).first() is None,
            "Four-step zero-model proof requires an empty actual Attempt ledger")
    if validate_input:
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
    outputs: dict[str, dict] = {}
    proved: list[dict] = []
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
    binding = binding or bound(store, c, user, job, limits, validate_input=False)
    try:
        validate_value(binding["draft"]["candidate"]["manifest"]["input_schema"], binding["snapshot"]["input"])
    except DomainError:
        require(job["status"] == binding["app_run"]["status"] == "FAILED"
            and job["error"] is not None and job["error"].get("code") == "INVALID_INPUT"
            and fingerprint(job["error"]) == fingerprint(binding["app_run"]["error"])
            and job["context"]["tools"] == 0
            and not c.execute(select(operations.c.id).where(operations.c.run_id == job["id"])).first()
            and not c.execute(select(events.c.id).where(events.c.run_id == job["id"], events.c.kind == "TEXT_WORKFLOW_SKIPPED")).first(),
            "Invalid-input history must have its actual empty failed execution")
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
            validate_value(binding["draft"]["candidate"]["manifest"]["output_schema"], a["output"])
            require(job["status"] == "SUCCEEDED" and len(rows) == 1 and fingerprint(a["output"]) == fingerprint(outputs["report"]))
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
        claimed = c.execute(select(events.c.id).where(events.c.run_id == job["id"], events.c.kind == "CLAIMED",
            events.c.data["fence"].as_integer() == job["fence"])).first() is not None
        current_steps = c.execute(select(events.c.id).where(events.c.run_id == job["id"],
            events.c.kind == "TEXT_WORKFLOW_STEP_VERIFIED", events.c.data["fence"].as_integer() == job["fence"])).first()
        just_claimed = job["status"] == "RUNNING" and a["status"] == "QUEUED" and claimed and current_steps is None
        # Commands/lost leases transition Run first; only their persisted command
        # or worker-loss metadata can explain a short state synchronization gap.
        gap = (job["status"] in {"QUEUED", "PAUSED", "WAITING_RESOURCE", "RECONCILING"}
            and a["status"] == "RUNNING" and c.execute(select(events.c.id).where(events.c.run_id == job["id"],
                events.c.kind == "WORKER_LOST", events.c.data["fence"].as_integer() == job["fence"])).first() is not None)
        require((a["status"] == job["status"] or just_claimed or gap)
            and fingerprint(a["error"]) == fingerprint(job["error"]), "AppRun state/error differs from accepted execution")
        require(job["status"] != "FAILED" or isinstance(job["error"], dict), "Failed text task requires its retained error")
    if require_success:
        require(job["status"] == "SUCCEEDED" and complete and "report" in outputs,
                "Only an actual complete successful four-step task can be extracted")
    return binding, outputs, proved


def verified_source(store, c, user, rid, limits, *, expected_pid=None, initial_only=False):
    # Independent owned instance/release metadata gates before source job bodies.
    from .text_continuations import job_gate
    pid = c.execute(select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)).scalar()
    if pid is None:
        raise DomainError("PERMISSION_DENIED")
    if expected_pid is not None and pid != expected_pid:
        raise DomainError("PERMISSION_DENIED", "Task source belongs to another project")
    store.own_project(c, user, pid)
    job_gate(store, c, user, rid)
    if initial_only:
        source_ref = c.execute(select(internal_releases.c.snapshot["draft"]["candidate"]["manifest"]["source_run_ref"].as_string())
            .join(internal_app_runs, internal_app_runs.c.release_id == internal_releases.c.id)
            .join(internal_run_bindings, internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
            .where(internal_run_bindings.c.run_id == rid, internal_app_runs.c.principal_id == user,
                internal_releases.c.principal_id == user, internal_releases.c.project_id == pid)).scalar()
        require(source_ref is None, "Only an initial actual task permits one extraction hop")
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
    # Three independent metadata anchors; a missing join must never hide history.
    app_ids = set(c.execute(select(internal_app_runs.c.id).where(
        internal_app_runs.c.instance_id == instance["id"])).scalars())
    bindings = c.execute(select(internal_run_bindings.c.run_id, internal_run_bindings.c.app_run_id,
        internal_run_bindings.c.snapshot["instance_id"].as_string().label("iid"))
        .where((internal_run_bindings.c.snapshot["instance_id"].as_string() == instance["id"])
            | internal_run_bindings.c.app_run_id.in_(app_ids))).mappings().all()
    accepted = c.execute(select(events.c.run_id, events.c.data["app_run_id"].as_string().label("aid"),
        events.c.data["instance_id"].as_string().label("iid"))
        .where(events.c.kind == "ACCEPTED", events.c.data["namespace"].as_string() == "INTERNAL_APPRUN",
            (events.c.data["instance_id"].as_string() == instance["id"])
            | events.c.data["app_run_id"].as_string().in_(app_ids)
            | events.c.run_id.in_([b["run_id"] for b in bindings]))).mappings().all()
    require(len(bindings) == len(app_ids) == len(accepted)
        and {b["app_run_id"] for b in bindings} == {a["aid"] for a in accepted} == app_ids
        and {b["run_id"] for b in bindings} == {a["run_id"] for a in accepted}
        and all(b["iid"] == instance["id"] for b in bindings)
        and all(a["iid"] == instance["id"] for a in accepted), "Independent text task history anchors differ")
    jobs = [b["run_id"] for b in bindings]
    scope_rows = c.execute(select(delivery_graph_requests.c.app_id, delivery_graph_requests.c.kind)
        .where(delivery_graph_requests.c.kind.in_([RUN_META, RUN_META + "_seal"]),
            delivery_graph_requests.c.snapshot["request"]["instance_id"].as_string() == instance["id"])).mappings().all()
    require(all({r["app_id"] for r in scope_rows if r["kind"] == kind} == set(jobs)
                for kind in (RUN_META, RUN_META + "_seal")), "Independent accepted text scope history differs")
    verified_ids = set()
    for rid in jobs:
        metadata = c.execute(select(runs.c.project_id, runs.c.principal_id).where(runs.c.id == rid)).mappings().first()
        require(metadata is not None and metadata["project_id"] == instance["project_id"] and metadata["principal_id"] == user)
        job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
            runs.c.project_id == instance["project_id"])).mappings().one()
        binding, _, _ = verify_job(store, c, user, job, limits)
        if job["status"] == "SUCCEEDED":
            verified_ids.add(binding["app_run"]["id"])
    require({r["run_id"] for r in records} == verified_ids, "Typed records and successful text tasks differ")
    require(type(instance["data_version"]) is int and instance["data_version"] == len(records)
        and [r["version"] for r in records] == list(range(1, len(records) + 1)), "Instance typed version sequence changed")


def commit_guard(worker, c, run, binding, delta=0):
    from .app_jobs import lock_live
    job = lock_live(worker.store, c, run)
    if worker.s.mode != "mock" or worker.s.live_enabled:
        raise DomainError("PERMISSION_DENIED", "Closed text workflow is offline engineering only")
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
        store.event(c, job["id"], "TEXT_WORKFLOW_STEP_VERIFIED", dict(step_id=step["step_id"], operation_id=oid, fence=live["fence"]))
        commit_guard(worker, c, run, binding)
        return True


def _sqlite_heartbeat_contention(store, exc):
    code = getattr(getattr(exc, "orig", None), "sqlite_errorcode", None)
    return (store.sqlite and isinstance(exc, OperationalError)
        and isinstance(exc.orig, sqlite3.Error) and type(code) is int
        and code & 255 in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED})


def publish_sync_renewal(worker, run, state, renewed):
    """Publish only after the original heartbeat transaction returned committed."""
    with state["lock"]:
        sequence = state.get("sync_renewal", {}).get("sequence", 0) + 1
        state["lease_until"] = max(state["lease_until"], renewed)
        state["sync_renewal"] = dict(sequence=sequence, worker_id=worker.id,
            run_id=run["id"], fence=run["fence"], lease_until=renewed)


def _renew_sync_locked(worker, run, state, *, deadline=None, lease_seconds=None):
    """Original guarded renewal; caller already holds the renewal writer lock."""
    with state["lock"]:
        fatal = state.get("fatal_heartbeat")
        bounds = [state["lease_until"], run["created_at"] + worker.s.run_seconds]
        if state["deadline"] is not None:
            bounds.append(state["deadline"])
    if fatal is not None:
        raise fatal
    if deadline is not None:
        bounds.append(deadline)
    cutoff = min(bounds)
    remaining = cutoff - time.time()
    if worker.stop.is_set() or remaining <= 0:
        raise DomainError("BUDGET_EXHAUSTED", "Original heartbeat interval ended")
    renewed = worker.store.heartbeat(worker.id, run["id"], run["fence"],
        worker.s.lease_seconds if lease_seconds is None else lease_seconds,
        _deadline=cutoff, _wait_seconds=min(5.0, remaining), _running_only=True)
    publish_sync_renewal(worker, run, state, renewed)
    return renewed


def renew_sync(worker, run, state, *, deadline=None, lease_seconds=None):
    """Serialize renewals through their actual commit and publication.

    Acquire this writer lock before opening a DB transaction. The short state
    lock remains safe for validation that already holds a DB transaction.
    """
    with state["lock"]:
        renewal_lock = state.setdefault("renewal_lock", threading.Lock())
    with renewal_lock:
        return _renew_sync_locked(worker, run, state, deadline=deadline, lease_seconds=lease_seconds)


@contextmanager
def natural_reservation_writer(worker, run, state, *, deadline):
    """Keep the original post-quota renewal and reservation writer together.

    The caller has finished quota waiting and has not opened its reservation
    transaction. Background renewal remains available throughout that wait.
    """
    with state["lock"]:
        renewal_lock = state.setdefault("renewal_lock", threading.Lock())
    with renewal_lock:
        _renew_sync_locked(worker, run, state, deadline=deadline)
        yield


def process_job(worker, run, advance_fn=None, *, _heartbeat_state=None):
    from .app_jobs import fail_job
    stopped = threading.Event()
    failed = threading.Event()
    failure = []
    failure_sequence = [0]
    state = _heartbeat_state or dict(lock=threading.Lock(),
        lease_until=run["lease_until"], deadline=None)
    state.setdefault("renewal_lock", threading.Lock())
    atomic_metadata = worker.store.sqlite and state.get("sync_contention_recovery") is True

    def beat():
        while not stopped.wait(worker.s.lease_seconds / 3):
            for attempt in range(3):
                if stopped.is_set() or worker.stop.is_set():
                    return
                with state["renewal_lock"] if atomic_metadata else nullcontext():
                    with state["lock"]:
                        deadline = state["deadline"]
                        cutoff = min(state["lease_until"], deadline) if deadline is not None else None
                    try:
                        options = {}
                        if cutoff is not None:
                            remaining = cutoff - time.time()
                            if remaining <= 0:
                                raise DomainError("BUDGET_EXHAUSTED", "Original heartbeat interval ended")
                            options = dict(_deadline=cutoff, _wait_seconds=min(5.0, remaining),
                                _running_only=True)
                        renewed = worker.store.heartbeat(worker.id, run["id"], run["fence"],
                            worker.s.lease_seconds, **options)
                    except Exception as exc:
                        # Re-read only numeric bounds after an identified lock
                        # error: validation or a committed sync renewal may have
                        # progressed while the driver was waiting.
                        contention = _sqlite_heartbeat_contention(worker.store, exc)
                        retry_cutoff = None
                        if contention:
                            with state["lock"]:
                                latest_deadline = state["deadline"]
                                latest_lease = state["lease_until"]
                            if latest_deadline is not None:
                                if deadline is not None:
                                    latest_deadline = min(deadline, latest_deadline)
                                retry_cutoff = min(latest_lease, latest_deadline)
                        if retry_cutoff is not None and time.time() + 0.1 < retry_cutoff:
                            if attempt < 2:
                                if stopped.wait(0.1):
                                    return
                                continue
                            if latest_lease > run["lease_until"]:
                                # This batch still failed. Already guarded sync
                                # progress in this invocation keeps the owner live;
                                # it need not coincide with this retry batch. Wait the original
                                # cadence before a new bounded batch, never fabricate
                                # heartbeat success or extend the interval locally.
                                logging.getLogger(__name__).info("heartbeat_contention_deferred", extra=dict(
                                    run_id=run["id"], fence=run["fence"], attempts=3,
                                    heartbeat_lease_until=latest_lease,
                                    heartbeat_deadline=latest_deadline))
                                break
                        logging.getLogger(__name__).info("heartbeat_background_halted", extra=dict(
                            run_id=run["id"], fence=run["fence"], error_type=type(exc).__name__))
                        with state["lock"]:
                            if atomic_metadata and not contention:
                                state["fatal_heartbeat"] = exc
                            failure_sequence[0] = state.get("sync_renewal", {}).get("sequence", 0)
                            failure.append(exc)
                            failed.set()
                        return
                    else:
                        if renewed is not None:
                            with state["lock"]:
                                state["lease_until"] = max(state["lease_until"], renewed)
                        break

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    observed_contention = False
    try:
        while True:
            if failed.is_set():
                # A SQLite lock failure can precede the foreground boundary's
                # actual, same-owner committed renewal. Numeric bounds alone
                # are insufficient: require its newer explicit commit marker.
                with state["lock"]:
                    renewed = dict(state.get("sync_renewal", {}))
                    deadline = state["deadline"]
                recovered = (worker.store.sqlite and state.get("sync_contention_recovery") is True
                    and _sqlite_heartbeat_contention(worker.store, failure[0])
                    and renewed.get("sequence", 0) > failure_sequence[0]
                    and renewed.get("worker_id") == worker.id
                    and renewed.get("run_id") == run["id"] and renewed.get("fence") == run["fence"]
                    and deadline is not None and not worker.stop.is_set()
                    and time.time() < min(renewed.get("lease_until", 0), deadline))
                if recovered:
                    logging.getLogger(__name__).info("heartbeat_contention_recovered", extra=dict(
                        run_id=run["id"], fence=run["fence"],
                        sync_renewal_sequence=renewed["sequence"],
                        heartbeat_lease_until=renewed["lease_until"]))
                    # The failed sender has no work after setting failed. A new
                    # sender starts with the original cadence, not another retry.
                    failure.clear()
                    failed.clear()
                    thread = threading.Thread(target=beat, daemon=True)
                    thread.start()
                    continue
                logging.getLogger(__name__).info("heartbeat_failure_observed", extra=dict(
                    run_id=run["id"], fence=run["fence"]))
                if _sqlite_heartbeat_contention(worker.store, failure[0]):
                    # A known driver lock failure ends this invocation; it is
                    # not an unexpected worker crash or proof of a known effect.
                    # The existing metadata writer alone decides ownership,
                    # stop intent and unknown-result settlement.
                    observed_contention = True
                    raise DomainError("RESOURCE_UNAVAILABLE", "Heartbeat renewal could not acquire the database lock") from failure[0]
                raise failure[0]
            again = (advance_fn or advance)(worker, run)
            # A completed terminal transaction wins over a late background
            # error; existing settlement/commit guards remain authoritative.
            if not again:
                break
    except DomainError as exc:
        try:
            fail_job(worker, run, exc)
        except Exception as settlement_error:
            if not (observed_contention
                    and _sqlite_heartbeat_contention(worker.store, settlement_error)):
                raise
            # No settlement committed. Leave the exact original Run and lease
            # for fenced recovery; do not retry, renew or fabricate a terminal.
            logging.getLogger(__name__).info("heartbeat_settlement_contended", extra=dict(
                run_id=run["id"], fence=run["fence"], error_type=type(settlement_error).__name__))
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

    @app.get("/api/internal/instances/{iid}/text-workflow-run-requests/{key}")
    def get_run_recover(iid: str, key: str, user=user_dependency):
        from . import app_jobs, lifecycle
        with store.tx() as c:
            i, release = lifecycle.instance(store, c, user, iid, limits)
            require(is_candidate(release["snapshot"]["draft"]["candidate"]))
            job_id = c.execute(select(internal_run_bindings.c.run_id)
                .join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
                .where(internal_app_runs.c.instance_id == iid, internal_app_runs.c.principal_id == user,
                    internal_app_runs.c.request_key == key)).scalar()
            if job_id is None:
                raise DomainError("OUTCOME_UNKNOWN", "No accepted Run for this original key")
        return app_jobs.inspect_job(store, user, job_id)
