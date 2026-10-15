"""Explicit P-B extraction of one proved natural-spec Run, never cached answers.

The editable recipe is bounded by the source budget and existing codec. A review
is read-only; its exact fingerprint is rederived under the project transaction.
Source lineage remains authorized audit evidence, not runtime inference input.
"""

import copy
import time
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import insert, select

from . import natural_specs as natural
from .contracts import Limits, Strict
from .db import (
    app_drafts,
    attempts,
    events,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    local_effects,
    new_id,
    operation_intents,
    operations,
    principals,
    reservations,
    run_contracts,
    runs,
    task_extractions,
)
from .delivery_graph_apps import HASH, controlled
from .errors import DomainError
from .pa_material_bindings import Metadata
from .text_logic_reuse import KEY, pair, remember, require

VERSION = "pb-natural-spec-extraction.v1"
KIND = "pb_natural_spec_task.v1"
META, EXTRACT = "pb_natural_spec_metadata", "pb_natural_spec_extract"
CONSENT = "EXTRACT_THIS_SUCCESSFUL_NATURAL_SPEC_RUN_WITH_THIS_REVIEW_AND_TARGET"
MAX = 64


class ReviewInput(Strict):
    source_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    expected_source_proof_fingerprint: str = Field(pattern=HASH)
    expected_source_recipe_fingerprint: str = Field(pattern=HASH)
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_goal_version: int = Field(strict=True, ge=1)
    expected_goal_fingerprint: str = Field(pattern=HASH)
    expected_source_hash: str = Field(pattern=HASH)
    recipe: natural.Recipe
    name: str = Field(min_length=1, max_length=100)
    request_key: str = Field(pattern=KEY)


class ExtractInput(Strict):
    review: ReviewInput
    expected_review_fingerprint: str = Field(pattern=HASH)
    consent: Literal["EXTRACT_THIS_SUCCESSFUL_NATURAL_SPEC_RUN_WITH_THIS_REVIEW_AND_TARGET"]
    artifact_write_consent: Literal[
        "ALLOW_ONLY_THIS_APP_TO_SAVE_VALIDATED_CHECKLIST_JSON_IN_THIS_PROJECT"
    ]


def source_gate(store, c, user, pid, rid):
    """Scalar classification bounds lineage depth before any protected Run body."""
    from . import pa_spec_apps as spec
    from .db import delivery_graph_requests
    from .text_workflows import RunScopeInput

    store.own_project(c, user, pid)
    header = c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id)
                       .where(runs.c.id == rid)).mappings().first()
    if header is None or header["principal_id"] != user or header["project_id"] != pid:
        raise DomainError("PERMISSION_DENIED")
    apps = c.execute(select(app_drafts.c.id,
        app_drafts.c.candidate["namespace"].as_string().label("family"),
        app_drafts.c.candidate["manifest"]["origin"].as_string().label("origin"),
        app_drafts.c.candidate["spec_task"]["kind"].as_string().label("task"))
        .where(app_drafts.c.runtime_id == header["runtime_id"],
               app_drafts.c.project_id == pid)).mappings().all()
    require(len(apps) == 1 and apps[0]["family"] == natural.VERSION
            and apps[0]["origin"] == "goal" and apps[0]["task"] is None,
            "Only an original natural-spec successful task may be extracted; no extraction chains")
    aid = apps[0]["id"]
    kind = c.execute(select(task_extractions.c.snapshot["kind"].as_string())
                     .where(task_extractions.c.app_id == aid)).scalar()
    require(kind in {None, spec.KIND})
    require(c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.app_id == aid,
        delivery_graph_requests.c.kind.in_([META, META + "_seal", EXTRACT, EXTRACT + "_seal"])
    )).first() is None, "P-B lineage cannot be disguised as P-A")
    require(spec.job_scope_gate(store, c, user, rid))
    require(c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == "SUCCEEDED",
            "Only a completed successful task is a P-B source")
    # Independent committed metadata must agree before any source Run/receipt body.
    scope, seal = pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
    require(fingerprint(scope.model_dump()) == fingerprint(seal))
    saved = c.execute(select(local_effects.c.resource_id).join(operations,
        operations.c.id == local_effects.c.operation_id).where(operations.c.run_id == rid,
        operations.c.tool_ref == natural.SAVE, operations.c.status == "VERIFIED")).scalars().all()
    committed = c.execute(select(events.c.data["artifact_resource"].as_string()).where(
        events.c.run_id == rid, events.c.kind == "SPEC_COMMITTED")).scalars().all()
    output = c.execute(select(internal_app_runs.c.output["resource_id"].as_string()).where(
        internal_app_runs.c.id == scope.app_run_id,
        internal_app_runs.c.instance_id == scope.instance_id)).scalars().all()
    typed = c.execute(select(internal_instance_data.c.data["result"]["resource_id"].as_string()).where(
        internal_instance_data.c.run_id == scope.app_run_id,
        internal_instance_data.c.instance_id == scope.instance_id)).scalars().all()
    require(len(saved) == 1 and saved == committed == output == typed and saved[0],
            "Independent committed source artifact pointers differ")
    store.authorize(c, user, header["runtime_id"], pid, saved[0], natural.READ)



