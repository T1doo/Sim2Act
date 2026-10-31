"""Production admission boundary with an exact server source/software target.

The offline harness exercises the existing consent and seven-slot ledger. Its
fixed data sender cannot perform IO. It is not a network dispatch implementation
or evidence that a DB transaction can fence an external provider request.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field
from sqlalchemy import select

from . import natural_live_admission as gate
from . import natural_trial_budget as budget
from . import production_evidence
from .contracts import Strict
from .db import attempts, fingerprint, runs
from .errors import DomainError
from .text_continuations import ANCHOR_HASH

PRODUCTION_QUALIFICATION_HASH = "3f70fce88ec018ab5e258b1dedb8c6e95683e7c6799b17887827551063631a58"


class AccountEvidence(Strict):
    """Server-owned exact account mapping, never an HTTP request field.

    These synthetic records demonstrate required scope/freshness checks. They
    confer no legal entitlement or production zero-charge authority.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    scope: Literal["SYNTHETIC_ONLY"] = "SYNTHETIC_ONLY"
    principal_id: str
    project_id: str
    trial_key: str
    contract_fingerprint: str = Field(pattern=gate.HASH)
    provider: Literal["intern-ai"] = "intern-ai"
    account_id: str = Field(min_length=1, max_length=200)
    quota_subject: str = Field(min_length=1, max_length=200)
    evidence_sha256: str = Field(pattern=gate.HASH)
    checked_at: float = Field(gt=0, allow_inf_nan=False)
    expires_at: float = Field(gt=0, allow_inf_nan=False)
    legal_free_entitlement: bool
    enforced_non_chargeable: bool
    revoked: bool = False
    paid_cap: Literal[0] = 0


@dataclass(frozen=True)
class OfflineSender:
    """Canned synthetic bytes only; deliberately has no callback/transport."""

    response: bytes = b'{"synthetic":true}'
    prompt_tokens: int | None = 1
    completion_tokens: int | None = 1
    total_tokens: int | None = 2
    outcome_unknown: bool = False

    def __post_init__(self):
        if (type(self.response) is not bytes or type(self.outcome_unknown) is not bool
                or any(v is not None and (type(v) is not int or v < 0) for v in
                       (self.prompt_tokens, self.completion_tokens, self.total_tokens))):
            raise DomainError("LIVE_BLOCKED", "Offline sender must contain fixed typed data only")


@dataclass(frozen=True)
class OfflineRegistry:
    """Explicit fixture installation, confined to test-only SQLite."""

    accounts: tuple[AccountEvidence, ...]
    sender: OfflineSender


def blocked():
    raise DomainError("LIVE_BLOCKED", "No reviewed production account resolver and sender registered")


def canonical_quota_subject(account_id):
    """Stable server opaque account ID; production identity resolver absent."""
    gate.require(type(account_id) is str and 0 < len(account_id) <= 200)
    return "intern-ai-account-" + hashlib.sha256(account_id.encode()).hexdigest()


def _qualified():
    """Exact reviewed production target; historical compatibility stays separate."""
    root = Path(__file__).parent
    try:
        gate.require(hashlib.sha256((root / "text_software_anchors.json").read_bytes()).hexdigest()
                     == ANCHOR_HASH, "Software anchors changed")
        raw = (root / "production_software_qualification.json").read_bytes()
        gate.require(hashlib.sha256(raw).hexdigest() == PRODUCTION_QUALIFICATION_HASH,
                     "Production software manifest changed")
        proof = json.loads(raw)
        gate.require(set(proof) == {"version", "baseline", "files"}
            and proof["version"] == "production-software-qualification.v1"
            and proof["baseline"] == "206153da27edb5353e7106ab52b6e5bcaad86627")
        current = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (*root.glob("*.py"), *root.glob("*.c"), *root.glob("*.h")) if p.name != "config.py"}
        current["_owned_sql_catalog.json"] = hashlib.sha256((root / "_owned_sql_catalog.json").read_bytes()).hexdigest()
        source = Path(__file__).read_bytes()
        literal = ('PRODUCTION_QUALIFICATION_HASH = "' + PRODUCTION_QUALIFICATION_HASH + '"').encode()
        gate.require(source.count(literal) == 1, "Exact production manifest pin required")
        current[Path(__file__).name] = hashlib.sha256(source.replace(literal,
            ('PRODUCTION_QUALIFICATION_HASH = "' + '0' * 64 + '"').encode())).hexdigest()
        gate.require(proof["files"] == current,
                     "Current production software differs from the reviewed target")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise DomainError("VERSION_CONFLICT", "Unavailable exact production software qualification") from exc


