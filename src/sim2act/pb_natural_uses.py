"""Explicit per-Run target bindings for one saved P-B app and immutable Release."""
import copy
import time
from typing import Literal

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


@controlled
def scope_gate(store, c, user, rid, header):
    hinted = c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.app_id == rid,
        delivery_graph_requests.c.kind.in_([META, META + "_seal"]))).first()
    # Independent scalar identifiers prevent deleting both dedicated seals from
    # downgrading a per-use Run to its saved default target's authorization.
    hinted = hinted or c.execute(select(internal_run_bindings.c.snapshot["pb_use"]["review"]["resource_id"].as_string())
        .where(internal_run_bindings.c.run_id == rid)).scalar_one_or_none()
    hinted = hinted or c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.kind == USE,
        delivery_graph_requests.c.snapshot["response"]["run_id"].as_string() == rid)).first()
    if not hinted:
        return False
    meta, seal = pair(c, user, rid, META, "accepted", RunScopeInput)
    require(fingerprint(meta.model_dump()) == fingerprint(seal) and meta.run_id == rid
        and meta.principal_id == user == header["principal_id"]
        and meta.project_id == header["project_id"] and meta.runtime_id == header["runtime_id"])
    from .db import app_drafts
    accepted, accepted_seal = pair(c, user, rid, spec.RUN_META, "accepted", RunScopeInput)
    require(accepted.model_dump() == meta.model_dump() == accepted_seal)
    require(c.execute(select(app_drafts.c.candidate["spec_task"]["kind"].as_string()).where(
        app_drafts.c.id == meta.app_id, app_drafts.c.project_id == meta.project_id,
        app_drafts.c.runtime_id == meta.runtime_id)).scalar_one_or_none() == pb.KIND)
    store.own_project(c, user, meta.project_id)
    store.authorize(c, user, meta.runtime_id, meta.project_id, meta.resource_id, natural.READ)
    store.authorize(c, user, meta.runtime_id, meta.project_id, meta.project_id, natural.SAVE)
    return True


@controlled
def review(store, c, user, instance, release, body, limits, *, runtime=None, approved_grants=None):
    base = release["snapshot"]["draft"]
    require(base["candidate"].get("spec_task", {}).get("kind") == pb.KIND
        and instance["source_app_id"] == base["id"] and instance["runtime_id"] == base["runtime_id"]
        and instance["revision"] == body.expected_revision
        and release["fingerprint"] == body.expected_release_fingerprint
        and base["fingerprint"] == body.expected_app_fingerprint
        and fingerprint(base["candidate"]["spec_recipe"]) == body.expected_recipe_fingerprint)
    material, goal = spec.target(store, c, user, instance["project_id"], body.card_id,
        body.expected_goal_version, body.expected_goal_fingerprint, runtime, family=natural.VERSION)
    require(material["hash"] == body.expected_source_hash and material["resource_id"] == body.resource_id)
    declared = Limits(**base["candidate"]["manifest"]["runtime_limits"])
    value = natural.expand(base["candidate"]["spec_recipe"], base["id"], goal.card_id,
        base["project_id"], material["hash"], material["resource_id"], goal.snapshot["content"],
        declared, base["candidate"]["model_sample_check"]["sample_fingerprint"])
    value["manifest"]["origin"] = "task_run"
    value["manifest"]["source_run_ref"] = base["candidate"]["manifest"]["source_run_ref"]
    value["spec_task"] = {**base["candidate"]["spec_task"], "target_goal_fingerprint": goal.fingerprint}
    _, _, report = natural.compile_candidate(value, limits)
    grant_state = approved_grants
    if grant_state is None:
        grant_state = [{**dict(row), "effective": not row["revoked"] and row["expires_at"] > time.time()} for row in c.execute(select(grants).where(
            grants.c.principal_id == instance["runtime_id"],
            grants.c.project_id == instance["project_id"],
            grants.c.resource_id == material["resource_id"], grants.c.tool_ref == natural.READ)
            .order_by(grants.c.id)).mappings()]
    result = dict(approved_grant_state=grant_state, namespace=VERSION, principal_id=user, project_id=instance["project_id"],
        app_id=base["id"], runtime_id=base["runtime_id"], instance_id=instance["id"],
        release_id=release["id"], release_fingerprint=release["fingerprint"],
        saved_app_fingerprint=base["fingerprint"], recipe_fingerprint=body.expected_recipe_fingerprint,
        source_run_id=value["manifest"]["source_run_ref"],
        source_audit_fingerprint=pb.audit_fingerprint(store, c, user, base),
        request=body.model_dump(), target_goal=goal.model_dump(),
        variable_bindings=dict(resource_id=material["resource_id"], source_hash=material["hash"],
            format=material["format"], goal_id=goal.card_id, goal_version=goal.version),
        effective_candidate=value, effective_fingerprint=fingerprint(value), report=report,
        required_permissions=[dict(tool_ref=natural.READ, resource_ref=material["resource_id"]),
            dict(tool_ref=natural.SAVE, resource_ref=instance["project_id"])],
        preview=natural.preview(material, value, {}), consent=CONSENT,
        new_model_requests=0, artifact_writes=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
        formal_publication_enabled=False)
    return {**result, "review_fingerprint": fingerprint(result)}, material, goal


