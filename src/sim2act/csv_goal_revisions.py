"""One explicit same-card CSV Goal/column revision on the original Worker.

The original candidate, generation ledger, runtime and Grants never change.
Independent proposal/CHECK seals authorize a finite effective definition; a
Release keeps its original draft and points at that proof, never at a moving
business-instance pointer. No language interpretation or model is involved.
"""
import copy
import json
from contextlib import contextmanager

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import apps, lifecycle
from . import delivery_graph_apps as graph
from .contracts import Strict, validate_action
from .db import (
    delivery_graph_requests as requests,
)
from .db import (
    events,
    fingerprint,
    goal_card_versions,
    goal_cards,
    internal_app_runs,
    internal_approvals,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    run_contracts,
    runs,
)
from .errors import DomainError
from .goals import validate_card_version
from .text_logic_reuse import pair, remember
from .tools import csv_column_options

VERSION = "csv-goal-revision.v1"
PREVIEW, CHECK, CHECKED, JOB, APPROVAL = [VERSION + "." + x for x in
    ("preview", "check", "checked", "job", "approval")]
MARKER = "csv_goal_revision"
SOURCE = MARKER + "_source"
CHECK_CONSENT = "RUN_EXACT_CSV_GOAL_CHECK_KEEP_ORIGINAL"
VERSION_CONSENT = "CREATE_EXACT_CHECKED_CSV_GOAL_RELEASE"


def require(value,message="Exact frozen CSV Goal revision changed"):
    if not value:
        raise DomainError("VERSION_CONFLICT",message)


def extension(namespace):
    from . import csv_column_revisions, csv_material_revisions
    for module in (csv_column_revisions,csv_material_revisions):
        if namespace == module.VERSION:
            return module
    require(False,"Unknown CSV revision contract")


def material_policy(value):
    from .csv_material_revisions import VERSION as material_version
    return value["namespace"] == material_version or value["context"].get("parent",{}).get("material_revision",False)


class Preview(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=1)
    expected_release_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    goal_version: int = Field(ge=2)
    goal_fingerprint: str = Field(pattern=graph.HASH)
    baseline_column: str = Field(min_length=1, max_length=200)
    column: str = Field(min_length=1, max_length=200)


