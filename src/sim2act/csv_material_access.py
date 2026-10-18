"""Explicit App business authority for one existing CSV, never system access.

Only the existing App runtime receives the existing two tools for 24 hours.
Durable records contain control metadata and request commitments, no source or
Goal text. Reads/replays never mint, renew or restore a Grant.
"""
import time
from contextlib import contextmanager
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import func, select

from . import apps, lifecycle
from . import delivery_graph_apps as graph
from .contracts import Strict
from .db import app_drafts, fingerprint, grants, resources
from .errors import DomainError
from .local_tasks import retirement_row
from .text_logic_reuse import pair, remember, require
from .tools import authorized_read, csv_column_options

VERSION = "csv-app-material-access.v1"
AUTH, REVOKE = VERSION+".authorize", VERSION+".revoke"
TOOLS = ("resource.read","data.aggregate_csv")
KEY = r"^[A-Za-z0-9_-]{1,100}$"
CONSENT = "AUTHORIZE_ONLY_THIS_APP_ALL_INSTANCES_READ_SUM_THIS_CSV_FOR_24H"
STOP = "REVOKE_THIS_APP_READ_SUM_THIS_CSV"


class Authorize(Strict):
    request_key: str = Field(pattern=KEY)
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=graph.HASH)
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_grant_version: str = Field(pattern=graph.HASH)
    expected_app_grants_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["AUTHORIZE_ONLY_THIS_APP_ALL_INSTANCES_READ_SUM_THIS_CSV_FOR_24H"]


class Revoke(Strict):
    request_key: str = Field(pattern=KEY)
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_app_grants_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["REVOKE_THIS_APP_READ_SUM_THIS_CSV"]


class Record(Strict):
    request_key: str = Field(pattern=KEY)
    request_fingerprint: str = Field(pattern=graph.HASH)
    principal_id: str
    project_id: str
    app_id: str
    runtime_id: str
    resource_id: str


@graph.controlled
def scope(store,c,user,aid):
    # Metadata only: withdrawal/status must remain available after source loss.
    meta = c.execute(select(app_drafts.c.id,app_drafts.c.project_id,app_drafts.c.runtime_id,
        app_drafts.c.fingerprint,
        app_drafts.c.candidate["generation"]["goal_card_id"].as_string().label("goal_id"),
        app_drafts.c.candidate["manifest"]["data_bindings"][0]["resource_ref"].as_string().label("source_id"),
        app_drafts.c.candidate["actions"][0]["executor"]["ref"].as_string().label("executor"))
        .where(app_drafts.c.id == aid)).mappings().first()
    if meta is None:
        raise DomainError("PERMISSION_DENIED")
    project = store.lock_project(c,user,meta["project_id"])
    require(meta["goal_id"] is not None and meta["executor"] == "data.aggregate_csv",
        "Only the existing GoalCard CSV App business scope is supported")
    return dict(meta),project


def app_grants(c,meta,rid):
    rows = [dict(r) for r in c.execute(select(grants).where(
        grants.c.principal_id == meta["runtime_id"],grants.c.project_id == meta["project_id"],
        grants.c.resource_id == rid,grants.c.tool_ref.in_(TOOLS))
        .order_by(grants.c.id).with_for_update()).mappings()]
    require(len(rows) <= 64,"Finite material authority capacity reached")
    return rows


def state(rows):
    active = {r["tool_ref"] for r in rows if not r["revoked"] and r["expires_at"] > time.time()}
    return "ACTIVE" if active == set(TOOLS) else "PARTIAL" if active else "INACTIVE"


@graph.controlled
def control_state(store,user,aid):
    with store.tx() as c:
        meta,project=scope(store,c,user,aid)
        ids=c.execute(select(grants.c.resource_id).where(grants.c.principal_id == meta["runtime_id"],
            grants.c.project_id == project["id"],grants.c.tool_ref.in_(TOOLS))
            .distinct().order_by(grants.c.resource_id).limit(65)).scalars().all()
        require(len(ids) <= 64,"Finite App material control capacity reached")
        items=[]
        for rid in ids:
            rows=app_grants(c,meta,rid)
            items.append(dict(resource_id=rid,app_grants=rows,
                app_grants_fingerprint=fingerprint(rows),status=state(rows)))
        return dict(namespace=VERSION,principal_id=user,project_id=project["id"],app_id=aid,
            runtime_id=meta["runtime_id"],items=items,tools=list(TOOLS),
            scope="THIS_APP_ALL_INSTANCES",content_access=False)