def source_audit(store, c, user, pid, rid):
    """Fresh scope-qualified bytes, no replay cache or cross-transaction reuse.

    Full source replay precedes entry and follows final writes. Each intervening
    commit guard still authorizes before reading and compares every source byte.
    """
    from . import pa_spec_apps as spec
    from .db import delivery_graph_requests, goal_card_versions, goal_cards
    from .text_workflows import RunScopeInput

    source_gate(store, c, user, pid, rid)
    scope, seal = pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
    original = c.execute(select(app_drafts).where(app_drafts.c.id == scope.app_id,
        app_drafts.c.project_id == pid, app_drafts.c.runtime_id == scope.runtime_id)).mappings().one()
    require("spec_task" not in original["candidate"])
    rows = dict(scope=scope.model_dump(), seal=seal,
                original_audit=spec.audit_fingerprint(store, c, user, original))
    queries = {
        "run": select(runs).where(runs.c.id == rid, runs.c.principal_id == user, runs.c.project_id == pid),
        "contract": select(run_contracts).where(run_contracts.c.run_id == rid),
        "binding": select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid),
        "app_run": select(internal_app_runs).join(internal_instances,
            internal_instances.c.id == internal_app_runs.c.instance_id).where(
            internal_app_runs.c.id == scope.app_run_id, internal_app_runs.c.instance_id == scope.instance_id,
            internal_instances.c.principal_id == user, internal_instances.c.project_id == pid),
        "typed": select(internal_instance_data).where(
            internal_instance_data.c.instance_id == scope.instance_id,
            internal_instance_data.c.run_id == scope.app_run_id),
        "release": select(internal_releases).where(internal_releases.c.id == scope.release_id,
            internal_releases.c.principal_id == user, internal_releases.c.project_id == pid),
        "attempts": select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.id),
        "operations": select(operations).where(operations.c.run_id == rid).order_by(operations.c.id),
        "intents": select(operation_intents).join(operations,
            operations.c.id == operation_intents.c.operation_id).where(operations.c.run_id == rid)
            .order_by(operation_intents.c.operation_id),
        "effects": select(local_effects).join(operations,
            operations.c.id == local_effects.c.operation_id).where(operations.c.run_id == rid)
            .order_by(local_effects.c.operation_id),
        "events": select(events).where(events.c.run_id == rid).order_by(events.c.id),
        "reservations": select(reservations).where(reservations.c.run_id == rid).order_by(reservations.c.id),
    }
    queries["origin_marker"] = select(task_extractions).where(task_extractions.c.app_id == scope.app_id,
        task_extractions.c.principal_id == user)
    queries["origin_seals"] = select(delivery_graph_requests).where(
        delivery_graph_requests.c.app_id == scope.app_id,
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind.in_([spec.META, spec.META + "_seal", spec.BIND, spec.BIND + "_seal"])
        ).order_by(delivery_graph_requests.c.kind, delivery_graph_requests.c.request_key)
    contract = c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid)).scalar_one()
    goal_id = contract["goal"]["goal_id"]
    queries["current_goal"] = select(goal_cards).where(goal_cards.c.id == goal_id,
        goal_cards.c.project_id == pid)
    queries["current_goal_versions"] = select(goal_card_versions).join(goal_cards,
        goal_cards.c.id == goal_card_versions.c.card_id).where(goal_cards.c.id == goal_id,
        goal_cards.c.project_id == pid).order_by(goal_card_versions.c.version)
    rows["original"] = dict(original)
    for name, query in queries.items():
        rows[name] = [dict(row) for row in c.execute(query).mappings()]
    return fingerprint(rows)


