"""Exact P-A send permission; immutable scoped seals and nonrefundable attempts.

This namespace neither borrows the fixed CSV activation nor supplies a candidate.
Defaults grant zero requests. An explicitly approved one-goal/key scope can use
the existing Intern byte sender. Historical proof never needs live settings.
"""

import copy
import math
import time
from typing import Literal

from pydantic import Field
from sqlalchemy import select, update

from .contracts import ApplicationGenerationActivation, GoalCardRunSource, Limits, Strict
from .csv_logic_reuse import implementation
from .db import (
    attempts,
    delivery_graph_requests,
    events,
    fingerprint,
    grants,
    quotas,
    reservations,
)
from .delivery_graph_apps import controlled, lookup, remember
from .errors import DomainError
from .goals import validate_card_version
from .model import InternModel
from .text_logic_reuse import pair
from .tools import authorized_read

VERSION = "pa-intern-generation-approval.v1"
META, SCOPE, APPROVE, REVOKE, CHARGE, SEND, SETTLE = ("ga_provider_" + n for n in
    ("metadata", "scope", "approve", "revoke", "charge", "send", "settle"))
CONSENT = "APPROVE_ONLY_THIS_EXACT_P_A_GOAL_MATERIAL_AND_REQUEST_BUDGET"
WIRE_CAP = 32768
CAPS = dict(max_requests=3, max_tools=1, max_repairs=1, max_total_tokens=64000,
            max_output_tokens=1024, run_seconds=300)


def now():
    return time.time()


def require(ok, message="Exact P-A provider approval changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


class PrepareInput(Strict):
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_version: int = Field(strict=True, ge=1)
    expected_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    generation_request_key: str = Field(min_length=1, max_length=100)
    request_key: str = Field(min_length=1, max_length=100)


class Metadata(Strict):
    approval_id: str
    principal_id: str
    project_id: str
    runtime_id: str
    resource_id: str


class Scope(Strict):
    version: Literal["pa-intern-generation-approval.v1"]
    metadata: Metadata
    request: PrepareInput
    source: GoalCardRunSource
    mode: Literal["OFFLINE_TEST", "LIVE"]
    model: Literal["intern-s2"]
    endpoint: Literal["https://chat.intern-ai.org.cn/api/v1/chat/completions"]
    quota_subject: str = Field(min_length=1, max_length=200)
    limits: Limits
    wire_bytes: Literal[32768]
    rpm: Literal[1]
    grant_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    software_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class ApproveInput(Strict):
    expected_scope_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    consent: Literal["APPROVE_ONLY_THIS_EXACT_P_A_GOAL_MATERIAL_AND_REQUEST_BUDGET"]
    budget_note: str = Field(min_length=1, max_length=500)
    request_key: str = Field(min_length=1, max_length=100)


class Approval(Strict):
    approval_id: str
    scope_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    approved_at: float = Field(strict=True)
    deadline: float = Field(strict=True)
    request: ApproveInput


class RevokeInput(Strict):
    expected_scope_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)


class Charge(Strict):
    approval_id: str
    run_id: str
    attempt_id: str
    index: int = Field(strict=True, ge=0, le=2)
    fence: int = Field(strict=True, ge=1)
    envelope: int = Field(strict=True, ge=1, le=33792)
    wire_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    mode: Literal["MOCK", "LIVE"]
    max_tokens: int = Field(strict=True, ge=1, le=1024)


class Sending(Strict):
    charge_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    sent_at: float = Field(strict=True)


class Settlement(Strict):
    charge_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["RECEIVED", "FAILED"]
    usage: dict
    error: str | None


def _save(c, user, aid, kind, key, body):
    for name in (kind, kind + "_seal"):
        remember(c, user, aid, name, key, body, body.model_dump())


def _get(c, user, aid, kind, key, model):
    body, result = pair(c, user, aid, kind, key, model)
    require(fingerprint(body.model_dump()) == fingerprint(result))
    return body


