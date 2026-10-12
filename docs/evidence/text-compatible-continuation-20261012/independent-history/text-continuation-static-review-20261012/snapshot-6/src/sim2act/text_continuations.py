"""Explicit, instance-scoped continuation of two known literal software versions.

Old seals stay immutable. Archival reads never grant execution; a new sealed
software permission and Release authorize exactly one existing instance revision.
"""

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select, update

from . import delivery_graph_apps as graph
from . import text_logic_reuse as logic
from .contracts import Strict, validate_value
from .csv_logic_reuse import implementation
from .db import (
    app_drafts,
    delivery_graph_requests,
    fingerprint,
    internal_app_runs,
    internal_approvals,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    new_id,
    runs,
)
from .errors import DomainError
from .tools import authorized_read

VERSION = "literal-software-continuation.v1"
PREPARE, META, COMMIT, INDEX = ("text_software_" + s for s in ("prepare", "metadata", "commit", "app_index"))
CANCEL, REVOKE = "text_software_cancel", "text_software_revoke"
MAX = 64
ANCHOR_HASH = "24f26f3621b8fc49a24fa3566484b568148d9317f2d279d79f264416b994193a"
CHANGED = {"api.py", "app_jobs.py", "internal_api.py", "owner_acceptance.py", "app_owner_goals.py",
           "apps.py", "lifecycle.py", "text_logic_reuse.py", "text_continuations.py", "text_run_checks.py"}
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}


class PrepareInput(Strict):
    expected_revision: int = Field(ge=1)
    expected_release_fingerprint: str = Field(pattern=graph.HASH)
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_source_implementation: str = Field(pattern=graph.HASH)
    input: dict
    request_key: str = Field(pattern=logic.KEY)


class CommitInput(Strict):
    approval_id: str = Field(pattern=r"^iapproval_[a-f0-9]{32}$")
    expected_approval_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["CONTINUE_ONLY_THIS_EXACT_EXISTING_INSTANCE_WITH_THIS_SOFTWARE"]
    request_key: str = Field(pattern=logic.KEY)


class MetaInput(Strict):
    instance_id: str
    project_id: str
    principal_id: str
    prepare_key: str
    prepare_request_fingerprint: str
    approval_id: str
    approval_fingerprint: str


class IndexInput(Strict):
    app_id: str
    instance_id: str
    principal_id: str
    project_id: str
    commit_key: str
    release_id: str
    record_fingerprint: str = Field(pattern=graph.HASH)


class StopInput(Strict):
    command: Literal["CANCEL", "REVOKE"]
    target_key: str = Field(pattern=logic.KEY)
    expected_record_fingerprint: str | None = Field(default=None, pattern=graph.HASH)
    reason: str = Field(min_length=1, max_length=500)
    request_key: str = Field(pattern=logic.KEY)


def known(fp):
    raw = Path(__file__).with_name("text_software_anchors.json").read_bytes()
    logic.require(hashlib.sha256(raw).hexdigest() == ANCHOR_HASH)
    anchors = json.loads(raw)
    if fp not in anchors:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Unknown software has no finite literal compatibility contract")
    files = anchors[fp]["files"]
    logic.require(fingerprint(files) == fp)
    current = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py") if p.name != "config.py"}
    logic.require(not (set(current) - set(files) - CHANGED))
    logic.require(all(current.get(name) == sha for name, sha in files.items() if name not in CHANGED),
                  "Literal kernel or unknown software dependency changed")
    return anchors[fp]


def software(c, user, draft):
    if not logic.independent(draft):
        return None
    lid = draft["candidate"]["task_proof"]["proof"]["logic_id"]
    row = c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id == lid,
        internal_approvals.c.principal_id == user, internal_approvals.c.kind == logic.AUTH)).scalar_one_or_none()
    logic.require(isinstance(row, dict))
    fp = row["implementation_fingerprint"]
    return fp if fp != implementation() else None


def owned(store, c, user, iid):
    row = c.execute(select(internal_instances).where(internal_instances.c.id == iid,
        internal_instances.c.principal_id == user)).mappings().first()
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    store.lock_project(c, user, row["project_id"])
    return row


def keys(c, user, scope, kind):
    rows = c.execute(select(delivery_graph_requests.c.request_key, delivery_graph_requests.c.kind).where(
        delivery_graph_requests.c.app_id == scope, delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind.in_([kind, kind + "_seal"]))).mappings().all()
    a, b = [{r["request_key"] for r in rows if r["kind"] == k} for k in (kind, kind + "_seal")]
    logic.require(a == b and len(a) <= MAX)
    return sorted(a)