def scope_gate(store, c, user, aid, location):
    """Called by spec dispatch before full candidate or extraction ledger reads."""
    store.own_project(c, user, location["project_id"])
    store.authorize(c, user, location["runtime_id"], location["project_id"],
                    location["resource"], natural.READ)
    store.authorize(c, user, location["runtime_id"], location["project_id"],
                    location["project_id"], natural.SAVE)
    kind = c.execute(select(task_extractions.c.snapshot["kind"].as_string())
                     .where(task_extractions.c.app_id == aid)).scalar()
    require(kind == KIND and location["family"] == natural.VERSION and location["task"] == KIND)
    meta, seal = pair(c, user, aid, META, "scope", Metadata)
    require(fingerprint(meta.model_dump()) == fingerprint(seal)
            and meta.app_id == aid and meta.principal_id == user
            and meta.project_id == location["project_id"]
            and meta.runtime_id == location["runtime_id"] and meta.resource_id == location["resource"])
    source_gate(store, c, user, meta.project_id, meta.source_run_id)
    return True


@controlled
def source(store, c, user, pid, rid, limits):
    from . import pa_spec_apps as spec

    source_gate(store, c, user, pid, rid)
    status = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
    require(status == "SUCCEEDED", "Only a completed successful task is a P-B source")
    job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
                                     runs.c.project_id == pid)).mappings().one()
    binding, _, proved = spec.verify_job(store, c, user, job, limits)
    draft, snap, app_run = binding["draft"], binding["snapshot"], binding["app_run"]
    require(natural.is_candidate(draft["candidate"]) and "spec_task" not in draft["candidate"])
    typed = c.execute(select(internal_instance_data).where(
        internal_instance_data.c.instance_id == snap["instance_id"],
        internal_instance_data.c.run_id == app_run["id"])).mappings().one()
    proof = dict(version=VERSION, principal_id=user, project_id=pid, source_run_id=rid,
        source_app_id=draft["id"], source_app_fingerprint=draft["fingerprint"],
        instance_id=snap["instance_id"], app_run_id=app_run["id"], release_id=snap["release_id"],
        release_fingerprint=binding["release"]["fingerprint"], result_version=app_run["result_version"],
        goal_fingerprint=binding["goal"]["fingerprint"], source_hash=binding["source"]["hash"],
        recipe_fingerprint=fingerprint(draft["candidate"]["spec_recipe"]),
        run_fingerprint=fingerprint(dict(job)), binding_fingerprint=fingerprint(snap),
        app_run_fingerprint=fingerprint(dict(app_run)), typed_fingerprint=fingerprint(dict(typed)),
        output_fingerprint=fingerprint(app_run["output"]),
        receipt_fingerprint=fingerprint(proved), audit_fingerprint=binding["audit_fingerprint"],
        runtime_audit_fingerprint=source_audit(store, c, user, pid, rid),
        citation_status="PASS", semantic_status="UNKNOWN", owner_acceptance="PENDING")
    return binding, proof