def _keys(c, user, aid, kind):
    rows = c.execute(select(delivery_graph_requests.c.kind, delivery_graph_requests.c.request_key)
        .where(delivery_graph_requests.c.app_id == aid, delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.kind.in_([kind, kind + "_seal"]))).mappings().all()
    left = {r["request_key"] for r in rows if r["kind"] == kind}
    right = {r["request_key"] for r in rows if r["kind"] == kind + "_seal"}
    require(left == right, "Missing P-A approval/charge seal")
    return left


def _meta(store, c, user, aid, *, content=False):
    meta = _get(c, user, aid, META, "scope", Metadata)
    require(meta.approval_id == aid and meta.principal_id == user)
    store.own_project(c, user, meta.project_id)
    if content:
        store.authorize(c, user, meta.runtime_id, meta.project_id, meta.resource_id, "resource.read")
    return meta


def _grant(c, meta):
    return fingerprint([dict(r) for r in c.execute(select(grants).where(
        grants.c.project_id == meta.project_id, grants.c.principal_id.in_([meta.principal_id, meta.runtime_id]))
        .order_by(grants.c.id)).mappings()])


def _current_source(store, c, user, scope):
    meta = scope.metadata
    material = authorized_read(store, c, user, meta.runtime_id, meta.project_id,
        "resource.read", {"resource_id": meta.resource_id})
    require(material["format"] in {"txt", "md"} and len(material["content"].encode()) <= 4096
        and len(material["content"].splitlines()) <= 64, "Only finite TXT/MD literal reports are supported")
    saved = validate_card_version(store, c, user, scope.source.card_id, scope.source.version)
    from .db import goal_cards
    head = c.execute(select(goal_cards).where(goal_cards.c.id == scope.source.card_id)).mappings().first()
    require(head is not None and head["project_id"] == meta.project_id
        and head["version"] == scope.source.version and head["fingerprint"] == scope.source.fingerprint
        and fingerprint(saved["snapshot"]) == fingerprint(scope.source.snapshot) == scope.source.fingerprint
        and saved["snapshot"]["content"]["resource_refs"] == [meta.resource_id]
        and saved["snapshot"]["resource_snapshots"] == [{"resource_id": meta.resource_id,
            "hash": material["hash"], "format": material["format"]}]
        and _grant(c, meta) == scope.grant_fingerprint,
        "Current Goal, material or authorization differs from exact approval")


def _enabled(settings):
    if settings.application_generation_activation_enabled is not True:
        raise DomainError("RESOURCE_UNAVAILABLE", "P-A generation approval mechanism is disabled")


@controlled
def prepare(store, user, pid, body, settings):
    _enabled(settings)
    with store.tx() as c:
        project = store.lock_project(c, user, pid)
        from .db import goal_cards

        location = c.execute(select(goal_cards.c.project_id).where(goal_cards.c.id == body.card_id)).scalar()
        if location != pid:
            raise DomainError("PERMISSION_DENIED")
        saved = validate_card_version(store, c, user, body.card_id, body.expected_version)
        require(saved["fingerprint"] == body.expected_fingerprint)
        refs = saved["snapshot"]["content"]["resource_refs"]
        require(len(refs) == 1, "Exactly one authorized TXT/MD material is required")
        aid = "gaapproval_" + fingerprint({"user": user, "project": pid, "key": body.request_key})[:32]
        meta = Metadata(approval_id=aid, principal_id=user, project_id=pid,
            runtime_id=project["runtime_id"], resource_id=refs[0])
        limits = Limits(**{k: min(getattr(settings, k), cap) for k, cap in CAPS.items()})
        require(limits.max_requests >= 2 and settings.model == "intern-s2"
            and settings.goal_planner_provider == "intern-s2")
        scope = Scope(version=VERSION, metadata=meta, request=body,
            source=GoalCardRunSource(card_id=body.card_id, version=body.expected_version,
                fingerprint=body.expected_fingerprint, snapshot=saved["snapshot"]),
            mode="OFFLINE_TEST" if store.test_only else "LIVE", model="intern-s2",
            endpoint=InternModel.ENDPOINT, quota_subject=settings.quota_subject,
            limits=limits, wire_bytes=WIRE_CAP, rpm=1, grant_fingerprint=_grant(c, meta),
            software_fingerprint=implementation())
        _current_source(store, c, user, scope)
        if any(lookup(c, user, aid, k, "scope") for k in (META, META + "_seal", SCOPE, SCOPE + "_seal")):
            _meta(store, c, user, aid, content=True)
            old = _get(c, user, aid, SCOPE, "scope", Scope)
            require(fingerprint(old.model_dump()) == fingerprint(scope.model_dump()))
        else:
            _save(c, user, aid, META, "scope", meta)
            _save(c, user, aid, SCOPE, "scope", scope)
        return {"approval_id": aid, "scope_fingerprint": fingerprint(scope.model_dump()),
            "scope": scope.model_dump(), "status": "PREPARED", "actual_model_requests": 0,
            "formal_publication_enabled": False, "monetary_spending_cap": "NOT_ESTABLISHED"}


