"""Uninstalled server-side evidence contract; no real source producer exists.

Only an explicitly synthetic, test-only SQLite fixture can supply these four
raw evidence roles. Issuer labels, hashes and mirrored rows establish no real
account, entitlement or fee fact. There is no writer, HTTP route or callback.
"""

import base64
import hashlib
import json
import time
from typing import Literal

from pydantic import Field, ValidationError
from sqlalchemy import select
from sqlalchemy.engine import Connection

from . import production_trial_journal as journal
from . import production_trial_policy as policy
from .contracts import strict_json
from .db import Store, fingerprint
from .db import delivery_graph_requests as rows
from .errors import DomainError

KIND = "uninstalled-production-trial-source.v1"
ISSUER = "SIM2ACT_SYNTHETIC_FIXTURE_ONLY"
MAX_RAW = 8192


class Part(policy.evidence.EvidenceData):
    issuer: Literal["SIM2ACT_SYNTHETIC_FIXTURE_ONLY"]
    requirements_fingerprint: str = Field(pattern=policy.gate.HASH)
    account_id: str = Field(pattern=policy.evidence.OPAQUE)
    provider: Literal["intern-ai"]
    model: Literal["intern-s2"]
    endpoint: Literal["https://chat.intern-ai.org.cn/api/v1/chat/completions"]
    observed_at: float = Field(gt=0, allow_inf_nan=False)
    expires_at: float = Field(gt=0, allow_inf_nan=False)


class Identity(Part):
    role: Literal["identity"]
    identity_confirmed: bool | None


class Entitlement(Part):
    role: Literal["entitlement"]
    legal_free_entitlement: bool | None


class Enforcement(Part):
    role: Literal["enforcement"]
    enforced_zero_charge: bool | None
    paid_cap: int = Field(ge=0, le=1000000000)
    billable_fallback_disabled: bool | None


class Status(Part):
    role: Literal["status"]
    revoked: bool | None


class Bundle(policy.evidence.EvidenceData):
    version: Literal["UNINSTALLED_SYNTHETIC_ACCOUNT_SOURCE_V1"]
    identity: Identity
    entitlement: Entitlement
    enforcement: Enforcement
    status: Status


class Resolution(policy.evidence.EvidenceData):
    source: policy.SourceVerificationResult
    reason: str
    raw_sha256: str | None = Field(default=None, pattern=policy.gate.HASH)
    raw_bytes: int | None = Field(default=None, ge=0, le=MAX_RAW)
    scope: Literal["UNINSTALLED_SYNTHETIC_SOURCE_CONTRACT_ONLY"] = (
        "UNINSTALLED_SYNTHETIC_SOURCE_CONTRACT_ONLY"
    )
    live_allowed: Literal[False] = False
    dispatch_authorized: Literal[False] = False
    real_source_verified: Literal[False] = False


def _require(ok, code="PERMISSION_DENIED"):
    if not ok:
        raise DomainError(code, "Uninstalled source evidence contract boundary")


def request_for(scope, account_id):
    """Deterministic fixture storage binding, never a source selection interface."""
    return dict(namespace=KIND, requirements=scope.model_dump(mode="json"), account_id=account_id)


def _result(scope, account, at, decision, reason, *, payload=None, bundle=None):
    digest = None if payload is None else hashlib.sha256(payload).hexdigest()
    parts = (
        []
        if bundle is None
        else [bundle.identity, bundle.entitlement, bundle.enforcement, bundle.status]
    )
    enforced = None
    if bundle is not None:
        control = bundle.enforcement
        values = (control.enforced_zero_charge, control.billable_fallback_disabled)
        if control.paid_cap != 0 or any(value is False for value in values):
            enforced = False
        elif all(value is True for value in values):
            enforced = True
    return Resolution(
        source=policy.SourceVerificationResult(
            requirements_fingerprint=fingerprint(scope.model_dump()),
            account_id=account,
            quota_subject=scope.quota_subject,
            provider=scope.provider,
            model=scope.model,
            endpoint=scope.endpoint,
            # Zero is an unavailable-data sentinel, never positive evidence.
            evidence_fingerprint=digest or "0" * 64,
            decision=decision,
            legal_free_entitlement=None
            if bundle is None
            else bundle.entitlement.legal_free_entitlement,
            enforced_non_chargeable=enforced,
            revoked=None if bundle is None else bundle.status.revoked,
            observed_at=at if not parts else max(part.observed_at for part in parts),
            expires_at=scope.expires_at if not parts else min(part.expires_at for part in parts),
        ),
        reason=reason,
        raw_sha256=digest,
        raw_bytes=None if payload is None else len(payload),
    )


