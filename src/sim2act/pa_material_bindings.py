"""P-A model graph reused with explicit typed material/Goal slots.

This is not completed-task P-B extraction. The original received model candidate
and confirmation remain provenance; only named identity/material/Goal slots vary.
No canonical graph factory, old report output or new provider request is used.
"""

import copy
import time
from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select

from .contracts import GoalCardRunSource, Strict
from .db import (
    app_drafts,
    fingerprint,
    goal_application_candidates,
    goal_cards,
    grants,
    new_id,
    principals,
    runs,
    task_extractions,
)
from .delivery_graph_apps import controlled
from .errors import DomainError
from .goals import validate_card_version
from .text_logic_reuse import pair, remember, require
from .tools import authorized_read

VERSION = "pa-model-literal-material-binding.v1"
KIND = "pa_model_literal_material_binding.v1"
META, BIND = "pa_model_binding_metadata", "pa_model_binding_request"
CONSENT = "REUSE_ONLY_THIS_MODEL_GRAPH_WITH_THIS_EXPLICIT_TARGET_GOAL_AND_NEW_MATERIAL"


class BindInput(Strict):
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_goal_version: int = Field(strict=True, ge=1)
    expected_goal_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_model_candidate_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_graph_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    name: str = Field(min_length=1, max_length=100)
    consent: Literal["REUSE_ONLY_THIS_MODEL_GRAPH_WITH_THIS_EXPLICIT_TARGET_GOAL_AND_NEW_MATERIAL"]
    request_key: str = Field(min_length=1, max_length=100)


class Metadata(Strict):
    app_id: str
    principal_id: str
    project_id: str
    runtime_id: str
    resource_id: str
    source_run_id: str


def executable(candidate):
    require(set(candidate) == {"namespace", "pa_binding", "manifest", "actions", "source_hash", "goal"}
        and candidate["namespace"] == VERSION)
    return {k: copy.deepcopy(candidate[k]) for k in ("manifest", "actions", "source_hash", "goal")}


@controlled
def compile_candidate(candidate, limits):
    from .apps import compile_preview

    return compile_preview(executable(candidate), limits)


def slots(raw, *, aid="APP_SLOT", action_id="ACTION_SLOT", resource="RESOURCE_SLOT", source_hash="HASH_SLOT", goal="GOAL_SLOT", card_id="CARD_SLOT"):
    """Closed typed paths only. Every other byte/value is preserved from the model."""
    value = copy.deepcopy(raw)
    manifest, action = value["manifest"], value["actions"][0]
    manifest["app_id"], action["action_id"] = aid, action_id
    manifest["action_bindings"][0]["action_id"] = action_id
    manifest["goal_ref"] = card_id
    manifest["data_bindings"][0]["resource_ref"] = resource
    for permission in manifest["permission_requirements"] + action["permission_requirements"]:
        permission["resource_ref"] = resource
    action["dependencies"][0]["ref"] = resource
    for dependency in manifest["dependency_lock"]:
        if dependency["kind"] == "resource":
            dependency["ref"] = resource
    value["source_hash"], value["goal"] = source_hash, copy.deepcopy(goal)
    return value


@controlled
def scope_gate(store, c, user, aid):
    location = c.execute(select(app_drafts.c.project_id, app_drafts.c.runtime_id,
        app_drafts.c.candidate["namespace"].as_string().label("namespace"),
        app_drafts.c.candidate["pa_binding"]["kind"].as_string().label("binding"))
        .where(app_drafts.c.id == aid)).mappings().first()
    marker = c.execute(select(task_extractions.c.snapshot["kind"].as_string()).where(task_extractions.c.app_id == aid)).scalar()
    # Unrelated families must retain their own authorization-before-ledger gate.
    # Three projected family identifiers survive individual marker removal; do
    # not probe a full P-A ledger merely to classify an unrelated CSV draft.
    hinted = (location and (location["namespace"] == VERSION or location["binding"] == KIND)) or marker == KIND
    if not hinted:
        return False
    require(location is not None)
    store.own_project(c, user, location["project_id"])
    meta, result = pair(c, user, aid, META, "scope", Metadata)
    require(fingerprint(meta.model_dump()) == fingerprint(result) and marker == KIND
        and meta.app_id == aid and meta.principal_id == user
        and meta.project_id == location["project_id"] and meta.runtime_id == location["runtime_id"])
    store.authorize(c, user, meta.runtime_id, meta.project_id, meta.resource_id, "resource.read")
    return True


