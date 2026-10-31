"""Exact natural-spec trial consent, with no production zero-fee authority yet.

This module does not send, reserve, settle, create Runs, or grant permissions.
Consent alone is never LIVE admission. The only implemented fee authority is
explicitly synthetic and can issue only a SYNTHETIC_ONLY test permit.
"""

import hashlib
import math
import time
from dataclasses import dataclass
from inspect import getattr_static
from typing import Any, Literal, Protocol

from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.engine import CursorResult, MappingResult, Result

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
from . import _cold_source_packet as _source_owned_code
_SOURCE_OWNED_CHECK = _source_owned_code.CHECK
_SOURCE_BINDING_TYPE = _source_owned_code._BINDING
_SOURCE_OWNED_ENABLED = _source_owned_code._SOURCE_OK
_SOURCE_CAPACITY = _source_owned_code.Capacity
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



# Optional packaged C capture. Never load a caller path or retry a native error.
try:
    from pathlib import Path as _RawPath

    from . import _raw_snapshot as _RAW_MODULE
    from ._raw_snapshot import SOURCE_SHA256 as _RAW_SOURCE_SHA
    from ._raw_snapshot import UNSUPPORTED as _RAW_UNSUPPORTED
    from ._raw_snapshot import copy_snapshot as _RAW_COPY
    from ._raw_snapshot import equal_values as _RAW_EQUAL
    from ._raw_snapshot import row_lookup as _RAW_ROW_LOOKUP
    if hashlib.sha256(_RawPath(__file__).with_name("_raw_snapshot.c").read_bytes()).hexdigest() != _RAW_SOURCE_SHA:
        raise ImportError("Raw capture source/build mismatch")
    _RAW_BINARY_PATH = _RawPath(_RAW_MODULE.__file__).resolve()
    _RAW_BINARY_SHA = hashlib.sha256(_RAW_BINARY_PATH.read_bytes()).hexdigest()
except (ImportError, OSError):
    _RAW_COPY = _RAW_EQUAL = _RAW_ROW_LOOKUP = None

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


class SQLiteSettlementCaps(TrialCaps):
    """New signed P-B policy; old serialized caps keep the 30-second policy."""

    settlement_protocol: Literal["sqlite-exclusive-settlement.v1"] = "sqlite-exclusive-settlement.v1"
    settlement_seconds: Literal[120] = 120


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


class _TrialContractFields(Strict):
    namespace: Literal["natural-live-trial.v1", "natural-live-trial.v2"]
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
    caps: TrialCaps | SQLiteSettlementCaps = Field(default_factory=TrialCaps)

    @model_validator(mode="after")
    def finite(self):
        require(math.isfinite(self.expires_at) and self.expires_at > 0)
        require(len({b.resource_id for b in self.bindings}) == 2
                and len({b.card_id for b in self.bindings}) == 2
                and len({b.source_hash for b in self.bindings}) == 2,
                "Two distinct complete materials and Goals are required")
        return self


class TrialContract(_TrialContractFields):
    namespace: Literal["natural-live-trial.v1"] = VERSION


class TrialContractV2(_TrialContractFields):
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
    caps: TrialCaps | SQLiteSettlementCaps = Field(default_factory=SQLiteSettlementCaps)

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


def parse_contract(value, *, _guard=None):
    return _trial_result(_trial_result(contract_model(value), _guard).model_validate(value), _guard)


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
    def verify(self, contract: TrialContract | TrialContractV2) -> FeeProof: ...


@dataclass(frozen=True)
class SyntheticOnlyFeeAuthority:
    """Offline fixture authority, not a production registration mechanism."""

    contract_fingerprint: str
    quota_subject: str

    def verify(self, contract: TrialContract | TrialContractV2) -> FeeProof:
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


def _stage_deadlines(c, user, contract, stage, generation_run_id, *, _guard=None):
    if not isinstance(contract, TrialContractV2):
        return {}
    if stage == 'source':
        predecessor_id, runtime = (generation_run_id, contract.runtime_id)
        statuses = {'SUCCEEDED', 'PARTIAL'}
    else:
        require(stage == 'cold')
        require(_trial_result(_keys(c, user, _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), PHASE, **{'_guard': _guard} if _guard is not None else {}), _guard) <= {'source', 'cold'})
        source = _trial_result(_saved(c, user, _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), PHASE, 'source', StageApproveInput, **{'_guard': _guard} if _guard is not None else {}), _guard)
        original = _trial_result(_saved(c, user, _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), APPROVE, 'approve', Approval, **{'_guard': _guard} if _guard is not None else {}), _guard)
        generation_at = _trial_result(_trial_result(c.execute(select(runs.c.created_at).where(runs.c.id == generation_run_id)), _guard).scalar(), _guard)
        require(type(generation_at) in (int, float) and _trial_result(math.isfinite(generation_at), _guard))
        require(isinstance(source.authority, StageAuthorityV2) and source.approval_key == original.request.request_key and (source.authority.predecessor_run_id == generation_run_id) and (source.authority.predecessor_created_at == generation_at) and (source.authority.stage_approval_expires_at == min(generation_at + contract.stage_handoff_seconds, contract.execution_expires_at)) and (source.authority.stage == 'source') and (source.authority.contract_fingerprint == _trial_result(fingerprint(_trial_result(contract.model_dump(), _guard)), _guard)) and (source.authority.generation_run_id == generation_run_id) and (source.expected_authority_fingerprint == _trial_result(fingerprint(_trial_result(source.authority.model_dump(), _guard)), _guard)))
        predecessor_id, runtime = (source.authority.run_id, source.authority.runtime_id)
        statuses = {'SUCCEEDED'}
    previous = _trial_result(_trial_mapping_view(_trial_result(c.execute(select(runs.c.id, runs.c.created_at, runs.c.principal_id, runs.c.project_id, runs.c.runtime_id, runs.c.status, runs.c.cancel_intent).where(runs.c.id == predecessor_id)), _guard), _guard).first(), _guard)
    require(previous is not None and previous['principal_id'] == user and (previous['project_id'] == contract.project_id) and (previous['runtime_id'] == runtime) and (previous['status'] in statuses) and (previous['cancel_intent'] is False) and (type(previous['created_at']) in (int, float)) and _trial_result(math.isfinite(previous['created_at']), _guard) and (contract.prepared_at <= previous['created_at'] <= _trial_result(time.time(), _guard)), 'Exact previous stage timing or identity changed')
    return dict(predecessor_run_id=predecessor_id, predecessor_created_at=previous['created_at'], stage_approval_expires_at=min(previous['created_at'] + contract.stage_handoff_seconds, contract.execution_expires_at))


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


def _stage_instance_after_bound(store, c, user, project, job, snapshot, release, epoch, *, _guard=None, _graph_read=None):
    """Recheck the current pointers after the caller's complete SQLite bound proof."""
    from .lifecycle import immutable_release_pointer, owned_release_pointer
    require(store.test_only and store.sqlite and _trial_result(c.in_transaction(), _guard) and (c.connection.driver_connection is not None) and c.connection.driver_connection.in_transaction, 'Bound Release reuse requires an active offline SQLite transaction')
    inst = _trial_result(_trial_mapping_view(_trial_result(c.execute(select(internal_instances).where(internal_instances.c.id == snapshot['instance_id']).with_for_update()), _guard), _guard).first(), _guard)
    if inst is None or inst['principal_id'] != user:
        raise DomainError('PERMISSION_DENIED')
    draft = release['snapshot']['draft']
    require(inst['project_id'] == project == job['project_id'] == release['project_id'] and inst['source_app_id'] == draft['id'] and (inst['runtime_id'] == job['runtime_id'] == draft['runtime_id']) and (inst['release_id'] == release['id']) and (type(inst['revision']) is int) and (inst['revision'] >= 1) and (epoch == c.info.get('source_proof_write_epoch', 0)), 'Bound Instance or read segment changed')
    current = _trial_result(owned_release_pointer(store, c, user, inst['release_id'], **{'_graph_read': _graph_read} if _graph_read is not None else {}), _guard)
    _trial_result(immutable_release_pointer(c, user, current, **{'_graph_read': _graph_read} if _graph_read is not None else {}), _guard)
    require(dict(current) == dict(release) and epoch == c.info.get('source_proof_write_epoch', 0), 'Verified Release or read segment changed')
    return (inst, current)


def _stage_current(store, c, user, contract, stage, run_id):
    """Full existing lineage and accepted binding proofs; public hashes do not suffice."""
    from . import pa_spec_apps
    from .pa_trial_dispatch import JOURNAL_VERSION
    from .pb_natural_specs import _source_reads
    from .spec_production import VERSION as PRODUCTION_VERSION

    if store.test_only and store.sqlite and type(contract) in (TrialContract, TrialContractV2, PBTrialContract):
        versions = c.execute(select(attempts.c.parameters["pa_trial_binding"]["version"].as_string())
            .select_from(runs).join(attempts, attempts.c.run_id == runs.c.id)
            .where(runs.c.principal_id == user, runs.c.project_id == contract.project_id,
                runs.c.runtime_id == contract.runtime_id,
                runs.c.request_key == contract.stage_keys.generate)).scalars().all()
        eligible = (versions == [PRODUCTION_VERSION] * 3 if type(contract) is PBTrialContract
            else versions in ([JOURNAL_VERSION] * 3, [PRODUCTION_VERSION] * 3, ["pa-trial-dispatch.v1"] * 3))
        if eligible:
            with _source_reads(store, c):
                return _stage_current_read(store, c, user, contract, stage, run_id, pa_spec_apps,
                                           _journal=True)
    return _stage_current_read(store, c, user, contract, stage, run_id, pa_spec_apps)


