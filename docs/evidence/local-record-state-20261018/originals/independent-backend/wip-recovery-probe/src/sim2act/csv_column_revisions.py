"""Finite successive CSV bindings, with immutable historical parent Releases.

This is a version of the existing revision contract, not an executor or grant.
The original v1 reconstruction is deliberately kept in csv_goal_revisions.
"""
import copy
import json
import re
import threading
from contextlib import contextmanager

from sqlalchemy import select

from . import apps, lifecycle
from . import csv_goal_revisions as revision
from . import delivery_graph_apps as graph
from .contracts import validate_action
from .db import fingerprint, goal_cards, internal_releases
from .goals import validate_card_version
from .tools import csv_column_options

VERSION = "csv-column-revision.v2"
MAX_SPEC_REVISION = 8
require = revision.require


@contextmanager
def parent_scope(c, rid):
    stack = c.info.setdefault("csv_revision_parent_stack", [])
    require(rid not in stack and (not rid.startswith("irelease_") or
        sum(x.startswith("irelease_") for x in stack) < MAX_SPEC_REVISION),
        "Cyclic or over-limit CSV parent Release chain")
    stack.append(rid)
    try:
        yield
    finally:
        stack.pop()
        if not stack:
            c.info.pop("csv_revision_parent_stack", None)


def definition_graph(store, c, draft, manifest, rows, previous, authority, limits):
    """Pure overlay of verified specs and frozen current locks/authority.

    Nothing is written to the canonical draft graph. Historical reconstruction
    uses the saved authority context, never today's locks or moving pointer.
    """
    keys, external = graph.logical(store,c,draft,manifest,rows)
    versions = {}
    for key, definition in external.items():
        if key.startswith(("rule:","check:")):
            # Registered software was frozen by the canonical graph anchor.
            # Reconstructing history must not hash today's Python registry.
            versions[key] = copy.deepcopy(authority["source_versions"][key])
            continue
        fp = fingerprint(definition)
        old = previous["source_versions"][key]
        versions[key] = dict(revision=old["revision"] + (old["content_fingerprint"] != fp),content_fingerprint=fp)
    ctx = copy.deepcopy(authority["context"])
    # Rows were read through the existing exact source authorization gateway.
    # A sealed material overlay may bind B while the immutable canonical graph
    # still describes A. Extend only this derived context, never its anchor or
    # authorization snapshot, and keep old same-material hashes unchanged.
    if not {row["id"] for row in rows} <= set(ctx["resource_ids"]):
        ctx["resource_ids"] = sorted(set(ctx["resource_ids"]) | {row["id"] for row in rows})
    ctx.update(source_versions=versions,graph_fingerprint=None,
        node_revisions={key:rev if rev is not None else versions[key]["revision"] for key,rev in keys.items()})
    ids = {key:previous["stable_ids"][key] for key in keys}
    value = graph.core.derive_manifest_graph(manifest.model_dump(),draft["candidate"]["actions"],versions,ids,ctx,limits)
    ctx["graph_fingerprint"] = value["graph_fingerprint"]
    return {**copy.deepcopy(previous),"candidate_fingerprint":draft["fingerprint"],"graph":value,
        "context":ctx,"source_versions":versions,
        "authorization_fingerprint":authority["authorization_fingerprint"],
        "authorization_revision":authority["authorization_revision"],"graph_revision":authority["graph_revision"]}


def release_scope(store,c,user,rid,scope):
    require(isinstance(rid,str) and re.fullmatch(r"irelease_[0-9a-f]{32}",rid),"Malformed parent Release identity")
    meta = c.execute(select(internal_releases.c.project_id,internal_releases.c.fingerprint,
        internal_releases.c.snapshot["draft"]["id"].as_string().label("app_id"),
        internal_releases.c.snapshot["draft"]["runtime_id"].as_string().label("runtime_id"),
        internal_releases.c.snapshot[revision.SOURCE]["reference"]["instance_id"].as_string().label("iid"),
        internal_releases.c.snapshot[revision.SOURCE]["reference"]["preview_key"].as_string().label("key"))
        .where(internal_releases.c.id == rid,internal_releases.c.principal_id == user)).mappings().first()
    require(meta is not None and meta["project_id"] == scope["project_id"] and meta["app_id"] == scope["app_id"]
        and meta["runtime_id"] == scope["runtime_id"] and meta["iid"] == scope["instance_id"],
        "Parent Release scope changed")
    revision.source_gate(store,c,user,meta["iid"],meta["key"])
    return meta


def parent_cache(c):
    tx,epoch = c.get_transaction(),c.info.get("source_proof_write_epoch",0)
    cache = c.info.get("csv_parent_proofs")
    if cache is None or cache["transaction"] is not tx or cache["epoch"] != epoch:
        cache = dict(transaction=tx,epoch=epoch,items={})
        c.info["csv_parent_proofs"] = cache
    return cache["items"]


def parent(store, c, user, rid, limits, scope):
    meta = release_scope(store,c,user,rid,scope)
    with parent_scope(c,rid):
        key = (threading.get_ident(),user,rid,fingerprint(limits.model_dump()))
        saved = parent_cache(c).get(key)
        if saved is not None:
            require(saved["result"][0]["fingerprint"] == meta["fingerprint"])
            store.recheck_proof_authorities(c,saved)
            lifecycle.validate_source_bytes(store,c,user,saved["result"][0]["snapshot"]["draft"])
            require(parent_cache(c).get(key) is saved,"Parent proof changed during authority recheck")
            return copy.deepcopy(saved["result"])
        transaction,epoch = c.get_transaction(),c.info.get("source_proof_write_epoch",0)
        with store.proof_authorities(c) as authorities:
            release = lifecycle.read_release(store,c,user,rid,limits)
            require(release["id"] == rid and release["fingerprint"] == meta["fingerprint"])
            require(revision.SOURCE in release["snapshot"],"Continue only an explicitly adopted CSV revision")
            origin = release["snapshot"][revision.SOURCE]
            ref = revision.Reference.model_validate(origin["reference"])
            _,value = revision.load_preview(store,c,user,ref.instance_id,ref.preview_key,limits)
            draft,manifest,action,report = revision.bound(store,c,user,release,limits,current=False)
            require(action.executor.ref == "data.aggregate_csv" and len(draft["candidate"]["actions"]) == 1)
            n = manifest.revision
            require(type(n) is int and n == action.revision == manifest.action_bindings[0].revision
                and 2 <= n < MAX_SPEC_REVISION,"CSV specification revision limit reached")
            if value["namespace"] == revision.VERSION:
                seed = value["baseline_graph"]
            else:
                revision.extension(value["namespace"])
                seed = value["effective_graph"]
            result = (dict(release),draft,manifest,action,report,seed)
        cache = parent_cache(c)
        if (c.get_transaction() is transaction and c.info.get("source_proof_write_epoch",0) == epoch
                and len(cache) < MAX_SPEC_REVISION):
            cache[key] = dict(result=copy.deepcopy(result),_call_authorities=tuple(authorities))
        return result


def parent_metadata(release,draft,manifest,parent_graph):
    source = release["snapshot"][revision.SOURCE]
    column = manifest.input_schema["properties"]["column"]["enum"]
    require(len(column) == 1 and column == [source["input"]["column"]])
    value = dict(release_id=release["id"],release_fingerprint=release["fingerprint"],
        effective_fingerprint=draft["fingerprint"],spec_revision=manifest.revision,
        goal=copy.deepcopy(source["goal"]),column=column[0],
        reference=copy.deepcopy(source["reference"]),graph_fingerprint=parent_graph["graph"]["graph_fingerprint"])
    from .csv_material_revisions import VERSION as material_version
    if source["namespace"] == material_version or source.get("parent",{}).get("material_revision",False):
        value["material_revision"] = True
    return value


