"""Authenticated INTERNAL_ENGINEERING_ONLY adapter; formal deployment stays disabled."""

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import app_jobs, lifecycle
from .contracts import Strict
from .db import (
    app_drafts,
    internal_app_runs,
    internal_approvals,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    runs,
)
from .errors import DomainError


class PrepareInput(Strict):
    expected_draft_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    sample_input: dict
    offline_replay: list[dict] | None = Field(default=None, min_length=2, max_length=2)


class RegisteredExtractionInput(Strict):
    expected_proof_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    target_app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    expected_target_draft_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    name: str = Field(min_length=1, max_length=200)
    request_key: str = Field(min_length=1, max_length=100)


class ApprovalInput(Strict):
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class InstanceInput(Strict):
    expected_release_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)


class AppRunInput(InstanceInput):
    expected_revision: int = Field(ge=1)
    input: dict
    offline_replay: list[dict] | None = Field(default=None, min_length=2, max_length=2)


class SwitchInput(Strict):
    target_release_id: str = Field(min_length=1, max_length=100)
    expected_target_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=1)


class ControlInput(Strict):
    command: str = Field(pattern=r"^(pause|cancel|resume)$")
    version: int = Field(ge=1)


def envelope(**values):
    return {"namespace": lifecycle.NAMESPACE, "formal_publication_enabled": False, **values}