def candidate(body, proof, material, goal, aid, pid, limits):
    recipe = body.recipe.model_dump(exclude_none=True)
    value = natural.expand(recipe, aid, goal.card_id, pid, material["hash"], material["resource_id"],
                           goal.snapshot["content"], limits, proof["output_fingerprint"])
    value["manifest"]["origin"] = "task_run"
    value["manifest"]["source_run_ref"] = body.source_run_id
    value["spec_task"] = dict(kind=KIND, source_run_id=body.source_run_id,
        source_proof_fingerprint=fingerprint(proof), source_recipe_fingerprint=proof["recipe_fingerprint"],
        edited_recipe_fingerprint=fingerprint(recipe), target_goal_fingerprint=goal.fingerprint)
    return value


def review(store, c, user, pid, body, limits, runtime=None):
    from . import pa_spec_apps as spec

    binding, proof = source(store, c, user, pid, body.source_run_id, limits)
    require(fingerprint(proof) == body.expected_source_proof_fingerprint
            and proof["recipe_fingerprint"] == body.expected_source_recipe_fingerprint)
    material, goal = spec.target(store, c, user, pid, body.card_id, body.expected_goal_version,
        body.expected_goal_fingerprint, runtime, family=natural.VERSION)
    require(goal.card_id != binding["goal"]["card_id"] and body.name.strip()
            and material["resource_id"] != binding["source"]["resource_id"]
            and material["hash"] != binding["source"]["hash"]
            and material["hash"] == body.expected_source_hash,
            "An explicit different current Goal and material are required")
    aid = "app_" + fingerprint(dict(kind=KIND, user=user, project=pid, request=body.model_dump()))[:32]
    runtime_id = "appruntime_" + fingerprint(dict(kind=KIND, app=aid))[:32]
    approved = Limits(**binding["draft"]["candidate"]["manifest"]["runtime_limits"])
    value = candidate(body, proof, material, goal, aid, pid, approved)
    _, _, report = natural.compile_candidate(value, limits)
    result = dict(namespace=VERSION, principal_id=user, project_id=pid, source_run_id=body.source_run_id,
        request=body.model_dump(), request_fingerprint=fingerprint(body.model_dump()),
        source_proof=proof, source_proof_fingerprint=fingerprint(proof),
        original_recipe=binding["draft"]["candidate"]["spec_recipe"],
        original_recipe_fingerprint=proof["recipe_fingerprint"],
        edited_recipe=body.recipe.model_dump(exclude_none=True),
        edited_recipe_fingerprint=fingerprint(body.recipe.model_dump(exclude_none=True)),
        edited_recipe_execution="NOT_RUN", sample_scope="SUCCESSFUL_SOURCE_ONLY",
        target_goal=goal.model_dump(),
        variable_bindings=dict(source=dict(binding_id="source", resource_id=material["resource_id"],
            source_hash=material["hash"], format=material["format"]),
            goal=dict(card_id=goal.card_id, version=goal.version, fingerprint=goal.fingerprint)),
        candidate=value, candidate_fingerprint=fingerprint(value), app_id=aid, runtime_id=runtime_id,
        report=report, approved_source_limits=approved.model_dump(),
        preview=natural.preview(material, value, {}), consent=CONSENT,
        artifact_write_consent=natural.CONSENT, new_model_requests=0, project_writes=0,
        semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)
    return {**result, "review_fingerprint": fingerprint(result)}, material, goal


def frozen_for(user, pid, body, checked):
    return dict(kind=KIND, principal_id=user, project_id=pid, app_id=checked["app_id"],
        runtime_id=checked["runtime_id"], source_run_id=body.review.source_run_id,
        request_key=body.review.request_key, request_fingerprint=fingerprint(body.model_dump()),
        review_fingerprint=checked["review_fingerprint"], candidate_fingerprint=checked["candidate_fingerprint"],
        source_proof_fingerprint=checked["source_proof_fingerprint"],
        approved_source_limits=checked["approved_source_limits"])


