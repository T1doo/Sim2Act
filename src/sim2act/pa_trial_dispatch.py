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
from . import _cold_source_packet as _source_owned_code
_SOURCE_OWNED_CHECK = _source_owned_code.CHECK
_SOURCE_BINDING_TYPE = _source_owned_code._BINDING
_SOURCE_OWNED_ENABLED = _source_owned_code._SOURCE_OK
_SOURCE_CAPACITY = _source_owned_code.Capacity
from . import _cold_archive_packet as _owned_archive_code
_OWNED_ARCHIVE_CHECK = _owned_archive_code.CHECK
from .goal_applications import response_archive
from .model import CapturedResponse, InternModel, normalize_usage
from .natural_source_archives import BodyArchive, _body

REQUEST = "pa_trial_request_body.v1"
RESPONSE = "pa_trial_response_body.v1"
SENT = "pa_trial_dispatched.v1"
JOURNAL_VERSION = "UNINSTALLED-pa-journal-trial.v1"


# Immutable SQL structure only. Every call builds fresh predicates and executes
# both original reads; no row, digest, authority or validation result is retained.
_JOURNAL_METADATA_PROJECTION = select(
    rows.c.kind,
    rows.c.snapshot["request"]["trial"]["contract_fingerprint"].as_string().label("trial_fp"),
    rows.c.snapshot["request"]["attempt_id"].as_string().label("key_attempt"),
    rows.c.snapshot["request"]["family"].as_string().label("key_family"),
    rows.c.snapshot["request"]["wire_sha256"].as_string().label("wire_sha256"),
    *[rows.c.snapshot["response"][k].as_string().label(k) for k in (
        "run_id", "attempt_id", "principal_id", "project_id", "runtime_id",
        "phase", "sha256", "canonical_sha256", "omission")],
    rows.c.snapshot["response"]["byte_count"].as_integer().label("byte_count"),
    rows.c.snapshot["response"]["received_complete"].as_boolean().label("complete"),
)


def _checked_trial_contract(contract, approval_key, account_id):
    from .production_evidence import _contract_data, requirements_for

    gate.require(type(contract) in (gate.TrialContractV2, gate.TrialContract, gate.PBTrialContract))
    original = gate.parse_contract(_contract_data(contract))
    requirements_for(original.principal_id, original, approval_key)
    gate.require(original.quota_subject == production.canonical_quota_subject(account_id))
    budget.scope_for(original, approval_key)
    return original


@dataclass(frozen=True)
class JournalTrialBinding:
    """Explicit P-A offline controller fixture; never installed by an API."""

    contract: gate.TrialContractV2 | gate.TrialContract
    approval_key: str
    account_id: str
    contract_fingerprint: str = field(init=False)
    version: str = field(default=JOURNAL_VERSION, init=False)

    def __post_init__(self):
        from .production_evidence import _contract_data

        gate.require(type(self.contract) in (gate.TrialContractV2, gate.TrialContract))
        original = _checked_trial_contract(self.contract, self.approval_key, self.account_id)
        object.__setattr__(self, "contract", original)
        object.__setattr__(self, "contract_fingerprint", fingerprint(_contract_data(original)))


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


def _journal_binding(value):
    from .spec_production import ProductionTrialBinding
    return type(value) in (JournalTrialBinding, ProductionTrialBinding)


def _production_binding(value):
    from .spec_production import ProductionTrialBinding
    return type(value) is ProductionTrialBinding


def _binding_mode(value):
    return "LIVE" if _production_binding(value) else "MOCK"



def _binding(worker):
    binding = worker.pa_trial
    if _production_binding(binding):
        from .spec_production import environment
        environment(worker.store, worker.s, worker.goal_planner_transport)
        gate.require(worker.store is worker._journal_trial_store
            and binding is worker._journal_trial_binding and not worker._journal_trial_drift
            and worker.s.quota_subject == binding.contract.quota_subject
            and worker.s.max_output_tokens == binding.contract.caps.max_output_tokens
            and worker.s.lease_seconds == binding.contract.caps.lease_seconds
            and fingerprint(binding.contract.model_dump()) == binding.contract_fingerprint)
        return binding
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
            and worker.s.lease_seconds == binding.contract.caps.lease_seconds
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


def _admission(worker, *, _source_out=None):
    def admitted(store, c, user, contract, key, stage, rid, version, fence):
        b = _binding(worker)
        gate.require(
            fingerprint(contract.model_dump()) == b.contract_fingerprint
            and key == b.approval_key
            and user == b.contract.principal_id
        )
        if _journal_binding(b):
            from . import production_trial_policy as policy
            context = policy.check_run(store, c, user, contract, key, stage, rid, version, fence, worker.id)
            if type(contract) is gate.PBTrialContract and stage == "cold":
                _pb_source(worker, c, b)
            current_source = _journal_source(store, c, b)
            if _source_out is not None:
                from .natural_spec_runtime import _model_source_key
                _source_out.update(identity=_model_source_key(current_source),
                                   expires_at=current_source.expires_at)
            if _production_binding(b):
                gate.require(time.time() < min(context.deadline, current_source.expires_at),
                             "Production admission expired during verification")
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


def _account(worker, b, *, connection=None):
    if _journal_binding(b):
        if connection is not None:
            gate.require(worker.store.owns_connection(connection) and connection.in_transaction())
            return _journal_source(worker.store, connection, b)
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


def check_commit(worker, c, run, *, _read_out=None, _model_out=None):
    if _model_out is not None:
        _model_out.clear()
    if _read_out is not None:
        previous = _read_out.pop("stamp", None)
        if type(previous) is _CommitReadback:
            previous.consumed = True
    read_entry = _commit_readback_entry(worker, c, run) if _read_out is not None else None
    b = _binding(worker)
    gate.require(
        run["principal_id"] == b.contract.principal_id
        and run["project_id"] == b.contract.project_id
    )
    if _journal_binding(b):
        source_out: dict = {}
        with worker.store.proof_authorities(c) as authorities:
            gate._approved(worker.store, c, b.contract.principal_id, b.contract, b.approval_key)
            context = _admission(worker, **({"_source_out": source_out} if _model_out is not None else {}))(
                worker.store, c, run["principal_id"], b.contract, b.approval_key,
                _stage(b, run), run["id"], run["version"], run["fence"])
        if _model_out is not None:
            gate.require(_production_binding(b) and type(b.contract) is gate.PBTrialContract
                         and context.stage == "cold")
            _model_out.update(approval=context.approval_fingerprint,
                phase=context.stage_fingerprint, requirements=context.requirements_fingerprint,
                source_identity=source_out["identity"], source_deadline=source_out["expires_at"])
        if read_entry is not None:
            from .pb_natural_specs import _source_reads_current
            token = c.info.get("pb_source_reads")
            if (_production_binding(b) and type(b.contract) is gate.PBTrialContract
                    and context.stage == "cold" and _source_reads_current(worker.store, c, token)):
                from .natural_trial_runs import associated_sql
                actual = c.execute(select(runs).where(runs.c.id == run["id"])).mappings().one()
                stamp = _CommitReadback(**read_entry,
                    approval_fingerprint=context.approval_fingerprint,
                    phase_fingerprint=context.stage_fingerprint, authorities=tuple(sorted(authorities)))
                if (stamp.binding is b and _commit_readback_unchanged(worker, c, run, stamp)
                        and fingerprint(dict(actual)) == stamp.run_fingerprint
                        and c.execute(select(runs.c.id).where(runs.c.id == run["id"], associated_sql())).first() is None
                        and _commit_readback_unchanged(worker, c, run, stamp)):
                    _read_out["stamp"] = stamp
        return
    gate._approved(worker.store, c, b.contract.principal_id, b.contract, b.approval_key)
    if type(b.contract) is gate.PBTrialContract and _stage(b, run) == "cold":
        _pb_source(worker, c, b)
    _account(worker, _binding(worker))