def metadata(c, user, iid, key):
    body, value = logic.pair(c, user, iid, META, key, MetaInput)
    logic.require(body.instance_id == iid and body.principal_id == user
                  and body.prepare_key == key and fingerprint(body.model_dump()) == fingerprint(value))
    return value


def stopped(c, user, iid, commit_key):
    # Each stop is itself double sealed, bound to this owned instance and exact key.
    for key in keys(c, user, iid, REVOKE):
        body, value = logic.pair(c, user, iid, REVOKE, key, StopInput)
        logic.require(value == {"instance_id": iid, "principal_id": user, "command": "REVOKE",
                               "target_key": body.target_key, "stopped": True})
        if body.target_key == commit_key:
            return True
    return False


def committed(c, user, iid, key, *, check_software=True):
    body, value = logic.pair(c, user, iid, COMMIT, key, CommitInput)
    logic.require(body.request_key == key and set(value) == {"version", "instance_id", "project_id", "principal_id",
        "app_id", "runtime_id", "source_implementation", "target_implementation", "candidate_fingerprint",
        "resource_id", "source_hash", "release_id", "release_fingerprint", "revision", "previous_release_id",
        "approval_id", "approval_fingerprint", "prepare_key", "data_version_at_commit", "model_requests",
        "formal_publication_enabled", "semantic_status"})
    logic.require(value["version"] == VERSION and value["instance_id"] == iid and value["principal_id"] == user
        and value["approval_id"] == body.approval_id and value["approval_fingerprint"] == body.expected_approval_fingerprint
        and type(value["revision"]) is int and value["revision"] >= 2
        and type(value["data_version_at_commit"]) is int and value["data_version_at_commit"] >= 0
        and value["model_requests"] == 0 and value["formal_publication_enabled"] is False and value["semantic_status"] == "UNKNOWN")
    if check_software:
        known(value["source_implementation"])
        parent = c.execute(select(internal_approvals).where(internal_approvals.c.id == body.approval_id)).mappings().first()
        logic.require(parent is not None and parent["kind"] == PREPARE and parent["consumed"] is True
            and parent["principal_id"] == user and parent["project_id"] == value["project_id"]
            and fingerprint(parent["payload"]) == parent["fingerprint"] == body.expected_approval_fingerprint)
        prep, prepared = logic.pair(c, user, iid, PREPARE, value["prepare_key"], PrepareInput)
        p = parent["payload"]["continuation"]
        logic.require(fingerprint(prep.model_dump()) == fingerprint(parent["payload"]["request"])
            and prepared["approval_id"] == body.approval_id
            and prepared["approval_fingerprint"] == parent["fingerprint"]
            and prepared["expires_at"] == parent["expires_at"]
            and fingerprint(prepared["preflight"]) == fingerprint(p))
        snap = snapshot_for(p, iid, p["revision"] + 1, body)
        expected = permit_for(p, body, value["prepare_key"], value["release_id"], fingerprint(snap))
        logic.require(fingerprint(expected) == fingerprint(value), "Software receipt differs from exact approved preflight")
    return body, value


def archival_app(store, c, user, draft, old_fp):
    """Current approved software parses the unchanged old app for authorized reads."""
    for key in keys(c, user, draft["id"], INDEX):
        body, value = logic.pair(c, user, draft["id"], INDEX, key, IndexInput)
        logic.require(fingerprint(body.model_dump()) == fingerprint(value)
            and body.app_id == draft["id"] and body.principal_id == user and body.project_id == draft["project_id"])
        _, permit = committed(c, user, body.instance_id, body.commit_key)
        row = graph.lookup(c, user, body.instance_id, COMMIT, body.commit_key)
        logic.require(row["fingerprint"] == body.record_fingerprint and permit["app_id"] == draft["id"]
                      and permit["release_id"] == body.release_id)
        if (permit["target_implementation"] == implementation() and permit["source_implementation"] == old_fp
            and permit["candidate_fingerprint"] == draft["fingerprint"] and permit["runtime_id"] == draft["runtime_id"]):
            return permit
    raise DomainError("VERSION_CONFLICT", "Explicit compatible software approval required; archival reading grants no execution")


