"""Controller-only nonrefundable trial ledger. No transport or LIVE permission.

The installed admission callable is a trusted controller dependency, never API
input. It must validate the complete canonical approval inside the supplied
transaction. A reservation is accounting only: dispatch must admit again.
"""

import hashlib
import math
import time
from typing import Any, Literal, cast

from pydantic import Field
from sqlalchemy import select, update

from .contracts import Strict
from .db import delivery_graph_requests as rows
from .db import fingerprint
from .errors import DomainError

KIND = "natural-trial-budget.v1"
HASH = r"^[a-f0-9]{64}$"
KEY = r"^[A-Za-z0-9_-]{1,100}$"
STAGES = {"generate": 3, "source": 2, "cold": 2}


class Scope(Strict):
    trial_key: str = Field(pattern=KEY)
    approval_key: str = Field(pattern=KEY)
    contract_fingerprint: str = Field(pattern=HASH)
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    principal_id: str = Field(pattern=r"^user_[a-f0-9]{32}$")
    runtime_id: str
    quota_subject: str = Field(min_length=1, max_length=200)
    expires_at: float = Field(gt=0, allow_inf_nan=False)


class Reservation(Strict):
    request_key: str = Field(pattern=KEY)
    stage: Literal["generate", "source", "cold"]
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    expected_version: int = Field(ge=1)
    fence: int = Field(ge=1)
    wire_sha256: str = Field(pattern=HASH)
    wire_bytes: int = Field(ge=1, le=32768)


