"""Transactional ledger. SQLite is restricted to synthetic engineering tests."""

import hashlib
import json
import time
import uuid
from contextlib import contextmanager

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from .errors import DomainError

meta = MetaData()
principals = Table(
    "principals",
    meta,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("token_hash", String, unique=True),
)
projects = Table(
    "projects",
    meta,
    Column("id", String, primary_key=True),
    Column("owner_id", String, nullable=False),
    Column("runtime_id", String, nullable=False),
    Column("name", String, nullable=False),
)
resources = Table(
    "resources",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("name", String),
    Column("format", String),
    Column("content", String),
    Column("hash", String),
)
grants = Table(
    "grants",
    meta,
    Column("id", String, primary_key=True),
    Column("principal_id", String, nullable=False),
    Column("project_id", String, nullable=False),
    Column("resource_id", String, nullable=False),
    Column("tool_ref", String, nullable=False),
    Column("expires_at", Float, nullable=False),
    Column("revision", Integer, default=1),
    Column("revoked", Boolean, default=False),
)
runs = Table(
    "runs",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("runtime_id", String, nullable=False),
    Column("goal", String),
    Column("resource_refs", JSON),
    Column("status", String, nullable=False),
    Column("request_key", String),
    Column("fingerprint", String),
    Column("created_at", Float),
    Column("lease_until", Float, default=0),
    Column("fence", Integer, default=0),
    Column("worker_id", String),
    Column("context", JSON),
    Column("result", JSON),
    Column("error", JSON),
    Column("cancel_intent", Boolean, default=False),
    Column("version", Integer, default=1),
    UniqueConstraint("principal_id", "project_id", "request_key"),
)
events = Table(
    "events",
    meta,
    Column("id", String, primary_key=True),
    Column("run_id", String),
    Column("created_at", Float),
    Column("kind", String),
    Column("data", JSON),
)
operations = Table(
    "operations",
    meta,
    Column("id", String, primary_key=True),
    Column("run_id", String),
    Column("call_id", String),
    Column("fingerprint", String),
    Column("tool_ref", String),
    Column("status", String),
    Column("receipt", JSON),
    UniqueConstraint("run_id", "call_id"),
)
attempts = Table(
    "attempts",
    meta,
    Column("id", String, primary_key=True),
    Column("run_id", String),
    Column("created_at", Float),
    Column("mode", String),
    Column("request_model", String),
    Column("response_model", String),
    Column("status", String),
    Column("usage", JSON),
    Column("reserved_tokens", Integer),
    Column("parameters", JSON),
    Column("response", JSON),
    Column("error", String),
    Column("elapsed", Float),
)
quotas = Table(
    "quotas",
    meta,
    Column("subject", String, primary_key=True),
    Column("blocked_until", Float, default=0),
)
reservations = Table(
    "reservations",
    meta,
    Column("id", String, primary_key=True),
    Column("subject", String),
    Column("created_at", Float),
    Column("run_id", String),
)
heartbeats = Table("heartbeats", meta, Column("id", String, primary_key=True), Column("at", Float))


def new_id(prefix):
    return prefix + "_" + uuid.uuid4().hex


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


