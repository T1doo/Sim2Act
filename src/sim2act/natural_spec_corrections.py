"""One explicitly approved correction of an original natural-spec result.

No change to original goals, criteria, outputs, grants or model budgets. No
corrections-of-corrections: the first slice has a single acyclic parent edge.
"""
import copy
import time
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import natural_specs
from . import owner_acceptance as owner
from . import pa_spec_apps as spec
from .contracts import Limits, Strict
from .db import (
    delivery_graph_requests,
    events,
    fingerprint,
    goal_cards,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    runs,
)
from .errors import DomainError
from .text_logic_reuse import pair, remember
from .tools import authorized_read

VERSION = "natural-spec-correction.v1"
REVIEW = VERSION + ".review"
ACCEPTED = VERSION + ".accepted"
CONSENT = "RUN_NEW_BOUNDED_CORRECTION_KEEP_ORIGINAL_GOAL_AND_CRITERIA"
HASH = r"^[a-f0-9]{64}$"
MAX_REVIEWS = 32


class Prepare(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_owner_sequence: int = Field(ge=1)
    declaration_id: str
    declaration_fingerprint: str = Field(pattern=HASH)
    expected_context_fingerprint: str = Field(pattern=HASH)


class Commit(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_review_fingerprint: str = Field(pattern=HASH)
    consent: Literal["RUN_NEW_BOUNDED_CORRECTION_KEEP_ORIGINAL_GOAL_AND_CRITERIA"]


class Reference(Strict):
    parent_run_id: str
    instance_id: str
    review_key: str
    review_fingerprint: str = Field(pattern=HASH)
    declaration_id: str
    declaration_fingerprint: str = Field(pattern=HASH)
    declaration_sequence: int
    parent_app_run_id: str
    parent_typed_fingerprint: str = Field(pattern=HASH)
    parent_output_fingerprint: str = Field(pattern=HASH)
    parent_binding_fingerprint: str = Field(pattern=HASH)
    parent_proof_digest: str = Field(pattern=HASH)
    parent_material_id: str
    parent_artifact_id: str
    project_id: str
    base_data_version: int
    instance_revision: int
    release_id: str
    goal_id: str
    goal_version: int
    goal_fingerprint: str = Field(pattern=HASH)



def bounded_limits(*limits):
    return Limits(**{name:min(getattr(x,name) for x in limits) for name in Limits.model_fields})


def proof_digest(c,rid,material,artifact,goal,version,project):
    # Called only after parent material/artifact scope authorization. Snapshot was
    # fully verify_job-proven at preview; equality revalidates every frozen byte.
    from .db import (
        attempts,
        goal_card_versions,
        local_effects,
        operation_intents,
        operations,
        reservations,
        resources,
        run_contracts,
    )
    tables=[(runs,runs.c.id == rid),(internal_run_bindings,internal_run_bindings.c.run_id == rid),
        (run_contracts,run_contracts.c.run_id == rid),(attempts,attempts.c.run_id == rid),
        (operations,operations.c.run_id == rid),(events,events.c.run_id == rid)]
    op_ids=select(operations.c.id).where(operations.c.run_id == rid)
    attempt_ids=select(attempts.c.id).where(attempts.c.run_id == rid)
    bound_snapshot=c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == rid)).scalar_one()
    source_ids=c.execute(select(runs.c.resource_refs).where(runs.c.id == rid)).scalar_one()
    artifact_ids=c.execute(select(local_effects.c.resource_id).where(local_effects.c.operation_id.in_(op_ids))).scalars().all()
    frozen_goal=bound_snapshot.get("spec_goal")
    goal_project=c.execute(select(goal_cards.c.project_id).where(goal_cards.c.id == goal)).scalar()
    spec.require(source_ids == [material] and artifact_ids == [artifact]
        and isinstance(frozen_goal,dict) and frozen_goal.get("card_id") == goal
        and frozen_goal.get("version") == version and goal_project == project,
        "Source proof pointers differ from independently authorized frozen scope")
    # Never follow poisoned Run/binding/effect pointers to extra private objects.
    tables.extend([(resources,resources.c.id.in_([material,artifact])),
        (goal_cards,goal_cards.c.id == goal),
        (goal_card_versions,(goal_card_versions.c.card_id == goal) &
            (goal_card_versions.c.version == version)),(operation_intents,operation_intents.c.operation_id.in_(op_ids)),
        (local_effects,local_effects.c.operation_id.in_(op_ids)),
        (reservations,reservations.c.id.in_(attempt_ids))])
    return fingerprint({table.name:sorted((dict(r) for r in c.execute(select(table).where(condition)).mappings()),
        key=fingerprint) for table,condition in tables})