def _stage_current_read(store, c, user, contract, stage, run_id, pa_spec_apps, *, _journal=False):
    require(stage in ("source", "cold"))
    require(pa_spec_apps.job_scope_gate(store, c, user, run_id))
    job = c.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
    require(job is not None and job["principal_id"] == user
            and job["project_id"] == contract.project_id)
    epoch = c.info.get("source_proof_write_epoch", 0)
    bound = pa_spec_apps.bound(store, c, user, job, _limits(contract))
    return _stage_current_bound(store, c, user, contract, stage, job, bound, epoch,
                                _journal=_journal)


def _stage_target_from_facts(bound, target, *, _guard=None):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
    require(bound['source']['resource_id'] == target.resource_id and bound['source']['hash'] == target.source_hash and (bound['source']['content'] == target.content) and (bound['goal'] == dict(card_id=target.card_id, version=target.goal_version, fingerprint=target.goal_fingerprint, snapshot=_trial_result(target.goal_snapshot.model_dump(), _guard))))


def _stage_generate_from_facts(contract, approval, gen, frozen, *, _guard=None):
    """Pure original predicates; caller retains all preceding scope/IO gates."""
    first = contract.bindings[0]
    require(type(gen['created_at']) in (float, int) and _trial_result(math.isfinite(gen['created_at']), _guard) and (approval.approved_at <= gen['created_at'] < contract.expires_at) and (frozen.source_goal_card is not None) and (_trial_result(frozen.source_goal_card.model_dump(), _guard) == dict(card_id=first.card_id, version=first.goal_version, fingerprint=first.goal_fingerprint, snapshot=_trial_result(first.goal_snapshot.model_dump(), _guard))) and (frozen.application_generation is not None) and (frozen.application_generation.version == 'goal-natural-spec-application.v1') and (frozen.request_model == contract.model), 'Original Generate must be accepted under this precise trial approval')


def _stage_authority_fields_from_facts(contract, stage, timing, job, bound, inst, draft, release, gen_id, raw, target, *, _guard=None):
    """Partial fields only; never a complete StageAuthority or a permission."""
    return dict(**timing, contract_fingerprint=_trial_result(fingerprint(_trial_result(contract.model_dump(), _guard)), _guard), stage=stage, run_id=job['id'], accepted_fingerprint=job['fingerprint'], app_run_id=bound['app_run']['id'], instance_id=inst['id'], instance_revision=inst['revision'], runtime_id=job['runtime_id'], app_id=draft['id'], candidate_fingerprint=draft['fingerprint'], recipe_fingerprint=_trial_result(fingerprint(draft['candidate']['spec_recipe']), _guard), release_id=release['id'], release_fingerprint=release['fingerprint'], generation_run_id=gen_id, generation_candidate_fingerprint=_trial_result(fingerprint(raw), _guard), target_goal_fingerprint=target.goal_fingerprint)


