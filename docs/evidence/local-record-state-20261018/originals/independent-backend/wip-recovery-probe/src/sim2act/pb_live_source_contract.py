"""Read-only P-B LIVE source evidence contract; no production resolver is installed.

A response-shaped object is not trusted provenance. Only the explicitly synthetic
resolver below is executable in this slice. Its receipt never authorizes LIVE,
network dispatch, a Run, a reservation, or settlement. Production registration and
verification of real archived provider evidence remain separate acceptance work.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol

from pydantic import Field

from .contracts import Strict
from .db import fingerprint
from .errors import DomainError
from .natural_live_admission import HASH, KEY, ApproveInput, MaterialGoal, PBTrialContract
from .natural_specs import Recipe


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise DomainError("LIVE_BLOCKED", message)


class LivePBSourceContract(Strict):
    """Exact expectations, never a caller assertion that those facts were proved."""

    trial: PBTrialContract
    approval_key: str = Field(pattern=KEY)
    provider: str = Field(min_length=1, max_length=100)
    account_id: str = Field(min_length=1, max_length=200)
    source_run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    source_app_id: str = Field(pattern=r"^[a-z]+_[a-f0-9]{32}$")
    source_attempt_ids: tuple[
        Annotated[str, Field(pattern=r"^attempt_[a-f0-9]{32}$")],
        Annotated[str, Field(pattern=r"^attempt_[a-f0-9]{32}$")]]
    response_attempt_id: str = Field(pattern=r"^attempt_[a-f0-9]{32}$")
    extraction_request_key: str = Field(pattern=KEY)
    expected_extraction_fingerprint: str = Field(pattern=HASH)


@dataclass(frozen=True)
class UsageEvidence:
    status: str
    source: str
    response_sha256: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ResponseEvidence:
    trial_fingerprint: str
    approval_fingerprint: str
    attempt_id: str
    trial_key: str
    provider: str
    account_id: str
    source_run_id: str
    mode: str
    status: str
    provider_request_id: str
    provider_response_id: str
    wire: bytes
    wire_sha256: str
    raw_response: bytes
    response_sha256: str
    usage: UsageEvidence


@dataclass(frozen=True)
class SourceSlotEvidence:
    trial_fingerprint: str
    approval_fingerprint: str
    reserved_tokens: int
    trial_key: str
    source_run_id: str
    attempt_id: str
    stage: str
    accepted: bool
    wire_sha256: str
    response_sha256: str
    usage: UsageEvidence


@dataclass(frozen=True)
class SourceEvidence:
    trial_fingerprint: str
    approval_fingerprint: str
    trial_key: str
    project_id: str
    principal_id: str
    runtime_id: str
    provider: str
    account_id: str
    quota_subject: str
    source_run_id: str
    source_app_id: str
    source_request_key: str
    source_status: str
    source_material: MaterialGoal
    cold_material: MaterialGoal
    attempts: tuple[ResponseEvidence, ResponseEvidence]
    source_slots: tuple[SourceSlotEvidence, SourceSlotEvidence]
    extraction_request_key: str
    extraction_response_attempt_id: str
    extraction_response_sha256: str
    extraction_recipe: Recipe
    extraction_fingerprint: str


class SourceResolver(Protocol):
    """Future server-owned read-only archive resolver, never supplied by HTTP DTO."""

    def resolve(self, contract: LivePBSourceContract) -> SourceEvidence: ...


@dataclass(frozen=True)
class SyntheticSourceResolver:
    """Fixed offline fixture, with no callback or network capability."""

    evidence: SourceEvidence

    def resolve(self, contract: LivePBSourceContract) -> SourceEvidence:
        return self.evidence


class SourceReceipt(Strict):
    contract_fingerprint: str
    source_run_id: str
    response_attempt_id: str
    trial_fingerprint: str
    account_id: str
    quota_subject: str
    provider: str
    evidence_scope: Literal["SYNTHETIC"] = "SYNTHETIC"
    verification: Literal["NOT_LIVE_VERIFIED"] = "NOT_LIVE_VERIFIED"
    live_allowed: Literal[False] = False
    actual_model_requests: Literal[0] = 0


def extraction_fingerprint(evidence: SourceEvidence) -> str:
    """Fingerprint the entire paired extraction anchor, including edited Recipe."""
    return fingerprint(dict(trial_fingerprint=evidence.trial_fingerprint,
        approval_fingerprint=evidence.approval_fingerprint,
        trial_key=evidence.trial_key, project_id=evidence.project_id,
        principal_id=evidence.principal_id, provider=evidence.provider,
        account_id=evidence.account_id, source_run_id=evidence.source_run_id,
        source_app_id=evidence.source_app_id, request_key=evidence.extraction_request_key,
        response_attempt_id=evidence.extraction_response_attempt_id,
        response_sha256=evidence.extraction_response_sha256,
        recipe=evidence.extraction_recipe.model_dump(),
        source_material=evidence.source_material.model_dump(),
        cold_material=evidence.cold_material.model_dump()))


def approval_fingerprint(contract: LivePBSourceContract) -> str:
    """Original exact approval input identity, not a claim of current approval."""
    return fingerprint(ApproveInput(expected_contract_fingerprint=fingerprint(contract.trial.model_dump()),
        request_key=contract.approval_key,
        consent="APPROVE_ONLY_THIS_EXACT_SEVEN_SLOT_ZERO_PAID_NATURAL_TRIAL").model_dump())


def _response(contract: LivePBSourceContract, proof: ResponseEvidence) -> None:
    trial = contract.trial
    _require(proof.trial_fingerprint == fingerprint(trial.model_dump())
        and proof.approval_fingerprint == approval_fingerprint(contract)
        and proof.trial_key == trial.trial_key and proof.provider == contract.provider
        and proof.account_id == contract.account_id and proof.source_run_id == contract.source_run_id
        and proof.mode == "LIVE" and proof.status == "VERIFIED"
        and bool(proof.provider_request_id) and bool(proof.provider_response_id),
        "P-B source Attempt identity, provider provenance or terminal status differs")
    _require(type(proof.wire) is bytes and type(proof.raw_response) is bytes
        and 0 < len(proof.wire) <= trial.caps.max_wire_bytes
        and 0 < len(proof.raw_response) <= trial.caps.max_response_ascii_bytes
        and hashlib.sha256(proof.wire).hexdigest() == proof.wire_sha256
        and hashlib.sha256(proof.raw_response).hexdigest() == proof.response_sha256,
        "P-B original wire and complete raw response bytes must match their archives")
    try:
        wire = json.loads(proof.wire)
        response = json.loads(proof.raw_response.decode("ascii"))
    except (ValueError, UnicodeError) as error:
        raise DomainError("LIVE_BLOCKED", "P-B source archives are not complete JSON") from error
    _require(isinstance(wire, dict) and isinstance(response, dict),
        "P-B source archives must be JSON objects")
    _require(wire.get("model") == response.get("model") == trial.model
        and wire.get("stream") is False and type(wire.get("max_tokens")) is int
        and 0 < wire["max_tokens"] <= trial.caps.max_output_tokens
        and response.get("id") == proof.provider_response_id,
        "P-B original provider request and response pairing differs")
    usage = proof.usage
    tokens = dict(prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens)
    _require(usage.status == "known" and usage.source == "PROVIDER_RESPONSE"
        and usage.response_sha256 == proof.response_sha256
        and all(type(v) is int and v >= 0 for v in tokens.values())
        and usage.total_tokens == usage.prompt_tokens + usage.completion_tokens
        and usage.completion_tokens <= wire["max_tokens"]
        and usage.total_tokens <= len(proof.wire) + wire["max_tokens"]
        and isinstance(response.get("usage"), dict)
        and all(type(v) is int for v in response["usage"].values())
        and response["usage"] == tokens,
        "P-B source usage must be complete, known and paired with the original response")


def resolve_source(contract: LivePBSourceContract,
                   resolver: SourceResolver | None = None) -> SourceReceipt:
    """Check an isolated typed fixture; default production and foreign callbacks deny.

    No trusted production resolver is registered. In particular, calling code
    cannot grant LIVE by changing an evidence object's mode or scope string.
    """
    _require(type(resolver) is SyntheticSourceResolver,
        "No trusted production P-B source archive resolver is registered")
    _require(type(contract) is LivePBSourceContract, "P-B source contract must be typed")
    # Re-validate nested caller expectations even after unchecked model_copy().
    try:
        exact = LivePBSourceContract.model_validate(contract.model_dump())
    except (ValueError, TypeError) as error:
        raise DomainError("LIVE_BLOCKED", "P-B source contract is invalid") from error
    _require(exact == contract and contract.trial.expires_at > time.time(),
        "P-B source contract changed or expired")
    assert isinstance(resolver, SyntheticSourceResolver)
    evidence = resolver.resolve(contract)
    _require(type(evidence) is SourceEvidence, "P-B source evidence must be typed archive data")
    trial = contract.trial
    _require(evidence.trial_fingerprint == fingerprint(trial.model_dump())
        and evidence.approval_fingerprint == approval_fingerprint(contract)
        and evidence.trial_key == trial.trial_key and evidence.project_id == trial.project_id
        and evidence.principal_id == trial.principal_id and evidence.runtime_id == trial.runtime_id
        and evidence.provider == contract.provider and evidence.account_id == contract.account_id
        and evidence.quota_subject == trial.quota_subject
        and evidence.source_run_id == contract.source_run_id
        and evidence.source_app_id == contract.source_app_id
        and evidence.source_request_key == trial.stage_keys.source
        and evidence.source_status == "SUCCEEDED",
        "P-B requires the original successful task in this exact trial and account")
    _require(evidence.source_material == trial.bindings[0]
        and evidence.cold_material == trial.bindings[1]
        and evidence.extraction_recipe == trial.extraction_recipe
        and evidence.extraction_request_key == contract.extraction_request_key
        == trial.extraction_request_key,
        "P-B exact extraction Recipe, new cold material or full Goal differs")
    _require(type(evidence.attempts) is tuple and len(evidence.attempts) == 2
        and all(type(p) is ResponseEvidence and type(p.usage) is UsageEvidence
                for p in evidence.attempts)
        and len(set(contract.source_attempt_ids)) == 2
        and {p.attempt_id for p in evidence.attempts} == set(contract.source_attempt_ids)
        and contract.response_attempt_id in contract.source_attempt_ids
        and len({p.provider_request_id for p in evidence.attempts}) == 2
        and len({p.provider_response_id for p in evidence.attempts}) == 2,
        "P-B source requires two distinct original provider Attempts")
    for proof in evidence.attempts:
        _require(type(proof) is ResponseEvidence and type(proof.usage) is UsageEvidence,
            "P-B original response and usage must be typed archive data")
        _response(contract, proof)
    selected = next(p for p in evidence.attempts if p.attempt_id == contract.response_attempt_id)
    _require(evidence.extraction_response_attempt_id == selected.attempt_id
        and evidence.extraction_response_sha256 == selected.response_sha256
        and evidence.extraction_fingerprint == contract.expected_extraction_fingerprint
        == extraction_fingerprint(evidence),
        "P-B extraction is not paired with this original response Attempt and complete Recipe")
    _require(type(evidence.source_slots) is tuple and len(evidence.source_slots) == 2
        and all(type(s) is SourceSlotEvidence and type(s.usage) is UsageEvidence
                for s in evidence.source_slots)
        and {s.attempt_id for s in evidence.source_slots} == set(contract.source_attempt_ids),
        "P-B source ledger must contain exactly the two original source slots")
    for slot in evidence.source_slots:
        proof = next(p for p in evidence.attempts if p.attempt_id == slot.attempt_id)
        _require(slot.trial_fingerprint == fingerprint(trial.model_dump())
            and slot.approval_fingerprint == approval_fingerprint(contract)
            and type(slot.reserved_tokens) is int
            and slot.reserved_tokens == len(proof.wire) + json.loads(proof.wire)["max_tokens"]
            and slot.usage.total_tokens <= slot.reserved_tokens
            and slot.trial_key == trial.trial_key and slot.source_run_id == contract.source_run_id
            and slot.stage == "source" and slot.accepted is True
            and slot.wire_sha256 == proof.wire_sha256
            and slot.response_sha256 == proof.response_sha256 and slot.usage == proof.usage,
            "P-B source accounting slot is unknown, unaccepted or paired with different evidence")
    _require(sum(s.reserved_tokens for s in evidence.source_slots) <= trial.caps.per_run_reserved,
        "P-B source reserved envelope exceeds the original Run cap")
    return SourceReceipt(contract_fingerprint=fingerprint(contract.model_dump()),
        trial_fingerprint=fingerprint(trial.model_dump()), account_id=contract.account_id,
        quota_subject=trial.quota_subject, provider=contract.provider,
        source_run_id=contract.source_run_id, response_attempt_id=contract.response_attempt_id)
