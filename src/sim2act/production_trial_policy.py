"""Uninstalled production admission/accounting policy kernel, with no IO rights.

No API, Worker, resolver or sender installs this module. SourceVerificationResult
is an internal input contract, not a source authority or proof that its producer
exists. Tests supply synthetic results. Every receipt is non-executable.

Transitions return immutable ledger AND account quota snapshots. A future
controller must atomically lock/CAS and persist both, and independently install
reviewed source, software and sending authorities. Serialization is not durable
installation, and a supplied quota cursor is not a global DB/RPM guarantee.
"""

import hashlib
import math
import time
from typing import Literal

from pydantic import Field, ValidationError

from . import natural_live_admission as gate
from . import natural_trial_budget as budget
from . import production_evidence as evidence
from .db import fingerprint
from .errors import DomainError


class RunCheck(evidence.EvidenceData):
    requirements_fingerprint: str = Field(pattern=gate.HASH)
    approval_fingerprint: str = Field(pattern=gate.HASH)
    stage: gate.Stage
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    runtime_id: str
    version: int = Field(ge=1)
    fence: int = Field(ge=1)
    worker_id: str = Field(pattern=gate.KEY)
    stage_fingerprint: str | None = Field(default=None, pattern=gate.HASH)
    checked_at: float = Field(gt=0, allow_inf_nan=False)
    deadline: float = Field(gt=0, allow_inf_nan=False)


class SourceVerificationResult(evidence.EvidenceData):
    """Result interface for a future reviewed producer; never an HTTP input.

    Construction/ALLOW alone proves no provider facts. No real producer is
    installed. The kernel checks the supplied result's binding and validity;
    it does not discover free service or issue a FeeProof/Permit.
    """

    requirements_fingerprint: str = Field(pattern=gate.HASH)
    account_id: str = Field(pattern=evidence.OPAQUE)
    quota_subject: str = Field(min_length=1, max_length=200)
    # Channel identities must equal the original contract. Future channels need
    # a separately reviewed new contract; this result cannot select an endpoint.
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    endpoint: str = Field(min_length=1, max_length=300)
    evidence_fingerprint: str = Field(pattern=gate.HASH)
    decision: Literal["ALLOW", "DENY", "UNKNOWN"]
    legal_free_entitlement: bool | None
    enforced_non_chargeable: bool | None
    revoked: bool | None
    observed_at: float = Field(gt=0, allow_inf_nan=False)
    expires_at: float = Field(gt=0, allow_inf_nan=False)


class ReservationIdentity(evidence.EvidenceData):
    requirements_fingerprint: str = Field(pattern=gate.HASH)
    approval_fingerprint: str = Field(pattern=gate.HASH)
    stage: gate.Stage
    stage_fingerprint: str | None = Field(default=None, pattern=gate.HASH)
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    runtime_id: str
    version: int = Field(ge=1)
    fence: int = Field(ge=1)
    worker_id: str = Field(pattern=gate.KEY)
    account_id: str = Field(pattern=evidence.OPAQUE)
    quota_subject: str = Field(min_length=1, max_length=200)
    attempt_id: str = Field(pattern=r"^attempt_[a-f0-9]{32}$")
    wire_sha256: str = Field(pattern=gate.HASH)
    wire_bytes: int = Field(ge=1, le=32768)