def _stage_current_bound(store, c, user, contract, stage, job, bound, epoch, *, _journal=False):
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
    journal_plain = (_journal and type(contract) in (TrialContract, TrialContractV2)
        and natural_specs.is_candidate(draft["candidate"])
        and "spec_task" not in draft["candidate"]
        and not {"human_correction", "logic_check", "pb_use", "project_check", "offline_replay"}.intersection(snapshot)
        and not {"natural_logic_origin", "correction_run_id", "pb_use_run_id"}.intersection(draft)
        and "natural_logic_source" not in release["snapshot"])
    if store.test_only and store.sqlite and (journal_plain or ordinary and
            ((pb_cold and "spec_task" in draft["candidate"]) or original_pb_source)):
        # bound() just completed the full Release and family lineage proof. This
        # uninterrupted SQLite transaction retains fresh identity/approval
        # checks without recursively repeating that same Release proof.
        inst, current_release = _stage_instance_after_bound(
            store, c, user, contract.project_id, job, snapshot, release, epoch)
    else:
        inst, current_release = instance(store, c, user, snapshot["instance_id"], _limits(contract), lock=True)
    _stage_release_from_facts(contract, stage, bound, current_release, release)
    target = contract.bindings[1 if stage == "cold" else 0]
    _stage_target_from_facts(bound, target)
    # Match the original generation by its frozen future key, not a supplied ID.
    gen_id = c.execute(select(runs.c.id).where(runs.c.principal_id == user,
        runs.c.project_id == contract.project_id,
        runs.c.request_key == contract.stage_keys.generate)).scalar()
    require(gen_id is not None)
    raw, metadata = pa_spec_apps.model_source(store, c, user, gen_id,
                                             _limits(contract), contract.project_id)
    _stage_generation_metadata_from_facts(contract, metadata)
    approval = _saved(c, user, entity(contract), APPROVE, "approve", Approval)
    gen = c.execute(select(runs).where(runs.c.id == gen_id)).mappings().one()
    frozen = store.frozen_contract(c, gen)
    _stage_generate_from_facts(contract, approval, gen, frozen)
    original = draft["candidate"]
    if pb_cold:
        _pb_origin(store, c, user, contract, approval.request.request_key, bound)
    else:
        _stage_plain_origin_from_facts(original)
    if pb_cold:
        pass
    elif "spec_binding" in original:
        origin = c.execute(select(task_extractions.c.task_id).where(
            task_extractions.c.app_id == draft["id"], task_extractions.c.principal_id == user)).scalar()
        _stage_generation_origin_from_facts(origin, gen_id)
    else:
        _stage_goal_origin_from_facts(original, gen_id)
    # Existing bound/audit proves the whole app lineage. Additionally require its
    # actual graph to be exactly the original generated graph (no edited extras).
    expected_recipe = (contract.extraction_recipe.model_dump(exclude_none=True)
                       if pb_cold else raw["spec_recipe"])
    _stage_recipe_from_facts(expected_recipe, draft)
    backend = _generation_accounted(store, c, user, contract, approval.request.request_key, gen_id)
    if backend is not None and stage == "cold":
        from .pa_trial_dispatch import journal_stage_accounted
        source = _saved(c, user, entity(contract), PHASE, "source", StageApproveInput)
        _stage_source_phase_from_facts(contract, approval, gen_id, source)
        journal_stage_accounted(store, c, user, contract, approval.request.request_key,
                                source.authority.run_id, "source")
    timing = _stage_deadlines(c, user, contract, stage, gen_id)
    authority_model = StageAuthorityV2 if isinstance(contract, TrialContractV2) else StageAuthority
    fields = _stage_authority_fields_from_facts(contract, stage, timing, job, bound, inst, draft, release, gen_id, raw, target)
    authority = authority_model(**fields, authorization_fingerprint=authorization_fingerprint(c, user, contract.project_id,
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
    from .pa_trial_dispatch import _pb_accounting, journal_stage_accounted
    backend, ledger, source_id = _pb_accounting(store, c, user, contract, approval_key)
    if backend is not None:
        _stage_pb_origin_from_facts(contract, body, source_id)
        journal_stage_accounted(store, c, user, contract, approval_key, source_id, "source")
        return
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
    from .pa_trial_dispatch import JOURNAL_VERSION, journal_stage_accounted
    from .spec_production import VERSION as PRODUCTION_VERSION
    versions = c.execute(select(attempts.c.parameters["pa_trial_binding"]["version"].as_string())
                         .where(attempts.c.run_id == gen_id)).scalars().all()
    if any(v != "pa-trial-dispatch.v1" for v in versions):
        require(versions in ([JOURNAL_VERSION] * 3, [PRODUCTION_VERSION] * 3),
                "Mixed or unknown actual trial backends cannot prove a stage")
        journal_stage_accounted(store, c, user, contract, approval_key, gen_id, "generate")
        return versions[0]
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
def stage_review(store, user, contract: TrialContract | TrialContractV2, approval_key: str,
                 stage: Literal["source", "cold"], run_id: str):
    with store.tx() as c:
        _approved(store, c, user, contract, approval_key)
        authority, _ = _stage_current(store, c, user, contract, stage, run_id)
        _stage_review_window(authority)
        return dict(authority=authority.model_dump(), authority_fingerprint=fingerprint(authority.model_dump()),
                    live_allowed=False, fee_status="NOT_VERIFIED", actual_model_requests=0)


@controlled
def approve_stage(store, user, contract: TrialContract | TrialContractV2, body: StageApproveInput):
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
def recover_stage(store, user, contract: TrialContract | TrialContractV2, approval_key: str,
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


def entity(contract, *, _guard=None):
    return 'naturaltrial_' + _trial_result(fingerprint(dict(user=contract.principal_id, project=contract.project_id, key=contract.trial_key)), _guard)[:32]


def authorization_fingerprint(c, user, pid, runtime, resource_ids, *, _guard=None):
    rows = _trial_result(_trial_result(c.execute(select(grants).where(grants.c.project_id == pid, grants.c.principal_id.in_([user, runtime]), grants.c.resource_id.in_([pid, *resource_ids])).order_by(grants.c.id)), _guard).mappings(), _guard)
    values = _trial_result([dict(row) for row in rows], _guard)
    return _trial_result(fingerprint(values), _guard)


def _authorize(store, c, user, contract, *, _guard=None):
    if user != contract.principal_id:
        raise DomainError('PERMISSION_DENIED')
    project = _trial_result(store.lock_project(c, user, contract.project_id), _guard)
    require(project['runtime_id'] == contract.runtime_id)
    for binding in contract.bindings:
        _trial_result(store.authorize(c, user, contract.runtime_id, contract.project_id, binding.resource_id, 'resource.read'), _guard)
        location = _trial_result(_trial_result(c.execute(select(goal_cards.c.project_id).where(goal_cards.c.id == binding.card_id)), _guard).scalar(), _guard)
        if location != contract.project_id:
            raise DomainError('PERMISSION_DENIED')
    _trial_result(store.authorize(c, user, contract.runtime_id, contract.project_id, contract.project_id, 'artifact.save_text'), _guard)


def _current(store, c, user, contract, *, active=True, _guard=None):
    _trial_result(_authorize(store, c, user, contract, **{'_guard': _guard} if _guard is not None else {}), _guard)
    if isinstance(contract, TrialContractV2):
        require(_trial_result(TrialContractV2.model_validate(_trial_result(contract.model_dump(), _guard)), _guard) == contract)
    for binding in contract.bindings:
        material = _trial_result(authorized_read(store, c, user, contract.runtime_id, contract.project_id, 'resource.read', {'resource_id': binding.resource_id}), _guard)
        require(material['format'] == 'txt' and material['hash'] == binding.source_hash and (material['content'] == binding.content))
        saved = _trial_result(validate_card_version(store, c, user, binding.card_id, binding.goal_version), _guard)
        head = _trial_result(_trial_mapping_view(_trial_result(c.execute(select(goal_cards.c.version, goal_cards.c.fingerprint).where(goal_cards.c.id == binding.card_id)), _guard), _guard).first(), _guard)
        require(head is not None and head['version'] == binding.goal_version and (head['fingerprint'] == saved['fingerprint'] == binding.goal_fingerprint) and (_trial_result(fingerprint(saved['snapshot']), _guard) == _trial_result(fingerprint(_trial_result(binding.goal_snapshot.model_dump(), _guard)), _guard)))
    require(_trial_result(authorization_fingerprint(c, user, contract.project_id, contract.runtime_id, [b.resource_id for b in contract.bindings], **{'_guard': _guard} if _guard is not None else {}), _guard) == contract.authorization_fingerprint)
    if active:
        require(contract.software_fingerprint == _trial_result(implementation(), _guard), 'Trial software changed')
        require(_trial_result(time.time(), _guard) < contract.expires_at, 'Trial approval expired')
        if isinstance(contract, TrialContractV2):
            require(_trial_result(time.time(), _guard) >= contract.prepared_at, 'Trial not yet active')


def _keys(c, user, eid, kind, *, _guard=None):
    rows = _trial_result(_trial_mapping_view(_trial_result(c.execute(select(delivery_graph_requests.c.kind, delivery_graph_requests.c.request_key).where(delivery_graph_requests.c.app_id == eid, delivery_graph_requests.c.principal_id == user, delivery_graph_requests.c.kind.in_([kind, kind + '_seal']))), _guard), _guard).all(), _guard)
    left = {r['request_key'] for r in rows if r['kind'] == kind}
    right = {r['request_key'] for r in rows if r['kind'] == kind + '_seal'}
    require(left == right, 'Natural trial paired history incomplete')
    return left


def _saved(c, user, eid, kind, key, model, *, _guard=None):
    body, response = _trial_result(pair(c, user, eid, kind, key, model), _guard)
    if _guard is not None:
        _guard = _trial_typed_guard(_guard, [(model, body, response)])
        _guard()
    require(_trial_result(fingerprint(_trial_result(body.model_dump(), _guard)), _guard) == _trial_result(fingerprint(response), _guard))
    return body


def _save(c, user, eid, kind, key, body):
    remember(c, user, eid, kind, key, body, body.model_dump())


def _approved(store, c, user, contract, approval_key, *, active=True, _guard=None):
    _trial_result(_current(store, c, user, contract, active=active, **{'_guard': _guard} if _guard is not None else {}), _guard)
    eid = _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard)
    require(not _trial_result(_keys(c, user, eid, CLOSED, **{'_guard': _guard} if _guard is not None else {}), _guard), 'Natural trial preparation irreversibly closed')
    require(_trial_result(_keys(c, user, eid, SCOPE, **{'_guard': _guard} if _guard is not None else {}), _guard) == {'scope'} and _trial_result(_keys(c, user, eid, APPROVE, **{'_guard': _guard} if _guard is not None else {}), _guard) == {'approve'} and (_trial_result(_keys(c, user, eid, REVOKE, **{'_guard': _guard} if _guard is not None else {}), _guard) <= {'revoke'}))
    saved = _trial_result(_saved(c, user, eid, SCOPE, 'scope', type(contract), **{'_guard': _guard} if _guard is not None else {}), _guard)
    approval = _trial_result(_saved(c, user, eid, APPROVE, 'approve', Approval, **{'_guard': _guard} if _guard is not None else {}), _guard)
    fp = _trial_result(fingerprint(_trial_result(contract.model_dump(), _guard)), _guard)
    require(_trial_result(fingerprint(_trial_result(saved.model_dump(), _guard)), _guard) == fp == approval.contract_fingerprint == approval.request.expected_contract_fingerprint and approval.principal_id == user and (approval.project_id == contract.project_id) and (approval.request.request_key == approval_key) and _trial_result(math.isfinite(approval.approved_at), _guard) and (approval.approved_at > 0) and (approval.expires_at == contract.expires_at) and (approval.approved_at < approval.expires_at))
    if isinstance(contract, TrialContractV2):
        require(contract.prepared_at <= approval.approved_at < contract.review_expires_at, 'Original approval outside reviewed window')
    if active:
        require(not _trial_result(_keys(c, user, eid, REVOKE, **{'_guard': _guard} if _guard is not None else {}), _guard), 'Natural trial irreversibly revoked')
        require(approval.approved_at <= _trial_result(time.time(), _guard) < approval.expires_at)
    return approval


@controlled
def approve(store, user, contract: TrialContract | TrialContractV2, body: ApproveInput):
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
def recover(store, user, contract: TrialContract | TrialContractV2, approval_key: str):
    with store.tx() as c:
        approval = _approved(store, c, user, contract, approval_key, active=False)
        receipt = _receipt(approval)
        receipt["revoked"] = bool(_keys(c, user, entity(contract), REVOKE))
        receipt["expired"] = time.time() >= approval.expires_at
        return receipt


@controlled
def revoke(store, user, contract: TrialContract | TrialContractV2, body: RevokeInput):
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
        _stage_accepted_from_facts(phase, accepted)
    run = _run_context_row(c, run_id)
    at = time.time()
    _require_run_context_row(user, contract, stage, run, expected_version, fence, approval, phase, at)
    return approval, phase, run, at


def _require_run_context_row(user, contract, stage, run, expected_version, fence, approval, phase, at, *, _guard=None):
    """The original complete Run predicate, also after a synchronous readback."""
    binding = contract.bindings[1 if stage == 'cold' else 0]
    require(type(expected_version) is int and type(fence) is int and (run is not None) and (run['principal_id'] == user) and (run['project_id'] == contract.project_id) and (run['runtime_id'] == (contract.runtime_id if phase is None else phase.runtime_id)) and (phase is not None or run['request_key'] == contract.stage_keys.generate) and (run['resource_refs'] == [binding.resource_id]) and (run['status'] == 'RUNNING') and (run['cancel_intent'] is False) and (run['version'] == expected_version) and (run['fence'] == fence) and (fence >= 1) and (type(run['created_at']) in (int, float)) and _trial_result(math.isfinite(run['created_at']), _guard) and (approval.approved_at <= run['created_at'] <= at) and (type(run['lease_until']) in (int, float)) and _trial_result(math.isfinite(run['lease_until']), _guard) and (at < min(run['lease_until'], run['created_at'] + contract.caps.run_seconds, contract.expires_at)), 'Run identity, cancellation, version or finite lease changed')


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
def admit(store, c, user, contract: TrialContract | TrialContractV2, approval_key: str, stage: Stage,
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


def _graph_trial_pin(graph, store, c):
    """Continuity only; exact local type, never a Grant, permission or resolver."""
    from .natural_spec_runtime import _ColdGraphRead
    require(type(graph) is _ColdGraphRead)
    try:
        _ColdGraphRead.check(graph, store, c)
    except BaseException:
        _ColdGraphRead.invalidate(graph)
        raise


def _graph_trial_stage_parent_pin(graph, store, c, stage_facts, *, _owned=None):
    """Fixed composite for stage parents; independent readers still self-pin."""
    if _owned is not None:
        from ._cold_accounted_native import _NativeCandidate
        from .cold_accounted import _OwnedPrewriteMode
        if (type(_owned) is _OwnedPrewriteMode and type(_owned._native) is _NativeCandidate
                and _owned._native.owned_ready is True):
            _owned._pin_stage(graph, store, c, stage_facts)
            return
    _graph_trial_pin(graph, store, c)
    if _owned is None:
        from .natural_spec_runtime import _ColdGraphRead
        candidate = (vars(graph).get('_producer_segment_candidate')
            if type(graph) is _ColdGraphRead else None)
        if candidate is not None:
            from ._cold_producer_segment import _ProducerSegment
            if type(candidate) is _ProducerSegment and candidate.stage_parent(graph, store, c, stage_facts):
                return
    _graph_trial_stage_raw(graph, stage_facts, **{'_owned': _owned} if _owned is not None else {})


def _graph_stage_current(graph, store, c, user, contract, stage, stage_facts, *, _owned=None):
    """Original PB stage cross-role predicates after complete graph producers.

    No paired Authority is an input. Generate/Source accounting are full actual
    row/chain/NS-byte tuples from _graph_stage_accounted. Cold extraction facts
    are the complete pb.verify-equivalent graph node, not a request fingerprint.
    """

    def _parent_pin():
        _graph_trial_stage_parent_pin(graph, store, c, stage_facts, **{'_owned': _owned} if _owned is not None else {})
    _models: list[tuple[type, object, dict]] = []
    _guard = _trial_typed_guard(_parent_pin, _models)
    try:
        _guard()
        _graph_trial_contract_models(graph, store, c, _models, contract)
        _graph_trial_stage_models(graph, store, c, _models, stage_facts, **{'_owned': _owned} if _owned is not None else {})
        _guard()
        require(type(contract) is PBTrialContract and stage in ('source', 'cold'))
        job, bound, raw, metadata, gen, frozen, generated, source, extraction = stage_facts
        stage_prefix = _trial_result(_graph_stage_before_generation(graph, store, c, user, contract, stage, job, bound), _guard)
        draft, release = (bound['draft'], bound['release'])
        inst, current_release, target, gen_id, approval = _trial_result(_graph_stage_before_accounting(graph, store, c, user, contract, stage, job, bound, raw, metadata, gen, frozen, stage_prefix), _guard)
        _graph_trial_produced(graph, store, c, _models, Approval, approval)
        if _owned is not None:
            from . import cold_accounted
            _owned.assert_family(graph, generated, 'generate')
            _owned.assert_run('generate', gen)
            require(len(generated.actual) == len(generated.chains) == 3)
            for row in generated.actual:
                _trial_result(cold_accounted._stage_usage(generated, row.id), _guard)
        else:
            from . import _cold_source_packet as source_owned
            if _SOURCE_BINDING_TYPE is not None and type(generated) is _SOURCE_BINDING_TYPE:
                generated_facts=source_owned.facts(graph,generated,stage='generate')
                require(source_owned.image.business_equal(generated_facts[0],gen))
                source_owned.stage_usage(graph,generated,_guard,stage='generate')
            else:
                require(generated[0] == gen and len(generated[1]) == len(generated[2]) == 3)
                from .pa_trial_dispatch import _stage_usage_from_facts
                for chain in generated[2]:
                    require(chain[3] in generated[1])
                    _trial_result(_stage_usage_from_facts(chain[3], 'generate', chain[0], chain[2], chain[3], _guard=_guard), _guard)
        original = draft['candidate']
        if stage == 'cold':
            require(type(extraction) is tuple and len(extraction) == 4)
            extraction_draft, body, extraction_target, extraction_goal = extraction
            from . import _cold_source_packet as source_owned
            source_packet = source if (_SOURCE_BINDING_TYPE is not None and type(source) is _SOURCE_BINDING_TYPE) else None
            if _owned is None:
                source_run, source_actual, source_chains, source_ns = (
                    source_owned.facts(graph,source_packet) if source_packet is not None else source)
            require(extraction_draft['id'] == draft['id'])
            if _owned is not None:
                _owned.assert_family(graph, source, 'source')
                source_run = source.run
                _trial_result(_stage_pb_origin_from_facts(contract, body, source_run['id'], _guard=_guard), _guard)
                require(len(source.actual) == len(source.chains) == len(source.ns_reads) == 2)
                for row in source.actual:
                    _trial_result(cold_accounted._stage_usage(source, row.id), _guard)
            else:
                _trial_result(_stage_pb_origin_from_facts(contract, body, source_run['id'], _guard=_guard), _guard)
                require(len(source_actual) == len(source_chains) == len(source_ns) == 2)
                if source_packet is not None:
                    source_owned.stage_usage(graph,source_packet,_guard)
                else:
                    for chain in source_chains:
                        require(chain[3] in source_actual)
                        _trial_result(_stage_usage_from_facts(chain[3], 'source', chain[0], chain[2], chain[3], _guard=_guard), _guard)
        else:
            _trial_result(_stage_plain_origin_from_facts(original, _guard=_guard), _guard)
            if 'spec_binding' in original:
                ids = _trial_result(_trial_result(_trial_result(c.execute(select(task_extractions.c.task_id).where(task_extractions.c.app_id == draft['id'], task_extractions.c.principal_id == user)), _guard).scalars(), _guard).all(), _guard)
                require(len(ids) == 1)
                _trial_result(_stage_generation_origin_from_facts(ids[0], gen_id, _guard=_guard), _guard)
            else:
                _trial_result(_stage_goal_origin_from_facts(original, gen_id, _guard=_guard), _guard)
        expected_recipe = _trial_result(contract.extraction_recipe.model_dump(exclude_none=True), _guard) if stage == 'cold' else raw['spec_recipe']
        _trial_result(_stage_recipe_from_facts(expected_recipe, draft, _guard=_guard), _guard)
        if stage == 'cold':
            accepted = _trial_result(_saved(c, user, _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), PHASE, 'source', StageApproveInput, **{'_guard': _guard} if _guard is not None else {}), _guard)
            _graph_trial_produced(graph, store, c, _models, StageApproveInput, accepted)
            _trial_result(_stage_source_phase_from_facts(contract, approval, gen_id, accepted, _guard=_guard), _guard)
            require(accepted.authority.run_id == (source.run.id if _owned is not None else source_run['id']))
        timing = _trial_result(_stage_deadlines(c, user, contract, stage, gen_id, _guard=_guard), _guard)
        fields = _trial_result(_stage_authority_fields_from_facts(contract, stage, timing, job, bound, inst, draft, release, gen_id, raw, target, _guard=_guard), _guard)
        authority = _trial_result(StageAuthority(**fields, authorization_fingerprint=_trial_result(authorization_fingerprint(c, user, contract.project_id, job['runtime_id'], [x.resource_id for x in contract.bindings], **{'_guard': _guard} if _guard is not None else {}), _guard)), _guard)
        _graph_trial_produced(graph, store, c, _models, StageAuthority, authority)
        _guard()
        return (authority, job)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_run_context(graph, store, c, user, contract, approval_key, stage, run_id, expected_version, fence, stage_facts, *, _owned=None):
    """Original live edges around complete graph stage reconstruction."""

    def _parent_pin():
        _graph_trial_stage_parent_pin(graph, store, c, stage_facts, **{'_owned': _owned} if _owned is not None else {})
    _models: list[tuple[type, object, dict]] = []
    _guard = _trial_typed_guard(_parent_pin, _models)
    try:
        _guard()
        _graph_trial_contract_models(graph, store, c, _models, contract)
        _graph_trial_stage_models(graph, store, c, _models, stage_facts, **{'_owned': _owned} if _owned is not None else {})
        _guard()
        require(type(contract) is PBTrialContract and stage == 'cold')
        require(stage_facts[0]['id'] == run_id, 'Stage facts belong to another Run')
        approval = _trial_result(_approved(store, c, user, contract, approval_key, **{'_guard': _guard} if _guard is not None else {}), _guard)
        _graph_trial_produced(graph, store, c, _models, Approval, approval)
        require(_trial_result(_keys(c, user, _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), PHASE, **{'_guard': _guard} if _guard is not None else {}), _guard) <= {'source', 'cold'})
        accepted = _trial_result(_saved(c, user, _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), PHASE, stage, StageApproveInput, **{'_guard': _guard} if _guard is not None else {}), _guard)
        _graph_trial_produced(graph, store, c, _models, StageApproveInput, accepted)
        require(accepted.approval_key == approval_key)
        phase, _ = _trial_result(_graph_stage_current(graph, store, c, user, contract, stage, stage_facts, **{'_owned': _owned} if _owned is not None else {}), _guard)
        _graph_trial_produced(graph, store, c, _models, StageAuthority, phase)
        require(phase.run_id == run_id, 'Reconstructed stage belongs to another Run')
        _trial_result(_stage_accepted_from_facts(phase, accepted, _guard=_guard), _guard)
        run = _trial_result(_run_context_row(c, run_id, _guard=_guard), _guard)
        require(run is not None and run['id'] == run_id, 'Locked row belongs to another Run')
        at = _trial_result(time.time(), _guard)
        _trial_result(_require_run_context_row(user, contract, stage, run, expected_version, fence, approval, phase, at, _guard=_guard), _guard)
        _guard()
        return (approval, phase, run, at)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _stage_release_from_facts(contract, stage, bound, current_release, release, *, _guard=None):
    require(current_release['id'] == release['id'] and current_release['fingerprint'] == release['fingerprint'] and (bound['app_run']['request_key'] == getattr(contract.stage_keys, stage)))