@dataclass
class _CommitReadback:
    """One local continuation of a successful full proof, never a stored permit."""
    worker: object
    store: object
    connection: object
    token: object
    binding: object
    settings: object
    settings_values: dict
    stop: object
    transport: object
    worker_id: str
    run_fingerprint: str
    approval_fingerprint: str
    phase_fingerprint: str | None
    authorities: tuple
    binding_fingerprint: str
    consumed: bool = False


def _commit_readback_entry(worker, c, run):
    from .pb_natural_specs import _source_reads_current
    b, token = worker.pa_trial, c.info.get("pb_source_reads")
    if (not _production_binding(b) or type(b.contract) is not gate.PBTrialContract
            or getattr(worker, "_journal_trial_store", None) is not worker.store
            or getattr(worker, "_journal_trial_binding", None) is not b
            or getattr(worker, "_journal_trial_drift", None) is not False
            or not _source_reads_current(worker.store, c, token)):
        return None
    return dict(worker=worker, store=worker.store, connection=c, token=token, binding=b,
        settings=worker.s, settings_values=dict(vars(worker.s)), stop=worker.stop,
        transport=worker.goal_planner_transport, worker_id=worker.id,
        run_fingerprint=fingerprint(dict(run)), binding_fingerprint=fingerprint(dict(
            contract=b.contract.model_dump(), key=b.approval_key, account=b.account_id,
            version=b.version, fingerprint=b.contract_fingerprint)))


def _commit_readback_unchanged(worker, c, run, stamp):
    from .pb_natural_specs import _source_reads_current
    return (worker is stamp.worker and worker.store is stamp.store
        and c is stamp.connection and worker.pa_trial is stamp.binding
        and getattr(worker, "_journal_trial_store", None) is stamp.store
        and getattr(worker, "_journal_trial_binding", None) is stamp.binding
        and getattr(worker, "_journal_trial_drift", None) is False
        and worker.s is stamp.settings and vars(worker.s) == stamp.settings_values
        and worker.stop is stamp.stop and worker.goal_planner_transport is stamp.transport
        and worker.id == stamp.worker_id
        and fingerprint(dict(contract=worker.pa_trial.contract.model_dump(),
            key=worker.pa_trial.approval_key, account=worker.pa_trial.account_id,
            version=worker.pa_trial.version, fingerprint=worker.pa_trial.contract_fingerprint)) == stamp.binding_fingerprint
        and fingerprint(dict(run)) == stamp.run_fingerprint
        and _source_reads_current(worker.store, c, stamp.token))


def check_commit_after_readback(worker, c, run, read_out, *, _tail_authorities=()):
    """Continue only this exact postwrite SQLite proof; otherwise reprove it all.

    The first check_commit has already proved the complete phase and source
    lineage. No write, transaction, settings or callback drift may separate it
    from this readback. Current consent, fixed source and actual authorities are
    still checked here; PostgreSQL and all other controllers use the full path.
    """
    stamp = read_out.pop("stamp", None)
    if type(stamp) is not _CommitReadback or stamp.consumed:
        return check_commit(worker, c, run)
    stamp.consumed = True

    def unchanged():
        return _commit_readback_unchanged(worker, c, run, stamp)

    if not unchanged():
        return check_commit(worker, c, run)
    b = _binding(worker)
    if not unchanged():
        return check_commit(worker, c, run)
    approval = gate._approved(worker.store, c, run["principal_id"], b.contract, b.approval_key)
    if not unchanged() or fingerprint(approval.model_dump()) != stamp.approval_fingerprint:
        return check_commit(worker, c, run)
    gate.require(gate._keys(c, run["principal_id"], gate.entity(b.contract), gate.PHASE) <= {"source", "cold"})
    accepted = gate._saved(c, run["principal_id"], gate.entity(b.contract), gate.PHASE,
        "cold", gate.StageApproveInput)
    gate.require(accepted.approval_key == b.approval_key
        and accepted.authority.run_id == run["id"] and accepted.authority.stage == "cold"
        and accepted.authority.runtime_id == run["runtime_id"]
        and fingerprint(accepted.authority.model_dump()) == accepted.expected_authority_fingerprint
        == stamp.phase_fingerprint)
    if not unchanged():
        return check_commit(worker, c, run)
    source = _journal_source(worker.store, c, b)
    if not unchanged():
        return check_commit(worker, c, run)
    worker.store.recheck_proof_authorities(c, {"_call_authorities":
        tuple(sorted(set(stamp.authorities).union(_tail_authorities)))})
    if not unchanged():
        return check_commit(worker, c, run)
    actual = c.execute(select(runs).where(runs.c.id == run["id"]).with_for_update()).mappings().one()
    at = time.time()
    gate._require_run_context_row(run["principal_id"], b.contract, "cold", actual,
        run["version"], run["fence"], approval, accepted.authority, at)
    gate.require(fingerprint(dict(actual)) == stamp.run_fingerprint
        and actual["worker_id"] == worker.id and not worker.stop.is_set()
        and at < source.expires_at,
        "Production readback ownership or finite interval changed")
    if not unchanged():
        return check_commit(worker, c, run)
    gate.require(not worker.stop.is_set() and time.time() < min(actual["lease_until"],
        actual["created_at"] + b.contract.caps.run_seconds, b.contract.expires_at, source.expires_at),
        "Production readback final interval ended")


def _journal_reads(worker, c):
    """Share complete proofs only in this original controller read segment."""
    from contextlib import nullcontext
    binding = getattr(worker, "pa_trial", None)
    ordinary = (binding is None and worker.store.test_only and worker.store.sqlite
        and worker.s.mode == "mock" and worker.s.live_enabled is False)
    if not ordinary and not _journal_binding(binding):
        return nullcontext()
    if not ordinary:
        _binding(worker)
    gate.require(worker.store.owns_connection(c) and c.in_transaction())
    from .pb_natural_specs import _source_reads
    return _source_reads(worker.store, c)


def check_terminal_commit(worker, c, run, state):
    """Original terminal transaction continuation; never a send/Run admission."""
    b = _binding(worker)
    if not _journal_binding(b):
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
    terminal_source = _journal_source(worker.store, c, b)
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
    if type(b.contract) is gate.PBTrialContract and stage == "cold":
        _pb_source(worker, c, b)
    _binding(worker)
    if _production_binding(b):
        gate.require(not worker.stop.is_set() and time.time() < min(run["lease_until"],
            b.contract.expires_at, run["created_at"] + b.contract.caps.run_seconds,
            terminal_source.expires_at), "Production terminal proof expired")


def _pb_source(worker, c, b):
    """Reprove original successful source, exact extraction and both actual chains.

    The existing full resolver shares this transaction: its source consent,
    complete Goals/Recipe and current authorities remain mandatory at every
    admission/commit. Its read-only receipt never becomes reusable authority.
    """
    if _production_binding(b):
        return _pb_source_bound(worker.store, c, b)
    from . import natural_source_archives as archive
    from .pb_natural_specs import _source_reads

    with _source_reads(worker.store, c):
        resolved = archive._resolve_trial_source(worker.store, c, b.contract.principal_id,
            b.contract, b.approval_key)
        _pb_archive_chain(worker, c, b, resolved)


