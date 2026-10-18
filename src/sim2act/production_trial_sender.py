"""Uninstalled sender coordination through the existing synthetic Intern adapter.

Only test-only SQLite, original mock settings and an exact MockTransport can
exercise this path. It installs no API/Worker/source/sender or LIVE permission.
Marker is a may-have-sent record, not a reusable dispatch permit. The gap after
the final DB guard and before transport IO cannot be fenced by a DB transaction.
"""

import base64
import hashlib
import json
from typing import Literal

import httpx
from pydantic import Field, ValidationError
from sqlalchemy import select

from . import production_trial_journal as journal
from . import production_trial_policy as policy
from .config import Settings
from .contracts import strict_json
from .db import Store, runs
from .db import delivery_graph_requests as rows
from .errors import DomainError
from .goal_applications import response_archive
from .goal_planner import configured_provider
from .model import (
    CapturedResponse,
    InternModel,
    normalize_usage,
    parse_response,
    returned_model_identity,
)
from .worker import Worker

CAPTURE = "uninstalled-production-trial-capture.v1"
_SERVER_SOURCE = object()


class Capture(policy.evidence.EvidenceData):
    provenance: Literal["UNINSTALLED_SYNTHETIC_ADAPTER"] = "UNINSTALLED_SYNTHETIC_ADAPTER"
    raw_sha256: str = Field(pattern=policy.gate.HASH)
    raw_bytes: int = Field(ge=0, le=131072)
    body_b64: str | None = Field(default=None, max_length=43692)
    complete: bool
    received_response: bool
    omission: Literal["NONE", "EMPTY", "OVERSIZE"]
    canonical_sha256: str | None = Field(default=None, pattern=policy.gate.HASH)
    canonical_ascii_bytes: int | None = Field(default=None, ge=0)
    response_verdict: Literal["VALID_PROTOCOL", "UNKNOWN_OR_REJECTED"]
    outcome: policy.Outcome


class Receipt(policy.evidence.EvidenceData):
    journal: journal.Receipt
    capture_sha256: str | None = Field(default=None, pattern=policy.gate.HASH)
    capture_bytes: int | None = Field(default=None, ge=0)
    response_verdict: Literal["VALID_PROTOCOL", "UNKNOWN_OR_REJECTED"] | None = None
    may_have_sent: bool
    adapter_entered: bool
    business_accepted: Literal[False] = False
    scope: Literal["UNINSTALLED_OFFLINE_SENDER_ONLY"] = "UNINSTALLED_OFFLINE_SENDER_ONLY"
    live_allowed: Literal[False] = False
    dispatch_authorized: Literal[False] = False
    real_source_verified: Literal[False] = False


def _require(ok, code="LIVE_BLOCKED"):
    if not ok:
        raise DomainError(code, "Uninstalled offline sender boundary")


def _binding(worker):
    _require(type(worker) is Worker and type(worker.s) is Settings and type(worker.store) is Store)
    _require(
        worker.store.test_only
        and worker.store.sqlite
        and worker.s.mode == "mock"
        and worker.s.live_enabled is False
        and worker.s.token == ""
        and type(worker.goal_planner_transport) is httpx.MockTransport
    )


def _wire(contract, wire):
    _require(type(wire) is bytes and 0 < len(wire) <= contract.caps.max_wire_bytes)
    body = strict_json(wire, contract.caps.max_wire_bytes)
    _require(
        type(body) is dict
        and set(body) == {"model", "messages", "tools", "stream", "max_tokens"}
        and body["model"] == contract.model == "intern-s2"
        and body["stream"] is False
        and type(body["max_tokens"]) is int
        and 1 <= body["max_tokens"] <= contract.caps.max_output_tokens
        and type(body["messages"]) is list
        and bool(body["messages"])
        and type(body["tools"]) is list
    )


def _loaded(store, c, user, contract, key, item, wire):
    original, scope, request, quota_request, entity = journal._context(
        store, c, user, contract, key, item.account_id
    )
    journal._history_anchor(c, user, scope, request)
    _, cursor, quota_revision = journal._quota(c, quota_request, entity, create=False)
    _, state, revision = journal._ledger(c, scope, request, cursor, quota_revision)
    policy._bound(store, c, user, original, key, state, cursor, item, wire)
    slot = next((s for s in state.slots if s.identity.attempt_id == item.attempt_id), None)
    _require(slot is not None and slot.identity == item, "VERSION_CONFLICT")
    owner = (
        c.execute(
            select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id)
            .where(runs.c.id == item.run_id)
            .with_for_update()
        )
        .mappings()
        .first()
    )
    _require(
        owner is not None
        and owner["principal_id"] == user
        and owner["project_id"] == contract.project_id
        and owner["runtime_id"] == item.runtime_id,
        "PERMISSION_DENIED",
    )
    return original, state, cursor, slot, revision, quota_revision