def execution(store, c, user, instance, release, limits):
    draft = release["snapshot"]["draft"]
    fp = software(c, user, draft)
    marker = release["snapshot"].get("software_continuation")
    if fp is None:
        if marker is not None:
            raise DomainError("VERSION_CONFLICT", "Continuation cannot change executor family/software origin")
        return
    known(fp)
    logic.require(isinstance(marker, dict) and set(marker) == {"version", "instance_id", "revision", "commit_key", "approval_id"})
    _, permit = committed(c, user, instance["id"], marker["commit_key"])
    logic.require(marker == {"version": VERSION, "instance_id": instance["id"], "revision": permit["revision"],
        "commit_key": marker["commit_key"], "approval_id": permit["approval_id"]}
        and not stopped(c, user, instance["id"], marker["commit_key"])
        and permit["target_implementation"] == implementation() and permit["source_implementation"] == fp
        and permit["project_id"] == instance["project_id"] == release["project_id"]
        and permit["app_id"] == instance["source_app_id"] == draft["id"]
        and permit["runtime_id"] == instance["runtime_id"] == draft["runtime_id"]
        and permit["candidate_fingerprint"] == draft["fingerprint"]
        and permit["release_id"] == instance["release_id"] == release["id"]
        and permit["release_fingerprint"] == release["fingerprint"]
        and type(instance["revision"]) is int and permit["revision"] == instance["revision"])
    logic.verify_candidate(store, c, user, draft, limits, archival_software=fp)


def no_context(store, c, user, draft):
    if software(c, user, draft) is not None:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Legacy literal software requires its explicitly approved existing instance; no generic execution or new instance")


def legacy_release(store, c, user, row, limits, old_fp):
    from .apps import compile_preview, validate_source_family
    from .lifecycle import NAMESPACE, record_schema

    known(old_fp)
    a = c.execute(select(internal_approvals).where(internal_approvals.c.id == row["approval_id"])).mappings().first()
    s = row["snapshot"]
    logic.require(a is not None and a["kind"] == "release" and a["consumed"] is True
        and a["principal_id"] == row["principal_id"] == user and a["project_id"] == row["project_id"]
        and fingerprint(a["payload"]) == a["fingerprint"] and fingerprint(a["payload"]["snapshot"]) == row["fingerprint"]
        and fingerprint(s) == row["fingerprint"] and s["namespace"] == NAMESPACE
        and s["formal_publication_enabled"] is False and s["model_requests"] == 0
        and set(s) == {"namespace", "draft", "dependency_lock", "data_schema", "data_schema_version", "check_evidence", "model_requests", "formal_publication_enabled"})
    draft = s["draft"]
    logic.require(draft["project_id"] == row["project_id"])
    validate_source_family(c, user, draft)
    logic.verify_candidate(store, c, user, draft, limits, archival_software=old_fp)
    _, _, report = compile_preview(draft["candidate"], limits)
    logic.require(s["dependency_lock"] == draft["candidate"]["manifest"]["dependency_lock"]
                  and s["check_evidence"]["candidate_fingerprint"] == draft["fingerprint"]
                  and s["check_evidence"]["status"] == "PASS" and s["check_evidence"]["ref"] == "source.literal_evidence.v1"
                  and s["check_evidence"]["plan_fingerprint"] == fingerprint(report)
                  and type(s["data_schema_version"]) is int and s["data_schema_version"] >= 1)
    record_schema(draft["candidate"], s["data_schema"])
    logic.verify_release_index(c, user, row)
    from .lifecycle import validate_source_bytes

    validate_source_bytes(store, c, user, draft)
    return draft