@controlled
def approve(store, user, aid, body, settings):
    _enabled(settings)
    with store.tx() as c:
        meta = _meta(store, c, user, aid)
        store.lock_project(c, user, meta.project_id)
        store.authorize(c, user, meta.runtime_id, meta.project_id, meta.resource_id, "resource.read")
        scope = _get(c, user, aid, SCOPE, "scope", Scope)
        require(body.expected_scope_fingerprint == fingerprint(scope.model_dump()) and body.budget_note.strip())
        _current_source(store, c, user, scope)
        require(scope.software_fingerprint == implementation())
        require(not _keys(c, user, aid, REVOKE), "Approval has been irreversibly revoked")
        if _keys(c, user, aid, APPROVE):
            require(_keys(c, user, aid, APPROVE) == {"approve"})
            accepted = _get(c, user, aid, APPROVE, "approve", Approval)
            require(fingerprint(accepted.request.model_dump()) == fingerprint(body.model_dump()))
        else:
            at = now()
            require(math.isfinite(at))
            accepted = Approval(approval_id=aid, scope_fingerprint=fingerprint(scope.model_dump()),
                approved_at=at, deadline=at + scope.limits.run_seconds, request=body)
            _save(c, user, aid, APPROVE, "approve", accepted)
        return {"activation": ApplicationGenerationActivation(approval_id=aid,
            scope_fingerprint=accepted.scope_fingerprint,
            approval_fingerprint=fingerprint(accepted.model_dump())).model_dump(),
            "deadline": accepted.deadline, "scope": scope.model_dump(),
            "formal_publication_enabled": False, "actual_model_requests": 0}


@controlled
def revoke(store, user, aid, body):
    with store.tx() as c:
        meta = _meta(store, c, user, aid)
        store.lock_project(c, user, meta.project_id)
        # Metadata/hash projections only: stop does not recover protected Goal/material content.
        projections = c.execute(select(delivery_graph_requests.c.kind,
            delivery_graph_requests.c.fingerprint, delivery_graph_requests.c.request_fingerprint)
            .where(delivery_graph_requests.c.app_id == aid, delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind.in_([SCOPE, SCOPE + "_seal"]),
                delivery_graph_requests.c.request_key == "scope")).mappings().all()
        require(len(projections) == 2 and projections[0]["fingerprint"] == projections[1]["fingerprint"])
        require(body.reason.strip())
        approved = _get(c, user, aid, APPROVE, "approve", Approval)
        require(body.expected_scope_fingerprint == approved.scope_fingerprint
            and all(r["request_fingerprint"] == approved.scope_fingerprint for r in projections))
        if _keys(c, user, aid, REVOKE):
            old = _get(c, user, aid, REVOKE, "revoke", RevokeInput)
            require(fingerprint(old.model_dump()) == fingerprint(body.model_dump()))
        else:
            _save(c, user, aid, REVOKE, "revoke", body)
        return {"approval_id": aid, "status": "REVOKED", "actual_model_requests": 0}


