import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import Field
from sqlalchemy import select, update

from .apps import create_csv_draft, inspect_draft, preview
from .conditional_apps import NAMESPACE as CONDITIONAL_APP_NAMESPACE
from .conditional_apps import mount as mount_conditional_apps
from .conditional_checks import mount as mount_conditional_checks
from .conditional_runs import mount as mount_conditional_runs
from .config import Settings
from .contracts import (
    Limits,
    Strict,
    resource_id,
    strict_json,
    validate_action,
    validate_action_input,
)
from .db import (
    Store,
    app_drafts,
    fingerprint,
    grants,
    heartbeats,
    projects,
    resources,
    run_contracts,
    runs,
)
from .delivery_graph_apps import mount as mount_delivery_graph_apps
from .errors import DomainError
from .extraction import ExtractionInput, extract_preview
from .goal_planner import ConfirmNaturalPlanInput
from .goals import GoalCardInput, GoalCardUpdate, create_card, inspect_card, list_cards, revise_card
from .internal_api import RegisteredExtractionInput
from .internal_api import mount as mount_internal_api
from .local_tasks import (
    LocalTaskInput,
    RetirementInput,
    TaskExtractionInput,
    complete_csv_task,
    extract_task,
    inspect_task,
    retire_task_source,
    retirement_row,
)
from .planning import GoalCandidateInput, candidate_options, generate_candidate
from .preflight import preflight
from .protocol_api import mount as mount_protocol_api
from .protocol_recovery import mount as mount_protocol_recovery
from .protocol_reviews import mount as mount_protocol_reviews
from .report_manifest_apps import NAMESPACE as REPORT_MANIFEST_NAMESPACE
from .report_manifest_apps import mount as mount_report_manifest_apps
from .spec_checklists import SpecChecklistInput, complete_checklist, inspect_checklist


class ExpireNaturalActivationInput(Strict):
    pass


class ProjectInput(Strict):
    name: str = Field(min_length=1, max_length=200)


def _csv_instance_candidate(candidate):
    """Directory routing only; selected instances still require authoritative inspect."""
    if not isinstance(candidate, dict):
        return None
    manifest, actions = candidate.get("manifest"), candidate.get("actions")
    if not isinstance(manifest, dict) or not isinstance(actions, list) or len(actions) != 1:
        return None
    action = actions[0]
    executor = action.get("executor") if isinstance(action, dict) else None
    if not isinstance(executor, dict):
        return None
    if (
        manifest.get("validation_suite_ref") == "receipt.readback.v1"
        and executor.get("kind") == "registered_tool"
        and executor.get("ref") == "data.aggregate_csv"
    ):
        return True
    if (
        candidate.get("namespace") == REPORT_MANIFEST_NAMESPACE
        and manifest.get("validation_suite_ref") == "source.conditional_report.v1"
        and executor.get("kind") == "bounded_report"
        and executor.get("ref") == "intern.conditional_report"
    ):
        return False
    return None


class ResourceInput(Strict):
    name: str = Field(min_length=1, max_length=200)
    format: str
    content: str = Field(max_length=32768)


class RunInput(Strict):
    goal: str = Field(min_length=1, max_length=4000)
    resource_refs: list[str] = Field(max_length=8)
    request_key: str = Field(min_length=1, max_length=100)


class CommandInput(Strict):
    command: str
    version: int = Field(ge=1)


class ReconcileInput(Strict):
    attempt_id: str = Field(pattern=r"^attempt_[a-f0-9]{32}$")
    version: int = Field(ge=1)
    decision: str
    expected_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    evidence: str = Field(min_length=1, max_length=1000)
    acknowledge_unknown_cost: bool
    response: dict | None = None
    response_json: str | None = Field(default=None, max_length=32768)


class ContractInput(Strict):
    action: dict
    input: dict | None = None


class PreflightInput(Strict):
    manifest: dict
    actions: list[dict] = Field(max_length=16)


class OperationReconcileInput(Strict):
    operation_id: str = Field(pattern=r"^op_[a-f0-9]{32}$")
    version: int = Field(ge=1)
    expected_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence: str = Field(min_length=1, max_length=1000)


class CsvDraftInput(Strict):
    name: str = Field(min_length=1, max_length=200)
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    goal: str = Field(min_length=1, max_length=4000)


class PreviewInput(Strict):
    input: dict
    request_key: str = Field(min_length=1, max_length=100)


