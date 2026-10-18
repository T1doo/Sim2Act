"""Exact natural-spec trial consent, with no production zero-fee authority yet.

This module does not send, reserve, settle, create Runs, or grant permissions.
Consent alone is never LIVE admission. The only implemented fee authority is
explicitly synthetic and can issue only a SYNTHETIC_ONLY test permit.
"""

import hashlib
import math
import time
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import Field, model_validator
from sqlalchemy import select

from .contracts import Limits, Strict
from .csv_logic_reuse import implementation
from .db import (
    attempts,
    delivery_graph_requests,
    fingerprint,
    goal_cards,
    grants,
    internal_instances,
    runs,
    task_extractions,
)
from .delivery_graph_apps import controlled, lookup
from .errors import DomainError
from .goals import GoalCardInput, validate_card_version
from .natural_specs import Recipe
from .text_logic_reuse import pair, remember
from .tools import authorized_read

VERSION: Literal["natural-live-trial.v1"] = "natural-live-trial.v1"
CLOSED = VERSION + ".preparation-closed"
SCOPE, APPROVE, REVOKE, PHASE = (VERSION + "." + s for s in ("scope", "approve", "revoke", "phase"))
CONSENT = "APPROVE_ONLY_THIS_EXACT_SEVEN_SLOT_ZERO_PAID_NATURAL_TRIAL"
HASH = r"^[a-f0-9]{64}$"
KEY = r"^[A-Za-z0-9_-]{1,100}$"
Stage = Literal["generate", "source", "cold"]