def _capture_request(item):
    return dict(namespace=CAPTURE, identity=item.model_dump(mode="json"))


def _captured(c, user, item):
    prior = journal._pair(c, user, item.run_id, CAPTURE, item.attempt_id)
    if prior is None:
        return None
    _require(prior["request"] == _capture_request(item), "VERSION_CONFLICT")
    try:
        capture = Capture.model_validate_json(json.dumps(prior["response"]))
    except (ValidationError, TypeError, ValueError):
        _require(False, "VERSION_CONFLICT")
    if capture.body_b64 is not None:
        try:
            body = base64.b64decode(capture.body_b64, validate=True)
        except ValueError:
            _require(False, "VERSION_CONFLICT")
        _require(
            0 < len(body) == capture.raw_bytes <= 32768
            and hashlib.sha256(body).hexdigest() == capture.raw_sha256
            and base64.b64encode(body).decode("ascii") == capture.body_b64
            and capture.omission == "NONE",
            "VERSION_CONFLICT",
        )
        _require(
            capture == _derive(body, capture.complete, capture.received_response),
            "VERSION_CONFLICT",
        )
    else:
        _require(
            capture.omission == ("EMPTY" if capture.raw_bytes == 0 else "OVERSIZE")
            and (capture.raw_bytes == 0 or capture.raw_bytes > 32768),
            "VERSION_CONFLICT",
        )
        _require(
            capture.response_verdict == "UNKNOWN_OR_REJECTED"
            and capture.outcome.outcome == "UNKNOWN",
            "VERSION_CONFLICT",
        )
        if capture.raw_bytes == 0:
            _require(
                capture == _derive(b"", capture.complete, capture.received_response),
                "VERSION_CONFLICT",
            )
    _require(
        capture.outcome.response_sha256 == capture.raw_sha256
        and capture.outcome.response_ascii_bytes
        == (
            capture.canonical_ascii_bytes
            if capture.canonical_ascii_bytes is not None
            else capture.raw_bytes
        ),
        "VERSION_CONFLICT",
    )
    return capture


def _receipt(saved, item, capture, *, adapter_entered=False):
    slot = next(s for s in saved.ledger.slots if s.identity == item)
    return Receipt(
        journal=saved,
        capture_sha256=None if capture is None else capture.raw_sha256,
        capture_bytes=None if capture is None else capture.raw_bytes,
        response_verdict=None if capture is None else capture.response_verdict,
        may_have_sent=slot.attempted,
        adapter_entered=adapter_entered,
    )


def _history(store, user, contract, key, item, wire):
    with store.tx() as c:
        _, state, cursor, slot, revision, quota_revision = _loaded(
            store, c, user, contract, key, item, wire
        )
        # Original owned journal state precedes any private capture body read.
        capture = _captured(c, user, item)
        if capture is None:
            _require(slot.settlement is None, "OUTCOME_UNKNOWN")
        else:
            _require(slot.attempted and slot.settlement == capture.outcome, "VERSION_CONFLICT")
        return _receipt(
            journal._receipt(state, cursor, revision, quota_revision, duplicate=True), item, capture
        )