def _verify(scope, account, at, payload):
    try:
        raw = strict_json(payload, MAX_RAW)
        bundle = Bundle.model_validate_json(json.dumps(raw))
    except (DomainError, ValidationError, TypeError, ValueError):
        return _result(scope, account, at, "UNKNOWN", "SOURCE_FORMAT", payload=payload)
    parts = [bundle.identity, bundle.entitlement, bundle.enforcement, bundle.status]
    expected = fingerprint(scope.model_dump())
    if any(
        part.requirements_fingerprint != expected
        or part.account_id != account
        or part.provider != scope.provider
        or part.model != scope.model
        or part.endpoint != scope.endpoint
        for part in parts
    ):
        return _result(scope, account, at, "DENY", "SOURCE_BINDING", payload=payload)
    if any(not part.observed_at <= at < part.expires_at <= scope.expires_at for part in parts):
        return _result(scope, account, at, "DENY", "SOURCE_TIME", payload=payload, bundle=bundle)
    facts = (
        bundle.identity.identity_confirmed,
        bundle.entitlement.legal_free_entitlement,
        bundle.enforcement.enforced_zero_charge,
        bundle.enforcement.billable_fallback_disabled,
    )
    if (
        bundle.status.revoked is True
        or any(value is False for value in facts)
        or bundle.enforcement.paid_cap != 0
    ):
        return _result(
            scope, account, at, "DENY", "SOURCE_REJECTED", payload=payload, bundle=bundle
        )
    if any(value is None for value in facts) or bundle.status.revoked is None:
        return _result(
            scope, account, at, "UNKNOWN", "SOURCE_INCOMPLETE", payload=payload, bundle=bundle
        )
    return _result(
        scope, account, at, "ALLOW", "SYNTHETIC_CONTRACT_VALID", payload=payload, bundle=bundle
    )


def load_offline(store, c, user, contract, key, account_id):
    """Read only this owned fixture, on the original caller's transaction.

    No source/credential/URL/callback/ALLOW input. This returns data, not a send
    permit. Evidence errors are UNKNOWN/DENY; owner/DB errors are not swallowed.
    The sender re-reads at each mutation, wire guard and settlement.
    """
    _require(type(store) is Store and store.test_only and store.sqlite, "LIVE_BLOCKED")
    _require(type(c) is Connection and c.engine is store.engine and c.in_transaction())
    _, scope, _, _, _ = journal._context(store, c, user, contract, key, account_id)
    request = request_for(scope, account_id)
    at = time.time()
    anchors = (
        c.execute(
            select(rows.c.kind, rows.c.request_fingerprint).where(
                rows.c.principal_id == user,
                rows.c.app_id == scope.project_id,
                rows.c.kind.in_([KIND, KIND + "_seal"]),
                rows.c.request_key == scope.trial_key,
            )
        )
        .mappings()
        .all()
    )
    if not anchors:
        return _result(scope, account_id, at, "UNKNOWN", "SOURCE_MISSING")
    if len(anchors) != 2 or {row["kind"] for row in anchors} != {KIND, KIND + "_seal"}:
        return _result(scope, account_id, at, "UNKNOWN", "SOURCE_INTEGRITY")
    if any(row["request_fingerprint"] != fingerprint(request) for row in anchors):
        return _result(scope, account_id, at, "DENY", "SOURCE_BINDING")
    try:
        saved = journal._pair(c, user, scope.project_id, KIND, scope.trial_key)
    except DomainError as error:
        if error.code != "VERSION_CONFLICT":
            raise
        return _result(scope, account_id, at, "UNKNOWN", "SOURCE_INTEGRITY")
    if saved is None or saved["request"] != request:
        return _result(scope, account_id, at, "DENY", "SOURCE_BINDING")
    record = saved["response"]
    if (
        type(record) is not dict
        or set(record) != {"provenance", "raw_b64"}
        or record["provenance"] != "UNINSTALLED_SYNTHETIC_FIXTURE"
        or type(record["raw_b64"]) is not str
        or len(record["raw_b64"]) > 10924
    ):
        return _result(scope, account_id, at, "UNKNOWN", "SOURCE_FORMAT")
    try:
        payload = base64.b64decode(record["raw_b64"], validate=True)
    except ValueError:
        return _result(scope, account_id, at, "UNKNOWN", "SOURCE_FORMAT")
    if (
        not 0 < len(payload) <= MAX_RAW
        or base64.b64encode(payload).decode("ascii") != record["raw_b64"]
    ):
        return _result(scope, account_id, at, "UNKNOWN", "SOURCE_FORMAT")
    return _verify(scope, account_id, at, payload)
