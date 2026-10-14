"""Finite existing-app recipe dependency edit; immutable original provenance.

Only requirements -> qualifiers prior-result/feedback dependency can change.
Check Runs use an isolated instance of the original Release and the normal Worker.
An independently confirmed new internal Release keeps the original draft intact.
"""
import copy
from contextlib import contextmanager
from typing import Any, Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import delivery_graph_apps as graph
from . import lifecycle
from . import natural_specs as natural
from . import pa_spec_apps as spec
from .contracts import Limits, Strict
from .db import (
    delivery_graph_requests,
    fingerprint,
    runs,
)
from .errors import DomainError
from .text_logic_reuse import pair, remember

VERSION = "natural-local-logic.v1"
PREVIEW = VERSION + ".preview"
CHECK = VERSION + ".check"
CHECKED = VERSION + ".checked"
JOB = VERSION + ".job"
APPROVAL = VERSION + ".approval"
CHECK_CONSENT = "RUN_EXACT_LOCAL_LOGIC_CHECK_KEEP_ORIGINAL"
VERSION_CONSENT = "CREATE_EXACT_CHECKED_INTERNAL_LOGIC_VERSION"


class Preview(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=1)
    expected_release_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    consume_prior_feedback: bool


class Check(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_preview_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["RUN_EXACT_LOCAL_LOGIC_CHECK_KEEP_ORIGINAL"]


class Version(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_check_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["CREATE_EXACT_CHECKED_INTERNAL_LOGIC_VERSION"]


class Reference(Strict):
    instance_id: str
    preview_key: str
    preview_fingerprint: str = Field(pattern=graph.HASH)


@contextmanager
def proposal_tx(store,user,iid,stage,body,kind):
    """Proof only when this exact new request rolled back without acceptance."""
    failure=None
    absent=False
    try:
        with store.tx() as c:
            try:
                # Owned metadata first; do not inspect another principal's ledger.
                from .db import internal_instances
                pid=c.execute(select(internal_instances.c.project_id).where(
                    internal_instances.c.id == iid,internal_instances.c.principal_id == user)).scalar()
                store.lock_project(c,user,pid)
                absent=graph.lookup(c,user,iid,kind,body.request_key) is None
                yield c
            except DomainError as exc:
                failure=exc
                raise
    except DomainError as exc:
        if exc is failure and absent and exc.code in {"INVALID_INPUT","VERSION_CONFLICT",
                "GRANT_REVOKED","PERMISSION_DENIED","RESOURCE_UNAVAILABLE","UNSUPPORTED_CAPABILITY","LOCK_CONFLICT"}:
            exc.submission_rejection=dict(namespace=VERSION+".rejection",instance_id=iid,
                principal_id=user,stage=stage,request_key=body.request_key,
                request_fingerprint=fingerprint(body.model_dump()),acceptance="NOT_ACCEPTED",
                previous_request="ABSENT",phase="TX_ROLLED_BACK")
        raise


def effective(base, consume, limits):
    """Reconstruct exactly one allowed edit, without forging generation markers."""
    natural.compile_candidate(base, limits)
    recipe = copy.deepcopy(base["spec_recipe"])
    steps = recipe["steps"]
    if [s["operator"] for s in steps] != [natural.READ, "model.spec.requirements",
            "model.spec.qualifiers", natural.MERGE, natural.VERIFY, natural.SAVE]:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Only the existing two-model requirements/qualifiers recipe is supported")
    read, prior, changed = steps[:3]
    old = "prior_items" in changed["inputs"]
    spec.require(old != consume, "Select an actual recipe dependency change")
    for name, field in (("prior_items", "items"), ("prior_feedback", "feedback")):
        if consume:
            changed["inputs"][name] = dict(source="step", ref=prior["step_id"], field=field)
        else:
            changed["inputs"].pop(name, None)
    changed["depends_on"] = [read["step_id"]] + ([prior["step_id"]] if consume else [])
    m = base["manifest"]
    candidate = natural.expand(recipe, m["app_id"], m["goal_ref"],
        m["permission_requirements"][-1]["resource_ref"], base["source_hash"],
        m["data_bindings"][0]["resource_ref"], base["goal"], Limits(**m["runtime_limits"]),
        base["model_sample_check"]["sample_fingerprint"])
    revision = base["manifest"]["revision"] + 1
    spec.require(revision in {2, 3}, "At most two explicit local adjustments")
    candidate["logic_revision"] = dict(version=VERSION,step_id=changed["step_id"])
    if revision == 3:
        candidate["logic_revision"]["revision"] = revision
    candidate["manifest"]["revision"] = revision
    candidate["actions"][2]["revision"] = revision
    candidate["manifest"]["action_bindings"][2]["revision"] = revision
    natural.compile_candidate(candidate, limits)
    spec.require([a["action_id"] for a in base["actions"]] == [a["action_id"] for a in candidate["actions"]])
    # The effective candidate has no PA/PB generation marker. Original marker is
    # kept exclusively in the immutable base draft and independently sealed origin.
    return candidate, changed["step_id"]


def context(store, c, user, iid, limits, *, original=True, _verified_origin=None, _allow_last=False):
    origin: dict[str, Any] = {}
    logic_out: dict[str, Any] = {}
    instance, release = lifecycle.instance(store, c, user, iid, limits, lock=True,
        _origin_out=origin,_verified_origin=_verified_origin,_logic_out=logic_out)
    parent = None
    if "natural_logic_source" in release["snapshot"]:
        trace = lifecycle.logic_release_trace(store,c,user,release)
        depth = len(trace["edges"])
        spec.require(not trace["cyclic"] and not trace["over_limit"] and depth in {1, 2})
        if depth == 2 and not _allow_last:
            raise DomainError("UNSUPPORTED_CAPABILITY", "At most two explicit local adjustments")
        parent = logic_out["value"]["effective_candidate"]
        spec.require(parent["manifest"]["revision"] == depth + 1)
    base = release["snapshot"]["draft"]
    spec.require(natural.is_candidate(base["candidate"]))
    _, _, source, goal = origin["origin"]
    family = graph.load_family(store,c,user,instance["project_id"],base["id"],limits,_natural_origin=origin)
    saved = graph.current(store, c, user, instance["project_id"], base["id"], limits,_family=family)
    anchor = saved
    if parent is not None:
        # Original anchor stays independently authorized and immutable. Derive
        # only the proven parent's effective graph using the same trusted IDs,
        # external versions and current locks; never write a replacement anchor.
        saved = copy.deepcopy(anchor)
        ctx = saved["context"]
        for node in anchor["graph"]["nodes"]:
            if node["kind"] == "ACTION":
                step = node["key"].split(":",1)[1]
                index = next(i for i,x in enumerate(parent["spec_recipe"]["steps"]) if x["step_id"] == step)
                ctx["node_revisions"][node["key"]] = parent["actions"][index]["revision"]
            elif node["kind"] in {"MANIFEST", "ARTIFACT", "VIEW"}:
                ctx["node_revisions"][node["key"]] = parent["manifest"]["revision"]
        saved["graph"] = graph.core.derive_manifest_graph(parent["manifest"],parent["actions"],
            anchor["source_versions"],{n["key"]:n["id"] for n in anchor["graph"]["nodes"]},ctx,limits,
            natural_candidate=parent)
        ctx["graph_fingerprint"] = saved["graph"]["graph_fingerprint"]
        saved["candidate_fingerprint"] = fingerprint(parent)
        saved["effective_candidate"] = parent
    if any(x["scope"] == "PROJECT" for x in saved["graph"]["unknown_dependencies"]):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Unknown project dependencies require project validation outside this finite application slice")
    value = dict(instance_id=iid, project_id=instance["project_id"], principal_id=user,
        app_id=base["id"], runtime_id=base["runtime_id"], release_id=release["id"],
        release_fingerprint=release["fingerprint"], draft_fingerprint=base["fingerprint"],
        graph_fingerprint=saved["graph"]["graph_fingerprint"],
        graph_revision=saved["graph_revision"], audit_fingerprint=spec.audit_fingerprint(store,c,user,base),
        source=source, goal=goal, limits=limits.model_dump())
    if parent is not None:
        value["parent_logic"] = dict(depth=depth,
            origin=copy.deepcopy(release["snapshot"]["natural_logic_source"]),
            effective_fingerprint=fingerprint(parent),
            anchor_graph_fingerprint=anchor["graph"]["graph_fingerprint"])
    if original:
        value.update(instance_revision=instance["revision"], data_version=instance["data_version"])
    return value, instance, release, saved


def calculate(store, c, user, iid, limits, body, *, prepared=None):
    ctx, instance, release, saved = prepared or context(store,c,user,iid,limits)
    spec.require(instance["revision"] == body.expected_revision
        and release["fingerprint"] == body.expected_release_fingerprint
        and ctx["graph_fingerprint"] == body.expected_graph_fingerprint)
    candidate, sid = effective(saved.get("effective_candidate",release["snapshot"]["draft"]["candidate"]), body.consume_prior_feedback, limits)
    node = next(n for n in saved["graph"]["nodes"] if n["key"] == "action:" + sid)
    plan = graph.core.plan_change(saved["graph"], body.expected_graph_fingerprint,
        dict(project_id=ctx["project_id"], app_id=ctx["app_id"], request_key=body.request_key,
            changes=[dict(node_id=node["id"], expected_revision=node["revision"],
                expected_content_fingerprint=node["content_fingerprint"]) ]), saved["context"])
    base = saved.get("effective_candidate",release["snapshot"]["draft"]["candidate"])
    preserved = [dict(step_id=base["spec_recipe"]["steps"][i]["step_id"], action_id=old["action_id"],
        definition_fingerprint=fingerprint(old)) for i, old in enumerate(base["actions"])
        if old == candidate["actions"][i]]
    value = dict(namespace=VERSION, request_key=body.request_key, context=ctx, impact=plan,
        effective_candidate=candidate, effective_fingerprint=fingerprint(candidate),
        modified_step_id=sid, preserved_action_definitions=preserved,
        original_recipe_fingerprint=fingerprint(base["spec_recipe"]),
        new_recipe_fingerprint=fingerprint(candidate["spec_recipe"]),
        semantic_status="UNKNOWN", owner_acceptance="PENDING", formal_publication_enabled=False)
    value["preview_fingerprint"] = fingerprint(value)
    return value


def preview(store,user,iid,limits,body):
    with proposal_tx(store,user,iid,"previews",body,PREVIEW) as c:
        # Authorize original instance/source before any private proposal ledger.
        current = context(store,c,user,iid,limits)
        prior = graph.lookup(c,user,iid,PREVIEW,body.request_key)
        if prior:
            old, value = load_preview(store,c,user,iid,body.request_key,limits)
            spec.require(old == body)
            return value
        if len(c.execute(select(delivery_graph_requests.c.request_key).where(
                delivery_graph_requests.c.app_id == iid, delivery_graph_requests.c.kind == PREVIEW)).all()) >= 32:
            raise DomainError("BUDGET_EXCEEDED", "Finite local logic proposal capacity exhausted")
        value = calculate(store,c,user,iid,limits,body,prepared=current)
        remember(c,user,iid,PREVIEW,body.request_key,body,value)
        return value


@graph.controlled
def load_preview(store,c,user,iid,key,limits,*,original=True,_verified_origin=None,_prepared=None):
    if original and _verified_origin is None and _prepared is None:
        from .project_natural_revalidation import local_preview_segment
        segment=local_preview_segment(store,c,user,iid,key,limits)
        if segment is not None:return segment
    current = _prepared or context(store,c,user,iid,limits,original=original,_verified_origin=_verified_origin)
    spec.require(current[0]['instance_id']==iid and current[0]['principal_id']==user
        and current[0]['limits']==limits.model_dump())
    ctx,_,release,saved = current
    body,value = pair(c,user,iid,PREVIEW,key,Preview)
    frozen = copy.deepcopy(value["context"])
    if not original:
        frozen.pop("instance_revision")
        frozen.pop("data_version")
    spec.require(ctx == frozen, "Original app, authority, Goal, graph or instance version changed")
    if original:
        spec.require(calculate(store,c,user,iid,limits,body,prepared=current) == value, "Exact local logic proposal changed")
    else:
        candidate,_ = effective(saved.get("effective_candidate",release["snapshot"]["draft"]["candidate"]),body.consume_prior_feedback,limits)
        spec.require(candidate == value["effective_candidate"])
        check = copy.deepcopy(value)
        fp = check.pop("preview_fingerprint")
        spec.require(fingerprint(check) == fp)
    return body,value


def reference(iid,key,value):
    return Reference(instance_id=iid,preview_key=key,preview_fingerprint=value["preview_fingerprint"])


def check_job(store,c,user,job,snapshot,release,limits):
    ref = Reference.model_validate(snapshot["logic_check"])
    body,sealed = pair(c,user,job["id"],JOB,"accepted",Reference)
    spec.require(body == ref and sealed == ref.model_dump())
    _,value = load_preview(store,c,user,ref.instance_id,ref.preview_key,limits,
        original=job["status"] != "SUCCEEDED")
    spec.require(ref.preview_fingerprint == value["preview_fingerprint"]
        and release["id"] == value["context"]["release_id"]
        and snapshot["instance_id"] != ref.instance_id)
    return effective_bound(release,value,limits,original=job["status"] != "SUCCEEDED")


def effective_bound(release,value,limits,*,original=True):
    candidate = value["effective_candidate"]
    manifest,_,report = natural.compile_candidate(candidate,limits)
    draft = {**copy.deepcopy(release["snapshot"]["draft"]), "candidate":candidate,
        "fingerprint":fingerprint(candidate), "natural_logic_audit":value["context"]["audit_fingerprint"],
        "natural_logic_preview":value["preview_fingerprint"],
        "natural_logic_origin":dict(instance_id=value["context"]["instance_id"],
            preview_key=value["request_key"],limits=limits.model_dump(),original=original)}
    return draft,manifest,report,value["context"]["source"],value["context"]["goal"]


def checked(store,c,user,iid,key,limits,*,original=True,_project_partial=False):
    _,value = load_preview(store,c,user,iid,key,limits,original=original)
    body,started = pair(c,user,iid,CHECK,key,Check)
    spec.require(body.expected_preview_fingerprint == value["preview_fingerprint"])
    jid = started["run_id"]
    from . import owner_acceptance as owner
    owner.natural_scope(store,c,user,started["check_instance_id"],jid)
    owner.natural_authority(store,c,user,started["check_instance_id"],jid)
    job = c.execute(select(runs).where(runs.c.id == jid, runs.c.principal_id == user)).mappings().one()
    spec.require(job["status"] == "SUCCEEDED" and not job["cancel_intent"], "Actual local logic validation has not succeeded")
    bound,outputs,proved = spec.verify_job(store,c,user,job,limits)
    if "project_check" in bound["snapshot"] and not _project_partial:
        from .project_natural_revalidation import require_complete_checks
        require_complete_checks(store,c,user,bound["snapshot"]["project_check"],limits)
    spec.require(bound["draft"]["candidate"] == value["effective_candidate"]
        and len(proved) == 6 and bound["snapshot"]["logic_check"] == reference(iid,key,value).model_dump())
    result = dict(namespace=VERSION,run_id=jid,check_instance_id=started["check_instance_id"],
        preview_fingerprint=value["preview_fingerprint"], effective_fingerprint=value["effective_fingerprint"],
        actual_proof_fingerprint=fingerprint(dict(job=dict(job),output=outputs,proved=proved)),
        status="PASS",citation_status="PASS",semantic_status="UNKNOWN",owner_acceptance="PENDING")
    result["check_fingerprint"] = fingerprint(result)
    if graph.lookup(c,user,iid,CHECKED,key):
        old,sealed=pair(c,user,iid,CHECKED,key,Check)
        spec.require(old == body and sealed == result, "Actual check receipt changed")
    else:
        remember(c,user,iid,CHECKED,key,body,result)
    return value,result


@graph.controlled
def execution_digest(store,c,user,value,started):
    """Exact bytes after full Worker readback; no cross-transaction cache.

    A sealed digest never substitutes for the first actual verification or final
    version approval verification. Later reads authorize every frozen pointer
    first, then require byte equality of the complete proven history.
    """
    from . import owner_acceptance as owner
    from .db import (
        internal_app_runs,
        internal_instance_data,
        internal_instances,
        internal_run_bindings,
    )
    from .natural_spec_corrections import proof_digest
    from .tools import authorized_read
    ctx=value["context"]
    from .db import internal_run_bindings as project_bindings
    from .project_natural_revalidation import require_complete_checks
    project_ref=c.execute(select(project_bindings.c.snapshot["project_check"]).where(project_bindings.c.run_id==started["run_id"])).scalar_one()
    if project_ref is not None:
        require_complete_checks(store,c,user,project_ref,Limits(**value["context"]["limits"]))
    owner.natural_scope(store,c,user,started["check_instance_id"],started["run_id"])
    owner.natural_authority(store,c,user,started["check_instance_id"],started["run_id"])
    expected=reference(ctx["instance_id"],value["request_key"],value)
    job_ref,job_seal=pair(c,user,started["run_id"],JOB,"accepted",Reference)
    spec.require(job_ref == expected and job_seal == expected.model_dump(), "Actual logic check seals changed")
    _,proof=pair(c,user,ctx["instance_id"],CHECKED,value["request_key"],Check)
    spec.require(proof["run_id"] == started["run_id"] and proof["check_instance_id"] == started["check_instance_id"]
        and proof["preview_fingerprint"] == value["preview_fingerprint"] and proof["effective_fingerprint"] == value["effective_fingerprint"])
    coverage=c.execute(select(internal_instance_data.c.run_id,internal_instance_data.c.version,
        internal_instance_data.c.release_id).where(
            internal_instance_data.c.instance_id == started["check_instance_id"])).all()
    spec.require(coverage == [(started["app_run_id"],1,ctx["release_id"])],
        "Isolated validation instance has other or changed typed history")
    job=c.execute(select(runs).where(runs.c.id == started["run_id"],runs.c.principal_id == user,
        runs.c.project_id == ctx["project_id"],runs.c.runtime_id == ctx["runtime_id"])).mappings().one()
    spec.require(job["status"] == "SUCCEEDED" and not job["cancel_intent"])
    binding=c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == job["id"])).mappings().one()
    snap=binding["snapshot"]
    spec.require(snap["instance_id"] == started["check_instance_id"]
        and snap["app_run_id"] == started["app_run_id"] and snap["release_id"] == ctx["release_id"]
        and snap["logic_check"] == reference(ctx["instance_id"],value["request_key"],value).model_dump())
    app=c.execute(select(internal_app_runs).where(internal_app_runs.c.id == started["app_run_id"],
        internal_app_runs.c.instance_id == started["check_instance_id"],internal_app_runs.c.principal_id == user)).mappings().one()
    spec.require(app["status"] == "SUCCEEDED" and app["release_id"] == ctx["release_id"])
    artifact=app["output"]["resource_id"]
    authorized_read(store,c,user,ctx["runtime_id"],ctx["project_id"],"resource.read",dict(resource_id=artifact))
    goal=ctx["goal"]
    full=proof_digest(c,job["id"],ctx["source"]["resource_id"],artifact,goal["card_id"],goal["version"],ctx["project_id"])
    instance=c.execute(select(internal_instances).where(internal_instances.c.id == started["check_instance_id"],
        internal_instances.c.principal_id == user)).mappings().one()
    spec.require(instance["source_app_id"] == ctx["app_id"] and instance["release_id"] == ctx["release_id"]
        and instance["runtime_id"] == ctx["runtime_id"] and instance["project_id"] == ctx["project_id"])
    spec.require(instance["data_version"] == 1)
    rows=c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == started["check_instance_id"],
        internal_instance_data.c.run_id == started["app_run_id"])).mappings().all()
    return fingerprint(dict(full=full,app=dict(app),instance=dict(instance),typed=[dict(r) for r in rows]))