class Outcome(evidence.EvidenceData):
    outcome: Literal["RECEIVED", "UNKNOWN"]
    response_sha256: str = Field(pattern=gate.HASH)
    response_ascii_bytes: int = Field(ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class Slot(evidence.EvidenceData):
    identity: ReservationIdentity
    reserved_at: float = Field(gt=0, allow_inf_nan=False)
    attempted: bool = False
    settlement: Outcome | None = None
    accepted: bool = False


class Ledger(evidence.EvidenceData):
    scope: evidence.EvidenceRequirements
    account_id: str = Field(pattern=evidence.OPAQUE)
    slots: tuple[Slot, ...] = ()
    halted: bool = False


class AccountQuotaCursor(evidence.EvidenceData):
    account_id: str = Field(pattern=evidence.OPAQUE)
    quota_subject: str = Field(min_length=1, max_length=200)
    last_reserved_at: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class Transition(evidence.EvidenceData):
    ledger: Ledger
    quota: AccountQuotaCursor
    duplicate: bool = False
    scope: Literal["UNINSTALLED_POLICY_ONLY"] = "UNINSTALLED_POLICY_ONLY"
    live_allowed: Literal[False] = False
    dispatch_authorized: Literal[False] = False
    real_source_verified: Literal[False] = False


def _require(ok, code="VERSION_CONFLICT"):
    if not ok:
        raise DomainError(code, "Uninstalled production policy boundary")


def _data(value, depth=0):
    _require(depth <= 16)
    kind = type(value)
    if kind in (str, int, float, bool, type(None)):
        return value
    if kind is tuple:
        return tuple(_data(item, depth + 1) for item in value)
    if kind in (RunCheck, SourceVerificationResult, ReservationIdentity, Outcome, Slot,
                Ledger, AccountQuotaCursor, Transition, evidence.EvidenceRequirements):
        return {key: _data(item, depth + 1)
                for key, item in evidence._model_data(value, kind).items()}
    _require(False)


def _typed(value, model):
    _require(type(value) is model)
    try:
        return model.model_validate(_data(value))
    except ValidationError:
        _require(False)


def _requirements(user, contract, key, *, _guard=None):
    requirements = gate._trial_result(evidence.requirements_for(user, contract, key), _guard)
    original = gate._trial_result(gate.parse_contract(gate._trial_result(evidence._contract_data(contract), _guard), **{'_guard': _guard} if _guard is not None else {}), _guard)
    gate._trial_result(budget.scope_for(original, key), _guard)
    return (original, requirements)


def check_run(store, c, user, contract, key, stage, run_id, version, fence, worker_id):
    """Current DB checks, separate from source verification. Not a reusable permit."""
    _require(c.in_transaction(), "PERMISSION_DENIED")
    original, expected = _requirements(user, contract, key)
    approval, phase, run, at = gate._run_context(
        store, c, user, original, key, stage, run_id, version, fence)
    _require(type(worker_id) is str and bool(worker_id) and run["worker_id"] == worker_id)
    if phase is None:
        gate._generation_context(store, c, run, original)
    return _run_check_from_facts(original, expected, approval, phase, run, at, stage,
                                 run_id, version, fence, worker_id)


def check_source(requirements, result, *, now):
    """Validate an internal result, without imposing a provider renewal interval."""
    expected = _typed(requirements, evidence.EvidenceRequirements)
    supplied = _typed(result, SourceVerificationResult)
    _require(type(now) in (int, float) and math.isfinite(now), "LIVE_BLOCKED")
    from .production_trial_admission import canonical_quota_subject

    _require(supplied.requirements_fingerprint == fingerprint(expected.model_dump())
        and supplied.quota_subject == expected.quota_subject
        == canonical_quota_subject(supplied.account_id)
        and supplied.provider == expected.provider and supplied.model == expected.model
        and supplied.endpoint == expected.endpoint, "LIVE_BLOCKED")
    _require(supplied.decision == "ALLOW" and supplied.revoked is False
        and supplied.legal_free_entitlement is True and supplied.enforced_non_chargeable is True
        and supplied.observed_at <= now < supplied.expires_at <= expected.expires_at,
        "LIVE_BLOCKED")
    return supplied


def identity_for(context, source, attempt_id, wire):
    current = _typed(context, RunCheck)
    result = _typed(source, SourceVerificationResult)
    _require(type(wire) is bytes and 0 < len(wire) <= 32768)
    return ReservationIdentity(**{k: getattr(current, k) for k in (
        "requirements_fingerprint", "approval_fingerprint", "stage", "stage_fingerprint",
        "run_id", "runtime_id", "version", "fence", "worker_id")},
        account_id=result.account_id, quota_subject=result.quota_subject, attempt_id=attempt_id,
        wire_bytes=len(wire), wire_sha256=hashlib.sha256(wire).hexdigest())


def _ledger(value):
    ledger = _typed(value, Ledger)
    from .production_trial_admission import canonical_quota_subject

    _require(ledger.scope.quota_subject == canonical_quota_subject(ledger.account_id))
    identities = [slot.identity for slot in ledger.slots]
    _require(len(identities) <= 7 and len({i.attempt_id for i in identities}) == len(identities))
    stage_runs: dict[gate.Stage, str] = {}
    previous = 0.0
    for index, slot in enumerate(ledger.slots):
        item = slot.identity
        _require(item.requirements_fingerprint == fingerprint(ledger.scope.model_dump())
            and item.account_id == ledger.account_id and item.quota_subject == ledger.scope.quota_subject
            and previous <= slot.reserved_at < ledger.scope.expires_at
            and (slot.settlement is not None or not slot.accepted)
            and (not slot.accepted or slot.attempted and _known(slot.settlement)
                 and slot.settlement.total_tokens <= item.wire_bytes + 1024))
        # Only the last slot may be pending/rejected. Restored state must be
        # reachable through this policy, including the original 1-RPM bound.
        _require((index == len(ledger.slots) - 1 or slot.accepted)
                 and (index == 0 or slot.reserved_at - previous >= 60))
        _require(stage_runs.setdefault(item.stage, item.run_id) == item.run_id)
        previous = slot.reserved_at
    _require(len(set(stage_runs.values())) == len(stage_runs))
    for stage, limit in budget.STAGES.items():
        own = [i for i in identities if i.stage == stage]
        _require(len(own) <= limit and sum(i.wire_bytes + 1024 for i in own) <= 64000)
    _require(sum(i.wire_bytes + 1024 for i in identities) <= 192000)
    _require(not any(s.settlement is not None and not s.accepted for s in ledger.slots)
             or ledger.halted)
    return ledger


def _bound(store, c, user, contract, key, ledger, quota, identity, wire):
    _require(c.in_transaction(), "PERMISSION_DENIED")
    original, expected = _requirements(user, contract, key)
    state, cursor, item = _ledger(ledger), _typed(quota, AccountQuotaCursor), _typed(identity, ReservationIdentity)
    return _bound_from_checked_facts(store, c, user, original, expected, state, cursor, item, wire)


def _bound_from_checked_facts(store, c, user, original, expected, state, cursor, item, wire, *, _guard=None):
    """Bind already checked policy inputs; no ledger parsing or source/Run permit.

    The caller supplies this call's complete _requirements/_ledger/_typed results.
    Project locking and the original scope/wire/cursor predicates still run here;
    reserve/record/settle retain their distinct subsequent freshness semantics.
    """
    _require(user == state.scope.principal_id and expected == state.scope, 'PERMISSION_DENIED')
    project = gate._trial_result(store.lock_project(c, user, state.scope.project_id), _guard)
    _require(project['runtime_id'] == state.scope.runtime_id, 'PERMISSION_DENIED')
    _require(item.requirements_fingerprint == gate._trial_result(fingerprint(gate._trial_result(expected.model_dump(), _guard)), _guard) and item.account_id == state.account_id == cursor.account_id and (item.quota_subject == expected.quota_subject == cursor.quota_subject) and (type(wire) is bytes) and (len(wire) == item.wire_bytes) and (gate._trial_result(gate._trial_result(hashlib.sha256(wire), _guard).hexdigest(), _guard) == item.wire_sha256))
    _require(not state.slots or (cursor.last_reserved_at is not None and cursor.last_reserved_at >= state.slots[-1].reserved_at))
    return (original, state, cursor, item)


def _fresh(store, c, user, contract, key, ledger, item, source):
    context = check_run(store, c, user, contract, key, item.stage, item.run_id,
                        item.version, item.fence, item.worker_id)
    result = check_source(ledger.scope, source, now=context.checked_at)
    _require(all(getattr(item, name) == getattr(context, name) for name in (
        "requirements_fingerprint", "approval_fingerprint", "stage", "stage_fingerprint",
        "run_id", "runtime_id", "version", "fence", "worker_id"))
        and item.account_id == result.account_id and item.quota_subject == result.quota_subject)
    deadline = min(context.deadline, result.expires_at)
    _require(time.time() < deadline, "BUDGET_EXHAUSTED")
    return context.checked_at, deadline


def reserve(store, c, user, contract, key, ledger, quota, identity, wire, source):
    """Allocate in immutable policy state; caller must persist ledger+quota atomically."""
    original, state, cursor, item = _bound(store, c, user, contract, key, ledger, quota, identity, wire)
    for slot in state.slots:
        if slot.identity.attempt_id == item.attempt_id:
            _require(slot.identity == item)
            return Transition(ledger=state, quota=cursor, duplicate=True)
    at, deadline = _fresh(store, c, user, original, key, state, item, source)
    _require(not state.halted and all(s.accepted for s in state.slots), "OUTCOME_UNKNOWN")
    _require(cursor.last_reserved_at is None or at - cursor.last_reserved_at >= 60, "RATE_LIMITED")
    updated = state.model_copy(update=dict(slots=(*state.slots, Slot(identity=item, reserved_at=at))))
    _ledger(updated)  # Enforce stage/total counts, envelopes and Run binding before returning.
    _require(time.time() < deadline, "BUDGET_EXHAUSTED")
    return Transition(ledger=updated, quota=cursor.model_copy(update=dict(last_reserved_at=at)))


def record_attempt(store, c, user, contract, key, ledger, quota, identity, wire, source):
    """Irreversible policy marker only. It never authorizes a sender call."""
    original, state, cursor, item = _bound(store, c, user, contract, key, ledger, quota, identity, wire)
    slot = next((s for s in state.slots if s.identity == item), None)
    if slot is None:
        raise DomainError("VERSION_CONFLICT", "Uninstalled production policy boundary")
    _require(not state.halted and not slot.attempted and slot.settlement is None, "OUTCOME_UNKNOWN")
    _fresh(store, c, user, original, key, state, item, source)
    updated = tuple(s.model_copy(update=dict(attempted=True)) if s == slot else s for s in state.slots)
    return Transition(ledger=state.model_copy(update=dict(slots=updated)), quota=cursor)


def _known(outcome):
    return (outcome is not None and outcome.outcome == "RECEIVED"
            and budget._known(outcome.model_dump()) and outcome.completion_tokens <= 1024
            and outcome.response_ascii_bytes <= 32768)


def settle(store, c, user, contract, key, ledger, quota, identity, wire, source, outcome):
    """Keep original usage after cancellation/expiry/revocation; never refund or resend."""
    original, state, cursor, item = _bound(store, c, user, contract, key, ledger, quota, identity, wire)
    received = _typed(outcome, Outcome)
    slot = next((s for s in state.slots if s.identity == item), None)
    if slot is None:
        raise DomainError("VERSION_CONFLICT", "Uninstalled production policy boundary")
    if slot.settlement is not None:
        _require(slot.settlement == received)
        return Transition(ledger=state, quota=cursor, duplicate=True)
    active = False
    try:
        _fresh(store, c, user, original, key, state, item, source)
        active = True
    except DomainError:
        pass
    accepted = bool(active and slot.attempted and _known(received)
        and received.total_tokens <= item.wire_bytes + 1024 and not state.halted)
    replacement = slot.model_copy(update=dict(settlement=received, accepted=accepted))
    updated = state.model_copy(update=dict(slots=tuple(replacement if s == slot else s for s in state.slots),
                                         halted=state.halted or not accepted))
    _ledger(updated)
    return Transition(ledger=updated, quota=cursor)


def _run_check_from_facts(original, expected, approval, phase, run, at, stage, run_id, version, fence, worker_id, *, _guard=None):
    """Original result fields only, after fresh complete Run/phase predicates."""
    return gate._trial_result(RunCheck(requirements_fingerprint=gate._trial_result(fingerprint(gate._trial_result(expected.model_dump(), _guard)), _guard), approval_fingerprint=gate._trial_result(fingerprint(gate._trial_result(approval.model_dump(), _guard)), _guard), stage=stage, run_id=run_id, runtime_id=run['runtime_id'], version=version, fence=fence, worker_id=worker_id, stage_fingerprint=None if phase is None else gate._trial_result(fingerprint(gate._trial_result(phase.model_dump(), _guard)), _guard), checked_at=at, deadline=min(run['lease_until'], original.expires_at, run['created_at'] + original.caps.run_seconds)), _guard)


def _graph_check_run(graph, store, c, user, contract, key, stage, run_id, version, fence, worker_id, stage_facts):
    """Consume an assembled complete graph stage; never accept an Authority DTO.

    stage_facts is (job,bound,Generate candidate,Generate metadata,
    Generate job,Generate frozen,accounted Generate,accounted Source,extraction).
    Its producers are fixed graph nodes; _graph_stage_current replays every
    original cross-role predicate, not an opaque checked flag or hash summary.
    """

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
        gate._graph_trial_stage_raw(graph, stage_facts)
    _models: list[tuple[type, object, dict]] = []
    _guard = gate._trial_typed_guard(_parent_pin, _models)
    try:
        from . import natural_live_admission as admission
        _guard()
        gate._graph_trial_contract_models(graph, store, c, _models, contract)
        gate._graph_trial_stage_models(graph, store, c, _models, stage_facts)
        _guard()
        _require(stage == 'cold')
        original, expected = gate._trial_result(_requirements(user, contract, key, **{'_guard': _guard} if _guard is not None else {}), _guard)
        gate._graph_trial_produced(graph, store, c, _models, gate.PBTrialContract, original)
        gate._graph_trial_produced(graph, store, c, _models, evidence.EvidenceRequirements, expected)
        approval, phase, run, at = gate._trial_result(admission._graph_run_context(graph, store, c, user, original, key, stage, run_id, version, fence, stage_facts), _guard)
        gate._graph_trial_produced(graph, store, c, _models, gate.Approval, approval)
        gate._graph_trial_produced(graph, store, c, _models, gate.StageAuthority, phase)
        _require(type(worker_id) is str and bool(worker_id) and (run['worker_id'] == worker_id))
        _guard()
        return gate._trial_result(_run_check_from_facts(original, expected, approval, phase, run, at, stage, run_id, version, fence, worker_id, _guard=_guard), _guard)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise
