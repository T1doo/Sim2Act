"""Trusted current-authority graph anchors and planning-only revalidation jobs."""

import copy
import hashlib
from functools import wraps
from pathlib import Path

from fastapi import Depends
from pydantic import Field, ValidationError
from sqlalchemy import insert, select, update

from . import apps
from . import delivery_graph as core
from .contracts import Strict
from .db import app_drafts, fingerprint, grants, new_id, resources, runs
from .db import delivery_graph_anchors as anchors
from .db import delivery_graph_locks as locks
from .db import delivery_graph_requests as requests
from .db import delivery_graph_scope_jobs as jobs
from .db import delivery_graph_source_versions as versions
from .db import delivery_graph_states as states
from .errors import DomainError

NAMESPACE = "delivery-graph-apps.v1"
HASH = r"^[a-f0-9]{64}$"


class DeriveInput(Strict):
    expected_candidate_fingerprint: str = Field(pattern=HASH)
    request_key: str = Field(min_length=1, max_length=128)


class LockInput(Strict):
    expected_graph_fingerprint: str = Field(pattern=HASH)
    request_key: str = Field(min_length=1, max_length=128)
    change: core.Change
    locked: bool


class PlanInput(Strict):
    expected_graph_fingerprint: str = Field(pattern=HASH)
    request_key: str = Field(min_length=1, max_length=128)
    changes: list[core.Change] = Field(min_length=1, max_length=128)


def conflict(detail="DeliveryGraph persistent binding changed"):
    raise DomainError("VERSION_CONFLICT", detail)


def controlled(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValidationError, KeyError, TypeError, ValueError):
            conflict("Malformed persisted DeliveryGraph binding")

    return call


class SavedState(Strict):
    app_id: str
    project_id: str
    principal_id: str
    runtime_id: str
    candidate_fingerprint: str = Field(pattern=HASH)
    stable_ids: dict[str, str]
    source_versions: dict[str, core.SourceVersion]
    authorization_fingerprint: str = Field(pattern=HASH)
    authorization_revision: int = Field(ge=1)
    graph_revision: int = Field(ge=1)
    derivation_key: str = Field(min_length=1, max_length=128)
    graph: core.Graph
    context: core.Context


def checked(row):
    if (
        not row
        or not isinstance(row["snapshot"], dict)
        or fingerprint(row["snapshot"]) != row["fingerprint"]
    ):
        conflict()
    return copy.deepcopy(row["snapshot"])


def load_family(store, c, user, pid, aid, limits):
    project = store.lock_project(c, user, pid)
    draft = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().first()
    if not draft or draft["project_id"] != pid:
        raise DomainError("PERMISSION_DENIED")
    if (
        isinstance(draft["candidate"], dict)
        and draft["candidate"].get("namespace") == "bounded-report-manifest.v1"
    ):
        from .report_manifest_apps import load

        result = load(store, c, user, aid, limits, pid)
    else:
        result = apps.validate_frozen_candidate(store, c, user, draft, limits)
    draft, manifest, action, report = result
    # Recheck every declared tool/resource intersection, including rules-only source.
    for p in manifest.permission_requirements:
        store.authorize(c, user, draft["runtime_id"], pid, p.resource_ref, p.tool_ref)
    allowed = sorted(
        {
            p.resource_ref
            for p in manifest.permission_requirements
            if p.resource_ref.startswith("res_")
        }
    )
    rows = (
        c.execute(
            select(resources).where(resources.c.id.in_(allowed), resources.c.project_id == pid)
        )
        .mappings()
        .all()
    )
    if {r["id"] for r in rows} != set(allowed):
        raise DomainError("PERMISSION_DENIED")
    for r in rows:
        if (
            r["format"] not in {"csv", "txt", "md"}
            or not isinstance(r["content"], str)
            or hashlib.sha256(r["content"].encode()).hexdigest() != r["hash"]
        ):
            conflict("Current source content/hash/status changed")
    identities = {user, draft["runtime_id"], project["runtime_id"]}
    authorization = [
        dict(r)
        for r in c.execute(
            select(grants)
            .where(grants.c.project_id == pid, grants.c.principal_id.in_(identities))
            .order_by(grants.c.id)
        ).mappings()
    ]
    auth_fp = fingerprint(
        {"owner": user, "project": pid, "runtime": draft["runtime_id"], "grants": authorization}
    )
    return dict(draft), manifest, action, report, rows, auth_fp