@controlled
def approve(store, c, user, instance, release, body, limits):
    checked, material, goal = review(store, c, user, instance, release, body.review, limits)
    require(checked["review_fingerprint"] == body.expected_review_fingerprint)
    existing = c.execute(select(delivery_graph_requests.c.request_key).where(
        delivery_graph_requests.c.app_id == instance["id"], delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind == USE)).all()
    if len(existing) >= MAX:
        raise DomainError("BUDGET_EXHAUSTED", "Finite per-instance P-B use capacity exhausted")
    if c.execute(select(grants.c.id).where(grants.c.principal_id == instance["runtime_id"],
        grants.c.project_id == instance["project_id"], grants.c.resource_id == material["resource_id"],
        grants.c.tool_ref == natural.READ, grants.c.revoked.is_(False), grants.c.expires_at > time.time())).first() is None:
        c.execute(insert(grants).values(id=new_id("grant"), principal_id=instance["runtime_id"],
            project_id=instance["project_id"], resource_id=material["resource_id"], tool_ref=natural.READ,
            expires_at=time.time() + 86400, revision=1, revoked=False))
    checked_again, _, _ = review(store, c, user, instance, release, body.review, limits,
                                runtime=instance["runtime_id"], approved_grants=checked["approved_grant_state"])
    require(checked_again == checked)
    return checked, material, goal


def seal(c, user, base, snapshot, body, checked):
    frozen = dict(run_id=snapshot["run_id"], app_run_id=snapshot["app_run_id"], reviewed=checked,
        request_fingerprint=fingerprint(body.model_dump()), review_fingerprint=checked["review_fingerprint"])
    remember(c, user, snapshot["instance_id"], USE, body.review.request_key, body, frozen)
    meta = RunScopeInput(app_id=base["id"], principal_id=user, project_id=base["project_id"],
        runtime_id=base["runtime_id"], resource_id=checked["variable_bindings"]["resource_id"],
        run_id=snapshot["run_id"], instance_id=snapshot["instance_id"],
        app_run_id=snapshot["app_run_id"], release_id=snapshot["release_id"])
    remember(c, user, snapshot["run_id"], META, "accepted", meta, meta.model_dump())


