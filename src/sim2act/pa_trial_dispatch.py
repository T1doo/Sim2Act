"""Server-owned P-A/P-B trial wiring for existing Worker/InternModel boundaries.

No real account/zero-charge resolver is installed. The only executable binding
is an explicit isolated offline fixture; its records never authorize LIVE IO.
"""

import base64
import hashlib
import time
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select

from . import natural_live_admission as gate
from . import natural_trial_budget as budget
from . import production_trial_admission as production
from .contracts import strict_json
from .db import attempts, events, fingerprint, runs
from .db import delivery_graph_requests as rows
from .delivery_graph_apps import controlled
from .errors import DomainError
from .goal_applications import response_archive
from .model import CapturedResponse, InternModel, normalize_usage
from .natural_source_archives import BodyArchive, _body

REQUEST = "pa_trial_request_body.v1"
RESPONSE = "pa_trial_response_body.v1"
SENT = "pa_trial_dispatched.v1"


@dataclass(frozen=True)
class PATrialBinding:
    """Trusted controller configuration, never an HTTP request/fee override."""

    contract: gate.TrialContract | gate.PBTrialContract
    approval_key: str
    registry: production.OfflineRegistry | None = None
    contract_fingerprint: str = field(init=False)

    def __post_init__(self):
        gate.require(type(self.contract) in (gate.TrialContract, gate.PBTrialContract),
                     "Exact original P-A or P-B contract required")
        object.__setattr__(self, "contract_fingerprint", fingerprint(self.contract.model_dump()))
        budget.scope_for(self.contract, self.approval_key)


def _binding(worker):
    binding = worker.pa_trial
    if type(binding) is not PATrialBinding:
        production.blocked()
    gate.require(fingerprint(binding.contract.model_dump()) == binding.contract_fingerprint)
    if (
        not worker.store.test_only
        or not worker.store.sqlite
        or worker.s.mode != "mock"
        or worker.s.live_enabled
        or type(worker.goal_planner_transport) is not httpx.MockTransport
        or worker.s.quota_subject != binding.contract.quota_subject
        or binding.registry is None
    ):
        production.blocked()
    return binding


def validate(worker):
    """No production resolver: explicit production trial selection fails before claim."""
    b = _binding(worker)
    with worker.store.tx() as c:
        gate._approved(worker.store, c, b.contract.principal_id, b.contract, b.approval_key)
    _account(worker, b)


def _admission(worker):
    def admitted(store, c, user, contract, key, stage, rid, version, fence):
        b = _binding(worker)
        gate.require(
            fingerprint(contract.model_dump()) == b.contract_fingerprint
            and key == b.approval_key
            and user == b.contract.principal_id
        )
        _, result = production._account_admit(store, c, user, contract, key, stage,
            rid, version, fence, b.registry, worker.id)
        if type(contract) is gate.PBTrialContract and stage == "cold":
            _pb_source(worker, c, b)
        current = _binding(worker)
        gate.require(
            current.contract_fingerprint == b.contract_fingerprint
            and current.approval_key == b.approval_key
        )
        _account(worker, current)
        return result

    return admitted


def _account(worker, b):
    account = production._resolve(worker.store, b.contract.principal_id, b.contract, b.registry)
    gate.require(
        account.scope == "SYNTHETIC_ONLY"
        and type(account.legal_free_entitlement) is bool
        and type(account.enforced_non_chargeable) is bool
        and type(account.revoked) is bool
        and type(account.paid_cap) is int
        and account.paid_cap == 0
    )
    at = time.time()
    gate.require(
        account.checked_at <= at < min(account.expires_at, b.contract.expires_at)
        and at - account.checked_at <= 30,
        "Account evidence expired during proof",
    )
    return account


def check_commit(worker, c, run):
    b = _binding(worker)
    gate.require(
        run["principal_id"] == b.contract.principal_id
        and run["project_id"] == b.contract.project_id
    )
    gate._approved(worker.store, c, b.contract.principal_id, b.contract, b.approval_key)
    if type(b.contract) is gate.PBTrialContract and _stage(b, run) == "cold":
        _pb_source(worker, c, b)
    _account(worker, _binding(worker))