def rejected(c, user, iid, rid, declaration_id, declaration_fp, sequence):
    rows = owner.natural_ledger(c, user, iid, rid)
    spec.require(rows and len(rows) == sequence and rows[-1]["kind"] == "DECIDE"
        and rows[-1]["status"] == "REJECTED" and rows[-1]["id"] == declaration_id
        and rows[-1]["fingerprint"] == declaration_fp, "Rejected declaration changed or was revoked")
    return rows[-1]


def preview(store, user, iid, rid, limits, body):
    with store.tx() as c:
        owner.natural_scope(store,c,user,iid,rid)
        logic = c.execute(select(internal_releases.c.snapshot["natural_logic_source"]["namespace"].as_string())
            .join(internal_instances,internal_instances.c.release_id == internal_releases.c.id)
            .where(internal_instances.c.id == iid,internal_instances.c.principal_id == user)).scalar()
        if logic is not None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Corrections of this finite logic version are not supported")
        owner.natural_authority(store,c,user,iid,rid)
        old = c.execute(select(delivery_graph_requests.c.app_id).where(
            delivery_graph_requests.c.app_id == iid, delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.kind == REVIEW, delivery_graph_requests.c.request_key == body.request_key)).first()
        if old:
            original, value = pair(c,user,iid,REVIEW,body.request_key,Prepare)
            spec.require(original == body and value["parent_run_id"] == rid)
            return value
        # Never recursively broaden the correction lineage or create a sibling.
        spec.require(not hint(c,rid), "Corrections-of-corrections are outside this finite slice")
        spec.require(c.execute(select(delivery_graph_requests.c.app_id).where(
            delivery_graph_requests.c.kind == ACCEPTED,
            delivery_graph_requests.c.snapshot["response"]["reference"]["parent_run_id"].as_string() == rid)).first() is None,
            "This rejection already has an accepted correction")
        count = len(c.execute(select(delivery_graph_requests.c.app_id).where(
            delivery_graph_requests.c.app_id == iid, delivery_graph_requests.c.kind == REVIEW)).all())
        if count >= MAX_REVIEWS:
            raise DomainError("BUDGET_EXCEEDED", "Finite correction preview capacity exhausted")
        context = owner.natural_context(store,c,user,iid,rid,limits)
        spec.require(fingerprint(context) == body.expected_context_fingerprint)
        row = rejected(c,user,iid,rid,body.declaration_id,body.declaration_fingerprint,body.expected_owner_sequence)
        declaration = owner.natural_payload(c,row)
        spec.require(fingerprint(declaration["contract"]) == fingerprint(context))
        job = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        binding,_,_ = spec.verify_job(store,c,user,job,limits)
        value = dict(namespace=VERSION,principal_id=user,project_id=context["project_id"],
            instance_id=iid,parent_run_id=rid,request_key=body.request_key,
            declaration=dict(row,payload=declaration),context=context,
            effective_candidate=binding["draft"]["candidate"],
            parent_binding_fingerprint=job["fingerprint"],parent_proof_digest=proof_digest(c,rid,context["material"]["resource_id"],context["output"]["resource_id"],
                context["source_goal"]["card_id"],context["source_goal"]["version"],context["project_id"]),
            proposed_limits=bounded_limits(limits,store.frozen_contract(c,job).limits,
                Limits(**binding["draft"]["candidate"]["manifest"]["runtime_limits"])).model_dump(),
            proposed_model_nodes=sum(x["executor"]["ref"] in natural_specs.MODEL_KINDS for x in binding["draft"]["candidate"]["actions"]),
            proposed_artifact_writes_at_most=1,real_model_allowance=0,expires_at=time.time()+900,
            consent=CONSENT,new_model_requests=0,artifact_writes=0,
            semantic_status="UNKNOWN",owner_acceptance="PENDING",formal_publication_enabled=False)
        value["review_fingerprint"] = fingerprint(value)
        owner.natural_final_gate(store,c,user,iid,rid,context)
        remember(c,user,iid,REVIEW,body.request_key,body,value)
        return value


def load_review(store,c,user,iid,rid,key):
    owner.natural_scope(store,c,user,iid,rid)
    owner.natural_authority(store,c,user,iid,rid)
    original,value = pair(c,user,iid,REVIEW,key,Prepare)
    spec.require(value["parent_run_id"] == rid and value["instance_id"] == iid
        and value["principal_id"] == user and value["request_key"] == key)
    unsigned={k:v for k,v in value.items() if k != "review_fingerprint"}
    spec.require(value["review_fingerprint"] == fingerprint(unsigned))
    return original,value