def _pb_source_bound(store, c, b):
    from . import natural_source_archives as archive
    from .pb_natural_specs import _source_reads

    gate.require(_production_binding(b))
    with _source_reads(store, c):
        resolved = archive._resolve_trial_source(store, c, b.contract.principal_id,
            b.contract, b.approval_key)
        _pb_journal_archive_chain(store, c, b, resolved)


def _pb_accounting(store, c, user, contract, key):
    """Select original accounting from scalar markers, then reprove its authority.

    A marker selects a verifier only. Neither it nor this read returns a permit.
    Production has no fallback to the historical synthetic budget.
    """
    from .db import delivery_graph_requests
    from .production_trial_journal import KIND
    from .spec_production import VERSION, ProductionTrialBinding

    gate.require(type(contract) is gate.PBTrialContract and c.in_transaction())
    gate._approved(store, c, user, contract, key)
    generation = c.execute(select(runs.c.id).where(runs.c.principal_id == user,
        runs.c.project_id == contract.project_id, runs.c.runtime_id == contract.runtime_id,
        runs.c.request_key == contract.stage_keys.generate)).scalar_one_or_none()
    gate.require(generation is not None)
    fields = ("version", "trial_fingerprint", "approval_key", "account_id")
    markers = c.execute(select(*[attempts.c.parameters["pa_trial_binding"][k]
        .as_string().label(k) for k in fields]).where(attempts.c.run_id == generation)).mappings().all()
    if any(m["version"] == VERSION for m in markers):
        _pb_markers_from_facts(contract, key, markers)
        binding = ProductionTrialBinding(contract, key, markers[0]["account_id"])
        _journal_source(store, c, binding)
        state, _, _ = _journal_state(store, c, binding)
        source_id = _pb_prefix_source_from_facts(state)
        return binding, state, source_id
    # A lost/mixed production marker cannot reinterpret its journal as MOCK.
    gate.require(store.test_only and store.sqlite and c.execute(select(delivery_graph_requests.c.kind)
        .where(delivery_graph_requests.c.principal_id == user,
            delivery_graph_requests.c.app_id == contract.project_id,
            delivery_graph_requests.c.request_key == contract.trial_key,
            delivery_graph_requests.c.kind.in_([KIND, KIND + "_seal"]))).first() is None)
    ledger = budget.audit(store, c, user, budget.scope_for(contract, key))["ledger"]
    return None, ledger, ledger["stage_runs"].get("source")


@controlled
def _pb_journal_archive_chain(store, c, b, resolved):
    """Join production NS bytes to the exact original journal/capture chain."""
    receipt = resolved.public_receipt
    gate.require(_production_binding(b))
    state, _, _ = _journal_state(store, c, b)
    slots = [s for s in state.slots if s.identity.stage == "source"]
    gate.require(not state.halted and len(slots) == len(receipt["attempts"]) == 2
            and receipt["verification"] == "SPEC_PRODUCTION_CONTROLLER_ARCHIVE"
            and receipt["live_allowed"] is False)
    source = c.execute(select(runs).where(runs.c.id == receipt["source_run_id"])).mappings().one()
    for slot, proof in zip(slots, receipt["attempts"], strict=True):
        gate.require(slot.identity.run_id == source["id"]
                and slot.identity.attempt_id == proof["attempt_id"])
        _, capture, _, _ = _journal_chain(store, c, b, source, proof["attempt_id"])
        gate.require(slot.identity.wire_sha256 == proof["request_sha256"]
                and slot.identity.wire_bytes == proof["request_bytes"]
                and capture.raw_sha256 == proof["decoded_body_sha256"]
                and capture.raw_bytes == proof["decoded_body_bytes"]
                and capture.canonical_sha256 == proof["canonical_ascii_sha256"]
                and capture.canonical_ascii_bytes == proof["canonical_ascii_bytes"])


@controlled
def _pb_archive_chain(worker, c, b, resolved):
    """Join the existing actual NS archives to this controller's immutable sends."""
    if _production_binding(b):
        return _pb_journal_archive_chain(worker.store, c, b, resolved)
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
        _account(worker, _binding(worker), connection=c)
        resolved = archive._resolve_source_before_extraction(worker.store, c, user,
            b.contract, b.approval_key)
        gate.require(resolved.public_receipt["source_run_id"] == source_id)
        _pb_archive_chain(worker, c, b, resolved)
        result = pb._extract(worker.store, c, user, b.contract.project_id, source_id,
            body, gate._limits(b.contract))
        _pb_source(worker, c, b)
        _account(worker, _binding(worker), connection=c)
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


def wait_unreserved(worker, run_id, *, _heartbeat_state=None):
    """Wait only for a not-yet-reserved slot; original heartbeat and deadlines remain."""
    b = _binding(worker)
    if _heartbeat_state is not None:
        from .goal_applications import _check_heartbeat
        _check_heartbeat(_heartbeat_state)
    if _journal_binding(b):
        return _journal_wait(worker, b, run_id, _heartbeat_state=_heartbeat_state)
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
        if _heartbeat_state is not None:
            _check_heartbeat(_heartbeat_state)
        if worker.stop.is_set() or time.time() >= deadline:
            raise DomainError("BUDGET_EXHAUSTED", "Original trial waiting interval ended")
        worker.stop.wait(min(0.25, max(0, min(last + 60, deadline) - time.time())))
    if _heartbeat_state is not None:
        _check_heartbeat(_heartbeat_state)


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
    if _journal_binding(b):
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
    new = _journal_binding(b)
    slot = None if new else next(
        (s for s in budget._ledger(c, scope)["slots"] if s["reservation"]["request_key"] == aid),
        None,
    )
    if not new:
        if slot is None:
            raise DomainError("VERSION_CONFLICT", "Original trial slot missing")
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
        _production=_production_binding(b),
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
    if _journal_binding(b):
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


def request_captured(worker, run, aid, wire, original_guard, provider, *, _heartbeat_state=None):
    """Existing Intern adapter only; receipt facts precede original business acceptance."""
    gate.require(type(provider) is InternModel
        and provider.transport is worker.goal_planner_transport
        and (provider.transport is None if _production_binding(_binding(worker))
             else type(provider.transport) is httpx.MockTransport))
    if _journal_binding(_binding(worker)):
        return _journal_exchange(worker, run, aid, wire, original_guard, provider, _heartbeat_state)

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


def _metadata(c, run, aid, kind, *, _guard=None):
    """Late failure accounting reads digest/identity projections, never body_b64."""
    selected = gate._trial_result(c.execute(_JOURNAL_METADATA_PROJECTION.where(rows.c.principal_id == run['principal_id'], rows.c.app_id == run['id'], rows.c.request_key == aid, rows.c.kind.in_([kind, kind + '_seal']))), _guard)
    values = gate._trial_result([dict(r) for r in gate._trial_result(selected.mappings(), _guard)], _guard)
    if not values:
        return None
    gate.require(len(values) == 2 and {r.pop('kind') for r in values} == {kind, kind + '_seal'})
    gate.require(values[0] == values[1])
    value = values[0]
    gate.require(value['phase'] == ('RESERVED_REQUEST' if kind == REQUEST else 'RECEIVED_DECODED_BODY'))
    gate.require(value['run_id'] == run['id'] and value['attempt_id'] == aid and (value['key_attempt'] == aid) and (value['key_family'] == kind) and all((value[k] == run[k] for k in ('principal_id', 'project_id', 'runtime_id'))))
    anchors = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(events.c.data).where(events.c.run_id == run['id'], events.c.kind == 'PA_TRIAL_BODY', events.c.data['attempt_id'].as_string() == aid, events.c.data['family'].as_string() == kind)), _guard).scalars(), _guard).all(), _guard)
    gate.require(len(anchors) == 1 and all((anchors[0].get(k) == value[field] for k, field in (('decoded_sha256', 'sha256'), ('canonical_sha256', 'canonical_sha256'), ('byte_count', 'byte_count'), ('complete', 'complete'), ('omission', 'omission')))))
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