def _pb_source(worker, c, b):
    """Reprove original successful source, exact extraction and both actual chains.

    The existing full resolver shares this transaction: its source consent,
    complete Goals/Recipe and current authorities remain mandatory at every
    admission/commit. Its read-only receipt never becomes reusable authority.
    """
    from . import natural_source_archives as archive

    resolved = archive._resolve_trial_source(worker.store, c, b.contract.principal_id,
        b.contract, b.approval_key)
    _pb_archive_chain(worker, c, b, resolved)


@controlled
def _pb_archive_chain(worker, c, b, resolved):
    """Join the existing actual NS archives to this controller's immutable sends."""
    receipt = resolved.public_receipt
    scope = budget.scope_for(b.contract, b.approval_key)
    ledger = budget._ledger(c, scope)
    source_id = ledger["stage_runs"].get("source")
    gate.require(source_id == receipt["source_run_id"]
                 and receipt["verification"] == "ACTUAL_MOCK_ARCHIVE_NOT_LIVE_VERIFIED"
                 and receipt["live_allowed"] is False)
    source = c.execute(select(runs).where(runs.c.id == source_id)).mappings().one()
    slots = [s for s in ledger["slots"] if s["reservation"]["stage"] == "source"]
    gate.require(len(slots) == len(receipt["attempts"]) == 2)
    for slot, proof in zip(slots, receipt["attempts"], strict=True):
        aid = slot["reservation"]["request_key"]
        gate.require(aid == proof["attempt_id"])
        _identity(worker, c, source, aid)
        _full_chain(worker, c, source, aid, slot)
        request = _metadata(c, source, aid, REQUEST)
        response = _metadata(c, source, aid, RESPONSE)
        gate.require(request is not None and response is not None
            and request["sha256"] == proof["request_sha256"]
            and request["byte_count"] == proof["request_bytes"]
            and response["sha256"] == proof["decoded_body_sha256"]
            and response["byte_count"] == proof["decoded_body_bytes"]
            and response["canonical_sha256"] == proof["canonical_ascii_sha256"])


@controlled
def extract_pb(worker, user, source_id, body):
    """Server-selected same-trial extraction, using the original write group.

    No HTTP authority override or automatic trial selector is installed. The
    generic extraction API remains generic; this explicit controller entry also
    proves this trial's account, approved source, seven-slot ledger and bodies.
    """
    from . import natural_source_archives as archive
    from . import pb_natural_specs as pb

    b = _binding(worker)
    gate.require(type(b.contract) is gate.PBTrialContract and user == b.contract.principal_id)
    gate.require(type(body) is pb.ExtractInput
        and pb.ExtractInput.model_validate(body.model_dump()) == body)
    cold = b.contract.bindings[1]
    review = body.review
    gate.require(review.source_run_id == source_id
        and review.request_key == b.contract.extraction_request_key
        and review.recipe == b.contract.extraction_recipe
        and review.card_id == cold.card_id
        and review.expected_goal_version == cold.goal_version
        and review.expected_goal_fingerprint == cold.goal_fingerprint
        and review.expected_source_hash == cold.source_hash)
    with worker.store.tx() as c, worker.store.proof_authorities(c) as authorities:
        worker.store.lock_project(c, user, b.contract.project_id)
        _account(worker, _binding(worker))
        resolved = archive._resolve_source_before_extraction(worker.store, c, user,
            b.contract, b.approval_key)
        gate.require(resolved.public_receipt["source_run_id"] == source_id)
        _pb_archive_chain(worker, c, b, resolved)
        result = pb._extract(worker.store, c, user, b.contract.project_id, source_id,
            body, gate._limits(b.contract))
        _pb_source(worker, c, b)
        _account(worker, _binding(worker))
        gate._approved(worker.store, c, user, b.contract, b.approval_key)
        worker.store.recheck_proof_authorities(c,
            {"_call_authorities": tuple(sorted(authorities))})
        gate.require(time.time() < b.contract.expires_at)
        return result


def _stage(b, run):
    if run["runtime_id"] == b.contract.runtime_id:
        gate.require(run["request_key"] == b.contract.stage_keys.generate)
        return "generate"
    gate.require(run["resource_refs"] in [[x.resource_id] for x in b.contract.bindings])
    return "source" if run["resource_refs"] == [b.contract.bindings[0].resource_id] else "cold"


