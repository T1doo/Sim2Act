"""Shared sealed per-Run binding engine; distinct saved P-A/P-B provenance."""
import copy
import time
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import insert, select

from . import natural_specs as natural
from . import pa_spec_apps as spec
from . import pb_natural_specs as pb
from .contracts import Limits, Strict
from .db import (
    delivery_graph_requests,
    fingerprint,
    grants,
    internal_app_runs,
    internal_run_bindings,
    new_id,
    runs,
)
from .delivery_graph_apps import HASH, controlled
from .errors import DomainError
from .text_logic_reuse import KEY, pair, remember, require
from .text_workflows import RunScopeInput

VERSION = "pb-natural-per-run.v1"
USE, META = "pb_natural_use", "pb_natural_use_scope"
CONSENT = "RUN_THIS_SAVED_PB_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"
MAX = 64


class ReviewInput(Strict):
    expected_revision: int = Field(strict=True, ge=1)
    expected_release_fingerprint: str = Field(pattern=HASH)
    expected_app_fingerprint: str = Field(pattern=HASH)
    expected_recipe_fingerprint: str = Field(pattern=HASH)
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_goal_version: int = Field(strict=True, ge=1)
    expected_goal_fingerprint: str = Field(pattern=HASH)
    expected_source_hash: str = Field(pattern=HASH)
    request_key: str = Field(pattern=KEY)


class CommitInput(Strict):
    review: ReviewInput
    expected_review_fingerprint: str = Field(pattern=HASH)
    consent: Literal["RUN_THIS_SAVED_PB_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"]


PA_CONSENT = "RUN_THIS_SAVED_PA_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"


class PACommitInput(Strict):
    review: ReviewInput
    expected_review_fingerprint: str = Field(pattern=HASH)
    consent: Literal["RUN_THIS_SAVED_PA_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"]


@dataclass(frozen=True)
class Family:
    field: str
    namespace: str
    use: str
    meta: str
    consent: str
    body_type: type[CommitInput] | type[PACommitInput]
    route: str


PB = Family("pb_use", VERSION, USE, META, CONSENT, CommitInput, "pb-use")
PA = Family("pa_use", "pa-natural-per-run.v1", "pa_natural_use", "pa_natural_use_scope",
    PA_CONSENT, PACommitInput, "pa-use")
FAMILIES = (PB, PA)


def saved_family(candidate):
    if not natural.is_candidate(candidate):
        return None
    if candidate.get("spec_task", {}).get("kind") == pb.KIND:
        return PB
    if "spec_task" not in candidate and ("goal_application" in candidate or
            candidate.get("spec_binding", {}).get("kind") == spec.KIND):
        return PA
    return None


def base_audit(store, c, user, base, family):
    return (pb.audit_fingerprint if family == PB else spec.audit_fingerprint)(store, c, user, base)


def use_hint(c, rid, family=None):
    if family is None:
        return any(use_hint(c, rid, f) for f in FAMILIES)
    hinted = c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.app_id == rid,
        delivery_graph_requests.c.kind.in_([family.meta, family.meta + "_seal"]))).first()
    # Independent scalar identifiers prevent deleting both dedicated seals from
    # downgrading a per-use Run to its saved default target's authorization.
    hinted = hinted or c.execute(select(internal_run_bindings.c.snapshot[family.field]["review"]["resource_id"].as_string())
        .where(internal_run_bindings.c.run_id == rid)).scalar_one_or_none()
    hinted = hinted or c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.kind == family.use,
        delivery_graph_requests.c.snapshot["response"]["run_id"].as_string() == rid)).first()
    return bool(hinted)