def production_preflight(store, user, contract, approval_key, request):
    """Production default: no callback, credentials, network, Run creation or budget mutation.

    There is deliberately no resolver/authority/sender override parameter. A
    future live implementation requires separate review and registration.
    """
    with store.tx() as c:
        # Authorize exact identity/contract before reporting unavailable LIVE.
        gate._approved(store, c, user, contract, approval_key)
        from . import production_trial_policy as policy
        supplied = production_evidence.resolve_account(user, contract, approval_key)
        policy.check_source(production_evidence.requirements_for(user, contract, approval_key),
                            supplied, now=time.time())
        _qualified()
        worker_id = c.execute(select(runs.c.worker_id).where(runs.c.id == request.run_id)).scalar()
        context = policy.check_run(store, c, user, contract, approval_key, request.stage,
            request.run_id, request.expected_version, request.fence, worker_id)
        # A preflight observation is not a reusable dispatch permit. The bound
        # controller repeats source/current Run checks at claim/send/commit.
        return dict(status="SPEC_PRODUCTION_PREFLIGHT_CHECKED", context=context.model_dump(),
                    live_allowed=False, dispatch_authorized=False)


def _resolve(store, user, contract, registry):
    # Reject subclasses and arbitrary objects before attribute/callback access.
    if (not store.test_only or not store.sqlite or type(registry) is not OfflineRegistry
            or type(registry.sender) is not OfflineSender
            or type(registry.accounts) is not tuple
            or any(type(a) is not AccountEvidence for a in registry.accounts)):
        blocked()
    # One account owns one global quota subject across all projects/trials;
    # aliases cannot split the shared RPM bucket or share another account's.
    by_account: dict[tuple[str, str], str] = {}
    by_subject: dict[str, tuple[str, str]] = {}
    for record in registry.accounts:
        if (by_account.setdefault((record.provider, record.account_id), record.quota_subject)
                != record.quota_subject
                or by_subject.setdefault(record.quota_subject, (record.provider, record.account_id))
                != (record.provider, record.account_id)):
            blocked()
    accounts = [a for a in registry.accounts if a.principal_id == user
                and a.project_id == contract.project_id and a.trial_key == contract.trial_key
                and a.contract_fingerprint == fingerprint(contract.model_dump())]
    if len(accounts) != 1:
        blocked()
    account = accounts[0]
    now = time.time()
    if (account.provider != "intern-ai"
            or account.quota_subject != canonical_quota_subject(account.account_id)
            or account.quota_subject != contract.quota_subject or account.revoked
            or not account.legal_free_entitlement or not account.enforced_non_chargeable
            or not account.checked_at <= now < account.expires_at <= contract.expires_at
            or now - account.checked_at > 30):
        blocked()
    _qualified()
    return account


def _source_usage(attempt, slot, proof):
    usage = attempt["usage"]
    settlement = slot["settlement"]
    gate.require(isinstance(usage, dict) and usage.get("status") == "known"
                 and isinstance(usage.get("tokens"), dict)
                 and isinstance(settlement, dict), "Source usage evidence is incomplete")
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    gate.require(all(type(usage["tokens"].get(k)) is int
                     and usage["tokens"][k] == settlement.get(k) == getattr(proof.usage, k)
                     for k in keys), "Source usage evidence changed")


def _source(store, c, user, contract, approval_key, stage, account, source_contract, resolver):
    if stage != "cold" or not isinstance(contract, gate.PBTrialContract):
        gate.require(source_contract is None and resolver is None)
        return
    from . import pa_spec_apps as spec
    from .pb_live_source_contract import LivePBSourceContract, resolve_source
    from .text_workflows import RunScopeInput

    gate.require(type(source_contract) is LivePBSourceContract
                 and source_contract.trial.model_dump() == contract.model_dump()
                 and source_contract.approval_key == approval_key)
    receipt = resolve_source(source_contract, resolver)
    gate.require(receipt.trial_fingerprint == fingerprint(contract.model_dump())
                 and receipt.account_id == account.account_id
                 and receipt.quota_subject == account.quota_subject
                 and receipt.provider == account.provider
                 and receipt.evidence_scope == "SYNTHETIC"
                 and receipt.verification == "NOT_LIVE_VERIFIED"
                 and receipt.live_allowed is False)
    # An extra typed receipt must be joined to the original approved DB ledger,
    # never merely to another internally consistent two-attempt archive.
    ledger = budget.audit(store, c, user, budget.scope_for(contract, approval_key))["ledger"]
    source_id = ledger["stage_runs"].get("source")
    slots = [s for s in ledger["slots"] if s["reservation"]["stage"] == "source"]
    actual = c.execute(select(attempts).where(attempts.c.run_id == source_id)).mappings().all()
    gate.require(not ledger["halted"] and source_id is not None
                 and source_id == receipt.source_run_id == source_contract.source_run_id
                 and len(actual) == len(slots) == 2
                 and set(source_contract.source_attempt_ids) == {a["id"] for a in actual}
                 == {s["reservation"]["request_key"] for s in slots})
    source_scope = gate._saved(c, user, source_id, spec.RUN_META, "accepted", RunScopeInput)
    gate.require(source_scope.app_id == source_contract.source_app_id)
    evidence = resolver.evidence  # resolve_source already required the exact fixture type.
    for proof in evidence.attempts:
        slot = next(s for s in slots if s["reservation"]["request_key"] == proof.attempt_id)
        attempt = next(a for a in actual if a["id"] == proof.attempt_id)
        gate.require(slot["accepted"] is True and slot["settlement"] is not None
                     and slot["reservation"]["wire_sha256"] == proof.wire_sha256
                     and slot["settlement"]["response_sha256"] == proof.response_sha256)
        parameters, response = attempt["parameters"], attempt["response"]
        gate.require(attempt["mode"] == "LIVE" and attempt["status"] == "VERIFIED"
                     and attempt["request_model"] == attempt["response_model"] == contract.model
                     and isinstance(parameters, dict) and isinstance(response, dict),
                     "Actual source Attempt is not verified LIVE provenance")
        wire, raw = parameters.get("natural_spec_wire"), response.get("raw_evidence")
        received = response.get("received_raw")
        gate.require(isinstance(wire, dict) and isinstance(raw, dict)
                     and type(received) is str and received.isascii()
                     and received.encode("ascii") == proof.raw_response
                     and wire.get("sha256") == proof.wire_sha256
                     and wire.get("bytes") == len(proof.wire)
                     and raw.get("status") == "COMPLETE"
                     and raw.get("sha256") == proof.response_sha256
                     and raw.get("bytes") == len(proof.raw_response)
                     and parameters.get("provider") == proof.provider
                     and parameters.get("account_id") == proof.account_id
                     and parameters.get("provider_request_id") == proof.provider_request_id,
                     "Actual provider/account/wire/raw archive pairing changed")
        _source_usage(attempt, slot, proof)


