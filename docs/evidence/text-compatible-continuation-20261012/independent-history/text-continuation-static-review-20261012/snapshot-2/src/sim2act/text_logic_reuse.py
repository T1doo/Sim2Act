"""Explicit independent authority for one finite, content-free literal recipe.

Source lineage is verified only when minting. Subsequent loads use independent
authority and two sealed receipts, never the original private source tables.
"""

import copy
import math
import re
import time
from typing import Literal

from pydantic import Field
from sqlalchemy import func, insert, select, update

from . import delivery_graph_apps as graph
from . import text_apps
from .apps import compile_preview, load_draft, object_schema
from .contracts import Limits, Strict
from .csv_logic_reuse import implementation
from .db import (
    app_drafts,
    fingerprint,
    goal_application_candidates,
    grants,
    internal_approvals,
    internal_releases,
    new_id,
    principals,
    task_extractions,
)
from .errors import DomainError
from .registered_request_recovery import _scope
from .registered_run_extraction import TEXT_PROOF, verified_source
from .tools import authorized_read

VERSION = "internal.text-data-free-logic.v1"
AUTH = "text_logic_authority"
BIND = "text_logic_binding"
REVOKE = "text_logic_revocation"
KIND = "text_data_free_binding.v1"
PROOF = "authorized_data_free_text_logic.v1"
SCOPE = "EXISTING_AUTHORIZED_TXT_MD_SAME_OWNER_PROJECT"
TTL = 86400
MAX_LOGICS = MAX_BINDINGS = 64
RELEASE_INDEX = "text_logic_release_index"
KEY = r"^[A-Za-z0-9_-]{1,100}$"


class AuthorizeInput(Strict):
    expected_proof_fingerprint: str = Field(pattern=graph.HASH)
    expected_release_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["AUTHORIZE_DATA_FREE_TEXT_LOGIC_IN_THIS_PROJECT"]
    request_key: str = Field(pattern=KEY)


class BindInput(Strict):
    expected_logic_fingerprint: str = Field(pattern=graph.HASH)
    target_app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    expected_target_draft_fingerprint: str = Field(pattern=graph.HASH)
    expected_resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=graph.HASH)
    name: str = Field(min_length=1, max_length=200)
    consent: Literal["CREATE_NEW_READ_ONLY_RUNTIME_FOR_THIS_TEXT_RESOURCE"]
    request_key: str = Field(pattern=KEY)


class RevokeInput(Strict):
    expected_logic_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["REVOKE_DATA_FREE_TEXT_LOGIC"]
    request_key: str = Field(pattern=KEY)


class ReleaseIndex(Strict):
    namespace: Literal["internal.text-logic-release-index.v1"]
    release_id: str = Field(pattern=r"^irelease_[a-f0-9]{32}$")
    approval_id: str = Field(pattern=r"^iapproval_[a-f0-9]{32}$")
    release_fingerprint: str = Field(pattern=graph.HASH)
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    candidate_fingerprint: str = Field(pattern=graph.HASH)
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    owner_id: str = Field(pattern=r"^user_[a-f0-9]{32}$")
    logic_id: str = Field(pattern=r"^textlogic_[a-f0-9]{32}$")
    logic_fingerprint: str = Field(pattern=graph.HASH)


def independent(draft):
    return draft["candidate"].get("task_proof", {}).get("proof", {}).get("kind") == PROOF


def release_index(row):
    draft = row["snapshot"]["draft"]
    proof = draft["candidate"]["task_proof"]["proof"]
    return ReleaseIndex(namespace="internal.text-logic-release-index.v1",
        release_id=row["id"], approval_id=row["approval_id"], release_fingerprint=row["fingerprint"],
        app_id=draft["id"], candidate_fingerprint=draft["fingerprint"], project_id=row["project_id"],
        owner_id=row["principal_id"], logic_id=proof["logic_id"], logic_fingerprint=proof["logic_fingerprint"])