@controlled
def scope_gate(store, c, user, rid, header):
    if not use_hint(c, rid):
        return False
    hints = [f for f in FAMILIES if use_hint(c, rid, f)]
    require(len(hints) == 1, "Exact per-use family required")
    family = hints[0]
    meta, seal = pair(c, user, rid, family.meta, "accepted", RunScopeInput)
    require(fingerprint(meta.model_dump()) == fingerprint(seal) and meta.run_id == rid
        and meta.principal_id == user == header["principal_id"]
        and meta.project_id == header["project_id"] and meta.runtime_id == header["runtime_id"])
    from .db import app_drafts
    accepted, accepted_seal = pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
    require(accepted.model_dump() == meta.model_dump() == accepted_seal)
    location = c.execute(select(app_drafts.c.candidate["namespace"].as_string().label("namespace"),
        app_drafts.c.candidate["spec_task"]["kind"].as_string().label("task"),
        app_drafts.c.candidate["spec_binding"]["kind"].as_string().label("binding"),
        app_drafts.c.candidate["goal_application"]["run_id"].as_string().label("generation"))
        .where(app_drafts.c.id == meta.app_id, app_drafts.c.project_id == meta.project_id,
        app_drafts.c.runtime_id == meta.runtime_id)).mappings().first()
    require(location is not None and location["namespace"] == natural.VERSION
        and (location["task"] == pb.KIND if family == PB else location["task"] is None
             and (location["binding"] == spec.KIND or location["generation"] is not None)))
    if family == PA:
        from .db import internal_instance_data, internal_instances
        base = c.execute(select(internal_run_bindings.c.snapshot["pa_base_data_version"].as_integer())
            .where(internal_run_bindings.c.run_id == rid)).scalar_one_or_none()
        live = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
        current = c.execute(select(internal_instances.c.data_version, internal_instances.c.source_app_id,
            internal_instances.c.project_id, internal_instances.c.runtime_id)
            .where(internal_instances.c.id == meta.instance_id, internal_instances.c.principal_id == user)).mappings().first()
        require(type(base) is int and base >= 0 and current is not None
            and current["source_app_id"] == meta.app_id and current["project_id"] == meta.project_id
            and current["runtime_id"] == meta.runtime_id)
        if live not in {"SUCCEEDED", "FAILED", "CANCELLED"} and current["data_version"] != base:
            own = c.execute(select(internal_app_runs.c.status, internal_app_runs.c.result_version)
                .where(internal_app_runs.c.id == meta.app_run_id, internal_app_runs.c.instance_id == meta.instance_id,
                    internal_app_runs.c.principal_id == user)).mappings().first()
            typed = c.execute(select(internal_instance_data.c.version).where(
                internal_instance_data.c.instance_id == meta.instance_id,
                internal_instance_data.c.run_id == meta.app_run_id)).scalars().all()
            require(current["data_version"] == base + 1 and own is not None and own["status"] == "SUCCEEDED"
                and own["result_version"] == base + 1 and typed == [base + 1], "Confirmed P-A result version competed")

    store.own_project(c, user, meta.project_id)
    store.authorize(c, user, meta.runtime_id, meta.project_id, meta.resource_id, natural.READ)
    store.authorize(c, user, meta.runtime_id, meta.project_id, meta.project_id, natural.SAVE)
    return True


