"""Explicit bounded NL approval; no credential discovery, grants, network or refunds.

Caller holds project -> Run locks for in-transaction worker hooks. Sending is
linearized by committing SENDING before the provider request, not atomically
with the network. Expiry/revoke stop future effects; settlement retains receipts.
"""

import hashlib
import math
import re
import time
from typing import Literal

from pydantic import Field, ValidationError
from sqlalchemy import insert, select, update

from .contracts import Strict
from .db import (
    attempts,
    events,
    fingerprint,
    goal_cards,
    natural_activations,
    new_id,
    quotas,
    reservations,
    resources,
    run_contracts,
    runs,
)
from .errors import DomainError
from .goals import GoalCardInput, validate_card_version
from .model import InternModel

CSV = "item,quantity_z\na,7\nb,12\n"
CSV_HASH = hashlib.sha256(CSV.encode()).hexdigest()
KINDS = ("read_preview", "sum_quantity_z")
LEGACY_CAPS = {"requests": 2, "tokens": 22000, "output_tokens": 512, "ttl_seconds": 7200}
CAPS = {**LEGACY_CAPS, "rpm": 1}
CONSENT = "APPROVE_EXACT_SYNTHETIC_SCOPE_NO_GENERAL_MODEL_AUTHORITY"


def now():
    return time.time()


def synthetic_goal(rid, kind):
    if kind not in KINDS:
        raise DomainError("INVALID_INPUT")
    return GoalCardInput(
        title="Synthetic CSV preview" if kind == "read_preview" else "Synthetic quantity_z sum",
        goal="Read the synthetic CSV and preview its rows."
        if kind == "read_preview"
        else "Compute the sum of quantity_z in the synthetic CSV.",
        known=["Only the fixed synthetic CSV is in scope."],
        assumptions=[],
        unresolved=[],
        constraints=["Read only; no external data or arbitrary code."],
        acceptance_checks=["Use the bound registered read-only tool and retain its receipt."],
        resource_refs=[rid],
    ).model_dump()


class GoalBindingInput(Strict):
    kind: Literal["read_preview", "sum_quantity_z"]
    card_id: str = Field(pattern=r"^goal_[a-f0-9]{32}$")
    expected_version: int = Field(strict=True, ge=1)
    expected_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class CreateInput(Strict):
    goal_bindings: list[GoalBindingInput] = Field(min_length=1, max_length=2)
    request_key: str = Field(min_length=1, max_length=100)


class ApproveInput(Strict):
    expected_version: int = Field(strict=True, ge=1)
    expected_scope_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)
    consent: Literal["APPROVE_EXACT_SYNTHETIC_SCOPE_NO_GENERAL_MODEL_AUTHORITY"]


class RevokeInput(Strict):
    expected_version: int = Field(strict=True, ge=1)
    expected_scope_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)


def _input(cls, body):
    try:
        return cls.model_validate(body).model_dump()
    except ValidationError as exc:
        raise DomainError("INVALID_INPUT", "Invalid activation input") from exc


def _enabled(settings):
    if settings is None or getattr(settings, "natural_activation_enabled", False) is not True:
        raise DomainError("RESOURCE_UNAVAILABLE", "Natural activation mechanism is disabled")


def _provider(settings):
    endpoint = getattr(InternModel, "ENDPOINT", None)
    if not isinstance(endpoint, str) or not endpoint or settings.model != "intern-s2":
        raise DomainError("RESOURCE_UNAVAILABLE", "Registered provider endpoint required")
    if not isinstance(settings.quota_subject, str) or not settings.quota_subject:
        raise DomainError("RESOURCE_UNAVAILABLE", "Existing quota subject required")
    return {"model": settings.model, "endpoint": endpoint, "quota_subject": settings.quota_subject}