def settle_verified(worker, c, run, aid, raw, *, _model_after=None):
    if _model_after is not None:
        from .natural_spec_runtime import _ModelSettlementRead
        gate.require(type(_model_after) is _ModelSettlementRead)
        return _model_after.settle(worker, c, run, aid, raw)
    b = _identity(worker, c, run, aid)
    if _journal_binding(b):
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
    if _journal_binding(getattr(worker, "_journal_trial_binding", None)):
        # Receive already committed immutable accounting. No current binding,
        # duplicate settle or missing response may mint authority/refund here.
        b = worker._journal_trial_binding
        gate.require(worker._journal_trial_store.owns_connection(c))
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


def _journal_source(store, c, b, *, _guard=None):
    from .production_trial_policy import check_source, evidence
    from .production_trial_source import load_offline
    if gate._trial_result(_production_binding(b), _guard):
        from .spec_production import source
        return gate._trial_result(source(store, c, b), _guard)
    loaded = gate._trial_result(load_offline(store, c, b.contract.principal_id, b.contract, b.approval_key, b.account_id), _guard)
    return gate._trial_result(check_source(gate._trial_result(evidence.requirements_for(b.contract.principal_id, b.contract, b.approval_key), _guard), loaded.source, now=gate._trial_result(time.time(), _guard)), _guard)


def check_journal_claim(store, c, run, b):
    """Fixed original generic P-A queue, explicitly excluding qualified associations."""
    from .natural_trial_runs import associated_sql
    gate.require(_journal_binding(b) and (_production_binding(b) or store.test_only and store.sqlite)
        and run["principal_id"] == b.contract.principal_id
        and run["project_id"] == b.contract.project_id
        and run["status"] == "QUEUED" and not run["cancel_intent"]
        and c.execute(select(runs.c.id).where(runs.c.id == run["id"], associated_sql())).first() is None)
    gate._approved(store, c, run["principal_id"], b.contract, b.approval_key)
    _journal_source(store, c, b)
    stage = _stage(b, run)
    if stage == "generate":
        gate.require(run["request_key"] == b.contract.stage_keys.generate)
        gate._generation_context(store, c, run, b.contract)
    else:
        current, _ = gate._stage_current(store, c, run["principal_id"], b.contract, stage, run["id"])
        accepted = gate._saved(c, run["principal_id"], gate.entity(b.contract), gate.PHASE,
                              stage, gate.StageApproveInput)
        gate.require(current == accepted.authority and accepted.approval_key == b.approval_key
            and fingerprint(current.model_dump()) == accepted.expected_authority_fingerprint)
        gate._stage_review_window(current)
        if type(b.contract) is gate.PBTrialContract and stage == "cold":
            _pb_source_bound(store, c, b)
    frozen_seconds = store.frozen_contract(c, run).limits.run_seconds
    deadline = min(run["created_at"] + min(b.contract.caps.run_seconds, frozen_seconds),
                   b.contract.expires_at)
    gate.require(time.time() < deadline)
    return deadline


def _journal_state(store, c, b, *, _guard=None):
    from . import production_trial_journal as journal
    gate.require((gate._trial_result(_production_binding(b), _guard) or (store.test_only and store.sqlite)) and store.owns_connection(c))
    _, scope, request, quota_request, entity = gate._trial_result(journal._context(store, c, b.contract.principal_id, b.contract, b.approval_key, b.account_id), _guard)
    old = gate._trial_result(budget.scope_for(b.contract, b.approval_key), _guard)
    gate.require(gate._trial_result(budget._load(c, old.principal_id, old.project_id, budget.KIND, old.trial_key), _guard) is None)
    _, cursor, qr = gate._trial_result(journal._quota(c, quota_request, entity, create=False), _guard)
    _, state, revision = gate._trial_result(journal._ledger(c, scope, request, cursor, qr), _guard)
    return (state, cursor, revision)


def _journal_wait(worker, b, rid, *, _heartbeat_state=None):
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
    if _heartbeat_state is not None:
        from .goal_applications import _check_heartbeat
        _check_heartbeat(_heartbeat_state)
    while last is not None and time.time() < last + 60:
        _binding(worker)
        if _heartbeat_state is not None:
            from .goal_applications import _check_heartbeat
            _check_heartbeat(_heartbeat_state)
        if worker.stop.is_set() or time.time() >= deadline:
            raise DomainError("BUDGET_EXHAUSTED", "Original trial waiting interval ended")
        worker.stop.wait(min(0.25, max(0, min(last + 60, deadline) - time.time())))
    if _heartbeat_state is not None:
        _check_heartbeat(_heartbeat_state)


def _journal_owner(c, b, run, aid, *, _guard=None):
    header = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id, attempts.c.mode, *[attempts.c.parameters['pa_trial_binding'][k].as_string().label(k) for k in ('version', 'trial_fingerprint', 'approval_key', 'account_id', 'worker_id')], attempts.c.parameters['pa_trial_binding']['run_version'].as_integer().label('run_version'), attempts.c.parameters['pa_trial_binding']['fence'].as_integer().label('fence')).select_from(runs).join(attempts, attempts.c.run_id == runs.c.id).where(runs.c.id == run['id'], attempts.c.id == aid)), _guard).mappings(), _guard).first(), _guard)
    gate._trial_result(_journal_owner_from_facts(b, run, header, _guard=_guard), _guard)
    return header


def _journal_slot(store, c, b, run, aid, wire):
    from . import production_trial_policy as policy

    header = _journal_owner(c, b, run, aid)
    state, cursor, _ = _journal_state(store, c, b)
    slot = next((s for s in state.slots if s.identity.attempt_id == aid), None)
    if slot is None:
        raise DomainError("VERSION_CONFLICT", "Exact natural trial changed")
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
    _journal_slot_identity_from_facts(b, run, header, item, approval, phase_fp)
    return slot


def _journal_exchange(worker, run, aid, wire, original_guard, provider, heartbeat_state):
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
                                     expected_revision=revision, _heartbeat_state=heartbeat_state)


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
        payload = _journal_body_from_facts(b, run, aid, kind, scope, meta, saved)
        payloads.append(payload)
    wire, payload = payloads
    slot = _journal_slot(store, c, b, run, aid, wire)
    capture = sender._captured(c, run["principal_id"], slot.identity)
    _journal_capture_from_facts(slot, capture, payload)
    parsed = strict_json(payload, 131072)
    canonical, evidence = response_archive(parsed)
    response = _metadata(c, run, aid, RESPONSE)
    _journal_canonical_from_facts(response, capture, canonical, evidence, raw)
    actual = c.execute(select(attempts).where(attempts.c.run_id == run["id"],
                                               attempts.c.id == aid)).mappings().one()
    _journal_attempt_from_facts(b, wire, slot, actual)
    return slot, capture, parsed, actual


def _journal_attempt_from_facts(b, wire, slot, actual, *, _guard=None):
    """Bind the original Attempt after owner, full bodies/slot/capture/raw checks.

    Not a replacement for current authority, _journal_slot or full policy
    _bound: caller must retain its transaction and complete ledger validation.
    """
    params = actual['parameters']
    gate.require(actual['request_model'] == b.contract.model and actual['mode'] == gate._trial_result(_binding_mode(b), _guard) and (actual['reserved_tokens'] == len(wire) + params['max_tokens']) and (params['max_tokens'] == gate._trial_result(strict_json(wire, 32768), _guard)['max_tokens']) and (params['max_tokens'] <= b.contract.caps.max_output_tokens) and (params.get('generation_wire') == slot.identity.wire_sha256 and params.get('generation_fence') == slot.identity.fence if slot.identity.stage == 'generate' else params.get('natural_spec_wire', {}).get('sha256') == slot.identity.wire_sha256 and params['natural_spec_wire'].get('bytes') == len(wire) and (params['natural_spec'].get('fence') == slot.identity.fence) and (params['natural_spec'].get('run_version') == slot.identity.version)))