def protected_instance(c, iid):
    """Independent identifier-only hints, never a material or result body."""
    from .db import app_drafts, internal_instances, internal_releases

    kind = c.execute(select(internal_releases.c.snapshot["draft"]["candidate"]["spec_task"]["kind"].as_string())
        .join(internal_instances, internal_instances.c.release_id == internal_releases.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    app_kind = c.execute(select(app_drafts.c.candidate["spec_task"]["kind"].as_string())
        .join(internal_instances, internal_instances.c.source_app_id == app_drafts.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    ledger = c.execute(select(delivery_graph_requests.c.app_id).where(
        ((delivery_graph_requests.c.app_id == iid) & delivery_graph_requests.c.kind.in_([f.use + suffix for f in FAMILIES for suffix in ("", "_seal")]))
        | (delivery_graph_requests.c.kind.in_([spec.RUN_META, spec.RUN_META + "_seal"])
           & (delivery_graph_requests.c.snapshot["request"]["instance_id"].as_string() == iid)))).first()
    overlay = c.execute(select(internal_run_bindings.c.run_id)
        .join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
        .where(internal_app_runs.c.instance_id == iid,
            ((internal_run_bindings.c.snapshot["pb_use"]["review"]["resource_id"].as_string().is_not(None))
             | (internal_run_bindings.c.snapshot["pa_use"]["review"]["resource_id"].as_string().is_not(None))))).first()
    release_namespace = c.execute(select(internal_releases.c.snapshot["draft"]["candidate"]["namespace"].as_string())
        .join(internal_instances, internal_instances.c.release_id == internal_releases.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    app_namespace = c.execute(select(app_drafts.c.candidate["namespace"].as_string())
        .join(internal_instances, internal_instances.c.source_app_id == app_drafts.c.id)
        .where(internal_instances.c.id == iid)).scalar_one_or_none()
    return release_namespace == natural.VERSION or app_namespace == natural.VERSION or kind == pb.KIND or app_kind == pb.KIND or bool(ledger or overlay)


@controlled
def data_scope_gate(store, c, user, iid, *, app_run_id=None):
    if not protected_instance(c, iid):
        return False
    if store is None or user is None:
        raise DomainError("PERMISSION_DENIED", "Protected history requires current target authority")
    from .db import internal_instance_data, internal_instances

    i = c.execute(select(internal_instances).where(internal_instances.c.id == iid,
        internal_instances.c.principal_id == user)).mappings().first()
    if i is None:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, i["project_id"])
    scope = internal_app_runs.c.instance_id == iid
    records_scope = internal_instance_data.c.instance_id == iid
    if app_run_id is not None:
        scope = scope & (internal_app_runs.c.id == app_run_id)
        records_scope = records_scope & (internal_instance_data.c.run_id == app_run_id)
    app_headers = c.execute(select(internal_app_runs.c.id, internal_app_runs.c.instance_id,
        internal_app_runs.c.principal_id, internal_app_runs.c.release_id, internal_app_runs.c.status,
        internal_app_runs.c.result_version).where(scope)).mappings().all()
    require(all(a["principal_id"] == user and a["instance_id"] == iid for a in app_headers))
    covered = {a["id"]: a for a in app_headers}
    record_headers = c.execute(select(internal_instance_data.c.run_id, internal_instance_data.c.release_id,
        internal_instance_data.c.version).where(records_scope)).mappings().all()
    require(all(r["run_id"] in covered and covered[r["run_id"]]["status"] == "SUCCEEDED"
        and covered[r["run_id"]]["release_id"] == r["release_id"]
        and covered[r["run_id"]]["result_version"] == r["version"] for r in record_headers),
        "Typed history is outside the accepted instance scope")
    spec.instance_scope_gate(store, c, user, i, app_run_id=app_run_id)
    return True


@controlled
def control_scope(store, c, user, rid, *, iid=None, lock=False):
    """Owner stop authority uses accepted identifiers, never protected bodies.

    Current resource authority is deliberately required by resume's job gate;
    pause/cancel remain possible after revocation or expiry.
    """
    from .db import events, internal_instances

    hint = c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.app_id == rid,
        delivery_graph_requests.c.kind.in_([spec.RUN_META, spec.RUN_META + "_seal"]))).first()
    association = c.execute(select(internal_run_bindings.c.snapshot["instance_id"].as_string())
        .where(internal_run_bindings.c.run_id == rid)).scalar_one_or_none()
    protected = association is not None and protected_instance(c, association)
    if not hint and not use_hint(c, rid) and not protected:
        return None
    q = select(runs.c.id, runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
        runs.c.request_key, runs.c.fingerprint, runs.c.status, runs.c.version, runs.c.cancel_intent)
    header = c.execute((q.with_for_update() if lock else q).where(runs.c.id == rid)).mappings().first()
    if header is None or header["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, header["project_id"])
    meta, seal_meta = pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
    require(meta.model_dump() == seal_meta and meta.run_id == rid
        and meta.principal_id == user and meta.project_id == header["project_id"]
        and meta.runtime_id == header["runtime_id"] and header["request_key"] == "internal:" + meta.app_run_id)
    if iid is not None and meta.instance_id != iid:
        raise DomainError("PERMISSION_DENIED")
    if use_hint(c, rid):
        hints = [f for f in FAMILIES if use_hint(c, rid, f)]
        require(len(hints) == 1)
        own, own_seal = pair(c, user, rid, hints[0].meta, "accepted", RunScopeInput)
        require(own.model_dump() == own_seal == meta.model_dump())
    instance = c.execute(select(internal_instances.c.project_id, internal_instances.c.runtime_id,
        internal_instances.c.source_app_id).where(internal_instances.c.id == meta.instance_id,
        internal_instances.c.principal_id == user)).mappings().first()
    require(instance is not None and instance["project_id"] == meta.project_id
        and instance["runtime_id"] == meta.runtime_id and instance["source_app_id"] == meta.app_id)
    fields = ["run_id", "app_run_id", "instance_id", "release_id", "principal_id", "project_id", "runtime_id", "request_fingerprint"]
    binding = c.execute(select(internal_run_bindings.c.fingerprint,
        *(internal_run_bindings.c.snapshot[k].as_string().label(k) for k in fields))
        .where(internal_run_bindings.c.run_id == rid, internal_run_bindings.c.app_run_id == meta.app_run_id)).mappings().first()
    app_run = c.execute(select(internal_app_runs.c.id, internal_app_runs.c.fingerprint,
        internal_app_runs.c.instance_id, internal_app_runs.c.principal_id, internal_app_runs.c.release_id)
        .where(internal_app_runs.c.id == meta.app_run_id)).mappings().first()
    require(binding is not None and app_run is not None and binding["fingerprint"] == header["fingerprint"]
        and all(binding[k] == getattr(meta, k) for k in fields if k != "request_fingerprint")
        and app_run["instance_id"] == meta.instance_id and app_run["principal_id"] == user
        and app_run["release_id"] == meta.release_id and app_run["fingerprint"] == binding["request_fingerprint"])
    accepted = c.execute(select(events.c.data["instance_id"].as_string().label("iid"),
        events.c.data["app_run_id"].as_string().label("aid")).where(events.c.run_id == rid,
        events.c.kind == "ACCEPTED", events.c.data["namespace"].as_string() == "INTERNAL_APPRUN")).mappings().all()
    require(len(accepted) == 1 and accepted[0]["iid"] == meta.instance_id and accepted[0]["aid"] == meta.app_run_id)
    return dict(header), dict(app_run)


@controlled
def review(store, c, user, instance, release, body, limits, *, runtime=None, approved_grants=None, family=PB, _logic_out=None):
    base = release["snapshot"]["draft"]
    saved = base["candidate"]
    logic_origin = release["snapshot"].get("natural_logic_source")
    if logic_origin is not None:
        from .natural_logic_patches import release_bound
        if (_logic_out is not None and _logic_out.get("_call_connection") is c
                and _logic_out.get("_call_transaction") is c.get_transaction()
                and c.get_transaction() is not None and _logic_out.get("principal_id") == user
                and _logic_out.get("platform_limits") == limits.model_dump()
                and _logic_out.get("release_id") == release["id"]
                and _logic_out.get("release_fingerprint") == release["fingerprint"]):
            saved = _logic_out["value"]["effective_candidate"]
        else:
            saved = release_bound(store,c,user,release,limits)[0]["candidate"]
    require(saved_family(base["candidate"]) == family
        and instance["source_app_id"] == base["id"] and instance["runtime_id"] == base["runtime_id"]
        and instance["revision"] == body.expected_revision
        and release["fingerprint"] == body.expected_release_fingerprint
        and base["fingerprint"] == body.expected_app_fingerprint
        and fingerprint(saved["spec_recipe"]) == body.expected_recipe_fingerprint)
    material, goal = spec.target(store, c, user, instance["project_id"], body.card_id,
        body.expected_goal_version, body.expected_goal_fingerprint, runtime, family=natural.VERSION)
    require(material["hash"] == body.expected_source_hash and material["resource_id"] == body.resource_id)
    declared = Limits(**saved["manifest"]["runtime_limits"])
    value = natural.expand(saved["spec_recipe"], base["id"], goal.card_id,
        base["project_id"], material["hash"], material["resource_id"], goal.snapshot["content"],
        declared, base["candidate"]["model_sample_check"]["sample_fingerprint"])
    if logic_origin is not None:
        value["logic_revision"] = copy.deepcopy(saved["logic_revision"])
        value["manifest"]["revision"] = 2
        value["actions"][2]["revision"] = 2
        value["manifest"]["action_bindings"][2]["revision"] = 2
    elif family == PB:
        value["manifest"]["origin"] = "task_run"
        value["manifest"]["source_run_ref"] = base["candidate"]["manifest"]["source_run_ref"]
        value["spec_task"] = {**base["candidate"]["spec_task"], "target_goal_fingerprint": goal.fingerprint}
    else:
        spec.verify_origin(store, c, user, base, limits)
        for marker in ("goal_application", "spec_binding"):
            if marker in base["candidate"]:
                value[marker] = copy.deepcopy(base["candidate"][marker])
    _, _, report = natural.compile_candidate(value, limits)
    grant_state = approved_grants
    if grant_state is None:
        grant_state = [{**dict(row), "effective": not row["revoked"] and row["expires_at"] > time.time()} for row in c.execute(select(grants).where(
            grants.c.principal_id == instance["runtime_id"],
            grants.c.project_id == instance["project_id"],
            grants.c.resource_id == material["resource_id"], grants.c.tool_ref == natural.READ)
            .order_by(grants.c.id)).mappings()]
    result = dict(approved_grant_state=grant_state, namespace=family.namespace, principal_id=user, project_id=instance["project_id"],
        app_id=base["id"], runtime_id=base["runtime_id"], instance_id=instance["id"],
        release_id=release["id"], release_fingerprint=release["fingerprint"],
        saved_app_fingerprint=base["fingerprint"], recipe_fingerprint=body.expected_recipe_fingerprint,
        source_run_id=base["candidate"]["manifest"]["source_run_ref"],
        source_audit_fingerprint=base_audit(store, c, user, base, family),
        request=body.model_dump(), target_goal=goal.model_dump(),
        variable_bindings=dict(resource_id=material["resource_id"], source_hash=material["hash"],
            format=material["format"], goal_id=goal.card_id, goal_version=goal.version),
        effective_candidate=value, effective_fingerprint=fingerprint(value), report=report,
        required_permissions=[dict(tool_ref=natural.READ, resource_ref=material["resource_id"]),
            dict(tool_ref=natural.SAVE, resource_ref=instance["project_id"])],
        preview=natural.preview(material, value, {}), consent=family.consent,
        new_model_requests=0, artifact_writes=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
        formal_publication_enabled=False)
    if logic_origin is not None:
        result["source_audit_fingerprint"] = fingerprint(dict(original=result["source_audit_fingerprint"],
            logic_origin=logic_origin,effective_fingerprint=fingerprint(saved)))
        result["saved_logic_source"] = dict(origin=copy.deepcopy(logic_origin),
            effective_fingerprint=fingerprint(saved),recipe_fingerprint=fingerprint(saved["spec_recipe"]))
    if family == PA:
        result.update(instance_data_version=instance["data_version"],
            saved_origin={k: copy.deepcopy(base["candidate"][k]) for k in ("goal_application", "spec_binding") if k in base["candidate"]},
            proposed_limits=declared.model_dump(), proposed_model_nodes=declared.max_requests,
            proposed_artifact_writes_at_most=1, real_model_allowance=0)
    return {**result, "review_fingerprint": fingerprint(result)}, material, goal


@controlled
def approve(store, c, user, instance, release, body, limits, *, family=PB):
    checked, material, goal = review(store, c, user, instance, release, body.review, limits, family=family)
    require(checked["review_fingerprint"] == body.expected_review_fingerprint)
    existing = c.execute(select(delivery_graph_requests.c.request_key).where(
        delivery_graph_requests.c.app_id == instance["id"], delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind == family.use)).all()
    if len(existing) >= MAX:
        raise DomainError("BUDGET_EXHAUSTED", "Finite per-instance use capacity exhausted")
    if c.execute(select(grants.c.id).where(grants.c.principal_id == instance["runtime_id"],
        grants.c.project_id == instance["project_id"], grants.c.resource_id == material["resource_id"],
        grants.c.tool_ref == natural.READ, grants.c.revoked.is_(False), grants.c.expires_at > time.time())).first() is None:
        c.execute(insert(grants).values(id=new_id("grant"), principal_id=instance["runtime_id"],
            project_id=instance["project_id"], resource_id=material["resource_id"], tool_ref=natural.READ,
            expires_at=time.time() + 86400, revision=1, revoked=False))
    checked_again, _, _ = review(store, c, user, instance, release, body.review, limits,
                                runtime=instance["runtime_id"], approved_grants=checked["approved_grant_state"], family=family)
    require(checked_again == checked)
    return checked, material, goal


def seal(c, user, base, snapshot, body, checked, *, family=PB):
    frozen = dict(run_id=snapshot["run_id"], app_run_id=snapshot["app_run_id"], reviewed=checked,
        request_fingerprint=fingerprint(body.model_dump()), review_fingerprint=checked["review_fingerprint"])
    remember(c, user, snapshot["instance_id"], family.use, body.review.request_key, body, frozen)
    meta = RunScopeInput(app_id=base["id"], principal_id=user, project_id=base["project_id"],
        runtime_id=base["runtime_id"], resource_id=checked["variable_bindings"]["resource_id"],
        run_id=snapshot["run_id"], instance_id=snapshot["instance_id"],
        app_run_id=snapshot["app_run_id"], release_id=snapshot["release_id"])
    remember(c, user, snapshot["run_id"], family.meta, "accepted", meta, meta.model_dump())


@controlled
def bound(store, c, user, job, snapshot, release, limits, *, family=PB, _logic_out=None):
    from .db import internal_instances
    body, frozen = pair(c, user, snapshot["instance_id"], family.use, snapshot[family.field]["review"]["request_key"], family.body_type)
    require(body.model_dump() == snapshot[family.field] and frozen["run_id"] == job["id"]
        and frozen["app_run_id"] == snapshot["app_run_id"])
    instance = c.execute(select(internal_instances).where(internal_instances.c.id == snapshot["instance_id"],
        internal_instances.c.principal_id == user, internal_instances.c.project_id == job["project_id"])).mappings().one()
    # Historic results retain their accepted revision; the existing commit guard
    # separately requires the live revision for any new side effect.
    accepted_instance = {**dict(instance), "revision": snapshot["expected_revision"],
                         "runtime_id": snapshot["runtime_id"], "source_app_id": release["snapshot"]["draft"]["id"]}
    if family == PA:
        accepted_instance["data_version"] = snapshot["pa_base_data_version"]
    checked, material, goal = review(store, c, user, accepted_instance, release, body.review, limits, runtime=job["runtime_id"], approved_grants=frozen["reviewed"]["approved_grant_state"], family=family,_logic_out=_logic_out)
    require(body.expected_review_fingerprint == checked["review_fingerprint"]
        and frozen["reviewed"] == checked and frozen["request_fingerprint"] == fingerprint(body.model_dump())
        and snapshot["pb_effective_fingerprint" if family == PB else "pa_effective_fingerprint"] == checked["effective_fingerprint"])
    draft = {**copy.deepcopy(release["snapshot"]["draft"]), "candidate": checked["effective_candidate"],
        "fingerprint": checked["effective_fingerprint"], family.field + "_run_id": job["id"]}
    manifest, _, report = natural.compile_candidate(draft["candidate"], limits)
    return draft, manifest, report, material, goal.model_dump()


@controlled
def audit(store, c, user, draft, *, family=PB):
    rid = draft[family.field + "_run_id"]
    header = c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id).where(runs.c.id == rid)).mappings().one()
    require(scope_gate(store, c, user, rid, header))
    from .db import app_drafts
    base = c.execute(select(app_drafts).where(app_drafts.c.id == draft["id"],
        app_drafts.c.project_id == draft["project_id"])).mappings().one()
    meta, seal_meta = pair(c, user, rid, family.meta, "accepted", RunScopeInput)
    snapshot = c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == rid)).scalar_one()
    body, frozen = pair(c, user, meta.instance_id, family.use, snapshot[family.field]["review"]["request_key"], family.body_type)
    require(("saved_logic_source" in frozen["reviewed"]) ==
        (body.review.expected_recipe_fingerprint != fingerprint(base["candidate"]["spec_recipe"])),
        "Changed recipe requires its independent logic source proof")
    if "saved_logic_source" in frozen["reviewed"]:
        from .lifecycle import read_release
        current: dict[str, Any] = {}
        release = read_release(store,c,user,meta.release_id,Limits(**snapshot["limits"]),_logic_out=current)
        require(release["fingerprint"] == frozen["reviewed"]["release_fingerprint"]
            == snapshot["expected_release_fp"])
        saved = current["value"]["effective_candidate"]
        require(frozen["reviewed"]["saved_logic_source"] == dict(
            origin=release["snapshot"]["natural_logic_source"],effective_fingerprint=fingerprint(saved),
            recipe_fingerprint=fingerprint(saved["spec_recipe"])), "Current logic source proof changed")
    return fingerprint(dict(base=base_audit(store, c, user, base, family), meta=meta.model_dump(),
        scope_seal=seal_meta, request=body.model_dump(), frozen=frozen))


