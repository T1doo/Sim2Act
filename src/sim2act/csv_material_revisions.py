"""Explicit authorized CSV replacement on the same adopted business instance.

This sealed overlay uses the original revision journal, CHECK and adoption CAS.
GoalCard provenance remains immutable; the effective binding and Run freeze the
new material separately. It grants no authority and introduces no executor.
"""
import copy
import json
import threading

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import apps, lifecycle
from . import csv_column_revisions as column
from . import csv_goal_revisions as revision
from . import delivery_graph_apps as graph
from .contracts import validate_action
from .db import fingerprint, internal_releases, resources
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
    ctx,release,saved = revision.context(store,c,user,iid,limits)
    ctx = {**ctx,"revision_contract":VERSION}
    if revision.SOURCE not in release["snapshot"]:
        # The original Release has no fixed column yet. The proposal will
        # explicitly freeze one common numeric column, without a fake revision.
        ctx.update(initial_material=True,goal_mode="KEEP_ORIGINAL_GOAL")
        *_,meta,_rows = source_definition(store,c,user,ctx,saved,limits)
        ctx["parent"] = meta
    else:
        require(ctx["goal_mode"] == "KEEP_ADOPTED_GOAL",
            "Keep the exact adopted Goal when replacing material")
    return ctx,release,saved


def source_definition(store,c,user,ctx,saved,limits):
    if ctx.get("initial_material") is True:
        scope = revision.source_gate(store,c,user,ctx["instance_id"])
        require(all(scope[k] == ctx[k] for k in ("project_id","runtime_id")) and scope["source_app_id"] == ctx["app_id"])
        meta = c.execute(select(internal_releases.c.project_id,
            internal_releases.c.fingerprint,
            internal_releases.c.snapshot["draft"]["id"].as_string().label("app_id"),
            internal_releases.c.snapshot["draft"]["runtime_id"].as_string().label("runtime_id"))
            .where(internal_releases.c.id == ctx["release_id"],internal_releases.c.principal_id == user)).mappings().first()
        require(meta is not None and all(meta[k] == ctx[k] for k in ("project_id","app_id","runtime_id"))
            and meta["fingerprint"] == ctx["release_fingerprint"])
        # Reuse the existing same-transaction proof cache. A write invalidates
        # it; every hit still rechecks live authority and original source bytes.
        key = (threading.get_ident(),user,"original-material:"+ctx["release_id"],
            fingerprint(dict(context=ctx,graph=saved,limits=limits.model_dump())))
        cached = column.parent_cache(c).get(key)
        if cached is not None:
            store.recheck_proof_authorities(c,cached)
            lifecycle.validate_source_bytes(store,c,user,cached["result"][0]["snapshot"]["draft"])
            require(column.parent_cache(c).get(key) is cached,"Original material proof changed during authority recheck")
            return copy.deepcopy(cached["result"])
        transaction,epoch = c.get_transaction(),c.info.get("source_proof_write_epoch",0)
        with store.proof_authorities(c) as authorities:
            result = _original_definition(store,c,user,ctx,saved,limits)
        cache = column.parent_cache(c)
        if (c.get_transaction() is transaction and c.info.get("source_proof_write_epoch",0) == epoch
                and len(cache) < column.MAX_SPEC_REVISION):
            cache[key] = dict(result=copy.deepcopy(result),_call_authorities=tuple(authorities))
        return result
    require("initial_material" not in ctx,"Malformed original-material marker")
    actual,base,manifest,_,_,seed = column.parent(store,c,user,ctx["release_id"],limits,ctx)
    rows = effective_rows(store,c,user,ctx,base)
    parent_graph = column.definition_graph(store,c,base,manifest,rows,seed,saved,limits)
    return actual,base,manifest,parent_graph,column.parent_metadata(actual,base,manifest,parent_graph),rows


def _original_definition(store,c,user,ctx,saved,limits):
    actual = lifecycle.read_release(store,c,user,ctx["release_id"],limits)
    require(revision.SOURCE not in actual["snapshot"]
        and "execution_source" not in actual["snapshot"] and "natural_logic_source" not in actual["snapshot"])
    base,manifest,action,_ = apps.validate_frozen_candidate(store,c,user,actual["snapshot"]["draft"],limits)
    require(manifest.revision == action.revision == manifest.action_bindings[0].revision == 1
        and action.executor.ref == "data.aggregate_csv")
    origin = base["candidate"]["generation"]
    goal = dict(card_id=origin["goal_card_id"],version=origin["goal_version"],
        fingerprint=origin["goal_fingerprint"],snapshot=origin["goal_snapshot"])
    require(same(ctx["goal"],goal) and ctx["goal_mode"] == "KEEP_ORIGINAL_GOAL"
        and actual["id"] == ctx["release_id"] and actual["fingerprint"] == ctx["release_fingerprint"]
        and base["id"] == ctx["app_id"] and base["project_id"] == ctx["project_id"]
        and base["runtime_id"] == ctx["runtime_id"] and base["fingerprint"] == ctx["draft_fingerprint"])
    rows = effective_rows(store,c,user,ctx,base)
    parent_graph = column.definition_graph(store,c,base,manifest,rows,saved,saved,limits)
    require(same(parent_graph,saved),"Original CSV graph definition changed")
    meta = dict(kind="ORIGINAL_CSV_RELEASE",release_id=actual["id"],release_fingerprint=actual["fingerprint"],
        effective_fingerprint=base["fingerprint"],spec_revision=1,goal=goal,column=None,reference=None,
        graph_fingerprint=parent_graph["graph"]["graph_fingerprint"])
    return actual,base,manifest,parent_graph,meta,rows


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
        common = set(columns) & set(ctx["columns"])
        fixed = ctx["parent"]["column"]
        if guidance["error"] or not common or (fixed is not None and fixed not in columns) or row["hash"] == ctx["source"]["hash"]:
            continue
        name = c.execute(select(resources.c.name).where(resources.c.id == rid)).scalar_one()
        values.append(dict(resource_id=rid,name=name,hash=row["hash"],columns=columns))
    return values


def effective_next(base,goal,material,fixed_column,limits):
    build = revision.effective if base["candidate"]["manifest"]["revision"] == 1 else column.effective_next
    draft,_,_,_ = build(base,goal,fixed_column,limits)
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
    _,base,manifest,parent_graph,meta,rows = source_definition(store,c,user,ctx,saved,limits)
    require(same(meta,ctx["parent"]) and same(ctx["goal"],meta["goal"])
        and ctx["goal_mode"] == ("KEEP_ORIGINAL_GOAL" if ctx.get("initial_material") is True else "KEEP_ADOPTED_GOAL")
        and same(ctx["source"],dict(resource_id=rows[0]["id"],hash=rows[0]["hash"]))
        and release["snapshot"]["draft"]["fingerprint"] == ctx["draft_fingerprint"]
        and saved["app_id"] == ctx["app_id"] and saved["project_id"] == ctx["project_id"]
        and saved["principal_id"] == ctx["principal_id"] == user and saved["runtime_id"] == ctx["runtime_id"]
        and saved["authorization_fingerprint"] == ctx["authorization_fingerprint"]
        and saved["graph_revision"] == ctx["graph_revision"])
    goal = validate_card_version(store,c,user,ctx["goal"]["card_id"],body.goal_version)
    require(same(goal["snapshot"],ctx["goal"]["snapshot"]) and goal["fingerprint"] == body.goal_fingerprint)
    require(body.column == body.baseline_column and body.column in ctx["columns"]
        and (ctx.get("initial_material") is True or body.column == meta["column"]),
        "Explicitly keep one numeric column while replacing material")
    row = source_row(store,c,user,ctx,body.resource_id)
    require(row["id"] != ctx["source"]["resource_id"] and row["hash"] == body.source_hash
        and row["hash"] != ctx["source"]["hash"],"Select a different authorized CSV and freeze its current hash")
    guidance = csv_column_options(row["content"])
    require(not guidance["error"] and any(x["name"] == body.column and x["numeric"] for x in guidance["columns"]),
        "The new CSV must contain the adopted finite numeric column")
    # The first Release's open column input becomes a fixed enum as well.
    # Explicitly include that ACTION change so its manual lock is respected.
    initial = ctx.get("initial_material") is True
    nodes = [n for n in parent_graph["graph"]["nodes"] if n["key"] == "source:" + ctx["source"]["resource_id"]
        or (initial and n["key"] == "action:aggregate")]
    require(len(nodes) == 1 + initial)
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
        if ctx.get("initial_material") is True:
            base = source_definition(store,c,user,ctx,value["baseline_graph"],limits)[0]
        else:
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
    if value["context"].get("initial_material") is True:
        _,base,_,_,_,_ = source_definition(store,c,user,value["context"],value["baseline_graph"],limits)
    else:
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
