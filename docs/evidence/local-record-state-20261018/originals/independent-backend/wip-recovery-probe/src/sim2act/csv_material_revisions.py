"""Explicit authorized CSV replacement on the same adopted business instance.

This sealed overlay uses the original revision journal, CHECK and adoption CAS.
GoalCard provenance remains immutable; the effective binding and Run freeze the
new material separately. It grants no authority and introduces no executor.
"""
import copy
import json

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import apps
from . import csv_column_revisions as column
from . import csv_goal_revisions as revision
from . import delivery_graph_apps as graph
from .contracts import validate_action
from .db import fingerprint, resources
from .errors import DomainError
from .goals import validate_card_version
from .tools import authorized_read, csv_column_options

VERSION = "csv-material-revision.v1"
require = revision.require


def same(left,right):
    return fingerprint(left) == fingerprint(right)


class Preview(revision.Preview):
    expected_data_version: int = Field(ge=0)
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    source_hash: str = Field(pattern=graph.HASH)


def authorize_proposal(store,c,user,iid,body):
    meta = revision.source_gate(store,c,user,iid,current_head=True)
    project = store.lock_project(c,user,meta["project_id"])
    apps.authorize_source(store,c,user,project,body.resource_id,meta["runtime_id"])


def source_row(store, c, user, ctx, rid):
    project = store.lock_project(c,user,ctx["project_id"])
    apps.authorize_source(store,c,user,project,rid,ctx["runtime_id"])
    source = authorized_read(store,c,user,ctx["runtime_id"],ctx["project_id"],
        "resource.read",dict(resource_id=rid))
    require(source["format"] == "csv","Select an already authorized CSV material")
    return dict(id=rid,project_id=ctx["project_id"],format="csv",hash=source["hash"],content=source["content"])


def effective_rows(store,c,user,scope,draft):
    bindings = draft["candidate"]["manifest"]["data_bindings"]
    require(len(bindings) == 1)
    row = source_row(store,c,user,scope,bindings[0]["resource_ref"])
    require(row["hash"] == draft["candidate"]["source_hash"],"Effective CSV material changed")
    return [row]


def context(store,c,user,iid,limits):
    # The existing column context validates the exact adopted parent and Goal.
    ctx,release,saved = revision.context(store,c,user,iid,limits)
    require("parent" in ctx and ctx["goal_mode"] == "KEEP_ADOPTED_GOAL",
        "Replace material only on an adopted CSV binding with its unchanged Goal")
    ctx = {**ctx,"revision_contract":VERSION}
    return ctx,release,saved


def materials(store,c,user,ctx):
    # Identifier projection first. Names, hashes and columns are read only after
    # the existing owner/project/App-runtime intersection has authorized them.
    ids = c.execute(select(resources.c.id).where(resources.c.project_id == ctx["project_id"],
        resources.c.format == "csv").order_by(resources.c.id).limit(64)).scalars().all()
    values = []
    for rid in ids:
        if rid == ctx["source"]["resource_id"]:
            continue
        try:
            row = source_row(store,c,user,ctx,rid)
        except DomainError as exc:
            if exc.code in {"PERMISSION_DENIED","GRANT_REVOKED","RESOURCE_UNAVAILABLE"}:
                continue
            raise
        guidance = csv_column_options(row["content"])
        columns = [x["name"] for x in guidance["columns"] if x["numeric"]]
        if guidance["error"] or ctx["parent"]["column"] not in columns or row["hash"] == ctx["source"]["hash"]:
            continue
        name = c.execute(select(resources.c.name).where(resources.c.id == rid)).scalar_one()
        values.append(dict(resource_id=rid,name=name,hash=row["hash"],columns=columns))
    return values


def effective_next(base,goal,material,fixed_column,limits):
    draft,_,_,_ = column.effective_next(base,goal,fixed_column,limits)
    candidate = draft["candidate"]
    old = candidate["manifest"]["data_bindings"][0]["resource_ref"]
    new = material["resource_id"]
    require(old != new and candidate["source_hash"] != material["hash"])
    candidate["manifest"]["data_bindings"][0]["resource_ref"] = new
    for deps in (candidate["manifest"]["dependency_lock"],candidate["actions"][0]["dependencies"]):
        for dep in deps:
            if dep["kind"] == "resource":
                require(dep["ref"] == old)
                dep["ref"] = new
    for spec in (candidate["manifest"],candidate["actions"][0]):
        for permission in spec["permission_requirements"]:
            require(permission["resource_ref"] == old)
            permission["resource_ref"] = new
    candidate["source_hash"] = material["hash"]
    manifest,report = apps.preflight(json.dumps(candidate["manifest"]),candidate["actions"],limits)
    return {**draft,"fingerprint":fingerprint(candidate)},manifest,validate_action(json.dumps(candidate["actions"][0])),report