def preflight(worker, c, run, *, generation, natural):
    b = _binding(worker)
    stage = _stage(b, run)
    gate.require(
        (stage == "generate" and generation and not natural)
        or (stage != "generate" and natural and not generation)
    )
    _admission(worker)(
        worker.store,
        c,
        b.contract.principal_id,
        b.contract,
        b.approval_key,
        stage,
        run["id"],
        run["version"],
        run["fence"],
    )


def wait_unreserved(worker, run_id):
    """Wait only for a not-yet-reserved slot; original heartbeat and deadlines remain."""
    b = _binding(worker)
    scope = budget.scope_for(b.contract, b.approval_key)
    with worker.store.tx() as c:
        budget._context(worker.store, c, scope.principal_id, scope)
        ledger = budget._ledger(c, scope)
        if ledger["halted"] or any(not slot["accepted"] for slot in ledger["slots"]):
            raise DomainError("OUTCOME_UNKNOWN", "Original unknown trial cannot be retried")
        header = (
            c.execute(
                select(runs.c.created_at, runs.c.principal_id, runs.c.project_id).where(
                    runs.c.id == run_id
                )
            )
            .mappings()
            .one()
        )
        gate.require(
            header["principal_id"] == scope.principal_id
            and header["project_id"] == scope.project_id
        )
        entity = "trialquota_" + hashlib.sha256(scope.quota_subject.encode()).hexdigest()
        previous = budget._load(c, budget.KIND, entity, budget.KIND + ".quota", "quota")
        last = None if previous is None else previous["response"]["last_reserved_at"]
    deadline = min(
        header["created_at"] + worker.s.run_seconds,
        header["created_at"] + b.contract.caps.run_seconds,
        b.contract.expires_at,
    )
    while last is not None and time.time() < last + 60:
        if worker.stop.is_set() or time.time() >= deadline:
            raise DomainError("BUDGET_EXHAUSTED", "Original trial waiting interval ended")
        worker.stop.wait(min(0.25, max(0, min(last + 60, deadline) - time.time())))


def _request(b, run, aid, wire):
    return budget.Reservation(
        request_key=aid,
        stage=_stage(b, run),
        run_id=run["id"],
        expected_version=run["version"],
        fence=run["fence"],
        wire_sha256=hashlib.sha256(wire).hexdigest(),
        wire_bytes=len(wire),
    )


def _identity(worker, c, run, aid):
    b = _binding(worker)
    header = (
        c.execute(
            select(
                runs.c.principal_id,
                runs.c.project_id,
                runs.c.runtime_id,
                attempts.c.mode,
                attempts.c.parameters["pa_trial_binding"]["version"]
                .as_string()
                .label("binding_version"),
                attempts.c.parameters["pa_trial_binding"]["trial_fingerprint"]
                .as_string()
                .label("trial_fp"),
                attempts.c.parameters["pa_trial_binding"]["approval_key"]
                .as_string()
                .label("approval_key"),
            )
            .select_from(runs)
            .join(attempts, attempts.c.run_id == runs.c.id)
            .where(runs.c.id == run["id"], attempts.c.id == aid)
        )
        .mappings()
        .first()
    )
    gate.require(
        header is not None
        and header["mode"] == "MOCK"
        and header["binding_version"] == "pa-trial-dispatch.v1"
        and header["trial_fp"] == b.contract_fingerprint
        and header["approval_key"] == b.approval_key
        and all(header[k] == run[k] for k in ("principal_id", "project_id", "runtime_id"))
        and run["principal_id"] == b.contract.principal_id
        and run["project_id"] == b.contract.project_id
    )
    return b


