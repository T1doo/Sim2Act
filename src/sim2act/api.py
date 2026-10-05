import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import Field
from sqlalchemy import select, update

from .config import Settings
from .contracts import Strict, resource_id, strict_json
from .db import Store, grants, heartbeats, projects, resources, runs
from .errors import DomainError


class ProjectInput(Strict):
    name: str = Field(min_length=1, max_length=200)


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


def create_app(store=None, settings=None):
    s = settings or Settings.from_env()
    db = store or Store(s.database_url)
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
            return dict(r)

    @app.get("/api/projects/{pid}/runs")
    def list_runs(pid: str, user=user_dependency):
        with db.tx() as c:
            db.own_project(c, user, pid)
            return [
                dict(r)
                for r in c.execute(
                    select(runs.c.id, runs.c.status, runs.c.created_at)
                    .where(runs.c.project_id == pid, runs.c.principal_id == user)
                    .order_by(runs.c.created_at.desc())
                ).mappings()
            ]

    @app.post("/api/projects/{pid}/runs", status_code=202)
    def create_run(pid: str, body: RunInput, user=user_dependency):
        for rid in body.resource_refs:
            resource_id(rid)
        return {
            "run_id": db.submit(user, pid, body.goal, body.resource_refs, body.request_key),
            "mode": s.mode.upper(),
        }

    @app.get("/api/runs/{rid}")
    def inspect_run(rid: str, user=user_dependency):
        return db.inspect(user, rid)

    @app.post("/api/runs/{rid}/commands")
    def command(rid: str, body: CommandInput, user=user_dependency):
        return {"status": db.command(user, rid, body.command, body.version)}

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

    @app.get("/api/apps")
    def apps(user=user_dependency):
        return {
            "items": [],
            "state": "PLANNED",
            "reason": "F2 implements P-A, P-B and immutable releases",
        }

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

    web = Path(__file__).parent / "web"

    @app.get("/")
    def index():
        return FileResponse(web / "index.html")

    @app.get("/app.js")
    def js():
        return FileResponse(web / "app.js", media_type="text/javascript")

    @app.get("/app.css")
    def css():
        return FileResponse(web / "app.css", media_type="text/css")

    return app