def context(store,c,user,iid,limits,inst,release):
    require(not revision.pins(c,user,iid),"An isolated CHECK cannot start a business revision")
    origin = release["snapshot"][revision.SOURCE]
    require(origin["reference"]["instance_id"] == iid,"Parent must belong to this original business instance")
    scope = dict(instance_id=iid,project_id=inst["project_id"],app_id=inst["source_app_id"],runtime_id=inst["runtime_id"])
    actual,draft,manifest,_,_,seed = parent(store,c,user,release["id"],limits,scope)
    require(actual["fingerprint"] == release["fingerprint"])
    saved = graph.current(store,c,user,inst["project_id"],inst["source_app_id"],limits)
    from .csv_material_revisions import effective_rows
    rows = effective_rows(store,c,user,scope,draft)
    parent_graph = definition_graph(store,c,draft,manifest,rows,seed,saved,limits)
    frozen_parent = parent_metadata(release,draft,manifest,parent_graph)
    old = frozen_parent["goal"]
    card = c.execute(select(goal_cards).where(goal_cards.c.id == old["card_id"])).mappings().one()
    new = validate_card_version(store,c,user,card["id"],card["version"])
    require(card["version"] in (old["version"],old["version"]+1),"Only the adopted Goal or its explicit next version is supported")
    require(new["snapshot"]["resource_snapshots"] == old["snapshot"]["resource_snapshots"]
        and new["snapshot"]["content"]["resource_refs"] == old["snapshot"]["content"]["resource_refs"],
        "A column revision cannot replace Goal materials")
    source = rows[0]
    guidance = csv_column_options(source["content"])
    require(not guidance["error"])
    root = release["snapshot"]["draft"]
    value = dict(revision_contract=VERSION,instance_id=iid,principal_id=user,project_id=inst["project_id"],
        app_id=inst["source_app_id"],runtime_id=inst["runtime_id"],release_id=release["id"],
        release_fingerprint=release["fingerprint"],draft_fingerprint=root["fingerprint"],
        instance_revision=inst["revision"],data_version=inst["data_version"],
        source=dict(resource_id=source["id"],hash=source["hash"]),
        goal=dict(card_id=card["id"],version=card["version"],fingerprint=new["fingerprint"],snapshot=new["snapshot"]),
        goal_mode="KEEP_ADOPTED_GOAL" if card["version"] == old["version"] else "EXPLICIT_NEXT_GOAL",
        original_goal_version=root["candidate"]["generation"]["goal_version"],parent=frozen_parent,
        graph_fingerprint=saved["graph"]["graph_fingerprint"],graph_revision=saved["graph_revision"],
        authorization_fingerprint=saved["authorization_fingerprint"],
        columns=[x["name"] for x in guidance["columns"] if x["numeric"]],limits=limits.model_dump())
    return value,release,saved


def effective_next(base,goal,column,limits):
    candidate = copy.deepcopy(base["candidate"])
    n = candidate["manifest"]["revision"]
    require(type(n) is int and 2 <= n < MAX_SPEC_REVISION
        and n == candidate["actions"][0]["revision"] == candidate["manifest"]["action_bindings"][0]["revision"])
    candidate["goal"] = copy.deepcopy(goal["snapshot"]["content"])
    candidate["manifest"]["revision"] = candidate["actions"][0]["revision"] = n+1
    candidate["manifest"]["action_bindings"][0]["revision"] = n+1
    for schema in (candidate["manifest"]["input_schema"],candidate["actions"][0]["input_schema"]):
        schema["properties"]["column"] = dict(type="string",enum=[column])
    manifest,report = apps.preflight(json.dumps(candidate["manifest"]),candidate["actions"],limits)
    return {**copy.deepcopy(base),"candidate":candidate,"fingerprint":fingerprint(candidate)},manifest,validate_action(json.dumps(candidate["actions"][0])),report