def _account_admit(store, c, user, contract, approval_key, stage, run_id, version, fence,
                   registry, worker_id):
    """Original shared account, complete trial admission and current Worker owner."""
    account = _resolve(store, user, contract, registry)
    permit = gate.admit(store, c, user, contract, approval_key, stage, run_id, version, fence,
        gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject))
    owner = c.execute(select(runs.c.worker_id).where(runs.c.id == run_id)).scalar()
    gate.require(type(worker_id) is str and bool(worker_id) and owner == worker_id,
                 "Worker owner changed")
    return account, permit


def _admission(registry, worker_id, source_contract, resolver):
    def admit(store, c, user, contract, approval_key, stage, run_id, version, fence):
        account, permit = _account_admit(store, c, user, contract, approval_key, stage,
            run_id, version, fence, registry, worker_id)
        _source(store, c, user, contract, approval_key, stage, account, source_contract, resolver)
        return permit
    return admit

def recover(store, user, contract, approval_key):
    """Original sealed accounting only, including unknown/late results; no send."""
    return budget.read(store, user, budget.scope_for(contract, approval_key).model_dump())


def dispatch_offline(store, user, contract, approval_key, request, wire, *, registry, worker_id,
                     pb_source_contract=None, pb_source_resolver=None):
    """Fixture dispatch exactly once; reserve, recheck, canned result, settle.

    A committed reservation is the no-resend marker even if the process stops
    before the canned response. Recover by original key; never refund UNKNOWN.
    Missing prerequisites fail before reserve. Revocation after reserve retains
    the spent slot. No claim about atomicity with real external IO is made.
    """
    request = budget.Reservation.model_validate(request)
    gate.require(type(wire) is bytes and 0 < len(wire) <= 32768
                 and len(wire) == request.wire_bytes
                 and hashlib.sha256(wire).hexdigest() == request.wire_sha256)
    scope = budget.scope_for(contract, approval_key)
    # Duplicate original key is read-only, even after revocation/cold recovery.
    with store.tx() as c:
        budget._context(store, c, user, scope)
        ledger = budget._ledger(c, scope)
        for slot in ledger["slots"]:
            if slot["reservation"]["request_key"] == request.request_key:
                gate.require(slot["reservation"] == request.model_dump())
                return budget._public(scope, ledger, duplicate=True)
    account = _resolve(store, user, contract, registry)
    admission = _admission(registry, worker_id, pb_source_contract, pb_source_resolver)
    reserved = budget.reserve(store, user, scope, contract, request, admission=admission)
    if reserved["duplicate"]:
        return reserved
    with store.tx() as c:
        # Fresh single boundary immediately before the fixed offline sender.
        budget._active(store, c, scope, request, contract, admission)
        owner = c.execute(select(runs.c.worker_id).where(runs.c.id == request.run_id)).scalar()
        gate.require(owner == worker_id, "Worker owner changed")
    sender = registry.sender
    response = b"" if sender.outcome_unknown else sender.response
    # Invalid/unknown responses consume the original slot and halt acceptance.
    settlement = budget.Settlement(request_key=request.request_key,
        response_sha256=hashlib.sha256(response).hexdigest(), response_ascii_bytes=len(response),
        prompt_tokens=None if sender.outcome_unknown else sender.prompt_tokens,
        completion_tokens=None if sender.outcome_unknown else sender.completion_tokens,
        total_tokens=None if sender.outcome_unknown else sender.total_tokens)
    settled = budget.settle(store, user, scope, contract, settlement, admission=admission)
    return dict(settled, scope_kind="SYNTHETIC_ONLY", live_allowed=False,
                network_requests=0, account_evidence_sha256=account.evidence_sha256)