def _archive(worker, c, run, aid, wire, payload, complete, kind):
    b = _identity(worker, c, run, aid)
    scope = budget.scope_for(b.contract, b.approval_key)
    slot = next(
        (s for s in budget._ledger(c, scope)["slots"] if s["reservation"]["request_key"] == aid),
        None,
    )
    if slot is None:
        raise DomainError("VERSION_CONFLICT", "Original trial slot missing")
    gate.require(slot["reservation"] == _request(b, run, aid, wire).model_dump())
    sealed = (
        c.execute(
            select(
                attempts.c.parameters["generation_wire"].as_string().label("generation"),
                attempts.c.parameters["natural_spec_wire"]["sha256"].as_string().label("natural"),
                attempts.c.parameters["natural_spec_wire"]["bytes"].as_integer().label("bytes"),
                attempts.c.status,
            ).where(attempts.c.id == aid, attempts.c.run_id == run["id"])
        )
        .mappings()
        .one()
    )
    gate.require(
        sealed["generation"] == hashlib.sha256(wire).hexdigest()
        if slot["reservation"]["stage"] == "generate"
        else sealed["natural"] == hashlib.sha256(wire).hexdigest() and sealed["bytes"] == len(wire)
    )
    canonical = None
    if kind == RESPONSE and complete:
        try:
            parsed = strict_json(payload, 131072)
            original, evidence = response_archive(parsed)
            canonical = evidence["sha256"] if original is not None else None
        except DomainError:
            pass  # Invalid body is an observed failure fact, never success.
    item = _body(
        run,
        aid,
        payload,
        complete,
        canonical,
        "natural_source_request_body.v1" if kind == REQUEST else "natural_source_response_body.v1",
    )
    key = dict(
        trial=scope.model_dump(),
        attempt_id=aid,
        family=kind,
        wire_sha256=hashlib.sha256(wire).hexdigest(),
    )
    existing = _metadata(c, run, aid, kind)
    if existing is not None:
        anchors = (
            c.execute(
                select(events.c.data).where(
                    events.c.run_id == run["id"],
                    events.c.kind == "PA_TRIAL_BODY",
                    events.c.data["attempt_id"].as_string() == aid,
                    events.c.data["family"].as_string() == kind,
                )
            )
            .scalars()
            .all()
        )
        gate.require(
            existing["trial_fp"] == scope.contract_fingerprint
            and existing["wire_sha256"] == key["wire_sha256"]
            and anchors == [_body_event(aid, kind, item)],
            "Immutable trial body changed",
        )
        return
    gate.require(sealed["status"] == "STARTED", "Completed history cannot gain a body archive")
    if kind == RESPONSE:
        request = _metadata(c, run, aid, REQUEST)
        gate.require(
            request is not None
            and request["trial_fp"] == scope.contract_fingerprint
            and request["wire_sha256"] == key["wire_sha256"]
            and budget._load(c, run["principal_id"], run["id"], SENT, aid) is not None
        )
    else:
        gate.require(
            c.info.get("pa_trial_reserving_attempt") == aid
            and budget._load(c, run["principal_id"], run["id"], SENT, aid) is None,
            "Request archive can only be created in its original reservation call",
        )
    budget._write(c, run["principal_id"], run["id"], kind, aid, key, item.model_dump(), new=True)
    worker.store.event(c, run["id"], "PA_TRIAL_BODY", _body_event(aid, kind, item))


def _body_event(aid, kind, item):
    return dict(
        attempt_id=aid,
        family=kind,
        body_fingerprint=fingerprint(item.model_dump()),
        decoded_sha256=item.sha256,
        canonical_sha256=item.canonical_sha256,
        byte_count=item.byte_count,
        complete=item.received_complete,
        omission=item.omission,
    )


def reserved(worker, c, run, aid, wire):
    b = _binding(worker)
    scope = budget.scope_for(b.contract, b.approval_key)
    result = budget._reserve(
        worker.store,
        c,
        scope.principal_id,
        scope,
        b.contract,
        _request(b, run, aid, wire),
        admission=_admission(worker),
    )
    gate.require(not result["duplicate"], "Existing reservation cannot authorize a new send")
    gate.require("pa_trial_reserving_attempt" not in c.info)
    c.info["pa_trial_reserving_attempt"] = aid
    try:
        _archive(worker, c, run, aid, wire, wire, True, REQUEST)
    finally:
        c.info.pop("pa_trial_reserving_attempt", None)


