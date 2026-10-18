"""Bounded private execution bodies and original-trial OFFLINE source reads.

These archives record the actual serializer/adapter boundaries. They never
establish real provider provenance, account entitlement or LIVE permission.
"""

import base64
import hashlib
import time
from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import select

from .contracts import Strict, strict_json
from .db import (
    app_drafts,
    attempts,
    delivery_graph_requests,
    events,
    fingerprint,
    reservations,
    runs,
)
from .delivery_graph_apps import controlled
from .errors import DomainError
from .text_logic_reuse import pair, remember

VERSION: Literal["natural-source-body-archive.v1"] = "natural-source-body-archive.v1"
MAX_BODY_BYTES = 32768
REQUEST = "natural_source_request_body.v1"
RESPONSE = "natural_source_response_body.v1"


def require(ok, message="Original execution body archive changed"):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


class BodyArchive(Strict):
    version: Literal["natural-source-body-archive.v1"] = VERSION
    run_id: str = Field(pattern=r"^run_[a-f0-9]{32}$")
    attempt_id: str = Field(pattern=r"^attempt_[a-f0-9]{32}$")
    principal_id: str = Field(min_length=1, max_length=100)
    project_id: str = Field(min_length=1, max_length=100)
    runtime_id: str = Field(min_length=1, max_length=100)
    phase: Literal["RESERVED_REQUEST", "RECEIVED_DECODED_BODY"]
    provenance: Literal["OFFLINE_MOCKTRANSPORT"] = "OFFLINE_MOCKTRANSPORT"
    byte_count: int = Field(strict=True, ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    received_complete: bool
    extent: Literal["COMPLETE_BODY", "RECEIVED_PREFIX"]
    omission: Literal["NONE", "OVERSIZE", "EMPTY"]
    body_b64: str | None = Field(default=None, max_length=43692)
    canonical_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


def _body(job, aid, payload, complete, canonical_sha256, kind):
    omission: Literal["NONE", "OVERSIZE", "EMPTY"] = (
        "EMPTY" if not payload else "OVERSIZE" if len(payload) > MAX_BODY_BYTES else "NONE")
    return BodyArchive(run_id=job["id"], attempt_id=aid,
        principal_id=job["principal_id"], project_id=job["project_id"], runtime_id=job["runtime_id"],
        phase="RESERVED_REQUEST" if kind == REQUEST else "RECEIVED_DECODED_BODY",
        byte_count=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
        received_complete=complete, extent="COMPLETE_BODY" if complete else "RECEIVED_PREFIX",
        omission=omission,
        body_b64=base64.b64encode(payload).decode("ascii") if omission == "NONE" else None,
        canonical_sha256=canonical_sha256)


def receipt_owner(c, job, aid, request_body, *, reserved=False):
    # Scalar ownership and the original reserved wire precede any append. Late
    # receipt facts need no live lease, but may not follow a moved Run/Attempt.
    query = (select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
        attempts.c.mode, attempts.c.status,
        attempts.c.parameters["natural_spec_wire"]["sha256"].as_string().label("wire_sha256"),
        attempts.c.parameters["natural_spec_wire"]["bytes"].as_integer().label("wire_bytes"))
        .select_from(runs)
        .join(attempts, attempts.c.run_id == runs.c.id)
        .where(runs.c.id == job["id"], attempts.c.id == aid))
    # A response is an already received fact, not new reservation authority.
    # Losing a slot must still block verification, but cannot erase that fact.
    if reserved:
        query = query.join(reservations,
            (reservations.c.id == attempts.c.id) & (reservations.c.run_id == runs.c.id))
    identity = c.execute(query).mappings().first()
    require(identity is not None and identity["principal_id"] == job["principal_id"]
            and identity["project_id"] == job["project_id"]
            and identity["runtime_id"] == job["runtime_id"] and identity["mode"] == "MOCK"
            and identity["wire_sha256"] == hashlib.sha256(request_body).hexdigest()
            and identity["wire_bytes"] == len(request_body), "Body receipt owner or reserved wire changed")
    return identity