@controlled
def model_source(store, c, user, rid, limits, expected_pid=None, *, family="literal"):
    from .goal_applications import verified_candidate

    metadata = c.execute(select(runs.c.project_id, runs.c.principal_id, runs.c.runtime_id, runs.c.resource_refs)
        .where(runs.c.id == rid)).mappings().first()
    if (metadata is None or metadata["principal_id"] != user
        or (expected_pid is not None and metadata["project_id"] != expected_pid)):
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, metadata["project_id"])
    require(len(metadata["resource_refs"]) == 1)
    store.authorize(c, user, metadata["runtime_id"], metadata["project_id"], metadata["resource_refs"][0], "resource.read")
    confirmed = c.execute(select(goal_application_candidates).where(
        goal_application_candidates.c.run_id == rid, goal_application_candidates.c.principal_id == user)).mappings().first()
    require(confirmed is not None, "Only an explicitly confirmed P-A model candidate can be rebound")
    run = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user)).mappings().one()
    raw = verified_candidate(store, c, run, limits)
    if family == "spec":
        require(raw.get("namespace") in {"pa-spec-checklist-app.v1", "pa-natural-spec-app.v1"})
    else:
        require(family == "literal" and raw.get("namespace") is None and len(raw.get("actions", [])) == 1
            and raw["actions"][0].get("executor", {}).get("ref") == "text.literal_evidence")
    from .apps import load_draft

    original, _, _, _ = load_draft(store, c, user, confirmed["app_id"], limits)
    require(run["status"] == "PARTIAL" and run["error"] is None and not run["cancel_intent"]
        and original["candidate"].get("goal_application") == {"run_id": rid, "candidate_fingerprint": fingerprint(raw)}
        and confirmed["candidate_fingerprint"] == fingerprint(raw))
    return raw, metadata


@controlled
def target(store, c, user, pid, cid, version=None, goal_fp=None, runtime=None):
    head = c.execute(select(goal_cards).where(goal_cards.c.id == cid, goal_cards.c.project_id == pid)).mappings().first()
    if head is None:
        raise DomainError("PERMISSION_DENIED")
    require(version is None or version == head["version"])
    require(goal_fp is None or goal_fp == head["fingerprint"])
    # The references are identifiers only; authorize before full Goal history.
    from .db import goal_card_versions
    refs = c.execute(select(goal_card_versions.c.snapshot["content"]["resource_refs"])
        .where(goal_card_versions.c.card_id == cid, goal_card_versions.c.version == head["version"])).scalar()
    require(isinstance(refs, list) and len(refs) == 1)
    project = store.own_project(c, user, pid)
    material = authorized_read(store, c, user, runtime or project["runtime_id"], pid,
        "resource.read", {"resource_id": refs[0]})
    require(material["format"] in {"txt", "md"} and len(material["content"].encode()) <= 4096
        and len(material["content"].splitlines()) <= 64, "Finite TXT/MD literal report only")
    saved = validate_card_version(store, c, user, cid, head["version"])
    require(saved["snapshot"]["resource_snapshots"] == [{"resource_id": refs[0],
        "hash": material["hash"], "format": material["format"]}]
        and saved["fingerprint"] == head["fingerprint"] == fingerprint(saved["snapshot"]))
    return material, GoalCardRunSource(card_id=cid, version=head["version"], fingerprint=head["fingerprint"], snapshot=saved["snapshot"])


@controlled
def options(store, user, pid, rid, cid, limits):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        raw, metadata = model_source(store, c, user, rid, limits, pid)
        material, goal = target(store, c, user, pid, cid)
        require(material["resource_id"] != metadata["resource_refs"][0]
            and material["hash"] != raw["source_hash"], "Explicit different material is required")
        return dict(namespace=VERSION, project_id=pid, source_run_id=rid, model_candidate_fingerprint=fingerprint(raw),
            graph_fingerprint=fingerprint(slots(raw)), model_graph=slots(raw), target_goal=goal.model_dump(),
            resource_id=material["resource_id"], source_hash=material["hash"], model_requests=0,
            semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False,
            boundary="Reuse the received model graph; target Goal is explicitly human-bound, semantic understanding unverified; source remains an authorized audit dependency.")