def calculate(store,c,user,ctx,release,saved,body,limits):
    require(ctx["revision_contract"] == VERSION and ctx["release_id"] == release["id"]
        and ctx["release_fingerprint"] == release["fingerprint"] == body.expected_release_fingerprint
        and ctx["instance_revision"] == body.expected_revision and ctx["graph_fingerprint"] == body.expected_graph_fingerprint
        and ctx["goal"]["version"] == body.goal_version and ctx["goal"]["fingerprint"] == body.goal_fingerprint)
    parent_release,base,manifest,_,_,seed = parent(store,c,user,release["id"],limits,ctx)
    require(parent_release["snapshot"][revision.SOURCE]["reference"]["instance_id"] == ctx["instance_id"])
    from .csv_material_revisions import effective_rows
    rows = effective_rows(store,c,user,ctx,base)
    parent_graph = definition_graph(store,c,base,manifest,rows,seed,saved,limits)
    meta = parent_metadata(parent_release,base,manifest,parent_graph)
    require(meta == ctx["parent"] and meta["release_id"] == ctx["release_id"]
        and release["snapshot"]["draft"]["fingerprint"] == ctx["draft_fingerprint"]
        and saved["app_id"] == ctx["app_id"] and saved["project_id"] == ctx["project_id"]
        and saved["principal_id"] == ctx["principal_id"] == user and saved["runtime_id"] == ctx["runtime_id"]
        and saved["authorization_fingerprint"] == ctx["authorization_fingerprint"]
        and saved["graph_revision"] == ctx["graph_revision"])
    goal = ctx["goal"]
    expected = validate_card_version(store,c,user,goal["card_id"],goal["version"])
    require(goal["card_id"] == meta["goal"]["card_id"] and expected["snapshot"] == goal["snapshot"]
        and expected["fingerprint"] == goal["fingerprint"]
        and goal["snapshot"]["resource_snapshots"] == meta["goal"]["snapshot"]["resource_snapshots"]
        and goal["snapshot"]["content"]["resource_refs"] == meta["goal"]["snapshot"]["content"]["resource_refs"])
    same = goal == meta["goal"]
    require((same and ctx["goal_mode"] == "KEEP_ADOPTED_GOAL") or (
        not same and ctx["goal_mode"] == "EXPLICIT_NEXT_GOAL" and goal["version"] == meta["goal"]["version"]+1))
    require(body.baseline_column == meta["column"] and body.column in ctx["columns"]
        and body.column != body.baseline_column,"Select a new numeric column from the adopted binding")
    nodes = [n for n in parent_graph["graph"]["nodes"] if n["key"] == "action:aggregate" or (not same and n["kind"] == "GOAL")]
    require(len(nodes) == (1 if same else 2))
    plan = graph.core.plan_change(parent_graph["graph"],parent_graph["graph"]["graph_fingerprint"],
        dict(project_id=ctx["project_id"],app_id=ctx["app_id"],request_key=body.request_key,
            changes=[dict(node_id=n["id"],expected_revision=n["revision"],expected_content_fingerprint=n["content_fingerprint"]) for n in nodes]),parent_graph["context"])
    require(plan["revalidation_scope"] != "PROJECT","Unknown project dependencies exceed this finite revision")
    draft,next_manifest,_,report = effective_next(base,goal,body.column,limits)
    effective_graph = definition_graph(store,c,draft,next_manifest,rows,parent_graph,saved,limits)
    value = dict(namespace=VERSION,request_key=body.request_key,context=ctx,impact=plan,
        baseline_graph=saved,parent_graph=parent_graph,effective_graph=effective_graph,
        effective_candidate=draft["candidate"],effective_fingerprint=draft["fingerprint"],
        spec_revision=next_manifest.revision,plan_fingerprint=fingerprint(report),
        baseline_input=dict(column=body.baseline_column),input=dict(column=body.column),model_requests=0,
        semantic_status="UNKNOWN",owner_acceptance="PENDING",formal_publication_enabled=False)
    return {**value,"preview_fingerprint":fingerprint(value)}


def load(store,c,user,iid,key,limits,body,value,current):
    ctx = value["context"]
    require(ctx.get("revision_contract") == VERSION and ctx["instance_id"] == iid
        and ctx["principal_id"] == user and ctx["limits"] == limits.model_dump()
        and all(type(ctx[k]) is int for k in ("instance_revision","data_version","graph_revision","original_goal_version"))
        and type(ctx["goal"]["version"]) is int)
    with parent_scope(c,"preview:"+iid+":"+key):
        meta = release_scope(store,c,user,ctx["release_id"],ctx)
        require(meta["fingerprint"] == ctx["release_fingerprint"])
        base = parent(store,c,user,ctx["release_id"],limits,ctx)[0]
        require(calculate(store,c,user,ctx,base,value["baseline_graph"],body,limits) == value,
            "Frozen successive CSV definition changed")
    if current:
        fresh,actual,saved = revision.context(store,c,user,iid,limits)
        require(fresh == ctx and actual["id"] == base["id"] and saved == value["baseline_graph"],
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
    _,base,_,_,_,_ = parent(store,c,user,value["context"]["release_id"],limits,value["context"])
    answer = effective_next(base,value["context"]["goal"],value["input"]["column"],limits)
    require(answer[0]["fingerprint"] == value["effective_fingerprint"]
        and answer[0]["candidate"] == value["effective_candidate"])
    return answer


def validate_snapshot(store,c,user,snapshot,limits,current):
    origin = snapshot[revision.SOURCE]
    require(set(origin) == {"namespace","reference","check_fingerprint","goal","input","effective_fingerprint","parent","spec_revision"}
        and origin["namespace"] == VERSION)
    ref = revision.Reference.model_validate(origin["reference"])
    require(ref.purpose == "USE")
    value,proof = revision.checked(store,c,user,ref.instance_id,ref.preview_key,limits,current=current)
    require(value["namespace"] == VERSION and ref == revision.reference(ref.instance_id,ref.preview_key,value,"USE")
        and proof["check_fingerprint"] == origin["check_fingerprint"]
        and snapshot["check_evidence"] == proof and origin["goal"] == value["context"]["goal"]
        and origin["input"] == value["input"] and origin["parent"] == value["context"]["parent"]
        and type(origin["spec_revision"]) is int and origin["spec_revision"] == value["spec_revision"]
        and origin["effective_fingerprint"] == value["effective_fingerprint"]
        and snapshot["draft"]["fingerprint"] == value["context"]["draft_fingerprint"])
    return value