def record_release_index(c, user, row):
    body = release_index(row)
    remember(c, user, body.app_id, RELEASE_INDEX, body.release_id, body, body.model_dump())


@graph.controlled
def verify_release_index(c, user, row):
    expected = release_index(row)
    body, frozen = pair(c, user, expected.app_id, RELEASE_INDEX, expected.release_id, ReleaseIndex)
    require(fingerprint(body.model_dump()) == fingerprint(expected.model_dump()) == fingerprint(frozen))


@graph.controlled
def release_ids(store, c, user, draft, limits):
    from .db import delivery_graph_requests

    verify_candidate(store, c, user, draft, limits)
    rows = c.execute(select(delivery_graph_requests.c.request_key, delivery_graph_requests.c.kind).where(
        delivery_graph_requests.c.app_id == draft["id"], delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind.in_([RELEASE_INDEX, RELEASE_INDEX + "_seal"]))).mappings().all()
    left = {r["request_key"] for r in rows if r["kind"] == RELEASE_INDEX}
    right = {r["request_key"] for r in rows if r["kind"] == RELEASE_INDEX + "_seal"}
    require(left == right)
    for rid in sorted(left):
        body, frozen = pair(c, user, draft["id"], RELEASE_INDEX, rid, ReleaseIndex)
        require(body.release_id == rid and body.app_id == draft["id"] and body.owner_id == user
                and body.project_id == draft["project_id"] and body.candidate_fingerprint == draft["fingerprint"]
                and fingerprint(body.model_dump()) == fingerprint(frozen))
        # Metadata scope before reading any Release or approval snapshot.
        actual = c.execute(select(internal_releases.c.approval_id, internal_releases.c.fingerprint,
            internal_releases.c.project_id, internal_releases.c.principal_id).where(
            internal_releases.c.id == rid)).mappings().first()
        require(actual is not None and actual["principal_id"] == user
                and actual["project_id"] == body.project_id and actual["approval_id"] == body.approval_id
                and actual["fingerprint"] == body.release_fingerprint)
    return sorted(left)