def _sent(worker, run, aid, wire):
    b = _binding(worker)
    scope = budget.scope_for(b.contract, b.approval_key)
    request = _request(b, run, aid, wire)
    with worker.store.tx() as c:
        _identity(worker, c, run, aid)
        slot = next(
            (
                s
                for s in budget._ledger(c, scope)["slots"]
                if s["reservation"]["request_key"] == aid
            ),
            None,
        )
        gate.require(
            slot is not None
            and slot["reservation"] == request.model_dump()
            and slot["settlement"] is None
        )
        budget._active(worker.store, c, scope, request, b.contract, _admission(worker))
        archived = budget._load(c, scope.principal_id, run["id"], REQUEST, aid)
        gate.require(
            archived is not None
            and archived["request"]
            == dict(
                trial=scope.model_dump(),
                attempt_id=aid,
                family=REQUEST,
                wire_sha256=request.wire_sha256,
            )
        )
        body = BodyArchive.model_validate(archived["response"])
        anchors = (
            c.execute(
                select(events.c.data).where(
                    events.c.run_id == run["id"],
                    events.c.kind == "PA_TRIAL_BODY",
                    events.c.data["attempt_id"].as_string() == aid,
                    events.c.data["family"].as_string() == REQUEST,
                )
            )
            .scalars()
            .all()
        )
        gate.require(anchors == [_body_event(aid, REQUEST, body)])
        if body.body_b64 is None:
            raise DomainError("OUTCOME_UNKNOWN", "Original request body unavailable")
        meta = _metadata(c, run, aid, REQUEST)
        gate.require(
            meta is not None
            and meta["trial_fp"] == scope.contract_fingerprint
            and meta["wire_sha256"] == request.wire_sha256
        )
        gate.require(
            body.run_id == run["id"]
            and body.attempt_id == aid
            and body.phase == "RESERVED_REQUEST"
            and body.received_complete
            and body.omission == "NONE"
            and body.byte_count == len(wire)
            and body.sha256 == hashlib.sha256(wire).hexdigest()
            and base64.b64decode(body.body_b64, validate=True) == wire
        )
        if budget._load(c, scope.principal_id, run["id"], SENT, aid) is not None:
            raise DomainError(
                "OUTCOME_UNKNOWN", "Original send marker already committed; never resend"
            )
        key = dict(trial=scope.model_dump(), reservation=request.model_dump(), worker_id=worker.id)
        budget._write(
            c,
            scope.principal_id,
            run["id"],
            SENT,
            aid,
            key,
            dict(status="DISPATCHED", live_allowed=False),
            new=True,
        )
        worker.store.event(
            c,
            run["id"],
            "PA_TRIAL_DISPATCHED",
            dict(attempt_id=aid, reservation_fingerprint=fingerprint(request.model_dump())),
        )


def request_captured(worker, run, aid, wire, original_guard, provider):
    """Existing Intern adapter only; receipt facts precede original business acceptance."""
    gate.require(
        type(provider) is InternModel
        and type(provider.transport) is httpx.MockTransport
        and provider.transport is worker.goal_planner_transport
    )

    def guard(request):
        result = original_guard(request)
        gate.require(
            request.content == wire
            and str(request.url) == InternModel.ENDPOINT
            and request.method == "POST"
        )
        _sent(worker, run, aid, wire)
        return result

    try:
        captured = provider.request_serialized_captured(wire, guard)
    except DomainError as error:
        received = getattr(error, "_received_body", None)
        complete = getattr(error, "_received_body_complete", False)
        if type(received) is bytes:
            with worker.store.tx() as c:
                _archive(worker, c, run, aid, wire, received, complete, RESPONSE)
        raise
    gate.require(type(captured) is CapturedResponse)
    with worker.store.tx() as c:
        _archive(worker, c, run, aid, wire, captured.body, True, RESPONSE)
    return captured