def goal_anchor(store, c, user, draft, limits, old_fp):
    obj, _, _ = logic.verify_candidate(store, c, user, draft, limits, archival_software=old_fp)
    rid = draft["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
    source = authorized_read(store, c, user, draft["runtime_id"], draft["project_id"], "resource.read", {"resource_id": rid})
    logic.require(source["hash"] == draft["candidate"]["source_hash"])
    return dict(app_id=draft["id"], owner_id=user, project_id=draft["project_id"], runtime_id=draft["runtime_id"],
        candidate_fingerprint=draft["fingerprint"], resource_id=rid, source_hash=source["hash"],
        logic_id=obj["id"], logic_fingerprint=obj["fingerprint"])


def preconditions(store, c, user, iid, body, limits):
    from . import app_owner_goals, lifecycle, owner_acceptance, text_apps
    from .agent_apps import check_evidence
    from .apps import compile_preview

    i = owned(store, c, user, iid)
    target_gate(store, c, user, i)
    draft = c.execute(select(app_drafts).where(app_drafts.c.id == i["source_app_id"])).mappings().one()
    old_fp = software(c, user, draft)
    logic.require(old_fp is not None and old_fp == body.expected_source_implementation)
    known(old_fp)
    obj, _, _ = logic.verify_candidate(store, c, user, draft, limits, archival_software=old_fp)
    r = c.execute(select(internal_releases).where(internal_releases.c.id == i["release_id"])).mappings().one()
    frozen = legacy_release(store, c, user, r, limits, old_fp)
    logic.require(i["project_id"] == draft["project_id"] and i["runtime_id"] == draft["runtime_id"]
        and fingerprint(frozen) == fingerprint({k: draft[k] for k in frozen})
        and i["revision"] == body.expected_revision and type(i["revision"]) is int
        and r["fingerprint"] == body.expected_release_fingerprint
        and draft["fingerprint"] == body.expected_candidate_fingerprint
        and type(i["data_version"]) is int and i["data_version"] >= 0
        and 1 <= len(i["history"]) < MAX and i["history"][-1]["release_id"] == r["id"]
        and i["history"][-1]["revision"] == i["revision"])
    jobs = c.execute(select(internal_app_runs.c.id, internal_app_runs.c.status, internal_run_bindings.c.run_id)
        .outerjoin(internal_run_bindings, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
        .where(internal_app_runs.c.instance_id == iid).limit(MAX + 1)).mappings().all()
    if len(jobs) > MAX:
        raise DomainError("BUDGET_EXHAUSTED", "Finite software preflight supports at most64 historical jobs")
    for j in jobs:
        job = c.execute(select(runs).where(runs.c.id == j["run_id"])).mappings().first()
        logic.require(job is not None and job["principal_id"] == user and job["project_id"] == i["project_id"])
        if j["status"] not in TERMINAL or job["status"] not in TERMINAL or store.has_unknown(c, job["id"]):
            raise DomainError("OUTCOME_UNKNOWN", "Stop or reconcile outstanding instance jobs before software preflight")
        logic.require(j["status"] == job["status"])
    rows = c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == iid)
        .order_by(internal_instance_data.c.version).limit(MAX + 1)).mappings().all()
    logic.require(len(rows) == i["data_version"] <= MAX)
    rid = draft["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
    source = authorized_read(store, c, user, draft["runtime_id"], i["project_id"], "resource.read", {"resource_id": rid})
    logic.require(source["hash"] == draft["candidate"]["source_hash"] and source["format"] in {"txt", "md"})
    checked_rows = lifecycle.data_rows(c, iid)
    logic.require(fingerprint([dict(r) for r in checked_rows]) == fingerprint([dict(r) for r in rows]))
    for version, row in enumerate(rows, 1):
        logic.require(type(row["version"]) is int and row["version"] == version and fingerprint(row["data"]) == row["fingerprint"])
        validate_value(r["snapshot"]["data_schema"], row["data"])
        result = row["data"]["result"]
        check_evidence(source, {"resource_id": rid, "term": result["term"]}, result)
        from .text_run_checks import verify

        run_id = next((j["run_id"] for j in jobs if j["id"] == row["run_id"]), None)
        logic.require(run_id is not None)
        job = c.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
        verify(store, c, user, job, limits, archival_software=old_fp)
    manifest, _, report = compile_preview(draft["candidate"], limits)
    validate_value(manifest.input_schema, body.input)
    output = text_apps.compute(source, {"resource_id": rid, **body.input})
    check = {"ref": "source.literal_evidence.v1", "status": "PASS"}
    anchor = dict(app_id=draft["id"], owner_id=user, project_id=i["project_id"], runtime_id=draft["runtime_id"],
        candidate_fingerprint=draft["fingerprint"], resource_id=rid, source_hash=source["hash"],
        logic_id=obj["id"], logic_fingerprint=obj["fingerprint"])
    goals = app_owner_goals.records(c, user, draft["id"], anchor)
    head = app_owner_goals.head(c, user, anchor, goals)
    owners = owner_acceptance.ledger(c, user, iid)
    for row in owners:
        owner_acceptance.payload(c, row)
    return dict(version=VERSION, instance_id=iid, project_id=i["project_id"], principal_id=user,
        app_id=draft["id"], runtime_id=draft["runtime_id"], source_implementation=old_fp,
        target_implementation=implementation(), source_commit=known(old_fp)["commit"],
        source_release_id=r["id"], source_release_fingerprint=r["fingerprint"], revision=i["revision"],
        data_version=i["data_version"], data_fingerprint=fingerprint([dict(x) for x in rows]),
        history_fingerprint=fingerprint(i["history"]), candidate_fingerprint=draft["fingerprint"],
        resource_id=rid, source_hash=source["hash"], grant_version=lifecycle.grant_version(c, i["project_id"], user),
        limits=limits.model_dump(), goal_fingerprint=fingerprint({"goals": [[b.model_dump(), v] for b, v in goals], "head": head}),
        owner_ledger_fingerprint=fingerprint([dict(x) for x in owners]),
        old_snapshot=copy.deepcopy(r["snapshot"]), input=copy.deepcopy(body.input), output=output,
        check=check, plan_fingerprint=fingerprint(report), retained_records=len(rows),
        data_preserved=True, new_grants=False, model_requests=0, semantic_status="UNKNOWN", formal_publication_enabled=False)


def snapshot_for(p, iid, revision, body):
    snap = copy.deepcopy(p["old_snapshot"])
    snap["software_continuation"] = dict(version=VERSION, instance_id=iid, revision=revision,
        commit_key=body.request_key, approval_id=body.approval_id)
    snap["check_evidence"] = dict(ref="source.literal_evidence.v1", status="PASS", candidate_fingerprint=p["candidate_fingerprint"],
        input_fingerprint=fingerprint(p["input"]), output_fingerprint=fingerprint(p["output"]), plan_fingerprint=p["plan_fingerprint"])
    return snap


def permit_for(p, body, key, rid, release_fp):
    permit = {k: p[k] for k in ["version", "instance_id", "project_id", "principal_id", "app_id", "runtime_id", "source_implementation", "target_implementation", "candidate_fingerprint", "resource_id", "source_hash", "model_requests", "formal_publication_enabled", "semantic_status"]}
    permit.update(release_id=rid, release_fingerprint=release_fp, revision=p["revision"]+1,
        previous_release_id=p["source_release_id"], approval_id=body.approval_id, approval_fingerprint=body.expected_approval_fingerprint,
        prepare_key=key, data_version_at_commit=p["data_version"])
    return permit


def before_private_preflight(store, c, user, i, limits):
    target_gate(store, c, user, i)
    draft = c.execute(select(app_drafts).where(app_drafts.c.id == i["source_app_id"])).mappings().one()
    old_fp = software(c, user, draft)
    logic.require(old_fp is not None)
    logic.verify_candidate(store, c, user, draft, limits, archival_software=old_fp)


def target_gate(store, c, user, i):
    row = c.execute(select(app_drafts.c.project_id, app_drafts.c.runtime_id,
        app_drafts.c.candidate["manifest"]["data_bindings"][0]["resource_ref"].as_string().label("rid"))
        .where(app_drafts.c.id == i["source_app_id"])).mappings().first()
    logic.require(row is not None and row["project_id"] == i["project_id"] and row["runtime_id"] == i["runtime_id"])
    store.authorize(c, user, row["runtime_id"], row["project_id"], row["rid"], "resource.read")


def draft_gate(store, c, user, aid):
    from .db import task_extractions

    # Indexed origin metadata identifies this family before protected app bodies.
    exists = c.execute(select(task_extractions.c.app_id).where(task_extractions.c.app_id == aid,
        task_extractions.c.snapshot["kind"].as_string() == logic.KIND)).first()
    if exists is None:
        proof_kind = c.execute(select(app_drafts.c.candidate["task_proof"]["proof"]["kind"].as_string())
            .where(app_drafts.c.id == aid)).scalar_one_or_none()
        if proof_kind != logic.PROOF:
            return
    row = c.execute(select(app_drafts.c.project_id, app_drafts.c.runtime_id,
        app_drafts.c.candidate["manifest"]["data_bindings"][0]["resource_ref"].as_string().label("rid"))
        .where(app_drafts.c.id == aid)).mappings().first()
    logic.require(row is not None)
    store.own_project(c, user, row["project_id"])
    store.authorize(c, user, row["runtime_id"], row["project_id"], row["rid"], "resource.read")


def release_gate(store, c, user, rid):
    aid = c.execute(select(internal_releases.c.snapshot["draft"]["id"].as_string())
        .where(internal_releases.c.id == rid, internal_releases.c.principal_id == user)).scalar_one_or_none()
    if aid is not None:
        draft_gate(store, c, user, aid)


def job_gate(store, c, user, rid):
    aid = c.execute(select(internal_instances.c.source_app_id)
        .join(internal_app_runs, internal_app_runs.c.instance_id == internal_instances.c.id)
        .join(internal_run_bindings, internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
        .where(internal_run_bindings.c.run_id == rid, internal_instances.c.principal_id == user)).scalar_one_or_none()
    if aid is not None:
        draft_gate(store, c, user, aid)


@graph.controlled
def prepare(store, user, iid, body, limits):
    from . import lifecycle

    with store.tx() as c:
        i = owned(store, c, user, iid)
        before_private_preflight(store, c, user, i, limits)
        if graph.lookup(c, user, iid, CANCEL, body.request_key) or graph.lookup(c, user, iid, CANCEL + "_seal", body.request_key):
            raise DomainError("VERSION_CONFLICT", "Original software intent was cancelled")
        for key in keys(c, user, iid, PREPARE):
            if key == body.request_key:
                prior, value = logic.pair(c, user, iid, PREPARE, key, PrepareInput)
                logic.require(fingerprint(prior.model_dump()) == fingerprint(body.model_dump()))
                lifecycle.approval(c, user, value["approval_id"], value["approval_fingerprint"], PREPARE)
                logic.require(fingerprint(preconditions(store, c, user, iid, body, limits)) == fingerprint(value["preflight"]))
                return value
        if len(keys(c, user, iid, PREPARE)) >= MAX:
            raise DomainError("BUDGET_EXHAUSTED")
        if graph.lookup(c, user, iid, CANCEL, body.request_key) or graph.lookup(c, user, iid, CANCEL + "_seal", body.request_key):
            raise DomainError("VERSION_CONFLICT", "Original software intent was cancelled")
        value = preconditions(store, c, user, iid, body, limits)
        approval = lifecycle.new_approval(c, user, i["project_id"], PREPARE, {"continuation": value, "request": body.model_dump()})
        expiry = c.execute(select(internal_approvals.c.expires_at).where(internal_approvals.c.id == approval["id"])).scalar_one()
        value = {"approval_id": approval["id"], "approval_fingerprint": approval["fingerprint"], "expires_at": expiry, "preflight": value}
        logic.remember(c, user, iid, PREPARE, body.request_key, body, value)
        meta = MetaInput(instance_id=iid, project_id=i["project_id"], principal_id=user, prepare_key=body.request_key,
            prepare_request_fingerprint=fingerprint(body.model_dump()), approval_id=approval["id"], approval_fingerprint=approval["fingerprint"])
        logic.remember(c, user, iid, META, body.request_key, meta, meta.model_dump())
        logic.require(fingerprint(preconditions(store, c, user, iid, body, limits)) == fingerprint(value["preflight"]))
        return value


@graph.controlled
def commit(store, user, iid, body, limits):
    from . import lifecycle

    with store.tx() as c:
        i = owned(store, c, user, iid)
        before_private_preflight(store, c, user, i, limits)
        if body.request_key in keys(c, user, iid, COMMIT):
            prior, value = committed(c, user, iid, body.request_key)
            logic.require(fingerprint(prior.model_dump()) == fingerprint(body.model_dump()))
            return public_commit(store, c, user, iid, body.request_key, value, limits)
        if len(keys(c, user, iid, COMMIT)) >= MAX:
            raise DomainError("BUDGET_EXHAUSTED")
        # Metadata index binds the approval to the selected instance before private payload.
        matches = [metadata(c, user, iid, key) for key in keys(c, user, iid, META)]
        m = next((m for m in matches if m["approval_id"] == body.approval_id), None)
        if m is None:
            raise DomainError("VERSION_CONFLICT", "Approval not bound to selected software instance")
        logic.require(m["approval_fingerprint"] == body.expected_approval_fingerprint)
        key = m["prepare_key"]
        if graph.lookup(c, user, iid, CANCEL, key) or graph.lookup(c, user, iid, CANCEL + "_seal", key):
            raise DomainError("VERSION_CONFLICT", "Software preflight cancelled")
        before_private_preflight(store, c, user, i, limits)
        raw = c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id == body.approval_id)).scalar_one()
        request = PrepareInput.model_validate(raw["request"])
        current = preconditions(store, c, user, iid, request, limits)
        a = lifecycle.approval(c, user, body.approval_id, body.expected_approval_fingerprint, PREPARE)
        p, frozen = logic.pair(c, user, iid, PREPARE, key, PrepareInput)
        logic.require(fingerprint(request.model_dump()) == fingerprint(p.model_dump())
            and fingerprint(current) == fingerprint(a["payload"]["continuation"]) == fingerprint(frozen["preflight"])
            and frozen["approval_id"] == body.approval_id and frozen["approval_fingerprint"] == body.expected_approval_fingerprint)
        rid = new_id("irelease")
        snap = snapshot_for(current, iid, i["revision"] + 1, body)
        rel_approval = lifecycle.new_approval(c, user, i["project_id"], "release", {"snapshot": snap, "grant_version": current["grant_version"]})
        release = dict(id=rid, project_id=i["project_id"], principal_id=user, approval_id=rel_approval["id"], snapshot=snap, fingerprint=fingerprint(snap))
        c.execute(insert(internal_releases).values(**release))
        for aid in [body.approval_id, rel_approval["id"]]:
            c.execute(update(internal_approvals).where(internal_approvals.c.id == aid).values(consumed=True))
        permit = permit_for(current, body, key, rid, release["fingerprint"])
        logic.remember(c, user, iid, COMMIT, body.request_key, body, permit)
        row = graph.lookup(c, user, iid, COMMIT, body.request_key)
        index = IndexInput(app_id=i["source_app_id"], instance_id=iid, principal_id=user, project_id=i["project_id"],
            commit_key=body.request_key, release_id=rid, record_fingerprint=row["fingerprint"])
        if len(keys(c, user, i["source_app_id"], INDEX)) >= MAX:
            raise DomainError("BUDGET_EXHAUSTED")
        logic.remember(c, user, i["source_app_id"], INDEX, rid, index, index.model_dump())
        logic.record_release_index(c, user, release)
        history = [*i["history"], dict(kind="software_continuation", revision=i["revision"]+1, release_id=rid,
            previous_release_id=i["release_id"], approval_id=body.approval_id)]
        changed = c.execute(update(internal_instances).where(internal_instances.c.id == iid, internal_instances.c.revision == i["revision"],
            internal_instances.c.release_id == i["release_id"], internal_instances.c.data_version == i["data_version"])
            .values(release_id=rid, revision=i["revision"]+1, history=history)).rowcount
        logic.require(changed == 1)
        updated = c.execute(select(internal_instances).where(internal_instances.c.id == iid)).mappings().one()
        lifecycle.read_release(store, c, user, rid, limits)
        response = public_commit(store, c, user, iid, body.request_key, permit, limits)
        # History reads may report a stale permission; a new commit must fail closed.
        execution(store, c, user, updated, release, limits)
        logic.require(a["expires_at"] > time.time(), "Approval expired during software commit")
        logic.require(current["grant_version"] == lifecycle.grant_version(c, i["project_id"], user))
        logic.require(response["current_permission"])
        return response