def journal_stage_accounted(store, c, user, contract, key, rid, stage):
    """Original current lineage calls this only after its full ownership gate."""
    _journal_stage_header(store, c, user, contract, key, rid, stage)
    actual = c.execute(select(attempts).where(attempts.c.run_id == rid)
                       .order_by(attempts.c.created_at, attempts.c.id)).mappings().all()
    gate.require(len(actual) == (3 if stage == "generate" else 2))
    markers = [a["parameters"].get("pa_trial_binding", {}) for a in actual]
    from .spec_production import VERSION as PRODUCTION_VERSION
    from .spec_production import ProductionTrialBinding
    gate.require(markers[0].get("version") in (JOURNAL_VERSION, PRODUCTION_VERSION)
        and all(m.get("version") == markers[0].get("version") for m in markers)
        and len({m.get("account_id") for m in markers}) == 1)
    binding_type = ProductionTrialBinding if markers[0].get("version") == PRODUCTION_VERSION else JournalTrialBinding
    b = binding_type(contract, key, markers[0].get("account_id"))
    gate.require(user == contract.principal_id)
    run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    state, _, _ = _journal_state(store, c, b)
    _stage_slots_from_facts(state, actual, rid, stage)
    for a in actual:
        slot, capture, parsed, checked = _journal_chain(store, c, b, run, a["id"])
        _stage_usage_from_facts(a, stage, slot, parsed, checked)
        if stage == "generate":
            gate.require(a["parameters"].get("generation_raw_evidence") == response_archive(parsed)[1]
                and a["parameters"].get("generation_received_raw") == response_archive(parsed)[0])
        else:
            from .natural_source_archives import REQUEST as NS_REQUEST
            from .natural_source_archives import RESPONSE as NS_RESPONSE
            from .natural_source_archives import _read
            _, original_wire = _read(c, user, run, a["id"], NS_REQUEST)
            body, archived = _read(c, user, run, a["id"], NS_RESPONSE)
            _stage_source_archive_from_facts(a, body, archived, original_wire, slot, capture, parsed)
            from .db import operations
            op = c.execute(select(operations.c.status).where(operations.c.run_id == rid,
                operations.c.id == a["parameters"]["natural_spec"]["operation_id"])).scalar_one()
            gate.require(op == "VERIFIED")


def _stage_slots_from_facts(state, actual, rid, stage, *, _guard=None):
    """Use full checked ledger and Attempt multisets after original stage gates.

    Caller keeps exact 3/2 stage count, marker/account checks, phase/ownership,
    current permissions and _journal_state. This is not a ledger verifier.
    """
    slots = [s for s in state.slots if s.identity.stage == stage]
    gate.require(not state.halted and len(slots) == len(actual) and ({s.identity.attempt_id for s in slots} == {a['id'] for a in actual}) and all((s.identity.run_id == rid for s in slots)))


def _stage_usage_from_facts(a, stage, slot, parsed, checked, *, _guard=None):
    """Original accounting comparison after the complete same-aid journal chain."""
    usage = gate._trial_result(normalize_usage(parsed), _guard)
    gate.require(checked == a and a['status'] == ('RECEIVED' if stage == 'generate' else 'VERIFIED') and (a['usage'] == usage) and (usage['status'] == 'known') and all((getattr(slot.settlement, k) == usage['tokens'].get(k) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'))))


def _stage_source_archive_from_facts(a, body, archived, original_wire, slot, capture, parsed, *, _guard=None):
    """Join checked NS bytes to checked controller bytes before Operation SELECT.

    Caller retains both ordered _read gates, the entire stage history and the
    original following VERIFIED Operation check. Matching hashes alone do not
    establish authority or replace the raw-byte comparison here.
    """
    gate.require(body.sha256 == capture.raw_sha256 and archived == gate._trial_result(base64.b64decode(capture.body_b64), _guard) and (body.canonical_sha256 == capture.canonical_sha256) and (gate._trial_result(gate._trial_result(hashlib.sha256(original_wire), _guard).hexdigest(), _guard) == slot.identity.wire_sha256) and (a['response'].get('received_raw') == gate._trial_result(response_archive(parsed), _guard)[0]) and (a['response'].get('raw_evidence') == gate._trial_result(response_archive(parsed), _guard)[1]))


def _journal_owner_from_facts(b, run, header, *, _guard=None):
    gate.require(header is not None and header['mode'] == gate._trial_result(_binding_mode(b), _guard) and (header['version'] == b.version) and (header['trial_fingerprint'] == b.contract_fingerprint) and (header['approval_key'] == b.approval_key) and (header['account_id'] == b.account_id) and (header['principal_id'] == b.contract.principal_id) and (header['project_id'] == b.contract.project_id) and all((header[k] == run[k] for k in ('principal_id', 'project_id', 'runtime_id'))))


def _journal_slot_identity_from_facts(b, run, header, item, approval, phase_fp, *, _guard=None):
    gate.require(item.run_id == run['id'] and item.runtime_id == run['runtime_id'] and (item.version == header['run_version']) and (item.fence == header['fence']) and (item.worker_id == header['worker_id']) and (item.stage == gate._trial_result(_stage(b, run), _guard)) and (item.approval_fingerprint == gate._trial_result(fingerprint(gate._trial_result(approval.model_dump(), _guard)), _guard)) and (item.stage_fingerprint == phase_fp))


def _journal_body_from_facts(b, run, aid, kind, scope, meta, saved, *, _guard=None):
    gate.require(saved['request'] == dict(trial=gate._trial_result(scope.model_dump(), _guard), attempt_id=aid, family=kind, wire_sha256=meta['wire_sha256']))
    body = gate._trial_result(BodyArchive.model_validate(saved['response']), _guard)
    if _guard is not None:
        _guard = gate._trial_typed_guard(_guard, [(BodyArchive, body, saved['response'])])
        _guard()
    if body.body_b64 is None:
        raise DomainError('VERSION_CONFLICT', 'Exact natural trial changed')
    payload = gate._trial_result(base64.b64decode(body.body_b64, validate=True), _guard)
    gate.require(gate._trial_result(_body(run, aid, payload, True, body.canonical_sha256, 'natural_source_request_body.v1' if kind == REQUEST else 'natural_source_response_body.v1', _production=gate._trial_result(_production_binding(b), _guard)), _guard) == body)
    gate.require(meta['sha256'] == gate._trial_result(gate._trial_result(hashlib.sha256(payload), _guard).hexdigest(), _guard))
    return payload


def _journal_stage_header(store, c, user, contract, key, rid, stage, *, _guard=None, _graph_read=None):
    gate.require(stage in ('generate', 'source', 'cold') and user == contract.principal_id)
    owner = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(runs.c.principal_id, runs.c.project_id, runs.c.runtime_id, runs.c.request_key, runs.c.status).where(runs.c.id == rid)), _guard).mappings(), _guard).first(), _guard)
    gate.require(owner is not None and owner['principal_id'] == user and (owner['project_id'] == contract.project_id))
    if stage == 'generate':
        gate.require(owner['runtime_id'] == contract.runtime_id and owner['request_key'] == contract.stage_keys.generate)
        from .goal_applications import source_scope_gate
        gate._trial_result(source_scope_gate(store, c, rid, **{'_graph_read': _graph_read} if _graph_read is not None else {}), _guard)
    else:
        phase = gate._trial_result(gate._saved(c, user, gate._trial_result(gate.entity(contract, **{'_guard': _guard} if _guard is not None else {}), _guard), gate.PHASE, stage, gate.StageApproveInput, **{'_guard': _guard} if _guard is not None else {}), _guard)
        if _guard is not None:
            value = gate.StageApproveInput.model_dump(phase)
            _guard()
            _guard = gate._trial_typed_guard(_guard, [(gate.StageApproveInput, phase, value)])
            _guard()
        gate.require(phase.approval_key == key and phase.authority.run_id == rid and (phase.authority.stage == stage) and (phase.authority.runtime_id == owner['runtime_id']) and (phase.authority.contract_fingerprint == gate._trial_result(fingerprint(gate._trial_result(contract.model_dump(), _guard)), _guard)) and (phase.expected_authority_fingerprint == gate._trial_result(fingerprint(gate._trial_result(phase.authority.model_dump(), _guard)), _guard)) and (owner['status'] == 'SUCCEEDED'))
        from .pa_spec_apps import job_scope_gate
        gate.require(gate._trial_result(job_scope_gate(store, c, user, rid, **{'_graph_read': _graph_read} if _graph_read is not None else {}), _guard))
        from .db import internal_app_runs, internal_run_bindings
        app_key = gate._trial_result(gate._trial_result(c.execute(select(internal_app_runs.c.request_key).select_from(internal_run_bindings).join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id == rid, internal_app_runs.c.principal_id == user, internal_app_runs.c.id == phase.authority.app_run_id, internal_app_runs.c.instance_id == phase.authority.instance_id)), _guard).scalar_one_or_none(), _guard)
        gate.require(app_key == getattr(contract.stage_keys, stage) and owner['request_key'] == 'internal:' + phase.authority.app_run_id)


