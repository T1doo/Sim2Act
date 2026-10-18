"""Exact-Run human declarations for the existing closed four-step text adapter.

This adapter reuses the sealed per-Run owner journal. It grants no execution or
publication authority and never treats a source resource as a saved artifact.
"""

import time
from typing import Annotated

from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select

from . import lifecycle
from . import owner_acceptance as owner
from . import text_logic_reuse as seals
from . import text_workflows as flow
from .db import (
    fingerprint,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    runs,
)
from .errors import DomainError

VERSION = "owner.text-four-step.v1"
REJECTION = "text-workflow-owner-submission-rejection.v1"


def scope(store, c, user, iid, rid):
    """Owned identifiers and independent family seals, even after source revoke.

    This gate also precedes idempotent original-key returns and metadata stops.
    No Run, result, source, Goal or owner payload is selected here.
    """
    pid = owner.natural_scope(store, c, user, iid, rid)
    row = c.execute(select(
        internal_app_runs.c.id.label("aid"), internal_app_runs.c.release_id,
        internal_instances.c.source_app_id, internal_instances.c.runtime_id,
        internal_releases.c.snapshot["draft"]["candidate"]["namespace"].as_string().label("family"),
        runs.c.runtime_id.label("job_runtime"), runs.c.request_key,
    ).select_from(internal_app_runs)
        .join(internal_run_bindings, internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
        .join(internal_instances, internal_instances.c.id == internal_app_runs.c.instance_id)
        .join(internal_releases, internal_releases.c.id == internal_app_runs.c.release_id)
        .join(runs, runs.c.id == internal_run_bindings.c.run_id)
        .where(internal_run_bindings.c.run_id == rid, internal_app_runs.c.instance_id == iid,
            internal_app_runs.c.principal_id == user, runs.c.principal_id == user,
            runs.c.project_id == pid, internal_releases.c.principal_id == user,
            internal_releases.c.project_id == pid)).mappings().first()
    flow.require(row is not None and row["family"] == flow.VERSION,
        "This Run is not a closed four-step text execution")
    meta, value = seals.pair(c, user, rid, flow.RUN_META, "accepted", flow.RunScopeInput)
    flow.require(fingerprint(meta.model_dump()) == fingerprint(value)
        and meta.principal_id == user and meta.project_id == pid and meta.run_id == rid
        and meta.instance_id == iid and meta.app_run_id == row["aid"]
        and meta.app_id == row["source_app_id"] and meta.release_id == row["release_id"]
        and meta.runtime_id == row["runtime_id"] == row["job_runtime"]
        and row["request_key"] == "internal:" + row["aid"], "Four-step review scope changed")
    return pid


def ledger(c, user, pid, iid, rid):
    rows = owner.natural_ledger(c, user, iid, rid)
    flow.require(all(r["project_id"] == pid for r in rows), "Review project changed")
    return rows


def context(store, c, user, iid, rid, limits):
    pid = scope(store, c, user, iid, rid)
    # The existing independent resource gate precedes every protected body.
    flow.job_scope_gate(store, c, user, rid)
    job = c.execute(select(runs).where(runs.c.id == rid, runs.c.principal_id == user,
        runs.c.project_id == pid)).mappings().one()
    binding, outputs, proved = flow.verify_job(store, c, user, job, limits, require_success=True)
    snapshot, app_run, release = binding["snapshot"], binding["app_run"], binding["release"]
    instance = c.execute(select(internal_instances).where(internal_instances.c.id == iid,
        internal_instances.c.principal_id == user, internal_instances.c.project_id == pid)).mappings().one()
    flow.require(snapshot["instance_id"] == iid and app_run["instance_id"] == iid
        and instance["revision"] == snapshot["expected_revision"]
        and instance["release_id"] == release["id"] and instance["data_version"] == app_run["result_version"],
        "Selected report is no longer the current instance result")
    flow.require(c.execute(select(internal_app_runs.c.id).where(internal_app_runs.c.instance_id == iid,
        internal_app_runs.c.status.not_in(["SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED"]))).first() is None,
        "A new instance Run is still in progress")
    typed = c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == iid,
        internal_instance_data.c.run_id == app_run["id"])).mappings().one()
    goal = binding["goal"]
    content = goal["snapshot"]["content"]
    items = [dict(id="title", text=content["title"]), dict(id="goal", text=content["goal"])]
    for field in ("known", "assumptions", "unresolved", "constraints", "acceptance_checks"):
        items.extend(dict(id=f"{field}.{n}", text=text) for n, text in enumerate(content[field], 1))
    items.extend([
        dict(id="source-and-report", text="逐一核对两次检索词、各自原文行号和完整引用报告；字面与来源核对不证明目标语义正确。"),
        dict(id="technical-boundary", text="本声明仅针对当前四步文本 Run 及 Goal；不继承旧签收，不批准发布，不改变执行权限。"),
    ])
    return dict(version=VERSION, principal_id=user, project_id=pid, instance_id=iid,
        app_id=binding["draft"]["id"], runtime_id=job["runtime_id"], run_id=rid,
        app_run_id=app_run["id"], instance_revision=instance["revision"],
        data_version=instance["data_version"], result_version=app_run["result_version"],
        release_id=release["id"], release_fingerprint=release["fingerprint"],
        draft_fingerprint=binding["draft"]["fingerprint"], source_goal=goal, goal=content, items=items,
        material=binding["source"], input=snapshot["input"], output=outputs["report"],
        output_fingerprint=fingerprint(outputs["report"]), typed_fingerprint=typed["fingerprint"],
        binding_fingerprint=fingerprint(snapshot), actual_operations=proved,
        grant_version=lifecycle.grant_version(c, pid, user), current_limits=limits.model_dump(),
        declaration_scope="EXACT_FOUR_STEP_GOAL_RELEASE_INSTANCE_RUN_REPORT",
        technical_semantic_status="UNKNOWN", automatic_goal_acceptance="NOT_RUN",
        model_requests=0, formal_publication_enabled=False)