def _metadata(c, run, aid, kind):
    """Late failure accounting reads digest/identity projections, never body_b64."""
    selected = c.execute(
        select(
            rows.c.kind,
            rows.c.snapshot["request"]["trial"]["contract_fingerprint"]
            .as_string()
            .label("trial_fp"),
            rows.c.snapshot["request"]["attempt_id"].as_string().label("key_attempt"),
            rows.c.snapshot["request"]["family"].as_string().label("key_family"),
            rows.c.snapshot["request"]["wire_sha256"].as_string().label("wire_sha256"),
            *[
                rows.c.snapshot["response"][k].as_string().label(k)
                for k in (
                    "run_id",
                    "attempt_id",
                    "principal_id",
                    "project_id",
                    "runtime_id",
                    "phase",
                    "sha256",
                    "canonical_sha256",
                    "omission",
                )
            ],
            rows.c.snapshot["response"]["byte_count"].as_integer().label("byte_count"),
            rows.c.snapshot["response"]["received_complete"].as_boolean().label("complete"),
        ).where(
            rows.c.principal_id == run["principal_id"],
            rows.c.app_id == run["id"],
            rows.c.request_key == aid,
            rows.c.kind.in_([kind, kind + "_seal"]),
        )
    )
    values = [dict(r) for r in selected.mappings()]
    if not values:
        return None
    gate.require(len(values) == 2 and {r.pop("kind") for r in values} == {kind, kind + "_seal"})
    gate.require(values[0] == values[1])
    value = values[0]
    gate.require(
        value["phase"] == ("RESERVED_REQUEST" if kind == REQUEST else "RECEIVED_DECODED_BODY")
    )
    gate.require(
        value["run_id"] == run["id"]
        and value["attempt_id"] == aid
        and value["key_attempt"] == aid
        and value["key_family"] == kind
        and all(value[k] == run[k] for k in ("principal_id", "project_id", "runtime_id"))
    )
    anchors = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == run["id"],
                events.c.kind == "PA_TRIAL_BODY",
                events.c.data["attempt_id"].as_string() == aid,
                events.c.data["family"].as_string() == kind,
            )
        )
        .scalars()
        .all()
    )
    gate.require(
        len(anchors) == 1
        and all(
            anchors[0].get(k) == value[field]
            for k, field in (
                ("decoded_sha256", "sha256"),
                ("canonical_sha256", "canonical_sha256"),
                ("byte_count", "byte_count"),
                ("complete", "complete"),
                ("omission", "omission"),
            )
        )
    )
    return value


def _full_chain(worker, c, run, aid, slot):
    b = _binding(worker)
    scope = budget.scope_for(b.contract, b.approval_key)
    request = budget.Reservation.model_validate(slot["reservation"])
    wire = None
    for kind in (REQUEST, RESPONSE):
        meta = _metadata(c, run, aid, kind)
        gate.require(
            meta is not None
            and meta["trial_fp"] == scope.contract_fingerprint
            and meta["wire_sha256"] == request.wire_sha256
            and meta["complete"]
            and meta["omission"] == "NONE"
        )
        saved = budget._load(c, run["principal_id"], run["id"], kind, aid)
        gate.require(
            saved is not None
            and saved["request"]
            == dict(
                trial=scope.model_dump(),
                attempt_id=aid,
                family=kind,
                wire_sha256=request.wire_sha256,
            )
        )
        body = BodyArchive.model_validate(saved["response"])
        if body.body_b64 is None:
            raise DomainError("OUTCOME_UNKNOWN", "Original body unavailable")
        payload = base64.b64decode(body.body_b64, validate=True)
        gate.require(
            len(payload) == body.byte_count and hashlib.sha256(payload).hexdigest() == body.sha256
        )
        anchor = (
            c.execute(
                select(events.c.data).where(
                    events.c.run_id == run["id"],
                    events.c.kind == "PA_TRIAL_BODY",
                    events.c.data["attempt_id"].as_string() == aid,
                    events.c.data["family"].as_string() == kind,
                )
            )
            .scalars()
            .one()
        )
        gate.require(anchor["body_fingerprint"] == fingerprint(body.model_dump()))
        if kind == REQUEST:
            gate.require(
                body.phase == "RESERVED_REQUEST"
                and len(payload) == request.wire_bytes
                and body.sha256 == request.wire_sha256
            )
            wire = payload
        else:
            gate.require(body.phase == "RECEIVED_DECODED_BODY")
            decoded = strict_json(payload, 32768)
            canonical, evidence = response_archive(decoded)
            gate.require(canonical is not None and body.canonical_sha256 == evidence["sha256"])
    sent = budget._load(c, run["principal_id"], run["id"], SENT, aid)
    gate.require(
        sent
        == dict(
            request=dict(
                trial=scope.model_dump(), reservation=request.model_dump(), worker_id=run["worker_id"]
            ),
            response=dict(status="DISPATCHED", live_allowed=False),
        )
    )
    anchors = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == run["id"],
                events.c.kind == "PA_TRIAL_DISPATCHED",
                events.c.data["attempt_id"].as_string() == aid,
            )
        )
        .scalars()
        .all()
    )
    gate.require(
        anchors == [dict(attempt_id=aid, reservation_fingerprint=fingerprint(request.model_dump()))]
    )
    if wire is None:
        raise DomainError("VERSION_CONFLICT", "Original request wire missing")
    # Join immutable trial archive back to the original actual Attempt wire.
    original = (
        c.execute(
            select(
                attempts.c.parameters["generation_wire"].as_string().label("gen"),
                attempts.c.parameters["natural_spec_wire"]["sha256"].as_string().label("nat"),
                attempts.c.parameters["natural_spec_wire"]["bytes"].as_integer().label("bytes"),
            ).where(attempts.c.id == aid, attempts.c.run_id == run["id"])
        )
        .mappings()
        .one()
    )
    gate.require(
        original["gen"] == request.wire_sha256
        if request.stage == "generate"
        else original["nat"] == request.wire_sha256 and original["bytes"] == len(wire)
    )