def _stage_generation_metadata_from_facts(contract, metadata, *, _guard=None):
    require(metadata['runtime_id'] == contract.runtime_id and metadata['resource_refs'] == [contract.bindings[0].resource_id])


def _stage_plain_origin_from_facts(original, *, _guard=None):
    require('spec_task' not in original, 'Only P-B cold may use an extracted task')


def _stage_generation_origin_from_facts(origin, gen_id, *, _guard=None):
    require(origin == gen_id)


def _stage_goal_origin_from_facts(original, gen_id, *, _guard=None):
    require(original.get('goal_application', {}).get('run_id') == gen_id)


def _stage_recipe_from_facts(expected_recipe, draft, *, _guard=None):
    require(_trial_result(fingerprint(expected_recipe), _guard) == _trial_result(fingerprint(draft['candidate']['spec_recipe']), _guard))


def _stage_source_phase_from_facts(contract, approval, gen_id, source, *, _guard=None):
    require(source.approval_key == approval.request.request_key and source.authority.contract_fingerprint == _trial_result(fingerprint(_trial_result(contract.model_dump(), _guard)), _guard) and (source.authority.generation_run_id == gen_id))


def _stage_accepted_from_facts(phase, accepted, *, _guard=None):
    require(phase == accepted.authority and _trial_result(fingerprint(_trial_result(phase.model_dump(), _guard)), _guard) == accepted.expected_authority_fingerprint)