def _derive(payload, complete, received):
    _require(type(payload) is bytes and len(payload) <= 131072 and type(complete) is bool)
    raw = None
    try:
        raw = strict_json(payload, 131072)
    except DomainError:
        pass
    usage = normalize_usage(raw)["tokens"] or {}
    canonical, metadata = response_archive(raw)
    valid = False
    if (
        received
        and complete
        and 0 < len(payload) <= 32768
        and type(raw) is dict
        and canonical is not None
    ):
        try:
            valid = returned_model_identity("intern-s2", raw.get("model"))["verdict"] == "ACCEPTED"
            parse_response(raw)  # Existing generic protocol, never business/tool execution.
        except DomainError:
            valid = False
    outcome = policy.Outcome(
        outcome="RECEIVED" if valid else "UNKNOWN",
        response_sha256=hashlib.sha256(payload).hexdigest(),
        response_ascii_bytes=metadata["bytes"]
        if metadata and "bytes" in metadata
        else len(payload),
        **{key: usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
    )
    omission = "EMPTY" if not payload else "OVERSIZE" if len(payload) > 32768 else "NONE"
    return Capture(
        raw_sha256=outcome.response_sha256,
        raw_bytes=len(payload),
        body_b64=base64.b64encode(payload).decode("ascii") if omission == "NONE" else None,
        complete=complete,
        received_response=received,
        omission=omission,
        canonical_sha256=metadata.get("sha256") if metadata else None,
        canonical_ascii_bytes=metadata.get("bytes") if metadata else None,
        response_verdict="VALID_PROTOCOL" if valid else "UNKNOWN_OR_REJECTED",
        outcome=outcome,
    )


def _receive(
    store,
    user,
    contract,
    key,
    item,
    wire,
    source,
    expected_revision,
    payload,
    complete,
    received,
    *,
    _server_source=False,
    _business=None,
):
    _require(type(store) is Store and store.test_only and store.sqlite)
    capture = _derive(payload, complete, received)
    with store.tx() as c:
        original, _, _, slot, revision, _ = _loaded(store, c, user, contract, key, item, wire)
        _require(slot.attempted, "OUTCOME_UNKNOWN")
        if _server_source:
            from .production_trial_source import load_offline

            source = load_offline(store, c, user, original, key, item.account_id).source
        prior = _captured(c, user, item)
        if prior is not None:
            _require(prior == capture and slot.settlement == capture.outcome, "VERSION_CONFLICT")
            saved = journal._apply_in_transaction(
                store,
                c,
                user,
                original,
                key,
                item,
                wire,
                source,
                expected_revision,
                "settle",
                capture.outcome,
            )
            return _receipt(saved, item, prior, adapter_entered=True)
        _require(slot.settlement is None and revision == expected_revision, "VERSION_CONFLICT")
        journal._cas_pair(
            c,
            user,
            item.run_id,
            CAPTURE,
            item.attempt_id,
            None,
            journal._snapshot(_capture_request(item), capture.model_dump(mode="json")),
        )
        saved = journal._apply_in_transaction(
            store,
            c,
            user,
            original,
            key,
            item,
            wire,
            source,
            expected_revision,
            "settle",
            capture.outcome,
        )
        if _business is not None:
            from .pa_trial_dispatch import _journal_received
            binding, run = _business
            _journal_received(store, c, binding, run, item, wire, payload, complete)
        return _receipt(saved, item, capture, adapter_entered=True)


def _source_history(store, user, contract, key, item, wire):
    """An original owned key never needs a source read or new send authority."""
    with store.tx() as c:
        original, scope, request, quota_request, entity = journal._context(
            store, c, user, contract, key, item.account_id
        )
        anchors = c.execute(
            select(rows.c.kind).where(
                rows.c.principal_id == user,
                rows.c.app_id == scope.project_id,
                rows.c.kind.in_([journal.KIND, journal.KIND + "_seal"]),
                rows.c.request_key == scope.trial_key,
            )
        ).all()
        if not anchors:
            return None
        journal._history_anchor(c, user, scope, request)
        _, cursor, quota_revision = journal._quota(c, quota_request, entity, create=False)
        _, state, _ = journal._ledger(c, scope, request, cursor, quota_revision)
        policy._bound(store, c, user, original, key, state, cursor, item, wire)
        slot = next((s for s in state.slots if s.identity.attempt_id == item.attempt_id), None)
        if slot is None:
            return None
        _require(slot.identity == item, "VERSION_CONFLICT")
    return _history(store, user, original, key, item, wire)


def dispatch_from_source_offline(worker, contract, key, identity, wire, *, expected_revision):
    """Fixed server fixture loader; no source object, selector or callback input."""
    return _dispatch(
        worker, contract, key, identity, wire, _SERVER_SOURCE, expected_revision=expected_revision
    )


def dispatch_offline(worker, contract, key, identity, wire, source, *, expected_revision):
    """Original synthetic data path, still uninstalled and not a source verifier."""
    return _dispatch(
        worker, contract, key, identity, wire, source, expected_revision=expected_revision
    )


def _dispatch_business(worker, binding, run, identity, wire, original_guard, provider,
                       *, expected_revision):
    """Private continuation of the existing original controller call only."""
    from .pa_trial_dispatch import JournalTrialBinding
    from .pa_trial_dispatch import _binding as trial_binding
    _require(type(binding) is JournalTrialBinding and trial_binding(worker) is binding)
    return _dispatch(worker, binding.contract, binding.approval_key, identity, wire,
        _SERVER_SOURCE, expected_revision=expected_revision,
        _business=(binding, run, original_guard, provider))


def _dispatch(worker, contract, key, identity, wire, source, *, expected_revision, _business=None):
    """One explicit synthetic exchange; every original key retry is history only."""
    _binding(worker)
    store, settings, transport, worker_id = (
        worker.store,
        worker.s,
        worker.goal_planner_transport,
        worker.id,
    )
    engine = store.engine

    def same_binding():
        _binding(worker)
        if _business is not None:
            from .pa_trial_dispatch import _binding as trial_binding
            _require(trial_binding(worker) is _business[0])
        _require(
            worker.store is store
            and worker.s is settings
            and worker.goal_planner_transport is transport
            and worker.id == worker_id
            and store.engine is engine
        )

    _require(
        type(contract)
        in (policy.gate.TrialContract, policy.gate.TrialContractV2, policy.gate.PBTrialContract)
    )
    item = policy._typed(identity, policy.ReservationIdentity)
    server_source = source is _SERVER_SOURCE
    supplied = None if server_source else policy._typed(source, policy.SourceVerificationResult)
    original, _ = policy._requirements(contract.principal_id, contract, key)
    _require(
        worker.s.model == original.model
        and worker.s.max_output_tokens == original.caps.max_output_tokens
        and worker.s.quota_subject == original.quota_subject
    )
    _wire(original, wire)
    user = original.principal_id
    if worker_id != item.worker_id:
        # A restarted worker may inspect the original key, never inherit its send.
        _require(_business is None, "OUTCOME_UNKNOWN")
        return _history(store, user, original, key, item, wire)
    if server_source:
        prior = _source_history(store, user, original, key, item, wire)
        if prior is not None:
            _require(_business is None, "OUTCOME_UNKNOWN")
            return prior

    def transition(operation, revision):
        if server_source:
            from .production_trial_source import load_offline

            with store.tx() as c:
                current_source = load_offline(store, c, user, original, key, item.account_id).source
                return journal._apply_in_transaction(
                    store, c, user, original, key, item, wire, current_source, revision, operation
                ), current_source
        action = journal.reserve if operation == "reserve" else journal.record_attempt
        return action(
            store, user, original, key, item, wire, supplied, expected_revision=revision
        ), supplied

    same_binding()
    reserved, supplied = transition("reserve", expected_revision)
    if reserved.duplicate:
        _require(_business is None, "OUTCOME_UNKNOWN")
        return _history(store, user, original, key, item, wire)
    same_binding()
    marked, supplied = transition("record_attempt", reserved.revision)
    if marked.duplicate:
        _require(_business is None, "OUTCOME_UNKNOWN")
        return _history(store, user, original, key, item, wire)
    same_binding()
    provider = configured_provider(worker) if _business is None else _business[3]
    _require(type(provider) is InternModel and provider.transport is transport)
    token = "synthetic-offline-planner"
    if _business is not None:
        params = provider.settings
        token = ("synthetic-offline-planner" if item.stage == "generate"
                 else "synthetic-offline-natural-spec")
        _require(params.mode == "mock" and params.live_enabled is True and params.token == token
            and params.model == original.model and params.quota_subject == original.quota_subject
            and params.max_output_tokens == strict_json(wire, 32768)["max_tokens"]
            and 0 < params.max_output_tokens <= original.caps.max_output_tokens
            and 0 < params.run_seconds <= original.caps.run_seconds)

    def guard(request):
        same_binding()
        controller = None if _business is None else _business[2](request)
        same_binding()
        _require(
            worker.goal_planner_transport is transport
            and worker.id == item.worker_id
            and provider.transport is transport
            and request.method == "POST"
            and str(request.url) == original.endpoint == InternModel.ENDPOINT
            and request.content == wire
            and request.headers.get("Authorization") == "Bearer " + token
        )
        with store.tx() as c:
            current, state, _, slot, _, _ = _loaded(store, c, user, original, key, item, wire)
            _require(
                slot.attempted and slot.settlement is None and not state.halted, "OUTCOME_UNKNOWN"
            )
            current_source = supplied
            if server_source:
                from .production_trial_source import load_offline

                current_source = load_offline(store, c, user, current, key, item.account_id).source
            _, deadline = policy._fresh(store, c, user, current, key, state, item, current_source)
            if controller is not None:
                _require(type(controller) is dict and set(controller) == {"deadline"})
                deadline = min(deadline, controller["deadline"])
            return dict(deadline=deadline)

    payload, complete, received = b"", False, False
    failure = None
    try:
        captured = provider.request_serialized_captured(wire, guard)
        _require(type(captured) is CapturedResponse and type(captured.body) is bytes)
        payload, complete, received = captured.body, True, True
    except DomainError as error:
        failure = error
        body = getattr(error, "_received_body", None)
        if type(body) is bytes:
            payload, complete = body, getattr(error, "_received_body_complete", False) is True
    _require(store.engine is engine)
    saved = _receive(
        store,
        user,
        original,
        key,
        item,
        wire,
        supplied,
        marked.revision,
        payload,
        complete,
        received,
        _server_source=server_source,
        _business=None if _business is None else _business[:2],
    )
    if _business is None:
        return saved
    try:
        if failure is not None:
            raise failure
        same_binding()
        slot = next(s for s in saved.journal.ledger.slots if s.identity == item)
        _require(slot.accepted and saved.adapter_entered and received, "OUTCOME_UNKNOWN")
        # Only this exchange's actual bytes, never a journal history response.
        return CapturedResponse(strict_json(payload, 131072), payload)
    except DomainError as error:
        error._received_body = payload
        error._received_body_complete = complete
        try:
            error._received_response = strict_json(payload, 131072)
        except DomainError:
            pass
        raise