def _settlement(worker, c, run, aid, raw, *, verified=False):
    b = _binding(worker)
    scope = budget.scope_for(b.contract, b.approval_key)
    slot = next(
        (s for s in budget._ledger(c, scope)["slots"] if s["reservation"]["request_key"] == aid),
        None,
    )
    if slot is None:
        raise DomainError("VERSION_CONFLICT", "Original trial slot missing")
    if verified:
        _full_chain(worker, c, run, aid, slot)
    meta = _metadata(c, run, aid, RESPONSE)
    original, evidence = response_archive(raw) if isinstance(raw, dict) else (None, {})
    complete = meta is not None and meta["complete"] and meta["omission"] == "NONE"
    if complete and original is not None:
        gate.require(
            meta["trial_fp"] == scope.contract_fingerprint
            and meta["wire_sha256"] == slot["reservation"]["wire_sha256"]
            and meta["canonical_sha256"] == evidence["sha256"]
        )
    usage = (
        normalize_usage(raw)
        if complete and original is not None
        else dict(status="unknown", tokens=None)
    )
    known = usage["status"] == "known" and original is not None
    tokens = usage["tokens"] if known else {}
    return budget.Settlement(
        request_key=aid,
        response_sha256=evidence["sha256"]
        if original is not None
        else hashlib.sha256(b"").hexdigest(),
        response_ascii_bytes=evidence["bytes"] if original is not None else 0,
        **{k: tokens.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
    )


def settle_verified(worker, c, run, aid, raw):
    b = _identity(worker, c, run, aid)
    scope = budget.scope_for(b.contract, b.approval_key)
    check_commit(worker, c, run)
    result = budget._settle(
        worker.store,
        c,
        scope.principal_id,
        scope,
        b.contract,
        _settlement(worker, c, run, aid, raw, verified=True),
        admission=_admission(worker),
    )
    slot = next(s for s in result["ledger"]["slots"] if s["reservation"]["request_key"] == aid)
    if not slot["accepted"]:
        raise DomainError("OUTCOME_UNKNOWN", "Trial response cannot authorize business acceptance")


def reject(worker, c, run, aid, raw):
    """Evidence-only monotonic failure accounting; no synthetic re-admission."""
    b = _identity(worker, c, run, aid)
    scope = budget.scope_for(b.contract, b.approval_key)
    slot = next(
        (s for s in budget._ledger(c, scope)["slots"] if s["reservation"]["request_key"] == aid),
        None,
    )
    if slot is None:
        raise DomainError("VERSION_CONFLICT", "Original trial slot missing")
    if slot["settlement"] is not None and raw is None:
        return  # No new response fact; never undo already immutable accounting.

    def denied(*args):
        raise DomainError("LIVE_BLOCKED", "Failed original trial node cannot be accepted")

    budget._settle(
        worker.store,
        c,
        scope.principal_id,
        scope,
        b.contract,
        _settlement(worker, c, run, aid, raw),
        admission=denied,
    )