def _stage_pb_origin_from_facts(contract, body, source_id, *, _guard=None):
    require(source_id is not None and body.review.source_run_id == source_id and (body.review.request_key == contract.extraction_request_key) and (body.review.recipe == contract.extraction_recipe), "P-B requires this original trial's successful source and exact extraction")


def _run_context_row(c, run_id, *, _guard=None):
    run = _trial_result(_trial_mapping_view(_trial_result(c.execute(select(runs.c.id, runs.c.project_id, runs.c.principal_id, runs.c.runtime_id, runs.c.request_key, runs.c.status, runs.c.cancel_intent, runs.c.version, runs.c.fence, runs.c.lease_until, runs.c.created_at, runs.c.worker_id, runs.c.resource_refs).where(runs.c.id == run_id).with_for_update()), _guard), _guard).first(), _guard)
    return run


# Code identities only, never input values or a remembered validation verdict.
_RESULT_MAPPINGS = Result.mappings
_MAPPING_INIT = MappingResult.__init__
_MAPPING_NEW = getattr_static(MappingResult, "__new__")
_MAPPING_SETATTR = getattr_static(MappingResult, "__setattr__")
_MAPPING_MISSING = object()
_MAPPING_FIELDS = tuple((name, getattr_static(MappingResult, name, _MAPPING_MISSING)) for name in
    ("_real_result", "_unique_filter_state", "_metadata"))
_MAPPING_CODES = (_RESULT_MAPPINGS.__code__, _MAPPING_INIT.__code__)
_RESULT_FIELDS = tuple((name, getattr_static(CursorResult, name)) for name in
    ("_source_supports_scalars", "_unique_filter_state", "_metadata"))


def _trial_mapping_view(result, _guard):
    """Fixed non-fetching view between original execute/fetch content pins.

    Exact CursorResult with scalar reduction disabled only assigns three fields
    in the original MappingResult constructor. SQL execution and actual fetch
    remain independently post-pinned at their original caller frames. Unknown
    result classes or changed code retain the old intermediate boundary.
    """
    fixed = (type(result) is CursorResult
        and getattr_static(result, "_source_supports_scalars") is False
        and getattr_static(result, "__getattribute__") is object.__getattribute__
        and getattr_static(result, "mappings") is _RESULT_MAPPINGS
        and all(getattr_static(CursorResult, name) is field for name, field in _RESULT_FIELDS)
        and getattr_static(type(result), 'mappings') is _RESULT_MAPPINGS
        and Result.mappings is _RESULT_MAPPINGS
        and MappingResult.__init__ is _MAPPING_INIT
        and getattr_static(MappingResult, "__new__") is _MAPPING_NEW
        and getattr_static(MappingResult, "__setattr__") is _MAPPING_SETATTR
        and all(getattr_static(MappingResult, name, _MAPPING_MISSING) is field
            for name, field in _MAPPING_FIELDS)
        and _RESULT_MAPPINGS.__code__ is _MAPPING_CODES[0]
        and _MAPPING_INIT.__code__ is _MAPPING_CODES[1]
        and _RESULT_MAPPINGS.__globals__.get('MappingResult') is MappingResult)
    value = result.mappings()
    if not fixed and _guard is not None:
        _guard()
    return value


def _trial_result(value, _guard=None):
    """Post-callee pin before its result is consumed; None keeps original behavior.

    Strict callers pass only a fixed local exact-graph pin closure. This leaf
    does not validate a predicate, resolve anything, or grant authority.
    """
    if _guard is not None:
        _guard()
    return value


def _graph_stage_before_generation(graph, store, c, user, contract, stage, job, bound):
    """Original current Instance/Release/target and Generate-ID prefix only; no model source, J or Authority."""

    def _parent_pin():
        _graph_trial_pin(graph, store, c)
    _models: list[tuple[type, object, dict]] = []
    _guard = _trial_typed_guard(_parent_pin, _models)
    try:
        from . import natural_specs, pa_spec_apps
        _guard()
        _graph_trial_contract_models(graph, store, c, _models, contract)
        _guard()
        require(type(contract) is PBTrialContract and stage in ('source', 'cold'))
        require(_trial_result(pa_spec_apps.job_scope_gate(store, c, user, job['id'], _graph_read=graph), _guard))
        require(job['principal_id'] == user and job['project_id'] == contract.project_id)
        snapshot, draft, release = (bound['snapshot'], bound['draft'], bound['release'])
        require(_trial_result(natural_specs.is_candidate(draft['candidate']), _guard))
        inst, current_release = _trial_result(_stage_instance_after_bound(store, c, user, contract.project_id, job, snapshot, release, c.info.get('source_proof_write_epoch', 0), _guard=_guard, _graph_read=graph), _guard)
        _trial_result(_stage_release_from_facts(contract, stage, bound, current_release, release, _guard=_guard), _guard)
        target = contract.bindings[1 if stage == 'cold' else 0]
        _trial_result(_stage_target_from_facts(bound, target, _guard=_guard), _guard)
        gen_id = _trial_result(_trial_result(c.execute(select(runs.c.id).where(runs.c.principal_id == user, runs.c.project_id == contract.project_id, runs.c.request_key == contract.stage_keys.generate)), _guard).scalar(), _guard)
        require(gen_id is not None)
        return (inst, current_release, target, gen_id)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_stage_before_accounting(graph, store, c, user, contract, stage, job, bound, raw, metadata, gen, frozen, stage_prefix):
    """Original Generate metadata/approval/frozen prefix after complete native source; no J, accounting or Authority."""

    def _parent_pin():
        _graph_trial_pin(graph, store, c)
    _models: list[tuple[type, object, dict]] = []
    _guard = _trial_typed_guard(_parent_pin, _models)
    try:
        _guard()
        _graph_trial_contract_models(graph, store, c, _models, contract)
        _graph_trial_frozen_models(graph, store, c, _models, frozen)
        _guard()
        require(type(contract) is PBTrialContract and stage in ('source', 'cold'))
        inst, current_release, target, gen_id = stage_prefix
        require(gen['id'] == gen_id)
        _trial_result(_stage_generation_metadata_from_facts(contract, metadata, _guard=_guard), _guard)
        approval = _trial_result(_saved(c, user, _trial_result(entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), APPROVE, 'approve', Approval, **{'_guard': _guard} if _guard is not None else {}), _guard)
        _graph_trial_produced(graph, store, c, _models, Approval, approval)
        _trial_result(_stage_generate_from_facts(contract, approval, gen, frozen, _guard=_guard), _guard)
        return (inst, current_release, target, gen_id, approval)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _trial_typed_classes():
    from . import natural_source_archives as archive
    from . import natural_trial_budget as budget
    from . import pb_natural_specs as pb
    from . import pb_natural_uses as use
    from . import production_trial_policy as policy
    from . import production_trial_sender as sender
    from .contracts import AppManifest, FrozenRunContract, GoalCardRunSource, Limits
    return (PBTrialContract, TrialContract, TrialContractV2, Approval,
        StageApproveInput, StageAuthority, StageAuthorityV2, MaterialGoal,
        AppManifest, FrozenRunContract, GoalCardRunSource, Limits, budget.Scope,
        pb.ExtractInput, use.CommitInput, use.ReviewInput, policy.Ledger,
        policy.AccountQuotaCursor, policy.Slot, policy.ReservationIdentity,
        policy.RunCheck, policy.SourceVerificationResult, policy.evidence.EvidenceRequirements, sender.Capture,
        archive.BodyArchive)