def require(ok, message="Independent text logic binding changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def pair(c, user, lid, kind, key, model):
    rows = [graph.lookup(c, user, lid, k, key) for k in (kind, kind + "_seal")]
    require(all(rows), "Independent text logic seals missing")
    left, right = [graph.checked(r) for r in rows]
    require(set(left) == {"request", "response"} and fingerprint(left) == fingerprint(right))
    body = model.model_validate(left["request"])
    require(all(r["request_fingerprint"] == fingerprint(body.model_dump()) for r in rows))
    return body, left["response"]


def remember(c, user, lid, kind, key, body, value):
    for k in (kind, kind + "_seal"):
        graph.remember(c, user, lid, k, key, body, value)


def recipe():
    return dict(tool_ref=text_apps.REF, tool_version="1", check_ref=text_apps.CHECK,
                runtime_parameters=["term"], formats=["txt", "md"], max_bytes=4096,
                max_lines=64, max_term_length=80, max_citations=16,
                action_input_schema=text_apps.schemas()[0], output_schema=text_apps.schemas()[1])


def public(p):
    return {k: copy.deepcopy(v) for k, v in p.items() if k != "private_audit"}


@graph.controlled
def load(store, c, user, lid, limits, *, active=True):
    return _load(store, c, user, lid, limits, implementation(), active=active)


def _load(store, c, user, lid, limits, software_fingerprint, *, active=True):
    # Scope metadata before reading even the independent authority payload.
    meta = c.execute(select(internal_approvals.c.project_id).where(
        internal_approvals.c.id == lid, internal_approvals.c.principal_id == user,
        internal_approvals.c.kind == AUTH)).scalar_one_or_none()
    store.lock_project(c, user, meta)
    row = c.execute(select(internal_approvals).where(internal_approvals.c.id == lid)).mappings().one()
    p = row["payload"]
    require(fingerprint(p) == row["fingerprint"])
    cap = Limits.model_validate(p["limits"])
    a = p["private_audit"]
    require(set(a) == {"source_app_id", "instance_id", "run_id", "release_id",
                       "proof_fingerprint", "release_fingerprint", "material_commitment"})
    for key, prefix in (("source_app_id", "app"), ("instance_id", "iinstance"),
                        ("run_id", "run"), ("release_id", "irelease")):
        require(isinstance(a[key], str) and re.fullmatch(prefix + r"_[a-f0-9]{32}", a[key]))
    require(all(isinstance(a[k], str) and re.fullmatch(graph.HASH, a[k]) for k in
                ("proof_fingerprint", "release_fingerprint", "material_commitment")))
    require(type(p["created_at"]) in (int, float) and math.isfinite(p["created_at"])
            and type(p["expires_at"]) in (int, float) and math.isfinite(p["expires_at"])
            and p["created_at"] + TTL == p["expires_at"] == row["expires_at"])
    expected = dict(namespace=VERSION, id=lid, owner_id=user, project_id=meta,
                    created_at=p["created_at"], expires_at=p["expires_at"], scope=SCOPE,
                    recipe=recipe(), limits=cap.model_dump(),
                    implementation_fingerprint=software_fingerprint, audit_ref=lid,
                    model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
                    formal_publication_enabled=False)
    require(fingerprint(public(p)) == fingerprint(expected), "Canonical text logic/software changed")
    body, frozen = pair(c, user, lid, AUTH, lid, AuthorizeInput)
    require(fingerprint(frozen) == fingerprint(p) and body.expected_proof_fingerprint == a["proof_fingerprint"]
            and body.expected_release_fingerprint == a["release_fingerprint"]
            and lid == "textlogic_" + fingerprint([user, a["instance_id"], a["run_id"], body.request_key])[:32])
    revoked = row["consumed"] or any(graph.lookup(c, user, lid, k, lid)
                                   for k in (REVOKE, REVOKE + "_seal"))
    if active and (revoked or time.time() >= row["expires_at"]):
        raise DomainError("GRANT_REVOKED", "Independent text logic revoked or expired")
    if active and limits is not None and any(getattr(limits, k) < getattr(cap, k) for k in Limits.model_fields):
        raise DomainError("BUDGET_EXHAUSTED", "Current budget below frozen text envelope")
    obj = dict(**expected, fingerprint=fingerprint(expected),
               status="REVOKED" if revoked else "EXPIRED" if time.time() >= row["expires_at"] else "ACTIVE")
    return obj, a


@graph.controlled
def source_options(store, user, iid, rid, limits):
    with store.tx() as c:
        pid = _scope(store, c, user, iid, rid)
        draft, proof = verified_source(store, c, user, iid, rid, limits)
        require(proof["kind"] == TEXT_PROOF, "Initial registered literal source required")
        return dict(namespace=VERSION, project_id=pid, owner_id=user,
                    source_proof_fingerprint=fingerprint(proof),
                    release_fingerprint=proof["release_fingerprint"], recipe=recipe(),
                    limits=draft["candidate"]["manifest"]["runtime_limits"], ttl_seconds=TTL,
                    model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
                    formal_publication_enabled=False)


@graph.controlled
def authorize(store, user, iid, rid, body, limits):
    lid = "textlogic_" + fingerprint([user, iid, rid, body.request_key])[:32]
    with store.tx() as c:
        if c.execute(select(internal_approvals.c.id).where(internal_approvals.c.id == lid)).first():
            obj, _ = load(store, c, user, lid, limits)
            prior, _ = pair(c, user, lid, AUTH, lid, AuthorizeInput)
            require(fingerprint(prior.model_dump()) == fingerprint(body.model_dump()))
            return dict(logic=obj, cached=True)
        pid = _scope(store, c, user, iid, rid)
        draft, proof = verified_source(store, c, user, iid, rid, limits)
        require(proof["kind"] == TEXT_PROOF and fingerprint(proof) == body.expected_proof_fingerprint
                and proof["release_fingerprint"] == body.expected_release_fingerprint)
        count = c.execute(select(func.count()).select_from(internal_approvals).where(
            internal_approvals.c.project_id == pid, internal_approvals.c.kind == AUTH)).scalar_one()
        if count >= MAX_LOGICS:
            raise DomainError("BUDGET_EXHAUSTED", "Project text logic capacity reached")
        now = time.time()
        p = dict(namespace=VERSION, id=lid, owner_id=user, project_id=pid, created_at=now,
                 expires_at=now + TTL, scope=SCOPE, recipe=recipe(),
                 limits=draft["candidate"]["manifest"]["runtime_limits"],
                 implementation_fingerprint=implementation(), audit_ref=lid, model_requests=0,
                 semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False,
                 private_audit=dict(source_app_id=draft["id"], instance_id=iid, run_id=rid,
                    release_id=proof["release_id"], proof_fingerprint=fingerprint(proof),
                    release_fingerprint=proof["release_fingerprint"],
                    material_commitment=fingerprint([lid, proof["source_resource_id"]])))
        c.execute(insert(internal_approvals).values(id=lid, principal_id=user, project_id=pid,
            kind=AUTH, payload=p, fingerprint=fingerprint(p), expires_at=p["expires_at"], consumed=False))
        remember(c, user, lid, AUTH, lid, body, p)
        obj, _ = load(store, c, user, lid, limits)
        return dict(logic=obj, cached=False)


@graph.controlled
def inspect(store, user, lid, limits):
    with store.tx() as c:
        return load(store, c, user, lid, limits, active=False)[0]


@graph.controlled
def recover_authorization(store, user, iid, rid, key, limits):
    lid = "textlogic_" + fingerprint([user, iid, rid, key])[:32]
    with store.tx() as c:
        obj, audit = load(store, c, user, lid, limits, active=False)
        body, _ = pair(c, user, lid, AUTH, lid, AuthorizeInput)
        require(audit["instance_id"] == iid and audit["run_id"] == rid and body.request_key == key)
        return dict(logic=obj, request_fingerprint=fingerprint(body.model_dump()), request_key=key, cached=True)


@graph.controlled
def history(store, user, pid, limits):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        ids = c.execute(select(internal_approvals.c.id).where(
            internal_approvals.c.project_id == pid, internal_approvals.c.principal_id == user,
            internal_approvals.c.kind == AUTH)).scalars().all()
        require(len(ids) <= MAX_LOGICS)
        return dict(namespace=VERSION, items=[load(store, c, user, lid, limits, active=False)[0] for lid in ids])


@graph.controlled
def revoke(store, user, lid, body, limits):
    with store.tx() as c:
        obj, _ = load(store, c, user, lid, limits, active=False)
        require(body.expected_logic_fingerprint == obj["fingerprint"])
        if any(graph.lookup(c, user, lid, k, lid) for k in (REVOKE, REVOKE + "_seal")):
            prior, result = pair(c, user, lid, REVOKE, lid, RevokeInput)
            require(fingerprint(prior.model_dump()) == fingerprint(body.model_dump()))
            return result
        result = dict(namespace=VERSION, id=lid, logic_fingerprint=obj["fingerprint"],
                      request_key=body.request_key, status="REVOKED")
        c.execute(update(internal_approvals).where(internal_approvals.c.id == lid).values(consumed=True))
        remember(c, user, lid, REVOKE, lid, body, result)
        return result


def target(store, c, user, obj, audit, aid, limits):
    pid = c.execute(select(app_drafts.c.project_id).where(app_drafts.c.id == aid)).scalar_one_or_none()
    if pid != obj["project_id"]:
        raise DomainError("PERMISSION_DENIED")
    if aid == audit["source_app_id"]:
        raise DomainError("INVALID_INPUT", "Choose another existing TXT/MD material")
    if not c.execute(select(goal_application_candidates.c.app_id).where(
        goal_application_candidates.c.app_id == aid,
        goal_application_candidates.c.principal_id == user)).first():
        raise DomainError("UNSUPPORTED_CAPABILITY", "Current initial literal target required")
    raw = c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
    rid = raw["manifest"]["data_bindings"][0]["resource_ref"]
    if fingerprint([obj["id"], rid]) == audit["material_commitment"]:
        raise DomainError("INVALID_INPUT", "Choose another existing TXT/MD material")
    draft, manifest, action, _ = load_draft(store, c, user, aid, limits)
    require(action.executor.ref == text_apps.REF and manifest.origin == "goal"
            and "goal_application" in draft["candidate"], "Current initial literal target required")
    rid = manifest.data_bindings[0].resource_ref
    if fingerprint([obj["id"], rid]) == audit["material_commitment"]:
        raise DomainError("INVALID_INPUT", "Choose another existing TXT/MD material")
    source = authorized_read(store, c, user, draft["runtime_id"], pid, "resource.read", {"resource_id": rid})
    require(source["format"] in {"txt", "md"} and len(source["content"].encode()) <= 4096
            and len(source["content"].splitlines()) <= 64 and source["hash"] == draft["candidate"]["source_hash"])
    expiries = []
    for who in (user, draft["runtime_id"]):
        expiries.append(c.execute(select(func.max(grants.c.expires_at)).where(
            grants.c.principal_id == who, grants.c.project_id == pid, grants.c.resource_id == rid,
            grants.c.tool_ref == "resource.read", grants.c.revoked.is_(False),
            grants.c.expires_at > time.time())).scalar_one())
    require(all(type(v) in (int, float) and math.isfinite(v) for v in expiries))
    return dict(target_app_id=aid, project_id=pid, name=draft["name"], resource_id=rid,
                source_hash=source["hash"], candidate_fingerprint=draft["fingerprint"],
                grant_expires_at=min(obj["expires_at"], *expiries))


@graph.controlled
def options(store, user, lid, limits):
    with store.tx() as c:
        obj, audit = load(store, c, user, lid, limits)
        ids = c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == obj["project_id"])).scalars().all()
        items = []
        for aid in ids:
            # Never reopen the original app, including when its material is gone.
            if aid == audit["source_app_id"]:
                continue
            try:
                items.append(target(store, c, user, obj, audit, aid, limits))
            except DomainError:
                continue
        return dict(namespace=VERSION, logic=obj, items=items)