class Settlement(Strict):
    request_key: str = Field(pattern=KEY)
    response_sha256: str = Field(pattern=HASH)
    response_ascii_bytes: int = Field(ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


def _require(ok, code="VERSION_CONFLICT"):
    if not ok:
        raise DomainError(code, "Frozen trial accounting boundary")


def scope_for(contract, approval_key):
    """Project approved canonical identifiers, never persist raw Goal/material."""
    data = contract.model_dump()
    caps = data["caps"]
    from .natural_live_admission import SQLiteSettlementCaps, TrialCaps
    _require(type(contract.caps) in (TrialCaps, SQLiteSettlementCaps))
    _require(type(contract.caps).model_validate(caps).model_dump() == caps)
    expected = dict(generate_requests=3, source_requests=2, cold_requests=2,
                    max_requests=7, max_output_tokens=1024, max_wire_bytes=32768,
                    max_response_ascii_bytes=32768, per_run_reserved=64000,
                    total_reserved=192000, total_output_tokens=7168,
                    lease_seconds=30, requests_per_minute=1, paid_cap=0)
    _require(all(type(caps.get(k)) is int and caps[k] == v for k, v in expected.items())
             and type(caps.get("run_seconds")) is int and 0 < caps["run_seconds"] <= 300,
             "BUDGET_EXHAUSTED")
    return Scope(**{k: data[k] for k in (
        "trial_key", "project_id", "principal_id", "runtime_id", "quota_subject", "expires_at")},
        approval_key=approval_key, contract_fingerprint=fingerprint(data))


def _load(c, owner, entity, kind, key):
    found = [c.execute(select(rows).where(rows.c.principal_id == owner,
        rows.c.app_id == entity, rows.c.kind == k, rows.c.request_key == key)
        .with_for_update()).mappings().first() for k in (kind, kind + "_seal")]
    if not any(found):
        return None
    _require(all(found))
    left, right = found
    for row in found:
        _require(fingerprint(row["snapshot"]) == row["fingerprint"]
                 and set(row["snapshot"]) == {"request", "response"}
                 and fingerprint(row["snapshot"]["request"]) == row["request_fingerprint"])
    _require(left["snapshot"] == right["snapshot"])
    return left["snapshot"]


def _write(c, owner, entity, kind, key, request, response, *, new=False):
    snapshot = dict(request=request, response=response)
    values = dict(snapshot=snapshot, fingerprint=fingerprint(snapshot),
                  request_fingerprint=fingerprint(request))
    for k in (kind, kind + "_seal"):
        if new:
            c.execute(rows.insert().values(principal_id=owner, app_id=entity,
                      kind=k, request_key=key, **values))
        else:
            changed = c.execute(update(rows).where(rows.c.principal_id == owner,
                rows.c.app_id == entity, rows.c.kind == k,
                rows.c.request_key == key).values(**values))
            _require(changed.rowcount == 1)


def _ledger(c, scope):
    prior = _load(c, scope.principal_id, scope.project_id, KIND, scope.trial_key)
    if prior is None:
        return dict(slots=[], stage_runs={}, halted=False, last_reserved_at=None)
    _require(prior["request"] == scope.model_dump())
    ledger = prior["response"]
    _require(set(ledger) == {"slots", "stage_runs", "halted", "last_reserved_at"}
             and type(ledger["halted"]) is bool and isinstance(ledger["slots"], list)
             and isinstance(ledger["stage_runs"], dict))
    requests = [Reservation.model_validate(x["reservation"]) for x in ledger["slots"]]
    _require(len(requests) <= 7 and len({x.request_key for x in requests}) == len(requests))
    for stage, cap in STAGES.items():
        own = [x for x in requests if x.stage == stage]
        _require(len(own) <= cap and sum(x.wire_bytes + 1024 for x in own) <= 64000
                 and (not own or ledger["stage_runs"].get(stage) == own[0].run_id)
                 and all(x.run_id == own[0].run_id for x in own))
    _require(set(ledger["stage_runs"]) == {x.stage for x in requests}
             and len(set(ledger["stage_runs"].values())) == len(ledger["stage_runs"])
             and sum(x.wire_bytes + 1024 for x in requests) <= 192000)
    for slot in ledger["slots"]:
        _require(set(slot) == {"reservation", "reserved_at", "settlement", "accepted", "settlement_history"}
                 and type(slot["reserved_at"]) is float and math.isfinite(slot["reserved_at"])
                 and type(slot["accepted"]) is bool)
        if slot["settlement"] is not None:
            settled = Settlement.model_validate(slot["settlement"])
            _require(settled.request_key == slot["reservation"]["request_key"])
            history = slot["settlement_history"]
            _require(isinstance(history, list) and 1 <= len(history) <= 2
                     and history[-1] == slot["settlement"])
            for item in history:
                Settlement.model_validate(item)
            if len(history) == 2:
                _require(_recovery(history[0], history[1]) and not slot["accepted"]
                         and ledger["halted"])
            if slot["accepted"]:
                completion, total = settled.completion_tokens, settled.total_tokens
                _require(_known(settled.model_dump()) and completion is not None
                         and total is not None and completion <= 1024
                         and total <= slot["reservation"]["wire_bytes"] + 1024
                         and settled.response_ascii_bytes <= 32768)
        else:
            _require(not slot["accepted"] and slot["settlement_history"] == [])
    _require(ledger["last_reserved_at"] == (
        ledger["slots"][-1]["reserved_at"] if ledger["slots"] else None))
    return ledger


def _context(store, c, user, scope):
    _require(user == scope.principal_id, "PERMISSION_DENIED")
    project = store.lock_project(c, user, scope.project_id)
    _require(project["runtime_id"] == scope.runtime_id, "PERMISSION_DENIED")


def _active(store, c, scope, request, contract, admission):
    _require(scope == scope_for(contract, scope.approval_key), "PERMISSION_DENIED")
    _require(time.time() < scope.expires_at, "PERMISSION_DENIED")
    _require(callable(admission), "PERMISSION_DENIED")
    # Return value is deliberately not treated as permission to send.
    permit = admission(store, c, scope.principal_id, contract, scope.approval_key,
                       request.stage, request.run_id, request.expected_version, request.fence)
    _require(getattr(permit, "scope", None) == "SYNTHETIC_ONLY"
             and store.test_only and store.sqlite
             and getattr(permit, "live_allowed", None) is False
             and getattr(permit, "contract_fingerprint", None) == scope.contract_fingerprint
             and getattr(permit, "stage", None) == request.stage
             and getattr(permit, "run_id", None) == request.run_id
             and getattr(permit, "run_version", None) == request.expected_version
             and getattr(permit, "fence", None) == request.fence
             and type(getattr(permit, "expires_at", None)) in (int, float)
             and math.isfinite(permit.expires_at)
             and time.time() < permit.expires_at <= scope.expires_at,
             "PERMISSION_DENIED")
    run = store.guard(c, request.run_id, request.fence)
    _require(run["principal_id"] == scope.principal_id
             and run["project_id"] == scope.project_id
             and run["runtime_id"] == getattr(permit, "runtime_id", None)
             and (run["runtime_id"] == scope.runtime_id if request.stage == "generate"
                  else isinstance(getattr(permit, "stage_authority_fingerprint", None), str)
                  and len(permit.stage_authority_fingerprint) == 64
                  and all(x in "0123456789abcdef" for x in permit.stage_authority_fingerprint))
             and run["version"] == request.expected_version
             and run["status"] == "RUNNING" and not run["cancel_intent"])
    _require(all(type(run[k]) in (int, float) and math.isfinite(run[k])
                 for k in ("created_at", "lease_until")), "PERMISSION_DENIED")
    deadline = min(scope.expires_at, permit.expires_at, run["lease_until"],
                   run["created_at"] + contract.model_dump()["caps"]["run_seconds"])
    _require(time.time() < deadline, "BUDGET_EXHAUSTED")
    return deadline


def _quota(c, subject):
    """One global DB row serializes the approved account across projects/trials."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    entity = "trialquota_" + hashlib.sha256(subject.encode()).hexdigest()
    request = dict(quota_subject_sha256=hashlib.sha256(subject.encode()).hexdigest())
    insert = sqlite_insert if c.dialect.name == "sqlite" else pg_insert
    for kind in (KIND + ".quota", KIND + ".quota_seal"):
        snapshot = dict(request=request, response=dict(last_reserved_at=None))
        c.execute(insert(rows).values(app_id=entity, principal_id=KIND,
            kind=kind, request_key="quota", request_fingerprint=fingerprint(request),
            snapshot=snapshot, fingerprint=fingerprint(snapshot)).on_conflict_do_nothing())
    value = _load(c, KIND, entity, KIND + ".quota", "quota")
    _require(value["request"] == request
             and set(value["response"]) == {"last_reserved_at"})
    last = value["response"]["last_reserved_at"]
    _require(last is None or type(last) is float and math.isfinite(last))
    return entity, request, last


def reserve(store, user, scope, contract, request, *, admission=None):
    """Deduct exactly once. Duplicate keys return history and never permit resend."""
    scope = Scope.model_validate(scope.model_dump() if isinstance(scope, Scope) else scope)
    request = Reservation.model_validate(request.model_dump() if isinstance(request, Reservation) else request)
    with store.tx() as c:
        return _reserve(store, c, user, scope, contract, request, admission=admission)


def _reserve(store, c, user, scope, contract, request, *, admission=None):
    """Same ledger logic in the caller-owned transaction; no nested connection."""
    _require(c.in_transaction(), "PERMISSION_DENIED")
    _context(store, c, user, scope)
    _require(scope == scope_for(contract, scope.approval_key), "PERMISSION_DENIED")
    ledger = _ledger(c, scope)
    for slot in ledger["slots"]:
        if slot["reservation"]["request_key"] == request.request_key:
            _require(slot["reservation"] == request.model_dump())
            return _public(scope, ledger, duplicate=True)
    original_deadline = _active(store, c, scope, request, contract, admission)
    _require(not ledger["halted"] and all(x["settlement"] is not None
        and x["accepted"] for x in ledger["slots"]), "OUTCOME_UNKNOWN")
    own = [x for x in ledger["slots"] if x["reservation"]["stage"] == request.stage]
    _require(len(own) < STAGES[request.stage]
             and len(ledger["slots"]) < 7
             and sum(x["reservation"]["wire_bytes"] + 1024 for x in own)
                 + request.wire_bytes + 1024 <= 64000
             and sum(x["reservation"]["wire_bytes"] + 1024 for x in ledger["slots"])
                 + request.wire_bytes + 1024 <= 192000, "BUDGET_EXHAUSTED")
    bound = ledger["stage_runs"].get(request.stage)
    _require(bound == request.run_id if bound else request.run_id not in ledger["stage_runs"].values())
    entity, quota_request, last = _quota(c, scope.quota_subject)
    # Account locking can wait past the initially admitted interval. Recheck
    # authority after that wait, without renewing the first permit/Run/lease.
    deadline = min(original_deadline, _active(store, c, scope, request, contract, admission))
    now = time.time()
    _require(now < deadline, "PERMISSION_DENIED")
    _require(last is None or now - last >= 60, "RATE_LIMITED")
    _write(c, KIND, entity, KIND + ".quota", "quota", quota_request,
           dict(last_reserved_at=now))
    ledger["stage_runs"][request.stage] = request.run_id
    ledger["last_reserved_at"] = now
    ledger["slots"].append(dict(reservation=request.model_dump(), reserved_at=now,
                               settlement=None, settlement_history=[], accepted=False))
    _write(c, user, scope.project_id, KIND, scope.trial_key, scope.model_dump(), ledger,
           new=len(ledger["slots"]) == 1)
    # A write-side wait must also roll back the complete accounting transaction.
    _require(time.time() < deadline, "PERMISSION_DENIED")
    return _public(scope, ledger)


def settle(store, user, scope, contract, settlement, *, admission=None):
    """Keep actual usage even after cancellation/expiry; acceptance stays false."""
    scope = Scope.model_validate(scope.model_dump() if isinstance(scope, Scope) else scope)
    settlement = Settlement.model_validate(
        settlement.model_dump() if isinstance(settlement, Settlement) else settlement)
    with store.tx() as c:
        return _settle(store, c, user, scope, contract, settlement, admission=admission)


def _settle(store, c, user, scope, contract, settlement, *, admission=None):
    """Same ledger logic in the caller-owned transaction; no nested connection."""
    _require(c.in_transaction(), "PERMISSION_DENIED")
    _context(store, c, user, scope)
    _require(scope == scope_for(contract, scope.approval_key), "PERMISSION_DENIED")
    ledger = _ledger(c, scope)
    slot = next((x for x in ledger["slots"] if
                 x["reservation"]["request_key"] == settlement.request_key), None)
    _require(slot is not None)
    slot = cast(dict[str, Any], slot)
    if slot["settlement"] is not None:
        if slot["settlement"] == settlement.model_dump():
            return _public(scope, ledger, duplicate=True)
        _require(_recovery(slot["settlement"], settlement.model_dump())
                 and len(slot["settlement_history"]) == 1
                 and not slot["accepted"] and ledger["halted"])
        # Accounting recovery only, never re-admit or re-enable this slot.
        slot["settlement"] = settlement.model_dump()
        slot["settlement_history"].append(settlement.model_dump())
        _write(c, user, scope.project_id, KIND, scope.trial_key, scope.model_dump(), ledger)
        return _public(scope, ledger)
    slot["settlement"] = settlement.model_dump()
    slot["settlement_history"].append(settlement.model_dump())
    known = all(v is not None for v in (settlement.prompt_tokens,
                settlement.completion_tokens, settlement.total_tokens))
    within = (known and settlement.total_tokens == settlement.prompt_tokens
              + settlement.completion_tokens and settlement.completion_tokens <= 1024
              and settlement.total_tokens <= slot["reservation"]["wire_bytes"] + 1024
              and settlement.response_ascii_bytes <= 32768)
    output = sum(x["settlement"]["completion_tokens"] or 0 for x in ledger["slots"]
                 if x["settlement"] is not None)
    active = False
    try:
        _active(store, c, scope, Reservation.model_validate(slot["reservation"]),
                contract, admission)
        active = True
    except DomainError:
        pass
    slot["accepted"] = bool(active and within and output <= 7168 and not ledger["halted"])
    ledger["halted"] = ledger["halted"] or not slot["accepted"]
    _write(c, user, scope.project_id, KIND, scope.trial_key, scope.model_dump(), ledger)
    return _public(scope, ledger)


def read(store, user, scope):
    """Cold original-key history only: no admission, slot, dispatch or refund."""
    scope = Scope.model_validate(scope)
    with store.tx() as c:
        return audit(store, c, user, scope)


def audit(store, c, user, scope):
    """Read the sealed account inside the caller's existing transaction."""
    scope = Scope.model_validate(scope.model_dump() if isinstance(scope, Scope) else scope)
    _context(store, c, user, scope)
    _require(_load(c, user, scope.project_id, KIND, scope.trial_key) is not None)
    return _public(scope, _ledger(c, scope))


def _recovery(old, new):
    fixed = ("request_key", "response_sha256", "response_ascii_bytes")
    usage = ("prompt_tokens", "completion_tokens", "total_tokens")
    return (not _known(old) and _known(new) and all(old[k] == new[k] for k in fixed)
            and any(old[k] is None for k in usage)
            and all(old[k] is None or old[k] == new[k] for k in usage))


def _known(settlement):
    return (settlement is not None and all(settlement[k] is not None for k in
            ("prompt_tokens", "completion_tokens", "total_tokens"))
            and settlement["total_tokens"] == settlement["prompt_tokens"]
                + settlement["completion_tokens"])


def _projection(slots):
    """Read-only finite trial accounting, never a dispatch or pricing permit.

    Every original slot remains held, including failures and unknown outcomes.
    Synthetic usage cannot establish real monetary cost or a currency rate.
    """
    held = sum(slot["reservation"]["wire_bytes"] + 1024 for slot in slots)
    stages = {}
    for stage, limit in STAGES.items():
        own = [slot for slot in slots if slot["reservation"]["stage"] == stage]
        envelope = sum(slot["reservation"]["wire_bytes"] + 1024 for slot in own)
        stages[stage] = dict(request_limit=limit, held_requests=len(own),
            unreserved_request_capacity=limit - len(own), token_envelope_limit=64000,
            held_token_envelope=envelope, unreserved_token_capacity=64000 - envelope,
            run_id=own[0]["reservation"]["run_id"] if own else None)
    known = [slot for slot in slots if _known(slot["settlement"])]
    return dict(contract_kind="EXACT_SEVEN_SLOT_SYNTHETIC_TRIAL", dispatch_authorized=False,
        request_limit=7, held_requests=len(slots), unreserved_request_capacity=7 - len(slots),
        token_envelope_limit=192000, held_token_envelope=held,
        unreserved_token_capacity=192000 - held, output_token_limit=7168,
        unresolved_usage_requests=len(slots) - len(known),
        known_unaccepted_tokens=sum(slot["settlement"]["total_tokens"] for slot in known
            if not slot["accepted"]),
        stages=stages, money=dict(paid_cap=0, actual_paid=None, currency=None,
            status="UNKNOWN", fee_verification="NOT_LIVE_VERIFIED", live_allowed=False))


def _public(scope, ledger, duplicate=False):
    slots = ledger["slots"]
    known = all(_known(x["settlement"]) for x in slots)
    return dict(scope=scope.model_dump(), ledger=ledger, duplicate=duplicate,
        budget_projection=_projection(slots),
        dispatch_authorized=False, live_admission="NOT_VERIFIED",
        reserved_requests=len(slots), reserved_envelope=sum(
            x["reservation"]["wire_bytes"] + 1024 for x in slots),
        usage_status="KNOWN" if known else "UNKNOWN",
        known_total_tokens=sum(x["settlement"]["total_tokens"] or 0 for x in slots
            if x["settlement"] is not None),
        total_tokens=sum(x["settlement"]["total_tokens"] for x in slots) if known else None,
        status="RECONCILING" if not known else "HALTED" if ledger["halted"] else "ACCOUNTED")