def upstream(store,c,user,project,rid):
    for tool in TOOLS:
        store.authorize(c,user,project["runtime_id"],project["id"],rid,tool)
    if retirement_row(c,rid):
        raise DomainError("RESOURCE_UNAVAILABLE")


def authority_guard(store,c,user,meta,project,rid):
    upstream(store,c,user,project,rid)
    apps.authorize_source(store,c,user,project,meta["source_id"],meta["runtime_id"])
    if retirement_row(c,meta["source_id"]):
        raise DomainError("RESOURCE_UNAVAILABLE")


@graph.controlled
def options(store,user,aid,limits):
    with store.tx() as c:
        meta,project = scope(store,c,user,aid)
        draft,manifest,action,_ = apps.load_draft(store,c,user,aid,limits)
        require(len(draft["candidate"]["actions"]) == len(manifest.data_bindings) == 1
            and action.executor.ref == "data.aggregate_csv" and "generation" in draft["candidate"])
        ids = c.execute(select(resources.c.id).where(resources.c.project_id == project["id"],
            resources.c.format == "csv",resources.c.id != meta["source_id"])
            .order_by(resources.c.id).limit(64)).scalars().all()
        items=[]
        for rid in ids:
            try:
                upstream(store,c,user,project,rid)
                value=authorized_read(store,c,user,project["runtime_id"],project["id"],
                    "resource.read",dict(resource_id=rid))
            except DomainError as exc:
                if exc.code in {"PERMISSION_DENIED","GRANT_REVOKED","RESOURCE_UNAVAILABLE"}:
                    continue
                raise
            guidance=csv_column_options(value["content"])
            if guidance["error"] or not any(v["numeric"] for v in guidance["columns"]):
                continue
            rows=app_grants(c,meta,rid)
            name=c.execute(select(resources.c.name).where(resources.c.id == rid)).scalar_one()
            items.append(dict(resource_id=rid,name=name,source_hash=value["hash"],
                app_grants=rows,app_grants_fingerprint=fingerprint(rows),status=state(rows)))
        return dict(namespace=VERSION,principal_id=user,project_id=project["id"],app_id=aid,
            runtime_id=meta["runtime_id"],candidate_fingerprint=meta["fingerprint"],
            grant_version=lifecycle.grant_version(c,project["id"],user),items=items,
            tools=list(TOOLS),ttl_seconds=86400,scope="THIS_APP_ALL_INSTANCES",
            new_system_permissions=False,new_credentials=False,model_requests=0)


def record_for(meta,user,rid,body):
    return Record(request_key=body.request_key,request_fingerprint=fingerprint(body.model_dump()),
        principal_id=user,project_id=meta["project_id"],app_id=meta["id"],
        runtime_id=meta["runtime_id"],resource_id=rid)


def accepted(c,user,meta,key,kind):
    record,frozen=pair(c,user,meta["id"],kind,key,Record)
    if frozen is None:
        raise DomainError("VERSION_CONFLICT")
    require(record.request_key == key and record.principal_id == user
        and record.project_id == meta["project_id"] and record.app_id == meta["id"]
        and record.runtime_id == meta["runtime_id"] and frozen["record"] == record.model_dump()
        and frozen["namespace"] == VERSION and frozen["kind"] == kind
        and frozen["tools"] == list(TOOLS))
    require(frozen["fingerprint"] == fingerprint({k:v for k,v in frozen.items() if k != "fingerprint"}))
    require(frozen["scope"] == "THIS_APP_ALL_INSTANCES" and frozen["model_requests"] == 0
        and frozen["new_system_permissions"] is False and frozen["new_credentials"] is False)
    if kind == AUTH:
        require(len(frozen["grants"]) == 2 and {v["tool_ref"] for v in frozen["grants"]} == set(TOOLS)
            and frozen["ttl_seconds"] == 86400
            and all(v["revision"] == 1 and v["revoked"] is False
                and v["expires_at"] == frozen["created_at"]+86400 for v in frozen["grants"]))
    return record,frozen