def candidate(obj, body, aid, action_id):
    """Closed constructor: copies no source/target goal, identity or declaration."""
    rid, cap = body.expected_resource_id, obj["limits"]
    inp, out = text_apps.schemas()
    permissions = [dict(tool_ref="resource.read", resource_ref=rid)]
    proof = dict(kind=PROOF, logic_id=obj["id"], logic_fingerprint=obj["fingerprint"],
                 request_key=body.request_key, request_fingerprint=fingerprint(body.model_dump()))
    action = dict(schema_version="1.0-draft", action_id=action_id, revision=1,
        input_schema=inp, output_schema=out,
        executor=dict(kind="registered_tool", ref=text_apps.REF, version="1"),
        allowed_tool_refs=[], dependencies=[dict(kind="resource", ref=rid, version="1")],
        permission_requirements=permissions, effect="read", preconditions=[],
        postcheck_refs=[text_apps.CHECK], limits=cap, idempotency="read_only",
        reconcile_ref="operation.lookup.v1", error_contract=["INVALID_INPUT", "PERMISSION_DENIED", "GRANT_REVOKED"])
    manifest = dict(schema_version="1.0-draft", app_id=aid, revision=1, origin="task_run",
        goal_ref=obj["id"], source_run_ref=obj["id"], input_schema=object_schema({"term": inp["properties"]["term"]}),
        output_schema=out, outputs={k: dict(source="step", ref="evidence", field=k) for k in out["properties"]},
        views=[dict(component_ref="table", output_field="citations")],
        workflow=[dict(step_id="evidence", binding_id="literal", depends_on=[],
            inputs=dict(resource_id=dict(source="data", ref="source", field="resource_id"),
                        term=dict(source="input", field="term")))],
        action_bindings=[dict(binding_id="literal", action_id=action_id, revision=1)],
        data_bindings=[dict(binding_id="source", resource_ref=rid)],
        runtime_identity_requirements=dict(mode="user_and_app_intersection"),
        permission_requirements=permissions,
        dependency_lock=[dict(kind="resource", ref=rid, version="1"), dict(kind="tool", ref=text_apps.REF, version="1"),
                         dict(kind="check", ref=text_apps.CHECK, version="1")],
        validation_suite_ref=text_apps.CHECK, runtime_limits=cap, data_schema_version=1)
    return dict(manifest=manifest, actions=[action], source_hash=body.expected_source_hash,
                goal=dict(known="Fixed literal line retrieval", assumptions=[],
                          unresolved=["Owner acceptance pending; semantic interpretation unknown"]),
                task_proof=dict(proof=proof, proof_fingerprint=fingerprint(proof)))