@controlled
def verify(store, c, user, draft, limits):
    from . import pa_spec_apps as spec

    require(spec.scope_gate(store, c, user, draft["id"]))
    marker = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"])).mappings().one()
    body, frozen = pair(c, user, draft["id"], EXTRACT, marker["request_key"], ExtractInput)
    meta, _ = pair(c, user, draft["id"], META, "scope", Metadata)
    require(marker["principal_id"] == user and marker["task_id"] == body.review.source_run_id == meta.source_run_id
            and marker["request_key"] == body.review.request_key
            and marker["request_fingerprint"] == fingerprint(body.model_dump()))
    checked, material, goal = review(store, c, user, draft["project_id"], body.review, limits, draft["runtime_id"])
    require(body.expected_review_fingerprint == checked["review_fingerprint"]
            and frozen == frozen_for(user, draft["project_id"], body, checked)
            and fingerprint(marker["snapshot"]) == fingerprint(frozen)
            and draft["id"] == checked["app_id"] and draft["runtime_id"] == checked["runtime_id"]
            and fingerprint(draft["candidate"]) == draft["fingerprint"] == checked["candidate_fingerprint"]
            and c.execute(select(app_drafts.c.name).where(app_drafts.c.id == draft["id"])).scalar_one() == body.review.name
            and meta.resource_id == material["resource_id"])
    manifest, _, report = natural.compile_candidate(draft["candidate"], limits)
    return manifest, report, material, goal.model_dump()


def audit_fingerprint(store, c, user, draft):
    from . import pa_spec_apps as spec

    require(spec.scope_gate(store, c, user, draft["id"]))
    meta, meta_seal = pair(c, user, draft["id"], META, "scope", Metadata)
    marker = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"])).mappings().one()
    body, frozen = pair(c, user, draft["id"], EXTRACT, marker["request_key"], ExtractInput)
    actual = c.execute(select(app_drafts).where(app_drafts.c.id == draft["id"],
        app_drafts.c.project_id == draft["project_id"], app_drafts.c.runtime_id == draft["runtime_id"])).mappings().one()
    return fingerprint(dict(source_audit=source_audit(store, c, user, draft["project_id"], meta.source_run_id),
        metadata=meta.model_dump(), metadata_seal=meta_seal,
        marker=dict(marker), request=body.model_dump(), frozen=frozen, draft=dict(actual)))


def receipt(body, checked, frozen):
    return dict(namespace=VERSION, id=frozen["app_id"], **frozen, request=body.model_dump(),
        reviewed=checked, new_model_requests=0, project_writes=0,
        semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)


@controlled
def extract(store, user, pid, rid, body, limits):
    with store.tx() as c:
        return _extract(store, c, user, pid, rid, body, limits)