def _trial_typed_equal(actual, saved):
    """Compare complete fixed-model dumps without Python numeric coercion."""
    if _RAW_EQUAL is not None:
        same = _RAW_EQUAL(actual, saved)
        if same is not _RAW_UNSUPPORTED:
            return same
    pending = [(actual, saved)]
    while pending:
        left, right = pending.pop()
        kind = type(left)
        if kind is not type(right):
            return False
        if kind is dict:
            if (len(left) != len(right)
                    or not all(type(key) is str for key in left)
                    or not all(type(key) is str for key in right)
                    or left.keys() != right.keys()):
                return False
            pending.extend((value, right[key]) for key, value in left.items())
        elif kind is list or kind is tuple:
            if len(left) != len(right):
                return False
            pending.extend(zip(left, right, strict=True))
        elif (kind is str or kind is int or kind is float or kind is bool
                or kind is bytes or kind is type(None)):
            if left != right:
                return False
        else:
            return False
    return True


def _trial_typed_nested_classes():
    """Fixed standard-Pydantic schemas reachable from the fixed cohort roots."""
    from . import contracts
    from . import natural_specs as natural
    from . import pb_natural_specs as pb
    from . import production_trial_policy as policy

    return _trial_typed_classes() + (ApproveInput, TrialCaps, SQLiteSettlementCaps, SourceSnapshot,
        GoalSnapshot, StageKeys, GoalCardInput, natural.Recipe, natural.Step,
        pb.ReviewInput, policy.Outcome,
        contracts.Dependency, contracts.PermissionRequirement, contracts.View,
        contracts.FieldSource, contracts.BranchCondition, contracts.BranchGroup,
        contracts.WorkflowStep, contracts.ActionBinding, contracts.DataBinding,
        contracts.RuntimeIdentity, contracts.GoalSpec, contracts.ResourceSnapshot,
        contracts.NaturalPlanningPolicy, contracts.NaturalActivationBinding,
        contracts.FixedGoalAcceptance, contracts.ApplicationGenerationPolicy,
        contracts.ApplicationGenerationActivation, contracts.OrdinaryCsvReport,
        contracts.OrdinaryHumanReview, contracts.OrdinaryArtifactDelivery,
        contracts.OrdinaryCorrection, contracts.OrdinaryCorrectionFeedback,
        contracts.OrdinaryCorrectionRequest, contracts.OrdinaryCorrectionIssue)


def _trial_pure_mapping(value):
    """Exact native mapping projection, before any key lookup or comparison."""
    # The common exact-str dictionary already IS the required projection.
    # Walk every current key, without allocating tuple(items) or walking it
    # twice. Unknown require hooks retain the original callback/error order.
    if (require is _RAW_REQUIRE_ORIGINAL and require.__code__ is _RAW_REQUIRE_CODE
            and type(value) is dict and all(type(key) is str for key in value)):
        return value
    from sqlalchemy.engine import RowMapping
    from sqlalchemy.sql.elements import quoted_name

    if type(value) is RowMapping:
        from .natural_spec_runtime import _cold_graph_row_values

        # Native SQL row storage and dict(row) preserve trusted quoted_name
        # column keys. Project either shape only after checking every key.
        items = _cold_graph_row_values(value)
    else:
        require(type(value) is dict, 'Exact complete trial raw mapping required')
        items = tuple(dict.items(value))
    require(all(type(key) is str or type(key) is quoted_name for key, _ in items),
        'Exact trusted trial raw keys required')
    if type(value) is dict and all(type(key) is str for key, _ in items):
        return value
    names = tuple(str(key) for key, _ in items)
    require(len(set(names)) == len(names), 'Complete trial raw keys must remain distinct')
    return {name: item for name, (_, item) in zip(names, items, strict=True)}


_RAW_MAPPING_ORIGINAL = _trial_pure_mapping
_RAW_REQUIRE_ORIGINAL = require
_RAW_REQUIRE_CODE = require.__code__


def _trial_pure_data(value):
    """Copy only complete controlled data; never equality/iteration on strangers."""
    if (_RAW_COPY is not None and _trial_pure_mapping is _RAW_MAPPING_ORIGINAL
            and require is _RAW_REQUIRE_ORIGINAL):
        copied = _RAW_COPY(value)
        if copied is not _RAW_UNSUPPORTED:
            return copied
    from sqlalchemy.engine import RowMapping

    active = set()

    def visit(item):
        result: Any
        kind = type(item)
        if kind is str or kind is int or kind is float or kind is bool or kind is bytes or kind is type(None):
            return item
        require(kind is dict or kind is RowMapping or kind is list or kind is tuple,
            'Unsupported nested trial raw data')
        identity = id(item)
        require(identity not in active, 'Cyclic trial raw data')
        active.add(identity)
        if kind is dict or kind is RowMapping:
            raw = _trial_pure_mapping(item)
            result = {key: visit(child) for key, child in dict.items(raw)}
        elif kind is list:
            result = [visit(child) for child in item]
        else:
            result = tuple(visit(child) for child in item)
        active.remove(identity)
        return result

    return visit(value)


def _trial_typed_storage(expected, model):
    """Gate every actual nested value before the fixed standard serializer."""
    from .contracts import BranchCondition, WorkflowStep

    roots, allowed = _trial_typed_classes(), _trial_typed_nested_classes()
    require(any(expected is kind for kind in roots) and type(model) is expected,
        'Exact typed trial fact required')
    active: set[int] = set()
    seen: dict[int, Any] = {}

    def visit(value):
        result: Any
        kind = type(value)
        if (kind is str or kind is int or kind is float or kind is bool
                or kind is bytes or kind is type(None)):
            return value
        require(kind is dict or kind is list or kind is tuple
            or any(kind is item for item in allowed), 'Unsupported nested typed trial fact')
        identity = id(value)
        require(identity not in active, 'Cyclic typed trial fact')
        if identity in seen:
            return seen[identity]
        active.add(identity)
        if kind is dict:
            require(all(type(key) is str for key in value), 'Exact typed trial JSON keys required')
            result = {key: visit(child) for key, child in dict.items(value)}
        elif kind is list:
            result = [visit(child) for child in value]
        elif kind is tuple:
            result = tuple(visit(child) for child in value)
        else:
            raw = object.__getattribute__(value, '__dict__')
            fields = type.__getattribute__(kind, '__pydantic_fields__')
            selected = object.__getattribute__(value, '__pydantic_fields_set__')
            require(type(raw) is dict and all(type(key) is str for key in raw)
                and type(fields) is dict and all(type(key) is str for key in fields)
                and raw.keys() == fields.keys()
                and type(selected) is set and all(type(key) is str for key in selected)
                and selected <= fields.keys()
                and object.__getattribute__(value, '__pydantic_extra__') is None
                and object.__getattribute__(value, '__pydantic_private__') is None,
                'Complete fixed typed trial storage required')
            # These are the only two output omissions in the fixed schemas.
            # Preserve all actual container/numeric types before serialization;
            # a serializer must not normalize a list/tuple drift into equality.
            result = {key: visit(child) for key, child in dict.items(raw)
                if not (child is None and (kind is BranchCondition and key == 'value'
                    or kind is WorkflowStep and key == 'when'))}
        active.remove(identity)
        seen[identity] = result
        return result

    return visit(model)


def _trial_typed_values(models):
    """One pure complete cohort pass; no graph pin, IO, parse or authority."""
    from ._cold_typed_stream import _stream_values

    require(type(models) is list, 'Exact trial model cohort required')
    for entry in models:
        require(type(entry) is tuple and len(entry) == 3, 'Exact trial model triple required')
        expected, model, raw = entry
        if _stream_values(expected, model, raw):
            continue
        # A modified serializer retains the original pre-serializer raw
        # snapshot semantics; never assume an arbitrary replacement is pure.
        actual = _trial_typed_storage(expected, model)
        require(type(raw) is dict, 'Complete typed trial raw pin required')
        saved = _trial_pure_data(raw)
        require(_trial_typed_equal(actual, saved),
            'Typed trial storage changed after its complete raw proof')
        # All reachable actual values were gated above. The fixed schemas have
        # standard serializers only; their two exclude_if hooks test `is None`.
        # Suppress Pydantic's warning-dispatch callback for rejected typed
        # values; the complete type-aware comparison below owns that rejection.
        value = expected.model_dump(model, warnings=False)
        require(_trial_typed_equal(value, saved),
            'Typed trial fact changed after its complete raw proof')