def _graph_journal_state(graph, store, c, b):

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
    _models: list[tuple[type, object, dict]] = []
    _guard = gate._trial_typed_guard(_parent_pin, _models)
    try:
        _guard()
        gate.require(b is graph.binding)
        _guard()
        gate.require(gate._trial_result(_production_binding(b), _guard) and type(b.contract) is gate.PBTrialContract)
        value = gate._trial_result(_journal_state(store, c, b, _guard=_guard), _guard)
        _guard()
        state, cursor, revision = value
        from . import production_trial_policy as policy
        ledger_raw = gate._graph_trial_produced(graph, store, c, _models, policy.Ledger, state)
        cursor_raw = gate._graph_trial_produced(graph, store, c, _models, policy.AccountQuotaCursor, cursor)
        completed_raw = dict(ledger=ledger_raw, cursor=cursor_raw, revision=revision)
        if 'cold-trial:journal' in graph.inputs:
            gate.require(completed_raw == graph.inputs['cold-trial:journal'])
        else:
            graph.add('cold-trial:journal', completed_raw)
        _guard()
        return value
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_journal_chain(graph, store, c, b, run, aid, state, cursor, raw=None):
    """Original complete same-aid proof with one already loaded complete J.

    Fresh owned scalar gate, body/seal/event bytes, checked policy binding,
    capture and actual Attempt all remain. No source/stage ancestor is rebuilt.
    """

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
    _models: list[tuple[type, object, dict]] = []
    _guard = gate._trial_typed_guard(_parent_pin, _models)
    try:
        from . import production_trial_policy as policy
        from . import production_trial_sender as sender
        _guard()
        gate.require(b is graph.binding)
        gate._graph_trial_journal_models(graph, store, c, _models, state, cursor)
        _guard()
        header = gate._trial_result(_journal_owner(c, b, run, aid, _guard=_guard), _guard)
        scope = gate._trial_result(budget.scope_for(b.contract, b.approval_key), _guard)
        gate._graph_trial_produced(graph, store, c, _models, budget.Scope, scope)
        payloads = []
        for kind in (REQUEST, RESPONSE):
            meta = gate._trial_result(_metadata(c, run, aid, kind, _guard=_guard), _guard)
            gate.require(meta is not None and meta['trial_fp'] == b.contract_fingerprint and meta['complete'] and (meta['omission'] == 'NONE'))
            saved = gate._trial_result(budget._load(c, run['principal_id'], run['id'], kind, aid), _guard)
            payloads.append(gate._trial_result(_journal_body_from_facts(b, run, aid, kind, scope, meta, saved, _guard=_guard), _guard))
            _guard()
        wire, payload = payloads
        matches = tuple((s for s in state.slots if s.identity.attempt_id == aid))
        gate.require(len(matches) == 1, 'Exact natural trial changed')
        slot = matches[0]
        original, expected = gate._trial_result(policy._requirements(run['principal_id'], b.contract, b.approval_key, **{'_guard': _guard} if _guard is not None else {}), _guard)
        gate._graph_trial_produced(graph, store, c, _models, gate.PBTrialContract, original)
        gate._graph_trial_produced(graph, store, c, _models, policy.evidence.EvidenceRequirements, expected)
        gate._trial_result(policy._bound_from_checked_facts(store, c, run['principal_id'], original, expected, state, cursor, slot.identity, wire, _guard=_guard), _guard)
        approval = gate._trial_result(gate._saved(c, run['principal_id'], gate._trial_result(gate.entity(b.contract, **{'_guard': _guard} if _guard is not None else {}), _guard), gate.APPROVE, 'approve', gate.Approval, **{'_guard': _guard} if _guard is not None else {}), _guard)
        gate._graph_trial_produced(graph, store, c, _models, gate.Approval, approval)
        phase_fp = None
        if slot.identity.stage != 'generate':
            phase = gate._trial_result(gate._saved(c, run['principal_id'], gate._trial_result(gate.entity(b.contract, **{'_guard': _guard} if _guard is not None else {}), _guard), gate.PHASE, slot.identity.stage, gate.StageApproveInput, **{'_guard': _guard} if _guard is not None else {}), _guard)
            gate._graph_trial_produced(graph, store, c, _models, gate.StageApproveInput, phase)
            phase_fp = gate._trial_result(fingerprint(gate._trial_result(phase.authority.model_dump(), _guard)), _guard)
        gate._trial_result(_journal_slot_identity_from_facts(b, run, header, slot.identity, approval, phase_fp, _guard=_guard), _guard)
        capture = gate._trial_result(sender._captured(c, run['principal_id'], slot.identity), _guard)
        gate._graph_trial_produced(graph, store, c, _models, sender.Capture, capture)
        gate._trial_result(_journal_capture_from_facts(slot, capture, payload, _guard=_guard), _guard)
        parsed = gate._trial_result(strict_json(payload, 131072), _guard)
        canonical, evidence = gate._trial_result(response_archive(parsed), _guard)
        response = gate._trial_result(_metadata(c, run, aid, RESPONSE, _guard=_guard), _guard)
        gate._trial_result(_journal_canonical_from_facts(response, capture, canonical, evidence, raw, _guard=_guard), _guard)
        actual = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(attempts).where(attempts.c.run_id == run['id'], attempts.c.id == aid)), _guard).mappings(), _guard).one(), _guard)
        gate._trial_result(_journal_attempt_from_facts(b, wire, slot, actual, _guard=_guard), _guard)
        _guard()
        return (slot, capture, parsed, actual, wire, payload)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_stage_accounted(graph, store, c, b, state, cursor, rid, stage, *, _owned=None):
    """Complete Generate/Source V accounting, retaining every actual aid.

    Returns (full Run, ordered actual Attempts, ordered complete chains,
    ordered NS reads). No stage Authority is accepted as a substitute.
    """

    if stage=='source' and graph.phase=='post' and _owned is None and _SOURCE_OWNED_ENABLED:
        checker,code,defaults=_SOURCE_OWNED_CHECK
        if (_source_owned_code.current is not checker or checker.__code__ is not code
                or checker.__defaults__ is not defaults):
            raise DomainError('VERSION_CONFLICT','Source producer code changed')
        checker()

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
    _models: list[tuple[type, object, dict]] = []
    _guard = gate._trial_typed_guard(_parent_pin, _models)
    try:
        _guard()
        if _owned is not None:
            from .cold_accounted import _prewrite_mode
            _prewrite_mode(_owned, graph)._begin(graph, stage)
        gate.require(b is graph.binding)
        gate._graph_trial_journal_models(graph, store, c, _models, state, cursor)
        _guard()
        gate.require(stage in ('generate', 'source') and gate._trial_result(_production_binding(b), _guard))
        user, contract, key = (b.contract.principal_id, b.contract, b.approval_key)
        gate._trial_result(_journal_stage_header(store, c, user, contract, key, rid, stage, _guard=_guard, _graph_read=graph), _guard)
        actual = tuple(gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at, attempts.c.id)), _guard).mappings(), _guard).all(), _guard))
        gate.require(len(actual) == (3 if stage == 'generate' else 2))
        markers = [a['parameters'].get('pa_trial_binding', {}) for a in actual]
        gate.require(all((m.get('version') == b.version and m.get('account_id') == b.account_id and (m.get('trial_fingerprint') == b.contract_fingerprint) and (m.get('approval_key') == key) for m in markers)))
        run = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(runs).where(runs.c.id == rid)), _guard).mappings(), _guard).one(), _guard)
        gate._trial_result(_stage_slots_from_facts(state, actual, rid, stage, _guard=_guard), _guard)
        chains, ns_reads = ([], [])
        for a in actual:
            chain = gate._trial_result(_graph_journal_chain(graph, store, c, b, run, a['id'], state, cursor), _guard)
            from . import production_trial_policy as policy
            from . import production_trial_sender as sender
            gate._graph_trial_produced(graph, store, c, _models, policy.Slot, chain[0])
            gate._graph_trial_produced(graph, store, c, _models, sender.Capture, chain[1])
            slot, capture, parsed, checked, wire, payload = chain
            gate._trial_result(_stage_usage_from_facts(a, stage, slot, parsed, checked, _guard=_guard), _guard)
            if stage == 'generate':
                gate.require(a['parameters'].get('generation_raw_evidence') == gate._trial_result(response_archive(parsed), _guard)[1] and a['parameters'].get('generation_received_raw') == gate._trial_result(response_archive(parsed), _guard)[0])
            else:
                from . import natural_source_archives as archive
                from .db import operations
                request, original_wire = gate._trial_result(archive._read(c, user, run, a['id'], archive.REQUEST, _guard=_guard), _guard)
                gate._graph_trial_produced(graph, store, c, _models, archive.BodyArchive, request)
                body, archived = gate._trial_result(archive._read(c, user, run, a['id'], archive.RESPONSE, _guard=_guard), _guard)
                gate._graph_trial_produced(graph, store, c, _models, archive.BodyArchive, body)
                gate._trial_result(_stage_source_archive_from_facts(a, body, archived, original_wire, slot, capture, parsed, _guard=_guard), _guard)
                gate.require(original_wire == wire and archived == payload)
                op = gate._trial_result(gate._trial_result(c.execute(select(operations.c.status).where(operations.c.run_id == rid, operations.c.id == a['parameters']['natural_spec']['operation_id'])), _guard).scalar_one(), _guard)
                gate.require(op == 'VERIFIED')
                ns_reads.append((a['id'], request, original_wire, body, archived))
            chains.append(chain)
            _guard()
        completed_value = (run, actual, tuple(chains), tuple(ns_reads))
        completed_raw = gate._graph_trial_accounted_raw(graph, store, c, completed_value, _models)
        key = 'cold-trial:accounted-' + stage
        from . import _cold_source_packet as source_owned
        if stage=='source' and graph.phase=='post' and _owned is None and _SOURCE_OWNED_ENABLED:
            checker,code,defaults=_SOURCE_OWNED_CHECK
            if (source_owned.current is not checker or checker.__code__ is not code
                    or checker.__defaults__ is not defaults):
                raise DomainError('VERSION_CONFLICT','Source publisher code changed')
            checker()
            # The complete producer is finished. No legacy Source node escaped.
            try:
                return source_owned.publish(graph,completed_value,completed_raw,_guard)
            except _SOURCE_CAPACITY:
                # Bounded capacity failure before publication only retains all
                # original full checks; errors after publication invalidate.
                checker()
                gate.require(key not in graph.inputs)
                _guard()
                checker()
        if key in graph.inputs:
            gate.require(completed_raw == graph.inputs[key])
        else:
            graph.add(key, completed_raw)
        _guard()
        if _owned is not None:
            from .cold_accounted import _prewrite_mode
            return _prewrite_mode(_owned, graph)._completed(graph, stage, completed_value)
        return completed_value
    except BaseException:
        if _owned is not None:
            from .cold_accounted import _OwnedPrewriteMode
            if type(_owned) is _OwnedPrewriteMode and _owned.graph is graph:
                _owned.close()
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_pb_accounting(graph, store, c, b, generation, state, *, _owned=None):
    """Production J/Generate marker selection with all original fresh edges."""

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
    _models: list[tuple[type, object, dict]] = []
    _guard = gate._trial_typed_guard(_parent_pin, _models)
    try:
        _guard()
        gate.require(b is graph.binding)
        gate._graph_trial_journal_models(graph, store, c, _models, state)
        _guard()
        if _owned is not None:
            from .cold_accounted import _prewrite_mode
            _prewrite_mode(_owned, graph).assert_run('generate', generation)
        gate.require(gate._trial_result(_production_binding(b), _guard) and type(b.contract) is gate.PBTrialContract)
        user, contract, key = (b.contract.principal_id, b.contract, b.approval_key)
        gate._trial_result(gate._approved(store, c, user, contract, key, **{'_guard': _guard} if _guard is not None else {}), _guard)
        gate.require(generation['principal_id'] == user and generation['project_id'] == contract.project_id and (generation['runtime_id'] == contract.runtime_id) and (generation['request_key'] == contract.stage_keys.generate))
        markers = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(*[attempts.c.parameters['pa_trial_binding'][k].as_string().label(k) for k in ('version', 'trial_fingerprint', 'approval_key', 'account_id')]).where(attempts.c.run_id == generation['id'])), _guard).mappings(), _guard).all(), _guard)
        gate._trial_result(_pb_markers_from_facts(contract, key, markers, _guard=_guard), _guard)
        gate.require(all((m['account_id'] == b.account_id for m in markers)))
        gate._trial_result(_journal_source(store, c, b, _guard=_guard), _guard)
        _guard()
        return gate._trial_result(_pb_prefix_source_from_facts(state, _guard=_guard), _guard)
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _graph_pb_archive_chain(graph, store, c, b, state, resolved, source_facts, *, _accounted_test=None, _owned=None):
    """Join full NS/controller byte sets; not only their public digests."""

    def _parent_pin():
        gate._graph_trial_pin(graph, store, c)
    _models: list[tuple[type, object, dict]] = []
    _guard = gate._trial_typed_guard(_parent_pin, _models)
    try:
        _guard()
        gate.require(b is graph.binding)
        gate._graph_trial_journal_models(graph, store, c, _models, state)
        gate._graph_trial_accounted_models(graph, store, c, _models, source_facts, 'source', **{'_owned': _owned} if _owned is not None else {})
        _guard()
        from . import _cold_archive_packet as owned_archive
        # Exact native classification cannot invoke a replaced packet callback.
        if type(resolved) is tuple:
            gate.require(_owned is None and _accounted_test is None)
            checker, code, defaults, config = _OWNED_ARCHIVE_CHECK
            gate.require(owned_archive.current is checker and checker.__code__ is code
                and checker.__defaults__ is defaults and owned_archive._CONFIG is config)
            consumer_code = _OWNED_ARCHIVE_CONSUMERS
            checker(config, consumer_code)
            receipt, requests, responses = owned_archive.bound(graph, resolved)
            def owned_continuation():
                # The original dynamic/whole-graph/typed guard still runs.
                # A callback in it cannot replace the immutable-view semantics
                # before the next consumer access, even temporarily.
                _guard()
                gate.require(owned_archive.current is checker and checker.__code__ is code
                    and checker.__defaults__ is defaults and owned_archive._CONFIG is config)
                checker(config, consumer_code)
            _archive_chain_values(b, state, receipt, requests, responses, source_facts,
                _guard=owned_continuation, _source_graph=graph)
        elif _owned is None:
            _archive_chain_from_facts(b, state, resolved, source_facts, _guard=_guard)
        else:
            from . import cold_accounted
            gate.require(_accounted_test is None)
            _owned.assert_archive(b, state, resolved)  # assertion-only legacy comparison
            cold_accounted._archive_chain(source_facts, state, resolved)
        if _accounted_test is not None:
            from . import cold_accounted
            owned = cold_accounted._source_test_family(_accounted_test, graph)
            cold_accounted._archive_chain(owned, state, resolved)
        _guard()
    except BaseException:
        from .natural_spec_runtime import _ColdGraphRead
        if type(graph) is _ColdGraphRead:
            _ColdGraphRead.invalidate(graph)
        raise


