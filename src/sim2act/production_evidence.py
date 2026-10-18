"""Production account evidence boundary, with no supported authority source.

Candidate validation checks data consistency only. Caller booleans, opaque IDs
and evidence hashes do not prove provenance, entitlement or non-chargeability.
No function here returns a FeeProof, Permit, account credential or dispatch right.
"""

import math
import time
from typing import Literal, NoReturn

from pydantic import ConfigDict, Field, ValidationError

from . import natural_live_admission as gate
from .contracts import FieldSource, Strict
from .db import fingerprint
from .errors import DomainError
from .goals import GoalCardInput
from .natural_specs import Recipe, Step

SOURCE_MISSING = "No reviewed production account evidence source is supported"
OPAQUE = r"^[A-Za-z0-9_-]{1,200}$"


class EvidenceData(Strict):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True,
                              revalidate_instances="always")


class EvidenceRequirements(EvidenceData):
    """Projection of an original contract, not proof of current authorization."""

    namespace: Literal["production-account-requirements.v1"] = "production-account-requirements.v1"
    principal_id: str = Field(pattern=r"^user_[a-f0-9]{32}$")
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    runtime_id: str = Field(pattern=r"^runtime_[a-f0-9]{32}$")
    trial_key: str = Field(pattern=gate.KEY)
    approval_key: str = Field(pattern=gate.KEY)
    contract_fingerprint: str = Field(pattern=gate.HASH)
    software_fingerprint: str = Field(pattern=gate.HASH)
    authorization_fingerprint: str = Field(pattern=gate.HASH)
    provider: Literal["intern-ai"] = "intern-ai"
    model: Literal["intern-s2"] = "intern-s2"
    endpoint: Literal["https://chat.intern-ai.org.cn/api/v1/chat/completions"] = (
        "https://chat.intern-ai.org.cn/api/v1/chat/completions")
    quota_subject: str = Field(min_length=1, max_length=200)
    expires_at: float = Field(gt=0, allow_inf_nan=False)
    paid_cap: int = Field(default=0, strict=True, ge=0, le=0)


class AccountEvidenceCandidate(EvidenceData):
    """Untrusted data references; never raw provider payloads or credentials.

    Revocation and both entitlement claims must be explicit. Even complete
    claims are not verified facts without a separately reviewed trusted source.
    """

    namespace: Literal["production-account-candidate.v1"] = "production-account-candidate.v1"
    requirements_fingerprint: str = Field(pattern=gate.HASH)
    source_id: str = Field(pattern=OPAQUE)
    account_id: str = Field(pattern=OPAQUE)
    quota_subject: str = Field(min_length=1, max_length=200)
    entitlement_evidence_sha256: str = Field(pattern=gate.HASH)
    enforcement_evidence_sha256: str = Field(pattern=gate.HASH)
    issued_at: float = Field(gt=0, allow_inf_nan=False)
    checked_at: float = Field(gt=0, allow_inf_nan=False)
    expires_at: float = Field(gt=0, allow_inf_nan=False)
    outcome: Literal["RECEIVED", "UNKNOWN"]
    legal_free_entitlement: bool | None
    enforced_non_chargeable: bool | None
    revoked: bool | None
    paid_cap: int = Field(strict=True, ge=0, le=0)


class CandidateDiagnostic(EvidenceData):
    requirements_fingerprint: str = Field(pattern=gate.HASH)
    candidate_fingerprint: str = Field(pattern=gate.HASH)
    data_consistent: Literal[True] = True
    source_verification: Literal["SOURCE_UNVERIFIED"] = "SOURCE_UNVERIFIED"
    fee_verification: Literal["NOT_VERIFIED"] = "NOT_VERIFIED"
    live_allowed: Literal[False] = False
    dispatch_authorized: Literal[False] = False


def _deny(message: str) -> NoReturn:
    raise DomainError("LIVE_BLOCKED", message)


def _model_data(value, model):
    data = object.__getattribute__(value, "__dict__")
    if (type(data) is not dict or any(type(k) is not str for k in data)
            or set(data) != set(model.model_fields)
            or object.__getattribute__(value, "__pydantic_extra__") is not None
            or object.__getattribute__(value, "__pydantic_private__") is not None):
        _deny("Account evidence model contains undeclared data")
    return data


