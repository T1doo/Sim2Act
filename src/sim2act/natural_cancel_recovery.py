"""Close cancelled Cold runs from durable received/accounted evidence only.

No current material read, model call, source resolver or business replay. The
expired original owner's response is rejected without changing its accounting.
"""
import base64
import copy
import hashlib
import time

from sqlalchemy import exists, select, update
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

from . import natural_live_admission as gate
from . import natural_spec_runtime as model
from . import natural_specs as codec
from . import pa_spec_apps as spec
from . import pa_trial_dispatch as trial
from . import pb_natural_uses as uses
from .db import (attempts, delivery_graph_requests, events, fingerprint,
                 internal_app_runs, operation_intents, operations, runs)
from .errors import DomainError
from .model import normalize_usage
from .spec_production import ProductionTrialBinding, VERSION

SCAN_LIMIT = 16
ERROR = 'OWNER_CANCELLED_KNOWN_RESPONSE'


def _chain(store, c, binding, job, aid):
    """Complete historical chain for rejection only, never business acceptance.

    Normal trial._journal_chain requires slot.accepted. A cancelled receive may
    have recorded known cost with accepted=False after revocation/expiry. This
    separate control path preserves every body/slot/capture/usage join while
    gaining no permission to verify an operation or publish a result.
    """
    from . import natural_trial_budget as budget
    from . import production_trial_sender as sender
    from .contracts import strict_json
    trial._journal_owner(c, binding, job, aid)
    scope = budget.scope_for(binding.contract, binding.approval_key)
    payloads = []
    response = None
    for kind in (trial.REQUEST, trial.RESPONSE):
        meta = trial._metadata(c, job, aid, kind)
        spec.require(meta is not None and meta['trial_fp'] == binding.contract_fingerprint
            and meta['complete'] and meta['omission'] == 'NONE')
        saved = budget._load(c, job['principal_id'], job['id'], kind, aid)
        payloads.append(trial._journal_body_from_facts(binding, job, aid, kind, scope, meta, saved))
        if kind == trial.RESPONSE:response = meta
    wire, payload = payloads
    slot = trial._journal_slot(store, c, binding, job, aid, wire)
    capture = sender._captured(c, job['principal_id'], slot.identity)
    spec.require(slot.attempted and capture is not None and slot.settlement == capture.outcome
        and capture.complete and capture.raw_sha256 == hashlib.sha256(payload).hexdigest()
        and capture.body_b64 == base64.b64encode(payload).decode('ascii'))
    parsed = strict_json(payload, 131072)
    canonical, evidence = trial.response_archive(parsed)
    response = trial._metadata(c, job, aid, trial.RESPONSE)
    trial._journal_canonical_from_facts(response, capture, canonical, evidence, None)
    actual = c.execute(select(attempts).where(attempts.c.run_id == job['id'], attempts.c.id == aid)).mappings().one()
    trial._journal_attempt_from_facts(binding, wire, slot, actual)
    return slot, capture, parsed, actual


def _binding(c, job, rows, meta):
    markers = [row['parameters']['pa_trial_binding'] for row in rows]
    first = markers[0]
    spec.require(first['version'] == VERSION and all(
        all(marker[k] == first[k] for k in ('version', 'trial_fingerprint', 'approval_key', 'account_id'))
        for marker in markers))
    eid = c.execute(select(delivery_graph_requests.c.app_id).where(
        delivery_graph_requests.c.principal_id == job['principal_id'],
        delivery_graph_requests.c.kind == gate.SCOPE,
        delivery_graph_requests.c.request_key == 'scope',
        delivery_graph_requests.c.request_fingerprint == first['trial_fingerprint'])).scalar_one()
    contract = gate._saved(c, job['principal_id'], eid, gate.SCOPE, 'scope', gate.PBTrialContract)
    binding = ProductionTrialBinding(contract, first['approval_key'], first['account_id'])
    spec.require(binding.contract_fingerprint == first['trial_fingerprint']
        and gate.entity(contract) == eid and contract.principal_id == job['principal_id']
        and contract.project_id == job['project_id'] and trial._stage(binding, job) == 'cold')
    phase = gate._saved(c, job['principal_id'], eid, gate.PHASE, 'cold', gate.StageApproveInput)
    authority = phase.authority
    spec.require(phase.approval_key == binding.approval_key and authority.stage == 'cold'
        and authority.run_id == job['id'] and authority.runtime_id == job['runtime_id']
        and authority.app_run_id == meta.app_run_id and authority.instance_id == meta.instance_id
        and authority.contract_fingerprint == binding.contract_fingerprint
        and phase.expected_authority_fingerprint == fingerprint(authority.model_dump()))
    return binding


