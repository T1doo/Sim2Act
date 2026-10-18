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
JOURNAL_VERSION = "UNINSTALLED-pa-journal-trial.v1"


@dataclass(frozen=True)
class JournalTrialBinding:
    """Explicit P-A offline controller fixture; never installed by an API."""

    contract: gate.TrialContractV2 | gate.TrialContract
    approval_key: str
    account_id: str
    contract_fingerprint: str = field(init=False)
    version: str = field(default=JOURNAL_VERSION, init=False)

    def __post_init__(self):
        from .production_evidence import _contract_data, requirements_for

        gate.require(type(self.contract) in (gate.TrialContractV2, gate.TrialContract))
        original = gate.parse_contract(_contract_data(self.contract))
        requirements_for(original.principal_id, original, self.approval_key)
        object.__setattr__(self, "contract", original)
        gate.require(self.contract.quota_subject == production.canonical_quota_subject(self.account_id))
        object.__setattr__(self, "contract_fingerprint", fingerprint(_contract_data(original)))
        budget.scope_for(self.contract, self.approval_key)


@dataclass(frozen=True)
class PATrialBinding:
    """Trusted controller configuration, never an HTTP request/fee override."""

    contract: gate.TrialContractV2 | gate.TrialContract | gate.PBTrialContract
    approval_key: str
    registry: production.OfflineRegistry | None = None
    contract_fingerprint: str = field(init=False)

    def __post_init__(self):
        gate.require(type(self.contract) in (gate.TrialContractV2, gate.TrialContract, gate.PBTrialContract),
                     "Exact original P-A or P-B contract required")
        object.__setattr__(self, "contract_fingerprint", fingerprint(self.contract.model_dump()))
        budget.scope_for(self.contract, self.approval_key)


def _binding(worker):
    binding = worker.pa_trial
    if type(binding) is JournalTrialBinding:
        from .config import Settings
        from .db import Store
        from .production_evidence import _contract_data
        from .worker import Worker

        gate.require(type(worker) is Worker and type(worker.s) is Settings
            and type(worker.store) is Store and worker.store.test_only and worker.store.sqlite
            and worker.s.mode == "mock" and worker.s.live_enabled is False and worker.s.token == ""
            and type(worker.goal_planner_transport) is httpx.MockTransport
            and worker.s.quota_subject == binding.contract.quota_subject
            and worker.s.model == binding.contract.model
            and worker.s.max_output_tokens == binding.contract.caps.max_output_tokens
            and worker.store is worker._journal_trial_store
            and binding is worker._journal_trial_binding and not worker._journal_trial_drift
            and fingerprint(_contract_data(binding.contract)) == binding.contract_fingerprint)
        return binding
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
        if type(b) is JournalTrialBinding:
            from . import production_trial_policy as policy
            context = policy.check_run(store, c, user, contract, key, stage, rid, version, fence, worker.id)
            _journal_source(store, c, b)
            return context
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
    if type(b) is JournalTrialBinding:
        with worker.store.tx() as c:
            return _journal_source(worker.store, c, b)
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
    if type(b) is JournalTrialBinding:
        _admission(worker)(worker.store, c, run["principal_id"], b.contract, b.approval_key,
            _stage(b, run), run["id"], run["version"], run["fence"])
        return
    if type(b.contract) is gate.PBTrialContract and _stage(b, run) == "cold":
        _pb_source(worker, c, b)
    _account(worker, _binding(worker))


def check_terminal_commit(worker, c, run, state):
    """Original terminal transaction continuation; never a send/Run admission."""
    b = _binding(worker)
    if type(b) is not JournalTrialBinding:
        return check_commit(worker, c, run)
    stage = _stage(b, run)
    gate.require(state == ("PARTIAL" if stage == "generate" else "SUCCEEDED"))
    fields = ("id", "principal_id", "project_id", "runtime_id", "worker_id", "fence",
              "created_at", "fingerprint", "request_key")
    terminal = c.execute(select(*(getattr(runs.c, k) for k in fields), runs.c.status,
        runs.c.version, runs.c.cancel_intent, runs.c.lease_until)
        .where(runs.c.id == run["id"])).mappings().one()
    gate.require(run["status"] == "RUNNING" and run["worker_id"] == worker.id
        and not worker.stop.is_set() and not run["cancel_intent"]
        and all(terminal[k] == run[k] for k in fields)
        and terminal["status"] == state and terminal["version"] == run["version"] + 1
        and not terminal["cancel_intent"] and terminal["lease_until"] == 0
        and time.time() < min(run["lease_until"], b.contract.expires_at,
                              run["created_at"] + b.contract.caps.run_seconds))
    gate._approved(worker.store, c, run["principal_id"], b.contract, b.approval_key)
    _journal_source(worker.store, c, b)
    if stage == "generate":
        gate._generation_context(worker.store, c, run, b.contract)
    else:
        phase, _ = gate._stage_current(worker.store, c, run["principal_id"], b.contract, stage, run["id"])
        consent = gate._saved(c, run["principal_id"], gate.entity(b.contract), gate.PHASE,
                             stage, gate.StageApproveInput)
        gate.require(phase == consent.authority
            and consent.approval_key == b.approval_key
            and fingerprint(phase.model_dump()) == consent.expected_authority_fingerprint)
    journal_stage_accounted(worker.store, c, run["principal_id"], b.contract,
                            b.approval_key, run["id"], stage)
    _binding(worker)


