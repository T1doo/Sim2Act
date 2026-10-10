"""Explicit, revocable data-free authority for two fixed closed CSV recipes.

Original data grants are never substituted by this authority. Only canonical
structure and frozen caps are reusable; immutable source JSON is hash-audited,
never interpreted as new input or copied into the new plan.
"""

import copy
import hashlib
import math
import time
from pathlib import Path
from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select, update

from . import csv_dag as dag
from . import csv_dag_instances as instances
from . import csv_material_reuse as material
from . import csv_reports as report
from . import delivery_graph_apps as graph
from . import lifecycle
from .column_patches import KeyInput, read_pair, require_capacity
from .contracts import Limits
from .db import app_drafts, fingerprint, internal_approvals, internal_releases, runs
from .errors import DomainError

VERSION = "internal.csv-data-free-logic.v1"
AUTH_KIND = "csv_logic_authority"
ORIGIN = "csv_logic_plan_origin"
DERIVED = "csv_logic_instance_origin"
REVOKE = "csv_logic_revocation"
PREFIX = "logic-plan-"
INSTANCE_PREFIX = "logic-instance-plan-"
LOGIC_ID = r"^csvlogic_[a-f0-9]{32}$"
CONSENT = "AUTHORIZE_DATA_FREE_CSV_LOGIC_IN_THIS_PROJECT"
SCOPE = "EXISTING_AUTHORIZED_CSV_DRAFTS_SAME_OWNER_PROJECT"
TTL = 86400
SCHEMA = report.obj({"result": report.INPUT})