class Check(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_preview_fingerprint: str = Field(pattern=graph.HASH)
    consent: str = Field(pattern="^" + CHECK_CONSENT + "$")


class Version(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_check_fingerprint: str = Field(pattern=graph.HASH)
    consent: str = Field(pattern="^" + VERSION_CONSENT + "$")


class Reference(Strict):
    instance_id: str = Field(pattern=r"^iinstance_[a-f0-9]{32}$")
    preview_key: str = Field(min_length=1, max_length=100)
    preview_fingerprint: str = Field(pattern=graph.HASH)
    purpose: str = Field(pattern="^(CHECK|USE)$")


class Adopt(Strict):
    request_key: str = Field(min_length=1,max_length=100)
    expected_revision: int = Field(ge=1)
    target_release_id: str = Field(pattern=r"^irelease_[a-f0-9]{32}$")
    expected_target_fingerprint: str = Field(pattern=graph.HASH)


def reference(iid, key, value, purpose="CHECK"):
    return Reference(instance_id=iid, preview_key=key,
        preview_fingerprint=value["preview_fingerprint"], purpose=purpose)


@contextmanager
def proposal_tx(store,user,iid,stage,body,kind):
    """Only a proved absent intent and completed rollback authorize a new key."""
    from .db import internal_instances
    failure=None
    absent=False
    try:
        with store.tx() as c:
            try:
                pid=c.execute(select(internal_instances.c.project_id).where(internal_instances.c.id == iid,
                    internal_instances.c.principal_id == user)).scalar()
                store.lock_project(c,user,pid)
                # Existence projections only: a rejected request must not read
                # its old private proposal before current source authorization.
                prior=c.execute(select(requests.c.app_id).where(requests.c.app_id == iid,
                    requests.c.principal_id == user,requests.c.kind.in_([kind,kind+"_seal"]),
                    requests.c.request_key == body.request_key)).first()
                accepted=c.execute(select(requests.c.app_id).where(requests.c.principal_id == user,
                    requests.c.kind.in_([JOB,JOB+"_seal"]),
                    requests.c.snapshot["request"]["instance_id"].as_string() == iid,
                    requests.c.snapshot["request"]["preview_key"].as_string() == body.request_key)).first()
                frozen=c.execute(select(events.c.id).join(runs,runs.c.id == events.c.run_id).where(
                    runs.c.principal_id == user,events.c.kind == "CSV_GOAL_REVISION_FROZEN",
                    events.c.data["reference"]["instance_id"].as_string() == iid,
                    events.c.data["reference"]["preview_key"].as_string() == body.request_key)).first()
                origin=c.execute(select(internal_approvals.c.id).where(internal_approvals.c.principal_id == user,
                    internal_approvals.c.payload["snapshot"][SOURCE]["reference"]["instance_id"].as_string() == iid,
                    internal_approvals.c.payload["snapshot"][SOURCE]["reference"]["preview_key"].as_string() == body.request_key)).first()
                absent=prior is None and accepted is None and frozen is None and origin is None
                yield c
            except DomainError as exc:
                failure=exc
                raise
    except DomainError as exc:
        if exc is failure and absent and exc.code in {"INVALID_INPUT","VERSION_CONFLICT","PERMISSION_DENIED",
                "GRANT_REVOKED","RESOURCE_UNAVAILABLE","UNSUPPORTED_CAPABILITY","LOCK_CONFLICT"}:
            exc.submission_rejection=dict(namespace=VERSION+".rejection",instance_id=iid,principal_id=user,
                stage=stage,request_key=body.request_key,request_fingerprint=fingerprint(body.model_dump()),
                acceptance="NOT_ACCEPTED",previous_request="ABSENT",phase="TX_ROLLED_BACK")
        raise


@graph.controlled
def source_gate(store, c, user, iid, key=None, *, current_head=False):
    """Owned scalar identifiers and material union before any Goal/proposal body."""
    # The business pointer moves during adoption. Do not follow its current
    # Release here (that would recurse through release_gate after adoption).
    from .db import internal_instances
    meta = c.execute(select(internal_instances.c.id,internal_instances.c.principal_id,
        internal_instances.c.project_id,internal_instances.c.source_app_id,internal_instances.c.runtime_id)
        .where(internal_instances.c.id == iid,internal_instances.c.principal_id == user)).mappings().first()
    if meta is None:
        raise DomainError("PERMISSION_DENIED")
    from .db import app_drafts
    row = c.execute(select(app_drafts.c.project_id, app_drafts.c.runtime_id,
        app_drafts.c.candidate["generation"]["goal_card_id"].as_string().label("cid"),
        app_drafts.c.candidate["generation"]["goal_version"].as_integer().label("version"),
        app_drafts.c.candidate["manifest"]["data_bindings"][0]["resource_ref"].as_string().label("rid"))
        .where(app_drafts.c.id == meta["source_app_id"])).mappings().first()
    require(row is not None and row["project_id"] == meta["project_id"]
        and row["runtime_id"] == meta["runtime_id"] and row["cid"] is not None,
        "Only an original GoalCard CSV candidate can be revised")
    project = store.lock_project(c,user,meta["project_id"])
    versions = [row["version"]]
    if current_head:
        versions.append(c.execute(select(goal_cards.c.version).where(goal_cards.c.id == row["cid"])).scalar_one())
    if key is not None:
        hints = c.execute(select(requests.c.snapshot["response"]["context"]["goal"]["version"].as_integer())
            .where(requests.c.app_id == iid,requests.c.principal_id == user,
                requests.c.kind.in_([PREVIEW, PREVIEW + "_seal"]),requests.c.request_key == key)).scalars().all()
        versions += [v for v in hints if v is not None]
    # These are resource identifiers, never the private Goal text.
    refs = {row["rid"]}
    for version in set(versions):
        frozen = c.execute(select(goal_card_versions.c.snapshot["resource_snapshots"])
            .where(goal_card_versions.c.card_id == row["cid"],goal_card_versions.c.version == version)).scalar()
        require(isinstance(frozen,list))
        refs.update(x["resource_id"] for x in frozen)
    for rid in sorted(refs):
        store.authorize(c,user,project["runtime_id"],project["id"],rid,"resource.read")
    apps.authorize_source(store,c,user,project,row["rid"],row["runtime_id"])
    if key is not None:
        # Only identifier projections from both independent proposal anchors.
        # Authorize parent and target bindings before any private proposal body.
        hints = c.execute(select(
            requests.c.snapshot["request"]["resource_id"].as_string(),
            requests.c.snapshot["response"]["context"]["source"]["resource_id"].as_string(),
            requests.c.snapshot["response"]["material"]["resource_id"].as_string(),
            requests.c.snapshot["response"]["effective_candidate"]["manifest"]["data_bindings"][0]["resource_ref"].as_string())
            .where(requests.c.app_id == iid,requests.c.principal_id == user,
                requests.c.kind.in_([PREVIEW,PREVIEW+"_seal"]),requests.c.request_key == key)).all()
        for rid in sorted({rid for hint in hints for rid in hint if rid is not None}):
            apps.authorize_source(store,c,user,project,rid,row["runtime_id"])
    return meta


@graph.controlled
def context(store,c,user,iid,limits):
    source_gate(store,c,user,iid,current_head=True)
    inst, release = lifecycle.instance(store,c,user,iid,limits,lock=True)
    if SOURCE in release["snapshot"]:
        from . import csv_column_revisions as successive
        return successive.context(store,c,user,iid,limits,inst,release)
    require(SOURCE not in release["snapshot"] and "execution_source" not in release["snapshot"]
        and "natural_logic_source" not in release["snapshot"], "Only one revision of the original CSV Release is supported")
    base = release["snapshot"]["draft"]
    _,manifest,action,_ = apps.validate_frozen_candidate(store,c,user,base,limits)
    require(action.executor.ref == "data.aggregate_csv" and "generation" in base["candidate"])
    origin = base["candidate"]["generation"]
    card = c.execute(select(goal_cards).where(goal_cards.c.id == origin["goal_card_id"])).mappings().one()
    old = validate_card_version(store,c,user,card["id"],origin["goal_version"])
    new = validate_card_version(store,c,user,card["id"],card["version"])
    require(new["snapshot"]["resource_snapshots"] == old["snapshot"]["resource_snapshots"]
        and new["snapshot"]["content"]["resource_refs"] == old["snapshot"]["content"]["resource_refs"],
        "This finite revision cannot change or add Goal materials")
    saved = graph.current(store,c,user,inst["project_id"],base["id"],limits)
    from .tools import authorized_read
    source = authorized_read(store,c,user,base["runtime_id"],base["project_id"],"resource.read",
        dict(resource_id=manifest.data_bindings[0].resource_ref))
    guidance = csv_column_options(source["content"])
    require(not guidance["error"])
    value = dict(instance_id=iid,principal_id=user,project_id=inst["project_id"],app_id=base["id"],
        runtime_id=base["runtime_id"],release_id=release["id"],release_fingerprint=release["fingerprint"],
        draft_fingerprint=base["fingerprint"],instance_revision=inst["revision"],data_version=inst["data_version"],
        source=dict(resource_id=source["resource_id"],hash=source["hash"]),
        goal=dict(card_id=card["id"],version=card["version"],fingerprint=new["fingerprint"],snapshot=new["snapshot"]),
        original_goal_version=origin["goal_version"],graph_fingerprint=saved["graph"]["graph_fingerprint"],
        graph_revision=saved["graph_revision"],authorization_fingerprint=saved["authorization_fingerprint"],
        columns=[x["name"] for x in guidance["columns"] if x["numeric"]],limits=limits.model_dump())
    return value, release, saved


def effective(base, goal, column, limits):
    """Only this function builds effective specs, from a fully validated base."""
    value = copy.deepcopy(base["candidate"])
    require(value["manifest"]["revision"] == value["actions"][0]["revision"] == 1)
    value["goal"] = copy.deepcopy(goal["snapshot"]["content"])
    value["manifest"]["revision"] = value["actions"][0]["revision"] = 2
    value["manifest"]["action_bindings"][0]["revision"] = 2
    for schema in (value["manifest"]["input_schema"],value["actions"][0]["input_schema"]):
        schema["properties"]["column"] = dict(type="string",enum=[column])
    # Output schemas intentionally remain compatible with all retained results.
    manifest, report = apps.preflight(json.dumps(value["manifest"]),value["actions"],limits)
    return {**copy.deepcopy(base),"candidate":value,"fingerprint":fingerprint(value)},manifest,validate_action(json.dumps(value["actions"][0])),report


def calculate(ctx,release,saved,body,limits):
    require(ctx["instance_revision"] == body.expected_revision
        and ctx["release_fingerprint"] == body.expected_release_fingerprint
        and ctx["graph_fingerprint"] == body.expected_graph_fingerprint
        and ctx["goal"]["version"] == body.goal_version == ctx["original_goal_version"] + 1
        and ctx["goal"]["fingerprint"] == body.goal_fingerprint)
    column_changed = body.column != body.baseline_column
    require(body.column in ctx["columns"] and body.baseline_column in ctx["columns"]
        and (column_changed or ctx["goal"]["snapshot"]["content"] != release["snapshot"]["draft"]["candidate"]["goal"]),
        "Explicitly change Goal content or the numeric column")
    nodes = [n for n in saved["graph"]["nodes"] if n["kind"] == "GOAL"
        or (column_changed and n["key"] == "action:aggregate")]
    require(len(nodes) == 1 + column_changed)
    plan = graph.core.plan_change(saved["graph"],body.expected_graph_fingerprint,
        dict(project_id=ctx["project_id"],app_id=ctx["app_id"],request_key=body.request_key,
            changes=[dict(node_id=n["id"],expected_revision=n["revision"],expected_content_fingerprint=n["content_fingerprint"]) for n in nodes]),saved["context"])
    if plan["revalidation_scope"] == "PROJECT":
        raise DomainError("UNSUPPORTED_CAPABILITY","Unknown project dependencies exceed this finite check")
    draft,_,_,report = effective(release["snapshot"]["draft"],ctx["goal"],body.column,limits)
    result = dict(namespace=VERSION,request_key=body.request_key,context=ctx,impact=plan,
        baseline_graph=saved,effective_candidate=draft["candidate"],effective_fingerprint=draft["fingerprint"],
        plan_fingerprint=fingerprint(report),baseline_input=dict(column=body.baseline_column),input=dict(column=body.column),
        model_requests=0,semantic_status="UNKNOWN",owner_acceptance="PENDING",formal_publication_enabled=False)
    result["preview_fingerprint"] = fingerprint(result)
    return result


def preview_pair(c,user,iid,key):
    """Strict paired request type, only after source_gate authorized its scope."""
    namespaces = c.execute(select(requests.c.snapshot["response"]["namespace"].as_string()).where(
        requests.c.app_id == iid,requests.c.principal_id == user,
        requests.c.kind.in_([PREVIEW,PREVIEW+"_seal"]),requests.c.request_key == key)).scalars().all()
    from . import csv_material_revisions as material
    model = material.Preview if material.VERSION in namespaces else Preview
    return pair(c,user,iid,PREVIEW,key,model)


@graph.controlled
def load_preview(store,c,user,iid,key,limits,*,current=False):
    source_gate(store,c,user,iid,key)
    body,value = preview_pair(c,user,iid,key)
    if value.get("namespace") != VERSION:
        return extension(value.get("namespace")).load(store,c,user,iid,key,limits,body,value,current)
    ctx = value["context"]
    require(ctx["instance_id"] == iid and ctx["principal_id"] == user and ctx["limits"] == limits.model_dump())
    require(all(type(ctx[k]) is int for k in ("instance_revision","data_version","graph_revision","original_goal_version"))
        and type(ctx["goal"]["version"]) is int,"Frozen revision versions must be exact integers")
    base = lifecycle.read_release(store,c,user,ctx["release_id"],limits)
    require(base["fingerprint"] == ctx["release_fingerprint"] and SOURCE not in base["snapshot"]
        and base["snapshot"]["draft"]["id"] == ctx["app_id"]
        and base["snapshot"]["draft"]["fingerprint"] == ctx["draft_fingerprint"])
    goal = ctx["goal"]
    old = validate_card_version(store,c,user,goal["card_id"],goal["version"])
    require(old["snapshot"] == goal["snapshot"] and old["fingerprint"] == goal["fingerprint"])
    require(calculate(ctx,base,value["baseline_graph"],body,limits) == value,"Sealed Goal/column definition changed")
    if current:
        fresh,actual,saved = context(store,c,user,iid,limits)
        require(fresh == ctx and actual["id"] == base["id"] and saved == value["baseline_graph"],
            "Goal, authority, graph, locks or original instance changed; prepare a fresh revision")
    return body,value


def preview(store,user,iid,body,limits):
    with proposal_tx(store,user,iid,"previews",body,PREVIEW) as c:
        from . import csv_material_revisions as material
        operation = material if isinstance(body,material.Preview) else None
        if operation:
            operation.authorize_proposal(store,c,user,iid,body)
        ctx,base,saved = (operation.context if operation else context)(store,c,user,iid,limits)
        if graph.lookup(c,user,iid,PREVIEW,body.request_key):
            old,value = load_preview(store,c,user,iid,body.request_key,limits,current=True)
            require(old == body)
            return value
        require(len(c.execute(select(requests.c.request_key).where(requests.c.app_id == iid,
            requests.c.kind == PREVIEW)).all()) < 32,"Finite revision proposal capacity exhausted")
        if "revision_contract" in ctx:
            value = extension(ctx["revision_contract"]).calculate(store,c,user,ctx,base,saved,body,limits)
        else:
            value = calculate(ctx,base,saved,body,limits)
        remember(c,user,iid,PREVIEW,body.request_key,body,value)
        return value


def bound(store,c,user,release,limits,snapshot=None,*,current=False):
    ref_value = snapshot.get(MARKER) if snapshot is not None else None
    if ref_value is None and SOURCE in release["snapshot"]:
        ref_value = release["snapshot"][SOURCE]["reference"]
    if ref_value is None:
        return apps.validate_frozen_candidate(store,c,user,release["snapshot"]["draft"],limits)
    ref = Reference.model_validate(ref_value)
    _,value = load_preview(store,c,user,ref.instance_id,ref.preview_key,limits,current=current and ref.purpose == "CHECK")
    require(reference(ref.instance_id,ref.preview_key,value,ref.purpose) == ref)
    if value["namespace"] != VERSION:
        return extension(value["namespace"]).bound(store,c,user,release,limits,snapshot,ref,value,current)
    if ref.purpose == "CHECK":
        require(SOURCE not in release["snapshot"] and release["id"] == value["context"]["release_id"]
            and snapshot is not None and snapshot["instance_id"] != ref.instance_id)
    else:
        require(SOURCE in release["snapshot"] and release["snapshot"][SOURCE]["reference"] == ref.model_dump())
        if current:
            eligibility(store,c,user,value,limits)
    return effective(release["snapshot"]["draft"],value["context"]["goal"],value["input"]["column"],limits)


def eligibility(store,c,user,value,limits,instance=None,target_id=None):
    """New work/approval/adoption only. Historical reads keep frozen versions."""
    ctx = value["context"]
    head = c.execute(select(goal_cards.c.version,goal_cards.c.fingerprint).where(goal_cards.c.id == ctx["goal"]["card_id"])).mappings().one()
    require(head == dict(version=ctx["goal"]["version"],fingerprint=ctx["goal"]["fingerprint"]),"Goal head changed")
    saved = graph.current(store,c,user,ctx["project_id"],ctx["app_id"],limits)
    require(saved == value["baseline_graph"],"Graph, authority or manual locks changed")
    if instance is not None:
        require(instance["id"] == ctx["instance_id"],"Adopt this checked revision on its original instance")
        if instance["release_id"] != target_id:
            require(instance["revision"] == ctx["instance_revision"] and instance["data_version"] == ctx["data_version"]
                and instance["release_id"] == ctx["release_id"],"Original instance changed before adoption")


@graph.controlled
def job_gate(store,c,user,rid):
    anchors = c.execute(select(requests.c.app_id,requests.c.snapshot["request"]["instance_id"].as_string().label("iid"),
        requests.c.snapshot["request"]["preview_key"].as_string().label("key"))
        .where(requests.c.app_id == rid,requests.c.kind.in_([JOB,JOB+"_seal"]),requests.c.principal_id == user)).mappings().all()
    marker = c.execute(select(internal_run_bindings.c.snapshot[MARKER]).where(internal_run_bindings.c.run_id == rid)).scalar()
    context_marker = c.execute(select(runs.c.context[MARKER]).where(runs.c.id == rid)).scalar()
    accepted = c.execute(select(events.c.data).where(events.c.run_id == rid,events.c.kind == "CSV_GOAL_REVISION_FROZEN")).scalars().all()
    checks = c.execute(select(requests.c.app_id,requests.c.request_key).where(requests.c.kind.in_([CHECK,CHECK+"_seal"]),
        requests.c.principal_id == user,requests.c.snapshot["response"]["run_id"].as_string() == rid)).mappings().all()
    key = c.execute(select(runs.c.request_key).where(runs.c.id == rid,runs.c.principal_id == user)).scalar()
    release_id = c.execute(select(internal_app_runs.c.release_id).where(internal_app_runs.c.id == key.removeprefix("internal:"),
        internal_app_runs.c.principal_id == user)).scalar() if isinstance(key,str) and key.startswith("internal:") else None
    release_ref = c.execute(select(internal_releases.c.snapshot[SOURCE]["reference"]).where(internal_releases.c.id == release_id,
        internal_releases.c.principal_id == user)).scalar() if release_id else None
    if not anchors and marker is None and context_marker is None and not accepted and not checks and release_ref is None:
        return False
    metadata = c.execute(select(runs.c.principal_id,runs.c.project_id).where(runs.c.id == rid)).mappings().first()
    if metadata is None or metadata["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c,user,metadata["project_id"])
    # Authorize every hinted proposal before reading its protected payload.
    hints = [(r["iid"],r["key"]) for r in anchors]
    hints += [(r["app_id"],r["request_key"]) for r in checks]
    if isinstance(release_ref,dict):
        hints.append((release_ref.get("instance_id"),release_ref.get("preview_key")))
    if isinstance(marker,dict):
        hints.append((marker.get("instance_id"),marker.get("preview_key")))
    for iid,key in hints:
        source_gate(store,c,user,iid,key)
    # Independent actual-material hints also protect cold reads if one proposal
    # marker has been stripped or re-signed. Bodies are read only below.
    material_ids = c.execute(select(runs.c.resource_refs,runs.c.runtime_id).where(
        runs.c.id == rid,runs.c.principal_id == user)).mappings().one()
    contract_resource = c.execute(select(run_contracts.c.snapshot[
        "resources"][0]["resource_id"].as_string()).where(run_contracts.c.run_id == rid)).scalar()
    project = store.lock_project(c,user,metadata["project_id"])
    for resource in set(material_ids["resource_refs"] + ([contract_resource] if contract_resource else [])):
        apps.authorize_source(store,c,user,project,resource,material_ids["runtime_id"])
    require(len(anchors) == 2 and marker is not None)
    ref,sealed = pair(c,user,rid,JOB,"accepted",Reference)
    binding_meta = c.execute(select(internal_run_bindings.c.snapshot["instance_id"].as_string().label("iid"),
        internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id == rid)).mappings().one()
    require(fingerprint(marker) == fingerprint(sealed) == fingerprint(ref.model_dump())
        and context_marker == fingerprint(marker) and accepted == [dict(reference=marker,reference_fingerprint=fingerprint(marker),
            instance_id=binding_meta["iid"],app_run_id=binding_meta["app_run_id"])],
        "Frozen CSV revision cannot be removed or replaced")
    return True


def verify_job(store,c,user,job,snapshot,release,limits,contract):
    active = job_gate(store,c,user,job["id"])
    require(active == (MARKER in snapshot))
    if SOURCE in release["snapshot"]:
        require(active)
    if not active:
        return
    ref = Reference.model_validate(snapshot[MARKER])
    _,value = load_preview(store,c,user,ref.instance_id,ref.preview_key,limits)
    if SOURCE in release["snapshot"] and ref.purpose != "USE":
        require(ref.purpose == "CHECK")
        extension(value["namespace"])
    bound(store,c,user,release,limits,snapshot)
    if ref.purpose == "CHECK":
        _,started = pair(c,user,ref.instance_id,CHECK,ref.preview_key,Check)
        require(started["run_id"] == job["id"] and started["app_run_id"] == snapshot["app_run_id"]
            and started["check_instance_id"] == snapshot["instance_id"],"Run must be the independently accepted isolated CHECK")
    goal = value["context"]["goal"]
    expected = goal_spec(goal,contract.goal.model_dump())
    require(snapshot.get("csv_goal") == goal and contract.goal.model_dump() == expected
        and job["goal"] == goal["snapshot"]["content"]["goal"],"Run must freeze the exact revised Goal")


def goal_spec(goal,base):
    from .pa_spec_apps import goal_unresolved
    content = goal["snapshot"]["content"]
    return {**base,"goal_id":goal["card_id"],"goal":content["goal"],"constraints":content["constraints"],
        "unresolved":goal_unresolved(goal)}


def checked(store,c,user,iid,key,limits,*,current=False):
    _,value = load_preview(store,c,user,iid,key,limits,current=current)
    body,started = pair(c,user,iid,CHECK,key,Check)
    require(body.expected_preview_fingerprint == value["preview_fingerprint"])
    from .csv_owner_review import context as proof_context
    actual = proof_context(store,c,user,started["check_instance_id"],started["run_id"],limits)
    require(actual["input"] == value["input"] and actual["result_version"] == 1)
    # Current authorization is checked above, but its revision is not history.
    actual.pop("grant_version")
    result = dict(namespace=VERSION,ref="csv.exact_integer_sum.v1",status="PASS",run_id=started["run_id"],
        check_instance_id=started["check_instance_id"],preview_fingerprint=value["preview_fingerprint"],
        effective_fingerprint=value["effective_fingerprint"],candidate_fingerprint=value["context"]["draft_fingerprint"],
        input_fingerprint=fingerprint(value["input"]),output_fingerprint=actual["output_fingerprint"],
        plan_fingerprint=value["plan_fingerprint"],actual_proof_fingerprint=fingerprint(actual),
        semantic_status="UNKNOWN",owner_acceptance="PENDING",model_requests=0)
    if value["namespace"] != VERSION:
        result.update(namespace=value["namespace"],spec_revision=value["spec_revision"])
    result["check_fingerprint"] = fingerprint(result)
    if graph.lookup(c,user,iid,CHECKED,key):
        old,sealed = pair(c,user,iid,CHECKED,key,Check)
        require(old == body and fingerprint(sealed) == fingerprint(result),"Actual independent CSV check changed")
    else:
        remember(c,user,iid,CHECKED,key,body,result)
    return value,result


def validate_snapshot(store,c,user,snapshot,limits,*,current=False):
    origin = snapshot[SOURCE]
    if origin.get("namespace") != VERSION:
        return extension(origin.get("namespace")).validate_snapshot(store,c,user,snapshot,limits,current)
    require(set(origin) == {"namespace","reference","check_fingerprint","goal","input","effective_fingerprint"}
        and origin["namespace"] == VERSION)
    ref = Reference.model_validate(origin["reference"])
    require(ref.purpose == "USE")
    value,proof = checked(store,c,user,ref.instance_id,ref.preview_key,limits,current=current)
    require(ref == reference(ref.instance_id,ref.preview_key,value,"USE")
        and proof["check_fingerprint"] == origin["check_fingerprint"]
        and fingerprint(snapshot["check_evidence"]) == fingerprint(proof)
        and origin["goal"] == value["context"]["goal"] and origin["input"] == value["input"]
        and origin["effective_fingerprint"] == value["effective_fingerprint"]
        and snapshot["draft"]["fingerprint"] == value["context"]["draft_fingerprint"])
    return value


def validate_family(c,user,approval_id,snapshot):
    rows = c.execute(select(requests.c.app_id,requests.c.request_key).where(requests.c.kind == APPROVAL,
        requests.c.snapshot["response"]["id"].as_string() == approval_id)).mappings().all()
    require(bool(rows) == (SOURCE in snapshot),"CSV Goal revision origin cannot be removed or added")
    if rows:
        require(len(rows) == 1)
        _,sealed = pair(c,user,rows[0]["app_id"],APPROVAL,rows[0]["request_key"],Version)
        require(sealed["id"] == approval_id and sealed["snapshot_fingerprint"] == fingerprint(snapshot))


def release_gate(store,c,user,rid=None,approval_id=None):
    if rid is not None:
        approval_id = c.execute(select(internal_releases.c.approval_id).where(internal_releases.c.id == rid,
            internal_releases.c.principal_id == user)).scalar()
    rows = c.execute(select(requests.c.app_id,requests.c.request_key).where(requests.c.kind.in_([APPROVAL,APPROVAL+"_seal"]),
        requests.c.snapshot["response"]["id"].as_string() == approval_id,requests.c.principal_id == user)).mappings().all() if approval_id else []
    for row in rows:
        source_gate(store,c,user,row["app_id"],row["request_key"])
    if rid is not None:
        hint = c.execute(select(internal_releases.c.snapshot[SOURCE]["reference"]).where(internal_releases.c.id == rid,
            internal_releases.c.principal_id == user)).scalar()
    else:
        hint = c.execute(select(internal_approvals.c.payload["snapshot"][SOURCE]["reference"]).where(
            internal_approvals.c.id == approval_id,internal_approvals.c.principal_id == user)).scalar() if approval_id else None
    if isinstance(hint,dict):
        source_gate(store,c,user,hint.get("instance_id"),hint.get("preview_key"))
    require(bool(rows) == (hint is not None),"CSV revision Release/approval authority index changed")


def pins(c,user,iid):
    rows = c.execute(select(requests.c.app_id).where(requests.c.kind.in_([CHECK,CHECK+"_seal"]),
        requests.c.principal_id == user,requests.c.snapshot["response"]["check_instance_id"].as_string() == iid)).all()
    bindings = c.execute(select(internal_run_bindings.c.run_id).where(
        internal_run_bindings.c.snapshot["instance_id"].as_string() == iid,
        internal_run_bindings.c.snapshot[MARKER]["purpose"].as_string() == "CHECK")).all()
    frozen = c.execute(select(events.c.id).where(events.c.kind == "CSV_GOAL_REVISION_FROZEN",
        events.c.data["instance_id"].as_string() == iid,
        events.c.data["reference"]["purpose"].as_string() == "CHECK")).all()
    return [dict(role="csv_goal_check")] if rows or bindings or frozen else []


def control_scope(store,c,user,rid,*,iid=None,lock=False):
    """Owned stop metadata remains usable after source revocation; no bodies."""
    marked=c.execute(select(runs.c.context[MARKER]).where(runs.c.id == rid)).scalar()
    seal=c.execute(select(requests.c.app_id).where(requests.c.app_id == rid,requests.c.kind.in_([JOB,JOB+"_seal"]))).first()
    source=c.execute(select(internal_releases.c.snapshot[SOURCE]["reference"])
        .join(internal_app_runs,internal_app_runs.c.release_id == internal_releases.c.id)
        .join(internal_run_bindings,internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
        .where(internal_run_bindings.c.run_id == rid)).scalar()
    if marked is None and seal is None and source is None:
        return None
    query=select(runs.c.id,runs.c.project_id,runs.c.principal_id,runs.c.runtime_id,runs.c.status,
        runs.c.version,runs.c.cancel_intent).where(runs.c.id == rid)
    job=c.execute(query.with_for_update() if lock else query).mappings().first()
    if job is None or job["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c,user,job["project_id"])
    app=c.execute(select(internal_app_runs.c.id,internal_app_runs.c.instance_id,internal_app_runs.c.release_id,
        internal_app_runs.c.principal_id).join(internal_run_bindings,internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
        .where(internal_run_bindings.c.run_id == rid,internal_app_runs.c.principal_id == user)).mappings().first()
    if app is None or (iid is not None and app["instance_id"] != iid):
        raise DomainError("PERMISSION_DENIED")
    owned=c.execute(select(internal_instances.c.project_id,internal_instances.c.runtime_id).where(
        internal_instances.c.id == app["instance_id"],internal_instances.c.principal_id == user)).mappings().first()
    require(owned is not None and owned["project_id"] == job["project_id"] and owned["runtime_id"] == job["runtime_id"])
    return dict(job),dict(app)


def mount(app,store,limits,identity):
    dep = Depends(identity)
    path = "/api/internal/instances/{iid}/csv-goal-revisions"

    @app.get(path + "/context")
    def baseline(iid:str,user=dep):
        with store.tx() as c:
            ctx,_,_ = context(store,c,user,iid,limits)
            return ctx

    @app.post(path + "/previews",status_code=201)
    def propose(iid:str,body:Preview,user=dep):
        return preview(store,user,iid,body,limits)

    @app.get(path + "/previews/{key}")
    def recover_preview(iid:str,key:str,user=dep):
        with store.tx() as c:
            return load_preview(store,c,user,iid,key,limits)[1]

    @app.post(path + "/checks",status_code=202)
    def start(iid:str,body:Check,user=dep):
        from .app_jobs import enqueue
        from .csv_owner_review import CONSENT
        with proposal_tx(store,user,iid,"checks",body,CHECK) as c:
            _,value = load_preview(store,c,user,iid,body.request_key,limits,current=True)
            require(body.expected_preview_fingerprint == value["preview_fingerprint"])
            if graph.lookup(c,user,iid,CHECK,body.request_key):
                old,result = pair(c,user,iid,CHECK,body.request_key,Check)
                require(old == body)
                return result
            ctx = value["context"]
            inst = lifecycle.create_instance_tx(store,c,user,ctx["release_id"],ctx["release_fingerprint"],limits,
                request_key="csv-goal-check:" + fingerprint([iid,body.request_key]),
                _csv_goal_check=reference(iid,body.request_key,value))
            result = enqueue(store,user,inst["id"],inst["revision"],ctx["release_fingerprint"],value["input"],
                body.request_key,limits,logic_tx=c,csv_goal_check=reference(iid,body.request_key,value),csv_review=CONSENT)
            result = {**result,"check_instance_id":inst["id"],"request_key":body.request_key,
                "accepted_request_fingerprint":fingerprint(body.model_dump())}
            remember(c,user,iid,CHECK,body.request_key,body,result)
            return result

    @app.get(path + "/checks/{key}")
    def outcome(iid:str,key:str,user=dep):
        with store.tx() as c:
            load_preview(store,c,user,iid,key,limits)
            _,started = pair(c,user,iid,CHECK,key,Check)
            job_gate(store,c,user,started["run_id"])
            status = c.execute(select(runs.c.status).where(runs.c.id == started["run_id"])).scalar_one()
            if status != "SUCCEEDED":
                return {**started,"status":status,"check_status":"NOT_PASSED"}
            return {**checked(store,c,user,iid,key,limits)[1],"request_key":key,
                "accepted_request_fingerprint":started["accepted_request_fingerprint"]}

    @app.post(path + "/version-approvals",status_code=201)
    def version(iid:str,body:Version,user=dep):
        with proposal_tx(store,user,iid,"version-approvals",body,APPROVAL) as c:
            value,proof = checked(store,c,user,iid,body.request_key,limits,current=True)
            require(body.expected_check_fingerprint == proof["check_fingerprint"])
            if graph.lookup(c,user,iid,APPROVAL,body.request_key):
                old,result = pair(c,user,iid,APPROVAL,body.request_key,Version)
                require(old == body)
                return result
            base = lifecycle.read_release(store,c,user,value["context"]["release_id"],limits)
            snap = copy.deepcopy(base["snapshot"])
            snap[SOURCE] = dict(namespace=value["namespace"],reference=reference(iid,body.request_key,value,"USE").model_dump(),
                check_fingerprint=proof["check_fingerprint"],goal=value["context"]["goal"],input=value["input"],
                effective_fingerprint=value["effective_fingerprint"])
            if value["namespace"] != VERSION:
                snap[SOURCE].update(parent=value["context"]["parent"],spec_revision=value["spec_revision"])
            snap["check_evidence"] = proof
            result = lifecycle.new_approval(c,user,value["context"]["project_id"],"release",
                dict(snapshot=snap,grant_version=lifecycle.grant_version(c,value["context"]["project_id"],user)))
            result.update(snapshot=snap,snapshot_fingerprint=fingerprint(snap))
            result["expires_at"] = lifecycle.approval(c,user,result["id"],result["fingerprint"],"release")["expires_at"]
            remember(c,user,iid,APPROVAL,body.request_key,body,result)
            return result

    @app.get(path + "/version-approvals/{key}")
    def recover_version(iid:str,key:str,user=dep):
        with store.tx() as c:
            load_preview(store,c,user,iid,key,limits)
            return pair(c,user,iid,APPROVAL,key,Version)[1]

    @app.post(path + "/adoption-approvals",status_code=201)
    def adopt(iid:str,body:Adopt,user=dep):
        with proposal_tx(store,user,iid,"adoption-approvals",body,VERSION+".adoption") as c:
            source_gate(store,c,user,iid,body.request_key)
            target = lifecycle.read_release(store,c,user,body.target_release_id,limits)
            require(SOURCE in target["snapshot"] and target["snapshot"][SOURCE]["reference"]["instance_id"] == iid)
            kind = VERSION + ".adoption"
            if graph.lookup(c,user,iid,kind,body.request_key):
                old,result = pair(c,user,iid,kind,body.request_key,Adopt)
                require(old == body)
                return result
            result = lifecycle.prepare_switch(store,user,iid,body.target_release_id,body.expected_revision,limits,
                expected_target_fingerprint=body.expected_target_fingerprint,_tx=c)
            remember(c,user,iid,kind,body.request_key,body,result)
            return result

    @app.get(path + "/adoption-approvals/{key}")
    def recover_adopt(iid:str,key:str,user=dep):
        with store.tx() as c:
            source_gate(store,c,user,iid,key)
            _,result = pair(c,user,iid,VERSION+".adoption",key,Adopt)
        return lifecycle.inspect_switch_approval(store,user,iid,result["id"],limits)