def approve(store,c,user,iid,rid,limits,body,value):
    original,fresh = load_review(store,c,user,iid,rid,body.request_key)
    spec.require(limits.model_dump() == value["proposed_limits"], "Frozen correction limits changed")
    spec.require(fresh == value and body.expected_review_fingerprint == fresh["review_fingerprint"]
        and time.time() < fresh["expires_at"], "Correction confirmation expired or changed")
    spec.require(not hint(c,rid))
    spec.require(c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.kind == ACCEPTED,
        delivery_graph_requests.c.snapshot["response"]["reference"]["parent_run_id"].as_string() == rid)).first() is None)
    current = owner.natural_context(store,c,user,iid,rid,limits)
    spec.require(current == fresh["context"], "Original Goal, criteria, material or result changed")
    row = rejected(c,user,iid,rid,original.declaration_id,original.declaration_fingerprint,original.expected_owner_sequence)
    spec.require(owner.natural_payload(c,row) == fresh["declaration"]["payload"])
    spec.require(fingerprint(fresh["effective_candidate"]) == current["effective_plan_fingerprint"])
    owner.natural_final_gate(store,c,user,iid,rid,current,expires_at=fresh["expires_at"])
    return fresh


def reference(value):
    ctx=value["context"]
    row=value["declaration"]
    return Reference(parent_run_id=value["parent_run_id"],instance_id=value["instance_id"],
        review_key=value["request_key"],review_fingerprint=value["review_fingerprint"],
        declaration_id=row["id"],declaration_fingerprint=row["fingerprint"],declaration_sequence=row["sequence"],
        parent_app_run_id=ctx["app_run_id"],parent_typed_fingerprint=ctx["typed_fingerprint"],
        parent_output_fingerprint=ctx["output_fingerprint"],parent_binding_fingerprint=value["parent_binding_fingerprint"],parent_proof_digest=value["parent_proof_digest"],parent_material_id=ctx["material"]["resource_id"],
        parent_artifact_id=ctx["output"]["resource_id"],project_id=ctx["project_id"],
        base_data_version=ctx["result_version"],instance_revision=ctx["instance_revision"],release_id=ctx["release_id"],
        goal_id=ctx["source_goal"]["card_id"],goal_version=ctx["source_goal"]["version"],goal_fingerprint=ctx["source_goal"]["fingerprint"])


def seal(c,user,snapshot,ref):
    remember(c,user,snapshot["run_id"],ACCEPTED,"accepted",ref,
        dict(reference=ref.model_dump(),run_id=snapshot["run_id"],app_run_id=snapshot["app_run_id"],
            binding_fingerprint=fingerprint(snapshot)))


def hint(c,rid):
    return bool(c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.app_id == rid,delivery_graph_requests.c.kind.in_([ACCEPTED,ACCEPTED+"_seal"]))).first()
        or c.execute(select(internal_run_bindings.c.snapshot["human_correction"]["parent_run_id"].as_string())
            .where(internal_run_bindings.c.run_id == rid)).scalar()
        or c.execute(select(events.c.id).where(events.c.run_id == rid,events.c.kind == "HUMAN_CORRECTION_ACCEPTED")).first())