def _received(store, c, job, meta):
    from .contracts import AppManifest
    from .db import internal_releases
    from .natural_source_archives import REQUEST, RESPONSE, _read
    from .project_check_recovery import known_receipts

    manifest = c.execute(select(internal_releases.c.snapshot['draft']['candidate']['manifest'])
        .where(internal_releases.c.id == meta.release_id)).scalar_one()
    rows = model.counters(c, job, AppManifest.model_validate(manifest))
    spec.require(bool(rows) and all(row['status'] in {'RECEIVED', 'VERIFIED', 'REJECTED_KNOWN'}
                                  for row in rows))
    binding = _binding(c, job, rows, meta)
    ledger, _, revision = trial._journal_state(store, c, binding)
    ledger_witness = (ledger.model_dump_json(), revision)
    closed = []
    for row in rows:
        slot, capture, parsed, checked = _chain(store, c, binding, job, row['id'])
        usage = normalize_usage(parsed)
        spec.require(dict(checked) == dict(row) and slot.identity.stage == 'cold'
            and slot.attempted and slot.settlement is not None
            and slot.settlement.outcome == 'RECEIVED' and usage['status'] == 'known'
            and row['usage'] == usage and all(getattr(slot.settlement, k) == usage['tokens'][k]
                for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')))
        _, wire = _read(c, job['principal_id'], job, row['id'], REQUEST)
        body, payload = _read(c, job['principal_id'], job, row['id'], RESPONSE)
        trial._stage_source_archive_from_facts(row, body, payload, wire, slot, capture, parsed)
        info = row['parameters']['natural_spec']
        op = c.execute(select(operations).where(operations.c.id == info['operation_id'],
            operations.c.run_id == job['id']).with_for_update()).mappings().one()
        intent = c.execute(select(operation_intents.c.request).where(
            operation_intents.c.operation_id == op['id'])).scalar_one()
        spec.require(op['tool_ref'] in codec.MODEL_KINDS and intent == info['intent']
            and fingerprint(intent) == op['fingerprint'] and op['call_id'] == info['step_id'])
        if row['status'] != 'RECEIVED':
            continue
        spec.require(op['status'] == 'DISPATCHED' and op['receipt'] is None)
        changed = c.execute(update(attempts).where(attempts.c.id == row['id'],
            attempts.c.run_id == job['id'], attempts.c.status == 'RECEIVED',
            attempts.c.parameters == row['parameters'], attempts.c.response == row['response'],
            attempts.c.usage == row['usage']).values(status='REJECTED_KNOWN'))
        spec.require(changed.rowcount == 1)
        changed = c.execute(update(operations).where(operations.c.id == op['id'],
            operations.c.run_id == job['id'], operations.c.status == 'DISPATCHED',
            operations.c.fingerprint == op['fingerprint'], operations.c.receipt.is_(None))
            .values(status='REJECTED_KNOWN'))
        spec.require(changed.rowcount == 1)
        store.event(c, job['id'], 'NS_REJECTED', dict(attempt_id=row['id'],
            operation_id=op['id'], error=ERROR,
            attempt_fingerprint=fingerprint({**dict(row), 'status': 'REJECTED_KNOWN'})))
        closed.append(row['id'])
    # Other tools/unknown sends, duplicate anchors and incomplete prior receipts
    # must roll back the whole tentative rejection as well as terminal metadata.
    receipts = known_receipts(c, job, meta)
    spec.require(not store.has_unknown(c, job['id']))
    ledger, _, revision = trial._journal_state(store, c, binding)
    spec.require((ledger.model_dump_json(), revision) == ledger_witness)
    return closed, receipts, ledger_witness


def recover_cancelled_cold(store, *, scan=None):
    scan = {} if scan is None else scan
    eligible_attempt = exists(select(attempts.c.id).where(attempts.c.run_id == runs.c.id,
        attempts.c.parameters['pa_trial_binding']['version'].as_string() == VERSION,
        attempts.c.parameters['natural_spec']['operation_id'].as_string().is_not(None)))
    with store.tx() as c:
        query = select(runs.c.id).where(runs.c.status == 'RECONCILING',
            runs.c.cancel_intent.is_(True), runs.c.lease_until <= time.time(), eligible_attempt)
        if scan.get('after') is not None:
            query = query.where(runs.c.id > scan['after'])
        ids = c.execute(query.order_by(runs.c.id).limit(SCAN_LIMIT)).scalars().all()
    scan['after'] = ids[-1] if ids else None
    for rid in ids:
        try:
            with store.tx() as c:
                owner = c.execute(select(runs.c.principal_id, runs.c.project_id)
                                  .where(runs.c.id == rid)).mappings().one()
                store.lock_project(c, owner['principal_id'], owner['project_id'])
                job = dict(c.execute(select(runs).where(runs.c.id == rid)
                                     .with_for_update()).mappings().one())
                original_job = copy.deepcopy(job)
                spec.require(job['status'] == 'RECONCILING' and job['cancel_intent']
                    and job['lease_until'] <= time.time() and job['result'] is None
                    and all(job[k] == owner[k] for k in owner))
                scoped = uses.control_scope(store, c, job['principal_id'], rid, lock=True)
                spec.require(scoped is not None)
                _, app = scoped
                meta, sealed = uses.pair(c, job['principal_id'], rid, spec.RUN_META,
                                         'accepted', uses.RunScopeInput)
                spec.require(meta.model_dump() == sealed)
                original_meta = copy.deepcopy(sealed)
                app_row = copy.deepcopy(dict(c.execute(select(internal_app_runs)
                    .where(internal_app_runs.c.id == app['id'])).mappings().one()))
                state = app_row['status']
                spec.require(state == 'RECONCILING')
                closed, receipts, ledger_witness = _received(store, c, job, meta)
                changed = c.execute(update(runs).where(runs.c.id == rid,
                    runs.c.status == 'RECONCILING', runs.c.cancel_intent.is_(True),
                    runs.c.version == job['version'], runs.c.fence == job['fence'],
                    runs.c.worker_id == job['worker_id'], runs.c.lease_until == job['lease_until'],
                    runs.c.lease_until <= time.time()).values(status='CANCELLED',
                        version=job['version'] + 1, fence=job['fence'] + 1, lease_until=0))
                spec.require(changed.rowcount == 1)
                changed = c.execute(update(internal_app_runs).where(
                    internal_app_runs.c.id == app['id'], internal_app_runs.c.status == state,
                    internal_app_runs.c.principal_id == meta.principal_id,
                    internal_app_runs.c.instance_id == meta.instance_id,
                    internal_app_runs.c.release_id == meta.release_id,
                    internal_app_runs.c.fingerprint == app['fingerprint']).values(status='CANCELLED'))
                spec.require(changed.rowcount == 1)
                store.event(c, rid, 'COLD_CANCEL_RECOVERED', dict(status='CANCELLED',
                    reason=ERROR, previous_version=job['version'], version=job['version'] + 1,
                    previous_fence=job['fence'], fence=job['fence'] + 1,
                    received_closed=closed, receipts_preserved=True, new_model_requests=0,
                    attempts=[dict(id=r['id'], fingerprint=fingerprint(dict(r))) for r in receipts]))
                store.event(c, rid, 'STATE', dict(status='CANCELLED', error=job['error']))
                # Event callbacks cannot silently change the terminal owner or
                # accepted receipt evidence before the atomic commit.
                final = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
                spec.require(dict(final) == {**original_job, 'status':'CANCELLED',
                    'version':original_job['version']+1, 'fence':original_job['fence']+1, 'lease_until':0})
                # Rejoin the complete historical bodies, capture, ledger and
                # intent after callbacks, too. All rows are now known: this
                # second pass cannot emit another rejection or alter history.
                extra, final_receipts, final_ledger = _received(store, c, final, meta)
                spec.require(extra == [] and final_ledger == ledger_witness
                    and [dict(r) for r in final_receipts] == [dict(r) for r in receipts])
                final_scope = uses.control_scope(store, c, job['principal_id'], rid, lock=True)
                spec.require(final_scope is not None)
                header, final_app = final_scope
                spec.require(header == {key: final[key] for key in header}
                    and final_app == app)
                final_meta, final_seal = uses.pair(c, job['principal_id'], rid, spec.RUN_META,
                    'accepted', uses.RunScopeInput)
                spec.require(final_meta.model_dump() == final_seal == original_meta)
                final_row = c.execute(select(internal_app_runs)
                    .where(internal_app_runs.c.id == app['id'])).mappings().one()
                spec.require(dict(final_row) == {**app_row, 'status':'CANCELLED'})
            return True
        except (DomainError, ValueError, KeyError, TypeError, NoResultFound, MultipleResultsFound):
            # Catch OUTSIDE the transaction: a failed late proof rolls back
            # every rejection, anchor and control write, not just Run metadata.
            continue
    return False