def public_commit(store, c, user, iid, key, value, limits):
    i = owned(store, c, user, iid)
    r = c.execute(select(internal_releases).where(internal_releases.c.id == i["release_id"])).mappings().one()
    try:
        execution(store, c, user, i, r, limits)
        current = i["release_id"] == value["release_id"] and i["revision"] == value["revision"]
    except DomainError:
        current = False
    return {**copy.deepcopy(value), "record_fingerprint": graph.lookup(c, user, iid, COMMIT, key)["fingerprint"],
            "current_permission": current, "historical_receipt": True}


@graph.controlled
def recover(store, user, iid, key, limits):
    from . import lifecycle

    with store.tx() as c:
        i = owned(store, c, user, iid)
        for kind in (CANCEL, REVOKE):
            if graph.lookup(c, user, iid, kind, key) or graph.lookup(c, user, iid, kind+"_seal", key):
                _, value = logic.pair(c, user, iid, kind, key, StopInput)
                return {"kind": "STOPPED" if value["stopped"] else "STOP_RECEIPT", "request_key": key, **value}
        before_private_preflight(store, c, user, i, limits)
        if key in keys(c, user, iid, COMMIT):
            _, value = committed(c, user, iid, key)
            # Full current target authorisation before current permit/output details.
            draft = c.execute(select(app_drafts).where(app_drafts.c.id == value["app_id"])).mappings().one()
            logic.verify_candidate(store, c, user, draft, limits, archival_software=value["source_implementation"])
            return {"kind": "COMMITTED", "request_key": key, **public_commit(store, c, user, iid, key, value, limits)}
        if key not in keys(c, user, iid, META):
            raise DomainError("OUTCOME_UNKNOWN", "No receipt for this original software key")
        m = metadata(c, user, iid, key)
        before_private_preflight(store, c, user, i, limits)
        lifecycle.approval(c, user, m["approval_id"], m["approval_fingerprint"], PREPARE)
        _, value = logic.pair(c, user, iid, PREPARE, key, PrepareInput)
        request = PrepareInput.model_validate(c.execute(select(internal_approvals.c.payload).where(
            internal_approvals.c.id == m["approval_id"])).scalar_one()["request"])
        current = preconditions(store, c, user, iid, request, limits)
        logic.require(fingerprint(current) == fingerprint(value["preflight"]))
        return {"kind": "PREPARED", "request_key": key, **value}