@controlled
def bound(store, c, user, job, snapshot, release, limits):
    from .db import internal_instances
    body, frozen = pair(c, user, snapshot["instance_id"], USE, snapshot["pb_use"]["review"]["request_key"], CommitInput)
    require(body.model_dump() == snapshot["pb_use"] and frozen["run_id"] == job["id"]
        and frozen["app_run_id"] == snapshot["app_run_id"])
    instance = c.execute(select(internal_instances).where(internal_instances.c.id == snapshot["instance_id"],
        internal_instances.c.principal_id == user, internal_instances.c.project_id == job["project_id"])).mappings().one()
    # Historic results retain their accepted revision; the existing commit guard
    # separately requires the live revision for any new side effect.
    accepted_instance = {**dict(instance), "revision": snapshot["expected_revision"],
                         "runtime_id": snapshot["runtime_id"], "source_app_id": release["snapshot"]["draft"]["id"]}
    checked, material, goal = review(store, c, user, accepted_instance, release, body.review, limits, runtime=job["runtime_id"], approved_grants=frozen["reviewed"]["approved_grant_state"])
    require(body.expected_review_fingerprint == checked["review_fingerprint"]
        and frozen["reviewed"] == checked and frozen["request_fingerprint"] == fingerprint(body.model_dump())
        and snapshot["pb_effective_fingerprint"] == checked["effective_fingerprint"])
    draft = {**copy.deepcopy(release["snapshot"]["draft"]), "candidate": checked["effective_candidate"],
        "fingerprint": checked["effective_fingerprint"], "pb_use_run_id": job["id"]}
    manifest, _, report = natural.compile_candidate(draft["candidate"], limits)
    return draft, manifest, report, material, goal.model_dump()


@controlled
def audit(store, c, user, draft):
    rid = draft["pb_use_run_id"]
    header = c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id).where(runs.c.id == rid)).mappings().one()
    require(scope_gate(store, c, user, rid, header))
    from .db import app_drafts
    base = c.execute(select(app_drafts).where(app_drafts.c.id == draft["id"],
        app_drafts.c.project_id == draft["project_id"])).mappings().one()
    meta, seal_meta = pair(c, user, rid, META, "accepted", RunScopeInput)
    snapshot = c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == rid)).scalar_one()
    body, frozen = pair(c, user, meta.instance_id, USE, snapshot["pb_use"]["review"]["request_key"], CommitInput)
    return fingerprint(dict(base=pb.audit_fingerprint(store, c, user, base), meta=meta.model_dump(),
        scope_seal=seal_meta, request=body.model_dump(), frozen=frozen))


def mount(app, store, limits, identity):
    user_dep = Depends(identity)

    @app.post("/api/internal/instances/{iid}/pb-use-reviews")
    def preview(iid: str, body: ReviewInput, user=user_dep):
        from .lifecycle import instance
        with store.tx() as c:
            i, release = instance(store, c, user, iid, limits)
            checked, _, _ = review(store, c, user, i, release, body, limits)
            return checked

    @app.post("/api/internal/instances/{iid}/pb-use-runs", status_code=202)
    def run(iid: str, body: CommitInput, user=user_dep):
        from .app_jobs import enqueue
        return enqueue(store, user, iid, body.review.expected_revision,
            body.review.expected_release_fingerprint, {}, body.review.request_key, limits, pb_use=body)

    @app.get("/api/internal/instances/{iid}/pb-use-requests/{key}")
    @controlled
    def recover(iid: str, key: str, user=user_dep):
        from .lifecycle import instance
        with store.tx() as c:
            i, release = instance(store, c, user, iid, limits)
            # Only the Run identifier is inspected before target authorization.
            rid = c.execute(select(delivery_graph_requests.c.snapshot["response"]["run_id"].as_string()).where(
                delivery_graph_requests.c.app_id == iid, delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind == USE, delivery_graph_requests.c.request_key == key)).scalar_one_or_none()
            if rid is None:
                raise DomainError("OUTCOME_UNKNOWN", "No accepted use for this original key")
            require(spec.job_scope_gate(store, c, user, rid))
            body, frozen = pair(c, user, iid, USE, key, CommitInput)
            require(frozen["run_id"] == rid)
            job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
                runs.c.project_id == i["project_id"])).mappings().one()
            binding, _, _ = spec.verify_job(store, c, user, job, limits)
            return dict(namespace=VERSION, request=body.model_dump(), request_key=key,
                **frozen, principal_id=user, project_id=i["project_id"], app_id=i["source_app_id"],
                instance_id=iid, release_id=binding["release"]["id"], status=job["status"],
                effective_fingerprint=binding["draft"]["fingerprint"], new_model_requests=0,
                semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)