def _scope(store, c, user, pid, bindings, settings):
    project = store.own_project(c, user, pid)
    if len({b["kind"] for b in bindings}) != len(bindings) or len(
        {b["card_id"] for b in bindings}
    ) != len(bindings):
        raise DomainError("INVALID_INPUT", "Kinds and goal cards must be distinct")
    goals = []
    for b in sorted(bindings, key=lambda v: KINDS.index(v["kind"])):
        card = (
            c.execute(select(goal_cards).where(goal_cards.c.id == b["card_id"])).mappings().first()
        )
        if not card or card["project_id"] != pid:
            raise DomainError("PERMISSION_DENIED")
        if (
            type(card["version"]) is not int
            or card["version"] != b["expected_version"]
            or card["fingerprint"] != b["expected_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        saved = validate_card_version(store, c, user, card["id"], card["version"])
        if saved["fingerprint"] != b["expected_fingerprint"]:
            raise DomainError("VERSION_CONFLICT")
        refs = saved["snapshot"]["content"].get("resource_refs")
        if not isinstance(refs, list) or len(refs) != 1:
            raise DomainError("INVALID_INPUT", "Exactly one synthetic material required")
        rid = refs[0]
        resource = (
            c.execute(select(resources).where(resources.c.id == rid, resources.c.project_id == pid))
            .mappings()
            .first()
        )
        if (
            not resource
            or resource["format"] != "csv"
            or resource["content"] != CSV
            or resource["hash"] != CSV_HASH
            or fingerprint(saved["snapshot"]["content"])
            != fingerprint(synthetic_goal(rid, b["kind"]))
        ):
            raise DomainError(
                "INVALID_INPUT", "Exact synthetic bytes and full goal template required"
            )
        for tool in ("resource.read", "data.aggregate_csv"):
            store.authorize(c, user, project["runtime_id"], pid, rid, tool)
        goals.append(
            {**b, "snapshot": saved["snapshot"], "resource_id": rid, "resource_hash": CSV_HASH}
        )
    return {
        "version": "natural-activation.v2",
        "principal_id": user,
        "project_id": pid,
        "runtime_id": project["runtime_id"],
        "mode": "OFFLINE_TEST" if store.test_only else "LIVE",
        "provider": _provider(settings),
        "caps": CAPS,
        "goals": goals,
    }


def _event_values(c, aid, kind):
    return (
        c.execute(select(events.c.data).where(events.c.run_id == aid, events.c.kind == kind))
        .scalars()
        .all()
    )


def _row(store, c, user, aid, *, lock=True):
    row = (
        c.execute(
            select(natural_activations).where(
                natural_activations.c.id == aid, natural_activations.c.principal_id == user
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise DomainError("PERMISSION_DENIED")
    store.own_project(c, user, row["project_id"])
    if lock:
        row = (
            c.execute(
                select(natural_activations).where(natural_activations.c.id == aid).with_for_update()
            )
            .mappings()
            .one()
        )
    return row


def _scope_shape(scope):
    if set(scope) != {
        "version",
        "principal_id",
        "project_id",
        "runtime_id",
        "mode",
        "provider",
        "caps",
        "goals",
    }:
        raise ValueError()
    if scope["version"] not in {"natural-activation.v1", "natural-activation.v2"} or scope["mode"] not in {
        "OFFLINE_TEST",
        "LIVE",
    }:
        raise ValueError()
    provider = scope["provider"]
    if (
        set(provider) != {"model", "endpoint", "quota_subject"}
        or provider["model"] != "intern-s2"
        or provider["endpoint"] != InternModel.ENDPOINT
        or not isinstance(provider["quota_subject"], str)
        or not provider["quota_subject"]
    ):
        raise ValueError()
    goals = scope["goals"]
    if not isinstance(goals, list) or not 1 <= len(goals) <= 2:
        raise ValueError()
    if len({g["kind"] for g in goals}) != len(goals) or len({g["card_id"] for g in goals}) != len(
        goals
    ):
        raise ValueError()
    for g in goals:
        if set(g) != set(GoalBindingInput.model_fields) | {
            "snapshot",
            "resource_id",
            "resource_hash",
        }:
            raise ValueError()
        parsed = GoalBindingInput.model_validate({k: g[k] for k in GoalBindingInput.model_fields})
        if fingerprint(parsed.model_dump()) != fingerprint(
            {k: g[k] for k in GoalBindingInput.model_fields}
        ):
            raise ValueError()
        snap = {
            "schema_version": "F2-goal-card.v1",
            "content": synthetic_goal(g["resource_id"], g["kind"]),
            "resource_snapshots": [
                {"resource_id": g["resource_id"], "hash": CSV_HASH, "format": "csv"}
            ],
        }
        if (
            fingerprint(g["snapshot"]) != fingerprint(snap)
            or g["expected_fingerprint"] != fingerprint(snap)
            or g["resource_hash"] != CSV_HASH
        ):
            raise ValueError()


def _static(c, row, transition_attempt=None):
    try:
        _scope_shape(row["scope"])
        expected = {
            "activation_id": row["id"],
            "principal_id": row["principal_id"],
            "project_id": row["project_id"],
            "request_key": row["request_key"],
            "scope": row["scope"],
            "scope_fingerprint": row["scope_fingerprint"],
            "created_at": row["created_at"],
        }
        if (
            fingerprint(_event_values(c, row["id"], "NL_ACTIVATION_CREATED"))
            != fingerprint([expected])
            or fingerprint(row["scope"]) != row["scope_fingerprint"]
            or fingerprint(row["scope"]["caps"]) != fingerprint(LEGACY_CAPS if row["scope"]["version"] == "natural-activation.v1" else CAPS)
            or row["scope"]["principal_id"] != row["principal_id"]
            or row["scope"]["project_id"] != row["project_id"]
            or type(row["version"]) is not int
        ):
            raise ValueError()
        approvals = _event_values(c, row["id"], "NL_ACTIVATION_APPROVED")
        if row["approval"] is None:
            if (
                approvals
                or row["approval_fingerprint"] is not None
                or row["status"] != "DRAFT"
                or row["version"] != 1
            ):
                raise ValueError()
        else:
            approval = row["approval"]
            if (
                fingerprint(approvals) != fingerprint([approval])
                or fingerprint(approval) != row["approval_fingerprint"]
                or approval["scope_fingerprint"] != row["scope_fingerprint"]
                or approval["activation_id"] != row["id"]
                or approval["principal_id"] != row["principal_id"]
                or approval["consent"] != CONSENT
                or type(approval["expected_version"]) is not int
                or approval["expected_version"] != 1
                or type(approval["approved_at"]) not in {int, float}
                or type(approval["expires_at"]) not in {int, float}
                or not math.isfinite(approval["approved_at"])
                or not math.isfinite(approval["expires_at"])
                or approval["expires_at"] != approval["approved_at"] + CAPS["ttl_seconds"]
            ):
                raise ValueError()
            transitions = _event_values(c, row["id"], "NL_ACTIVATION_REVOKED") + _event_values(
                c, row["id"], "NL_ACTIVATION_EXPIRED"
            )
            if transitions and transitions[0].get("status") not in {"REVOKED", "EXPIRED"}:
                raise ValueError()
            expected_status = transitions[-1]["status"] if transitions else "APPROVED"
            if (
                len(transitions) > 1
                or row["status"] != expected_status
                or row["version"] != 2 + len(transitions)
            ):
                raise ValueError()
        _audit(c, row, transition_attempt)
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise DomainError("OUTCOME_UNKNOWN", "Activation seals or ledger inconsistent") from exc


def _binding(snapshot):
    if not isinstance(snapshot, dict):
        return None
    policy = snapshot.get("natural_planning")
    return policy.get("activation") if isinstance(policy, dict) else None


def _attempt_seal(a):
    p = a["parameters"]
    return {
        "run_id": a["run_id"],
        "mode": a["mode"],
        "request_model": a["request_model"],
        "reserved_tokens": a["reserved_tokens"],
        "request_fingerprint": p.get("request_fingerprint"),
        "planning_wire": p.get("planning_wire"),
        "planning_fence": p.get("planning_fence"),
        "max_tokens": p.get("max_tokens"),
        "stream": p.get("stream"),
    }


def _audit(c, row, transition_attempt=None):
    ledger = row["ledger"]
    if not isinstance(ledger, list) or len(ledger) > 2:
        raise ValueError()
    charged = _event_values(c, row["id"], "NL_ACTIVATION_SLOT_RESERVED")
    if len(charged) != len(ledger):
        raise ValueError()
    run_ids = set()
    for rid, snapshot in c.execute(select(run_contracts.c.run_id, run_contracts.c.snapshot)):
        b = _binding(snapshot)
        if isinstance(b, dict) and b.get("activation_id") == row["id"]:
            run_ids.add(rid)
    for rid, data in c.execute(
        select(events.c.run_id, events.c.data).where(events.c.kind == "ACCEPTED")
    ):
        b = _binding(data)
        if isinstance(b, dict) and b.get("activation_id") == row["id"]:
            run_ids.add(rid)
    all_attempts = c.execute(select(attempts)).mappings().all()
    # Independent Attempt marker survives deletion of a contract or ACCEPTED row.
    for a in all_attempts:
        params = a["parameters"]
        marker = params.get("natural_activation_slot") if isinstance(params, dict) else None
        if isinstance(marker, dict) and marker.get("activation_id") == row["id"]:
            run_ids.add(a["run_id"])
    actual = [a for a in all_attempts if a["run_id"] in run_ids]
    for rid in run_ids:
        r = c.execute(select(runs).where(runs.c.id == rid)).mappings().first()
        own_attempts = [a for a in actual if a["run_id"] == rid and a["id"] != transition_attempt]
        if transition_attempt in {s["charge"]["attempt_id"] for s in ledger}:
            own_attempts = [a for a in actual if a["run_id"] == rid]
        if (
            not r
            or not isinstance(r["context"], dict)
            or type(r["context"].get("requests")) is not int
            or r["context"]["requests"] != len(own_attempts)
            or type(r["context"].get("reserved_tokens")) is not int
            or r["context"]["reserved_tokens"] != sum(a["reserved_tokens"] for a in own_attempts)
        ):
            raise ValueError()
    ledger_ids = {s["charge"]["attempt_id"] for s in ledger}
    actual_ids = {a["id"] for a in actual}
    if transition_attempt is not None and transition_attempt not in ledger_ids:
        actual_ids.discard(transition_attempt)
    if actual_ids != ledger_ids:
        raise ValueError()
    by_id = {a["id"]: a for a in actual}
    if len({s["charge"]["kind"] for s in ledger}) != len(ledger):
        raise ValueError()
    total = 0
    for slot in ledger:
        if set(slot) != {"charge", "status", "settlement"}:
            raise ValueError()
        charge = slot["charge"]
        if set(charge) != {
            "activation_id",
            "scope_fingerprint",
            "approval_fingerprint",
            "kind",
            "run_id",
            "fence",
            "attempt_id",
            "envelope",
            "wire_fingerprint",
            "request_fingerprint",
            "attempt_fingerprint",
        }:
            raise ValueError()
        saved = (
            c.execute(select(run_contracts).where(run_contracts.c.run_id == charge["run_id"]))
            .mappings()
            .first()
        )
        r = c.execute(select(runs).where(runs.c.id == charge["run_id"])).mappings().first()
        matching_goal = [g for g in row["scope"]["goals"] if g["kind"] == charge["kind"]]
        if (
            not saved
            or fingerprint(saved["snapshot"]) != saved["fingerprint"]
            or not r
            or len(matching_goal) != 1
            or fingerprint(_binding(saved["snapshot"]))
            != fingerprint(
                {
                    "activation_id": row["id"],
                    "scope_fingerprint": row["scope_fingerprint"],
                    "approval_fingerprint": row["approval_fingerprint"],
                }
            )
            or saved["snapshot"].get("source_goal_card", {}).get("card_id")
            != matching_goal[0]["card_id"]
            or r["principal_id"] != row["principal_id"]
            or r["project_id"] != row["project_id"]
            or type(r["fence"]) is not int
            or r["fence"] < charge["fence"]
        ):
            raise ValueError()
        if sum(fingerprint(e) == fingerprint(charge) for e in charged) != 1:
            raise ValueError()
        if (
            charge["activation_id"] != row["id"]
            or charge["scope_fingerprint"] != row["scope_fingerprint"]
            or charge["approval_fingerprint"] != row["approval_fingerprint"]
            or type(charge["envelope"]) is not int
            or not 1 <= charge["envelope"] <= 11000
            or type(charge["fence"]) is not int
            or charge["fence"] < 1
        ):
            raise ValueError()
        total += charge["envelope"]
        a = by_id[charge["attempt_id"]]
        if (
            fingerprint(_attempt_seal(a)) != charge["attempt_fingerprint"]
            or fingerprint(a["parameters"].get("natural_activation_slot")) != fingerprint(charge)
            or a["run_id"] != charge["run_id"]
        ):
            raise ValueError()
        sent = [
            v
            for v in _event_values(c, row["id"], "NL_ACTIVATION_SENDING")
            if v["attempt_id"] == a["id"]
        ]
        finished = [
            v
            for v in _event_values(c, row["id"], "NL_ACTIVATION_SETTLED")
            if v["attempt_id"] == a["id"]
        ]
        if slot["status"] == "STARTED":
            if (
                (a["status"] != "STARTED" and a["id"] != transition_attempt)
                or sent
                or finished
                or slot["settlement"] is not None
            ):
                raise ValueError()
        elif slot["status"] == "SENDING":
            if (
                (a["status"] != "STARTED" and a["id"] != transition_attempt)
                or fingerprint(sent) != fingerprint([charge])
                or finished
                or slot["settlement"] is not None
            ):
                raise ValueError()
        elif slot["status"] in {"RECEIVED", "FAILED", "UNKNOWN"}:
            settlement = slot["settlement"]
            if (
                fingerprint(finished) != fingerprint([settlement])
                or settlement["attempt_id"] != a["id"]
                or settlement["status"] != slot["status"]
            ):
                raise ValueError()
            if settlement["attempt_fingerprint"] != fingerprint(dict(a)) or fingerprint(
                settlement["usage"]
            ) != fingerprint(a["usage"]):
                raise ValueError()
            if slot["status"] == "RECEIVED" and (
                a["status"] != "RECEIVED" or fingerprint(sent) != fingerprint([charge])
            ):
                raise ValueError()
            if slot["status"] == "FAILED" and a["status"] != "FAILED":
                raise ValueError()
            _tokens(settlement["usage"])
        else:
            raise ValueError()
    if total > CAPS["tokens"]:
        raise ValueError()


def _tokens(usage):
    if not isinstance(usage, dict) or set(usage) != {"status", "tokens"}:
        raise ValueError()
    if usage["status"] == "unknown" and usage["tokens"] is None:
        return None
    t = usage["tokens"]
    keys = {"prompt_tokens", "completion_tokens", "total_tokens"}
    if not isinstance(t, dict) or not t or not set(t) <= keys:
        raise ValueError()
    if any(type(v) is not int or v < 0 for v in t.values()):
        raise ValueError()
    complete = set(t) == keys and t["total_tokens"] == t["prompt_tokens"] + t["completion_tokens"]
    if usage["status"] == "partial" and not complete:
        return None  # Preserve every normalized partial field; never infer known total.
    if usage["status"] != "known" or not complete:
        raise ValueError()
    return t["total_tokens"]


def _active(store, c, row, settings):
    _enabled(settings)
    if row["scope"]["version"] != "natural-activation.v2" or row["scope"]["caps"].get("rpm") != 1:
        raise DomainError("VERSION_CONFLICT", "A new explicit rate-bound scope is required")
    if (
        row["status"] != "APPROVED"
        or now() >= row["approval"]["expires_at"]
        or now() < row["approval"]["approved_at"]
    ):
        raise DomainError("PERMISSION_DENIED", "Approval revoked, expired or absent")
    if fingerprint(row["scope"]["provider"]) != fingerprint(_provider(settings)):
        raise DomainError("VERSION_CONFLICT", "Provider configuration differs from approval")
    mode = "OFFLINE_TEST" if store.test_only else "LIVE"
    if row["scope"]["mode"] != mode:
        raise DomainError("PERMISSION_DENIED", "Activation mode differs")
    if mode == "LIVE" and (
        getattr(settings, "natural_activation_live_id", "") != row["id"]
        or not settings.live_enabled
        or not settings.token
        or settings.mode != "live"
    ):
        raise DomainError(
            "RESOURCE_UNAVAILABLE",
            "Exact LIVE activation and existing sender configuration required",
        )
    current = _scope(
        store,
        c,
        row["principal_id"],
        row["project_id"],
        [{k: g[k] for k in GoalBindingInput.model_fields} for g in row["scope"]["goals"]],
        settings,
    )
    if fingerprint(current) != row["scope_fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "Current approved scope differs")
    for s in row["ledger"]:
        if s["status"] == "FAILED":
            raise DomainError("PERMISSION_DENIED", "Failed send closes further activation use")
        if s["status"] == "UNKNOWN":
            raise DomainError("OUTCOME_UNKNOWN", "Unresolved send prevents further activation use")
        if s["settlement"] is not None:
            total = _tokens(s["settlement"]["usage"])
            if total is None or total > s["charge"]["envelope"]:
                raise DomainError(
                    "OUTCOME_UNKNOWN", "Unknown or excess usage prevents further sends"
                )


def _public(row):
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "version": row["version"],
        "status": row["status"],
        "scope": row["scope"],
        "scope_fingerprint": row["scope_fingerprint"],
        "approval": row["approval"],
        "approval_fingerprint": row["approval_fingerprint"],
        "charged_requests": len(row["ledger"]),
        "reserved_tokens": sum(s["charge"]["envelope"] for s in row["ledger"]),
        "approved_not_expired": row["status"] == "APPROVED"
        and now() < row["approval"]["expires_at"],
    }


def create(store, user, pid, body, settings):
    _enabled(settings)
    req = _input(CreateInput, body)
    with store.tx() as c:
        store.lock_project(c, user, pid)
        scope = _scope(store, c, user, pid, req["goal_bindings"], settings)
        old = (
            c.execute(
                select(natural_activations).where(
                    natural_activations.c.principal_id == user,
                    natural_activations.c.project_id == pid,
                    natural_activations.c.request_key == req["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if old:
            _static(c, old)
            if fingerprint(scope) != old["scope_fingerprint"]:
                raise DomainError("VERSION_CONFLICT")
            return _public(old)
        aid = new_id("nlactivation")
        created = now()
        values = dict(
            id=aid,
            principal_id=user,
            project_id=pid,
            request_key=req["request_key"],
            version=1,
            status="DRAFT",
            scope=scope,
            scope_fingerprint=fingerprint(scope),
            approval=None,
            approval_fingerprint=None,
            ledger=[],
            created_at=created,
        )
        c.execute(insert(natural_activations).values(**values))
        store.event(
            c,
            aid,
            "NL_ACTIVATION_CREATED",
            {
                "activation_id": aid,
                "principal_id": user,
                "project_id": pid,
                "request_key": req["request_key"],
                "scope": scope,
                "scope_fingerprint": fingerprint(scope),
                "created_at": created,
            },
        )
        return _public(values)


def inspect(store, user, activation_id, settings=None):
    with store.tx() as c:
        row = _row(store, c, user, activation_id, lock=False)
        _static(c, row)
        return _public(row)



def list_for_project(store, user, pid, settings):
    """Owner-scoped audited read; eligibility is not an approval or a model call."""
    with store.tx() as c:
        store.own_project(c, user, pid)
        rows = c.execute(select(natural_activations).where(
            natural_activations.c.project_id == pid,
            natural_activations.c.principal_id == user,
        ).order_by(natural_activations.c.created_at)).mappings().all()
        items = []
        for row in rows:
            _static(c, row)
            reason = None
            try:
                _active(store, c, row, settings)
            except DomainError as error:
                reason = error.code
            items.append({**_public(row), "submission_available": reason is None,
                          "blocked_reason": reason,
                          "charged_kinds": [slot["charge"]["kind"] for slot in row["ledger"]]})
        return {"project_id": pid, "items": items, "general_live_request_allowance": 0}

def approve(store, user, activation_id, body, settings):
    _enabled(settings)
    req = _input(ApproveInput, body)
    with store.tx() as c:
        location = _row(store, c, user, activation_id, lock=False)
        store.lock_project(c, user, location["project_id"])
        row = _row(store, c, user, activation_id)
        _static(c, row)
        if row["approval"] is not None:
            if fingerprint(
                {k: row["approval"][k] for k in ApproveInput.model_fields}
            ) != fingerprint(req):
                raise DomainError("VERSION_CONFLICT")
            return _public(row)  # Never renew approval or expiry on retry.
        if (
            row["version"] != req["expected_version"]
            or row["scope_fingerprint"] != req["expected_scope_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        fresh = _scope(
            store,
            c,
            user,
            row["project_id"],
            [{k: g[k] for k in GoalBindingInput.model_fields} for g in row["scope"]["goals"]],
            settings,
        )
        if fingerprint(fresh) != row["scope_fingerprint"]:
            raise DomainError("VERSION_CONFLICT")
        at = now()
        approval = {
            **req,
            "activation_id": activation_id,
            "principal_id": user,
            "scope_fingerprint": row["scope_fingerprint"],
            "approved_at": at,
            "expires_at": at + CAPS["ttl_seconds"],
        }
        c.execute(
            update(natural_activations)
            .where(natural_activations.c.id == activation_id)
            .values(
                approval=approval,
                approval_fingerprint=fingerprint(approval),
                status="APPROVED",
                version=2,
            )
        )
        store.event(c, activation_id, "NL_ACTIVATION_APPROVED", approval)
        return _public(
            {
                **row,
                "approval": approval,
                "approval_fingerprint": fingerprint(approval),
                "status": "APPROVED",
                "version": 2,
            }
        )


def revoke(store, user, activation_id, body, settings):
    _enabled(settings)
    req = _input(RevokeInput, body)
    with store.tx() as c:
        location = _row(store, c, user, activation_id, lock=False)
        store.lock_project(c, user, location["project_id"])
        row = _row(store, c, user, activation_id)
        _static(c, row)
        prior = _event_values(c, activation_id, "NL_ACTIVATION_REVOKED")
        if prior:
            if fingerprint(prior[0]["request"]) != fingerprint(req):
                raise DomainError("VERSION_CONFLICT")
            return _public(row)
        if (
            row["status"] != "APPROVED"
            or row["version"] != req["expected_version"]
            or row["scope_fingerprint"] != req["expected_scope_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        store.event(
            c,
            activation_id,
            "NL_ACTIVATION_REVOKED",
            {"status": "REVOKED", "request": req, "at": now()},
        )
        c.execute(
            update(natural_activations)
            .where(natural_activations.c.id == activation_id)
            .values(status="REVOKED", version=row["version"] + 1)
        )
        return _public({**row, "status": "REVOKED", "version": row["version"] + 1})


def close_expired(store, user, activation_id, settings):
    _enabled(settings)
    with store.tx() as c:
        location = _row(store, c, user, activation_id, lock=False)
        store.lock_project(c, user, location["project_id"])
        row = _row(store, c, user, activation_id)
        _static(c, row)
        if row["status"] != "APPROVED" or now() < row["approval"]["expires_at"]:
            raise DomainError("VERSION_CONFLICT")
        store.event(c, activation_id, "NL_ACTIVATION_EXPIRED", {"status": "EXPIRED", "at": now()})
        c.execute(
            update(natural_activations)
            .where(natural_activations.c.id == activation_id)
            .values(status="EXPIRED", version=row["version"] + 1)
        )
        return _public({**row, "status": "EXPIRED", "version": row["version"] + 1})


def binding_for_run(store, user, activation_id, card_id, body, settings):
    with store.tx() as c:
        location = _row(store, c, user, activation_id, lock=False)
        store.lock_project(c, user, location["project_id"])
        row = _row(store, c, user, activation_id)
        _static(c, row)
        _active(store, c, row, settings)
        matches = [g for g in row["scope"]["goals"] if g["card_id"] == card_id]
        if (
            len(matches) != 1
            or body.get("expected_version") != matches[0]["expected_version"]
            or body.get("expected_fingerprint") != matches[0]["expected_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        return {
            "activation_id": activation_id,
            "scope_fingerprint": row["scope_fingerprint"],
            "approval_fingerprint": row["approval_fingerprint"],
        }


def validate_run(store, c, run, settings=None, active=False, *, _transition_attempt=None):
    saved = (
        c.execute(
            select(run_contracts.c.snapshot, run_contracts.c.fingerprint).where(
                run_contracts.c.run_id == run["id"]
            )
        )
        .mappings()
        .first()
    )
    if not saved or fingerprint(saved["snapshot"]) != saved["fingerprint"]:
        raise DomainError("VERSION_CONFLICT")
    b = _binding(saved["snapshot"])
    if not isinstance(b, dict) or set(b) != {
        "activation_id",
        "scope_fingerprint",
        "approval_fingerprint",
    }:
        raise DomainError("VERSION_CONFLICT", "Activation binding required")
    row = _row(store, c, run["principal_id"], b["activation_id"])
    _static(c, row, _transition_attempt)
    source = saved["snapshot"].get("source_goal_card")
    goals = [g for g in row["scope"]["goals"] if source and g["card_id"] == source.get("card_id")]
    if (
        row["project_id"] != run["project_id"]
        or row["scope"]["runtime_id"] != run["runtime_id"]
        or b["scope_fingerprint"] != row["scope_fingerprint"]
        or b["approval_fingerprint"] != row["approval_fingerprint"]
        or len(goals) != 1
        or source["version"] != goals[0]["expected_version"]
        or source["fingerprint"] != goals[0]["expected_fingerprint"]
        or fingerprint(source["snapshot"]) != fingerprint(goals[0]["snapshot"])
        or run["resource_refs"] != [goals[0]["resource_id"]]
        or run["goal"] != goals[0]["snapshot"]["content"]["goal"]
        or saved["snapshot"]["run_id"] != run["id"]
    ):
        raise DomainError("VERSION_CONFLICT", "Run differs from its exact activation goal")
    limits = saved["snapshot"].get("limits")
    caps = {
        "max_requests": 1,
        "max_repairs": 0,
        "max_tools": 2,
        "max_total_tokens": 11000,
        "max_output_tokens": 512,
        "run_seconds": 120,
    }
    policy = saved["snapshot"].get("natural_planning", {})
    if (
        not isinstance(limits, dict)
        or set(limits) != set(caps)
        or any(
            type(limits[k]) is not int
            or limits[k] < (0 if k == "max_repairs" else 1)
            or limits[k] > v
            for k, v in caps.items()
        )
        or policy.get("require_confirmation") is not True
        or saved["snapshot"].get("request_model") != "intern-s2"
        or saved["snapshot"].get("runtime_id") != run["runtime_id"]
        or type(source["version"]) is not int
    ):
        raise DomainError(
            "VERSION_CONFLICT", "Activation requires tightened confirmed read-only Run limits"
        )
    accepted = (
        c.execute(
            select(events.c.data).where(events.c.run_id == run["id"], events.c.kind == "ACCEPTED")
        )
        .scalars()
        .all()
    )
    if len(accepted) != 1 or fingerprint(_binding(accepted[0])) != fingerprint(b):
        raise DomainError("VERSION_CONFLICT", "Accepted activation binding changed")
    if active:
        _active(store, c, row, settings)
        from .goal_planner import check_run_deadline
        check_run_deadline(store, c, run)
    return row


def validate_plan(store, c, run, plan):
    row = validate_run(store, c, run)
    snapshot = c.execute(
        select(run_contracts.c.snapshot).where(run_contracts.c.run_id == run["id"])
    ).scalar_one()
    goal = next(
        g for g in row["scope"]["goals"] if g["card_id"] == snapshot["source_goal_card"]["card_id"]
    )
    steps = plan.get("steps") if isinstance(plan, dict) else None
    expected_tool = "resource.read" if goal["kind"] == "read_preview" else "data.aggregate_csv"
    if (
        not isinstance(steps, list)
        or len(steps) != 1
        or not isinstance(steps[0], dict)
        or steps[0].get("tool_ref") != expected_tool
        or steps[0].get("resource_id") != goal["resource_id"]
        or steps[0].get("depends_on") != []
        or steps[0].get("column") != (None if goal["kind"] == "read_preview" else "quantity_z")
    ):
        raise DomainError("MODEL_OUTPUT_INVALID", "Plan is outside exact approved goal operation")
    return {"kind": goal["kind"], "resource_id": goal["resource_id"]}


def reserve_slot(store, c, run, fence, attempt_id, envelope, wire_fp, settings):
    row = validate_run(store, c, run, settings, active=True, _transition_attempt=attempt_id)
    if (
        type(fence) is not int
        or fence != run["fence"]
        or type(envelope) is not int
        or not 1 <= envelope <= 11000
        or not re.fullmatch(r"[a-f0-9]{64}", wire_fp)
    ):
        raise DomainError("INVALID_INPUT")
    if (
        len(row["ledger"]) >= 2
        or sum(s["charge"]["envelope"] for s in row["ledger"]) + envelope > 22000
    ):
        raise DomainError("BUDGET_EXHAUSTED")
    if any(s["status"] in {"STARTED", "SENDING", "UNKNOWN"} for s in row["ledger"]):
        raise DomainError("OUTCOME_UNKNOWN", "Previous send has not settled")
    source = c.execute(
        select(run_contracts.c.snapshot).where(run_contracts.c.run_id == run["id"])
    ).scalar_one()["source_goal_card"]
    goal = next(g for g in row["scope"]["goals"] if g["card_id"] == source["card_id"])
    if any(s["charge"]["kind"] == goal["kind"] for s in row["ledger"]):
        raise DomainError("BUDGET_EXHAUSTED", "This approved goal already used its one request")
    a = (
        c.execute(
            select(attempts).where(attempts.c.id == attempt_id, attempts.c.run_id == run["id"])
        )
        .mappings()
        .one()
    )
    p = a["parameters"]
    if (
        a["status"] != "STARTED"
        or a["request_model"] != row["scope"]["provider"]["model"]
        or a["mode"] != ("MOCK" if store.test_only else "LIVE")
        or a["reserved_tokens"] != envelope
        or type(p.get("max_tokens")) is not int
        or not 1 <= p["max_tokens"] <= 512
        or p.get("stream") is not False
        or p.get("planning_fence") != fence
        or not isinstance(p.get("planning_wire"), dict)
        or set(p["planning_wire"]) != {"sha256", "bytes", "characters"}
        or type(p["planning_wire"].get("bytes")) is not int
        or type(p["planning_wire"].get("characters")) is not int
        or not 1 <= p["planning_wire"]["characters"] <= p["planning_wire"]["bytes"] <= 10000
        or p["planning_wire"]["characters"] > 8000
        or envelope != p["planning_wire"]["bytes"] + p["max_tokens"]
        or not isinstance(p.get("request_fingerprint"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", p["request_fingerprint"])
        or p["planning_wire"].get("sha256") != wire_fp
    ):
        raise DomainError("VERSION_CONFLICT", "Actual Attempt envelope differs")
    charge = {
        "activation_id": row["id"],
        "scope_fingerprint": row["scope_fingerprint"],
        "approval_fingerprint": row["approval_fingerprint"],
        "kind": goal["kind"],
        "run_id": run["id"],
        "fence": fence,
        "attempt_id": attempt_id,
        "envelope": envelope,
        "wire_fingerprint": wire_fp,
        "request_fingerprint": p.get("request_fingerprint"),
        "attempt_fingerprint": fingerprint(_attempt_seal(a)),
    }
    ledger = [*row["ledger"], {"charge": charge, "status": "STARTED", "settlement": None}]
    params = {**p, "natural_activation_slot": charge}
    c.execute(update(attempts).where(attempts.c.id == attempt_id).values(parameters=params))
    c.execute(
        update(natural_activations)
        .where(natural_activations.c.id == row["id"])
        .values(ledger=ledger)
    )
    store.event(c, row["id"], "NL_ACTIVATION_SLOT_RESERVED", charge)
    return charge


def mark_sending(store, c, run, fence, attempt_id, settings):
    row = validate_run(store, c, run, settings, active=True)
    if fence != run["fence"]:
        raise DomainError("VERSION_CONFLICT")
    ledger = [dict(s) for s in row["ledger"]]
    matching = [
        s
        for s in ledger
        if s["charge"]["attempt_id"] == attempt_id
        and s["charge"]["run_id"] == run["id"]
        and s["charge"]["fence"] == fence
    ]
    if (
        len(matching) != 1
        or matching[0]["status"] != "STARTED"
        or any(
            s["status"] in {"STARTED", "SENDING", "UNKNOWN"} and s is not matching[0]
            for s in ledger
        )
    ):
        raise DomainError("OUTCOME_UNKNOWN", "Dispatch requires its sole unsent reservation")
    subject = row["scope"]["provider"]["quota_subject"]
    quota = c.execute(select(quotas).where(quotas.c.subject == subject).with_for_update()).mappings().first()
    own = c.execute(select(reservations).where(reservations.c.id == attempt_id,
                    reservations.c.subject == subject, reservations.c.run_id == run["id"])).mappings().first()
    current = now()
    recent = c.execute(select(reservations.c.id).where(
        reservations.c.subject == subject, reservations.c.id != attempt_id,
        reservations.c.created_at > current - 60)).first()
    if not quota or not own:
        raise DomainError("VERSION_CONFLICT", "Actual account reservation required")
    pending = c.execute(select(attempts.c.id).join(
        reservations, reservations.c.id == attempts.c.id).where(
        reservations.c.subject == subject, attempts.c.id != attempt_id,
        attempts.c.status == "STARTED")).first()
    if quota["blocked_until"] > current or recent or pending:
        raise DomainError("RATE_LIMITED", "Frozen activation account rate is one per minute")
    # A delayed final guard starts a fresh account-wide window; reserve-time age is not a bypass.
    c.execute(update(reservations).where(reservations.c.id == attempt_id).values(created_at=current))
    c.execute(update(quotas).where(quotas.c.subject == subject).values(blocked_until=current + 60))
    store.event(c, row["id"], "NL_ACTIVATION_SEND_TIME",
                {"attempt_id": attempt_id, "subject": subject, "sent_at": current, "rpm": 1})
    matching[0]["status"] = "SENDING"
    c.execute(
        update(natural_activations)
        .where(natural_activations.c.id == row["id"])
        .values(ledger=ledger)
    )
    store.event(c, row["id"], "NL_ACTIVATION_SENDING", matching[0]["charge"])
    return matching[0]["charge"]


def settle(store, c, run, fence, attempt_id, status, usage, error_code=None):
    # Receipt cleanup deliberately bypasses mechanism/expiry/revoke/current Grant gates.
    row = validate_run(store, c, run, active=False, _transition_attempt=attempt_id)
    if (
        status not in {"RECEIVED", "FAILED", "UNKNOWN"}
        or error_code is not None
        and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", error_code)
    ):
        raise DomainError("INVALID_INPUT")
    try:
        count = _tokens(usage)
    except (ValueError, TypeError, KeyError) as exc:
        raise DomainError("OUTCOME_UNKNOWN", "Malformed actual usage") from exc
    ledger = [dict(s) for s in row["ledger"]]
    matches = [
        s
        for s in ledger
        if s["charge"]["attempt_id"] == attempt_id
        and s["charge"]["run_id"] == run["id"]
        and s["charge"]["fence"] == fence
    ]
    if len(matches) != 1 or matches[0]["status"] not in {"STARTED", "SENDING"}:
        raise DomainError("OUTCOME_UNKNOWN")
    a = c.execute(select(attempts).where(attempts.c.id == attempt_id)).mappings().one()
    if (
        fingerprint(a["usage"]) != fingerprint(usage)
        or status in {"RECEIVED", "FAILED"}
        and a["status"] != status
    ):
        raise DomainError("VERSION_CONFLICT")
    if status == "RECEIVED" and matches[0]["status"] != "SENDING":
        raise DomainError("OUTCOME_UNKNOWN", "No linearized send exists")
    actual_status = (
        "UNKNOWN" if count is None or count > matches[0]["charge"]["envelope"] else status
    )
    receipt = {
        "attempt_id": attempt_id,
        "status": actual_status,
        "usage": usage,
        "error_code": error_code,
        "attempt_fingerprint": fingerprint(dict(a)),
    }
    matches[0]["status"] = actual_status
    matches[0]["settlement"] = receipt
    c.execute(
        update(natural_activations)
        .where(natural_activations.c.id == row["id"])
        .values(ledger=ledger)
    )
    store.event(c, row["id"], "NL_ACTIVATION_SETTLED", receipt)
    return receipt