def logical(store, c, draft, manifest, rows):
    """Exactly mirror core logical keys; external definitions come from trusted state."""
    keys = {}
    external = {}
    goal = "goal:" + manifest.goal_ref
    external[goal] = {
        "goal_ref": manifest.goal_ref,
        "candidate_goal": draft["candidate"].get("goal"),
        "origin": {
            k: draft["candidate"][k]
            for k in ("report_proof", "task_proof", "extraction", "generation", "agent_provenance")
            if k in draft["candidate"]
        },
    }
    if manifest.source_run_ref:
        origin_run = (
            c.execute(select(runs).where(runs.c.id == manifest.source_run_ref)).mappings().first()
        )
        if origin_run and draft["candidate"].get("namespace") == "bounded-report-manifest.v1":
            external[goal]["verified_frozen_goal"] = store.frozen_contract(
                c, origin_run
            ).goal.model_dump()
    for r in rows:
        external["source:" + r["id"]] = {
            "resource_id": r["id"],
            "project_id": r["project_id"],
            "format": r["format"],
            "stored_hash": r["hash"],
            "content_sha256": hashlib.sha256(r["content"].encode()).hexdigest(),
        }
    registry_files = sorted(
        p.name for p in Path(__file__).parent.glob("*.py") if p.name != "config.py"
    )
    registry = {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in registry_files
    }
    for dep in manifest.dependency_lock:
        if dep.kind in {"tool", "prompt", "check"}:
            external[f"rule:{dep.kind}:{dep.ref}"] = {
                "dependency": dep.model_dump(),
                "registry_versions": registry,
            }
    checks = (
        {manifest.validation_suite_ref}
        | {d.ref for d in manifest.dependency_lock if d.kind == "check"}
        | {ref for a in draft["candidate"]["actions"] for ref in a["postcheck_refs"]}
    )
    for ref in checks:
        external["check:" + ref] = {"check_ref": ref, "registry_versions": registry}
    keys.update({k: None for k in external})
    actions = {(a["action_id"], a["revision"]): a for a in draft["candidate"]["actions"]}
    bindings = {b.binding_id: (b.action_id, b.revision) for b in manifest.action_bindings}
    for step in manifest.workflow:
        keys["action:" + step.step_id] = actions[bindings[step.binding_id]]["revision"]
    for field in manifest.outputs:
        keys["artifact:" + field] = manifest.revision
    for view in manifest.views:
        keys["view:" + view.component_ref + ":" + view.output_field] = manifest.revision
    keys["manifest:" + manifest.app_id] = manifest.revision
    return keys, external