def _pb_source(worker, c, b):
    """Reprove original successful source, exact extraction and both actual chains.

    The existing full resolver shares this transaction: its source consent,
    complete Goals/Recipe and current authorities remain mandatory at every
    admission/commit. Its read-only receipt never becomes reusable authority.
    """
    from . import natural_source_archives as archive
    from .pb_natural_specs import _source_reads

    with _source_reads(worker.store, c):
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
    if type(b) is JournalTrialBinding:
        return _journal_wait(worker, b, run_id)
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
    if type(b) is JournalTrialBinding:
        _journal_owner(c, b, run, aid)
        return b
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
    return _archive_bound(worker.store, c, b, run, aid, wire, payload, complete, kind)


def _archive_bound(store, c, b, run, aid, wire, payload, complete, kind):
    scope = budget.scope_for(b.contract, b.approval_key)
    new = type(b) is JournalTrialBinding
    slot = None if new else next(
        (s for s in budget._ledger(c, scope)["slots"] if s["reservation"]["request_key"] == aid),
        None,
    )
    if not new and slot is None:
        raise DomainError("VERSION_CONFLICT", "Original trial slot missing")
    if not new:
        gate.require(slot["reservation"] == _request(b, run, aid, wire).model_dump())
    else:
        _journal_owner(c, b, run, aid)
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
        if _stage(b, run) == "generate"
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
            and (_journal_slot(store, c, b, run, aid, wire).attempted if new
                else budget._load(c, run["principal_id"], run["id"], SENT, aid) is not None)
        )
    else:
        gate.require(
            c.info.get("pa_trial_reserving_attempt") == aid
            and budget._load(c, run["principal_id"], run["id"], SENT, aid) is None,
            "Request archive can only be created in its original reservation call",
        )
    budget._write(c, run["principal_id"], run["id"], kind, aid, key, item.model_dump(), new=True)
    store.event(c, run["id"], "PA_TRIAL_BODY", _body_event(aid, kind, item))


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
    if type(b) is JournalTrialBinding:
        gate.require("pa_trial_reserving_attempt" not in c.info)
        c.info["pa_trial_reserving_attempt"] = aid
        try:
            _archive(worker, c, run, aid, wire, wire, True, REQUEST)
        finally:
            c.info.pop("pa_trial_reserving_attempt", None)
        return
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
    if type(_binding(worker)) is JournalTrialBinding:
        return _journal_exchange(worker, run, aid, wire, original_guard, provider)

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
    if type(b) is JournalTrialBinding:
        check_commit(worker, c, run)
        _journal_chain(worker.store, c, b, run, aid, raw)
        return
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
    if type(getattr(worker, "_journal_trial_binding", None)) is JournalTrialBinding:
        # Receive already committed immutable accounting. No current binding,
        # duplicate settle or missing response may mint authority/refund here.
        b = worker._journal_trial_binding
        gate.require(c.engine is worker._journal_trial_store.engine)
        _journal_owner(c, b, run, aid)
        return
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


def _journal_source(store, c, b):
    from .production_trial_policy import check_source, evidence
    from .production_trial_source import load_offline

    loaded = load_offline(store, c, b.contract.principal_id, b.contract,
                          b.approval_key, b.account_id)
    return check_source(evidence.requirements_for(b.contract.principal_id, b.contract,
                        b.approval_key), loaded.source, now=time.time())