def create_app(store=None, settings=None):
    s = settings or Settings.from_env()
    db = store or Store(s.database_url)
    platform_limits = Limits(**{key: getattr(s, key) for key in Limits.model_fields})
    app = FastAPI(title="Sim2Act F1", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def security(request: Request, call_next):
        # No cross-origin auth; strict duplicate-key parsing also applies to HTTP input.
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"error": {"code": "PERMISSION_DENIED"}}, status_code=403)
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                strict_json(await request.body())
            except DomainError as e:
                return JSONResponse({"error": e.public()}, status_code=400)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        code = (
            403
            if exc.code in {"PERMISSION_DENIED", "GRANT_REVOKED"}
            else 409
            if exc.code == "VERSION_CONFLICT"
            else 400
        )
        return JSONResponse({"error": exc.public()}, status_code=code)

    def identity(authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise DomainError("PERMISSION_DENIED")
        return db.authenticate(authorization[7:])

    user_dependency = Depends(identity)

    @app.get("/health")
    def health():
        # Public local health returns neither IDs nor connection strings.
        with db.engine.connect() as c:
            c.execute(select(1))
            beat = c.execute(
                select(heartbeats.c.at).order_by(heartbeats.c.at.desc()).limit(1)
            ).scalar()
        return {
            "api": "UP",
            "database": "UP",
            "worker": "UP" if beat and time.time() - beat < 40 else "OFFLINE",
            "mode": s.mode.upper(),
            "live_acceptance": "BLOCKED",
        }

    @app.get("/api/projects")
    def list_projects(user=user_dependency):
        with db.engine.connect() as c:
            return [
                dict(x)
                for x in c.execute(
                    select(projects.c.id, projects.c.name).where(projects.c.owner_id == user)
                ).mappings()
            ]

    @app.post("/api/projects", status_code=201)
    def create_project(body: ProjectInput, user=user_dependency):
        pid = db.project(user, body.name)
        with db.tx() as c:
            p = db.own_project(c, user, pid)
            # Project creation authorizes only own local artifact writes, never external action.
            db.add_grants(c, user, p["runtime_id"], pid, pid, ["artifact.save_text"])
        return {"id": pid}

    @app.get("/api/projects/{pid}/resources")
    def list_resources(pid: str, user=user_dependency):
        with db.tx() as c:
            p = db.own_project(c, user, pid)
            rows = (
                c.execute(
                    select(
                        resources.c.id, resources.c.name, resources.c.format, resources.c.hash
                    ).where(resources.c.project_id == pid)
                )
                .mappings()
                .all()
            )
            output = []
            for r in rows:
                try:
                    db.authorize(c, user, p["runtime_id"], pid, r["id"], "resource.read")
                    output.append(dict(r))
                except DomainError:
                    pass
            return output

    @app.post("/api/projects/{pid}/resources", status_code=201)
    def create_resource(pid: str, body: ResourceInput, user=user_dependency):
        return {"id": db.resource(user, pid, body.name, body.format, body.content)}

    @app.get("/api/resources/{rid}")
    def get_resource(rid: str, user=user_dependency):
        resource_id(rid)
        with db.tx() as c:
            r = c.execute(select(resources).where(resources.c.id == rid)).mappings().first()
            if not r:
                raise DomainError("PERMISSION_DENIED")
            p = db.own_project(c, user, r["project_id"])
            db.authorize(c, user, p["runtime_id"], p["id"], rid, "resource.read")
            if retirement_row(c, rid):
                raise DomainError("RESOURCE_UNAVAILABLE", "来源已显式退休，旧内容不可读取")
            return dict(r)

    @app.get("/api/projects/{pid}/runs")
    def list_runs(pid: str, user=user_dependency):
        with db.tx() as c:
            db.own_project(c, user, pid)
            items = []
            for r in c.execute(
                select(runs.c.id, runs.c.status, runs.c.created_at, runs.c.goal,
                       runs.c.request_key, run_contracts.c.snapshot)
                .outerjoin(run_contracts, run_contracts.c.run_id == runs.c.id)
                .where(runs.c.project_id == pid, runs.c.principal_id == user)
                .order_by(runs.c.created_at.desc(), runs.c.id.desc())
            ).mappings():
                goal = " ".join((r["goal"] or "").split())
                snapshot = r["snapshot"] or {}
                mode = snapshot.get("mode")
                # Protocol providers have their own bound scope; the ordinary
                # frozen contract's placeholder must not label them as MOCK.
                if (r["request_key"] or "").startswith("protocol:"):
                    mode = None
                items.append({
                    "id": r["id"], "status": r["status"], "created_at": r["created_at"],
                    "goal_summary": goal[:160] + ("…" if len(goal) > 160 else ""),
                    "mode": mode.upper() if isinstance(mode, str) and mode in {"mock", "live"} else "UNKNOWN",
                })
            return items

    @app.post("/api/projects/{pid}/runs", status_code=202)
    def create_run(pid: str, body: RunInput, user=user_dependency):
        for rid in body.resource_refs:
            resource_id(rid)
        return {
            "run_id": db.submit(
                user,
                pid,
                body.goal,
                body.resource_refs,
                body.request_key,
                policy={
                    "limits": platform_limits.model_dump(),
                    "mode": s.mode,
                    "request_model": s.model,
                },
            ),
            "mode": s.mode.upper(),
        }

    @app.get("/api/runs/{rid}")
    def inspect_run(rid: str, response: Response, user=user_dependency):
        result = db.inspect(user, rid)
        if result.get("natural_deadline") is not None:
            if result["contract"]["snapshot"]["natural_planning"].get("activation") is not None:
                from .natural_activations import now
                server_time = now()
            else:
                server_time = time.time()
            response.headers["X-Sim2Act-Server-Time"] = str(server_time)
        return result

    @app.post("/api/runs/{rid}/commands")
    def command(rid: str, body: CommandInput, user=user_dependency):
        return {"status": db.command(user, rid, body.command, body.version)}

    @app.get("/api/runs/{rid}/unresolved-attempts")
    def unresolved(rid: str, user=user_dependency):
        return db.unresolved_attempts(user, rid)

    @app.post("/api/runs/{rid}/reconcile")
    def reconcile(rid: str, body: ReconcileInput, user=user_dependency):
        values = body.model_dump()
        raw = values.pop("response_json")
        if raw is not None:
            if values["response"] is not None:
                raise DomainError("INVALID_INPUT", "Supply one response representation")
            values["response"] = strict_json(raw)
        return db.reconcile_attempt(user, rid, **values)

    @app.post("/api/projects/{pid}/contracts/validate")
    def validate_contract(pid: str, body: ContractInput, user=user_dependency):
        import json

        action = validate_action(json.dumps(body.action))
        with db.tx() as c:
            project = db.own_project(c, user, pid)
            for dependency in action.dependencies:
                if dependency.kind == "resource":
                    db.authorize(
                        c, user, project["runtime_id"], pid, dependency.ref, "resource.read"
                    )
            for requirement in action.permission_requirements:
                db.authorize(
                    c,
                    user,
                    project["runtime_id"],
                    pid,
                    requirement.resource_ref,
                    requirement.tool_ref,
                )
        if body.input is not None:
            validate_action_input(action, body.input)
        return {
            "state": "VALIDATED_DRAFT",
            "publishable": False,
            "execution_performed": False,
            "action": action.model_dump(),
        }

    @app.post("/api/projects/{pid}/contracts/preflight")
    def preflight_contract(pid: str, body: PreflightInput, user=user_dependency):
        import json

        manifest, report = preflight(json.dumps(body.manifest), body.actions, platform_limits)
        with db.tx() as c:
            project = db.own_project(c, user, pid)
            for rid in report["resource_refs"]:
                db.authorize(c, user, project["runtime_id"], pid, rid, "resource.read")
            for requirement in manifest.permission_requirements:
                db.authorize(
                    c,
                    user,
                    project["runtime_id"],
                    pid,
                    requirement.resource_ref,
                    requirement.tool_ref,
                )
        report["candidate_fingerprint"] = fingerprint(
            {"manifest": report.pop("candidate_fingerprint_basis"), "actions": body.actions}
        )
        return report

    @app.get("/api/runs/{rid}/unresolved-operations")
    def unresolved_operations(rid: str, user=user_dependency):
        return db.unresolved_operations(user, rid)

    @app.post("/api/runs/{rid}/reconcile-operation")
    def reconcile_operation(rid: str, body: OperationReconcileInput, user=user_dependency):
        return db.reconcile_operation(user, rid, **body.model_dump())

    @app.get("/api/projects/{pid}/grants")
    def list_grants(pid: str, user=user_dependency):
        with db.tx() as c:
            db.own_project(c, user, pid)
            return [
                dict(x)
                for x in c.execute(select(grants).where(grants.c.project_id == pid)).mappings()
            ]

    @app.post("/api/grants/{gid}/revoke")
    def revoke(gid: str, body: CommandInput, user=user_dependency):
        with db.tx() as c:
            g = (
                c.execute(select(grants).where(grants.c.id == gid).with_for_update())
                .mappings()
                .first()
            )
            if not g:
                raise DomainError("PERMISSION_DENIED")
            db.own_project(c, user, g["project_id"])
            if g["revision"] != body.version or body.command != "revoke":
                raise DomainError("VERSION_CONFLICT")
            c.execute(
                update(grants)
                .where(grants.c.id == gid)
                .values(revoked=True, revision=g["revision"] + 1)
            )
        return {"status": "REVOKED"}

    @app.get("/api/projects/{pid}/goal-cards")
    def project_goal_cards(pid: str, user=user_dependency):
        return list_cards(db, user, pid)

    @app.post("/api/projects/{pid}/goal-cards", status_code=201)
    def new_goal_card(pid: str, body: GoalCardInput, user=user_dependency):
        return create_card(db, user, pid, body.model_dump())

    @app.get("/api/goal-cards/{cid}")
    def get_goal_card(cid: str, user=user_dependency):
        return inspect_card(db, user, cid)

    @app.put("/api/goal-cards/{cid}")
    def update_goal_card(cid: str, body: GoalCardUpdate, user=user_dependency):
        return revise_card(
            db, user, cid, body.model_dump(exclude={"expected_version"}), body.expected_version
        )

    from .goal_runs import GoalRunInput, acceptance

    @app.post("/api/projects/{pid}/goal-cards/{cid}/runs", status_code=202)
    def run_saved_goal(pid: str, cid: str, body: GoalRunInput, user=user_dependency):
        rid = db.submit(user, pid, "", [], body.request_key, policy={
            "limits": {**platform_limits.model_dump(), "max_repairs": 0},
            "mode": s.mode, "request_model": s.model,
        }, goal_source={"card_id": cid, "version": body.expected_version,
                        "fingerprint": body.expected_fingerprint})
        return acceptance(db, user, rid)

    @app.post("/api/projects/{pid}/goal-cards/{cid}/planned-runs", status_code=202)
    def plan_saved_goal(pid: str, cid: str, body: GoalRunInput, user=user_dependency):
        from .goal_planner import policy

        selected = policy(s.goal_planner_provider)
        rid = db.submit(user, pid, "", [], body.request_key, policy={
            "limits": {**platform_limits.model_dump(), "max_requests": 1, "max_repairs": 0},
            "mode": s.mode, "request_model": s.model, "natural_planning": selected,
        }, goal_source={"card_id": cid, "version": body.expected_version,
                        "fingerprint": body.expected_fingerprint})
        return {**acceptance(db, user, rid), "planning_policy": selected}

    @app.post("/api/runs/{rid}/confirm-natural-plan")
    def confirm_goal_plan(rid: str, body: ConfirmNaturalPlanInput, user=user_dependency):
        from .goal_planner import confirm_natural_plan

        return confirm_natural_plan(db, user, rid, body.model_dump(), s)

    from .natural_activations import ApproveInput, CreateInput, RevokeInput

    @app.post("/api/projects/{pid}/natural-activations", status_code=201)
    def create_natural_activation(pid: str, body: CreateInput, user=user_dependency):
        from .natural_activations import create

        return create(db, user, pid, body.model_dump(), s)

    @app.get("/api/projects/{pid}/natural-activations")
    def list_natural_activations(pid: str, user=user_dependency):
        from .natural_activations import list_for_project

        return list_for_project(db, user, pid, s)

    @app.get("/api/natural-activations/{aid}")
    def inspect_natural_activation(aid: str, user=user_dependency):
        from .natural_activations import inspect

        return inspect(db, user, aid, s)

    @app.post("/api/natural-activations/{aid}/approve")
    def approve_natural_activation(aid: str, body: ApproveInput, user=user_dependency):
        from .natural_activations import approve

        return approve(db, user, aid, body.model_dump(), s)

    @app.post("/api/natural-activations/{aid}/revoke")
    def revoke_natural_activation(aid: str, body: RevokeInput, user=user_dependency):
        from .natural_activations import revoke

        return revoke(db, user, aid, body.model_dump(), s)

    @app.post("/api/natural-activations/{aid}/close-expired")
    def close_expired_natural_activation(aid: str, body: ExpireNaturalActivationInput,
                                         user=user_dependency):
        from .natural_activations import close_expired

        return close_expired(db, user, aid, s)

    @app.post("/api/natural-activations/{aid}/goal-cards/{cid}/planned-runs", status_code=202)
    def run_activated_goal(aid: str, cid: str, body: GoalRunInput, user=user_dependency):
        from .goal_planner import policy
        from .natural_activations import binding_for_run, inspect

        bound = binding_for_run(db, user, aid, cid, body.model_dump(), s)
        pid = inspect(db, user, aid, s)["project_id"]
        selected = policy(s.goal_planner_provider, activation=bound)
        limits = platform_limits.model_dump()
        for key, cap in {"max_requests": 1, "max_repairs": 0, "max_tools": 2,
                         "max_total_tokens": 11000, "max_output_tokens": 512,
                         "run_seconds": 120}.items():
            limits[key] = min(limits[key], cap)
        rid = db.submit(user, pid, "", [], body.request_key,
                        policy={"limits": limits, "mode": s.mode, "request_model": s.model,
                                "natural_planning": selected},
                        goal_source={"card_id": cid, "version": body.expected_version,
                                     "fingerprint": body.expected_fingerprint})
        return {**acceptance(db, user, rid), "planning_policy": selected}

    @app.get("/api/projects/{pid}/natural-planning-status")
    def natural_planning_status(pid: str, user=user_dependency):
        with db.tx() as c:
            db.own_project(c, user, pid)
        return {
            "project_id": pid, "provider": s.goal_planner_provider,
            "live_request_allowance": 0, "available": False,
            "reason": "PROVIDER_DISABLED" if s.goal_planner_provider == "disabled"
                      else "LIVE_ALLOWANCE_ZERO",
            "confirmation_required": True,
        }

    @app.get("/api/goal-cards/{cid}/candidate-options")
    def goal_candidate_options(cid: str, user=user_dependency):
        return candidate_options(db, user, cid)

    @app.post("/api/goal-cards/{cid}/candidates", status_code=201)
    def goal_to_candidate(cid: str, body: GoalCandidateInput, user=user_dependency):
        return generate_candidate(db, user, cid, body.model_dump(), platform_limits)

    @app.get("/api/apps")
    def apps(user=user_dependency):
        with db.tx() as c:
            rows = (
                c.execute(
                    select(app_drafts.c.id, app_drafts.c.name, app_drafts.c.project_id, app_drafts.c.candidate)
                    .join(projects, projects.c.id == app_drafts.c.project_id)
                    .where(projects.c.owner_id == user)
                    .order_by(app_drafts.c.created_at.desc())
                )
                .mappings()
                .all()
            )
        items = []
        for r in rows:
            candidate = r["candidate"]
            if isinstance(candidate, dict) and candidate.get("namespace") == CONDITIONAL_APP_NAMESPACE:
                continue
            summary = {k: v for k, v in r.items() if k != "candidate"}
            hint = _csv_instance_candidate(candidate)
            if hint is not None:
                summary["csv_instance_candidate"] = hint
            items.append(summary)
        return {"items": items, "state": "PREVIEW_ONLY", "publishable": False}

    @app.post("/api/projects/{pid}/apps/csv-preview", status_code=201)
    def create_csv_preview(pid: str, body: CsvDraftInput, user=user_dependency):
        return create_csv_draft(
            db, user, pid, body.name, body.resource_id, body.goal, platform_limits
        )

    @app.get("/api/apps/{aid}")
    def get_app_draft(aid: str, user=user_dependency):
        return inspect_draft(db, user, aid, platform_limits)

    @app.post("/api/apps/{aid}/previews")
    def run_preview(aid: str, body: PreviewInput, user=user_dependency):
        return preview(db, user, aid, body.input, body.request_key, platform_limits)

    @app.get("/api/runs/{rid}/receipt-candidate-options")
    def receipt_candidate_options(rid: str, user=user_dependency):
        from .natural_receipt_extraction import options
        return options(db, user, rid, platform_limits)

    @app.post("/api/runs/{rid}/receipt-candidates", status_code=201)
    def receipt_candidate(rid: str, body: RegisteredExtractionInput, user=user_dependency):
        from .natural_receipt_extraction import extract
        return extract(db, user, rid, body.model_dump(), platform_limits)

    @app.post("/api/previews/{pid}/extract", status_code=201)
    def preview_to_candidate(pid: str, body: ExtractionInput, user=user_dependency):
        return extract_preview(db, user, pid, body.model_dump(), platform_limits)

    @app.post("/api/projects/{pid}/spec-checklist-tasks", status_code=201)
    def spec_checklist_task(pid: str, body: SpecChecklistInput, user=user_dependency):
        if s.mode != "mock":
            raise DomainError("UNSUPPORTED_CAPABILITY", "仅合成标注规范检查，不允许LIVE")
        return complete_checklist(db, user, pid, body.model_dump())

    @app.get("/api/spec-checklist-tasks/{tid}")
    def get_spec_checklist(tid: str, user=user_dependency):
        return inspect_checklist(db, user, tid)

    @app.post("/api/projects/{pid}/local-csv-tasks", status_code=201)
    def local_csv_task(pid: str, body: LocalTaskInput, user=user_dependency):
        if s.mode != "mock":
            raise DomainError("UNSUPPORTED_CAPABILITY", "仅本地合成固定任务，不允许LIVE")
        return complete_csv_task(db, user, pid, body.model_dump())

    @app.get("/api/local-csv-tasks/{tid}")
    def get_local_task(tid: str, user=user_dependency):
        return inspect_task(db, user, tid)

    @app.post("/api/local-csv-tasks/{tid}/extract", status_code=201)
    def local_task_extract(tid: str, body: TaskExtractionInput, user=user_dependency):
        return extract_task(db, user, tid, body.model_dump(), platform_limits)

    @app.post("/api/local-csv-tasks/{tid}/retire-source")
    def local_task_retire(tid: str, body: RetirementInput, user=user_dependency):
        return retire_task_source(db, user, tid, body.model_dump())

    @app.get("/api/capabilities")
    def capabilities(user=user_dependency):
        return {
            "materials": ["txt", "md", "csv", "json"],
            "tools": ["resource.read", "data.aggregate_csv", "artifact.save_text"],
            "connection": {
                "model": s.model,
                "mode": s.mode.upper(),
                "status": "MOCK_ENGINEERING" if s.mode == "mock" else "LIVE_NOT_ACCEPTED",
            },
            "code_execution": "DISABLED",
        }

    mount_internal_api(app, db, platform_limits, identity)
    mount_protocol_api(app, db, platform_limits, identity, s)
    mount_protocol_recovery(app, db, identity)
    mount_protocol_reviews(app, db, identity)
    mount_conditional_checks(app, db, identity)
    mount_conditional_runs(app, db, identity, platform_limits, s)
    mount_conditional_apps(app, db, identity, platform_limits, s)
    mount_report_manifest_apps(app, db, identity, platform_limits, s)
    mount_delivery_graph_apps(app, db, identity, platform_limits, s)

    web = Path(__file__).parent / "web"

    @app.get("/")
    def index():
        return FileResponse(web / "index.html")

    @app.get("/natural-goal.js")
    def natural_goal_script():
        return FileResponse(web / "natural-goal.js", media_type="text/javascript")

    @app.get("/app.js")
    def js():
        return FileResponse(web / "app.js", media_type="text/javascript")

    @app.get("/internal.js")
    def internal_js():
        return FileResponse(web / "internal.js", media_type="text/javascript")

    @app.get("/protocol.js")
    def protocol_js():
        return FileResponse(web / "protocol.js", media_type="text/javascript")

    @app.get("/conditional-runs.js")
    def conditional_runs_js():
        return FileResponse(web / "conditional-runs.js", media_type="text/javascript")

    @app.get("/report-manifest.js")
    def report_manifest_js():
        return FileResponse(web / "report-manifest.js", media_type="text/javascript")

    @app.get("/delivery-graph.js")
    def delivery_graph_js():
        return FileResponse(web / "delivery-graph.js", media_type="text/javascript")

    @app.get("/conditional-apps.js")
    def conditional_apps_js():
        return FileResponse(web / "conditional-apps.js", media_type="text/javascript")

    @app.get("/use.js")
    def use_js():
        return FileResponse(web / "use.js", media_type="text/javascript")

    @app.get("/app.css")
    def css():
        return FileResponse(web / "app.css", media_type="text/css")

    return app