def receipt(store,c,user,meta,project,record,frozen):
    rows=app_grants(c,meta,record.resource_id)
    scoped={r["id"]:r for r in rows}
    originals=frozen["grants"]
    for old in originals:
        require(old["principal_id"] == meta["runtime_id"] and old["project_id"] == project["id"]
            and old["resource_id"] == record.resource_id and old["tool_ref"] in TOOLS)
        now=scoped.get(old["id"])
        if now is not None:
            require(all(now[k] == old[k] for k in ("id","principal_id","project_id","resource_id","tool_ref","expires_at"))
                and now["revision"] >= old["revision"])
    group=[scoped[v["id"]] for v in originals if v["id"] in scoped]
    status="MISSING" if len(group) != len(originals) else "REVOKED" if any(v["revoked"] for v in group) else "EXPIRED" if any(v["expires_at"] <= time.time() for v in group) else "ACTIVE"
    effective=True
    try:
        authority_guard(store,c,user,meta,project,record.resource_id)
    except DomainError as exc:
        if exc.code not in {"PERMISSION_DENIED","GRANT_REVOKED","RESOURCE_UNAVAILABLE"}:
            raise
        effective=False
    return dict(receipt=frozen,receipt_status=status,app_grants=rows,
        app_grants_fingerprint=fingerprint(rows),app_material_status=state(rows),
        upstream_available=effective,content_access=False,scope="THIS_APP_ALL_INSTANCES")


@graph.controlled
def read(store,user,aid,key,kind):
    with store.tx() as c:
        meta,project=scope(store,c,user,aid)
        record,frozen=accepted(c,user,meta,key,kind)
        return receipt(store,c,user,meta,project,record,frozen)


def prior(c,user,aid,kind,key):
    return any(graph.lookup(c,user,aid,k,key) is not None for k in (kind,kind+"_seal"))


@contextmanager
def submission_tx(store,user,aid,body,kind):
    """Existing rejection-proof pattern: absent original intent, completed rollback."""
    failure=None
    absent=False
    meta=None
    try:
        with store.tx() as c:
            try:
                meta,project=scope(store,c,user,aid)
                absent=not prior(c,user,aid,kind,body.request_key)
                yield c,meta,project
            except DomainError as exc:
                failure=exc
                raise
    except DomainError as exc:
        if exc is failure and absent and meta is not None and exc.code in {
                "INVALID_INPUT","VERSION_CONFLICT","PERMISSION_DENIED","GRANT_REVOKED",
                "RESOURCE_UNAVAILABLE","UNSUPPORTED_CAPABILITY","LOCK_CONFLICT"}:
            exc.submission_rejection=dict(namespace=VERSION+".rejection",app_id=aid,
                project_id=meta["project_id"],principal_id=user,runtime_id=meta["runtime_id"],
                kind=kind,request_key=body.request_key,
                request_fingerprint=fingerprint(body.model_dump()),acceptance="NOT_ACCEPTED",
                previous_request="ABSENT",phase="TX_ROLLED_BACK")
        raise


def freeze(record,kind,rows):
    value=dict(namespace=VERSION,kind=kind,record=record.model_dump(),tools=list(TOOLS),
        grants=rows,created_at=rows[0]["expires_at"]-86400 if kind == AUTH else time.time(),
        ttl_seconds=86400 if kind == AUTH else 0,scope="THIS_APP_ALL_INSTANCES",model_requests=0,
        new_system_permissions=False,new_credentials=False)
    return {**value,"fingerprint":fingerprint(value)}