class AuthorizeInput(KeyInput):
    expected_release_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["AUTHORIZE_DATA_FREE_CSV_LOGIC_IN_THIS_PROJECT"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


class RevokeInput(KeyInput):
    expected_logic_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["REVOKE_DATA_FREE_CSV_LOGIC"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


class MaterialInput(KeyInput):
    expected_logic_fingerprint: str = Field(pattern=graph.HASH)
    target_app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    expected_resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=graph.HASH)
    column: str = Field(min_length=1, max_length=200)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


def implementation():
    return fingerprint({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(Path(__file__).parent.glob("*.py"))
                        if p.name != "config.py"})


def canonical(version, column=None):
    instances.require(version in instances.VERSIONS)
    nodes = [dict(step_id="read", action="resource.read", depends_on=[],
                  inputs={"resource_id": dict(source="data", ref="source", field="resource_id")}),
             dict(step_id="aggregate", action="data.aggregate_csv", depends_on=["read"],
                  inputs={"resource_id": dict(source="step", ref="read", field="resource_id"),
                          "column": dict(source="input", field="aggregate_column")})]
    if column is not None:
        nodes[1]["column"] = column
    if version == instances.REPORT_VERSION:
        nodes.append(dict(step_id="report", action=report.REF, depends_on=["aggregate"],
                          inputs={k: dict(source="step", ref="aggregate", field=k)
                                  for k in report.FIELDS}))
    return dict(version=dag.COMPOSITION_VERSION, nodes=nodes)


def pair(c, user, aid, kind, key, model):
    # Material intent key differs from its deterministic origin key.
    rows = [graph.lookup(c, user, aid, k, key) for k in (kind, kind + "_seal")]
    instances.require(all(rows), "Missing independent logic authority/origin")
    left, right = [graph.checked(r) for r in rows]
    instances.require(set(left) == {"request", "response"} and fingerprint(left) == fingerprint(right))
    body = model.model_validate(left["request"])
    instances.require(all(r["request_fingerprint"] == fingerprint(body.model_dump()) for r in rows))
    return body, left["response"]


def audit(c, user, pid, a):
    instances.require(set(a) == {"release_id", "release_fingerprint", "approval_id",
                                "approval_fingerprint", "run_id", "app_id"})
    rel = c.execute(select(internal_releases).where(
        internal_releases.c.id == a["release_id"])).mappings().first()
    approval = c.execute(select(internal_approvals).where(
        internal_approvals.c.id == a["approval_id"])).mappings().first()
    instances.require(rel is not None and approval is not None
        and rel["principal_id"] == approval["principal_id"] == user
        and rel["project_id"] == approval["project_id"] == pid
        and rel["approval_id"] == approval["id"] and approval["kind"] == "release"
        and approval["consumed"] and rel["fingerprint"] == a["release_fingerprint"]
        and approval["fingerprint"] == a["approval_fingerprint"]
        and fingerprint(rel["snapshot"]) == rel["fingerprint"]
        and fingerprint(approval["payload"]) == approval["fingerprint"]
        and approval["payload"]["snapshot"] == rel["snapshot"], "Immutable source audit changed")
    s = rel["snapshot"]
    e = s["execution_source"]
    instances.require(e["version"] in instances.VERSIONS
        and not e["plan_key"].startswith((material.PREFIX, PREFIX, INSTANCE_PREFIX))
        and s["namespace"] == lifecycle.NAMESPACE and s["data_schema"] == SCHEMA
        and s["draft"]["id"] == a["app_id"] and e["run_id"] == a["run_id"]
        and s["draft"]["project_id"] == pid and s["model_requests"] == 0
        and s["formal_publication_enabled"] is False)
    instances.validate_family(c, user, approval["id"], s)
    # No Run.result/context or old Operation/resource SELECT in this audit.
    job = c.execute(select(runs.c.id, runs.c.principal_id, runs.c.project_id,
        runs.c.runtime_id, runs.c.status, runs.c.version, runs.c.fence, runs.c.fingerprint)
        .where(runs.c.id == a["run_id"])).mappings().first()
    draft = c.execute(select(app_drafts.c.id, app_drafts.c.project_id, app_drafts.c.runtime_id)
        .where(app_drafts.c.id == a["app_id"])).mappings().first()
    instances.require(job is not None and draft is not None and job["status"] == "SUCCEEDED"
        and job["principal_id"] == user and job["project_id"] == draft["project_id"] == pid
        and job["runtime_id"] == draft["runtime_id"] == s["draft"]["runtime_id"]
        and job["version"] == e["run_version"] and job["fence"] == e["fence"]
        and job["fingerprint"] == e["accepted_fingerprint"], "Source audit identity changed")
    return s


def public(payload):
    return {k: copy.deepcopy(v) for k, v in payload.items() if k != "private_audit"}


def load(store, c, user, lid, limits, *, active=True):
    row = c.execute(select(internal_approvals).where(internal_approvals.c.id == lid)).mappings().first()
    if row is None or row["kind"] != AUTH_KIND or row["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.lock_project(c, user, row["project_id"])
    p = row["payload"]
    instances.require(fingerprint(p) == row["fingerprint"] and p["id"] == lid
        and p["owner_id"] == user and p["project_id"] == row["project_id"]
        and type(p["expires_at"]) in (float, int) and math.isfinite(p["expires_at"])
        and p["expires_at"] == row["expires_at"])
    src = audit(c, user, row["project_id"], p["private_audit"])
    cap = Limits(**src["execution_source"]["limits"])
    expected = dict(namespace=VERSION, id=lid, owner_id=user, project_id=row["project_id"],
        expires_at=p["expires_at"], scope=SCOPE, execution_version=src["execution_source"]["version"],
        recipe=canonical(src["execution_source"]["version"]), data_schema=SCHEMA,
        limits=cap.model_dump(), implementation_fingerprint=implementation(), audit_ref=lid,
        model_requests=0, semantic_status="UNKNOWN", owner_acceptance="PENDING",
        formal_publication_enabled=False)
    instances.require(public(p) == expected, "Canonical logic/software version changed")
    body, frozen = pair(c, user, p["private_audit"]["app_id"], AUTH_KIND, lid, AuthorizeInput)
    instances.require(frozen == p and body.expected_release_fingerprint == p["private_audit"]["release_fingerprint"])
    revoke_rows = [graph.lookup(c, user, p["private_audit"]["app_id"], kind, lid)
                   for kind in (REVOKE, REVOKE + "_seal")]
    revoked = bool(row["consumed"] or any(revoke_rows))
    if active and (revoked or time.time() >= row["expires_at"]):
        raise DomainError("GRANT_REVOKED", "Independent logic authority revoked or expired")
    if active and limits is not None and any(getattr(limits, k) < getattr(cap, k) for k in Limits.model_fields):
        raise DomainError("BUDGET_EXHAUSTED", "Current budget below frozen logic envelope")
    return dict(**expected, fingerprint=fingerprint(expected),
                status="REVOKED" if revoked else "EXPIRED" if time.time() >= row["expires_at"] else "ACTIVE"), src


@graph.controlled
def authorize(store, user, rid, body, limits):
    lid = "csvlogic_" + fingerprint([user, rid, body.request_key])[:32]
    with store.tx() as c:
        old = c.execute(select(internal_approvals.c.id).where(internal_approvals.c.id == lid)).first()
        if old:
            obj, s = load(store, c, user, lid, limits)
            prior, _ = pair(c, user, s["draft"]["id"], AUTH_KIND, lid, AuthorizeInput)
            instances.require(prior == body)
            return dict(logic=obj, cached=True, model_requests=0, formal_publication_enabled=False)
        rel, _, cap = material.recipe(store, c, user, rid, limits)
        instances.require(rel["fingerprint"] == body.expected_release_fingerprint)
        s = rel["snapshot"]
        e = s["execution_source"]
        instances.require(not e["plan_key"].startswith((PREFIX, INSTANCE_PREFIX)) and s["data_schema"] == SCHEMA)
        a = c.execute(select(internal_approvals).where(internal_approvals.c.id == rel["approval_id"])).mappings().one()
        require_capacity(c, user, s["draft"]["id"], AUTH_KIND)
        payload = dict(namespace=VERSION, id=lid, owner_id=user, project_id=rel["project_id"],
            expires_at=time.time() + TTL, scope=SCOPE, execution_version=e["version"],
            recipe=canonical(e["version"]), data_schema=copy.deepcopy(SCHEMA), limits=cap.model_dump(),
            implementation_fingerprint=implementation(), audit_ref=lid, model_requests=0,
            semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False,
            private_audit=dict(release_id=rid, release_fingerprint=rel["fingerprint"],
                approval_id=a["id"], approval_fingerprint=a["fingerprint"], run_id=e["run_id"], app_id=s["draft"]["id"]))
        c.execute(insert(internal_approvals).values(id=lid, principal_id=user, project_id=rel["project_id"],
            kind=AUTH_KIND, payload=payload, fingerprint=fingerprint(payload), expires_at=payload["expires_at"], consumed=False))
        for kind in (AUTH_KIND, AUTH_KIND + "_seal"):
            graph.remember(c, user, s["draft"]["id"], kind, lid, body, payload)
        obj, _ = load(store, c, user, lid, limits)
        return dict(logic=obj, cached=False, model_requests=0, formal_publication_enabled=False)


@graph.controlled
def inspect(store, user, lid, limits):
    with store.tx() as c:
        obj, _ = load(store, c, user, lid, limits, active=False)
        return obj


@graph.controlled
def history(store, user, pid, limits):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        ids = c.execute(select(internal_approvals.c.id).where(internal_approvals.c.project_id == pid,
            internal_approvals.c.principal_id == user, internal_approvals.c.kind == AUTH_KIND)).scalars().all()
        return dict(namespace=VERSION, items=[load(store, c, user, lid, limits, active=False)[0]
                                            for lid in ids], model_requests=0, formal_publication_enabled=False)


@graph.controlled
def revoke(store, user, lid, body, limits):
    with store.tx() as c:
        obj, s = load(store, c, user, lid, limits, active=False)
        instances.require(obj["fingerprint"] == body.expected_logic_fingerprint)
        aid = s["draft"]["id"]
        rows = [graph.lookup(c, user, aid, kind, lid) for kind in (REVOKE, REVOKE + "_seal")]
        if any(rows):
            prior, result = pair(c, user, aid, REVOKE, lid, RevokeInput)
            instances.require(prior == body)
            return result
        result = dict(namespace=VERSION, id=lid, logic_fingerprint=obj["fingerprint"],
                      status="REVOKED", request_key=body.request_key, model_requests=0,
                      formal_publication_enabled=False)
        c.execute(update(internal_approvals).where(internal_approvals.c.id == lid).values(consumed=True))
        for kind in (REVOKE, REVOKE + "_seal"):
            graph.remember(c, user, aid, kind, lid, body, result)
        return result


def target(store, c, user, obj, src, aid, cap):
    # Reuse only the established target gates; no old resource bytes/hash copied.
    return material.target_for_schema(store, c, user, obj["project_id"], aid, cap, SCHEMA,
        excluded_id=src["draft"]["candidate"]["manifest"]["data_bindings"][0]["resource_ref"])


@graph.controlled
def options(store, user, lid, limits):
    with store.tx() as c:
        obj, src = load(store, c, user, lid, limits)
        cap = Limits(**obj["limits"])
        ids = c.execute(select(app_drafts.c.id).where(app_drafts.c.project_id == obj["project_id"])).scalars().all()
        items = []
        for aid in ids:
            if aid == src["draft"]["id"]:
                continue
            try:
                items.append(target(store, c, user, obj, src, aid, cap))
            except DomainError:
                continue
        return dict(namespace=VERSION, logic=obj, items=items, model_requests=0,
                    formal_publication_enabled=False)


def plan_key(lid, body):
    return PREFIX + fingerprint([lid, body.request_key])[:48]


def definition(store, c, user, lid, body, limits, key):
    obj, src = load(store, c, user, lid, limits)
    cap = Limits(**obj["limits"])
    instances.require(obj["fingerprint"] == body.expected_logic_fingerprint)
    t = target(store, c, user, obj, src, body.target_app_id, cap)
    instances.require(t["candidate_fingerprint"] == body.expected_candidate_fingerprint
        and t["graph_fingerprint"] == body.expected_graph_fingerprint
        and t["resource_id"] == body.expected_resource_id and t["source_hash"] == body.expected_source_hash)
    if body.column not in t["columns"]:
        raise DomainError("INVALID_INPUT", "Choose a current target numeric column")
    plan_body = dag.PlanInput(expected_candidate_fingerprint=t["candidate_fingerprint"],
        expected_graph_fingerprint=t["graph_fingerprint"], column=body.column,
        composition=canonical(obj["execution_version"], body.column), request_key=key)
    b = dict(version=VERSION, logic=obj, target=t, column=body.column, limits=cap.model_dump(),
             plan_input=plan_body.model_dump(exclude_none=True), principal_id=user,
             request_key=body.request_key, model_requests=0, formal_publication_enabled=False)
    return b, plan_body, cap


def marker(key, binding):
    return dict(version=VERSION, logic_id=binding["logic"]["id"],
        logic_fingerprint=binding["logic"]["fingerprint"], origin_key=key,
        binding_fingerprint=fingerprint(binding))


def base_origin(store, c, user, aid, key, limits):
    body, old = pair(c, user, aid, ORIGIN, key, MaterialInput)
    instances.require(key == plan_key(old["logic"]["id"], body) and aid == body.target_app_id)
    binding, expected, cap = definition(store, c, user, old["logic"]["id"], body, limits, key)
    instances.require(fingerprint(old) == fingerprint(binding))
    return binding, expected, cap


def plan_origin(store, c, user, pid, aid, body, limits):
    prior = graph.lookup(c, user, aid, "csv_dag_plan", body.request_key)
    marked = prior is not None and "logical_reuse" in graph.checked(prior).get("response", {})
    if body.request_key.startswith(PREFIX):
        binding, expected, cap = base_origin(store, c, user, aid, body.request_key, limits)
        instances.require(body == expected and pid == binding["target"]["project_id"])
        return marker(body.request_key, binding), cap
    if body.request_key.startswith(INSTANCE_PREFIX) or body.logic_origin is not None or marked:
        instances.require(body.request_key.startswith(INSTANCE_PREFIX) and body.logic_origin is not None)
        old_body, ref = read_pair(c, user, aid, DERIVED, body.request_key, dag.PlanInput)
        origin = body.logic_origin.model_dump()
        binding, _, cap = base_origin(store, c, user, aid, origin["origin_key"], limits)
        instances.require(ref == origin == marker(origin["origin_key"], binding) and body == old_body
            and pid == binding["target"]["project_id"]
            and body.expected_candidate_fingerprint == binding["target"]["candidate_fingerprint"]
            and body.expected_graph_fingerprint == binding["target"]["graph_fingerprint"]
            and body.column in binding["target"]["columns"]
            and body.composition.model_dump(exclude_none=True) == canonical(binding["logic"]["execution_version"], body.column)
            and body.branch_patch is None and body.wiring_patch is None)
        return origin, cap
    return None


def prepare_instance_plan(store, c, user, pid, aid, source_plan, body, cap):
    ref = source_plan["logical_reuse"]
    binding, _, frozen = base_origin(store, c, user, aid, ref["origin_key"], cap)
    instances.require(ref == marker(ref["origin_key"], binding) and cap == frozen
        and body.request_key.startswith(INSTANCE_PREFIX) and pid == binding["target"]["project_id"])
    body = body.model_copy(update={"logic_origin": dag.LogicOrigin(**ref)})
    instances.require(body.column in binding["target"]["columns"]
        and body.composition.model_dump(exclude_none=True) == canonical(binding["logic"]["execution_version"], body.column))
    dag.build(store, c, user, pid, aid, body.model_copy(update={"request_key": "logic-preflight-" + body.request_key[-48:], "logic_origin": None}), cap)
    old = graph.lookup(c, user, aid, DERIVED, body.request_key)
    if old:
        prior, value = read_pair(c, user, aid, DERIVED, body.request_key, dag.PlanInput)
        instances.require(prior == body and value == ref)
    else:
        require_capacity(c, user, aid, DERIVED)
        for kind in (DERIVED, DERIVED + "_seal"):
            graph.remember(c, user, aid, kind, body.request_key, body, ref)
    return body


@graph.controlled
def propose(store, user, lid, body, limits):
    with store.tx() as c:
        key = plan_key(lid, body)
        b, plan_body, cap = definition(store, c, user, lid, body, limits, key)
        aid, pid = body.target_app_id, b["target"]["project_id"]
        dag.build(store, c, user, pid, aid, plan_body.model_copy(update={"request_key": "logic-preflight-" + key[-48:]}), cap)
        from .db import delivery_graph_requests
        rows = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.kind.in_([ORIGIN, ORIGIN + "_seal"]), delivery_graph_requests.c.request_key == key)).mappings().all()
        instances.require(not rows or len(rows) == 2 and all(r["app_id"] == aid for r in rows))
        if rows:
            prior, old = pair(c, user, aid, ORIGIN, key, MaterialInput)
            instances.require(prior == body and old == b)
        else:
            require_capacity(c, user, aid, ORIGIN)
            for kind in (ORIGIN, ORIGIN + "_seal"):
                graph.remember(c, user, aid, kind, key, body, b)
        plan = dag.propose_tx(store, c, user, pid, aid, plan_body, cap)
        return dict(namespace=VERSION, binding=b, binding_fingerprint=fingerprint(b),
                    plan=plan, cached=bool(rows), model_requests=0, formal_publication_enabled=False)


@graph.controlled
def inspect_plan(store, user, lid, aid, key, limits):
    with store.tx() as c:
        b, _, cap = base_origin(store, c, user, aid, key, limits)
        instances.require(b["logic"]["id"] == lid)
        plan = dag.load_plan(store, c, user, b["target"]["project_id"], aid, key, cap)
        return dict(namespace=VERSION, binding=b, binding_fingerprint=fingerprint(b),
                    plan=plan, model_requests=0, formal_publication_enabled=False)


def commit_authority(store, c, job, plan, limits):
    ref = plan.get("logical_reuse")
    if ref is None:
        return
    obj, _ = load(store, c, job["principal_id"], ref["logic_id"], limits)
    instances.require(obj["fingerprint"] == ref["logic_fingerprint"] and obj["project_id"] == job["project_id"])
    rid = plan["definition"]["manifest"]["data_bindings"][0]["resource_ref"]
    store.authorize(c, job["principal_id"], job["runtime_id"], job["project_id"], rid, "data.aggregate_csv")