@graph.controlled
def validate_snapshot(store,c,user,snapshot,limits,*,commit=False,_verified_origin=None):
    origin = snapshot["natural_logic_source"]
    spec.require(set(origin) == {"namespace","instance_id","preview_key","preview_fingerprint","check_fingerprint","execution_digest"}
        and origin["namespace"] == VERSION)
    if commit:
        value,proof = checked(store,c,user,origin["instance_id"],origin["preview_key"],limits)
        spec.require(proof["check_fingerprint"] == origin["check_fingerprint"])
    else:
        _,value=load_preview(store,c,user,origin["instance_id"],origin["preview_key"],limits,original=False,_verified_origin=_verified_origin)
    _,started=pair(c,user,origin["instance_id"],CHECK,origin["preview_key"],Check)
    _,sealed=pair(c,user,origin["instance_id"],CHECKED,origin["preview_key"],Check)
    spec.require(sealed["check_fingerprint"] == origin["check_fingerprint"])
    spec.require(execution_digest(store,c,user,value,started) == origin["execution_digest"]
        and value["preview_fingerprint"] == origin["preview_fingerprint"]
        and snapshot["draft"]["fingerprint"] == value["context"]["draft_fingerprint"])
    return value


def release_bound(store,c,user,release,limits):
    return effective_bound(release,validate_snapshot(store,c,user,release["snapshot"],limits),limits,original=False)