def mount(app, store, limits, identity, *, family=PB):
    user_dep = Depends(identity)

    @app.post("/api/internal/instances/{iid}/" + family.route + "-reviews")
    def preview(iid: str, body: ReviewInput, user=user_dep):
        from .lifecycle import instance
        with store.tx() as c:
            i, release = instance(store, c, user, iid, limits)
            checked, _, _ = review(store, c, user, i, release, body, limits, family=family)
            return checked

    def run(iid: str, body: CommitInput | PACommitInput, user=user_dep):
        from .app_jobs import enqueue
        return enqueue(store, user, iid, body.review.expected_revision,
            body.review.expected_release_fingerprint, {}, body.review.request_key, limits, **{family.field: body},
            submission=dict(endpoint=family.route + "-runs", body=body.model_dump(exclude_unset=True)))

    # FastAPI receives the exact immutable family schema; the implementation has
    # an explicit static union rather than a variable used as a type annotation.
    run.__annotations__["body"] = family.body_type
    app.post("/api/internal/instances/{iid}/" + family.route + "-runs", status_code=202)(run)

    @app.get("/api/internal/instances/{iid}/" + family.route + "-requests/{key}")
    @controlled
    def recover(iid: str, key: str, user=user_dep):
        from .lifecycle import instance
        with store.tx() as c:
            i, release = instance(store, c, user, iid, limits)
            # Only the Run identifier is inspected before target authorization.
            rid = c.execute(select(delivery_graph_requests.c.snapshot["response"]["run_id"].as_string()).where(
                delivery_graph_requests.c.app_id == iid, delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind == family.use, delivery_graph_requests.c.request_key == key)).scalar_one_or_none()
            if rid is None:
                raise DomainError("OUTCOME_UNKNOWN", "No accepted use for this original key")
            require(spec.job_scope_gate(store, c, user, rid))
            body, frozen = pair(c, user, iid, family.use, key, family.body_type)
            require(frozen["run_id"] == rid)
            job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
                runs.c.project_id == i["project_id"])).mappings().one()
            binding, _, _ = spec.verify_job(store, c, user, job, limits)
            return dict(namespace=family.namespace, request=body.model_dump(), request_key=key,
                **frozen, principal_id=user, project_id=i["project_id"], app_id=i["source_app_id"],
                instance_id=iid, release_id=binding["release"]["id"], status=job["status"],
                effective_fingerprint=binding["draft"]["fingerprint"], new_model_requests=0,
                semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)