def check_journal_claim(store, c, run, b):
    """Fixed original generic P-A queue, explicitly excluding qualified associations."""
    from .natural_trial_runs import associated_sql
    gate.require(type(b) is JournalTrialBinding and store.test_only and store.sqlite
        and run["principal_id"] == b.contract.principal_id
        and run["project_id"] == b.contract.project_id
        and run["status"] == "QUEUED" and not run["cancel_intent"]
        and c.execute(select(runs.c.id).where(runs.c.id == run["id"], associated_sql())).first() is None)
    gate._approved(store, c, run["principal_id"], b.contract, b.approval_key)
    _journal_source(store, c, b)
    stage = _stage(b, run)
    gate.require(run["request_key"] == getattr(b.contract.stage_keys, stage))
    if stage == "generate":
        gate._generation_context(store, c, run, b.contract)
    else:
        current, _ = gate._stage_current(store, c, run["principal_id"], b.contract, stage, run["id"])
        accepted = gate._saved(c, run["principal_id"], gate.entity(b.contract), gate.PHASE,
                              stage, gate.StageApproveInput)
        gate.require(current == accepted.authority and accepted.approval_key == b.approval_key
            and fingerprint(current.model_dump()) == accepted.expected_authority_fingerprint)
        gate._stage_review_window(current)
    frozen_seconds = store.frozen_contract(c, run).limits.run_seconds
    deadline = min(run["created_at"] + min(b.contract.caps.run_seconds, frozen_seconds),
                   b.contract.expires_at)
    gate.require(time.time() < deadline)
    return deadline


def _journal_state(store, c, b):
    from . import production_trial_journal as journal

    gate.require(store.test_only and store.sqlite and c.engine is store.engine)
    _, scope, request, quota_request, entity = journal._context(
        store, c, b.contract.principal_id, b.contract, b.approval_key, b.account_id)
    # Backend mixing cannot acquire history/send authority.
    old = budget.scope_for(b.contract, b.approval_key)
    gate.require(budget._load(c, old.principal_id, old.project_id, budget.KIND, old.trial_key) is None)
    _, cursor, qr = journal._quota(c, quota_request, entity, create=False)
    _, state, revision = journal._ledger(c, scope, request, cursor, qr)
    return state, cursor, revision


def _journal_wait(worker, b, rid):
    with worker.store.tx() as c:
        state, cursor, _ = _journal_state(worker.store, c, b)
        gate.require(not state.halted and all(s.accepted for s in state.slots))
        header = c.execute(select(runs.c.created_at, runs.c.principal_id, runs.c.project_id)
                           .where(runs.c.id == rid)).mappings().one()
        gate.require(header["principal_id"] == b.contract.principal_id
                     and header["project_id"] == b.contract.project_id)
    deadline = min(header["created_at"] + min(worker.s.run_seconds, b.contract.caps.run_seconds),
                   b.contract.expires_at)
    last = cursor.last_reserved_at
    while last is not None and time.time() < last + 60:
        _binding(worker)
        if worker.stop.is_set() or time.time() >= deadline:
            raise DomainError("BUDGET_EXHAUSTED", "Original trial waiting interval ended")
        worker.stop.wait(min(0.25, max(0, min(last + 60, deadline) - time.time())))


def _journal_owner(c, b, run, aid):
    # Exact scalar binding before any private request/response or journal body.
    header = c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
        attempts.c.mode,
        *[attempts.c.parameters["pa_trial_binding"][k].as_string().label(k)
          for k in ("version", "trial_fingerprint", "approval_key", "account_id", "worker_id")],
        attempts.c.parameters["pa_trial_binding"]["run_version"].as_integer().label("run_version"),
        attempts.c.parameters["pa_trial_binding"]["fence"].as_integer().label("fence"))
        .select_from(runs).join(attempts, attempts.c.run_id == runs.c.id)
        .where(runs.c.id == run["id"], attempts.c.id == aid)).mappings().first()
    gate.require(header is not None and header["mode"] == "MOCK"
        and header["version"] == JOURNAL_VERSION
        and header["trial_fingerprint"] == b.contract_fingerprint
        and header["approval_key"] == b.approval_key and header["account_id"] == b.account_id
        and header["principal_id"] == b.contract.principal_id
        and header["project_id"] == b.contract.project_id
        and all(header[k] == run[k] for k in ("principal_id", "project_id", "runtime_id")))
    return header


def _journal_slot(store, c, b, run, aid, wire):
    from . import production_trial_policy as policy

    header = _journal_owner(c, b, run, aid)
    state, cursor, _ = _journal_state(store, c, b)
    slot = next((s for s in state.slots if s.identity.attempt_id == aid), None)
    gate.require(slot is not None)
    item = slot.identity
    policy._bound(store, c, run["principal_id"], b.contract, b.approval_key,
                  state, cursor, item, wire)
    approval = gate._saved(c, run["principal_id"], gate.entity(b.contract), gate.APPROVE,
                           "approve", gate.Approval)
    phase_fp = None
    if item.stage != "generate":
        phase = gate._saved(c, run["principal_id"], gate.entity(b.contract), gate.PHASE,
                            item.stage, gate.StageApproveInput)
        phase_fp = fingerprint(phase.authority.model_dump())
    gate.require(item.run_id == run["id"] and item.runtime_id == run["runtime_id"]
        and item.version == header["run_version"] and item.fence == header["fence"]
        and item.worker_id == header["worker_id"]
        and item.stage == _stage(b, run)
        and item.approval_fingerprint == fingerprint(approval.model_dump())
        and item.stage_fingerprint == phase_fp)
    return slot