def _flat(value, model):
    # Do not call methods, format errors/reprs, or serialize arbitrary objects.
    # model_copy/model_construct can bypass Pydantic validation and frozen=True.
    if type(value) is not model:
        _deny("Account evidence must be exact typed data")
    data = _model_data(value, model)
    if any(type(v) not in (str, int, float, bool, type(None)) for v in data.values()):
        _deny("Account evidence must contain flat primitive data only")
    try:
        return model.model_validate(dict(data))
    except ValidationError:
        _deny("Account evidence data does not satisfy its strict schema")


def _contract_data(value, depth=0):
    """Extract only declared trusted schema data, without instance serializers."""
    if depth > 16:
        _deny("Production evidence original contract exceeds its data depth")
    kind = type(value)
    if kind in (str, int, float, bool, type(None)):
        return value
    if kind is list:
        return [_contract_data(item, depth + 1) for item in value]
    if kind is dict:
        if any(type(key) is not str for key in value):
            _deny("Production evidence original contract has invalid data keys")
        return {key: _contract_data(item, depth + 1) for key, item in value.items()}
    if kind in (gate.TrialContract, gate.TrialContractV2, gate.PBTrialContract,
                gate.TrialCaps, gate.MaterialGoal, gate.StageKeys, gate.GoalSnapshot,
                gate.SourceSnapshot, GoalCardInput, Recipe, Step, FieldSource):
        return _contract_data(_model_data(value, kind), depth + 1)
    _deny("Production evidence original contract contains untrusted data")


def requirements_for(user, contract, approval_key) -> EvidenceRequirements:
    """Pure projection; production caller must first check original _approved.

    This helper alone does not read consent, current permissions or revocation.
    The complete contract fingerprint binds both materials/Goals and all caps.
    """
    if (type(contract) not in (gate.TrialContract, gate.TrialContractV2, gate.PBTrialContract)
            or type(user) is not str or type(approval_key) is not str):
        _deny("Production evidence requires an exact original trial contract")
    try:
        original = gate.parse_contract(_contract_data(contract))
        if original.principal_id != user:
            _deny("Production evidence principal differs from the original contract")
        return EvidenceRequirements(principal_id=user, project_id=original.project_id,
            runtime_id=original.runtime_id, trial_key=original.trial_key,
            approval_key=approval_key, contract_fingerprint=fingerprint(original.model_dump()),
            software_fingerprint=original.software_fingerprint,
            authorization_fingerprint=original.authorization_fingerprint,
            model=original.model, endpoint=original.endpoint,
            quota_subject=original.quota_subject, expires_at=original.expires_at,
            paid_cap=original.caps.paid_cap)
    except ValidationError:
        _deny("Production evidence original contract does not satisfy its strict schema")


def validate_candidate(requirements, candidate, *, now=None) -> CandidateDiagnostic:
    """Pure structural diagnostic; never promoted into production admission.

    The 30-second maximum age is a conservative engineering bound, not a claim
    about provider rules. No expiry is refreshed, extended or persisted here.
    """
    expected = _flat(requirements, EvidenceRequirements)
    supplied = _flat(candidate, AccountEvidenceCandidate)
    reference = time.time() if now is None else now
    if (type(reference) not in (int, float) or not math.isfinite(reference) or reference <= 0):
        _deny("Account evidence reference time is invalid")
    # Reuse the sole account-to-quota algorithm; no second bucket convention.
    from .production_trial_admission import canonical_quota_subject

    if (supplied.requirements_fingerprint != fingerprint(expected.model_dump())
            or supplied.quota_subject != expected.quota_subject
            or supplied.quota_subject != canonical_quota_subject(supplied.account_id)):
        _deny("Account evidence binding differs from the exact trial requirements")
    if (supplied.outcome != "RECEIVED" or supplied.revoked is not False
            or supplied.legal_free_entitlement is not True
            or supplied.enforced_non_chargeable is not True):
        _deny("Account evidence outcome, revocation or entitlement is incomplete")
    if (not supplied.issued_at <= supplied.checked_at <= reference
            < supplied.expires_at <= expected.expires_at
            or reference - supplied.checked_at > 30):
        _deny("Account evidence is stale, expired or outside its original time bounds")
    return CandidateDiagnostic(requirements_fingerprint=fingerprint(expected.model_dump()),
                               candidate_fingerprint=fingerprint(supplied.model_dump()))


def resolve_account(user, contract, approval_key) -> NoReturn:
    """Unregistered production boundary; accepts no source/record/callback override.

    Call only after original _approved. Candidate diagnostics cannot supply
    authority here. Missing source fails before reservation, send or settlement;
    no automatic resend or assumption of zero usage/fees can follow this result.
    """
    requirements_for(user, contract, approval_key)
    _deny(SOURCE_MISSING)