def _archive_chain_from_facts(b, state, resolved, source_facts, *, _guard=None):
    """Original pure archive-family comparison; caller keeps every outer gate."""
    from ._cold_archive_packet import reject_experiment
    reject_experiment(resolved)
    return _archive_chain_values(b, state, resolved.public_receipt,
        resolved.request_bodies, resolved.response_bodies, source_facts, _guard=_guard)


def _archive_chain_values(b, state, receipt, requests, responses, source_facts, *, _guard=None, _source_graph=None):
    """Same complete joins; owned consumers read only immutable node views."""
    from . import _cold_source_packet as source_owned
    source_packet=source_facts if (_SOURCE_BINDING_TYPE is not None and type(source_facts) is _SOURCE_BINDING_TYPE) else None
    source, actual, chains, ns_reads = (source_owned.facts(_source_graph,source_packet)
        if source_packet is not None else source_facts)
    slots = [s for s in state.slots if s.identity.stage == 'source']
    gate.require(gate._trial_result(_production_binding(b), _guard) and (not state.halted) and (len(slots) == len(receipt['attempts']) == len(chains) == len(ns_reads) == 2) and (receipt['verification'] == 'SPEC_PRODUCTION_CONTROLLER_ARCHIVE') and (receipt['live_allowed'] is False) and (receipt['source_run_id'] == source['id']))
    for slot, proof in gate._trial_result(zip(slots, receipt['attempts'], strict=True), _guard):
        matching = tuple((chain for chain in chains if chain[3]['id'] == proof['attempt_id']))
        gate.require(len(matching) == 1)
        linked, capture, parsed, checked, wire, payload = matching[0]
        if source_packet is not None:
            source_owned.slot_join(_source_graph,source_packet,state,linked,proof['attempt_id'],_guard)
        gate.require((source_packet is not None or linked == slot) and checked in actual and (slot.identity.run_id == source['id']) and (slot.identity.attempt_id == proof['attempt_id']) and (slot.identity.wire_sha256 == proof['request_sha256']) and (slot.identity.wire_bytes == proof['request_bytes']) and (capture.raw_sha256 == proof['decoded_body_sha256']) and (capture.raw_bytes == proof['decoded_body_bytes']) and (capture.canonical_sha256 == proof['canonical_ascii_sha256']) and (capture.canonical_ascii_bytes == proof['canonical_ascii_bytes']))
        index = receipt['attempts'].index(proof)
        gate.require(requests[index] == wire and responses[index] == payload)