@graph.controlled
def stop(store, user, iid, body):
    with store.tx() as c:
        owned(store, c, user, iid)
        kind = CANCEL if body.command == "CANCEL" else REVOKE
        if not body.reason.strip():
            raise DomainError("INVALID_INPUT")
        old = graph.lookup(c, user, iid, kind, body.request_key)
        if old:
            previous, result = logic.pair(c, user, iid, kind, body.request_key, StopInput)
            logic.require(fingerprint(previous.model_dump()) == fingerprint(body.model_dump()))
            return result
        required = 2 if body.command == "CANCEL" and body.request_key != body.target_key else 1
        if len(keys(c, user, iid, kind)) + required > MAX:
            raise DomainError("BUDGET_EXHAUSTED")
        if body.command == "REVOKE":
            rows = [graph.lookup(c, user, iid, k, body.target_key) for k in (COMMIT, COMMIT+"_seal")]
            logic.require(all(rows) and rows[0]["fingerprint"] == rows[1]["fingerprint"] == body.expected_record_fingerprint)
        else:
            # A prepared-key tombstone blocks a late preflight; never labels a commit cancelled.
            for key in keys(c, user, iid, COMMIT):
                _, permit = committed(c, user, iid, key, check_software=False)
                if permit["prepare_key"] == body.target_key:
                    value = {"instance_id": iid, "principal_id": user, "command": "CANCEL", "target_key": body.target_key,
                             "stopped": False, "already_committed": True, "commit_key": key}
                    logic.remember(c, user, iid, kind, body.request_key, body, value)
                    return value
        value = {"instance_id": iid, "principal_id": user, "command": body.command, "target_key": body.target_key, "stopped": True}
        logic.remember(c, user, iid, kind, body.request_key, body, value)
        # CANCEL lookup uses the original prepare key, even if the stop receipt has its own key.
        if body.command == "CANCEL" and body.request_key != body.target_key:
            logic.remember(c, user, iid, CANCEL, body.target_key, body, value)
        return value