def _write(store, c, job, aid, payload, complete, canonical_sha256, kind, request_body):
    require(store.test_only and store.sqlite and type(payload) is bytes
            and type(request_body) is bytes and type(complete) is bool,
            "Body capture requires isolated offline SQLite")
    identity = receipt_owner(c, job, aid, request_body, reserved=kind == REQUEST)
    body = _body(job, aid, payload, complete, canonical_sha256, kind)
    if kind == RESPONSE:
        request = _body(job, aid, request_body, True, None, REQUEST).model_dump()
        headers = c.execute(select(delivery_graph_requests.c.kind,
            delivery_graph_requests.c.request_fingerprint, delivery_graph_requests.c.fingerprint).where(
            delivery_graph_requests.c.app_id == job["id"],
            delivery_graph_requests.c.principal_id == job["principal_id"],
            delivery_graph_requests.c.request_key == aid,
            delivery_graph_requests.c.kind.in_([REQUEST, REQUEST + "_seal"]))).mappings().all()
        require(len(headers) == 2 and {r["kind"] for r in headers} == {REQUEST, REQUEST + "_seal"}
                and all(r["request_fingerprint"] == fingerprint(request)
                    and r["fingerprint"] == fingerprint(dict(request=request, response=request))
                    for r in headers), "Original reserved request archive differs")
    existing = c.execute(select(delivery_graph_requests.c.kind,
        delivery_graph_requests.c.request_fingerprint, delivery_graph_requests.c.fingerprint).where(
        delivery_graph_requests.c.app_id == job["id"],
        delivery_graph_requests.c.principal_id == job["principal_id"],
        delivery_graph_requests.c.request_key == aid,
        delivery_graph_requests.c.kind.in_([kind, kind + "_seal"]))).mappings().all()
    if existing:
        expected = fingerprint(dict(request=body.model_dump(), response=body.model_dump()))
        require(len(existing) == 2 and {r["kind"] for r in existing} == {kind, kind + "_seal"}
                and all(r["request_fingerprint"] == fingerprint(body.model_dump())
                    and r["fingerprint"] == expected for r in existing),
                "Original body receipt is immutable; a different capture cannot replace it")
        return
    require(identity["status"] in ({"STARTED"} if kind == REQUEST else {"STARTED", "RECEIVED"}),
            "Completed execution history cannot be backfilled")
    if kind == REQUEST:
        require(c.execute(select(events.c.id).where(events.c.run_id == job["id"],
            events.c.kind == "MODEL_RESERVED", events.c.data["attempt_id"].as_string() == aid))
            .first() is None, "Old reservations cannot acquire a new body archive")
    # Only immutable, already owned identifiers are used here. In particular,
    # late receipt capture performs no new protected Run or material body read.
    remember(c, job["principal_id"], job["id"], kind, aid, body, body.model_dump())
    store.event(c, job["id"], "NS_WIRE_ARCHIVED" if kind == REQUEST else "NS_BODY_ARCHIVED",
        dict(attempt_id=aid, archive_fingerprint=fingerprint(body.model_dump())))


def record_request(store, c, job, aid, payload):
    require(0 < len(payload) <= MAX_BODY_BYTES, "Reserved request body exceeds its original bound")
    _write(store, c, job, aid, payload, True, None, REQUEST, payload)


def record_response(store, c, job, aid, payload, complete, canonical_sha256=None, *, request_body):
    _write(store, c, job, aid, payload, complete, canonical_sha256, RESPONSE, request_body)


def _read(c, user, job, aid, kind):
    # This helper is private and reached only after full current source gates.
    exists = c.execute(select(delivery_graph_requests.c.request_key).where(
        delivery_graph_requests.c.app_id == job["id"],
        delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind == kind,
        delivery_graph_requests.c.request_key == aid)).first()
    if exists is None:
        raise DomainError("OUTCOME_UNKNOWN", "Original execution has no complete body archive")
    body, saved = pair(c, user, job["id"], kind, aid, BodyArchive)
    require(saved == body.model_dump() and body.run_id == job["id"] and body.attempt_id == aid
            and body.principal_id == user == job["principal_id"]
            and body.project_id == job["project_id"] and body.runtime_id == job["runtime_id"]
            and body.phase == ("RESERVED_REQUEST" if kind == REQUEST else "RECEIVED_DECODED_BODY"))
    anchors = c.execute(select(events.c.data).where(events.c.run_id == job["id"],
        events.c.kind == ("NS_WIRE_ARCHIVED" if kind == REQUEST else "NS_BODY_ARCHIVED"),
        events.c.data["attempt_id"].as_string() == aid)).scalars().all()
    require(anchors == [dict(attempt_id=aid, archive_fingerprint=fingerprint(body.model_dump()))])
    require(body.extent == ("COMPLETE_BODY" if body.received_complete else "RECEIVED_PREFIX"))
    if not body.received_complete or body.omission != "NONE" or body.body_b64 is None:
        raise DomainError("OUTCOME_UNKNOWN", "Original body archive is incomplete")
    try:
        payload = base64.b64decode(body.body_b64, validate=True)
    except ValueError as error:
        raise DomainError("VERSION_CONFLICT", "Body archive encoding changed") from error
    require(0 < len(payload) == body.byte_count <= MAX_BODY_BYTES
            and hashlib.sha256(payload).hexdigest() == body.sha256
            and base64.b64encode(payload).decode("ascii") == body.body_b64)
    return body, payload


@dataclass(frozen=True)
class ResolvedSourceArchive:
    """Server-private bytes; only public_receipt is returned by HTTP."""

    public_receipt: dict
    request_bodies: tuple[bytes, bytes]
    response_bodies: tuple[bytes, bytes]


