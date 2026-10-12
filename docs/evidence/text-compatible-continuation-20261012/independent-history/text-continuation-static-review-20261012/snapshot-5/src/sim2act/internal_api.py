"""Authenticated INTERNAL_ENGINEERING_ONLY adapter; formal deployment stays disabled."""

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select

from . import (
    app_jobs,
    csv_dag,
    csv_dag_instances,
    csv_logic_reuse,
    csv_material_reuse,
    lifecycle,
    text_logic_reuse,
)
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
from .registered_request_recovery import CloseRequestInput, PrepareRequestInput
from .registered_run_extraction import RegisteredExtractionInput


class PrepareInput(Strict):
    expected_draft_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    sample_input: dict
    offline_replay: list[dict] | None = Field(default=None, min_length=2, max_length=2)


class DagPrepareInput(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_plan_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class ApprovalInput(Strict):
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class InstanceInput(Strict):
    expected_release_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)


class AppRunInput(InstanceInput):
    expected_revision: int = Field(ge=1)
    input: dict
    offline_replay: list[dict] | None = Field(default=None, min_length=2, max_length=2)
    expected_owner_goal_binding_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


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

    def supported_app(c, user, aid):
        row = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().first()
        pid = row["project_id"] if row else None
        store.own_project(c, user, pid)
        if isinstance(row["candidate"], dict) and row["candidate"].get("namespace") == "bounded-report-manifest.v1":
            raise DomainError("UNSUPPORTED_CAPABILITY", "Bounded Report manifests support private previews only")
        return pid

    def inspect_job(user, rid):
        if csv_dag.is_job(store, rid):
            return csv_dag_instances.inspect_job(store, user, rid, limits)
        return app_jobs.inspect_job(store, user, rid)

    @app.post("/api/csv-dag/runs/{rid}/release-approvals", status_code=201)
    def dag_release(rid: str, body: DagPrepareInput, user=user_dependency):
        return csv_dag_instances.prepare_release(store, user, rid, body.expected_plan_fingerprint, limits, request_key=body.request_key)

    def scope_run(user, iid, rid, *, historical=False):
        # Stop must remain possible after grant revocation; immutable binding/owner still required.
        with store.tx() as c:
            pid = c.execute(select(runs.c.project_id).where(
                runs.c.id == rid, runs.c.principal_id == user,
            )).scalar_one_or_none()
            if pid is None:
                raise DomainError("PERMISSION_DENIED")
            store.own_project(c, user, pid)
            job = c.execute(select(runs).where(
                runs.c.id == rid, runs.c.principal_id == user, runs.c.project_id == pid,
            )).mappings().first()
            if not job:
                raise DomainError("PERMISSION_DENIED")
            if csv_dag.is_job(store, rid):
                accepted = csv_dag.binding(store, c, job, None, authorize=False, historical=historical)
                value = csv_dag_instances.validate_binding(store, c, job, accepted, None, authorize=False, historical=historical)
                if value is None:
                    raise DomainError("PERMISSION_DENIED")
                snapshot, _ = value
            else:
                snapshot, _ = app_jobs.load_binding(store, c, user, job, None, authorize=False)
            if snapshot["instance_id"] != iid:
                raise DomainError("PERMISSION_DENIED")
            return dict(job)

    @app.post("/api/internal/apps/{aid}/release-approvals", status_code=201)
    def prepare(aid: str, body: PrepareInput, user=user_dependency):
        from .agent_apps import offline_replay_model

        with store.tx() as c:
            supported_app(c, user, aid)
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
            csv_dag_instances.validate_family(c, user, aid, row["payload"]["snapshot"])
            draft = row["payload"]["snapshot"]["draft"]
            store.own_project(c, user, row["project_id"])
            lifecycle.validate_frozen_candidate(store, c, user, draft, limits)
            lifecycle.validate_source_bytes(store, c, user, draft)
            if "execution_source" in row["payload"]["snapshot"]:
                csv_dag_instances.validate_snapshot(store, c, user, row["payload"]["snapshot"], limits)
            return envelope(**dict(row))

    @app.post("/api/internal/approvals/{aid}/commit")
    def commit(aid: str, body: ApprovalInput, user=user_dependency):
        return envelope(**lifecycle.commit_release(store, user, aid, body.fingerprint, limits))

    @app.get("/api/internal/apps/{aid}/releases")
    @app.get("/api/internal/apps/{aid}/dag-releases")
    def releases(aid: str, request: Request, user=user_dependency):
        dag_only = request.url.path.endswith("/dag-releases")
        with store.tx() as c:
            pid = supported_app(c, user, aid)
            # Validate the independent family before choosing a discovery path;
            # damaged markers cannot downgrade into the legacy project scan.
            draft, _, _, _ = lifecycle.load_draft(store, c, user, aid, limits)
            if text_logic_reuse.independent(draft):
                if dag_only:
                    raise DomainError("UNSUPPORTED_CAPABILITY", "Literal releases only")
                ids = text_logic_reuse.release_ids(store, c, user, draft, limits)
                return envelope(items=[dict(lifecycle.read_release(store, c, user, rid, limits)) for rid in ids])
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
                and ("execution_source" in row["snapshot"]) == dag_only
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

    @app.get("/api/internal/releases/{rid}/csv-materials")
    def material_options(rid: str, user=user_dependency):
        return csv_material_reuse.options(store, user, rid, limits)

    @app.post("/api/internal/releases/{rid}/csv-logic-authorizations", status_code=201)
    def authorize_logic(rid: str, body: csv_logic_reuse.AuthorizeInput, user=user_dependency):
        return csv_logic_reuse.authorize(store, user, rid, body, limits)

    @app.get("/api/projects/{pid}/csv-logics")
    def logic_history(pid: str, user=user_dependency):
        return csv_logic_reuse.history(store, user, pid, limits)

    @app.get("/api/internal/csv-logics/{lid}")
    def logic_read(lid: str, user=user_dependency):
        return csv_logic_reuse.inspect(store, user, lid, limits)

    @app.post("/api/internal/csv-logics/{lid}/revoke")
    def logic_revoke(lid: str, body: csv_logic_reuse.RevokeInput, user=user_dependency):
        return csv_logic_reuse.revoke(store, user, lid, body, limits)

    @app.get("/api/internal/csv-logics/{lid}/materials")
    def logic_materials(lid: str, user=user_dependency):
        return csv_logic_reuse.options(store, user, lid, limits)

    @app.post("/api/internal/csv-logics/{lid}/material-plans", status_code=201)
    def logic_plan(lid: str, body: csv_logic_reuse.MaterialInput, user=user_dependency):
        return csv_logic_reuse.propose(store, user, lid, body, limits)

    @app.get("/api/internal/csv-logics/{lid}/material-plans/{aid}/{key}")
    def logic_plan_read(lid: str, aid: str, key: str, user=user_dependency):
        return csv_logic_reuse.inspect_plan(store, user, lid, aid, key, limits)

    @app.post("/api/internal/releases/{rid}/csv-material-plans", status_code=201)
    def material_plan(rid: str, body: csv_material_reuse.MaterialInput, user=user_dependency):
        return csv_material_reuse.propose(store, user, rid, body, limits)

    @app.get("/api/internal/releases/{rid}/csv-material-plans/{aid}/{key}")
    def material_read(rid: str, aid: str, key: str, user=user_dependency):
        return csv_material_reuse.inspect(store, user, rid, aid, key, limits)

    @app.get("/api/internal/apps/{aid}/instances")
    @app.get("/api/internal/apps/{aid}/dag-instances")
    def instances(aid: str, request: Request, user=user_dependency):
        dag_only = request.url.path.endswith("/dag-instances")
        with store.tx() as c:
            pid = supported_app(c, user, aid)
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
            items = []
            for iid in ids:
                value, rel = lifecycle.instance(store, c, user, iid, limits)
                if ("execution_source" in rel["snapshot"]) == dag_only:
                    items.append({**dict(value), "namespace": lifecycle.NAMESPACE,
                        **({} if dag_only else {"data": [dict(x) for x in lifecycle.data_rows(c, iid)]})})
        return envelope(items=items)

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
            runs=[inspect_job(user, rid) for rid in ids],
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
                owner_goal_fp=body.expected_owner_goal_binding_fingerprint,
            )
        )

    @app.get("/api/internal/instances/{iid}/runs/{rid}")
    def inspect_run(iid: str, rid: str, user=user_dependency):
        scope_run(user, iid, rid, historical=True)
        return envelope(**inspect_job(user, rid))

    def text_logic_response(value):
        return JSONResponse(envelope(**value), headers={"Cache-Control": "no-store", "Vary": "Authorization"})

    @app.get("/api/internal/instances/{iid}/runs/{rid}/text-logic-options")
    def text_logic_options(iid: str, rid: str, user=user_dependency):
        return text_logic_response(text_logic_reuse.source_options(store, user, iid, rid, limits))

    @app.post("/api/internal/instances/{iid}/runs/{rid}/text-logic-authorizations", status_code=201)
    def text_logic_authorize(iid: str, rid: str, body: text_logic_reuse.AuthorizeInput, user=user_dependency):
        return envelope(**text_logic_reuse.authorize(store, user, iid, rid, body, limits))

    @app.get("/api/internal/instances/{iid}/runs/{rid}/text-logic-receipts")
    def text_logic_authorization_receipt(iid: str, rid: str, request_key: str, user=user_dependency):
        return text_logic_response(text_logic_reuse.recover_authorization(store, user, iid, rid, request_key, limits))

    @app.get("/api/projects/{pid}/text-logics")
    def text_logic_history(pid: str, user=user_dependency):
        return text_logic_response(text_logic_reuse.history(store, user, pid, limits))

    @app.get("/api/internal/text-logics/{lid}")
    def text_logic_inspect(lid: str, user=user_dependency):
        return text_logic_response(text_logic_reuse.inspect(store, user, lid, limits))

    @app.post("/api/internal/text-logics/{lid}/revoke")
    def text_logic_revoke(lid: str, body: text_logic_reuse.RevokeInput, user=user_dependency):
        return envelope(**text_logic_reuse.revoke(store, user, lid, body, limits))

    @app.get("/api/internal/text-logics/{lid}/materials")
    def text_logic_materials(lid: str, user=user_dependency):
        return text_logic_response(text_logic_reuse.options(store, user, lid, limits))

    @app.post("/api/internal/text-logics/{lid}/bindings", status_code=201)
    def text_logic_bind(lid: str, body: text_logic_reuse.BindInput, user=user_dependency):
        return envelope(**text_logic_reuse.bind(store, user, lid, body, limits))

    @app.get("/api/internal/text-logics/{lid}/bindings")
    def text_logic_receipt(lid: str, request_key: str, user=user_dependency):
        return text_logic_response(text_logic_reuse.recover_binding(store, user, lid, request_key, limits))

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

    @app.get("/api/internal/instances/{iid}/runs/{rid}/extraction-receipts")
    def extraction_receipt(iid: str, rid: str, request_key: str,
                           require_latest: bool = False, user=user_dependency):
        from .registered_run_extraction import recover

        scope_run(user, iid, rid)
        return JSONResponse(envelope(**recover(store, user, iid, rid, request_key, limits,
                                              require_latest=require_latest)),
                            headers={"Cache-Control": "no-store", "Vary": "Authorization"})

    @app.get("/api/internal/instances/{iid}/runs/{rid}/extraction-requests")
    def extraction_requests(iid: str, rid: str, request_key: str | None = None, user=user_dependency):
        from .registered_request_recovery import index, read

        return JSONResponse(envelope(**(index(store, user, iid, rid, limits) if request_key is None
                           else read(store, user, iid, rid, request_key, limits))),
                            headers={"Cache-Control": "no-store", "Vary": "Authorization"})

    @app.get("/api/projects/{pid}/registered-text-requests")
    def project_extraction_requests(pid: str, user=user_dependency):
        from .registered_request_recovery import project_index

        return JSONResponse(envelope(**project_index(store, user, pid)),
                            headers={"Cache-Control": "no-store", "Vary": "Authorization"})

    @app.post("/api/internal/instances/{iid}/runs/{rid}/extraction-requests", status_code=201)
    def prepare_extraction_request(iid: str, rid: str,
                                   body: PrepareRequestInput, user=user_dependency):
        from .registered_request_recovery import prepare

        return envelope(**prepare(store, user, iid, rid, body, limits))

    @app.post("/api/internal/instances/{iid}/runs/{rid}/extraction-request-close")
    def close_extraction_request(iid: str, rid: str,
                                 body: CloseRequestInput, user=user_dependency):
        from .registered_request_recovery import close

        return envelope(**close(store, user, iid, rid, body))

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
        status = (csv_dag.command_job if csv_dag.is_job(store, rid) else app_jobs.command_job)(store, user, rid, body.command, body.version)
        return envelope(status=status)