def _journal_exchange(worker, run, aid, wire, original_guard, provider):
    from . import production_trial_policy as policy
    from . import production_trial_sender as sender

    b, store = _binding(worker), worker.store
    with store.tx() as c:
        _journal_owner(c, b, run, aid)
        _, _, revision = _journal_state(store, c, b)
        context = policy.check_run(store, c, run["principal_id"], b.contract, b.approval_key,
            _stage(b, run), run["id"], run["version"], run["fence"], worker.id)
        item = policy.identity_for(context, _journal_source(store, c, b), aid, wire)
        request = _metadata(c, run, aid, REQUEST)
        gate.require(request is not None and request["wire_sha256"] == item.wire_sha256)
        if item.stage != "generate":
            limits = c.execute(select(attempts.c.parameters["natural_spec"]["limits"])
                               .where(attempts.c.id == aid)).scalar_one()
            gate.require(all(getattr(provider.settings, k) == v for k, v in limits.items()))
    return sender._dispatch_business(worker, b, run, item, wire, original_guard, provider,
                                     expected_revision=revision)


def _journal_received(store, c, b, run, item, wire, payload, complete):
    """Same receive transaction, fixed original Store/binding; no live admission."""
    _archive_bound(store, c, b, run, item.attempt_id, wire, payload, complete, RESPONSE)
    if item.stage != "generate":
        from .natural_source_archives import record_response
        canonical = None
        try:
            parsed = strict_json(payload, 131072)
            original, evidence = response_archive(parsed)
            canonical = evidence["sha256"] if original is not None else None
        except DomainError:
            pass
        record_response(store, c, run, item.attempt_id, payload, complete, canonical,
                        request_body=wire)


def _journal_chain(store, c, b, run, aid, raw=None):
    """Immutable same-aid bodies/accounting proof; no lease or send authority."""
    from . import production_trial_sender as sender

    _journal_owner(c, b, run, aid)
    scope = budget.scope_for(b.contract, b.approval_key)
    payloads = []
    for kind in (REQUEST, RESPONSE):
        meta = _metadata(c, run, aid, kind)
        gate.require(meta is not None and meta["trial_fp"] == b.contract_fingerprint
            and meta["complete"] and meta["omission"] == "NONE")
        saved = budget._load(c, run["principal_id"], run["id"], kind, aid)
        gate.require(saved["request"] == dict(trial=scope.model_dump(), attempt_id=aid,
            family=kind, wire_sha256=meta["wire_sha256"]))
        body = BodyArchive.model_validate(saved["response"])
        gate.require(body.body_b64 is not None)
        payload = base64.b64decode(body.body_b64, validate=True)
        gate.require(_body(run, aid, payload, True, body.canonical_sha256,
            "natural_source_request_body.v1" if kind == REQUEST
            else "natural_source_response_body.v1") == body)
        gate.require(meta["sha256"] == hashlib.sha256(payload).hexdigest())
        payloads.append(payload)
    wire, payload = payloads
    slot = _journal_slot(store, c, b, run, aid, wire)
    capture = sender._captured(c, run["principal_id"], slot.identity)
    gate.require(slot.accepted and slot.attempted and capture is not None
        and slot.settlement == capture.outcome and capture.complete
        and capture.raw_sha256 == hashlib.sha256(payload).hexdigest()
        and capture.body_b64 == base64.b64encode(payload).decode("ascii"))
    parsed = strict_json(payload, 131072)
    canonical, evidence = response_archive(parsed)
    response = _metadata(c, run, aid, RESPONSE)
    gate.require(canonical is not None and response["canonical_sha256"] == evidence["sha256"]
        == capture.canonical_sha256 and capture.canonical_ascii_bytes == evidence["bytes"])
    if raw is not None:
        gate.require(response_archive(raw) == (canonical, evidence))
    actual = c.execute(select(attempts).where(attempts.c.run_id == run["id"],
                                               attempts.c.id == aid)).mappings().one()
    params = actual["parameters"]
    gate.require(actual["request_model"] == b.contract.model and actual["mode"] == "MOCK"
        and actual["reserved_tokens"] == len(wire) + params["max_tokens"]
        and params["max_tokens"] == strict_json(wire, 32768)["max_tokens"]
        and params["max_tokens"] <= b.contract.caps.max_output_tokens
        and (params.get("generation_wire") == slot.identity.wire_sha256
             and params.get("generation_fence") == slot.identity.fence
            if slot.identity.stage == "generate" else
            params.get("natural_spec_wire", {}).get("sha256") == slot.identity.wire_sha256
            and params["natural_spec_wire"].get("bytes") == len(wire)
            and params["natural_spec"].get("fence") == slot.identity.fence
            and params["natural_spec"].get("run_version") == slot.identity.version))
    return slot, capture, parsed, actual