@graph.controlled
def options(store, user, pid):
    from .db import task_extractions

    with store.tx() as c:
        store.lock_project(c, user, pid)
        rows = c.execute(select(internal_instances.c.id, internal_instances.c.source_app_id, internal_instances.c.release_id,
            internal_instances.c.revision, internal_instances.c.data_version, app_drafts.c.name, app_drafts.c.fingerprint)
            .join(app_drafts, app_drafts.c.id == internal_instances.c.source_app_id)
            .join(task_extractions, task_extractions.c.app_id == app_drafts.c.id)
            .where(internal_instances.c.project_id == pid, internal_instances.c.principal_id == user,
                task_extractions.c.principal_id == user, task_extractions.c.snapshot["kind"].as_string() == logic.KIND)
            .order_by(internal_instances.c.id).limit(MAX+1)).mappings().all()
        result = []
        for row in rows[:MAX]:
            release_fp = c.execute(select(internal_releases.c.fingerprint).where(internal_releases.c.id == row["release_id"])).scalar_one()
            lid = c.execute(select(task_extractions.c.task_id).where(task_extractions.c.app_id == row["source_app_id"])).scalar_one()
            source_fp = c.execute(select(internal_approvals.c.payload["implementation_fingerprint"].as_string()).where(internal_approvals.c.id == lid)).scalar_one()
            if source_fp == implementation():
                continue
            result.append({**dict(row), "release_fingerprint": release_fp, "source_implementation": source_fp,
                           "target_implementation": implementation(), "requires_explicit_preflight": True})
        return {"version": VERSION, "project_id": pid, "principal_id": user, "items": result, "more": len(rows)>MAX,
                "formal_publication_enabled": False, "model_requests": 0}


def mount(app, store, limits, identity):
    from fastapi import Depends
    from fastapi.responses import JSONResponse

    dep = Depends(identity)
    @app.get("/api/projects/{pid}/software-continuation-options")
    def list_options(pid: str, user=dep):
        return options(store, user, pid)
    @app.post("/api/internal/instances/{iid}/software-continuation-preflights", status_code=201)
    def preview(iid: str, body: PrepareInput, user=dep):
        return prepare(store, user, iid, body, limits)
    @app.post("/api/internal/instances/{iid}/software-continuations", status_code=201)
    def confirm(iid: str, body: CommitInput, user=dep):
        return commit(store, user, iid, body, limits)
    @app.get("/api/internal/instances/{iid}/software-continuations")
    def inspect(iid: str, request_key: str, user=dep):
        return JSONResponse(recover(store, user, iid, request_key, limits), headers={"Cache-Control":"no-store", "Vary":"Authorization"})
    @app.post("/api/internal/instances/{iid}/software-continuation-stops", status_code=201)
    def stop_permission(iid: str, body: StopInput, user=dep):
        return stop(store, user, iid, body)