def candidate(raw, body, goal, resource_id, aid, action_id):
    value = slots(raw, aid=aid, action_id=action_id, resource=resource_id,
        source_hash=body.expected_source_hash, goal=goal.snapshot["content"], card_id=goal.card_id)
    require(fingerprint(slots(value)) == fingerprint(slots(raw)) == body.expected_graph_fingerprint)
    return dict(namespace=VERSION, **value, pa_binding=dict(kind=KIND,
        model_candidate_fingerprint=body.expected_model_candidate_fingerprint,
        graph_fingerprint=body.expected_graph_fingerprint, target_goal_fingerprint=goal.fingerprint))


@controlled
def verify(store, c, user, draft, limits):
    scope_gate(store, c, user, draft["id"])
    marker = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"],
        task_extractions.c.principal_id == user)).mappings().first()
    require(marker is not None)
    body, frozen = pair(c, user, draft["id"], BIND, marker["request_key"], BindInput)
    meta, metadata_result = pair(c, user, draft["id"], META, "scope", Metadata)
    require(set(frozen) == {"kind", "app_id", "project_id", "runtime_id", "action_id", "resource_id",
        "candidate_fingerprint", "source_run_id", "request_fingerprint", "request_key"}
        and fingerprint(meta.model_dump()) == fingerprint(metadata_result)
        and meta.source_run_id == frozen["source_run_id"] == marker["task_id"]
        and meta.resource_id == frozen["resource_id"] and body.request_key == frozen["request_key"] == marker["request_key"]
        and frozen["request_fingerprint"] == fingerprint(body.model_dump()))
    require(fingerprint(frozen) == fingerprint(marker["snapshot"])
        and marker["request_fingerprint"] == fingerprint(body.model_dump())
        and frozen["kind"] == KIND and frozen["app_id"] == draft["id"]
        and frozen["project_id"] == draft["project_id"] and frozen["runtime_id"] == draft["runtime_id"])
    raw, metadata = model_source(store, c, user, marker["task_id"], limits, draft["project_id"])
    material, goal = target(store, c, user, draft["project_id"], body.card_id,
        body.expected_goal_version, body.expected_goal_fingerprint, draft["runtime_id"])
    require(material["resource_id"] != metadata["resource_refs"][0] and material["hash"] != raw["source_hash"]
        and material["hash"] == body.expected_source_hash
        and fingerprint(raw) == body.expected_model_candidate_fingerprint)
    wanted = candidate(raw, body, goal, material["resource_id"], draft["id"], frozen["action_id"])
    require(fingerprint(wanted) == fingerprint(draft["candidate"]) == draft["fingerprint"] == frozen["candidate_fingerprint"])
    compile_candidate(wanted, limits)
    return frozen