def _attempt(c, aid):
    return c.execute(select(attempts.c.id, attempts.c.run_id, attempts.c.status,
        attempts.c.mode, attempts.c.request_model, attempts.c.reserved_tokens, attempts.c.usage,
        attempts.c.error,
        *[attempts.c.parameters[k].label(k) for k in
          ("generation_activation", "generation_wire", "generation_fence", "generation_index",
           "request_fingerprint", "max_tokens")]).where(attempts.c.id == aid)).mappings().first()


@controlled
def audit(store, c, user, aid, transition=None):
    _meta(store, c, user, aid)
    keys = _keys(c, user, aid, CHARGE)
    sent, settled = _keys(c, user, aid, SEND), _keys(c, user, aid, SETTLE)
    require(sent <= keys and settled <= keys and len(keys) <= 3)
    charges = sorted([_get(c, user, aid, CHARGE, key, Charge) for key in keys], key=lambda v: v.index)
    require([r.index for r in charges] == list(range(len(charges)))
        and len({r.run_id for r in charges}) <= 1)
    anchored = c.execute(select(events.c.data).where(events.c.run_id == aid,
        events.c.kind == "GA_PROVIDER_RESERVED")).scalars().all()
    require(fingerprint(sorted(anchored, key=lambda r: r["index"]))
        == fingerprint([r.model_dump() for r in charges]), "Independent provider charge history differs")
    marked = set(c.execute(select(attempts.c.id).where(
        attempts.c.parameters["generation_activation"]["approval_id"].as_string() == aid)).scalars())
    require(marked == keys, "Actual Attempt and provider charge sets differ")
    for charge in charges:
        actual = _attempt(c, charge.attempt_id)
        require(actual is not None and actual["run_id"] == charge.run_id
            and actual["mode"] == charge.mode and actual["request_model"] == "intern-s2"
            and actual["reserved_tokens"] == charge.envelope
            and actual["generation_activation"] == {"approval_id": aid,
                "charge_fingerprint": fingerprint(charge.model_dump())}
            and actual["generation_wire"] == charge.wire_fingerprint
            and actual["request_fingerprint"] == charge.request_fingerprint
            and actual["generation_fence"] == charge.fence
            and actual["generation_index"] == charge.index and actual["max_tokens"] == charge.max_tokens)
        if charge.attempt_id in sent:
            marker = _get(c, user, aid, SEND, charge.attempt_id, Sending)
            require(marker.charge_fingerprint == fingerprint(charge.model_dump()) and math.isfinite(marker.sent_at))
        if charge.attempt_id in settled:
            result = _get(c, user, aid, SETTLE, charge.attempt_id, Settlement)
            require(result.charge_fingerprint == fingerprint(charge.model_dump())
                and result.status == actual["status"] and fingerprint(result.usage) == fingerprint(actual["usage"])
                and result.error == actual["error"])
        elif charge.attempt_id != transition:
            require(actual["status"] == "STARTED", "Missing provider settlement proof")
    return charges, sent, settled


