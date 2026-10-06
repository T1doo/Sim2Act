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

from .contracts import FrozenRunContract, GoalSpec, Limits, ResourceSnapshot
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
run_contracts = Table(
    "run_contracts",
    meta,
    Column("run_id", String, primary_key=True),
    Column("snapshot", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
)
operation_intents = Table(
    "operation_intents",
    meta,
    Column("operation_id", String, primary_key=True),
    Column("request", JSON, nullable=False),
)
local_effects = Table(
    "local_effects",
    meta,
    Column("operation_id", String, primary_key=True),
    Column("resource_id", String, unique=True, nullable=False),
    Column("content_hash", String, nullable=False),
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

# F2 engineering preview namespace, separate from F1 tasks and release/instance data.
goal_cards = Table(
    "goal_cards",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("title", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("created_at", Float, nullable=False),
)
goal_candidate_requests = Table(
    "goal_candidate_requests",
    meta,
    Column("card_id", String, primary_key=True),
    Column("principal_id", String, primary_key=True),
    Column("request_key", String, primary_key=True),
    Column("request_fingerprint", String, nullable=False),
    Column("app_id", String, nullable=False),
)
goal_card_versions = Table(
    "goal_card_versions",
    meta,
    Column("card_id", String, primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("snapshot", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("created_at", Float, nullable=False),
)

app_drafts = Table(
    "app_drafts",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("runtime_id", String, nullable=False),
    Column("name", String, nullable=False),
    Column("candidate", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("created_at", Float, nullable=False),
)
app_previews = Table(
    "app_previews",
    meta,
    Column("id", String, primary_key=True),
    Column("app_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("request_key", String, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("input", JSON, nullable=False),
    Column("status", String, nullable=False),
    Column("output", JSON),
    Column("error", JSON),
    Column("created_at", Float, nullable=False),
    UniqueConstraint("app_id", "principal_id", "request_key"),
)

# Explicit migration only; bounded P-B extraction from verified PREVIEW receipts.
preview_extractions = Table(
    "preview_extractions",
    meta,
    Column("preview_id", String, primary_key=True),
    Column("principal_id", String, primary_key=True),
    Column("request_key", String, primary_key=True),
    Column("request_fingerprint", String, nullable=False),
    Column("app_id", String, unique=True, nullable=False),
    Column("snapshot", JSON, nullable=False),
)


# Explicit migration only: completed local fixed tasks, proof-bound candidates and retirement.
local_csv_tasks = Table(
    "local_csv_tasks",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("resource_id", String, nullable=False),
    Column("request_key", String, nullable=False),
    Column("request_fingerprint", String, nullable=False),
    Column("status", String, nullable=False),
    Column("input", JSON),
    Column("output", JSON),
    Column("error", JSON),
    Column("proof", JSON),
    Column("proof_fingerprint", String),
    UniqueConstraint("project_id", "principal_id", "request_key"),
)
task_extractions = Table(
    "task_extractions",
    meta,
    Column("task_id", String, primary_key=True),
    Column("principal_id", String, primary_key=True),
    Column("request_key", String, primary_key=True),
    Column("request_fingerprint", String, nullable=False),
    Column("app_id", String, unique=True, nullable=False),
    Column("snapshot", JSON, nullable=False),
)
resource_retirements = Table(
    "resource_retirements",
    meta,
    Column("resource_id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("task_id", String, nullable=False),
    Column("proof_fingerprint", String, nullable=False),
    Column("source_hash", String, nullable=False),
    Column("policy", String, nullable=False),
)


# Internal F2-T08 engineering namespace only; explicit migration, no publication API.
internal_approvals = Table(
    "internal_approvals",
    meta,
    Column("id", String, primary_key=True),
    Column("principal_id", String, nullable=False),
    Column("project_id", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("expires_at", Float, nullable=False),
    Column("consumed", Boolean, nullable=False),
)
internal_releases = Table(
    "internal_releases",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("approval_id", String, unique=True, nullable=False),
    Column("snapshot", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
)
internal_instances = Table(
    "internal_instances",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("source_app_id", String, nullable=False),
    Column("runtime_id", String, nullable=False),
    Column("release_id", String, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("data_version", Integer, nullable=False),
    Column("history", JSON, nullable=False),
)
internal_app_runs = Table(
    "internal_app_runs",
    meta,
    Column("id", String, primary_key=True),
    Column("instance_id", String, nullable=False),
    Column("release_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("request_key", String, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("input", JSON, nullable=False),
    Column("status", String, nullable=False),
    Column("output", JSON),
    Column("error", JSON),
    Column("result_version", Integer),
    UniqueConstraint("instance_id", "principal_id", "request_key"),
)
internal_instance_data = Table(
    "internal_instance_data",
    meta,
    Column("instance_id", String, primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("run_id", String, unique=True, nullable=False),
    Column("release_id", String, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("data", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
)

internal_run_bindings = Table(
    "internal_run_bindings",
    meta,
    Column("run_id", String, primary_key=True),
    Column("app_run_id", String, unique=True, nullable=False),
    Column("snapshot", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
)


# Explicit controller migration; isolated protocol namespace, no identity/capability grant.
protocol_jobs = Table(
    "protocol_jobs",
    meta,
    Column("run_id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("runtime_id", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("accepted_snapshot", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("result_snapshot", JSON),
    Column("result_fingerprint", String),
    Column("completed_fence", Integer),
    Column("created_at", Float, nullable=False),
)
protocol_reviews = Table(
    "protocol_reviews",
    meta,
    Column("id", String, primary_key=True),
    Column("run_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("project_id", String, nullable=False),
    Column("contract_id", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("fingerprint", String, nullable=False),
    Column("request_key", String, nullable=False),
    Column("created_at", Float, nullable=False),
    UniqueConstraint("run_id", "request_key"),
)


# Explicit migration only; fixed service-selected protocol pools, no runtime DDL.
protocol_request_pools = Table(
    "protocol_request_pools",
    meta,
    Column("id", String, primary_key=True),
    Column("mode", String, nullable=False),
    Column("request_limit", Integer, nullable=False),
    Column("token_limit", Integer, nullable=False),
    Column("reserved_requests", Integer, nullable=False),
    Column("reserved_tokens", Integer, nullable=False),
    Column("known_tokens", Integer, nullable=False),
    Column("halted", Boolean, nullable=False),
    Column("halt_reason", String),
    Column("policy_fingerprint", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", Float, nullable=False),
)
protocol_request_slots = Table(
    "protocol_request_slots",
    meta,
    Column("attempt_id", String, primary_key=True),
    Column("pool_id", String, nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("run_id", String, nullable=False),
    Column("fence", Integer, nullable=False),
    Column("phase", String, nullable=False),
    Column("request_fingerprint", String, nullable=False),
    Column("reserved_tokens", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("usage", JSON),
    Column("safe_response_fingerprint", String),
    Column("error", String),
    Column("created_at", Float, nullable=False),
    Column("finished_at", Float),
    UniqueConstraint("pool_id", "ordinal"),
)

# Explicit Store.initialize/controller migration only, never API DDL.
spec_checklist_tasks = Table(
    "spec_checklist_tasks",
    meta,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False),
    Column("principal_id", String, nullable=False),
    Column("runtime_id", String, nullable=False),
    Column("resource_id", String, nullable=False),
    Column("source_hash", String, nullable=False),
    Column("request_key", String, nullable=False),
    Column("request_fingerprint", String, nullable=False),
    Column("request", JSON, nullable=False),
    Column("status", String, nullable=False),
    Column("output", JSON),
    Column("receipt", JSON),
    Column("proof", JSON),
    Column("proof_fingerprint", String),
    Column("error", JSON),
    UniqueConstraint("principal_id", "project_id", "request_key"),
)


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
        self.test_only = test_only  # Explicit fixture guard; production entrypoints leave False.

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

    def lock_project(self, c, principal, project_id):
        """Consumer creation and source retirement share project -> entity -> grant order."""
        p = (
            c.execute(
                select(projects)
                .where(projects.c.id == project_id, projects.c.owner_id == principal)
                .with_for_update()
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

    def submit(self, principal, project_id, goal, refs, key, *, policy=None):
        policy = policy or {
            "limits": Limits(
                max_requests=4,
                max_tools=4,
                max_repairs=1,
                max_total_tokens=64000,
                max_output_tokens=1024,
                run_seconds=300,
            ).model_dump(),
            "mode": "mock",
            "request_model": "intern-s2",
        }
        if len(set(refs)) != len(refs):
            raise DomainError("INVALID_INPUT", "Duplicate input resource")
        fp = fingerprint({"goal": goal, "resource_refs": refs, "policy": policy})
        try:
            with self.tx() as c:
                p = self.lock_project(c, principal, project_id)
                for rid in refs:
                    self.authorize(c, principal, p["runtime_id"], project_id, rid, "resource.read")
                    if c.execute(
                        select(resource_retirements.c.resource_id).where(
                            resource_retirements.c.resource_id == rid
                        )
                    ).first():
                        raise DomainError("RESOURCE_UNAVAILABLE", "退休来源不能成为新的任务输入")
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
                snapshot = FrozenRunContract(
                    run_id=rid,
                    runtime_id=p["runtime_id"],
                    contract_version="F1.3",
                    goal=GoalSpec(
                        goal_id=new_id("goal"),
                        project_id=project_id,
                        owner_id=principal,
                        goal=goal,
                        constraints=[],
                        acceptance_version="F1-tool-chain.v1",
                        resource_refs=refs,
                        unresolved=["Semantic goal acceptance NOT_RUN"],
                    ),
                    resources=[
                        ResourceSnapshot(
                            resource_id=r["id"],
                            revision=1,
                            content_hash=r["hash"],
                            format=r["format"],
                        )
                        for r in c.execute(
                            select(resources).where(resources.c.id.in_(refs))
                        ).mappings()
                    ],
                    **policy,
                ).model_dump()
                c.execute(
                    insert(run_contracts).values(
                        run_id=rid, snapshot=snapshot, fingerprint=fingerprint(snapshot)
                    )
                )
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
            return self.submit(principal, project_id, goal, refs, key, policy=policy)

    def guard(self, c, run_id, fence):
        r = c.execute(select(runs).where(runs.c.id == run_id).with_for_update()).mappings().one()
        if (
            r["fence"] != fence
            or r["lease_until"] <= time.time()
            or r["status"] not in {"RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED"}
        ):
            raise DomainError("VERSION_CONFLICT", "Stale worker lease")
        self.frozen_contract(c, r)
        return dict(r)

    def frozen_contract(self, c, run):
        saved = (
            c.execute(select(run_contracts).where(run_contracts.c.run_id == run["id"]))
            .mappings()
            .first()
        )
        if not saved or fingerprint(saved["snapshot"]) != saved["fingerprint"]:
            raise DomainError(
                "VERSION_CONFLICT",
                "Missing or modified frozen Run contract; legacy runs require explicit closure",
            )
        contract = FrozenRunContract.model_validate(saved["snapshot"])
        goal = contract.goal
        if (
            contract.run_id != run["id"]
            or contract.runtime_id != run["runtime_id"]
            or goal.goal != run["goal"]
            or goal.resource_refs != run["resource_refs"]
            or goal.project_id != run["project_id"]
            or goal.owner_id != run["principal_id"]
        ):
            raise DomainError("VERSION_CONFLICT", "Run no longer matches frozen goal")
        for item in contract.resources:
            current = (
                c.execute(
                    select(resources).where(
                        resources.c.id == item.resource_id,
                        resources.c.project_id == run["project_id"],
                    )
                )
                .mappings()
                .first()
            )
            if (
                not current
                or current["hash"] != item.content_hash
                or current["format"] != item.format
                or hashlib.sha256(current["content"].encode()).hexdigest() != item.content_hash
            ):
                raise DomainError(
                    "VERSION_CONFLICT", "Input resource no longer matches frozen snapshot"
                )
        return contract

    def claim(self, worker_id, lease_seconds):
        from .protocol_jobs import protocol_run_ids
        from .protocol_recovery import recover_expired_protocols

        recover_expired_protocols(self)
        now = time.time()
        with self.tx() as c:
            protocol_member = runs.c.id.in_(protocol_run_ids(c))
            expired = (
                c.execute(
                    select(runs)
                    .where(
                        ~protocol_member,
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
                        operations.c.status.in_(["DISPATCHED", "OUTCOME_UNKNOWN", "RECEIPT_KNOWN"]),
                    )
                ).first()
                state = (
                    ("RECONCILING" if r["cancel_intent"] else "WAITING_RESOURCE")
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
                # Reconciliation/row acquisition may consume the scan's entire lease.
                # Start this new ownership interval only after that work completes.
                lease_until=time.time() + lease_seconds,
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
        from .protocol_jobs import inspect as inspect_protocol_job
        from .protocol_jobs import is_protocol_job

        if is_protocol_job(self, run_id):
            return inspect_protocol_job(self, principal, run_id)
        from .app_jobs import inspect_job, is_app_job

        if is_app_job(self, run_id):
            return inspect_job(self, principal, run_id)
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
                "contract": self.contract_metadata(c, r),
                "known_effects": self.known_effects(c, run_id),
            }

    def contract_metadata(self, c, run):
        saved = (
            c.execute(select(run_contracts).where(run_contracts.c.run_id == run["id"]))
            .mappings()
            .first()
        )
        return (
            {"snapshot": saved["snapshot"], "fingerprint": saved["fingerprint"]}
            if saved
            else {"state": "LEGACY_UNFROZEN"}
        )

    def known_effects(self, c, run_id):
        return [
            dict(x)
            for x in c.execute(
                select(
                    operations.c.id,
                    operations.c.tool_ref,
                    operations.c.status,
                    local_effects.c.resource_id,
                    local_effects.c.content_hash,
                )
                .select_from(
                    operations.outerjoin(
                        local_effects, operations.c.id == local_effects.c.operation_id
                    )
                )
                .where(
                    operations.c.run_id == run_id,
                    operations.c.status.in_(["VERIFIED", "EFFECT_KNOWN_INVALID"]),
                )
            ).mappings()
        ]

    def has_unknown(self, c, run_id):
        return bool(
            c.execute(
                select(attempts.c.id).where(
                    attempts.c.run_id == run_id, attempts.c.status == "STARTED"
                )
            ).first()
            or c.execute(
                select(operations.c.id).where(
                    operations.c.run_id == run_id,
                    operations.c.status.in_(["DISPATCHED", "OUTCOME_UNKNOWN", "RECEIPT_KNOWN"]),
                )
            ).first()
        )

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
        from .protocol_jobs import command_job as command_protocol_job
        from .protocol_jobs import is_protocol_job

        if is_protocol_job(self, run_id):
            return command_protocol_job(self, principal, run_id, command, version)
        from .app_jobs import command_job, is_app_job

        if is_app_job(self, run_id):
            return command_job(self, principal, run_id, command, version)
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
                pending = self.has_unknown(c, run_id)
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
                self.frozen_contract(c, r)
                self.authorize_receipts(c, r)
                if self.has_unknown(c, run_id):
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

    def unresolved_attempts(self, principal, run_id):
        from .protocol_jobs import is_protocol_job, verified_pending

        if is_protocol_job(self, run_id):
            with self.tx() as c:
                verified_pending(self, c, principal, run_id)
        with self.engine.connect() as c:
            if not c.execute(
                select(runs.c.id).where(runs.c.id == run_id, runs.c.principal_id == principal)
            ).first():
                raise DomainError("PERMISSION_DENIED")
            rows = (
                c.execute(
                    select(attempts).where(
                        attempts.c.run_id == run_id, attempts.c.status == "STARTED"
                    )
                )
                .mappings()
                .all()
            )
        return [
            {
                "attempt_id": a["id"],
                "mode": a["mode"],
                "request_model": a["request_model"],
                "request_fingerprint": (a["parameters"] or {}).get("request_fingerprint"),
                "usage": a["usage"],
                "state": "OUTCOME_UNKNOWN",
            }
            for a in rows
        ]

    def reconcile_attempt(
        self,
        principal,
        run_id,
        attempt_id,
        version,
        decision,
        expected_fingerprint,
        evidence,
        acknowledge_unknown_cost,
        response=None,
    ):
        from .model import parse_response, require_returned_model, returned_model_identity
        from .protocol_jobs import is_protocol_job, verified_pending

        if is_protocol_job(self, run_id):
            with self.tx() as c:
                verified_pending(self, c, principal, run_id)
            raise DomainError(
                "UNSUPPORTED_CAPABILITY", "Protocol continuation is not implemented; no F1 fallback"
            )

        with self.tx() as c:
            run = (
                c.execute(
                    select(runs)
                    .where(runs.c.id == run_id, runs.c.principal_id == principal)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if not run:
                raise DomainError("PERMISSION_DENIED")
            if run["version"] != version or run["status"] not in {
                "WAITING_RESOURCE",
                "RECONCILING",
            }:
                raise DomainError(
                    "VERSION_CONFLICT", "Reconciliation requires the current waiting version"
                )
            self.own_project(c, principal, run["project_id"])
            if decision == "record_response":
                for rid in run["resource_refs"]:
                    self.authorize(
                        c, principal, run["runtime_id"], run["project_id"], rid, "resource.read"
                    )
                self.authorize_receipts(c, run)
            attempt = (
                c.execute(
                    select(attempts)
                    .where(attempts.c.id == attempt_id, attempts.c.run_id == run_id)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if not attempt or attempt["status"] != "STARTED":
                raise DomainError("VERSION_CONFLICT", "Attempt is not unresolved")
            stored_fp = (attempt["parameters"] or {}).get("request_fingerprint")
            if (
                not acknowledge_unknown_cost
                or not evidence.strip()
                or expected_fingerprint != stored_fp
            ):
                raise DomainError(
                    "INVALID_INPUT",
                    "Exact request binding and explicit unknown-cost acknowledgement required",
                )
            unresolved = c.execute(
                select(attempts.c.id).where(
                    attempts.c.run_id == run_id, attempts.c.status == "STARTED"
                )
            ).all()
            unknown_ops = c.execute(
                select(operations.c.id).where(
                    operations.c.run_id == run_id,
                    operations.c.status.in_(["DISPATCHED", "OUTCOME_UNKNOWN", "RECEIPT_KNOWN"]),
                )
            ).first()
            if unknown_ops:
                raise DomainError(
                    "OUTCOME_UNKNOWN", "Model reconciliation cannot resolve unknown tool effects"
                )
            ctx = dict(run["context"])
            result = {
                "decision": decision,
                "evidence_note": evidence,
                "principal_id": principal,
                "attempt_id": attempt_id,
                "request_fingerprint": stored_fp,
                "unknown_cost_acknowledged": True,
                "provenance": "USER_SUPPLIED",
            }
            if decision == "record_response":
                if len(unresolved) != 1 or not stored_fp or not isinstance(response, dict):
                    raise DomainError(
                        "INVALID_INPUT", "A uniquely bound complete response is required"
                    )
                # Recover only the exact recorded request. Changed context is never silently accepted.
                from .tools import definitions

                current_fp = fingerprint(
                    {
                        "messages": ctx["messages"],
                        "tools": definitions(),
                        "model": attempt["request_model"],
                    }
                )
                if current_fp != stored_fp:
                    raise DomainError("VERSION_CONFLICT", "Request context has changed")
                raw_returned_model = response.get("model")
                identity = returned_model_identity(
                    attempt["request_model"], raw_returned_model, enforced=attempt["mode"] == "LIVE"
                )
                if attempt["mode"] == "MOCK":
                    if raw_returned_model != "MOCK-intern-contract":
                        raise DomainError(
                            "MODEL_OUTPUT_INVALID",
                            "Recovered response model does not match synthetic attempt",
                        )
                elif attempt["mode"] == "LIVE":
                    require_returned_model(identity)
                else:
                    raise DomainError("MODEL_OUTPUT_INVALID", "Unknown attempt mode")
                contract = self.frozen_contract(c, run)
                message, calls = parse_response(response)
                if len(calls) + ctx["tools"] > contract.limits.max_tools:
                    raise DomainError("BUDGET_EXHAUSTED")
                ctx["messages"] = [*ctx["messages"], message]
                c.execute(
                    update(attempts)
                    .where(attempts.c.id == attempt_id)
                    .values(
                        status="RECONCILED_RESPONSE",
                        response_model=raw_returned_model,
                        parameters={**(attempt["parameters"] or {}), "model_identity": identity},
                        response=message,
                    )
                )
                state = "CANCELLED" if run["cancel_intent"] else "PAUSED"
                result["model_identity"] = identity
                result["response_fingerprint"] = fingerprint(message)
                result["tools_dispatched"] = 0
            elif decision == "close_unknown":
                if response is not None:
                    raise DomainError(
                        "INVALID_INPUT", "Closing unknown attempts does not import a response"
                    )
                c.execute(
                    update(attempts)
                    .where(attempts.c.id == attempt_id)
                    .values(status="CLOSED_UNKNOWN", error="OUTCOME_UNKNOWN")
                )
                state = "WAITING_RESOURCE" if len(unresolved) > 1 else "CANCELLED"
            else:
                raise DomainError("INVALID_INPUT", "Unsupported reconciliation decision")
            # Original usage and reservations are never erased or set to zero by an operator.
            c.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(
                    context=ctx,
                    status=state,
                    fence=run["fence"] + 1,
                    lease_until=0,
                    version=version + 1,
                    cancel_intent=run["cancel_intent"] or decision == "close_unknown",
                    error={
                        "code": "OUTCOME_UNKNOWN",
                        "message": "已结束任务；模型用量仍未知，已发生的效果保留",
                    }
                    if decision == "close_unknown"
                    else None,
                )
            )
            self.event(c, run_id, "ATTEMPT_RECONCILED", result)
            return {
                "status": state,
                "version": version + 1,
                "tools_dispatched": 0,
                "usage": attempt["usage"],
            }

    def unresolved_operations(self, principal, run_id):
        with self.tx() as c:
            run = (
                c.execute(select(runs).where(runs.c.id == run_id, runs.c.principal_id == principal))
                .mappings()
                .first()
            )
            if not run:
                raise DomainError("PERMISSION_DENIED")
            return [
                dict(x)
                for x in c.execute(
                    select(
                        operations.c.id,
                        operations.c.tool_ref,
                        operations.c.status,
                        operations.c.fingerprint,
                    ).where(
                        operations.c.run_id == run_id,
                        operations.c.status.in_(["DISPATCHED", "OUTCOME_UNKNOWN", "RECEIPT_KNOWN"]),
                    )
                ).mappings()
            ]

    def reconcile_operation(
        self, principal, run_id, operation_id, version, expected_fingerprint, evidence
    ):
        from .protocol_jobs import is_protocol_job, verified_pending
        from .tools import reconcile_readback

        if is_protocol_job(self, run_id):
            with self.tx() as c:
                verified_pending(self, c, principal, run_id)
            raise DomainError(
                "UNSUPPORTED_CAPABILITY", "Protocol reconciliation requires its own immutable plan"
            )

        with self.tx() as c:
            run = (
                c.execute(
                    select(runs)
                    .where(runs.c.id == run_id, runs.c.principal_id == principal)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if not run:
                raise DomainError("PERMISSION_DENIED")
            self.own_project(c, principal, run["project_id"])
            if run["version"] != version or run["status"] not in {
                "WAITING_RESOURCE",
                "RECONCILING",
            }:
                raise DomainError("VERSION_CONFLICT")
            op = (
                c.execute(
                    select(operations)
                    .where(operations.c.id == operation_id, operations.c.run_id == run_id)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if not op or op["status"] not in {"DISPATCHED", "OUTCOME_UNKNOWN", "RECEIPT_KNOWN"}:
                raise DomainError("VERSION_CONFLICT")
            if (
                not evidence.strip()
                or not op["fingerprint"]
                or expected_fingerprint != op["fingerprint"]
            ):
                raise DomainError(
                    "INVALID_INPUT", "Exact operation fingerprint and evidence note required"
                )
            status, receipt = reconcile_readback(self, c, run, op)
            ctx = dict(run["context"])
            if status == "VERIFIED":
                # Recover feedback only to the original recorded assistant intent.
                matching = [
                    call
                    for message in ctx["messages"]
                    if message["role"] == "assistant"
                    for call in message.get("tool_calls", [])
                    if call["id"] == op["call_id"]
                ]
                if len(matching) != 1:
                    raise DomainError("VERSION_CONFLICT", "No unique recorded tool call")
                call = matching[0]
                intent = {
                    "tool": call["function"]["name"],
                    "args": json.loads(call["function"]["arguments"]),
                }
                if fingerprint(intent) != op["fingerprint"]:
                    raise DomainError("VERSION_CONFLICT", "Tool context changed")
                feedback = {
                    "role": "tool",
                    "tool_call_id": op["call_id"],
                    "content": json.dumps(receipt, ensure_ascii=False),
                }
                messages = list(ctx["messages"])
                existing = [
                    index
                    for index, message in enumerate(messages)
                    if message["role"] == "tool" and message.get("tool_call_id") == op["call_id"]
                ]
                if len(existing) > 1:
                    raise DomainError("VERSION_CONFLICT", "Duplicate tool feedback")
                if existing:
                    messages[existing[0]] = feedback
                else:
                    position = (
                        next(
                            index
                            for index, message in enumerate(messages)
                            if message["role"] == "assistant"
                            and any(
                                call["id"] == op["call_id"]
                                for call in message.get("tool_calls", [])
                            )
                        )
                        + 1
                    )
                    while position < len(messages) and messages[position]["role"] == "tool":
                        position += 1
                    messages.insert(position, feedback)
                ctx["messages"] = messages
            c.execute(
                update(operations)
                .where(operations.c.id == operation_id)
                .values(status=status, receipt=receipt if status == "VERIFIED" else op["receipt"])
            )
            known_count = len(
                c.execute(
                    select(operations.c.id).where(
                        operations.c.run_id == run_id,
                        operations.c.status.in_(["VERIFIED", "EFFECT_KNOWN_INVALID"]),
                    )
                ).all()
            )
            ctx["tools"] = max(ctx["tools"], known_count)
            if self.has_unknown(c, run_id):
                state = "RECONCILING" if run["cancel_intent"] else "WAITING_RESOURCE"
            else:
                invalid = c.execute(
                    select(operations.c.id).where(
                        operations.c.run_id == run_id, operations.c.status == "EFFECT_KNOWN_INVALID"
                    )
                ).first()
                state = "CANCELLED" if run["cancel_intent"] else "FAILED" if invalid else "PAUSED"
            c.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(
                    status=state,
                    context=ctx,
                    fence=run["fence"] + 1,
                    lease_until=0,
                    version=version + 1,
                    error={
                        "code": "OUTCOME_UNKNOWN"
                        if status == "OUTCOME_UNKNOWN"
                        else "VERIFICATION_FAILED"
                    }
                    if status != "VERIFIED"
                    else None,
                )
            )
            self.event(
                c,
                run_id,
                "OPERATION_RECONCILED",
                {
                    "operation_id": operation_id,
                    "status": status,
                    "request_fingerprint": expected_fingerprint,
                    "principal_id": principal,
                    "evidence_note": evidence,
                    "provenance": "TRUSTED_LOCAL_READBACK"
                    if status != "OUTCOME_UNKNOWN"
                    else "UNCONFIRMED",
                    "tools_dispatched": 0,
                },
            )
            return {
                "status": state,
                "operation_status": status,
                "version": version + 1,
                "tools_dispatched": 0,
                "known_effects": self.known_effects(c, run_id),
            }