def _source_prefix(store, c, user, contract, approval_key):
    from . import natural_live_admission as gate
    from . import natural_trial_budget as budget

    approval = gate._approved(store, c, user, contract, approval_key)
    ledger = budget.audit(store, c, user, budget.scope_for(contract, approval_key))["ledger"]
    source_id = ledger["stage_runs"].get("source")
    require(not ledger["halted"] and source_id is not None)
    require(gate._keys(c, user, gate.entity(contract), gate.PHASE) <= {"source", "cold"})
    current, job, source_proof = gate._source_stage_current(store, c, user, contract, source_id)
    accepted = gate._saved(c, user, gate.entity(contract), gate.PHASE, "source", gate.StageApproveInput)
    require(accepted.approval_key == approval_key and accepted.authority == current
            and accepted.expected_authority_fingerprint == fingerprint(current.model_dump())
            and job["status"] == "SUCCEEDED" and not job["cancel_intent"])
    return approval, ledger, current, job, source_proof


def _source_bodies(c, user, contract, job, ledger):
    from . import natural_live_admission as gate
    from .goal_applications import response_archive
    from .model import normalize_usage

    source_id = job["id"]
    rows = c.execute(select(attempts).where(attempts.c.run_id == source_id)).mappings().all()
    slots = [s for s in ledger["slots"] if s["reservation"]["stage"] == "source"]
    require(len(rows) == len(slots) == 2
            and {r["id"] for r in rows} == {s["reservation"]["request_key"] for s in slots})
    expected_ids = {r["id"] for r in rows}
    for kind in (REQUEST, RESPONSE):
        keys = gate._keys(c, user, source_id, kind)
        if not expected_ids <= keys:
            raise DomainError("OUTCOME_UNKNOWN", "Original execution has no complete body archive")
        require(keys == expected_ids, "Source archive contains an unrelated Attempt")
    by_id = {r["id"]: r for r in rows}
    requests, responses, public = [], [], []
    for slot in slots:
        row = by_id[slot["reservation"]["request_key"]]
        require(row["mode"] == "MOCK" and row["status"] == "VERIFIED"
                and row["request_model"] == row["response_model"] == contract.model
                and slot["accepted"] is True and slot["settlement"] is not None)
        request, wire = _read(c, user, job, row["id"], REQUEST)
        response, received = _read(c, user, job, row["id"], RESPONSE)
        raw = strict_json(received, MAX_BODY_BYTES)
        original, canonical = response_archive(raw)
        usage = normalize_usage(raw)
        envelope = strict_json(wire, MAX_BODY_BYTES)
        require(isinstance(envelope, dict) and envelope.get("model") == contract.model
                and envelope.get("stream") is False
                and type(envelope.get("max_tokens")) is int
                and 0 < envelope["max_tokens"] <= contract.caps.max_output_tokens
                and row["parameters"]["natural_spec_wire"] == dict(sha256=request.sha256,
                    bytes=len(wire), characters=len(wire.decode("utf-8")))
                and slot["reservation"]["wire_sha256"] == request.sha256
                and slot["reservation"]["wire_bytes"] == len(wire)
                and original is not None and row["response"] == dict(received_raw=original,
                    raw_evidence=canonical)
                and response.canonical_sha256 == canonical["sha256"]
                and usage == row["usage"] and usage["status"] == "known"
                and slot["settlement"]["response_sha256"] == canonical["sha256"]
                and slot["settlement"]["response_ascii_bytes"] == canonical["bytes"]
                and all(slot["settlement"][k] == usage["tokens"][k] for k in
                    ("prompt_tokens", "completion_tokens", "total_tokens")))
        requests.append(wire)
        responses.append(received)
        public.append(dict(attempt_id=row["id"], request_bytes=len(wire),
            request_sha256=request.sha256, decoded_body_bytes=len(received),
            decoded_body_sha256=response.sha256, canonical_ascii_bytes=canonical["bytes"],
            canonical_ascii_sha256=canonical["sha256"]))
    return requests, responses, public