def _trial_typed_guard(parent, models):
    """Keep the original full parent boundary, then the same pure cohort pass."""
    if parent is None:
        return None

    def checked():
        parent()
        _trial_typed_values(models)
    return checked


def _trial_typed_hold(models, expected, model, raw):
    """Identity-only lexical triples; no cached validation result or permit."""
    require(type(models) is list and type(model) is expected and type(raw) is dict)
    for entry in models:
        require(type(entry) is tuple and len(entry) == 3)
        kind, actual, previous = entry
        if kind is expected and actual is model and previous is raw:
            return
    models.append((expected, model, raw))


def _graph_trial_hold(graph, store, c, models, expected, model, raw):
    """Assemble one lexical parameter pin; caller checks the whole cohort."""
    _trial_typed_hold(models, expected, model, raw)


def _graph_trial_models_pin(graph, store, c, models):
    def parent():
        _graph_trial_pin(graph, store, c)
    try:
        _trial_typed_guard(parent, models)()
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_trial_produced(graph, store, c, models, expected, model):
    from .natural_spec_runtime import _ColdGraphRead

    if type(graph) is _ColdGraphRead:
        candidate = vars(graph).get('_producer_segment_candidate')
        if candidate is not None:
            from ._cold_producer_segment import _ProducerSegment
            require(type(candidate) is _ProducerSegment)
            return candidate.produced(graph, store, c, models, expected, model,
                                      _graph_trial_produced_legacy)
    return _graph_trial_produced_legacy(graph, store, c, models, expected, model)


def _graph_trial_produced_legacy(graph, store, c, models, expected, model):
    """Freeze one newly returned original-verifier output before following IO."""
    def parent():
        _graph_trial_pin(graph, store, c)
    checked = _trial_typed_guard(parent, models)
    checked()
    # Exact type is checked before invoking a fixed class serialization method.
    require(any(expected is kind for kind in _trial_typed_classes()) and type(model) is expected)
    raw = expected.model_dump(model)
    checked()
    _graph_trial_hold(graph, store, c, models, expected, model, raw)
    checked()
    return raw


def _graph_trial_contract_models(graph, store, c, models, contract):
    _graph_trial_pin(graph, store, c)
    raw = PBTrialContract.model_dump(graph.binding.contract)
    _graph_trial_pin(graph, store, c)
    _graph_trial_hold(graph, store, c, models, PBTrialContract, contract, raw)


def _graph_trial_journal_models_from_raw(models, state, cursor, raw):
    from . import production_trial_policy as policy

    raw = _trial_pure_mapping(raw)
    _trial_typed_hold(models, policy.Ledger, state, raw['ledger'])
    if cursor is not None:
        _trial_typed_hold(models, policy.AccountQuotaCursor, cursor, raw['cursor'])


def _graph_trial_accounted_models_from_raw(models, value, saved, *, _graph=None):
    from . import natural_source_archives as archive
    from . import production_trial_policy as policy
    from . import production_trial_sender as sender

    from . import _cold_source_packet as source_owned
    if (_SOURCE_BINDING_TYPE is not None and type(value) is _SOURCE_BINDING_TYPE):
        require(_graph is not None and saved is source_owned.pin(_graph,value))
        return
    saved = _trial_pure_mapping(saved)
    require(type(value) is tuple and len(value) == 4)
    run, actual, chains, ns = value
    require(type(actual) is tuple and type(chains) is tuple and type(ns) is tuple
        and type(saved['actual']) is tuple and type(saved['chains']) is tuple
        and type(saved['ns_reads']) is tuple)
    require(_trial_typed_equal(_trial_pure_data(_trial_pure_mapping(run)),
            _trial_pure_data(saved['run']))
        and _trial_typed_equal(tuple(_trial_pure_data(_trial_pure_mapping(a)) for a in actual),
            _trial_pure_data(saved['actual']))
        and len(chains) == len(saved['chains']) and len(ns) == len(saved['ns_reads']))
    for chain, raw in zip(chains, saved['chains'], strict=True):
        require(type(chain) is tuple and len(chain) == 6 and type(raw) is tuple and len(raw) == 6)
        slot, capture, parsed, checked, wire, payload = chain
        require(type(wire) is bytes and type(payload) is bytes
            and _trial_typed_equal(_trial_pure_data(parsed), _trial_pure_data(raw[2]))
            and _trial_typed_equal(_trial_pure_data(_trial_pure_mapping(checked)), _trial_pure_data(raw[3]))
            and _trial_typed_equal(wire, _trial_pure_data(raw[4]))
            and _trial_typed_equal(payload, _trial_pure_data(raw[5])))
        _trial_typed_hold(models, policy.Slot, slot, raw[0])
        _trial_typed_hold(models, sender.Capture, capture, raw[1])
    for entry, raw in zip(ns, saved['ns_reads'], strict=True):
        require(type(entry) is tuple and len(entry) == 5 and type(raw) is tuple and len(raw) == 5)
        aid, request, wire, response, payload = entry
        require(type(aid) is str and type(wire) is bytes and type(payload) is bytes
            and _trial_typed_equal(aid, _trial_pure_data(raw[0]))
            and _trial_typed_equal(wire, _trial_pure_data(raw[2]))
            and _trial_typed_equal(payload, _trial_pure_data(raw[4])))
        _trial_typed_hold(models, archive.BodyArchive, request, raw[1])
        _trial_typed_hold(models, archive.BodyArchive, response, raw[3])


def _graph_trial_frozen_models_from_raw(models, frozen, raw):
    from .contracts import FrozenRunContract

    _trial_typed_hold(models, FrozenRunContract, frozen, _trial_pure_mapping(raw))


def _graph_trial_extraction_models_from_raw(models, extraction, raw):
    from . import pb_natural_specs as pb

    raw = _trial_pure_mapping(raw)
    require(type(extraction) is tuple and len(extraction) == 4)
    draft, body, target, goal = extraction
    # Both sides retain their complete original raw comparison protocol;
    # only exact immutable views are decoded at this temporary boundary.
    require(_trial_typed_equal(_trial_pure_data(_source_owned_code.image.plain(draft)),
            _trial_pure_data(_source_owned_code.image.plain(raw['draft'])))
        and _trial_typed_equal(_trial_pure_data(target), _trial_pure_data(raw['target']))
        and _trial_typed_equal(_trial_pure_data(goal), _trial_pure_data(raw['goal'])))
    _trial_typed_hold(models, pb.ExtractInput, body, raw['request'])


def _graph_trial_stage_models_from_raw(models, stage_facts, inputs, *, _owned=None, _graph=None):
    inputs = _trial_pure_mapping(inputs)
    require((type(stage_facts) is tuple or type(stage_facts) is list) and len(stage_facts) == 9)
    job, bound, raw, metadata, gen, frozen, generated, source, extraction = stage_facts
    facet = _trial_pure_mapping(inputs['trial-generated-model-facet'])
    _graph_trial_frozen_models_from_raw(models, frozen, facet['frozen'])
    if _owned is not None:
        _owned.assert_family(_owned.graph, generated, 'generate')
        if source is not None:
            _owned.assert_family(_owned.graph, source, 'source')
    else:
        _graph_trial_accounted_models_from_raw(models, generated, inputs['cold-trial:accounted-generate'], _graph=_graph)
        if source is not None:
            _graph_trial_accounted_models_from_raw(models, source, inputs['cold-trial:accounted-source'], _graph=_graph)
    if extraction is not None:
        full = _trial_pure_mapping(inputs['cold-trial:complete'])
        _graph_trial_extraction_models_from_raw(models, extraction, full['extraction'])