def require(ok, message="Exact natural trial changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


class TrialCaps(Strict):
    generate_requests: Literal[3] = 3
    source_requests: Literal[2] = 2
    cold_requests: Literal[2] = 2
    max_requests: Literal[7] = 7
    max_output_tokens: int = Field(default=1024, ge=1, le=1024)
    max_wire_bytes: Literal[32768] = 32768
    max_response_ascii_bytes: Literal[32768] = 32768
    per_run_reserved: Literal[64000] = 64000
    total_reserved: Literal[192000] = 192000
    total_output_tokens: Literal[7168] = 7168
    run_seconds: int = Field(default=300, ge=1, le=300)
    lease_seconds: Literal[30] = 30
    requests_per_minute: Literal[1] = 1
    paid_cap: Literal[0] = 0


class SourceSnapshot(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    hash: str = Field(pattern=HASH)
    format: Literal["txt"]


class GoalSnapshot(Strict):
    schema_version: Literal["F2-goal-card.v1"]
    content: GoalCardInput
    resource_snapshots: list[SourceSnapshot] = Field(min_length=1, max_length=1)


class MaterialGoal(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    content: str = Field(min_length=1, max_length=1024)
    source_hash: str = Field(pattern=HASH)
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    goal_version: int = Field(ge=1)
    goal_fingerprint: str = Field(pattern=HASH)
    goal_snapshot: GoalSnapshot

    @model_validator(mode="after")
    def complete(self):
        require(len(self.content.encode("utf-8")) <= 1024
                and len(self.content.splitlines()) <= 20,
                "Trial material exceeds the original finite TXT bound")
        require(hashlib.sha256(self.content.encode("utf-8")).hexdigest() == self.source_hash)
        require(self.goal_snapshot.content.resource_refs == [self.resource_id]
                and self.goal_snapshot.resource_snapshots == [SourceSnapshot(
                    resource_id=self.resource_id, hash=self.source_hash, format="txt")]
                and fingerprint(self.goal_snapshot.model_dump()) == self.goal_fingerprint,
                "Full Goal and exact material snapshots must agree")
        return self


class StageKeys(Strict):
    generate: str = Field(pattern=KEY)
    source: str = Field(pattern=KEY)
    cold: str = Field(pattern=KEY)

    @model_validator(mode="after")
    def distinct(self):
        require(len(set(self.model_dump().values())) == 3, "Stage keys must be distinct")
        return self


class TrialContract(Strict):
    namespace: Literal["natural-live-trial.v1"] = VERSION
    trial_key: str = Field(pattern=KEY)
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    principal_id: str = Field(pattern=r"^user_[a-f0-9]{32}$")
    runtime_id: str = Field(pattern=r"^runtime_[a-f0-9]{32}$")
    quota_subject: str = Field(min_length=1, max_length=200)
    software_fingerprint: str = Field(pattern=HASH)
    authorization_fingerprint: str = Field(pattern=HASH)
    bindings: list[MaterialGoal] = Field(min_length=2, max_length=2)
    stage_keys: StageKeys
    expires_at: float
    model: Literal["intern-s2"] = "intern-s2"
    endpoint: Literal["https://chat.intern-ai.org.cn/api/v1/chat/completions"] = (
        "https://chat.intern-ai.org.cn/api/v1/chat/completions")
    stream: Literal[False] = False
    caps: TrialCaps = Field(default_factory=TrialCaps)

    @model_validator(mode="after")
    def finite(self):
        require(math.isfinite(self.expires_at) and self.expires_at > 0)
        require(len({b.resource_id for b in self.bindings}) == 2
                and len({b.card_id for b in self.bindings}) == 2
                and len({b.source_hash for b in self.bindings}) == 2,
                "Two distinct complete materials and Goals are required")
        return self


class TrialContractV2(TrialContract):
    """New exact consent only. V1 is never inferred, migrated or extended."""

    namespace: Literal["natural-live-trial.v2"] = "natural-live-trial.v2"
    prepared_at: float = Field(gt=0, allow_inf_nan=False)
    review_expires_at: float = Field(gt=0, allow_inf_nan=False)
    execution_expires_at: float = Field(gt=0, allow_inf_nan=False)
    # Previous Run acceptance -> next explicit stage approval, including prior
    # Run (<=300s), queueing and human handoff. Not a completion-time guarantee.
    stage_handoff_seconds: Literal[900] = 900

    @model_validator(mode="after")
    def deadlines(self):
        require(self.review_expires_at == self.prepared_at + 300
            and self.execution_expires_at == self.prepared_at + 3600
            and self.expires_at == self.execution_expires_at,
            "Exact V2 review and execution deadlines changed")
        return self


class PBTrialContract(TrialContract):
    """P-B reuses this trial's completed source task, then a frozen edited recipe.

    Generate and source retain the original three/two slots. Only cold uses the
    extracted application; no extra source Run or cached answer is admissible.
    P-A's original serialized contract remains unchanged.
    """

    path: Literal["P-B"]
    extraction_request_key: str = Field(pattern=KEY)
    extraction_recipe: Recipe

    @model_validator(mode="after")
    def extraction_key_distinct(self):
        require(self.extraction_request_key not in self.stage_keys.model_dump().values(),
                "Extraction and model stage keys must be distinct")
        return self


def contract_model(value):
    if value.get("namespace") == "natural-live-trial.v2":
        return TrialContractV2
    require(value.get("namespace", VERSION) == VERSION, "Unknown trial contract version")
    return PBTrialContract if value.get("path") == "P-B" else TrialContract


def parse_contract(value):
    return contract_model(value).model_validate(value)


def _review_window(contract):
    if isinstance(contract, TrialContractV2):
        require(contract.prepared_at <= time.time() < contract.review_expires_at,
                "Original review deadline expired or not yet active")


class ApproveInput(Strict):
    expected_contract_fingerprint: str = Field(pattern=HASH)
    request_key: str = Field(pattern=KEY)
    consent: Literal["APPROVE_ONLY_THIS_EXACT_SEVEN_SLOT_ZERO_PAID_NATURAL_TRIAL"]


class Approval(Strict):
    contract_fingerprint: str = Field(pattern=HASH)
    principal_id: str
    project_id: str
    approved_at: float
    expires_at: float
    request: ApproveInput


class RevokeInput(Strict):
    expected_contract_fingerprint: str = Field(pattern=HASH)
    request_key: str = Field(pattern=KEY)
    consent: Literal["REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL"]


class FeeProof(Strict):
    """A server authority's answer, never accepted from a request DTO.

    A future production implementation must validate legal free entitlement AND
    a provider-side/account-side non-chargeable mechanism, their scope, freshness
    and revocation. No production implementation is registered in this slice.
    """

    scope: Literal["SYNTHETIC_ONLY", "LIVE_ZERO_FEE"]
    contract_fingerprint: str = Field(pattern=HASH)
    quota_subject: str
    expires_at: float
    legal_free_entitlement: Literal[True]
    enforced_non_chargeable: Literal[True]


class FeeAuthority(Protocol):
    def verify(self, contract: TrialContract) -> FeeProof: ...


@dataclass(frozen=True)
class SyntheticOnlyFeeAuthority:
    """Offline fixture authority, not a production registration mechanism."""

    contract_fingerprint: str
    quota_subject: str

    def verify(self, contract: TrialContract) -> FeeProof:
        require(self.contract_fingerprint == fingerprint(contract.model_dump())
                and self.quota_subject == contract.quota_subject)
        return FeeProof(scope="SYNTHETIC_ONLY", contract_fingerprint=self.contract_fingerprint,
                        quota_subject=self.quota_subject, expires_at=contract.expires_at,
                        legal_free_entitlement=True, enforced_non_chargeable=True)


class Permit(Strict):
    scope: Literal["SYNTHETIC_ONLY"]
    contract_fingerprint: str = Field(pattern=HASH)
    approval_fingerprint: str = Field(pattern=HASH)
    stage: Stage
    run_id: str
    runtime_id: str
    run_version: int
    fence: int
    expires_at: float
    live_allowed: Literal[False] = False
    stage_authority_fingerprint: str | None = Field(default=None, pattern=HASH)


class StageAuthority(Strict):
    contract_fingerprint: str = Field(pattern=HASH)
    stage: Literal["source", "cold"]
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    accepted_fingerprint: str = Field(pattern=HASH)
    app_run_id: str
    instance_id: str
    instance_revision: int = Field(ge=1)
    runtime_id: str
    app_id: str
    candidate_fingerprint: str = Field(pattern=HASH)
    recipe_fingerprint: str = Field(pattern=HASH)
    release_id: str
    release_fingerprint: str = Field(pattern=HASH)
    generation_run_id: str
    generation_candidate_fingerprint: str = Field(pattern=HASH)
    target_goal_fingerprint: str = Field(pattern=HASH)
    authorization_fingerprint: str = Field(pattern=HASH)


class StageAuthorityV2(StageAuthority):
    predecessor_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    predecessor_created_at: float = Field(gt=0, allow_inf_nan=False)
    stage_approval_expires_at: float = Field(gt=0, allow_inf_nan=False)


def _stage_deadlines(c, user, contract, stage, generation_run_id):
    if not isinstance(contract, TrialContractV2):
        return {}
    if stage == "source":
        predecessor_id, runtime = generation_run_id, contract.runtime_id
        # Generation is an accepted candidate, still semantically PARTIAL.
        statuses = {"SUCCEEDED", "PARTIAL"}
    else:
        require(stage == "cold")
        require(_keys(c, user, entity(contract), PHASE) <= {"source", "cold"})
        source = _saved(c, user, entity(contract), PHASE, "source", StageApproveInput)
        original = _saved(c, user, entity(contract), APPROVE, "approve", Approval)
        generation_at = c.execute(select(runs.c.created_at).where(runs.c.id == generation_run_id)).scalar()
        require(type(generation_at) in (int, float) and math.isfinite(generation_at))
        require(isinstance(source.authority, StageAuthorityV2)
            and source.approval_key == original.request.request_key
            and source.authority.predecessor_run_id == generation_run_id
            and source.authority.predecessor_created_at == generation_at
            and source.authority.stage_approval_expires_at == min(generation_at + contract.stage_handoff_seconds, contract.execution_expires_at)
            and source.authority.stage == "source"
            and source.authority.contract_fingerprint == fingerprint(contract.model_dump())
            and source.authority.generation_run_id == generation_run_id
            and source.expected_authority_fingerprint == fingerprint(source.authority.model_dump()))
        predecessor_id, runtime = source.authority.run_id, source.authority.runtime_id
        statuses = {"SUCCEEDED"}
    # Only scalar timing/identity metadata; no private result/context body.
    previous = c.execute(select(runs.c.id, runs.c.created_at, runs.c.principal_id,
        runs.c.project_id, runs.c.runtime_id, runs.c.status, runs.c.cancel_intent).where(
        runs.c.id == predecessor_id)).mappings().first()
    require(previous is not None and previous["principal_id"] == user
        and previous["project_id"] == contract.project_id and previous["runtime_id"] == runtime
        and previous["status"] in statuses and previous["cancel_intent"] is False
        and type(previous["created_at"]) in (int, float) and math.isfinite(previous["created_at"])
        and contract.prepared_at <= previous["created_at"] <= time.time(),
        "Exact previous stage timing or identity changed")
    return dict(predecessor_run_id=predecessor_id,
        predecessor_created_at=previous["created_at"],
        stage_approval_expires_at=min(previous["created_at"] + contract.stage_handoff_seconds,
                                      contract.execution_expires_at))


def _stage_review_window(authority):
    if isinstance(authority, StageAuthorityV2):
        require(authority.predecessor_created_at <= time.time() < authority.stage_approval_expires_at,
                "Original stage handoff deadline expired")


class StageApproveInput(Strict):
    authority: StageAuthorityV2 | StageAuthority
    expected_authority_fingerprint: str = Field(pattern=HASH)
    approval_key: str = Field(pattern=KEY)
    request_key: str = Field(pattern=KEY)
    consent: Literal["BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL"]


def _limits(contract):
    return Limits(max_requests=3, max_tools=4, max_repairs=1, max_total_tokens=64000,
                  max_output_tokens=contract.caps.max_output_tokens,
                  run_seconds=contract.caps.run_seconds)


def _stage_instance_after_bound(store, c, user, project, job, snapshot, release, epoch):
    """Recheck the current pointers after the caller's complete SQLite bound proof."""
    from .lifecycle import immutable_release_pointer, owned_release_pointer

    require(store.test_only and store.sqlite and c.in_transaction()
            and c.connection.driver_connection is not None
            and c.connection.driver_connection.in_transaction,
            "Bound Release reuse requires an active offline SQLite transaction")
    inst = c.execute(select(internal_instances).where(
        internal_instances.c.id == snapshot["instance_id"]).with_for_update()).mappings().first()
    if inst is None or inst["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    draft = release["snapshot"]["draft"]
    require(inst["project_id"] == project == job["project_id"] == release["project_id"]
            and inst["source_app_id"] == draft["id"]
            and inst["runtime_id"] == job["runtime_id"] == draft["runtime_id"]
            and inst["release_id"] == release["id"]
            and type(inst["revision"]) is int and inst["revision"] >= 1
            and epoch == c.info.get("source_proof_write_epoch", 0),
            "Bound Instance or read segment changed")
    current = owned_release_pointer(store, c, user, inst["release_id"])
    immutable_release_pointer(c, user, current)
    require(dict(current) == dict(release)
            and epoch == c.info.get("source_proof_write_epoch", 0),
            "Verified Release or read segment changed")
    return inst, current


def _stage_current(store, c, user, contract, stage, run_id):
    """Full existing lineage and accepted binding proofs; public hashes do not suffice."""
    from . import pa_spec_apps

    require(stage in ("source", "cold"))
    require(pa_spec_apps.job_scope_gate(store, c, user, run_id))
    job = c.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
    require(job is not None and job["principal_id"] == user
            and job["project_id"] == contract.project_id)
    epoch = c.info.get("source_proof_write_epoch", 0)
    bound = pa_spec_apps.bound(store, c, user, job, _limits(contract))
    return _stage_current_bound(store, c, user, contract, stage, job, bound, epoch)


def _stage_current_bound(store, c, user, contract, stage, job, bound, epoch):
    """Continuation of a complete binding proof in this synchronous read call."""
    from . import natural_specs, pa_spec_apps
    from .lifecycle import instance

    snapshot, draft, release = bound["snapshot"], bound["draft"], bound["release"]
    require(natural_specs.is_candidate(draft["candidate"]))
    pb_cold = isinstance(contract, PBTrialContract) and stage == "cold"
    ordinary = (not {"human_correction", "logic_check", "pb_use", "pa_use",
                        "project_check", "offline_replay"}.intersection(snapshot)
        and not {"natural_logic_origin", "correction_run_id", "pb_use_run_id", "pa_use_run_id"}.intersection(draft)
        and "natural_logic_source" not in release["snapshot"])
    original_pb_source = (type(contract) is PBTrialContract and stage == "source"
        and "spec_task" not in draft["candidate"])
    if store.test_only and store.sqlite and ordinary and ((pb_cold and "spec_task" in draft["candidate"]) or original_pb_source):
        # bound() just completed the full Release and P-B lineage proof. This
        # uninterrupted SQLite transaction retains fresh identity/approval
        # checks without recursively repeating that same Release proof.
        inst, current_release = _stage_instance_after_bound(
            store, c, user, contract.project_id, job, snapshot, release, epoch)
    else:
        inst, current_release = instance(store, c, user, snapshot["instance_id"], _limits(contract), lock=True)
    require(current_release["id"] == release["id"]
            and current_release["fingerprint"] == release["fingerprint"]
            and bound["app_run"]["request_key"] == getattr(contract.stage_keys, stage))
    target = contract.bindings[1 if stage == "cold" else 0]
    require(bound["source"]["resource_id"] == target.resource_id
            and bound["source"]["hash"] == target.source_hash
            and bound["source"]["content"] == target.content
            and bound["goal"] == dict(card_id=target.card_id, version=target.goal_version,
                fingerprint=target.goal_fingerprint, snapshot=target.goal_snapshot.model_dump()))
    # Match the original generation by its frozen future key, not a supplied ID.
    gen_id = c.execute(select(runs.c.id).where(runs.c.principal_id == user,
        runs.c.project_id == contract.project_id,
        runs.c.request_key == contract.stage_keys.generate)).scalar()
    require(gen_id is not None)
    raw, metadata = pa_spec_apps.model_source(store, c, user, gen_id,
                                             _limits(contract), contract.project_id)
    require(metadata["runtime_id"] == contract.runtime_id
            and metadata["resource_refs"] == [contract.bindings[0].resource_id])
    approval = _saved(c, user, entity(contract), APPROVE, "approve", Approval)
    gen = c.execute(select(runs).where(runs.c.id == gen_id)).mappings().one()
    frozen = store.frozen_contract(c, gen)
    first = contract.bindings[0]
    require(type(gen["created_at"]) in (float, int) and math.isfinite(gen["created_at"])
            and approval.approved_at <= gen["created_at"] < contract.expires_at
            and frozen.source_goal_card is not None
            and frozen.source_goal_card.model_dump() == dict(card_id=first.card_id,
                version=first.goal_version, fingerprint=first.goal_fingerprint,
                snapshot=first.goal_snapshot.model_dump())
            and frozen.application_generation is not None
            and frozen.application_generation.version == "goal-natural-spec-application.v1"
            and frozen.request_model == contract.model,
            "Original Generate must be accepted under this precise trial approval")
    original = draft["candidate"]
    if pb_cold:
        _pb_origin(store, c, user, contract, approval.request.request_key, bound)
    else:
        require("spec_task" not in original, "Only P-B cold may use an extracted task")
    if pb_cold:
        pass
    elif "spec_binding" in original:
        origin = c.execute(select(task_extractions.c.task_id).where(
            task_extractions.c.app_id == draft["id"], task_extractions.c.principal_id == user)).scalar()
        require(origin == gen_id)
    else:
        require(original.get("goal_application", {}).get("run_id") == gen_id)
    # Existing bound/audit proves the whole app lineage. Additionally require its
    # actual graph to be exactly the original generated graph (no edited extras).
    expected_recipe = (contract.extraction_recipe.model_dump(exclude_none=True)
                       if pb_cold else raw["spec_recipe"])
    require(fingerprint(expected_recipe) == fingerprint(draft["candidate"]["spec_recipe"]))
    _generation_accounted(store, c, user, contract, approval.request.request_key, gen_id)
    timing = _stage_deadlines(c, user, contract, stage, gen_id)
    authority_model = StageAuthorityV2 if isinstance(contract, TrialContractV2) else StageAuthority
    authority = authority_model(**timing, contract_fingerprint=fingerprint(contract.model_dump()),
        stage=stage, run_id=job["id"], accepted_fingerprint=job["fingerprint"],
        app_run_id=bound["app_run"]["id"], instance_id=inst["id"], instance_revision=inst["revision"],
        runtime_id=job["runtime_id"], app_id=draft["id"], candidate_fingerprint=draft["fingerprint"],
        recipe_fingerprint=fingerprint(draft["candidate"]["spec_recipe"]),
        release_id=release["id"], release_fingerprint=release["fingerprint"], generation_run_id=gen_id,
        generation_candidate_fingerprint=fingerprint(raw), target_goal_fingerprint=target.goal_fingerprint,
        authorization_fingerprint=authorization_fingerprint(c, user, contract.project_id,
            job["runtime_id"], [b.resource_id for b in contract.bindings]))
    return authority, job


def _source_stage_current(store, c, user, contract, source_id):
    """One fresh complete source proof, continued into exact trial stage checks.

    No binding is supplied by the caller or retained past this function. Other
    lineages use the original full stage path. Every guard calls this anew.
    """
    from threading import get_ident

    from . import natural_specs, pa_spec_apps, pb_natural_specs
    from .contracts import validate_value

    require(type(contract) is PBTrialContract)
    require(pa_spec_apps.job_scope_gate(store, c, user, source_id))
    job = c.execute(select(runs).where(runs.c.id == source_id)).mappings().first()
    require(job is not None and job["principal_id"] == user
            and job["project_id"] == contract.project_id)
    transaction = pb_natural_specs._source_transaction(store, c)
    epoch, thread = c.info.get("source_proof_write_epoch", 0), get_ident()
    limits = _limits(contract)
    with store.proof_authorities(c) as authorities:
        bound, proof = pb_natural_specs.source(store, c, user, contract.project_id, source_id, limits)
        snapshot, draft, release = bound["snapshot"], bound["draft"], bound["release"]
        ordinary = (transaction is not None
            and not {"human_correction", "logic_check", "pb_use", "pa_use",
                     "project_check", "offline_replay"}.intersection(snapshot)
            and not {"natural_logic_origin", "correction_run_id", "pb_use_run_id", "pa_use_run_id"}.intersection(draft)
            and "natural_logic_source" not in release["snapshot"]
            and "spec_task" not in draft["candidate"])
        if ordinary:
            # verify_job intentionally used validate_input=False. Restore the
            # original stage bound's input validation before continuing it.
            manifest, _, _ = natural_specs.compile_candidate(draft["candidate"], limits)
            validate_value(manifest.input_schema, snapshot["input"])
            require(transaction == pb_natural_specs._source_transaction(store, c)
                    and epoch == c.info.get("source_proof_write_epoch", 0)
                    and thread == get_ident() and limits == _limits(contract), "Source stage read segment changed")
            current, job = _stage_current_bound(store, c, user, contract, "source", job, bound, epoch)
        else:
            current, job = _stage_current(store, c, user, contract, "source", source_id)
        store.recheck_proof_authorities(c, {"_call_authorities": tuple(sorted(authorities))})
        require(transaction == pb_natural_specs._source_transaction(store, c)
                and epoch == c.info.get("source_proof_write_epoch", 0)
                and thread == get_ident() and limits == _limits(contract), "Source stage read segment changed")
        return current, job, proof


def _pb_origin(store, c, user, contract, approval_key, bound):
    from . import natural_trial_budget as budget
    from . import pb_natural_specs as pb

    draft, snapshot, release = bound["draft"], bound["snapshot"], bound["release"]
    # In this same read-only call, ordinary bound() already ran verify_origin()
    # -> pb.verify() with this exact draft, connection and limits. Alternative
    # binding branches do not prove that path, so retain their complete check.
    ordinary = ("spec_task" in draft["candidate"]
        and not {"human_correction", "logic_check", "pb_use", "pa_use"}.intersection(snapshot)
        and "natural_logic_source" not in release["snapshot"])
    if not ordinary:
        pb.verify(store, c, user, draft, _limits(contract))
    body, _ = pair(c, user, draft["id"], pb.EXTRACT,
                   contract.extraction_request_key, pb.ExtractInput)
    ledger = budget.audit(store, c, user, budget.scope_for(contract, approval_key))["ledger"]
    source_id = ledger["stage_runs"].get("source")
    slots = [s for s in ledger["slots"] if s["reservation"]["stage"] == "source"]
    actual = c.execute(select(attempts).where(attempts.c.run_id == source_id)).mappings().all()
    require(not ledger["halted"] and source_id is not None
            and body.review.source_run_id == source_id
            and body.review.request_key == contract.extraction_request_key
            and body.review.recipe == contract.extraction_recipe
            and len(slots) == len(actual) == 2
            and {s["reservation"]["request_key"] for s in slots} == {a["id"] for a in actual},
            "P-B requires this original trial's fully accounted successful source")
    by_id = {a["id"]: a for a in actual}
    for slot in slots:
        attempt = by_id[slot["reservation"]["request_key"]]
        settled, usage = slot["settlement"], attempt["usage"]
        wire = attempt["parameters"].get("natural_spec_wire", {})
        raw = attempt["response"].get("raw_evidence", {})
        require(slot["accepted"] is True and settled is not None
                and attempt["status"] == "VERIFIED" and attempt["mode"] == "MOCK"
                and slot["reservation"]["run_id"] == source_id
                and slot["reservation"]["wire_sha256"] == wire.get("sha256")
                and slot["reservation"]["wire_bytes"] == wire.get("bytes")
                and settled["response_sha256"] == raw.get("sha256")
                and settled["response_ascii_bytes"] == raw.get("bytes")
                and raw.get("status") == "COMPLETE"
                and attempt["request_model"] == contract.model
                and usage.get("status") == "known" and isinstance(usage.get("tokens"), dict)
                and all(settled[k] == usage["tokens"].get(k) for k in
                        ("prompt_tokens", "completion_tokens", "total_tokens")),
                "P-B source cost evidence changed or is unknown")


def _generation_accounted(store, c, user, contract, approval_key, gen_id):
    # No caller boolean or cached public pointer can stand in for the paired
    # original trial ledger and independently verified actual provider Attempts.
    try:
        from . import natural_trial_budget as budget
    except ImportError as exc:
        raise DomainError("LIVE_BLOCKED", "Same-trial accounting module is unavailable") from exc
    ledger = budget.audit(store, c, user, budget.scope_for(contract, approval_key))["ledger"]
    slots = [s for s in ledger["slots"] if s["reservation"]["stage"] == "generate"]
    actual = c.execute(select(attempts).where(attempts.c.run_id == gen_id)
                       .order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
    require(not ledger["halted"] and ledger["stage_runs"].get("generate") == gen_id
            and len(slots) == len(actual) == 3
            and {s["reservation"]["request_key"] for s in slots} == {a["id"] for a in actual},
            "Generate must consume this same trial's three actual accounted slots")
    by_id = {a["id"]: a for a in actual}
    for slot in slots:
        charge, settlement = slot["reservation"], slot["settlement"]
        attempt = by_id[charge["request_key"]]
        parameters, usage = attempt["parameters"], attempt["usage"]
        raw = parameters.get("generation_raw_evidence", {})
        require(slot["accepted"] is True and settlement is not None
                and charge["run_id"] == gen_id and attempt["status"] == "RECEIVED"
                and attempt["request_model"] == contract.model and attempt["mode"] == "MOCK"
                and charge["wire_sha256"] == parameters.get("generation_wire")
                and charge["wire_bytes"] + parameters["max_tokens"] == attempt["reserved_tokens"]
                and parameters["max_tokens"] <= contract.caps.max_output_tokens
                and raw.get("status") == "COMPLETE"
                and settlement["response_sha256"] == raw.get("sha256")
                and settlement["response_ascii_bytes"] == raw.get("bytes")
                and usage.get("status") == "known"
                and isinstance(usage.get("tokens"), dict)
                and all(settlement[k] == usage["tokens"].get(k) for k in
                    ("prompt_tokens", "completion_tokens", "total_tokens")),
                "Independent Generate trial charge/raw/usage evidence differs")


@controlled
def stage_review(store, user, contract: TrialContract, approval_key: str,
                 stage: Literal["source", "cold"], run_id: str):
    with store.tx() as c:
        _approved(store, c, user, contract, approval_key)
        authority, _ = _stage_current(store, c, user, contract, stage, run_id)
        _stage_review_window(authority)
        return dict(authority=authority.model_dump(), authority_fingerprint=fingerprint(authority.model_dump()),
                    live_allowed=False, fee_status="NOT_VERIFIED", actual_model_requests=0)


@controlled
def approve_stage(store, user, contract: TrialContract, body: StageApproveInput):
    with store.tx() as c:
        _approved(store, c, user, contract, body.approval_key)
        require(isinstance(body.authority, StageAuthorityV2) == isinstance(contract, TrialContractV2))
        stage = body.authority.stage
        current, job = _stage_current(store, c, user, contract, stage, body.authority.run_id)
        _stage_review_window(current)
        require(current == body.authority
                and fingerprint(current.model_dump()) == body.expected_authority_fingerprint)
        keys, eid = _keys(c, user, entity(contract), PHASE), entity(contract)
        require(keys <= {"source", "cold"})
        if stage in keys:
            require(_saved(c, user, eid, PHASE, stage, StageApproveInput) == body)
        else:
            require(job["status"] == "QUEUED" and not job["cancel_intent"]
                    and not c.execute(select(attempts.c.id).where(attempts.c.run_id == job["id"])).first()
                    and job["context"].get("requests") == 0,
                    "Stage binding must precede any stage model dispatch")
            _save(c, user, eid, PHASE, stage, body)
        # Recheck after writes; transaction rolls all paired records back on drift.
        _approved(store, c, user, contract, body.approval_key)
        fresh, _ = _stage_current(store, c, user, contract, stage, body.authority.run_id)
        require(fresh == current)
        _stage_review_window(fresh)
        return dict(status="EXACT_STAGE_BOUND_LIVE_BLOCKED", authority=current.model_dump(),
            authority_fingerprint=fingerprint(current.model_dump()), live_allowed=False,
            actual_model_requests=0, formal_publication_enabled=False)


@controlled
def recover_stage(store, user, contract: TrialContract, approval_key: str,
                  stage: Literal["source", "cold"], request_key: str):
    """Original consent receipt only, including after Run start or completion.

    Current instance revision and lease are irrelevant to historical inspection.
    This function neither calls admit nor issues a fresh StageAuthority.
    """
    from . import pa_spec_apps

    with store.tx() as c:
        _approved(store, c, user, contract, approval_key, active=False)
        require(stage in ("source", "cold")
                and _keys(c, user, entity(contract), PHASE) <= {"source", "cold"})
        ids = c.execute(select(delivery_graph_requests.c.snapshot["request"]["authority"]["run_id"].as_string())
            .where(delivery_graph_requests.c.principal_id == user,
                   delivery_graph_requests.c.app_id == entity(contract),
                   delivery_graph_requests.c.kind.in_([PHASE, PHASE + "_seal"]),
                   delivery_graph_requests.c.request_key == stage)).scalars().all()
        require(len(ids) == 2 and ids[0] == ids[1] and isinstance(ids[0], str))
        require(pa_spec_apps.job_scope_gate(store, c, user, ids[0]))
        accepted = _saved(c, user, entity(contract), PHASE, stage, StageApproveInput)
        require(accepted.approval_key == approval_key and accepted.request_key == request_key
                and accepted.authority.stage == stage and accepted.authority.run_id == ids[0]
                and accepted.authority.contract_fingerprint == fingerprint(contract.model_dump())
                and accepted.expected_authority_fingerprint == fingerprint(accepted.authority.model_dump()))
        return dict(status="HISTORICAL_STAGE_BINDING_LIVE_BLOCKED", request=accepted.model_dump(),
            authority_fingerprint=accepted.expected_authority_fingerprint, live_allowed=False,
            fee_status="NOT_VERIFIED", dispatch_authorized=False, new_model_requests=0)


def entity(contract):
    return "naturaltrial_" + fingerprint(dict(user=contract.principal_id,
        project=contract.project_id, key=contract.trial_key))[:32]


def authorization_fingerprint(c, user, pid, runtime, resource_ids):
    rows = c.execute(select(grants).where(grants.c.project_id == pid,
        grants.c.principal_id.in_([user, runtime]),
        grants.c.resource_id.in_([pid, *resource_ids])).order_by(grants.c.id)).mappings()
    return fingerprint([dict(row) for row in rows])


def _authorize(store, c, user, contract):
    if user != contract.principal_id:
        raise DomainError("PERMISSION_DENIED")
    project = store.lock_project(c, user, contract.project_id)
    require(project["runtime_id"] == contract.runtime_id)
    # Both READ gates and SAVE precede any private material/Goal/approval body.
    for binding in contract.bindings:
        store.authorize(c, user, contract.runtime_id, contract.project_id,
                        binding.resource_id, "resource.read")
        location = c.execute(select(goal_cards.c.project_id).where(
            goal_cards.c.id == binding.card_id)).scalar()
        if location != contract.project_id:
            raise DomainError("PERMISSION_DENIED")
    store.authorize(c, user, contract.runtime_id, contract.project_id,
                    contract.project_id, "artifact.save_text")


def _current(store, c, user, contract, *, active=True):
    _authorize(store, c, user, contract)
    if isinstance(contract, TrialContractV2):
        require(TrialContractV2.model_validate(contract.model_dump()) == contract)
    for binding in contract.bindings:
        material = authorized_read(store, c, user, contract.runtime_id,
            contract.project_id, "resource.read", {"resource_id": binding.resource_id})
        require(material["format"] == "txt" and material["hash"] == binding.source_hash
                and material["content"] == binding.content)
        saved = validate_card_version(store, c, user, binding.card_id, binding.goal_version)
        head = c.execute(select(goal_cards.c.version, goal_cards.c.fingerprint).where(
            goal_cards.c.id == binding.card_id)).mappings().first()
        require(head is not None and head["version"] == binding.goal_version
                and head["fingerprint"] == saved["fingerprint"] == binding.goal_fingerprint
                and fingerprint(saved["snapshot"]) == fingerprint(binding.goal_snapshot.model_dump()))
    require(authorization_fingerprint(c, user, contract.project_id, contract.runtime_id,
        [b.resource_id for b in contract.bindings]) == contract.authorization_fingerprint)
    if active:
        require(contract.software_fingerprint == implementation(), "Trial software changed")
        require(time.time() < contract.expires_at, "Trial approval expired")
        if isinstance(contract, TrialContractV2):
            require(time.time() >= contract.prepared_at, "Trial not yet active")


def _keys(c, user, eid, kind):
    rows = c.execute(select(delivery_graph_requests.c.kind,
        delivery_graph_requests.c.request_key).where(delivery_graph_requests.c.app_id == eid,
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind.in_([kind, kind + "_seal"]))).mappings().all()
    left = {r["request_key"] for r in rows if r["kind"] == kind}
    right = {r["request_key"] for r in rows if r["kind"] == kind + "_seal"}
    require(left == right, "Natural trial paired history incomplete")
    return left


def _saved(c, user, eid, kind, key, model):
    body, response = pair(c, user, eid, kind, key, model)
    require(fingerprint(body.model_dump()) == fingerprint(response))
    return body


def _save(c, user, eid, kind, key, body):
    remember(c, user, eid, kind, key, body, body.model_dump())


def _approved(store, c, user, contract, approval_key, *, active=True):
    _current(store, c, user, contract, active=active)
    eid = entity(contract)
    require(not _keys(c, user, eid, CLOSED), "Natural trial preparation irreversibly closed")
    require(_keys(c, user, eid, SCOPE) == {"scope"}
            and _keys(c, user, eid, APPROVE) == {"approve"}
            and _keys(c, user, eid, REVOKE) <= {"revoke"})
    saved = _saved(c, user, eid, SCOPE, "scope", type(contract))
    approval = _saved(c, user, eid, APPROVE, "approve", Approval)
    fp = fingerprint(contract.model_dump())
    require(fingerprint(saved.model_dump()) == fp == approval.contract_fingerprint
            == approval.request.expected_contract_fingerprint
            and approval.principal_id == user and approval.project_id == contract.project_id
            and approval.request.request_key == approval_key
            and math.isfinite(approval.approved_at) and approval.approved_at > 0
            and approval.expires_at == contract.expires_at
            and approval.approved_at < approval.expires_at)
    if isinstance(contract, TrialContractV2):
        require(contract.prepared_at <= approval.approved_at < contract.review_expires_at,
                "Original approval outside reviewed window")
    if active:
        require(not _keys(c, user, eid, REVOKE), "Natural trial irreversibly revoked")
        require(approval.approved_at <= time.time() < approval.expires_at)
    return approval


@controlled
def approve(store, user, contract: TrialContract, body: ApproveInput):
    with store.tx() as c:
        if user != contract.principal_id:
            raise DomainError("PERMISSION_DENIED")
        store.lock_project(c, user, contract.project_id)
        require(not _keys(c, user, entity(contract), CLOSED),
                "Natural trial preparation irreversibly closed")
        _current(store, c, user, contract)
        _review_window(contract)
        fp, eid = fingerprint(contract.model_dump()), entity(contract)
        require(body.expected_contract_fingerprint == fp)
        require(not _keys(c, user, eid, REVOKE), "Natural trial irreversibly revoked")
        existing = any(lookup(c, user, eid, kind, "scope")
            for kind in (SCOPE, SCOPE + "_seal"))
        if existing:
            accepted = _approved(store, c, user, contract, body.request_key)
            require(accepted.request == body)
        else:
            require(not _keys(c, user, eid, APPROVE))
            accepted = Approval(contract_fingerprint=fp, principal_id=user,
                project_id=contract.project_id, approved_at=time.time(),
                expires_at=contract.expires_at, request=body)
            require(accepted.approved_at < accepted.expires_at)
            _save(c, user, eid, SCOPE, "scope", contract)
            _save(c, user, eid, APPROVE, "approve", accepted)
        _review_window(contract)
        return _receipt(accepted)


def _receipt(approval):
    return dict(status="EXACT_APPROVAL_RECORDED_LIVE_BLOCKED", live_allowed=False,
        fee_status="NOT_VERIFIED", actual_model_requests=0, formal_publication_enabled=False,
        contract_fingerprint=approval.contract_fingerprint,
        approval_fingerprint=fingerprint(approval.model_dump()), approval=approval.model_dump())


@controlled
def recover(store, user, contract: TrialContract, approval_key: str):
    with store.tx() as c:
        approval = _approved(store, c, user, contract, approval_key, active=False)
        receipt = _receipt(approval)
        receipt["revoked"] = bool(_keys(c, user, entity(contract), REVOKE))
        receipt["expired"] = time.time() >= approval.expires_at
        return receipt


@controlled
def revoke(store, user, contract: TrialContract, body: RevokeInput):
    if user != contract.principal_id:
        raise DomainError("PERMISSION_DENIED")
    return revoke_exact(store, user, contract.project_id, entity(contract),
                        fingerprint(contract.model_dump()), body)


@controlled
def revoke_exact(store, user, project_id, eid, fp, body: RevokeInput):
    """Metadata-only stop, including after source permissions have been withdrawn."""
    with store.tx() as c:
        store.lock_project(c, user, project_id)
        require(body.expected_contract_fingerprint == fp)
        require(_keys(c, user, eid, SCOPE) == {"scope"}
                and _keys(c, user, eid, APPROVE) == {"approve"})
        projections = c.execute(select(delivery_graph_requests.c.request_fingerprint).where(
            delivery_graph_requests.c.app_id == eid, delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.kind.in_([SCOPE, SCOPE + "_seal"]),
            delivery_graph_requests.c.request_key == "scope")).scalars().all()
        require(len(projections) == 2 and all(v == fp for v in projections))
        if _keys(c, user, eid, REVOKE):
            require(_keys(c, user, eid, REVOKE) == {"revoke"})
            require(_saved(c, user, eid, REVOKE, "revoke", RevokeInput) == body)
        else:
            _save(c, user, eid, REVOKE, "revoke", body)
        return dict(status="REVOKED", live_allowed=False, actual_model_requests=0)


def _run_context(store, c, user, contract, approval_key, stage, run_id, expected_version, fence):
    """Shared current approval/phase/Run checks; no source or permission issuance."""
    require(stage in ("generate", "source", "cold"))
    approval = _approved(store, c, user, contract, approval_key)
    phase = None
    if stage != "generate":
        require(_keys(c, user, entity(contract), PHASE) <= {"source", "cold"})
        accepted = _saved(c, user, entity(contract), PHASE, stage, StageApproveInput)
        require(accepted.approval_key == approval_key)
        phase, _ = _stage_current(store, c, user, contract, stage, run_id)
        require(phase == accepted.authority
                and fingerprint(phase.model_dump()) == accepted.expected_authority_fingerprint)
    run = c.execute(select(runs.c.id, runs.c.project_id, runs.c.principal_id,
        runs.c.runtime_id, runs.c.request_key, runs.c.status, runs.c.cancel_intent,
        runs.c.version, runs.c.fence, runs.c.lease_until, runs.c.created_at, runs.c.worker_id,
        runs.c.resource_refs).where(runs.c.id == run_id).with_for_update()).mappings().first()
    binding = contract.bindings[1 if stage == "cold" else 0]
    at = time.time()
    require(type(expected_version) is int and type(fence) is int
            and run is not None and run["principal_id"] == user
            and run["project_id"] == contract.project_id
            and run["runtime_id"] == (contract.runtime_id if phase is None else phase.runtime_id)
            and (phase is not None or run["request_key"] == contract.stage_keys.generate)
            and run["resource_refs"] == [binding.resource_id]
            and run["status"] == "RUNNING" and run["cancel_intent"] is False
            and run["version"] == expected_version and run["fence"] == fence and fence >= 1
            and type(run["created_at"]) in (int, float) and math.isfinite(run["created_at"])
            and approval.approved_at <= run["created_at"] <= at
            and type(run["lease_until"]) in (int, float) and math.isfinite(run["lease_until"])
            and at < min(run["lease_until"], run["created_at"] + contract.caps.run_seconds,
                         contract.expires_at), "Run identity, cancellation, version or finite lease changed")
    return approval, phase, run, at


def _generation_context(store, c, run, contract):
    """Original frozen generation target checks, separate from any fee authority."""
    full_job = c.execute(select(runs).where(runs.c.id == run["id"])).mappings().one()
    frozen = store.frozen_contract(c, full_job)
    target = contract.bindings[0]
    require(frozen.application_generation is not None
            and frozen.application_generation.version == "goal-natural-spec-application.v1"
            and frozen.source_goal_card is not None
            and frozen.source_goal_card.model_dump() == dict(card_id=target.card_id,
                version=target.goal_version, fingerprint=target.goal_fingerprint,
                snapshot=target.goal_snapshot.model_dump())
            and frozen.request_model == contract.model)


@controlled
def admit(store, c, user, contract: TrialContract, approval_key: str, stage: Stage,
          run_id: str, expected_version: int, fence: int, fee_authority: FeeAuthority | None = None):
    """Original synthetic admission; shared context checks do not issue authority."""
    approval, phase, run, at = _run_context(
        store, c, user, contract, approval_key, stage, run_id, expected_version, fence)
    # Do not invoke an arbitrary callback (possibly HTTP) to "discover" entitlement.
    if type(fee_authority) is not SyntheticOnlyFeeAuthority:
        raise DomainError("LIVE_BLOCKED", "No verified production zero-charge authority is registered")
    if not store.test_only or not store.sqlite:
        raise DomainError("LIVE_BLOCKED", "Synthetic authority is confined to test-only SQLite")
    proof = fee_authority.verify(contract)
    require(proof.scope == "SYNTHETIC_ONLY" and proof.contract_fingerprint == approval.contract_fingerprint
            and proof.quota_subject == contract.quota_subject and at < proof.expires_at)
    # Fresh checks after the trusted fixture callback; no reusable send capability.
    _approved(store, c, user, contract, approval_key)
    if phase is None:
        _generation_context(store, c, run, contract)
    return Permit(scope="SYNTHETIC_ONLY", contract_fingerprint=approval.contract_fingerprint,
                  approval_fingerprint=fingerprint(approval.model_dump()), stage=stage,
                  run_id=run_id, runtime_id=run["runtime_id"], run_version=expected_version, fence=fence,
                  expires_at=min(contract.expires_at, run["created_at"] + contract.caps.run_seconds),
                  stage_authority_fingerprint=None if phase is None else fingerprint(phase.model_dump()))