@controlled
def bind(store, user, pid, rid, body, limits):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        raw, metadata = model_source(store, c, user, rid, limits, pid)
        material, goal = target(store, c, user, pid, body.card_id, body.expected_goal_version, body.expected_goal_fingerprint)
        require(material["resource_id"] != metadata["resource_refs"][0] and material["hash"] != raw["source_hash"]
            and material["hash"] == body.expected_source_hash and fingerprint(raw) == body.expected_model_candidate_fingerprint
            and fingerprint(slots(raw)) == body.expected_graph_fingerprint and body.name.strip())
        old = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
            task_extractions.c.principal_id == user, task_extractions.c.request_key == body.request_key)).scalar()
        if old:
            from .apps import load_draft
            draft, _, _, _ = load_draft(store, c, user, old, limits)
            prior, _ = pair(c, user, old, BIND, body.request_key, BindInput)
            require(fingerprint(prior.model_dump()) == fingerprint(body.model_dump()))
            return receipt(verify(store, c, user, draft, limits), body, cached=True)
        if len(c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
            task_extractions.c.principal_id == user)).all()) >= 64:
            raise DomainError("BUDGET_EXHAUSTED", "Finite P-A model bindings exhausted")
        aid, action_id, runtime, gid = new_id("app"), new_id("action"), new_id("appruntime"), new_id("grant")
        value = candidate(raw, body, goal, material["resource_id"], aid, action_id)
        compile_candidate(value, limits)
        frozen = dict(kind=KIND, app_id=aid, project_id=pid, runtime_id=runtime,
            action_id=action_id, resource_id=material["resource_id"], candidate_fingerprint=fingerprint(value),
            source_run_id=rid, request_fingerprint=fingerprint(body.model_dump()), request_key=body.request_key)
        c.execute(insert(principals).values(id=runtime, name="P-A model graph target reader", token_hash=None))
        c.execute(insert(grants).values(id=gid, principal_id=runtime, project_id=pid,
            resource_id=material["resource_id"], tool_ref="resource.read", expires_at=time.time() + 86400,
            revision=1, revoked=False))
        c.execute(insert(app_drafts).values(id=aid, project_id=pid, runtime_id=runtime,
            name=body.name, candidate=value, fingerprint=fingerprint(value), created_at=time.time()))
        c.execute(insert(task_extractions).values(task_id=rid, principal_id=user, request_key=body.request_key,
            request_fingerprint=fingerprint(body.model_dump()), app_id=aid, snapshot=frozen))
        meta = Metadata(app_id=aid, principal_id=user, project_id=pid, runtime_id=runtime,
            resource_id=material["resource_id"], source_run_id=rid)
        remember(c, user, aid, META, "scope", meta, meta.model_dump())
        remember(c, user, aid, BIND, body.request_key, body, frozen)
        draft = dict(id=aid, project_id=pid, runtime_id=runtime, candidate=value, fingerprint=fingerprint(value))
        verify(store, c, user, draft, limits)
        return receipt(frozen, body, cached=False)


def receipt(frozen, body, *, cached):
    return dict(namespace=VERSION, id=frozen["app_id"], project_id=frozen["project_id"],
        runtime_id=frozen["runtime_id"], candidate_fingerprint=frozen["candidate_fingerprint"],
        source_run_id=frozen["source_run_id"], request_key=body.request_key,
        request_fingerprint=fingerprint(body.model_dump()), model_requests=0,
        semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False, cached=cached)


@controlled
def recover(store, user, pid, rid, key, limits):
    with store.tx() as c:
        store.own_project(c, user, pid)
        aid = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.task_id == rid,
            task_extractions.c.principal_id == user, task_extractions.c.request_key == key)).scalar()
        if aid is None:
            raise DomainError("OUTCOME_UNKNOWN", "No P-A binding for this original request key")
        from .apps import load_draft
        location = c.execute(select(app_drafts.c.project_id).where(app_drafts.c.id == aid)).scalar()
        if location != pid:
            raise DomainError("PERMISSION_DENIED")
        draft, _, _, _ = load_draft(store, c, user, aid, limits)
        require(draft["project_id"] == pid)
        body, _ = pair(c, user, aid, BIND, key, BindInput)
        return receipt(verify(store, c, user, draft, limits), body, cached=True)


@controlled
def source_index(store, user, pid, limits):
    with store.tx() as c:
        store.own_project(c, user, pid)
        ids = c.execute(select(goal_application_candidates.c.run_id).join(runs,
            runs.c.id == goal_application_candidates.c.run_id).where(runs.c.project_id == pid,
            runs.c.principal_id == user, goal_application_candidates.c.principal_id == user)
            .order_by(runs.c.created_at.desc()).limit(64)).scalars().all()
        result = []
        for rid in ids:
            try:
                raw, _ = model_source(store, c, user, rid, limits, pid)
                result.append(dict(run_id=rid, model_candidate_fingerprint=fingerprint(raw),
                    graph_fingerprint=fingerprint(slots(raw)), model="intern-s2",
                    step_ids=[s["step_id"] for s in raw["manifest"]["workflow"]]))
            except DomainError:
                continue
        return dict(project_id=pid, namespace=VERSION, options=result, new_model_requests=0)