@graph.controlled
def verify_candidate(store, c, user, draft, limits, *, archival_software=None):
    row = c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"],
        task_extractions.c.principal_id == user)).mappings().first()
    require(row is not None and row["snapshot"]["kind"] == KIND)
    lid = row["task_id"]
    from . import text_continuations

    old_fp = text_continuations.software(c, user, draft)
    if archival_software is not None:
        require(old_fp == archival_software)
    if old_fp is None:
        obj, _ = load(store, c, user, lid, limits)
    else:
        text_continuations.known(old_fp)
        obj, _ = _load(store, c, user, lid, limits, old_fp)
    body, frozen = pair(c, user, lid, BIND, row["request_key"], BindInput)
    require(set(frozen) == {"kind", "logic_id", "project_id", "owner_id", "app_id", "action_id",
                           "runtime_id", "grant_id", "grant_expires_at", "candidate_fingerprint"})
    require(fingerprint(row["snapshot"]) == fingerprint(frozen) and row["request_fingerprint"] == fingerprint(body.model_dump())
            and frozen["logic_id"] == lid and frozen["owner_id"] == user
            and frozen["project_id"] == obj["project_id"] == draft["project_id"]
            and frozen["app_id"] == draft["id"] and frozen["runtime_id"] == draft["runtime_id"]
            and body.expected_logic_fingerprint == obj["fingerprint"]
            and type(frozen["grant_expires_at"]) in (int, float)
            and math.isfinite(frozen["grant_expires_at"])
            and frozen["grant_expires_at"] <= obj["expires_at"])
    expected = candidate(obj, body, draft["id"], frozen["action_id"])
    require(fingerprint(expected) == fingerprint(draft["candidate"]) == draft["fingerprint"] == frozen["candidate_fingerprint"])
    principal = c.execute(select(principals).where(principals.c.id == draft["runtime_id"])).mappings().first()
    gs = c.execute(select(grants).where(grants.c.principal_id == draft["runtime_id"])).mappings().all()
    require(principal is not None and principal["token_hash"] is None and len(gs) == 1)
    g = gs[0]
    require(g["id"] == frozen["grant_id"] and g["project_id"] == obj["project_id"]
            and g["resource_id"] == body.expected_resource_id and g["tool_ref"] == "resource.read"
            and g["expires_at"] == frozen["grant_expires_at"] and g["revision"] == 1)
    store.authorize(c, user, draft["runtime_id"], obj["project_id"], body.expected_resource_id, "resource.read")
    if old_fp is not None and archival_software is None:
        text_continuations.archival_app(store, c, user, draft, old_fp)
    return obj, body, frozen


