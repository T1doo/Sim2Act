"""Uninstalled sender coordination through the existing synthetic Intern adapter.

Only test-only SQLite, original mock settings and an exact MockTransport can
exercise this path. It installs no API/Worker/source/sender or LIVE permission.
Marker is a may-have-sent record, not a reusable dispatch permit. The gap after
the final DB guard and before transport IO cannot be fenced by a DB transaction.
"""

import base64
import hashlib
import json
import time
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
    provenance: Literal["UNINSTALLED_SYNTHETIC_ADAPTER", "SPEC_PRODUCTION_CONTROLLER"] = "UNINSTALLED_SYNTHETIC_ADAPTER"
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
    from .pa_trial_dispatch import _production_binding
    if _production_binding(getattr(worker, "pa_trial", None)):
        from .spec_production import environment
        environment(worker.store, worker.s, worker.goal_planner_transport)
        return
    _require(
        worker.store.test_only
        and worker.store.sqlite
        and worker.s.mode == "mock"
        and worker.s.live_enabled is False
        and worker.s.token == ""
        and type(worker.goal_planner_transport) is httpx.MockTransport
    )


def _wire(contract, wire, *, stage=None):
    _require(type(wire) is bytes and 0 < len(wire) <= contract.caps.max_wire_bytes)
    body = strict_json(wire, contract.caps.max_wire_bytes)
    _require(type(body) is dict)
    fields = {"model", "messages", "tools", "stream", "max_tokens"}
    version = None
    if stage in ("source", "cold"):
        messages = body.get("messages")
        _require(type(messages) is list and len(messages) == 2
            and all(type(message) is dict for message in messages)
            and messages[1].get("role") == "user"
            and type(messages[1].get("content")) is str)
        payload = strict_json(messages[1]["content"], contract.caps.max_wire_bytes)
        _require(type(payload) is dict)
        from .natural_request import protocol
        version = protocol(payload)
    if version is not None:
        from .natural_request import VERSION
        _require(version == VERSION and body.get("thinking_mode") is False
            and body.get("tools") == [])
        fields.add("thinking_mode")
    _require(
        type(body) is dict
        and set(body) == fields
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
    from .db import attempts, run_contracts
    from .spec_production import VERSION as PRODUCTION_VERSION
    marker = c.execute(select(attempts.c.mode,
        attempts.c.parameters["pa_trial_binding"]["version"].as_string().label("version"))
        .where(attempts.c.id == item.attempt_id, attempts.c.run_id == item.run_id)).mappings().first()
    mode = c.execute(select(run_contracts.c.snapshot["mode"].as_string())
                     .where(run_contracts.c.run_id == item.run_id)).scalar_one_or_none()
    _require(mode in ("mock", "live"), "VERSION_CONFLICT")
    production = mode == "live"
    if production:
        _require(marker is not None and marker["version"] == PRODUCTION_VERSION
                 and marker["mode"] == "LIVE", "VERSION_CONFLICT")
    else:
        # The original policy-only synthetic sender predates Core Attempts.
        # Its independently frozen Run mode still prevents a LIVE downgrade.
        _require(marker is None or marker["mode"] == "MOCK"
                 and marker["version"] != PRODUCTION_VERSION, "VERSION_CONFLICT")
    _require(capture.provenance == ("SPEC_PRODUCTION_CONTROLLER" if production
                                   else "UNINSTALLED_SYNTHETIC_ADAPTER"))
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
            capture == _derive(body, capture.complete, capture.received_response,
                               _generation=item.stage == "generate", _production=production),
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
                capture == _derive(b"", capture.complete, capture.received_response,
                                   _generation=item.stage == "generate", _production=production),
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


def _derive(payload, complete, received, *, _generation=False, _production=False):
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
            schemas = None
            if _generation:
                from .pa_spec_apps import CHECK_TOOL, check_envelope
                schemas = {CHECK_TOOL: check_envelope}
            # The original generation protocol includes its closed checker
            # envelope. This does not compile/execute/accept the candidate.
            parse_response(raw, schemas)
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
    omission: Literal["NONE", "EMPTY", "OVERSIZE"] = (
        "EMPTY" if not payload else "OVERSIZE" if len(payload) > 32768 else "NONE"
    )
    return Capture(
        provenance="SPEC_PRODUCTION_CONTROLLER" if _production else "UNINSTALLED_SYNTHETIC_ADAPTER",
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
    from .pa_trial_dispatch import _production_binding
    production = _business is not None and _production_binding(_business[0])
    _require(type(store) is Store and (production or store.test_only and store.sqlite))
    capture = _derive(payload, complete, received, _generation=item.stage == "generate", _production=production)
    with store.tx() as c:
        original, _, _, slot, revision, _ = _loaded(store, c, user, contract, key, item, wire)
        _require(slot.attempted, "OUTCOME_UNKNOWN")
        if _server_source:
            from .production_trial_source import load_offline

            if production:
                from .spec_production import receive_source
                source = receive_source(store, c, _business[0], source)
            else:
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
                       *, expected_revision, _heartbeat_state):
    """Private continuation of the existing original controller call only."""
    from .pa_trial_dispatch import _binding as trial_binding
    from .pa_trial_dispatch import _journal_binding
    _require(_journal_binding(binding) and trial_binding(worker) is binding)
    return _dispatch(worker, binding.contract, binding.approval_key, identity, wire,
        _SERVER_SOURCE, expected_revision=expected_revision,
        _business=(binding, run, original_guard, provider, _heartbeat_state))


def _dispatch(worker, contract, key, identity, wire, source, *, expected_revision, _business=None):
    """One explicit synthetic exchange; every original key retry is history only."""
    _binding(worker)
    from .pa_trial_dispatch import _production_binding
    production = _production_binding(getattr(worker, "pa_trial", None))
    if production:
        from .pa_trial_dispatch import _binding as trial_binding
        # Public offline entries accept synthetic inputs. Production can only
        # continue the original controller's exact, already verified binding.
        _require(type(_business) is tuple and len(_business) == 5
                 and _business[0] is worker.pa_trial
                 and trial_binding(worker) is _business[0])
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
    _wire(original, wire, stage=item.stage)
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
                if production:
                    from .spec_production import source as production_source
                    current_source = production_source(store, c, _business[0])
                else:
                    current_source = load_offline(store, c, user, original, key, item.account_id).source
                return journal._apply_in_transaction(
                    store, c, user, original, key, item, wire, current_source, revision, operation
                ), current_source
        action = journal.reserve if operation == "reserve" else journal.record_attempt
        return action(
            store, user, original, key, item, wire, supplied, expected_revision=revision
        ), supplied

    def renew_controller():
        if _business is None:
            return
        from .text_workflows import renew_sync
        same_binding()
        run, state, adapter = _business[1], _business[4], _business[3]
        deadline = min(run["created_at"] + adapter.settings.run_seconds,
                       run["created_at"] + original.caps.run_seconds, original.expires_at)
        _require(not worker.stop.is_set() and time.time() < deadline, "BUDGET_EXHAUSTED")
        if item.stage == "generate":
            from .goal_applications import _renew_committed_lease
            _require(type(state) is dict and state.get("generation_heartbeat") is True)
            _renew_committed_lease(worker, run, state, deadline=deadline)
            same_binding()
            _require(not worker.stop.is_set() and time.time() < deadline, "BUDGET_EXHAUSTED")
            return
        _require(type(state) is dict and state.get("sync_contention_recovery") is True)
        # Original guarded heartbeat, at a transaction boundary only. It
        # cannot revive an expired owner, renew a stop, or enlarge the deadline.
        if store.sqlite:
            renew_sync(worker, run, state, deadline=deadline,
                       lease_seconds=original.caps.lease_seconds)
        else:
            from .text_workflows import publish_sync_renewal
            renewed = store.heartbeat(worker_id, item.run_id, item.fence,
                original.caps.lease_seconds, _deadline=deadline,
                _wait_seconds=min(5.0, max(0.001, deadline - time.time())), _running_only=True)
            publish_sync_renewal(worker, run, state, renewed)
        same_binding()
        _require(not worker.stop.is_set() and time.time() < deadline, "BUDGET_EXHAUSTED")

    same_binding()
    renew_controller()
    reserved, supplied = transition("reserve", expected_revision)
    if reserved.duplicate:
        _require(_business is None, "OUTCOME_UNKNOWN")
        return _history(store, user, original, key, item, wire)
    same_binding()
    renew_controller()
    marked, supplied = transition("record_attempt", reserved.revision)
    if marked.duplicate:
        _require(_business is None, "OUTCOME_UNKNOWN")
        return _history(store, user, original, key, item, wire)
    same_binding()
    provider = configured_provider(worker) if _business is None else _business[3]
    _require(type(provider) is InternModel and provider.transport is transport)
    token = settings.token if production else "synthetic-offline-planner"
    if _business is not None:
        params = provider.settings
        token = (settings.token if production else
                 "synthetic-offline-planner" if item.stage == "generate" else "synthetic-offline-natural-spec")
        _require(params.mode == ("live" if production else "mock")
            and params.live_enabled is True and params.token == token
            and params.model == original.model and params.quota_subject == original.quota_subject
            and params.max_output_tokens == strict_json(wire, 32768)["max_tokens"]
            and 0 < params.max_output_tokens <= original.caps.max_output_tokens
            and 0 < params.run_seconds <= original.caps.run_seconds)

    def guard(request):
        same_binding()
        renew_controller()
        controller = None if _business is None else _business[2](request)
        same_binding()
        renew_controller()
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

                if production:
                    from .spec_production import source as production_source
                    current_source = production_source(store, c, _business[0])
                else:
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
        renew_controller()
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