def propose_version_tx(store,c,user,iid,body,limits):
    value,proof=checked(store,c,user,iid,body.request_key,limits)
    spec.require(body.expected_check_fingerprint == proof["check_fingerprint"])
    if graph.lookup(c,user,iid,APPROVAL,body.request_key):
        old,result=pair(c,user,iid,APPROVAL,body.request_key,Version)
        spec.require(old == body)
        return result
    _,_,release,_=context(store,c,user,iid,limits)
    snap=copy.deepcopy(release["snapshot"])
    _,started=pair(c,user,iid,CHECK,body.request_key,Check)
    snap["natural_logic_source"]=dict(namespace=VERSION,instance_id=iid,preview_key=body.request_key,
        preview_fingerprint=value["preview_fingerprint"],check_fingerprint=proof["check_fingerprint"],
        execution_digest=execution_digest(store,c,user,value,started))
    snap["check_evidence"]={**proof,"original_draft_fingerprint":snap["draft"]["fingerprint"]}
    result=lifecycle.new_approval(c,user,value["context"]["project_id"],"release",
        dict(snapshot=snap,grant_version=lifecycle.grant_version(c,value["context"]["project_id"],user)))
    result["snapshot_fingerprint"] = fingerprint(snap)
    result["snapshot"] = snap
    result["expires_at"] = lifecycle.approval(c,user,result["id"],result["fingerprint"],"release")["expires_at"]
    remember(c,user,iid,APPROVAL,body.request_key,body,result)
    return result