def receipt(obj, body, frozen, *, cached):
    return dict(namespace=VERSION, id=frozen["app_id"], project_id=obj["project_id"],
                owner_id=obj["owner_id"], logic_id=obj["id"], logic_fingerprint=obj["fingerprint"],
                runtime_id=frozen["runtime_id"], resource_id=body.expected_resource_id,
                candidate_fingerprint=frozen["candidate_fingerprint"], request_key=body.request_key,
                request_fingerprint=fingerprint(body.model_dump()), grant_expires_at=frozen["grant_expires_at"],
                cached=cached, model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
                formal_publication_enabled=False)


@graph.controlled
def bind(store, user, lid, body, limits):
    with store.tx() as c:
        obj, audit = load(store, c, user, lid, limits)
        require(body.expected_logic_fingerprint == obj["fingerprint"] and body.name.strip())
        old = c.execute(select(task_extractions).where(task_extractions.c.task_id == lid,
            task_extractions.c.principal_id == user, task_extractions.c.request_key == body.request_key)).mappings().first()
        if old:
            draft, _, _, _ = load_draft(store, c, user, old["app_id"], limits)
            _, prior, frozen = verify_candidate(store, c, user, draft, limits)
            require(fingerprint(prior.model_dump()) == fingerprint(body.model_dump()))
            return receipt(obj, body, frozen, cached=True)
        t = target(store, c, user, obj, audit, body.target_app_id, limits)
        require(t["candidate_fingerprint"] == body.expected_target_draft_fingerprint
                and t["resource_id"] == body.expected_resource_id and t["source_hash"] == body.expected_source_hash)
        count = c.execute(select(func.count()).select_from(task_extractions).where(task_extractions.c.task_id == lid)).scalar_one()
        if count >= MAX_BINDINGS:
            raise DomainError("BUDGET_EXHAUSTED", "Independent text binding capacity reached")
        aid, action_id, runtime, grant_id = new_id("app"), new_id("action"), new_id("appruntime"), new_id("grant")
        value = candidate(obj, body, aid, action_id)
        compile_preview(value, limits)
        frozen = dict(kind=KIND, logic_id=lid, project_id=obj["project_id"], owner_id=user,
                      app_id=aid, action_id=action_id, runtime_id=runtime, grant_id=grant_id,
                      grant_expires_at=t["grant_expires_at"], candidate_fingerprint=fingerprint(value))
        c.execute(insert(principals).values(id=runtime, name="Independent literal read runtime", token_hash=None))
        c.execute(insert(grants).values(id=grant_id, principal_id=runtime, project_id=obj["project_id"],
            resource_id=t["resource_id"], tool_ref="resource.read", expires_at=t["grant_expires_at"], revision=1, revoked=False))
        c.execute(insert(app_drafts).values(id=aid, project_id=obj["project_id"], runtime_id=runtime,
            name=body.name, candidate=value, fingerprint=fingerprint(value), created_at=time.time()))
        c.execute(insert(task_extractions).values(task_id=lid, principal_id=user, request_key=body.request_key,
            request_fingerprint=fingerprint(body.model_dump()), app_id=aid, snapshot=frozen))
        remember(c, user, lid, BIND, body.request_key, body, frozen)
        draft, _, _, _ = load_draft(store, c, user, aid, limits)
        verify_candidate(store, c, user, draft, limits)
        return receipt(obj, body, frozen, cached=False)


@graph.controlled
def recover_binding(store, user, lid, key, limits):
    with store.tx() as c:
        obj, _ = load(store, c, user, lid, limits)
        body, frozen = pair(c, user, lid, BIND, key, BindInput)
        draft, _, _, _ = load_draft(store, c, user, frozen["app_id"], limits)
        verify_candidate(store, c, user, draft, limits)
        return receipt(obj, body, frozen, cached=True)