@controlled
def _resolve_source_before_extraction(store, c, user, contract, approval_key):
    """Full same-transaction successful source proof before an extraction exists."""
    from . import natural_live_admission as gate
    from . import pa_spec_apps as spec

    require(store.test_only and store.sqlite and c.in_transaction())
    require(type(contract) is gate.PBTrialContract
            and gate.PBTrialContract.model_validate(contract.model_dump()) == contract)
    with store.proof_authorities(c) as authorities:
        approval, ledger, current, job, proof = _source_prefix(store, c, user, contract, approval_key)
        requests, responses, public = _source_bodies(c, user, contract, job, ledger)
        gate._approved(store, c, user, contract, approval_key)
        require(spec.job_scope_gate(store, c, user, job["id"]))
        store.recheck_proof_authorities(c, {"_call_authorities": tuple(sorted(authorities))})
        require(time.time() < contract.expires_at)
        receipt = dict(verification="ACTUAL_MOCK_ARCHIVE_NOT_LIVE_VERIFIED",
            trial_fingerprint=fingerprint(contract.model_dump()),
            source_run_id=job["id"], source_app_id=current.app_id,
            source_proof_fingerprint=fingerprint(proof),
            source_recipe_fingerprint=proof["recipe_fingerprint"],
            approval_fingerprint=fingerprint(approval.model_dump()), attempts=public,
            live_allowed=False, dispatch_authorized=False)
        return ResolvedSourceArchive(receipt, (requests[0], requests[1]), (responses[0], responses[1]))


@controlled
def resolve_trial_source(store, user, contract, approval_key):
    from . import natural_live_admission as gate

    require(store.test_only and store.sqlite, "Only offline source archive verification is implemented")
    require(type(contract) is gate.PBTrialContract)
    require(gate.PBTrialContract.model_validate(contract.model_dump()) == contract)
    with store.tx() as c:
        return _resolve_trial_source(store, c, user, contract, approval_key)


@controlled
def _resolve_trial_source(store, c, user, contract, approval_key):
    from . import natural_live_admission as gate
    from . import pa_spec_apps as spec
    from . import pb_natural_specs as pb

    require(store.test_only and store.sqlite, "Only offline source archive verification is implemented")
    require(type(contract) is gate.PBTrialContract)
    exact = gate.PBTrialContract.model_validate(contract.model_dump())
    require(exact == contract)
    require(c.in_transaction(), "Original source proof requires the caller transaction")
    with store.proof_authorities(c) as authorities:
        # Active original approval, both current material/Goals and all identities
        # precede any private source or archive body. No caller evidence resolver.
        approval, ledger, current, job, source_proof = _source_prefix(store, c, user, contract, approval_key)
        source_id, limits = job["id"], gate._limits(contract)

        # Select scalar identity first, then the existing full extraction gates.
        ids = c.execute(select(delivery_graph_requests.c.app_id).join(app_drafts,
            app_drafts.c.id == delivery_graph_requests.c.app_id).where(
            app_drafts.c.project_id == contract.project_id,
            delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.kind == pb.EXTRACT,
            delivery_graph_requests.c.request_key == contract.extraction_request_key)).scalars().all()
        require(len(ids) == 1 and spec.scope_gate(store, c, user, ids[0]))
        draft = c.execute(select(app_drafts).where(app_drafts.c.id == ids[0],
            app_drafts.c.project_id == contract.project_id)).mappings().one()
        _, _, target, goal = pb.verify(store, c, user, draft, limits)
        extracted, _ = pair(c, user, draft["id"], pb.EXTRACT,
                            contract.extraction_request_key, pb.ExtractInput)
        cold = contract.bindings[1]
        require(extracted.review.source_run_id == source_id
                and extracted.review.request_key == contract.extraction_request_key
                and extracted.review.recipe == contract.extraction_recipe
                and extracted.review.expected_source_proof_fingerprint == fingerprint(source_proof)
                and target["resource_id"] == cold.resource_id and target["hash"] == cold.source_hash
                and target["content"] == cold.content
                and goal == dict(card_id=cold.card_id, version=cold.goal_version,
                    fingerprint=cold.goal_fingerprint, snapshot=cold.goal_snapshot.model_dump()))
        requests, responses, public = _source_bodies(c, user, contract, job, ledger)

        receipt = dict(version=VERSION, verification="ACTUAL_MOCK_ARCHIVE_NOT_LIVE_VERIFIED",
            trial_fingerprint=fingerprint(contract.model_dump()),
            approval_fingerprint=fingerprint(approval.model_dump()), source_run_id=source_id,
            source_app_id=current.app_id, extraction_app_id=draft["id"],
            extraction_request_key=contract.extraction_request_key,
            source_proof_fingerprint=fingerprint(source_proof),
            extraction_recipe_fingerprint=fingerprint(contract.extraction_recipe.model_dump()),
            cold_goal_fingerprint=cold.goal_fingerprint, attempts=public,
            live_allowed=False, dispatch_authorized=False, new_model_requests=0,
            new_reservations=0, project_writes=0, formal_publication_enabled=False)
        gate._approved(store, c, user, contract, approval_key)
        require(spec.job_scope_gate(store, c, user, source_id)
                and spec.scope_gate(store, c, user, draft["id"]))
        store.recheck_proof_authorities(c, {"_call_authorities": tuple(sorted(authorities))})
        require(time.time() < contract.expires_at, "Original trial approval expired during source proof")
        return ResolvedSourceArchive(receipt, (requests[0], requests[1]), (responses[0], responses[1]))