@controlled
def _extract(store, c, user, pid, rid, body, limits):
    """Original extraction write group, shared with the bounded trial controller."""
    from .apps import load_draft

    require(c.in_transaction())
    store.lock_project(c, user, pid)
    require(body.review.source_run_id == rid)
    checked, material, _ = review(store, c, user, pid, body.review, limits)
    require(checked["review_fingerprint"] == body.expected_review_fingerprint)
    prior = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
        task_extractions.c.principal_id == user, task_extractions.c.request_key == body.review.request_key)).scalar()
    if prior:
        draft, _, _, _ = load_draft(store, c, user, prior, limits)
        old, frozen = pair(c, user, prior, EXTRACT, body.review.request_key, ExtractInput)
        require(old.model_dump() == body.model_dump())
        return receipt(body, checked, frozen)
    if len(c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
        task_extractions.c.principal_id == user)).all()) >= MAX:
        raise DomainError("BUDGET_EXHAUSTED", "Finite P-B source extraction capacity exhausted")
    aid, runtime = checked["app_id"], checked["runtime_id"]
    frozen = frozen_for(user, pid, body, checked)
    c.execute(insert(principals).values(id=runtime, name="P-B natural spec target runtime"))
    for ref, tool in [(material["resource_id"], natural.READ), (pid, natural.SAVE)]:
        c.execute(insert(grants).values(id=new_id("grant"), principal_id=runtime, project_id=pid,
            resource_id=ref, tool_ref=tool, expires_at=time.time() + 86400, revision=1, revoked=False))
    c.execute(insert(app_drafts).values(id=aid, project_id=pid, runtime_id=runtime, name=body.review.name,
        candidate=checked["candidate"], fingerprint=checked["candidate_fingerprint"], created_at=time.time()))
    c.execute(insert(task_extractions).values(task_id=rid, principal_id=user,
        request_key=body.review.request_key, request_fingerprint=fingerprint(body.model_dump()),
        app_id=aid, snapshot=frozen))
    meta = Metadata(app_id=aid, principal_id=user, project_id=pid, runtime_id=runtime,
                    resource_id=material["resource_id"], source_run_id=rid)
    remember(c, user, aid, META, "scope", meta, meta.model_dump())
    remember(c, user, aid, EXTRACT, body.review.request_key, body, frozen)
    # Fresh final origin, target, seals, budget and exact candidate verification.
    draft, _, _, _ = load_draft(store, c, user, aid, limits)
    verify(store, c, user, draft, limits)
    return receipt(body, checked, frozen)

def mount(app, store, limits, identity):
    user_dependency = Depends(identity)

    @app.get("/api/projects/{pid}/natural-spec-task-runs/{rid}/extraction-options")
    def options(pid: str, rid: str, user=user_dependency):
        with store.tx() as c:
            binding, proof = source(store, c, user, pid, rid, limits)
            return dict(namespace=VERSION, principal_id=user, project_id=pid, source_run_id=rid,
                source_proof=proof, source_proof_fingerprint=fingerprint(proof),
                recipe=copy.deepcopy(binding["draft"]["candidate"]["spec_recipe"]),
                recipe_fingerprint=proof["recipe_fingerprint"],
                approved_source_limits=binding["draft"]["candidate"]["manifest"]["runtime_limits"],
                new_model_requests=0, project_writes=0, semantic_status="UNKNOWN",
                owner_acceptance="PENDING", formal_publication_enabled=False)

    @app.post("/api/projects/{pid}/natural-spec-task-runs/{rid}/extraction-reviews")
    def preview(pid: str, rid: str, body: ReviewInput, user=user_dependency):
        with store.tx() as c:
            store.lock_project(c, user, pid)
            require(body.source_run_id == rid)
            checked, _, _ = review(store, c, user, pid, body, limits)
            return checked

    @app.post("/api/projects/{pid}/natural-spec-task-runs/{rid}/extractions", status_code=201)
    def create(pid: str, rid: str, body: ExtractInput, user=user_dependency):
        return extract(store, user, pid, rid, body, limits)

    @app.get("/api/projects/{pid}/natural-spec-task-runs/{rid}/extractions/by-key/{key}")
    def recover(pid: str, rid: str, key: str, user=user_dependency):
        from .apps import load_draft

        with store.tx() as c:
            source_gate(store, c, user, pid, rid)
            aid = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
                task_extractions.c.principal_id == user, task_extractions.c.request_key == key)).scalar()
            if aid is None:
                raise DomainError("OUTCOME_UNKNOWN", "Only read this original extraction key; do not resend")
            draft, _, _, _ = load_draft(store, c, user, aid, limits)
            body, frozen = pair(c, user, aid, EXTRACT, key, ExtractInput)
            require(draft["project_id"] == pid and body.review.source_run_id == rid)
            checked, _, _ = review(store, c, user, pid, body.review, limits, draft["runtime_id"])
            verify(store, c, user, draft, limits)
            return receipt(body, checked, frozen)