def mount(app, store, limits, identity):
    user_dependency = Depends(identity)

    def scope_run(user, iid, rid):
        # Stop must remain possible after grant revocation; immutable binding/owner still required.
        with store.tx() as c:
            job = c.execute(select(runs).where(runs.c.id == rid)).mappings().first()
            if not job:
                raise DomainError("PERMISSION_DENIED")
            snapshot, _ = app_jobs.load_binding(store, c, user, job, None, authorize=False)
            if snapshot["instance_id"] != iid:
                raise DomainError("PERMISSION_DENIED")
            return dict(job)

    @app.post("/api/internal/apps/{aid}/release-approvals", status_code=201)
    def prepare(aid: str, body: PrepareInput, user=user_dependency):
        from .agent_apps import offline_replay_model

        return lifecycle.prepare_release(
            store, user, aid, body.expected_draft_fingerprint, limits, body.sample_input,
            replay=offline_replay_model(body.offline_replay) if body.offline_replay is not None else None,
        )

    @app.get("/api/internal/approvals/{aid}")
    def inspect_approval(aid: str, user=user_dependency):
        with store.tx() as c:
            row = (
                c.execute(select(internal_approvals).where(internal_approvals.c.id == aid))
                .mappings()
                .first()
            )
            if not row or row["principal_id"] != user or row["kind"] != "release":
                raise DomainError("PERMISSION_DENIED")
            lifecycle.approval(c, user, aid, row["fingerprint"], "release", allow_consumed=True)
            draft = row["payload"]["snapshot"]["draft"]
            store.own_project(c, user, row["project_id"])
            lifecycle.validate_frozen_candidate(store, c, user, draft, limits)
            lifecycle.validate_source_bytes(store, c, user, draft)
            return envelope(**dict(row))

    @app.post("/api/internal/approvals/{aid}/commit")
    def commit(aid: str, body: ApprovalInput, user=user_dependency):
        return envelope(**lifecycle.commit_release(store, user, aid, body.fingerprint, limits))

    @app.get("/api/internal/apps/{aid}/releases")
    def releases(aid: str, user=user_dependency):
        with store.tx() as c:
            pid = c.execute(select(app_drafts.c.project_id).where(app_drafts.c.id == aid)).scalar()
            store.own_project(c, user, pid)
            ids = (
                c.execute(
                    select(internal_releases.c.id, internal_releases.c.snapshot)
                    .where(
                        internal_releases.c.project_id == pid,
                        internal_releases.c.principal_id == user,
                    )
                    .order_by(internal_releases.c.id)
                )
                .mappings()
                .all()
            )
            items = [
                dict(lifecycle.read_release(store, c, user, row["id"], limits))
                for row in ids
                if row["snapshot"].get("draft", {}).get("id") == aid
            ]
            return envelope(items=items)

    @app.get("/api/internal/releases/{rid}")
    def release(rid: str, user=user_dependency):
        with store.tx() as c:
            return envelope(**dict(lifecycle.read_release(store, c, user, rid, limits)))

    @app.post("/api/internal/releases/{rid}/instances", status_code=201)
    def create(rid: str, body: InstanceInput, user=user_dependency):
        return envelope(
            **lifecycle.create_instance(
                store,
                user,
                rid,
                body.expected_release_fingerprint,
                limits,
                request_key=body.request_key,
            )
        )

    @app.get("/api/internal/apps/{aid}/instances")
    def instances(aid: str, user=user_dependency):
        with store.tx() as c:
            pid = c.execute(select(app_drafts.c.project_id).where(app_drafts.c.id == aid)).scalar()
            store.own_project(c, user, pid)
            ids = (
                c.execute(
                    select(internal_instances.c.id)
                    .where(
                        internal_instances.c.source_app_id == aid,
                        internal_instances.c.principal_id == user,
                        internal_instances.c.project_id == pid,
                    )
                    .order_by(internal_instances.c.id)
                )
                .scalars()
                .all()
            )
        return envelope(items=[lifecycle.inspect_instance(store, user, iid, limits) for iid in ids])

    @app.get("/api/internal/instances/{iid}")
    def inspect(iid: str, user=user_dependency):
        value = lifecycle.inspect_instance(store, user, iid, limits)
        with store.tx() as c:
            release = lifecycle.read_release(store, c, user, value["release_id"], limits)
            ids = (
                c.execute(
                    select(internal_run_bindings.c.run_id)
                    .join(
                        internal_app_runs,
                        internal_app_runs.c.id == internal_run_bindings.c.app_run_id,
                    )
                    .where(
                        internal_app_runs.c.instance_id == iid,
                        internal_app_runs.c.principal_id == user,
                    )
                    .order_by(internal_run_bindings.c.run_id)
                )
                .scalars()
                .all()
            )
        return envelope(
            **value,
            release_fingerprint=release["fingerprint"],
            runs=[app_jobs.inspect_job(store, user, rid) for rid in ids],
        )

    @app.post("/api/internal/instances/{iid}/switch-approvals", status_code=201)
    def prepare_switch(iid: str, body: SwitchInput, user=user_dependency):
        return lifecycle.prepare_switch(
            store,
            user,
            iid,
            body.target_release_id,
            body.expected_revision,
            limits,
            expected_target_fingerprint=body.expected_target_fingerprint,
        )

    @app.get("/api/internal/instances/{iid}/switch-approvals/{aid}")
    def inspect_switch(iid: str, aid: str, user=user_dependency):
        return envelope(**lifecycle.inspect_switch_approval(store, user, iid, aid, limits))

    @app.post("/api/internal/instances/{iid}/switch-approvals/{aid}/commit")
    def switch(iid: str, aid: str, body: ApprovalInput, user=user_dependency):
        lifecycle.inspect_switch_approval(store, user, iid, aid, limits)
        return envelope(**lifecycle.commit_switch(store, user, aid, body.fingerprint, limits))

    @app.post("/api/internal/instances/{iid}/runs", status_code=202)
    def enqueue(iid: str, body: AppRunInput, user=user_dependency):
        return envelope(
            **app_jobs.enqueue(
                store,
                user,
                iid,
                body.expected_revision,
                body.expected_release_fingerprint,
                body.input,
                body.request_key,
                limits,
                offline_replay=body.offline_replay,
                require_offline_replay=True,
            )
        )

    @app.get("/api/internal/instances/{iid}/runs/{rid}")
    def inspect_run(iid: str, rid: str, user=user_dependency):
        scope_run(user, iid, rid)
        return envelope(**app_jobs.inspect_job(store, user, rid))

    @app.get("/api/internal/instances/{iid}/runs/{rid}/extraction-options")
    def extraction_options(iid: str, rid: str, user=user_dependency):
        from .registered_run_extraction import options

        scope_run(user, iid, rid)
        return envelope(**options(store, user, iid, rid, limits))

    @app.post("/api/internal/instances/{iid}/runs/{rid}/extract", status_code=201)
    def extract_run(iid: str, rid: str, body: RegisteredExtractionInput, user=user_dependency):
        from .registered_run_extraction import extract

        scope_run(user, iid, rid)
        return envelope(
            **extract(
                store,
                user,
                iid,
                rid,
                body.expected_proof_fingerprint,
                body.target_app_id,
                body.expected_target_draft_fingerprint,
                body.name,
                body.request_key,
                limits,
            )
        )

    @app.get("/api/internal/instances/{iid}/runs/{rid}/control-status")
    def control_status(iid: str, rid: str, user=user_dependency):
        job = scope_run(user, iid, rid)
        # Only owner control metadata, never protected inputs/results/events or resource bytes.
        return envelope(
            id=rid,
            instance_id=iid,
            status=job["status"],
            version=job["version"],
            cancel_intent=job["cancel_intent"],
            content_access=False,
        )

    @app.post("/api/internal/instances/{iid}/runs/{rid}/commands")
    def command(iid: str, rid: str, body: ControlInput, user=user_dependency):
        scope_run(user, iid, rid)
        status = app_jobs.command_job(store, user, rid, body.command, body.version)
        return envelope(status=status)