def _journal_capture_from_facts(slot, capture, payload, *, _guard=None):
    gate.require(slot.accepted and slot.attempted and (capture is not None) and (slot.settlement == capture.outcome) and capture.complete and (capture.raw_sha256 == gate._trial_result(gate._trial_result(hashlib.sha256(payload), _guard).hexdigest(), _guard)) and (capture.body_b64 == gate._trial_result(gate._trial_result(base64.b64encode(payload), _guard).decode('ascii'), _guard)))


def _journal_canonical_from_facts(response, capture, canonical, evidence, raw, *, _guard=None):
    gate.require(canonical is not None and response['canonical_sha256'] == evidence['sha256'] == capture.canonical_sha256 and (capture.canonical_ascii_bytes == evidence['bytes']))
    if raw is not None:
        gate.require(gate._trial_result(response_archive(raw), _guard) == (canonical, evidence))


def _pb_markers_from_facts(contract, key, markers, *, _guard=None):
    from .spec_production import VERSION
    gate.require(len(markers) == 3 and all((m['version'] == VERSION and m['trial_fingerprint'] == gate._trial_result(fingerprint(gate._trial_result(contract.model_dump(), _guard)), _guard) and (m['approval_key'] == key) for m in markers)) and (len({m['account_id'] for m in markers}) == 1))


def _pb_prefix_source_from_facts(state, *, _guard=None):
    first = [s for s in state.slots if s.identity.stage in ('generate', 'source')]
    source_ids = {s.identity.run_id for s in first if s.identity.stage == 'source'}
    gate.require(not state.halted and len(first) == 5 and all((s.accepted for s in first)) and (len(source_ids) == 1))
    return next(iter(source_ids))

_OWNED_ARCHIVE_CONSUMERS = _owned_archive_code.witness(globals(),
    ('_graph_pb_archive_chain', '_archive_chain_values'))


from . import _cold_source_packet as _source_owned_code
# Exact independently reviewed Source fact-family closure. Reservation preflight
# and the outer Worker/runtime read-scope factory are different lifecycle
# boundaries; they retain their original checks and are not callee substitutes
# inside this ownership transfer.
_source_owned_code.register(2,globals(),(
    '_graph_stage_accounted','_graph_journal_state','_graph_pb_accounting',
    '_graph_pb_archive_chain','_archive_chain_values','_archive_chain_from_facts',
    '_binding_mode','_graph_journal_chain','_journal_attempt_from_facts',
    '_journal_body_from_facts','_journal_canonical_from_facts','_journal_capture_from_facts',
    '_journal_owner','_journal_owner_from_facts','_journal_slot_identity_from_facts',
    '_journal_source','_journal_stage_header','_journal_state','_metadata',
    '_pb_markers_from_facts','_pb_prefix_source_from_facts','_production_binding',
    '_stage','_stage_slots_from_facts','_stage_source_archive_from_facts',
    '_stage_usage_from_facts','normalize_usage','response_archive','strict_json','fingerprint'),
    constants=('_SOURCE_OWNED_CHECK','_SOURCE_BINDING_TYPE','_SOURCE_OWNED_ENABLED','_SOURCE_CAPACITY'))