def replacement_graph(store,c,draft,manifest,rows,parent_graph,saved,ctx,body,limits):
    previous = copy.deepcopy(parent_graph)
    old = "source:" + ctx["source"]["resource_id"]
    new = "source:" + body.resource_id
    require(old in previous["stable_ids"] and new not in previous["stable_ids"])
    # A resource has a new server-owned identity; every unrelated node keeps its
    # stable ID. The canonical original graph and human locks are not rewritten.
    previous["stable_ids"].pop(old)
    previous["stable_ids"][new] = "node_" + fingerprint([VERSION,ctx["instance_id"],
        ctx["release_id"],body.request_key,new])[:32]
    previous["source_versions"].pop(old)
    previous["source_versions"][new] = dict(revision=0,content_fingerprint=None)
    return column.definition_graph(store,c,draft,manifest,rows,previous,saved,limits)


def calculate(store,c,user,ctx,release,saved,body,limits):
    require(ctx["revision_contract"] == VERSION and ctx["instance_revision"] == body.expected_revision
        and ctx["data_version"] == body.expected_data_version
        and ctx["release_fingerprint"] == body.expected_release_fingerprint == release["fingerprint"]
        and ctx["graph_fingerprint"] == body.expected_graph_fingerprint
        and ctx["goal"]["version"] == body.goal_version and ctx["goal"]["fingerprint"] == body.goal_fingerprint)
    parent_release,base,manifest,_,_,seed = column.parent(store,c,user,ctx["release_id"],limits,ctx)
    rows = effective_rows(store,c,user,ctx,base)
    parent_graph = column.definition_graph(store,c,base,manifest,rows,seed,saved,limits)
    meta = column.parent_metadata(parent_release,base,manifest,parent_graph)
    require(same(meta,ctx["parent"]) and same(ctx["goal"],meta["goal"]) and ctx["goal_mode"] == "KEEP_ADOPTED_GOAL"
        and same(ctx["source"],dict(resource_id=rows[0]["id"],hash=rows[0]["hash"]))
        and release["snapshot"]["draft"]["fingerprint"] == ctx["draft_fingerprint"]
        and saved["app_id"] == ctx["app_id"] and saved["project_id"] == ctx["project_id"]
        and saved["principal_id"] == ctx["principal_id"] == user and saved["runtime_id"] == ctx["runtime_id"]
        and saved["authorization_fingerprint"] == ctx["authorization_fingerprint"]
        and saved["graph_revision"] == ctx["graph_revision"])
    goal = validate_card_version(store,c,user,ctx["goal"]["card_id"],body.goal_version)
    require(same(goal["snapshot"],ctx["goal"]["snapshot"]) and goal["fingerprint"] == body.goal_fingerprint)
    require(body.column == body.baseline_column == meta["column"],"A material replacement keeps the adopted numeric column")
    row = source_row(store,c,user,ctx,body.resource_id)
    require(row["id"] != ctx["source"]["resource_id"] and row["hash"] == body.source_hash
        and row["hash"] != ctx["source"]["hash"],"Select a different authorized CSV and freeze its current hash")
    guidance = csv_column_options(row["content"])
    require(not guidance["error"] and any(x["name"] == body.column and x["numeric"] for x in guidance["columns"]),
        "The new CSV must contain the adopted finite numeric column")
    nodes = [n for n in parent_graph["graph"]["nodes"] if n["key"] == "source:" + ctx["source"]["resource_id"]]
    require(len(nodes) == 1)
    plan = graph.core.plan_change(parent_graph["graph"],parent_graph["graph"]["graph_fingerprint"],
        dict(project_id=ctx["project_id"],app_id=ctx["app_id"],request_key=body.request_key,
            changes=[dict(node_id=n["id"],expected_revision=n["revision"],expected_content_fingerprint=n["content_fingerprint"]) for n in nodes]),parent_graph["context"])
    require(plan["revalidation_scope"] != "PROJECT","Unknown project dependencies exceed this finite replacement")
    material = dict(resource_id=row["id"],hash=row["hash"],format="csv",revision=1)
    draft,next_manifest,_,report = effective_next(base,ctx["goal"],material,body.column,limits)
    effective_graph = replacement_graph(store,c,draft,next_manifest,[row],parent_graph,saved,ctx,body,limits)
    value = dict(namespace=VERSION,request_key=body.request_key,context=ctx,impact=plan,
        baseline_graph=saved,parent_graph=parent_graph,effective_graph=effective_graph,material=material,
        effective_candidate=draft["candidate"],effective_fingerprint=draft["fingerprint"],
        spec_revision=next_manifest.revision,plan_fingerprint=fingerprint(report),
        baseline_input=dict(column=body.baseline_column),input=dict(column=body.column),model_requests=0,
        semantic_status="UNKNOWN",owner_acceptance="PENDING",formal_publication_enabled=False)
    return {**value,"preview_fingerprint":fingerprint(value)}