def journal_stage_accounted(store, c, user, contract, key, rid, stage):
    """Original current lineage calls this only after its full ownership gate."""
    gate.require(stage in ("generate", "source", "cold") and user == contract.principal_id)
    owner = c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id,
        runs.c.request_key, runs.c.status).where(runs.c.id == rid)).mappings().first()
    gate.require(owner is not None and owner["principal_id"] == user
        and owner["project_id"] == contract.project_id
        and owner["request_key"] == getattr(contract.stage_keys, stage))
    if stage == "generate":
        gate.require(owner["runtime_id"] == contract.runtime_id)
        from .goal_applications import source_scope_gate
        source_scope_gate(store, c, rid)
    else:
        phase = gate._saved(c, user, gate.entity(contract), gate.PHASE, stage, gate.StageApproveInput)
        gate.require(phase.approval_key == key and phase.authority.run_id == rid
            and phase.authority.stage == stage and phase.authority.runtime_id == owner["runtime_id"]
            and phase.authority.contract_fingerprint == fingerprint(contract.model_dump())
            and phase.expected_authority_fingerprint == fingerprint(phase.authority.model_dump())
            and owner["status"] == "SUCCEEDED")
        from .pa_spec_apps import job_scope_gate
        gate.require(job_scope_gate(store, c, user, rid))
    actual = c.execute(select(attempts).where(attempts.c.run_id == rid)
                       .order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
    gate.require(len(actual) == (3 if stage == "generate" else 2))
    markers = [a["parameters"].get("pa_trial_binding", {}) for a in actual]
    gate.require(all(m.get("version") == JOURNAL_VERSION for m in markers)
        and len({m.get("account_id") for m in markers}) == 1)
    b = JournalTrialBinding(contract, key, markers[0].get("account_id"))
    gate.require(user == contract.principal_id)
    run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    state, _, _ = _journal_state(store, c, b)
    slots = [s for s in state.slots if s.identity.stage == stage]
    gate.require(not state.halted and len(slots) == len(actual)
        and {s.identity.attempt_id for s in slots} == {a["id"] for a in actual}
        and all(s.identity.run_id == rid for s in slots))
    for a in actual:
        slot, capture, parsed, checked = _journal_chain(store, c, b, run, a["id"])
        usage = normalize_usage(parsed)
        gate.require(checked == a and a["status"] == ("RECEIVED" if stage == "generate" else "VERIFIED")
            and a["usage"] == usage and usage["status"] == "known"
            and all(getattr(slot.settlement, k) == usage["tokens"].get(k)
                    for k in ("prompt_tokens", "completion_tokens", "total_tokens")))
        if stage == "generate":
            gate.require(a["parameters"].get("generation_raw_evidence") == response_archive(parsed)[1]
                and a["parameters"].get("generation_received_raw") == response_archive(parsed)[0])
        else:
            from .natural_source_archives import REQUEST as NS_REQUEST
            from .natural_source_archives import RESPONSE as NS_RESPONSE
            from .natural_source_archives import _read
            _, original_wire = _read(c, user, run, a["id"], NS_REQUEST)
            body, archived = _read(c, user, run, a["id"], NS_RESPONSE)
            gate.require(body.sha256 == capture.raw_sha256
                and archived == base64.b64decode(capture.body_b64)
                and body.canonical_sha256 == capture.canonical_sha256
                and hashlib.sha256(original_wire).hexdigest() == slot.identity.wire_sha256
                and a["response"].get("received_raw") == response_archive(parsed)[0]
                and a["response"].get("raw_evidence") == response_archive(parsed)[1])
            from .db import operations
            op = c.execute(select(operations.c.status).where(operations.c.run_id == rid,
                operations.c.id == a["parameters"]["natural_spec"]["operation_id"])).scalar_one()
            gate.require(op == "VERIFIED")