def gate(store,c,user,rid):
    if not hint(c,rid):
        return None
    ref,frozen=pair(c,user,rid,ACCEPTED,"accepted",Reference)
    spec.require(frozen["reference"] == ref.model_dump() and frozen["run_id"] == rid
        and ref.parent_run_id != rid and not hint(c,ref.parent_run_id))
    accepted=c.execute(select(events.c.data).where(events.c.run_id == rid,
        events.c.kind == "HUMAN_CORRECTION_ACCEPTED")).scalars().all()
    spec.require(accepted == [dict(parent_run_id=ref.parent_run_id,review_key=ref.review_key,
        review_fingerprint=ref.review_fingerprint)])
    owner.natural_scope(store,c,user,ref.instance_id,ref.parent_run_id)
    authority=owner.natural_authority(store,c,user,ref.instance_id,ref.parent_run_id)
    spec.require(authority["project_id"] == ref.project_id)
    rejected(c,user,ref.instance_id,ref.parent_run_id,ref.declaration_id,ref.declaration_fingerprint,ref.declaration_sequence)
    head=c.execute(select(goal_cards.c.version,goal_cards.c.fingerprint).where(goal_cards.c.id == ref.goal_id)).mappings().first()
    i=c.execute(select(internal_instances.c.revision,internal_instances.c.release_id,internal_instances.c.data_version)
        .where(internal_instances.c.id == ref.instance_id)).mappings().one()
    parent=c.execute(select(internal_run_bindings.c.fingerprint).where(internal_run_bindings.c.run_id == ref.parent_run_id)).scalar()
    typed=c.execute(select(internal_instance_data.c.fingerprint,internal_instance_data.c.version).where(
        internal_instance_data.c.instance_id == ref.instance_id,internal_instance_data.c.run_id == ref.parent_app_run_id)).mappings().first()
    child=c.execute(select(runs.c.status,runs.c.fingerprint).where(runs.c.id == rid,runs.c.principal_id == user)).mappings().one()
    own_stage = c.execute(select(internal_app_runs.c.result_version).where(
        internal_app_runs.c.id == frozen["app_run_id"],internal_app_runs.c.instance_id == ref.instance_id,
        internal_app_runs.c.status == "SUCCEEDED",internal_app_runs.c.result_version == ref.base_data_version+1)).scalar()
    own_typed = c.execute(select(internal_instance_data.c.version).where(
        internal_instance_data.c.instance_id == ref.instance_id,internal_instance_data.c.run_id == frozen["app_run_id"],
        internal_instance_data.c.version == ref.base_data_version+1)).scalar()
    spec.require(head and head["version"] == ref.goal_version and head["fingerprint"] == ref.goal_fingerprint
        and i["revision"] == ref.instance_revision and i["release_id"] == ref.release_id
        and parent == ref.parent_binding_fingerprint and typed and typed["fingerprint"] == ref.parent_typed_fingerprint
        and typed["version"] == ref.base_data_version and child["fingerprint"] == frozen["binding_fingerprint"]
        and (child["status"] in {"SUCCEEDED","FAILED","CANCELLED"} or i["data_version"] == ref.base_data_version or
            i["data_version"] == own_stage == own_typed == ref.base_data_version+1),
        "Correction source was revoked or a competing result committed")
    owner.natural_payload(c,rejected(c,user,ref.instance_id,ref.parent_run_id,ref.declaration_id,ref.declaration_fingerprint,ref.declaration_sequence))
    spec.require(proof_digest(c,ref.parent_run_id,ref.parent_material_id,ref.parent_artifact_id,ref.goal_id,ref.goal_version,ref.project_id) == ref.parent_proof_digest, "Original actual Worker proof changed")
    return ref


def bound(store,c,user,job,snapshot,release,limits):
    ref=gate(store,c,user,job["id"])
    spec.require(ref is not None and snapshot["human_correction"] == ref.model_dump())
    _,value=load_review(store,c,user,ref.instance_id,ref.parent_run_id,ref.review_key)
    spec.require(reference(value) == ref)
    row=rejected(c,user,ref.instance_id,ref.parent_run_id,ref.declaration_id,ref.declaration_fingerprint,ref.declaration_sequence)
    spec.require(owner.natural_payload(c,row) == value["declaration"]["payload"])
    typed=c.execute(select(internal_instance_data).where(internal_instance_data.c.run_id == ref.parent_app_run_id)).mappings().one()
    parent=c.execute(select(internal_app_runs.c.output).where(internal_app_runs.c.id == ref.parent_app_run_id)).scalar()
    spec.require(fingerprint(typed["data"]) == ref.parent_typed_fingerprint and fingerprint(parent) == ref.parent_output_fingerprint)
    candidate=value["effective_candidate"]
    spec.require(fingerprint(candidate) == value["context"]["effective_plan_fingerprint"])
    manifest,_,report=natural_specs.compile_candidate(candidate,limits)
    draft={**copy.deepcopy(release["snapshot"]["draft"]),"candidate":candidate,
        "fingerprint":fingerprint(candidate),"correction_run_id":job["id"]}
    source=authorized_read(store,c,user,job["runtime_id"],job["project_id"],"resource.read",
        dict(resource_id=value["context"]["material"]["resource_id"]))
    spec.require(source == value["context"]["material"])
    return draft,manifest,report,source,value["context"]["source_goal"]