def load(store,c,user,iid,key,limits,body,value,current):
    ctx = value["context"]
    require(ctx.get("revision_contract") == VERSION and ctx["instance_id"] == iid and ctx["principal_id"] == user
        and same(ctx["limits"],limits.model_dump()) and type(ctx["goal"]["version"]) is int
        and all(type(ctx[k]) is int for k in ("instance_revision","data_version","graph_revision","original_goal_version")))
    with column.parent_scope(c,"preview:"+iid+":"+key):
        meta = column.release_scope(store,c,user,ctx["release_id"],ctx)
        require(meta["fingerprint"] == ctx["release_fingerprint"])
        base = column.parent(store,c,user,ctx["release_id"],limits,ctx)[0]
        require(same(calculate(store,c,user,ctx,base,value["baseline_graph"],body,limits),value),
            "Frozen CSV material replacement changed")
    if current:
        fresh,actual,saved = context(store,c,user,iid,limits)
        require(same(fresh,ctx) and actual["id"] == base["id"] and same(saved,value["baseline_graph"]),
            "Current parent, Goal, authority, locks or instance changed")
    return body,value


def bound(store,c,user,release,limits,snapshot,ref,value,current):
    require(value["namespace"] == VERSION)
    if ref.purpose == "CHECK":
        require(release["id"] == value["context"]["release_id"]
            and release["fingerprint"] == value["context"]["release_fingerprint"]
            and snapshot is not None and snapshot["instance_id"] != ref.instance_id)
    else:
        require(release["snapshot"].get(revision.SOURCE,{}).get("namespace") == VERSION
            and release["snapshot"][revision.SOURCE]["reference"] == ref.model_dump())
        if current:
            revision.eligibility(store,c,user,value,limits)
    _,base,_,_,_,_ = column.parent(store,c,user,value["context"]["release_id"],limits,value["context"])
    answer = effective_next(base,value["context"]["goal"],value["material"],value["input"]["column"],limits)
    require(answer[0]["fingerprint"] == value["effective_fingerprint"] and same(answer[0]["candidate"],value["effective_candidate"]))
    return answer


def validate_snapshot(store,c,user,snapshot,limits,current):
    origin = snapshot[revision.SOURCE]
    require(set(origin) == {"namespace","reference","check_fingerprint","goal","input","effective_fingerprint","parent","spec_revision"}
        and origin["namespace"] == VERSION)
    ref = revision.Reference.model_validate(origin["reference"])
    require(ref.purpose == "USE")
    value,proof = revision.checked(store,c,user,ref.instance_id,ref.preview_key,limits,current=current)
    require(value["namespace"] == VERSION and ref == revision.reference(ref.instance_id,ref.preview_key,value,"USE")
        and proof["check_fingerprint"] == origin["check_fingerprint"] and same(snapshot["check_evidence"],proof)
        and same(origin["goal"],value["context"]["goal"]) and same(origin["input"],value["input"])
        and same(origin["parent"],value["context"]["parent"]) and type(origin["spec_revision"]) is int
        and origin["spec_revision"] == value["spec_revision"] and origin["effective_fingerprint"] == value["effective_fingerprint"]
        and snapshot["draft"]["fingerprint"] == value["context"]["draft_fingerprint"])
    return value


def mount(app,store,limits,identity):
    dep = Depends(identity)
    path = "/api/internal/instances/{iid}/csv-material-revisions"

    @app.get(path + "/context")
    def baseline(iid:str,user=dep):
        with store.tx() as c:
            ctx,_,_ = context(store,c,user,iid,limits)
            return dict(context=ctx,materials=materials(store,c,user,ctx))

    @app.post(path + "/previews",status_code=201)
    def propose(iid:str,body:Preview,user=dep):
        return revision.preview(store,user,iid,body,limits)