@graph.controlled
def authorize(store,user,aid,body,limits):
    with submission_tx(store,user,aid,body,AUTH) as (c,meta,project):
        if prior(c,user,aid,AUTH,body.request_key):
            record,frozen=accepted(c,user,meta,body.request_key,AUTH)
            require(record == record_for(meta,user,body.resource_id,body),"Original authorization request changed")
            return receipt(store,c,user,meta,project,record,frozen)
        require(c.execute(select(func.count()).select_from(graph.requests).where(
            graph.requests.c.app_id == aid,graph.requests.c.principal_id == user,
            graph.requests.c.kind == AUTH)).scalar_one() < 64,"Finite App material authorizations exhausted")
        require(meta["fingerprint"] == body.expected_candidate_fingerprint
            and lifecycle.grant_version(c,project["id"],user) == body.expected_grant_version)
        upstream(store,c,user,project,body.resource_id)
        draft,manifest,action,_=apps.load_draft(store,c,user,aid,limits)
        require(len(draft["candidate"]["actions"]) == len(manifest.data_bindings) == 1
            and action.executor.ref == "data.aggregate_csv" and "generation" in draft["candidate"]
            and body.resource_id != meta["source_id"])
        source=authorized_read(store,c,user,project["runtime_id"],project["id"],
            "resource.read",dict(resource_id=body.resource_id))
        require(source["format"] == "csv" and source["hash"] == body.expected_source_hash)
        guidance=csv_column_options(source["content"])
        require(not guidance["error"] and any(v["numeric"] for v in guidance["columns"]))
        rows=app_grants(c,meta,body.resource_id)
        require(len(rows) <= 62 and fingerprint(rows) == body.expected_app_grants_fingerprint and state(rows) == "INACTIVE",
            "Current App material authority changed; explicitly withdraw partial authority or read existing scope")
        authority_guard(store,c,user,meta,project,body.resource_id)
        record=record_for(meta,user,body.resource_id,body)
        created=apps.grant_csv_material(c,project["id"],meta["runtime_id"],body.resource_id)
        frozen=freeze(record,AUTH,created)
        remember(c,user,aid,AUTH,body.request_key,record,frozen)
        answer=receipt(store,c,user,meta,project,record,frozen)
        authority_guard(store,c,user,meta,project,body.resource_id)
        require(answer["upstream_available"],"Authorization expired before acceptance")
        return answer


@graph.controlled
def revoke(store,user,aid,body):
    with submission_tx(store,user,aid,body,REVOKE) as (c,meta,project):
        if prior(c,user,aid,REVOKE,body.request_key):
            record,frozen=accepted(c,user,meta,body.request_key,REVOKE)
            require(record == record_for(meta,user,body.resource_id,body))
            return receipt(store,c,user,meta,project,record,frozen)
        rows=app_grants(c,meta,body.resource_id)
        require(rows and fingerprint(rows) == body.expected_app_grants_fingerprint,
            "Exact App material Grant versions changed")
        require(c.execute(select(func.count()).select_from(graph.requests).where(
            graph.requests.c.app_id == aid,graph.requests.c.principal_id == user,
            graph.requests.c.kind == REVOKE)).scalar_one() < 64,"Finite App material withdrawals exhausted")
        # Whole vector verified before writes, original single-Grant CAS in one TX.
        for row in rows:
            if not row["revoked"]:
                apps.revoke_grant(store,c,user,row["id"],"revoke",row["revision"])
        record=record_for(meta,user,body.resource_id,body)
        frozen=freeze(record,REVOKE,rows)
        remember(c,user,aid,REVOKE,body.request_key,record,frozen)
        return receipt(store,c,user,meta,project,record,frozen)


def mount(app,store,limits,identity):
    dep=Depends(identity)
    path="/api/apps/{aid}/csv-material-access"

    @app.get(path)
    def context(aid:str,user=dep):
        return options(store,user,aid,limits)

    @app.get(path+"/state")
    def state_only(aid:str,user=dep):
        return control_state(store,user,aid)

    @app.post(path+"/authorizations",status_code=201)
    def grant(aid:str,body:Authorize,user=dep):
        return authorize(store,user,aid,body,limits)

    @app.get(path+"/authorizations/{key}")
    def authorization(aid:str,key:str,user=dep):
        return read(store,user,aid,key,AUTH)

    @app.post(path+"/revocations",status_code=201)
    def withdraw(aid:str,body:Revoke,user=dep):
        return revoke(store,user,aid,body)

    @app.get(path+"/revocations/{key}")
    def withdrawal(aid:str,key:str,user=dep):
        return read(store,user,aid,key,REVOKE)