def mount(app,store,limits,identity):
    dep=Depends(identity)
    base="/api/internal/instances/{iid}/logic-patches"
    @app.get(base + "/context")
    def baseline(iid:str,user=dep):
        with store.tx() as c:
            ctx,_,release,saved=context(store,c,user,iid,limits,_allow_last=True)
            candidate=saved.get("effective_candidate",release["snapshot"]["draft"]["candidate"])
            return dict(namespace=VERSION+".context",context=ctx,base_candidate=candidate,
                graph={**graph.metadata(saved),"graph":saved["graph"],"source_versions":saved["source_versions"]},
                remaining_adjustments=3-candidate["manifest"]["revision"])

    @app.post(base + "/previews",status_code=201)
    def prepare(iid:str,body:Preview,user=dep):
        return preview(store,user,iid,limits,body)

    @app.get(base + "/previews/{key}")
    def read(iid:str,key:str,user=dep):
        with store.tx() as c:
            return load_preview(store,c,user,iid,key,limits)[1]

    @app.post(base + "/checks",status_code=202)
    def start(iid:str,body:Check,user=dep):
        from .app_jobs import enqueue
        with proposal_tx(store,user,iid,"checks",body,CHECK) as c:
            _,value=load_preview(store,c,user,iid,body.request_key,limits)
            spec.require(body.expected_preview_fingerprint == value["preview_fingerprint"])
            if graph.lookup(c,user,iid,CHECK,body.request_key):
                old,result=pair(c,user,iid,CHECK,body.request_key,Check)
                spec.require(old == body)
                return result
            ctx=value["context"]
            inst=lifecycle.create_instance_tx(store,c,user,ctx["release_id"],ctx["release_fingerprint"],limits,
                request_key="logic-check:"+fingerprint(dict(iid=iid,key=body.request_key)))
            # Explicit parent transaction keeps instance, queue and seal atomic.
            result=enqueue(store,user,inst["id"],inst["revision"],ctx["release_fingerprint"],{},
                body.request_key,limits,logic_check=reference(iid,body.request_key,value), logic_tx=c)
            result={**result,"check_instance_id":inst["id"]}
            remember(c,user,iid,CHECK,body.request_key,body,result)
            return result

    @app.get(base + "/checks/{key}")
    def outcome(iid:str,key:str,user=dep):
        with store.tx() as c:
            load_preview(store,c,user,iid,key,limits)
            _,started=pair(c,user,iid,CHECK,key,Check)
            spec.require(spec.job_scope_gate(store,c,user,started["run_id"]))
            job=c.execute(select(runs.c.status).where(runs.c.id == started["run_id"])).scalar()
            if job != "SUCCEEDED":
                return {**started,"status":job,"check_status":"NOT_PASSED"}
            return checked(store,c,user,iid,key,limits)[1]

    @app.get(base + "/check-controls/{key}")
    def control(iid:str,key:str,user=dep):
        # Owned metadata remains readable for cancellation after source revocation.
        from . import owner_acceptance as owner
        with store.tx() as c:
            owner.scope(store,c,user,iid)
            accepted_body,started=pair(c,user,iid,CHECK,key,Check)
            owner.natural_scope(store,c,user,started["check_instance_id"],started["run_id"])
            job=c.execute(select(runs.c.status,runs.c.version,runs.c.cancel_intent)
                .where(runs.c.id == started["run_id"],runs.c.principal_id == user)).mappings().one()
            proof={}
            if graph.lookup(c,user,iid,CHECKED,key):
                _,sealed=pair(c,user,iid,CHECKED,key,Check)
                proof={k:sealed[k] for k in ("check_fingerprint","actual_proof_fingerprint")}
            return dict(namespace=VERSION+".control",instance_id=iid,request_key=key,
                check_instance_id=started["check_instance_id"],run_id=started["run_id"],
                principal_id=user,accepted_request_fingerprint=fingerprint(accepted_body.model_dump()),**dict(job),**proof)

    @app.post(base + "/version-approvals",status_code=201)
    def propose(iid:str,body:Version,user=dep):
        with proposal_tx(store,user,iid,"version-approvals",body,APPROVAL) as c:
            return propose_version_tx(store,c,user,iid,body,limits)

    @app.get(base + "/version-approvals/{key}")
    def recover(iid:str,key:str,user=dep):
        with store.tx() as c:
            load_preview(store,c,user,iid,key,limits)
            return pair(c,user,iid,APPROVAL,key,Version)[1]


@graph.controlled
def validate_family(c,user,approval_id,snapshot):
    rows=c.execute(select(delivery_graph_requests.c.app_id,delivery_graph_requests.c.request_key)
        .where(delivery_graph_requests.c.kind == APPROVAL,
            delivery_graph_requests.c.snapshot["response"]["id"].as_string() == approval_id)).mappings().all()
    spec.require(bool(rows) == ("natural_logic_source" in snapshot), "Logic version origin cannot be removed")
    if rows:
        spec.require(len(rows) == 1)
        row=rows[0]
        _,sealed=pair(c,user,row["app_id"],APPROVAL,row["request_key"],Version)
        spec.require(sealed["id"] == approval_id and sealed["snapshot_fingerprint"] == fingerprint(snapshot))