class Store:
    def __init__(self, url: str, *, test_only=False):
        if not url.startswith("postgresql+psycopg://") and not (
            test_only and url.startswith("sqlite://")
        ):
            raise ValueError("PostgreSQL required outside engineering tests")
        self.engine = create_engine(url, pool_pre_ping=True)
        self.sqlite = self.engine.dialect.name == "sqlite"

    @contextmanager
    def tx(self):
        with self.engine.connect() as c:
            if self.sqlite:
                c.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                c.begin()
            try:
                yield c
                c.commit()
            except BaseException:
                c.rollback()
                raise

    def initialize(self, quota_subject="default-intern-account"):
        # Explicit migration command only, never implicitly from API/worker.
        meta.create_all(self.engine)
        with self.tx() as c:
            if not c.execute(select(quotas).where(quotas.c.subject == quota_subject)).first():
                c.execute(insert(quotas).values(subject=quota_subject, blocked_until=0))

    def user(self, name, token):
        uid = new_id("user")
        with self.tx() as c:
            c.execute(
                insert(principals).values(
                    id=uid, name=name, token_hash=hashlib.sha256(token.encode()).hexdigest()
                )
            )
        return uid

    def authenticate(self, token):
        with self.engine.connect() as c:
            row = c.execute(
                select(principals.c.id).where(
                    principals.c.token_hash == hashlib.sha256(token.encode()).hexdigest()
                )
            ).first()
        if not row:
            raise DomainError("PERMISSION_DENIED")
        return row.id

    def project(self, owner, name):
        pid, runtime = new_id("proj"), new_id("runtime")
        with self.tx() as c:
            c.execute(insert(principals).values(id=runtime, name="project runtime"))
            c.execute(
                insert(projects).values(id=pid, owner_id=owner, runtime_id=runtime, name=name)
            )
        return pid

    def own_project(self, c, principal, project_id):
        p = (
            c.execute(
                select(projects).where(
                    projects.c.id == project_id, projects.c.owner_id == principal
                )
            )
            .mappings()
            .first()
        )
        if not p:
            raise DomainError("PERMISSION_DENIED")
        return p

    def authorize(self, c, principal, runtime, project_id, rid, tool):
        self.own_project(c, principal, project_id)
        if rid != project_id and tool != "resource.read":
            self.authorize(c, principal, runtime, project_id, rid, "resource.read")
        if rid == project_id:
            if tool != "artifact.save_text":
                raise DomainError("PERMISSION_DENIED")
        elif not c.execute(
            select(resources.c.id).where(
                resources.c.id == rid, resources.c.project_id == project_id
            )
        ).first():
            raise DomainError("PERMISSION_DENIED")
        for identity in [principal, runtime]:
            g = (
                c.execute(
                    select(grants)
                    .where(
                        grants.c.principal_id == identity,
                        grants.c.project_id == project_id,
                        grants.c.resource_id == rid,
                        grants.c.tool_ref == tool,
                    )
                    .order_by(grants.c.id)
                    .with_for_update()
                )
                .mappings()
                .all()
            )
            if not g:
                raise DomainError("PERMISSION_DENIED")
            if not any(not x["revoked"] and x["expires_at"] > time.time() for x in g):
                raise DomainError("GRANT_REVOKED")

    def add_grants(self, c, principal, runtime, project_id, rid, tools):
        for who in [principal, runtime]:
            for tool in tools:
                c.execute(
                    insert(grants).values(
                        id=new_id("grant"),
                        principal_id=who,
                        project_id=project_id,
                        resource_id=rid,
                        tool_ref=tool,
                        expires_at=time.time() + 86400,
                        revision=1,
                        revoked=False,
                    )
                )

    def resource(self, principal, project_id, name, fmt, content):
        if fmt not in {"txt", "md", "csv", "json"} or len(content.encode()) > 32768:
            raise DomainError(
                "INVALID_INPUT", "Supported text resource exceeds limits or has unknown format"
            )
        from .contracts import strict_json

        if fmt == "json":
            strict_json(content)
        rid = new_id("res")
        with self.tx() as c:
            p = self.own_project(c, principal, project_id)
            c.execute(
                insert(resources).values(
                    id=rid,
                    project_id=project_id,
                    name=name[:200],
                    format=fmt,
                    content=content,
                    hash=hashlib.sha256(content.encode()).hexdigest(),
                )
            )
            self.add_grants(
                c,
                principal,
                p["runtime_id"],
                project_id,
                rid,
                ["resource.read", "data.aggregate_csv"],
            )
        return rid

    def event(self, c, run_id, kind, data=None):
        c.execute(
            insert(events).values(
                id=new_id("event"),
                run_id=run_id,
                created_at=time.time(),
                kind=kind,
                data=data or {},
            )
        )

    def submit(self, principal, project_id, goal, refs, key):
        fp = fingerprint({"goal": goal, "resource_refs": refs})
        try:
            with self.tx() as c:
                p = self.own_project(c, principal, project_id)
                for rid in refs:
                    self.authorize(c, principal, p["runtime_id"], project_id, rid, "resource.read")
                old = (
                    c.execute(
                        select(runs).where(
                            runs.c.principal_id == principal,
                            runs.c.project_id == project_id,
                            runs.c.request_key == key,
                        )
                    )
                    .mappings()
                    .first()
                )
                if old:
                    if old["fingerprint"] != fp:
                        raise DomainError(
                            "VERSION_CONFLICT", "Idempotency key reused with changed input"
                        )
                    return old["id"]
                rid = new_id("run")
                c.execute(
                    insert(runs).values(
                        id=rid,
                        project_id=project_id,
                        principal_id=principal,
                        runtime_id=p["runtime_id"],
                        goal=goal,
                        resource_refs=refs,
                        request_key=key,
                        fingerprint=fp,
                        status="QUEUED",
                        created_at=time.time(),
                        lease_until=0,
                        fence=0,
                        context={
                            "messages": [],
                            "requests": 0,
                            "tools": 0,
                            "repairs": 0,
                            "reserved_tokens": 0,
                        },
                        version=1,
                        cancel_intent=False,
                    )
                )
                self.event(c, rid, "ACCEPTED", {"input_fingerprint": fp})
                return rid
        except IntegrityError:
            # Concurrent duplicate submit: read winner; never create a second operation.
            return self.submit(principal, project_id, goal, refs, key)

    def guard(self, c, run_id, fence):
        r = c.execute(select(runs).where(runs.c.id == run_id).with_for_update()).mappings().one()
        if (
            r["fence"] != fence
            or r["lease_until"] <= time.time()
            or r["status"] not in {"RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}
        ):
            raise DomainError("VERSION_CONFLICT", "Stale worker lease")
        return dict(r)

    def claim(self, worker_id, lease_seconds):
        now = time.time()
        with self.tx() as c:
            expired = (
                c.execute(
                    select(runs)
                    .where(
                        runs.c.status.in_(["RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"]),
                        runs.c.lease_until <= now,
                    )
                    .with_for_update(skip_locked=True)
                )
                .mappings()
                .all()
            )
            for r in expired:
                c.execute(
                    update(runs)
                    .where(runs.c.id == r["id"])
                    .values(status="RECONCILING", fence=r["fence"] + 1, version=r["version"] + 1)
                )
                self.event(c, r["id"], "WORKER_LOST", {"fence": r["fence"] + 1})
                # Local tools commit their receipt atomically. Only model response may be unknown.
                pending = c.execute(
                    select(attempts.c.id).where(
                        attempts.c.run_id == r["id"], attempts.c.status == "STARTED"
                    )
                ).first()
                op = c.execute(
                    select(operations.c.id).where(
                        operations.c.run_id == r["id"],
                        operations.c.status.in_(["DISPATCHED", "OUTCOME_UNKNOWN"]),
                    )
                ).first()
                state = (
                    "WAITING_RESOURCE"
                    if pending or op
                    else (
                        "CANCELLED"
                        if r["cancel_intent"]
                        else "PAUSED"
                        if r["status"] == "PAUSE_REQUESTED"
                        else "QUEUED"
                    )
                )
                c.execute(
                    update(runs)
                    .where(runs.c.id == r["id"])
                    .values(
                        status=state, error={"code": "OUTCOME_UNKNOWN"} if pending or op else None
                    )
                )
                self.event(c, r["id"], "RECONCILED", {"status": state, "receipts_preserved": True})
            row = (
                c.execute(
                    select(runs)
                    .where(runs.c.status == "QUEUED")
                    .order_by(runs.c.created_at)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            data = dict(row)
            data.update(
                status="RUNNING",
                fence=row["fence"] + 1,
                lease_until=now + lease_seconds,
                worker_id=worker_id,
            )
            c.execute(
                update(runs)
                .where(runs.c.id == row["id"])
                .values(**{k: data[k] for k in ["status", "fence", "lease_until", "worker_id"]})
            )
            self.event(c, row["id"], "CLAIMED", {"fence": data["fence"]})
            return data

    def heartbeat(self, worker_id, run_id=None, fence=None, lease_seconds=30):
        with self.tx() as c:
            if c.execute(select(heartbeats.c.id).where(heartbeats.c.id == worker_id)).first():
                c.execute(
                    update(heartbeats).where(heartbeats.c.id == worker_id).values(at=time.time())
                )
            else:
                c.execute(insert(heartbeats).values(id=worker_id, at=time.time()))
            if run_id:
                self.guard(c, run_id, fence)
                c.execute(
                    update(runs)
                    .where(runs.c.id == run_id)
                    .values(lease_until=time.time() + lease_seconds)
                )

    def inspect(self, principal, run_id):
        with self.tx() as c:
            r = (
                c.execute(select(runs).where(runs.c.id == run_id, runs.c.principal_id == principal))
                .mappings()
                .first()
            )
            if not r:
                raise DomainError("PERMISSION_DENIED")
            for rid in r["resource_refs"]:
                self.authorize(c, principal, r["runtime_id"], r["project_id"], rid, "resource.read")
            self.authorize_receipts(c, r)
            ev = (
                c.execute(
                    select(events).where(events.c.run_id == run_id).order_by(events.c.created_at)
                )
                .mappings()
                .all()
            )
            return {
                "id": r["id"],
                "status": r["status"],
                "version": r["version"],
                "result": r["result"],
                "error": r["error"],
                "events": [dict(x) for x in ev],
            }

    def authorize_receipts(self, c, run):
        receipts = (
            c.execute(
                select(operations.c.receipt).where(
                    operations.c.run_id == run["id"],
                    operations.c.status == "VERIFIED",
                )
            )
            .scalars()
            .all()
        )
        for receipt in receipts:
            for rid in receipt.get("artifact_refs", []):
                self.authorize(
                    c,
                    run["principal_id"],
                    run["runtime_id"],
                    run["project_id"],
                    rid,
                    "resource.read",
                )

    def command(self, principal, run_id, command, version):
        with self.tx() as c:
            r = (
                c.execute(
                    select(runs)
                    .where(runs.c.id == run_id, runs.c.principal_id == principal)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if not r:
                raise DomainError("PERMISSION_DENIED")
            if r["version"] != version:
                raise DomainError("VERSION_CONFLICT")
            state = r["status"]
            if command == "pause" and state in {"RUNNING", "QUEUED"}:
                state = "PAUSE_REQUESTED" if state == "RUNNING" else "PAUSED"
            elif command == "cancel" and state in {
                "QUEUED",
                "RUNNING",
                "PAUSED",
                "WAITING_RESOURCE",
                "RECONCILING",
            }:
                pending = c.execute(
                    select(attempts.c.id).where(
                        attempts.c.run_id == run_id, attempts.c.status == "STARTED"
                    )
                ).first()
                state = (
                    "CANCEL_REQUESTED"
                    if state == "RUNNING"
                    else "RECONCILING"
                    if pending
                    else "CANCELLED"
                )
            elif command == "resume" and state in {"PAUSED", "WAITING_RESOURCE"}:
                for rid in r["resource_refs"]:
                    self.authorize(
                        c, principal, r["runtime_id"], r["project_id"], rid, "resource.read"
                    )
                if c.execute(
                    select(attempts.c.id).where(
                        attempts.c.run_id == run_id, attempts.c.status == "STARTED"
                    )
                ).first():
                    raise DomainError(
                        "OUTCOME_UNKNOWN", "Unresolved model attempt needs operator reconciliation"
                    )
                state = "QUEUED"
            else:
                raise DomainError("VERSION_CONFLICT", "Command unavailable in current state")
            c.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(
                    status=state,
                    version=version + 1,
                    cancel_intent=r["cancel_intent"] or command == "cancel",
                )
            )
            self.event(c, run_id, "COMMAND", {"command": command, "status": state})
            return state