def _graph_source_upstream_run_equal(ledger, value, expected):
    """Pre-issuance visible Run join, fully prepaid before compatibility copy.

    Only a parentless immutable SQL/JSON image is admitted here. Composite
    business readers continue using their original representation. No mutable
    copy, identity shortcut, authority or comparison result survives return.
    """
    from . import natural_spec_runtime as rt, cold_accounted as o
    from ._cold_accounted_budget import _Capacity, _Unsupported
    from ._cold_accounted_values import _node
    source = rt._source_owned_code
    source.current()
    if not source.image.is_kind(value, 'd', 'r'):
        raise _Unsupported('source_upstream_view')
    owner = value.owner()
    pin = rt._SOURCE_OWNER_PIN(owner)
    if len(pin) != 2:  # no unmetered parent expansion during plain()
        raise _Unsupported('source_upstream_parents')
    data = source.native.owned_data(owner)
    nodes, leaves = data[1], data[2]
    count = len(nodes)
    if count > ledger.bounds.nodes:
        raise _Capacity('source_upstream_nodes')
    ledger.spend(count + len(leaves) + 1)
    # Covers the complete metadata walk BEFORE examining payloads. Native
    # shape bounds each table by 100000 nodes and 1000000 edges. Refund only
    # after all temporary dictionaries/views/packets have been released.
    ticket = ledger.reserve(units=8192 + 4096 * count + 128 * len(leaves))
    copied = packet = None
    try:
        edges = 0
        for tag, payload in nodes:
            if tag not in ('n','t','f','i','v','s','b','u','d','r','l','q'):
                raise _Unsupported('source_upstream_node')
            edges += (2 * len(payload) if tag == 'd' else len(payload)
                if tag in ('r','l','q') else 1 if tag == 'u' else 0)
        if edges > ledger.bounds.edges:
            raise _Capacity('source_upstream_edges')
        leaf = sum(len(v) * (4 if type(v) is str else 1) for v in leaves)
        if leaf > ledger.bounds.leaf_bytes:
            raise _Capacity('source_upstream_leaf')
        ticket.grow(64 * edges + 8 * leaf)
        # Includes key collisions/linear native lookups, recursion frames and
        # text hashing; aliases use plain()'s canonical Owner/node memo.
        ledger.spend(128 * (count + edges + 1) ** 2 * (leaf + 1))
        copied = source.image.plain(value)
        source.current()
        if type(copied) is not dict or set(copied) != set(o._FIELDS['run']):
            raise _Unsupported('source_upstream_run_schema')
        with ledger.snapshot(copied, visible=True) as packet:
            result = ledger.equal(expected, _node(packet))
            packet = None
        return result
    finally:
        copied = packet = None
        ticket.close()



def _graph_trial_stage_raw_from_raw(stage_facts, full, *, _graph=None):
    """Original complete Stage identity joins, over exact controlled storage."""
    full = _trial_pure_mapping(full)
    require((type(stage_facts) is tuple or type(stage_facts) is list) and len(stage_facts) == 9)
    job, bound, raw, metadata, gen, frozen, generated, source, extraction = stage_facts
    _trial_pure_mapping(bound)
    if bound is full['binding']:
        require(_trial_typed_equal(_trial_pure_data(_trial_pure_mapping(job)),
                _trial_pure_data(_trial_pure_mapping(full['cold_job'])))
            and source is not None and extraction is not None)
    else:
        from . import _cold_source_packet as source_owned
        source_job = job
        if source_owned.image.is_kind(job, 'd', 'r'):
            # The first Source Run reader now owns its complete SQL row.
            # Only this immutable boundary projects to the original visible
            # mapping protocol. Keep the global raw/type gates unchanged;
            # hidden storage and aliases remain in the scoped Owner pin.
            require(_graph is not None)
            source_owned.fact_current(_graph)
            source_job = source_owned.image.plain(job)
        saved_source = (source_owned.raw_fields(_graph,full['source'])
            if type(full['source']) is tuple else _trial_pure_mapping(full['source']))
        saved_job = saved_source['run']
        if source_owned.image.is_kind(saved_job, 'd', 'r'):
            saved_job = source_owned.image.plain(saved_job)
        require(bound is full['source_binding']
            and _trial_typed_equal(_trial_pure_data(_trial_pure_mapping(source_job)),
                _trial_pure_data(saved_job))
            and source is None and extraction is None)
    generation = _trial_pure_mapping(full['generation'])
    require(raw is generation['raw'] and metadata is generation['metadata']
        and _trial_typed_equal(_trial_pure_data(_trial_pure_mapping(gen)),
            _trial_pure_data(generation['run'])))
    if extraction is not None:
        require(type(extraction) is tuple and len(extraction) == 4)
        draft, body, target, goal = extraction
        saved = _trial_pure_mapping(full['extraction'])
        require(draft is saved['draft'] and target is saved['target'] and goal is saved['goal'])


def _graph_trial_journal_models(graph, store, c, models, state, cursor=None):
    _graph_trial_pin(graph, store, c)
    inputs = _trial_pure_mapping(graph.inputs)
    require('cold-trial:journal' in inputs, 'Complete original J raw pin required')
    _graph_trial_journal_models_from_raw(models, state, cursor, inputs['cold-trial:journal'])


def _graph_trial_accounted_models(graph, store, c, models, value, stage, *, _owned=None):
    _graph_trial_pin(graph, store, c)
    require(type(stage) is str and stage in ('source', 'generate'))
    if _owned is not None:
        from .cold_accounted import _prewrite_mode
        _prewrite_mode(_owned, graph).assert_family(graph, value, stage)
        return
    key = 'cold-trial:accounted-' + stage
    inputs = _trial_pure_mapping(graph.inputs)
    require(key in inputs, 'Complete accounted stage raw pin required')
    _graph_trial_accounted_models_from_raw(models, value, inputs[key], _graph=graph)


def _graph_trial_frozen_models(graph, store, c, models, frozen):
    _graph_trial_pin(graph, store, c)
    inputs = _trial_pure_mapping(graph.inputs)
    require('trial-generated-model-facet' in inputs, 'Complete native Generation facet raw pin required')
    facet = _trial_pure_mapping(inputs['trial-generated-model-facet'])
    _graph_trial_frozen_models_from_raw(models, frozen, facet['frozen'])


def _graph_trial_extraction_models(graph, store, c, models, extraction):
    _graph_trial_pin(graph, store, c)
    inputs = _trial_pure_mapping(graph.inputs)
    require('cold-trial:complete' in inputs)
    full = _trial_pure_mapping(inputs['cold-trial:complete'])
    _graph_trial_extraction_models_from_raw(models, extraction, full['extraction'])


def _graph_trial_stage_models(graph, store, c, models, stage_facts, *, _owned=None):
    _graph_trial_pin(graph, store, c)
    _graph_trial_stage_models_from_raw(models, stage_facts, graph.inputs, _graph=graph, **{'_owned': _owned} if _owned is not None else {})


def _graph_trial_accounted_raw(graph, store, c, value, models):
    """One shared full serialization shape; contains every original body byte."""
    from . import natural_source_archives as archive
    from . import production_trial_policy as policy
    from . import production_trial_sender as sender
    run, actual, chains, ns = value
    full_chains, full_ns = [], []
    for slot, capture, parsed, checked, wire, payload in chains:
        a = _graph_trial_produced(graph, store, c, models, policy.Slot, slot)
        b = _graph_trial_produced(graph, store, c, models, sender.Capture, capture)
        full_chains.append((a, b, parsed, dict(checked), wire, payload))
    for aid, request, wire, response, payload in ns:
        a = _graph_trial_produced(graph, store, c, models, archive.BodyArchive, request)
        b = _graph_trial_produced(graph, store, c, models, archive.BodyArchive, response)
        full_ns.append((aid, a, wire, b, payload))
    return dict(run=dict(run), actual=tuple(dict(a) for a in actual),
        chains=tuple(full_chains), ns_reads=tuple(full_ns))


def _graph_trial_stage_raw(graph, stage_facts, *, _owned=None):
    """External boundary retains a full pin before the shared pure joins."""
    from .natural_spec_runtime import _ColdGraphRead

    require(type(graph) is _ColdGraphRead)
    _graph_trial_pin(graph, graph.store, graph.connection)
    if _owned is not None:
        from .cold_accounted import _prewrite_mode
        _prewrite_mode(_owned, graph).assert_stage(stage_facts)
        return
    inputs = _trial_pure_mapping(graph.inputs)
    require('cold-trial:complete' in inputs)
    _graph_trial_stage_raw_from_raw(stage_facts, inputs['cold-trial:complete'], _graph=graph)


def raw_snapshot_backend():
    """Loaded implementation identity, never a credential or an admission."""
    if _RAW_COPY is None:
        return {"kind": "python"}
    require(hashlib.sha256(_RAW_BINARY_PATH.read_bytes()).hexdigest() == _RAW_BINARY_SHA,
            "Loaded raw capture binary changed on disk")
    return {"kind": "native", "source_sha256": _RAW_SOURCE_SHA,
            "binary_sha256": _RAW_BINARY_SHA, "binary": _RAW_BINARY_PATH.name}


from . import _cold_source_packet as _source_owned_code
_COHORT_BUILTIN_ROLES = tuple((name, globals().get(name, __builtins__[name]
    if type(__builtins__) is dict else getattr(__builtins__, name))) for name in (
        'type','dict','list','tuple','set','str','int','float','bool','bytes','object',
        'all','any','len','id','iter','next','zip'))
_COHORT_MODULE_BINDINGS = tuple((name,value) for name,value in globals().copy().items()
    if not name.startswith('__'))
_source_owned_code.register(1,globals(),tuple(name for name,value in globals().copy().items()
    if type(value) is _source_owned_code.FunctionType and value.__module__==__name__),
    constants=('_SOURCE_OWNED_CHECK','_SOURCE_BINDING_TYPE','_SOURCE_OWNED_ENABLED','_SOURCE_CAPACITY',
        '_COHORT_BUILTIN_ROLES','_COHORT_MODULE_BINDINGS'))