@controlled
def validate_run(store, c, run, settings=None, *, active=False, transition=None):
    contract = store.frozen_contract(c, run)
    selected = contract.application_generation
    require(selected is not None and selected.activation is not None)
    b = selected.activation
    meta = _meta(store, c, run["principal_id"], b.approval_id, content=True)
    scope = _get(c, run["principal_id"], b.approval_id, SCOPE, "scope", Scope)
    approval = _get(c, run["principal_id"], b.approval_id, APPROVE, "approve", Approval)
    require(fingerprint(scope.model_dump()) == b.scope_fingerprint == approval.scope_fingerprint
        and fingerprint(approval.model_dump()) == b.approval_fingerprint
        and scope.metadata == meta and scope.software_fingerprint == implementation()
        and meta.project_id == run["project_id"] and meta.runtime_id == run["runtime_id"]
        and run["request_key"] == scope.request.generation_request_key
        and fingerprint(contract.source_goal_card.model_dump()) == fingerprint(scope.source.model_dump())
        and contract.mode == ("mock" if scope.mode == "OFFLINE_TEST" else "live")
        and contract.request_model == scope.model and selected.provider == scope.model
        and selected.response_archive_policy == "protected-json32768.v1"
        and selected.live_request_allowance == 0
        and all(v <= scope.limits.model_dump()[k] for k, v in contract.limits.model_dump().items())
        and math.isfinite(approval.approved_at) and math.isfinite(approval.deadline)
        and approval.deadline == approval.approved_at + scope.limits.run_seconds)
    require(_keys(c, run["principal_id"], b.approval_id, META) == {"scope"}
        and _keys(c, run["principal_id"], b.approval_id, SCOPE) == {"scope"}
        and _keys(c, run["principal_id"], b.approval_id, APPROVE) == {"approve"}
        and _keys(c, run["principal_id"], b.approval_id, REVOKE) <= {"revoke"})
    charges, sent, settled = audit(store, c, run["principal_id"], b.approval_id, transition)
    require(all(r.run_id == run["id"] for r in charges))
    require(sum(r.envelope for r in charges) <= scope.limits.max_total_tokens)
    for key in sent:
        marker = _get(c, run["principal_id"], b.approval_id, SEND, key, Sending)
        require(approval.approved_at <= marker.sent_at < approval.deadline,
            "Provider send lies outside original finite approval time")
    if active:
        _enabled(settings)
        require(not _keys(c, run["principal_id"], b.approval_id, REVOKE), "P-A generation approval revoked")
        at = now()
        require(math.isfinite(at) and approval.approved_at <= at < min(approval.deadline,
            approval.approved_at + settings.run_seconds), "P-A generation approval expired")
        require(settings.goal_planner_provider == scope.model and settings.model == scope.model
            and settings.quota_subject == scope.quota_subject)
        _current_source(store, c, run["principal_id"], scope)
    return scope, approval, charges, sent, settled


@controlled
def submission(store, user, pid, cid, body, settings):
    _enabled(settings)
    with store.tx() as c:
        b = body.activation
        meta = _meta(store, c, user, b.approval_id)
        if meta.project_id != pid:
            raise DomainError("PERMISSION_DENIED")
        store.lock_project(c, user, pid)
        store.authorize(c, user, meta.runtime_id, meta.project_id, meta.resource_id, "resource.read")
        scope = _get(c, user, b.approval_id, SCOPE, "scope", Scope)
        approval = _get(c, user, b.approval_id, APPROVE, "approve", Approval)
        require(meta.project_id == pid and scope.request.card_id == cid
            and body.expected_version == scope.source.version and body.expected_fingerprint == scope.source.fingerprint
            and body.request_key == scope.request.generation_request_key
            and fingerprint(scope.model_dump()) == b.scope_fingerprint == approval.scope_fingerprint
            and fingerprint(approval.model_dump()) == b.approval_fingerprint
            and scope.software_fingerprint == implementation()
            and not _keys(c, user, b.approval_id, REVOKE)
            and approval.approved_at <= now() < approval.deadline)
        _current_source(store, c, user, scope)
        return scope