def final_gate(store, c, user, iid, rid, limits, fresh, *, expires_at=None):
    # Same locked transaction; repeat the actual proof and dynamic authority.
    flow.require(fingerprint(context(store, c, user, iid, rid, limits)) == fingerprint(fresh),
        "Four-step human review changed before commit")
    flow.require(expires_at is None or time.time() < expires_at, "Human preview expired before commit")


def submit(store, user, iid, rid, limits, body):
    return owner.scoped_run_submit(store, user, rid, body, dict(
        namespace=REJECTION, scope_metadata={"instance_id": iid},
        scope=lambda c: scope(store, c, user, iid, rid),
        ledger=lambda c: ledger(c, user, scope(store, c, user, iid, rid), iid, rid),
        payload=owner.natural_payload,
        context=lambda c: context(store, c, user, iid, rid, limits),
        append=lambda c, pid, rows, request, status, **kw: owner.natural_append(
            c, user, pid, iid, rid, rows, request, status, **kw),
        final_gate=lambda c, fresh, **kw: final_gate(store, c, user, iid, rid, limits, fresh, **kw)))


def read(store, user, iid, rid, limits, key=None):
    with store.tx() as c:
        pid = scope(store, c, user, iid, rid)
        rows = ledger(c, user, pid, iid, rid)
        app_id = c.execute(select(internal_instances.c.source_app_id)
            .where(internal_instances.c.id == iid)).scalar_one()
        last = rows[-1] if rows else None
        out = dict(version=VERSION, principal_id=user, project_id=pid, instance_id=iid,
            app_id=app_id, run_id=rid, sequence=len(rows), history=rows, latest=last,
            owner_acceptance=last["status"] if last else "PENDING", content_access=False,
            technical_semantic_status="UNKNOWN", formal_publication_enabled=False)
        recovered = next((r for r in rows if r["request_key"] == key), None) if key else None
        if key and not recovered:
            raise DomainError("OUTCOME_UNKNOWN", "Original four-step declaration key not found")
        try:
            fresh = context(store, c, user, iid, rid, limits)
            # Resolve current authority, Goal, version, and result before owner bodies.
            values = {r["id"]: owner.natural_payload(c, r) for r in rows}
            if last and last["kind"] in {"PREPARE", "DECIDE"}:
                value = values[last["id"]]
                flow.require(fingerprint(fresh) == fingerprint(value["contract"]), "Exact review context changed")
                out["record"] = dict(last, payload=value)
                if last["kind"] == "PREPARE" and time.time() >= value["expires_at"]:
                    out["owner_acceptance"] = "EXPIRED"
            out.update(content_access=True, current=fresh)
            if recovered and fingerprint(values[recovered["id"]].get("contract", fresh)) == fingerprint(fresh):
                recovered = dict(recovered, payload=values[recovered["id"]])
        except DomainError as error:
            out.pop("record", None)
            out["invalidation_reason"] = error.code
            if last and last["kind"] not in {"CANCEL", "REVOKE"}:
                out["owner_acceptance"] = "STALE"
        if recovered:
            out["recovered"] = recovered
        return out


def mount(app, store, limits, identity):
    user_dependency = Depends(identity)

    @app.get("/api/internal/instances/{iid}/runs/{rid}/text-owner-review")
    def get_review(iid: str, rid: str, request_key: str | None = None, user=user_dependency):
        try:
            return read(store, user, iid, rid, limits, request_key)
        except DomainError as error:
            if error.code != "OUTCOME_UNKNOWN":
                raise
            return JSONResponse({"error": error.public()}, status_code=409)

    @app.post("/api/internal/instances/{iid}/runs/{rid}/text-owner-review-requests", status_code=201)
    def post_review(iid: str, rid: str,
        body: Annotated[owner.NaturalPrepare | owner.Decide | owner.Stop, Field(discriminator="command")],
        user=user_dependency):
        return dict(formal_publication_enabled=False,
            record=submit(store, user, iid, rid, limits, body.model_dump()))
