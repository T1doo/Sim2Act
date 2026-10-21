"""Bounded private execution bodies and exact original-trial source reads.

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
    provenance: Literal["OFFLINE_MOCKTRANSPORT", "SPEC_PRODUCTION_CONTROLLER"] = "OFFLINE_MOCKTRANSPORT"
    byte_count: int = Field(strict=True, ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    received_complete: bool
    extent: Literal["COMPLETE_BODY", "RECEIVED_PREFIX"]
    omission: Literal["NONE", "OVERSIZE", "EMPTY"]
    body_b64: str | None = Field(default=None, max_length=43692)
    canonical_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


def _body(job, aid, payload, complete, canonical_sha256, kind, *, _production=False):
    omission: Literal["NONE", "OVERSIZE", "EMPTY"] = (
        "EMPTY" if not payload else "OVERSIZE" if len(payload) > MAX_BODY_BYTES else "NONE")
    return BodyArchive(run_id=job["id"], attempt_id=aid,
        principal_id=job["principal_id"], project_id=job["project_id"], runtime_id=job["runtime_id"],
        phase="RESERVED_REQUEST" if kind == REQUEST else "RECEIVED_DECODED_BODY",
        provenance="SPEC_PRODUCTION_CONTROLLER" if _production else "OFFLINE_MOCKTRANSPORT",
        byte_count=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
        received_complete=complete, extent="COMPLETE_BODY" if complete else "RECEIVED_PREFIX",
        omission=omission,
        body_b64=base64.b64encode(payload).decode("ascii") if omission == "NONE" else None,
        canonical_sha256=canonical_sha256)


def receipt_owner(c, job, aid, request_body, *, reserved=False):
    from .spec_production import evidence_mode
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
            and identity["runtime_id"] == job["runtime_id"] and identity["mode"] == evidence_mode(c, job)
            and identity["wire_sha256"] == hashlib.sha256(request_body).hexdigest()
            and identity["wire_bytes"] == len(request_body), "Body receipt owner or reserved wire changed")
    return identity


def _write(store, c, job, aid, payload, complete, canonical_sha256, kind, request_body):
    from .spec_production import evidence_mode
    require((store.test_only and store.sqlite or evidence_mode(c, job) == "LIVE") and type(payload) is bytes
            and type(request_body) is bytes and type(complete) is bool,
            "Body capture requires isolated offline SQLite")
    identity = receipt_owner(c, job, aid, request_body, reserved=kind == REQUEST)
    production = identity["mode"] == "LIVE"
    body = _body(job, aid, payload, complete, canonical_sha256, kind, _production=production)
    if kind == RESPONSE:
        request = _body(job, aid, request_body, True, None, REQUEST,
                        _production=production).model_dump()
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


def _read(c, user, job, aid, kind, *, _guard=None):
    from . import natural_live_admission as gate
    from .spec_production import evidence_mode
    exists = gate._trial_result(gate._trial_result(c.execute(select(delivery_graph_requests.c.request_key).where(delivery_graph_requests.c.app_id == job['id'], delivery_graph_requests.c.principal_id == user, delivery_graph_requests.c.kind == kind, delivery_graph_requests.c.request_key == aid)), _guard).first(), _guard)
    if exists is None:
        raise DomainError('OUTCOME_UNKNOWN', 'Original execution has no complete body archive')
    body, saved = gate._trial_result(pair(c, user, job['id'], kind, aid, BodyArchive), _guard)
    if _guard is not None:
        _guard = gate._trial_typed_guard(_guard, [(BodyArchive, body, saved)])
        _guard()
    require(saved == gate._trial_result(body.model_dump(), _guard) and body.run_id == job['id'] and (body.attempt_id == aid) and (body.principal_id == user == job['principal_id']) and (body.project_id == job['project_id']) and (body.runtime_id == job['runtime_id']) and (body.provenance == ('SPEC_PRODUCTION_CONTROLLER' if gate._trial_result(evidence_mode(c, job), _guard) == 'LIVE' else 'OFFLINE_MOCKTRANSPORT')) and (body.phase == ('RESERVED_REQUEST' if kind == REQUEST else 'RECEIVED_DECODED_BODY')))
    anchors = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(events.c.data).where(events.c.run_id == job['id'], events.c.kind == ('NS_WIRE_ARCHIVED' if kind == REQUEST else 'NS_BODY_ARCHIVED'), events.c.data['attempt_id'].as_string() == aid)), _guard).scalars(), _guard).all(), _guard)
    return (body, gate._trial_result(_body_payload_from_facts(body, anchors, aid, _guard=_guard), _guard))


def _body_payload_from_facts(body, anchors, aid, *, _guard=None):
    """Decode after exists/pair/owner/mode checks, using the complete anchor list.

    Caller retains current scope/permissions and exact same-transaction identity
    checks. Bytes and completeness are evidence, never execution authority.
    """
    from . import natural_live_admission as gate
    require(anchors == [dict(attempt_id=aid, archive_fingerprint=gate._trial_result(fingerprint(gate._trial_result(body.model_dump(), _guard)), _guard))])
    require(body.extent == ('COMPLETE_BODY' if body.received_complete else 'RECEIVED_PREFIX'))
    if not body.received_complete or body.omission != 'NONE' or body.body_b64 is None:
        raise DomainError('OUTCOME_UNKNOWN', 'Original body archive is incomplete')
    try:
        payload = base64.b64decode(body.body_b64, validate=True)
    except ValueError as error:
        raise DomainError('VERSION_CONFLICT', 'Body archive encoding changed') from error
    payload = gate._trial_result(payload, _guard)
    require(0 < len(payload) == body.byte_count <= MAX_BODY_BYTES and gate._trial_result(gate._trial_result(hashlib.sha256(payload), _guard).hexdigest(), _guard) == body.sha256 and (gate._trial_result(gate._trial_result(base64.b64encode(payload), _guard).decode('ascii'), _guard) == body.body_b64))
    return payload


@dataclass(frozen=True)
class ResolvedSourceArchive:
    """Server-private bytes; only public_receipt is returned by HTTP."""

    public_receipt: dict
    request_bodies: tuple[bytes, bytes]
    response_bodies: tuple[bytes, bytes]


def _source_prefix(store, c, user, contract, approval_key):
    from . import natural_live_admission as gate
    from .pa_trial_dispatch import _pb_accounting, journal_stage_accounted

    approval = gate._approved(store, c, user, contract, approval_key)
    backend, ledger, source_id = _pb_accounting(store, c, user, contract, approval_key)
    require(source_id is not None)
    if backend is None:
        require(not ledger["halted"])
    require(gate._keys(c, user, gate.entity(contract), gate.PHASE) <= {"source", "cold"})
    current, job, source_proof = gate._source_stage_current(store, c, user, contract, source_id)
    accepted = gate._saved(c, user, gate.entity(contract), gate.PHASE, "source", gate.StageApproveInput)
    _source_accepted_from_facts(approval_key, accepted, current, job)
    if backend is not None:
        journal_stage_accounted(store, c, user, contract, approval_key, source_id, "source")
    return approval, ledger, current, job, source_proof


def _source_verification(ledger):
    from .production_trial_policy import Ledger
    return ("SPEC_PRODUCTION_CONTROLLER_ARCHIVE" if type(ledger) is Ledger
            else "ACTUAL_MOCK_ARCHIVE_NOT_LIVE_VERIFIED")


def _source_bodies(c, user, contract, job, ledger):
    source_id = job["id"]
    rows = c.execute(select(attempts).where(attempts.c.run_id == source_id)).mappings().all()
    return _source_bodies_from_rows(c, user, contract, job, ledger, rows)


def _source_slots_from_facts(rows, ledger, production, *, _guard=None):
    """Compare complete Attempt/slot multisets after current evidence-mode gating.

    The caller must fully validate the original ledger/accounting first; this
    projection is not _ledger, an approval or a fresh source check.
    """
    from . import natural_live_admission as gate
    if production:
        slots = [dict(reservation=dict(request_key=s.identity.attempt_id, wire_sha256=s.identity.wire_sha256, wire_bytes=s.identity.wire_bytes), accepted=s.accepted, settlement=None if s.settlement is None else gate._trial_result(s.settlement.model_dump(), _guard)) for s in ledger.slots if s.identity.stage == 'source']
    else:
        slots = [s for s in ledger['slots'] if s['reservation']['stage'] == 'source']
    require(len(rows) == len(slots) == 2 and {r['id'] for r in rows} == {s['reservation']['request_key'] for s in slots})
    return slots


def _source_keys_from_facts(expected_ids, keys, *, _guard=None):
    """Original missing-vs-extra error order for one complete archive key set."""
    if not expected_ids <= keys:
        raise DomainError('OUTCOME_UNKNOWN', 'Original execution has no complete body archive')
    require(keys == expected_ids, 'Source archive contains an unrelated Attempt')


def _source_exchange_from_facts(contract, row, slot, request, wire, response, received, production, *, _guard=None):
    """Original full byte/usage exchange check after both ordered archive reads.

    Requires complete source rows/slots, status/model checks and _read identity,
    seals, anchors and payload checks. Caller retains current permissions and
    role contract/caps; this leaf neither reads bodies nor authorizes a Run.
    """
    from . import natural_live_admission as gate
    from .goal_applications import response_archive
    from .model import normalize_usage
    raw = gate._trial_result(strict_json(received, MAX_BODY_BYTES), _guard)
    original, canonical = gate._trial_result(response_archive(raw), _guard)
    usage = gate._trial_result(normalize_usage(raw), _guard)
    envelope = gate._trial_result(strict_json(wire, MAX_BODY_BYTES), _guard)
    require(isinstance(envelope, dict) and envelope.get('model') == contract.model and (envelope.get('stream') is False) and (type(envelope.get('max_tokens')) is int) and (0 < envelope['max_tokens'] <= contract.caps.max_output_tokens) and (row['parameters']['natural_spec_wire'] == dict(sha256=request.sha256, bytes=len(wire), characters=len(gate._trial_result(wire.decode('utf-8'), _guard)))) and (slot['reservation']['wire_sha256'] == request.sha256) and (slot['reservation']['wire_bytes'] == len(wire)) and (original is not None) and (row['response'] == dict(received_raw=original, raw_evidence=canonical)) and (response.canonical_sha256 == canonical['sha256']) and (usage == row['usage']) and (usage['status'] == 'known') and (slot['settlement']['response_sha256'] == (response.sha256 if production else canonical['sha256'])) and (slot['settlement']['response_ascii_bytes'] == canonical['bytes']) and all((slot['settlement'][k] == usage['tokens'][k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'))))
    return canonical


@controlled
def _resolve_source_before_extraction(store, c, user, contract, approval_key):
    """Full same-transaction successful source proof before an extraction exists."""
    from . import natural_live_admission as gate
    from . import pa_spec_apps as spec

    require(c.in_transaction() and c.engine is store.engine)
    require(type(contract) is gate.PBTrialContract
            and gate.PBTrialContract.model_validate(contract.model_dump()) == contract)
    with store.proof_authorities(c) as authorities:
        approval, ledger, current, job, proof = _source_prefix(store, c, user, contract, approval_key)
        requests, responses, public = _source_bodies(c, user, contract, job, ledger)
        gate._approved(store, c, user, contract, approval_key)
        require(spec.job_scope_gate(store, c, user, job["id"]))
        store.recheck_proof_authorities(c, {"_call_authorities": tuple(sorted(authorities))})
        require(time.time() < contract.expires_at)
        receipt = dict(verification=_source_verification(ledger),
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

    require(type(contract) is gate.PBTrialContract)
    require(gate.PBTrialContract.model_validate(contract.model_dump()) == contract)
    with store.tx() as c:
        return _resolve_trial_source(store, c, user, contract, approval_key)


@controlled
def _resolve_trial_source(store, c, user, contract, approval_key):
    from . import natural_live_admission as gate
    from . import pa_spec_apps as spec
    from . import pb_natural_specs as pb

    require(type(contract) is gate.PBTrialContract)
    exact = gate.PBTrialContract.model_validate(contract.model_dump())
    require(exact == contract)
    require(c.in_transaction() and c.engine is store.engine,
            "Original source proof requires the caller transaction")
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
        _source_extraction_from_facts(contract, source_id, source_proof, extracted, target, goal)
        requests, responses, public = _source_bodies(c, user, contract, job, ledger)

        receipt = dict(version=VERSION, verification=_source_verification(ledger),
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


def _source_bodies_from_rows(c, user, contract, job, ledger, rows, *, _guard=None):
    from . import natural_live_admission as gate
    from .production_trial_policy import Ledger
    from .spec_production import evidence_mode
    source_id = job['id']
    production = type(ledger) is Ledger
    require(gate._trial_result(evidence_mode(c, job), _guard) == ('LIVE' if production else 'MOCK'))
    slots = gate._trial_result(_source_slots_from_facts(rows, ledger, production, _guard=_guard), _guard)
    expected_ids = {r['id'] for r in rows}
    for kind in (REQUEST, RESPONSE):
        keys = gate._trial_result(gate._keys(c, user, source_id, kind, **{'_guard': _guard} if _guard is not None else {}), _guard)
        gate._trial_result(_source_keys_from_facts(expected_ids, keys, _guard=_guard), _guard)
    by_id = {r['id']: r for r in rows}
    requests, responses, public = ([], [], [])
    for slot in slots:
        row = by_id[slot['reservation']['request_key']]
        gate._trial_result(_source_row_from_facts(contract, row, slot, production, _guard=_guard), _guard)
        request, wire = gate._trial_result(_read(c, user, job, row['id'], REQUEST, _guard=_guard), _guard)
        response, received = gate._trial_result(_read(c, user, job, row['id'], RESPONSE, _guard=_guard), _guard)
        canonical = gate._trial_result(_source_exchange_from_facts(contract, row, slot, request, wire, response, received, production, _guard=_guard), _guard)
        requests.append(wire)
        responses.append(received)
        public.append(dict(attempt_id=row['id'], request_bytes=len(wire), request_sha256=request.sha256, decoded_body_bytes=len(received), decoded_body_sha256=response.sha256, canonical_ascii_bytes=canonical['bytes'], canonical_ascii_sha256=canonical['sha256']))
    return (requests, responses, public)


def _source_extraction_from_facts(contract, source_id, source_proof, extracted, target, goal, *, _guard=None):
    from . import natural_live_admission as gate
    cold = contract.bindings[1]
    require(extracted.review.source_run_id == source_id and extracted.review.request_key == contract.extraction_request_key and (extracted.review.recipe == contract.extraction_recipe) and (extracted.review.expected_source_proof_fingerprint == gate._trial_result(fingerprint(source_proof), _guard)) and (target['resource_id'] == cold.resource_id) and (target['hash'] == cold.source_hash) and (target['content'] == cold.content) and (goal == dict(card_id=cold.card_id, version=cold.goal_version, fingerprint=cold.goal_fingerprint, snapshot=gate._trial_result(cold.goal_snapshot.model_dump(), _guard))))


def _graph_source_bodies(graph, store, c, user, contract, ledger, source_facts, *, _accounted_test=None):
    """Use full ordered NS reads from the actual accounted Source producer."""

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
    try:
        from . import natural_live_admission as gate
        _models: list[tuple[type, object, dict]] = []
        _guard = gate._trial_typed_guard(_parent_pin, _models)
        from .production_trial_policy import Ledger
        from .spec_production import evidence_mode
        _guard()
        gate._graph_trial_contract_models(graph, store, c, _models, contract)
        gate._graph_trial_journal_models(graph, store, c, _models, ledger)
        gate._graph_trial_accounted_models(graph, store, c, _models, source_facts, 'source')
        _guard()
        owned = None
        if _accounted_test is not None:
            from . import cold_accounted
            owned = cold_accounted._source_test_family(_accounted_test, graph)
        job, rows, chains, ns_reads = source_facts
        require(type(ledger) is Ledger and gate._trial_result(evidence_mode(c, job), _guard) == 'LIVE')
        slots = gate._trial_result(_source_slots_from_facts(rows, ledger, True, _guard=_guard), _guard)
        expected_ids = {r['id'] for r in rows}
        for kind in (REQUEST, RESPONSE):
            gate._trial_result(_source_keys_from_facts(expected_ids, gate._trial_result(gate._keys(c, user, job['id'], kind, **{'_guard': _guard} if _guard is not None else {}), _guard), _guard=_guard), _guard)
        require(len(rows) == len({r['id'] for r in rows}) == len(ns_reads) == len(chains) == 2)
        requests, responses, public = ([], [], [])
        for slot in slots:
            aid = slot['reservation']['request_key']
            own_rows = tuple((r for r in rows if r['id'] == aid))
            own_reads = tuple((r for r in ns_reads if r[0] == aid))
            own_chains = tuple((r for r in chains if r[3]['id'] == aid))
            require(len(own_rows) == len(own_reads) == len(own_chains) == 1)
            row, read, chain = (own_rows[0], own_reads[0], own_chains[0])
            _, request, wire, response, received = read
            gate._trial_result(_source_row_from_facts(contract, row, slot, True, _guard=_guard), _guard)
            require(chain[3] == row and chain[4] == wire and (chain[5] == received))
            canonical = gate._trial_result(_source_exchange_from_facts(contract, row, slot, request, wire, response, received, True, _guard=_guard), _guard)
            if owned is not None:
                cold_accounted._source_slot(owned, ledger, aid)
                cold_accounted._source_row(owned, aid)
                candidate = cold_accounted._source_exchange(owned, aid)
                require(dict(status=candidate.status, bytes=candidate.bytes, sha256=candidate.sha256) == canonical)
                _guard()
            requests.append(wire)
            responses.append(received)
            public.append(dict(attempt_id=aid, request_bytes=len(wire), request_sha256=request.sha256, decoded_body_bytes=len(received), decoded_body_sha256=response.sha256, canonical_ascii_bytes=canonical['bytes'], canonical_ascii_sha256=canonical['sha256']))
            _guard()
        return (tuple(requests), tuple(responses), public)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_resolve_trial_source(graph, store, c, user, contract, approval_key, ledger, source_stage_facts, source_proof, source_facts, extraction_facts, *, _accounted_test=None):
    """Assemble the original receipt from complete Source V + extraction V.

    source_stage_facts contains the complete original role facts; Authority is
    constructed here, never accepted as a DTO. source_proof is produced only
    by full Source receipt/result validation. The
    extraction tuple is (owned full draft,typed ExtractInput,full target,Goal)
    produced by the complete extraction/origin node, never by a paired P alone.
    """

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
        gate._graph_trial_stage_raw(graph, source_stage_facts)
        gate.require(source_proof is graph.inputs['cold-trial:complete']['source_proof'])
    try:
        from . import natural_live_admission as gate
        _models: list[tuple[type, object, dict]] = []
        _guard = gate._trial_typed_guard(_parent_pin, _models)
        from . import pa_spec_apps as spec
        from . import pb_natural_specs as pb
        _guard()
        gate._graph_trial_contract_models(graph, store, c, _models, contract)
        gate._graph_trial_journal_models(graph, store, c, _models, ledger)
        gate._graph_trial_stage_models(graph, store, c, _models, source_stage_facts)
        gate._graph_trial_accounted_models(graph, store, c, _models, source_facts, 'source')
        gate._graph_trial_extraction_models(graph, store, c, _models, extraction_facts)
        _guard()
        require(type(contract) is gate.PBTrialContract and gate._trial_result(gate.PBTrialContract.model_validate(gate._trial_result(contract.model_dump(), _guard)), _guard) == contract)
        with gate._trial_result(store.proof_authorities(c), _guard) as authorities:
            gate._trial_result(None, _guard)
            approval = gate._trial_result(gate._approved(store, c, user, contract, approval_key, **{'_guard': _guard} if _guard is not None else {}), _guard)
            gate._graph_trial_produced(graph, store, c, _models, gate.Approval, approval)
            require(gate._trial_result(gate._keys(c, user, gate._trial_result(gate.entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), gate.PHASE, **{'_guard': _guard} if _guard is not None else {}), _guard) <= {'source', 'cold'})
            current, job = gate._trial_result(gate._graph_stage_current(graph, store, c, user, contract, 'source', source_stage_facts), _guard)
            gate._graph_trial_produced(graph, store, c, _models, gate.StageAuthority, current)
            require(source_facts[0] == job)
            accepted = gate._trial_result(gate._saved(c, user, gate._trial_result(gate.entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), gate.PHASE, 'source', gate.StageApproveInput, **{'_guard': _guard} if _guard is not None else {}), _guard)
            gate._graph_trial_produced(graph, store, c, _models, gate.StageApproveInput, accepted)
            gate._trial_result(_source_accepted_from_facts(approval_key, accepted, current, job, _guard=_guard), _guard)
            draft, extracted, target, goal = extraction_facts
            ids = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(delivery_graph_requests.c.app_id).join(app_drafts, app_drafts.c.id == delivery_graph_requests.c.app_id).where(app_drafts.c.project_id == contract.project_id, delivery_graph_requests.c.principal_id == user, delivery_graph_requests.c.kind == pb.EXTRACT, delivery_graph_requests.c.request_key == contract.extraction_request_key)), _guard).scalars(), _guard).all(), _guard)
            require(ids == [draft['id']] and gate._trial_result(spec.scope_gate(store, c, user, draft['id'], _graph_read=graph), _guard))
            original, _ = gate._trial_result(pair(c, user, draft['id'], pb.EXTRACT, contract.extraction_request_key, pb.ExtractInput), _guard)
            require(original == extracted)
            gate._trial_result(_source_extraction_from_facts(contract, job['id'], source_proof, extracted, target, goal, _guard=_guard), _guard)
            requests, responses, public = gate._trial_result(_graph_source_bodies(graph, store, c, user, contract, ledger, source_facts, **{'_accounted_test': _accounted_test} if _accounted_test is not None else {}), _guard)
            cold = contract.bindings[1]
            receipt = dict(version=VERSION, verification=gate._trial_result(_source_verification(ledger), _guard), trial_fingerprint=gate._trial_result(fingerprint(gate._trial_result(contract.model_dump(), _guard)), _guard), approval_fingerprint=gate._trial_result(fingerprint(gate._trial_result(approval.model_dump(), _guard)), _guard), source_run_id=job['id'], source_app_id=current.app_id, extraction_app_id=draft['id'], extraction_request_key=contract.extraction_request_key, source_proof_fingerprint=gate._trial_result(fingerprint(source_proof), _guard), extraction_recipe_fingerprint=gate._trial_result(fingerprint(gate._trial_result(contract.extraction_recipe.model_dump(), _guard)), _guard), cold_goal_fingerprint=cold.goal_fingerprint, attempts=public, live_allowed=False, dispatch_authorized=False, new_model_requests=0, new_reservations=0, project_writes=0, formal_publication_enabled=False)
            gate._trial_result(gate._approved(store, c, user, contract, approval_key, **{'_guard': _guard} if _guard is not None else {}), _guard)
            require(gate._trial_result(spec.job_scope_gate(store, c, user, job['id'], _graph_read=graph), _guard) and gate._trial_result(spec.scope_gate(store, c, user, draft['id'], _graph_read=graph), _guard))
            gate._trial_result(store.recheck_proof_authorities(c, {'_call_authorities': tuple(sorted(authorities))}), _guard)
            require(gate._trial_result(time.time(), _guard) < contract.expires_at, 'Original trial approval expired during source proof')
            _guard()
            resolved = gate._trial_result(ResolvedSourceArchive(receipt, requests, responses), _guard)
        gate._trial_result(None, _guard)
        _guard()
        return resolved
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _source_accepted_from_facts(approval_key, accepted, current, job, *, _guard=None):
    from . import natural_live_admission as gate
    require(accepted.approval_key == approval_key and accepted.authority == current and (accepted.expected_authority_fingerprint == gate._trial_result(fingerprint(gate._trial_result(current.model_dump(), _guard)), _guard)) and (job['status'] == 'SUCCEEDED') and (not job['cancel_intent']))


def _source_row_from_facts(contract, row, slot, production, *, _guard=None):
    require(row['mode'] == ('LIVE' if production else 'MOCK') and row['status'] == 'VERIFIED' and (row['request_model'] == row['response_model'] == contract.model) and (slot['accepted'] is True) and (slot['settlement'] is not None))