def feedback(store,c,user,job,snapshot):
    ref=gate(store,c,user,job["id"])
    if not ref:
        return None
    _,value=load_review(store,c,user,ref.instance_id,ref.parent_run_id,ref.review_key)
    criteria={x["id"]:x["text"] for x in value["context"]["items"]}
    issues=[dict(item_id=x["item_id"],criterion=criteria[x["item_id"]],reason=x["reason"],
        new_result_assessment="MANUAL_REVIEW_REQUIRED") for x in value["declaration"]["payload"]["choices"] if x["decision"] == "REJECT"]
    return dict(reference=ref.model_dump(),original_goal=value["context"]["goal"],
        original_criteria=value["context"]["items"],issues=issues,
        original_checklist=value["context"]["output"]["checklist"],semantic_status="UNKNOWN")



def rejection_proof(c,user,iid,rid,body):
    # Metadata only, owned project/instance lock has been checked by caller.
    if c.execute(select(internal_app_runs.c.id).where(internal_app_runs.c.instance_id == iid,
        internal_app_runs.c.principal_id == user,internal_app_runs.c.request_key == body.request_key)).first():
        return None
    if c.execute(select(delivery_graph_requests.c.app_id).where(delivery_graph_requests.c.kind == ACCEPTED,
        delivery_graph_requests.c.snapshot["request"]["instance_id"].as_string() == iid,
        delivery_graph_requests.c.snapshot["request"]["review_key"].as_string() == body.request_key)).first():
        return None
    pid=c.execute(select(internal_instances.c.project_id).where(internal_instances.c.id == iid,
        internal_instances.c.principal_id == user)).scalar()
    if not pid:
        return None
    return dict(namespace="internal-run-rejection.v1",endpoint="correction-runs",principal_id=user,
        project_id=pid,instance_id=iid,parent_run_id=rid,request_key=body.request_key,
        request_fingerprint=fingerprint(body.model_dump()),acceptance="NOT_ACCEPTED",previous_request="ABSENT",
        phase="CORRECTION_TX_ROLLED_BACK")


def mount(app,store,limits,identity):
    dep=Depends(identity)
    @app.post("/api/internal/instances/{iid}/runs/{rid}/correction-reviews")
    def prepare(iid:str,rid:str,body:Prepare,user=dep):
        return preview(store,user,iid,rid,limits,body)

    @app.get("/api/internal/instances/{iid}/runs/{rid}/correction-reviews/{key}")
    def read_preview(iid:str,rid:str,key:str,user=dep):
        with store.tx() as c:
            _,value=load_review(store,c,user,iid,rid,key)
            return value

    @app.post("/api/internal/instances/{iid}/runs/{rid}/correction-runs",status_code=202)
    def submit(iid:str,rid:str,body:Commit,user=dep):
        from .app_jobs import enqueue, submission_tx
        guard: dict = {}
        with submission_tx(store,guard) as c:
            owner.natural_scope(store,c,user,iid,rid)
            guard["proof"]=rejection_proof(c,user,iid,rid,body)
            _,value=load_review(store,c,user,iid,rid,body.request_key)
        return enqueue(store,user,iid,value["context"]["instance_revision"],value["context"]["release_fingerprint"],
            {},body.request_key,bounded_limits(limits,Limits(**value["proposed_limits"])),human_correction=(body,value),
            submission=dict(endpoint="correction-runs",body=body.model_dump()))

    @app.get("/api/internal/instances/{iid}/runs/{rid}/correction-requests/{key}")
    def recover(iid:str,rid:str,key:str,user=dep):
        with store.tx() as c:
            _,value=load_review(store,c,user,iid,rid,key)
            child=c.execute(select(delivery_graph_requests.c.app_id).where(
                delivery_graph_requests.c.kind == ACCEPTED,
                delivery_graph_requests.c.snapshot["request"]["parent_run_id"].as_string() == rid,
                delivery_graph_requests.c.snapshot["request"]["review_key"].as_string() == key)).scalar()
            if child is None:
                raise DomainError("OUTCOME_UNKNOWN","No accepted correction Run for this original key")
            spec.require(spec.job_scope_gate(store,c,user,child))
            job=c.execute(select(runs).where(runs.c.id == child)).mappings().one()
            binding,_,_=spec.verify_job(store,c,user,job,limits)
            return dict(namespace=VERSION,principal_id=user,project_id=job["project_id"],instance_id=iid,
                parent_run_id=rid,request_key=key,review=value,run_id=child,app_run_id=binding["app_run"]["id"],
                status=job["status"],result_version=binding["app_run"]["result_version"],
                owner_acceptance="PENDING",semantic_status="UNKNOWN",formal_publication_enabled=False)