def state(store, c, user, pid, aid):
    row = c.execute(select(states).where(states.c.app_id == aid)).mappings().first()
    if not row:
        conflict("DeliveryGraph anchor has not been derived")
    if row["project_id"] != pid or row["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    saved = checked(row)
    SavedState.model_validate(saved)
    if any(saved[k] != row[k] for k in ("app_id", "project_id", "principal_id", "runtime_id")):
        conflict()
    anchor = c.execute(select(anchors).where(anchors.c.id == row["anchor_id"])).mappings().first()
    seal = checked(anchor)
    if (
        anchor["app_id"] != aid
        or type(anchor["revision"]) is not int
        or anchor["revision"] != saved.get("graph_revision")
        or fingerprint(seal) != fingerprint(saved)
    ):
        conflict("Independent graph anchor seal changed")
    accepted = lookup(c, user, aid, "derive", saved["derivation_key"])
    _, answer = checked_request(accepted)
    expected = {
        **metadata(saved),
        "graph": saved["graph"],
        "source_versions": saved["source_versions"],
    }
    accepted_body = {
        "expected_candidate_fingerprint": saved["candidate_fingerprint"],
        "request_key": saved["derivation_key"],
    }
    if accepted["request_fingerprint"] != fingerprint(accepted_body) or fingerprint(
        answer
    ) != fingerprint(expected):
        conflict("Independent derive receipt differs from graph anchor")
    for key, value in saved["source_versions"].items():
        entry = (
            c.execute(
                select(versions).where(
                    versions.c.app_id == aid,
                    versions.c.logical_key == key,
                    versions.c.revision == value["revision"],
                )
            )
            .mappings()
            .first()
        )
        snapshot = checked(entry)
        latest = c.execute(
            select(versions.c.revision)
            .where(versions.c.app_id == aid, versions.c.logical_key == key)
            .order_by(versions.c.revision.desc())
        ).scalar()
        if latest != value["revision"]:
            conflict("Source version ledger is ahead of saved anchor")
        if (
            snapshot.get("logical_key") != key
            or type(snapshot.get("revision")) is not int
            or snapshot["revision"] != value["revision"]
            or fingerprint(snapshot["definition"]) != value["content_fingerprint"]
        ):
            conflict("Source version ledger changed")
    return saved


def current_locks(c, user, pid, aid, ids):
    locked = []
    for row in c.execute(select(locks).where(locks.c.app_id == aid)).mappings():
        value = checked(row)
        if (
            set(value)
            != {
                "project_id",
                "app_id",
                "principal_id",
                "node_id",
                "logical_key",
                "locked",
                "revision",
                "request_key",
            }
            or type(value["locked"]) is not bool
            or type(value["revision"]) is not int
            or value["revision"] < 1
        ):
            conflict("Malformed trusted lock registry")
        if (
            value["app_id"] != aid
            or value["project_id"] != pid
            or value["principal_id"] != user
            or row["node_id"] != value["node_id"]
            or ids.get(value["logical_key"]) != value["node_id"]
        ):
            conflict("Trusted lock identity changed")
        record = lookup(c, user, aid, "lock", value["request_key"])
        request, response = checked_request(record)
        if (
            request.change.node_id != value["node_id"]
            or request.locked is not value["locked"]
            or request.request_key != value["request_key"]
        ):
            conflict("Accepted lock parameters changed")
        if fingerprint(response["lock"]) != fingerprint(value):
            conflict("Independent lock receipt changed")
        if value["locked"]:
            locked.append(value["node_id"])
    return sorted(locked)


@controlled
def set_lock(store, user, pid, aid, body, limits):
    """Internal explicit owner action; no public context/permission mutation API."""
    if not isinstance(body, LockInput):
        body = LockInput.model_validate(body)
    with store.tx() as c:
        saved = current(store, c, user, pid, aid, limits)
        if saved["graph"]["graph_fingerprint"] != body.expected_graph_fingerprint:
            conflict("Lock baseline changed")
        node = next((n for n in saved["graph"]["nodes"] if n["id"] == body.change.node_id), None)
        if (
            not node
            or node["revision"] != body.change.expected_revision
            or node["content_fingerprint"] != body.change.expected_content_fingerprint
        ):
            conflict("Lock node version changed")
        prior = lookup(c, user, aid, "lock", body.request_key)
        if prior:
            request, answer = checked_request(prior)
            if fingerprint(request.model_dump()) != fingerprint(body.model_dump()):
                conflict("Lock request key changed")
            return {**answer, "cached": True}
        row = (
            c.execute(select(locks).where(locks.c.app_id == aid, locks.c.node_id == node["id"]))
            .mappings()
            .first()
        )
        old = checked(row) if row else None
        value = dict(
            project_id=pid,
            app_id=aid,
            principal_id=user,
            node_id=node["id"],
            logical_key=node["key"],
            locked=body.locked,
            revision=old["revision"] + 1 if old else 1,
            request_key=body.request_key,
        )
        answer = {
            "namespace": NAMESPACE,
            "app_id": aid,
            "project_id": pid,
            "lock": value,
            "needs_derive": True,
            "patch_executed": False,
            "publishable": False,
        }
        values = dict(
            app_id=aid, node_id=node["id"], snapshot=value, fingerprint=fingerprint(value)
        )
        if row:
            c.execute(
                update(locks)
                .where(locks.c.app_id == aid, locks.c.node_id == node["id"])
                .values(**values)
            )
        else:
            c.execute(insert(locks).values(**values))
        remember(c, user, aid, "lock", body.request_key, body, answer)
        return {**answer, "cached": False}


def build(store, c, user, pid, aid, limits, previous=None):
    draft, manifest, action, _, rows, auth_fp = load_family(store, c, user, pid, aid, limits)
    keys, external = logical(store, c, draft, manifest, rows)
    ids = copy.deepcopy(previous["stable_ids"]) if previous else {}
    source_versions = {}
    writes = []
    for key, definition in sorted(external.items()):
        fp = fingerprint(definition)
        old = previous["source_versions"].get(key) if previous else None
        rev = (
            old["revision"]
            if old and old["content_fingerprint"] == fp
            else ((old["revision"] + 1) if old else 1)
        )
        source_versions[key] = core.SourceVersion(revision=rev, content_fingerprint=fp).model_dump()
        if not old or old["content_fingerprint"] != fp:
            writes.append({"logical_key": key, "revision": rev, "definition": definition})
    for key in sorted(keys):
        if key not in ids:
            if key.startswith("source:") or key.startswith("goal:") or key.startswith("manifest:"):
                ids[key] = key.split(":", 1)[1]
            elif key.startswith("action:"):
                step = next(s for s in manifest.workflow if "action:" + s.step_id == key)
                bound = next(b for b in manifest.action_bindings if b.binding_id == step.binding_id)
                ids[key] = (
                    bound.action_id if bound.action_id not in ids.values() else new_id("action")
                )
            else:
                ids[key] = new_id("node")
    active_ids = {k: ids[k] for k in keys}
    auth_rev = (
        previous["authorization_revision"]
        if previous and previous["authorization_fingerprint"] == auth_fp
        else (previous["authorization_revision"] + 1 if previous else 1)
    )
    ctx = dict(
        project_id=pid,
        app_id=aid,
        authorization_revision=auth_rev,
        authorized=True,
        resource_ids=sorted(r["id"] for r in rows),
        node_revisions={
            k: rev if rev is not None else source_versions[k]["revision"] for k, rev in keys.items()
        },
        locked_nodes=current_locks(c, user, pid, aid, active_ids),
        source_versions=source_versions,
        dependency_edges=[],
        unknown_dependencies=[
            dict(
                node_id=active_ids["manifest:" + aid],
                scope="PROJECT"
                if action.executor.kind in {"bounded_report", "bounded_agent"}
                else "APP",
                reason="Finite declarations do not certify full semantic dependency completeness; owner acceptance pending",
            )
        ],
        graph_fingerprint=None,
    )
    graph = core.derive_manifest_graph(
        manifest.model_dump(),
        draft["candidate"]["actions"],
        source_versions,
        active_ids,
        ctx,
        limits,
    )
    ctx["graph_fingerprint"] = graph["graph_fingerprint"]
    snapshot = dict(
        app_id=aid,
        project_id=pid,
        principal_id=user,
        runtime_id=draft["runtime_id"],
        candidate_fingerprint=draft["fingerprint"],
        stable_ids=ids,
        source_versions=source_versions,
        authorization_fingerprint=auth_fp,
        authorization_revision=auth_rev,
        graph_revision=(previous["graph_revision"] + 1 if previous else 1),
        derivation_key=previous["derivation_key"] if previous else "uncommitted",
        graph=graph,
        context=ctx,
    )
    return snapshot, writes


def metadata(saved):
    return dict(
        namespace=NAMESPACE,
        app_id=saved["app_id"],
        project_id=saved["project_id"],
        runtime_id=saved["runtime_id"],
        candidate_fingerprint=saved["candidate_fingerprint"],
        graph_revision=saved["graph_revision"],
        authorization_revision=saved["authorization_revision"],
        current_authorization_fingerprint=saved["authorization_fingerprint"],
        graph_fingerprint=saved["graph"]["graph_fingerprint"],
        state="PLANNING_ONLY",
        semantic_status="UNKNOWN",
        owner_acceptance="PENDING",
        patch_executed=False,
        business_write_performed=False,
        publishable=False,
        formal_publication_enabled=False,
    )


def current(store, c, user, pid, aid, limits):
    # Current source/identity authorization must precede protected ledger reads.
    load_family(store, c, user, pid, aid, limits)
    saved = state(store, c, user, pid, aid)
    fresh, _ = build(store, c, user, pid, aid, limits, saved)
    fresh["graph_revision"] = saved["graph_revision"]
    if fresh["authorization_fingerprint"] != saved["authorization_fingerprint"]:
        raise DomainError(
            "PERMISSION_DENIED", "Authorization state changed; explicitly derive a new anchor"
        )
    if fingerprint(fresh) != fingerprint(saved):
        conflict("Current graph baseline changed; explicitly derive a new anchor")
    return saved


def lookup(c, user, aid, kind, key):
    row = (
        c.execute(
            select(requests).where(
                requests.c.app_id == aid,
                requests.c.principal_id == user,
                requests.c.kind == kind,
                requests.c.request_key == key,
            )
        )
        .mappings()
        .first()
    )
    return row


def checked_request(row):
    stored = checked(row)
    if set(stored) != {"request", "response"}:
        conflict("Malformed request ledger")
    model = (
        DeriveInput
        if row["kind"] == "derive"
        else LockInput
        if row["kind"] == "lock"
        else PlanInput
    )
    body = model.model_validate(stored["request"])
    if (
        body.request_key != row["request_key"]
        or fingerprint(body.model_dump()) != row["request_fingerprint"]
    ):
        conflict("Accepted request parameters changed")
    return body, stored["response"]


def validate_plan_seal(c, user, aid, key, row):
    seal = lookup(c, user, aid, "plan_seal", key)
    checked_request(seal)
    if fingerprint(checked(seal)) != fingerprint(checked(row)):
        conflict("Independent accepted plan seal changed")


def remember(c, user, aid, kind, key, body, value):
    stored = {"request": body.model_dump(), "response": value}
    c.execute(
        insert(requests).values(
            app_id=aid,
            principal_id=user,
            kind=kind,
            request_key=key,
            request_fingerprint=fingerprint(body.model_dump()),
            snapshot=stored,
            fingerprint=fingerprint(stored),
        )
    )


@controlled
def derive(store, user, pid, aid, body, limits):
    with store.tx() as c:
        draft, *_ = load_family(store, c, user, pid, aid, limits)
        if draft["fingerprint"] != body.expected_candidate_fingerprint:
            conflict("Candidate version changed")
        row = c.execute(select(states).where(states.c.app_id == aid)).mappings().first()
        old = state(store, c, user, pid, aid) if row else None
        prior = lookup(c, user, aid, "derive", body.request_key)
        fp = fingerprint(body.model_dump())
        if prior:
            saved = current(store, c, user, pid, aid, limits)
            _, answer = checked_request(prior)
            if (
                prior["request_fingerprint"] != fp
                or answer["graph_fingerprint"] != saved["graph"]["graph_fingerprint"]
                or answer["candidate_fingerprint"] != saved["candidate_fingerprint"]
            ):
                conflict("Derive request key or current baseline changed")
            expected_answer = {
                **metadata(saved),
                "graph": saved["graph"],
                "source_versions": saved["source_versions"],
            }
            if fingerprint(answer) != fingerprint(expected_answer):
                conflict("Derive receipt metadata changed")
            return {**answer, "cached": True}
        saved, writes = build(store, c, user, pid, aid, limits, old)
        normalized = {**saved, "graph_revision": old["graph_revision"]} if old else None
        if old and fingerprint(normalized) == fingerprint(old):
            answer = {
                **metadata(old),
                "graph": old["graph"],
                "source_versions": old["source_versions"],
            }
            remember(c, user, aid, "derive", body.request_key, body, answer)
            return {**answer, "cached": False}
        saved["derivation_key"] = body.request_key
        # All compile/source/auth/version checks finish before the first insert.
        anchor_id = new_id("graph")
        for entry in writes:
            c.execute(
                insert(versions).values(
                    app_id=aid,
                    logical_key=entry["logical_key"],
                    revision=entry["revision"],
                    snapshot=entry,
                    fingerprint=fingerprint(entry),
                )
            )
        c.execute(
            insert(anchors).values(
                id=anchor_id,
                app_id=aid,
                revision=saved["graph_revision"],
                snapshot=saved,
                fingerprint=fingerprint(saved),
            )
        )
        values = dict(
            app_id=aid,
            project_id=pid,
            principal_id=user,
            runtime_id=draft["runtime_id"],
            anchor_id=anchor_id,
            snapshot=saved,
            fingerprint=fingerprint(saved),
        )
        if row:
            c.execute(update(states).where(states.c.app_id == aid).values(**values))
        else:
            c.execute(insert(states).values(**values))
        answer = {
            **metadata(saved),
            "graph": saved["graph"],
            "source_versions": saved["source_versions"],
        }
        remember(c, user, aid, "derive", body.request_key, body, answer)
        return {**answer, "cached": False}


@controlled
def inspect(store, user, pid, aid, limits):
    with store.tx() as c:
        saved = current(store, c, user, pid, aid, limits)
        return {
            **metadata(saved),
            "graph": saved["graph"],
            "source_versions": saved["source_versions"],
        }


def expansion(store, c, user, pid, aid, receipt, limits, key):
    targets = (
        [aid]
        if receipt["revalidation_scope"] != "PROJECT"
        else list(
            c.execute(
                select(app_drafts.c.id)
                .where(app_drafts.c.project_id == pid)
                .order_by(app_drafts.c.id)
            ).scalars()
        )
    )
    planned, omitted, applications, membership = [], [], [], []
    for target in targets:
        row = c.execute(
            select(app_drafts.c.fingerprint).where(app_drafts.c.id == target)
        ).scalar_one()
        membership.append({"app_id": target, "candidate_fingerprint": row})
        try:
            peer = current(store, c, user, pid, target, limits)
        except DomainError as exc:
            reason = (
                "GRAPH_NOT_DERIVED"
                if exc.message == "DeliveryGraph anchor has not been derived"
                else exc.code
            )
            omitted.append(dict(app_id=target, reason=reason))
            continue
        if peer["context"]["locked_nodes"]:
            raise DomainError(
                "LOCK_CONFLICT", "Project revalidation affects a manually locked graph"
            )
        binding = dict(
            project_id=pid,
            app_id=target,
            candidate_fingerprint=peer["candidate_fingerprint"],
            graph_fingerprint=peer["graph"]["graph_fingerprint"],
            authorization_revision=peer["authorization_revision"],
            graph_revision=peer["graph_revision"],
            locked_nodes=peer["context"]["locked_nodes"],
            lock_fingerprint=fingerprint(
                [
                    checked(row)
                    for row in c.execute(
                        select(locks).where(locks.c.app_id == target).order_by(locks.c.node_id)
                    ).mappings()
                ]
            ),
        )
        applications.append(binding)
        planned.append(
            dict(
                id=new_id("scopejob"),
                **binding,
                source_app_id=aid,
                request_key=key,
                scope=receipt["revalidation_scope"],
                reason="Conservative declaration/semantic revalidation; no check or patch executed",
                status="PENDING",
            )
        )
    binding = dict(
        scope=receipt["revalidation_scope"],
        applications=applications,
        snapshot_fingerprint=fingerprint(applications),
        membership=membership,
        membership_fingerprint=fingerprint(membership),
        status="BLOCKED_PARTIAL" if omitted else "PENDING",
        omissions=omitted,
    )
    return planned, binding


def seal_outer(answer):
    public_fields = (
        "project_id",
        "app_id",
        "graph_fingerprint",
        "authorization_revision",
        "locked_nodes",
    )
    applications = [
        {k: v[k] for k in public_fields} for v in answer["scope_expansion"]["applications"]
    ]
    expansion = {
        "scope": answer["scope_expansion"]["scope"],
        "applications": applications,
        "snapshot_fingerprint": fingerprint(applications),
    }
    answer["expansion"] = expansion
    answer["outer_fingerprint"] = fingerprint({"core": answer["receipt"], "expansion": expansion})
    answer["native_outer_fingerprint"] = fingerprint(
        {k: v for k, v in answer.items() if k != "native_outer_fingerprint"}
    )
    return answer


def verify_outer(answer):
    base = {
        k: v
        for k, v in answer.items()
        if k not in {"expansion", "outer_fingerprint", "native_outer_fingerprint"}
    }
    if fingerprint(seal_outer(base)) != fingerprint(answer):
        conflict("Outer receipt binding changed")


@controlled
def plan(store, user, pid, aid, body, limits):
    with store.tx() as c:
        saved = current(store, c, user, pid, aid, limits)
        request = dict(
            project_id=pid,
            app_id=aid,
            request_key=body.request_key,
            changes=[v.model_dump() for v in body.changes],
        )
        fp = fingerprint(body.model_dump())
        prior = lookup(c, user, aid, "plan", body.request_key)
        prior_answer = checked_request(prior)[1] if prior else None
        if prior and prior["request_fingerprint"] != fp:
            conflict("Plan request key changed")
        receipt = core.plan_change(
            saved["graph"],
            body.expected_graph_fingerprint,
            request,
            saved["context"],
            prior_answer["receipt"] if prior else None,
        )
        # Canonical fingerprint check defends strict bool/int even before core fix.
        if prior:
            validate_plan_seal(c, user, aid, body.request_key, prior)
            verify_outer(prior_answer)
            if set(prior_answer) != set(metadata(saved)) | {
                "receipt",
                "scope_jobs",
                "scope_expansion",
                "outer_fingerprint",
                "native_outer_fingerprint",
                "expansion",
            } or fingerprint({k: prior_answer[k] for k in metadata(saved)}) != fingerprint(
                metadata(saved)
            ):
                conflict("Plan receipt baseline changed")
            if fingerprint(prior_answer["receipt"]) != fingerprint(receipt):
                conflict("Persistent plan receipt changed")
            verify_jobs(c, user, aid, body.request_key, prior_answer["scope_jobs"])
            latest_jobs, latest_binding = expansion(
                store, c, user, pid, aid, receipt, limits, body.request_key
            )

            def targets(items):
                return sorted(
                    [{k: v for k, v in item.items() if k != "id"} for item in items],
                    key=lambda v: v["app_id"],
                )

            if fingerprint(targets(latest_jobs)) != fingerprint(
                targets(prior_answer["scope_jobs"])
            ) or fingerprint(latest_binding) != fingerprint(prior_answer["scope_expansion"]):
                conflict("Project revalidation membership or authority changed")
            return {**prior_answer, "cached": True}
        scope_jobs, binding = expansion(store, c, user, pid, aid, receipt, limits, body.request_key)
        answer = {
            **metadata(saved),
            "receipt": receipt,
            "scope_jobs": scope_jobs,
            "scope_expansion": binding,
        }
        seal_outer(answer)
        for value in scope_jobs:
            c.execute(
                insert(jobs).values(
                    id=value["id"],
                    project_id=pid,
                    principal_id=user,
                    app_id=value["app_id"],
                    source_app_id=aid,
                    request_key=body.request_key,
                    snapshot=value,
                    fingerprint=fingerprint(value),
                    status="PENDING",
                )
            )
        remember(c, user, aid, "plan", body.request_key, body, answer)
        remember(c, user, aid, "plan_seal", body.request_key, body, answer)
        return {**answer, "cached": False}


def verify_jobs(c, user, aid, key, expected):
    rows = (
        c.execute(
            select(jobs)
            .where(
                jobs.c.source_app_id == aid, jobs.c.principal_id == user, jobs.c.request_key == key
            )
            .order_by(jobs.c.app_id)
        )
        .mappings()
        .all()
    )
    actual = [checked(row) for row in rows]
    if fingerprint(sorted(actual, key=lambda v: v["app_id"])) != fingerprint(
        sorted(expected, key=lambda v: v["app_id"])
    ) or any(row["status"] != "PENDING" for row in rows):
        conflict("Revalidation queue receipt changed")


@controlled
def history(store, user, pid, aid, limits):
    with store.tx() as c:
        saved = current(store, c, user, pid, aid, limits)
        items = []
        for row in c.execute(
            select(requests)
            .where(
                requests.c.app_id == aid, requests.c.principal_id == user, requests.c.kind == "plan"
            )
            .order_by(requests.c.request_key)
        ).mappings():
            body, value = checked_request(row)
            validate_plan_seal(c, user, aid, row["request_key"], row)
            historical_row = (
                c.execute(
                    select(anchors).where(
                        anchors.c.app_id == aid, anchors.c.revision == value["graph_revision"]
                    )
                )
                .mappings()
                .first()
            )
            historical = checked(historical_row)
            SavedState.model_validate(historical)
            request = {
                "project_id": pid,
                "app_id": aid,
                "request_key": body.request_key,
                "changes": [v.model_dump() for v in body.changes],
            }
            expected = core.plan_change(
                historical["graph"], body.expected_graph_fingerprint, request, historical["context"]
            )
            if fingerprint(expected) != fingerprint(value["receipt"]) or fingerprint(
                {k: value[k] for k in metadata(historical)}
            ) != fingerprint(metadata(historical)):
                conflict("Historical receipt no longer matches independent graph anchor")
            verify_jobs(c, user, aid, row["request_key"], value["scope_jobs"])
            _, binding = expansion(
                store, c, user, pid, aid, value["receipt"], limits, row["request_key"]
            )
            verify_outer(value)
            if fingerprint(binding) != fingerprint(value["scope_expansion"]):
                conflict("Historical project graph/authority/lock membership changed")
            public_jobs = []
            for job in value["scope_jobs"]:
                try:
                    draft, *_ = load_family(store, c, user, pid, job["app_id"], limits)
                    if draft["fingerprint"] != job["candidate_fingerprint"]:
                        conflict()
                    public_jobs.append(job)
                except DomainError as exc:
                    public_jobs.append(
                        {
                            "id": job["id"],
                            "app_id": job["app_id"],
                            "status": "BLOCKED_PERMISSION"
                            if exc.code in {"PERMISSION_DENIED", "GRANT_REVOKED"}
                            else "BLOCKED_VERSION",
                            "reason": exc.code,
                        }
                    )
            items.append({**value, "scope_jobs": public_jobs, "request_key": row["request_key"]})
        return {**metadata(saved), "items": items}


def mount(app, store, identity, limits, settings=None):
    dependency = Depends(identity)
    base = "/api/projects/{pid}/apps/{aid}/delivery-graph"

    @app.get(base)
    def read(pid: str, aid: str, user=dependency):
        return inspect(store, user, pid, aid, limits)

    @app.post(base + "/derive", status_code=201)
    def save(pid: str, aid: str, body: DeriveInput, user=dependency):
        return derive(store, user, pid, aid, body, limits)

    @app.post(base + "/plans", status_code=201)
    def changes(pid: str, aid: str, body: PlanInput, user=dependency):
        return plan(store, user, pid, aid, body, limits)

    @app.get(base + "/plans")
    def receipts(pid: str, aid: str, user=dependency):
        return history(store, user, pid, aid, limits)