@controlled
def reserve_slot(worker, c, run, aid, envelope, wire_fp):
    scope, _, prior, _, settled = validate_run(worker.store, c, run, worker.s, active=True)
    require(len(prior) == run["context"]["requests"] and len(prior) < scope.limits.max_requests)
    if len(settled) != len(prior):
        raise DomainError("OUTCOME_UNKNOWN", "Original provider send is not settled; never resend")
    for r in prior:
        result = _get(c, run["principal_id"], scope.metadata.approval_id, SETTLE, r.attempt_id, Settlement)
        repair = r.index == 1 and result.error in {"INVALID_MANIFEST", "INVALID_INPUT"}
        if result.status != "RECEIVED" or (result.error and not repair) or result.usage.get("status") != "known":
            raise DomainError("OUTCOME_UNKNOWN", "Failed or unknown provider evidence halts further sends")
    actual = _attempt(c, aid)
    require(actual is not None and actual["status"] == "STARTED")
    if envelope > WIRE_CAP + actual["max_tokens"] or sum(r.envelope for r in prior) + envelope > scope.limits.max_total_tokens:
        raise DomainError("BUDGET_EXHAUSTED")
    charge = Charge(approval_id=scope.metadata.approval_id, run_id=run["id"], attempt_id=aid,
        index=len(prior), fence=run["fence"], envelope=envelope, wire_fingerprint=wire_fp,
        request_fingerprint=actual["request_fingerprint"], mode=actual["mode"], max_tokens=actual["max_tokens"])
    _save(c, run["principal_id"], charge.approval_id, CHARGE, aid, charge)
    params = c.execute(select(attempts.c.parameters).where(attempts.c.id == aid)).scalar_one()
    c.execute(update(attempts).where(attempts.c.id == aid).values(parameters={**params,
        "generation_activation": {"approval_id": charge.approval_id, "charge_fingerprint": fingerprint(charge.model_dump())}}))
    worker.store.event(c, charge.approval_id, "GA_PROVIDER_RESERVED", charge.model_dump())


@controlled
def mark_sending(worker, c, run, aid):
    scope, approval, charges, sent, settled = validate_run(worker.store, c, run, worker.s, active=True)
    require(charges and charges[-1].attempt_id == aid and aid not in sent and aid not in settled)
    require(all(r.attempt_id in settled for r in charges[:-1]))
    subject, at = scope.quota_subject, now()
    quota = c.execute(select(quotas).where(quotas.c.subject == subject).with_for_update()).mappings().first()
    own = c.execute(select(reservations).where(reservations.c.id == aid,
        reservations.c.subject == subject, reservations.c.run_id == run["id"])).mappings().first()
    other = c.execute(select(reservations.c.id).where(reservations.c.subject == subject,
        reservations.c.id != aid, reservations.c.created_at > at - 60)).first()
    pending = c.execute(select(attempts.c.id).join(reservations, attempts.c.id == reservations.c.id)
        .where(reservations.c.subject == subject, attempts.c.id != aid, attempts.c.status == "STARTED")).first()
    require(quota is not None and own is not None)
    if quota["blocked_until"] > at or other or pending:
        raise DomainError("RATE_LIMITED", "P-A approval uses the existing account at most once per minute")
    c.execute(update(reservations).where(reservations.c.id == aid).values(created_at=at))
    c.execute(update(quotas).where(quotas.c.subject == subject).values(blocked_until=at + 60))
    _save(c, run["principal_id"], scope.metadata.approval_id, SEND, aid,
        Sending(charge_fingerprint=fingerprint(charges[-1].model_dump()), sent_at=at))
    return min(approval.deadline, approval.approved_at + worker.s.run_seconds)


@controlled
def settle(store, c, user, activation, aid):
    # Evidence settlement is metadata-only and independent of current Goal/Grant/lease/expiry.
    approval_id = activation.approval_id
    charges, _, _ = audit(store, c, user, approval_id, transition=aid)
    charge = next((r for r in charges if r.attempt_id == aid), None)
    require(charge is not None)
    actual = _attempt(c, aid)
    require(actual["status"] in {"RECEIVED", "FAILED"})
    result = Settlement(charge_fingerprint=fingerprint(charge.model_dump()),
        status=actual["status"], usage=copy.deepcopy(actual["usage"]), error=actual["error"])
    if aid in _keys(c, user, approval_id, SETTLE):
        old = _get(c, user, approval_id, SETTLE, aid, Settlement)
        require(fingerprint(old.model_dump()) == fingerprint(result.model_dump()))
    else:
        _save(c, user, approval_id, SETTLE, aid, result)
