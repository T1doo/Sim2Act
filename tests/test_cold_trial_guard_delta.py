"""Isolated synthetic boundary units, not a complete Stage proof or trial permit.

Reuses existing local SQLite pin/release fixtures;
no Worker construction, claim, model, HTTP, sender, J or full P-B chain.
"""

import base64
import copy
import hashlib
import inspect
import json
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import event, insert, select
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope
from test_cold_release_stages import saved as saved

from sim2act import app_jobs, text_continuations
from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as dispatch
from sim2act import pb_natural_specs as pb
from sim2act import production_trial_policy as policy
from sim2act import production_trial_sender as sender
from sim2act.db import Store, fingerprint, internal_instances, internal_releases, new_id, runs
from sim2act.errors import DomainError


@pytest.mark.parametrize('where', ['input', 'phase', 'locked-row'])
def test_graph_run_context_rejects_each_wrong_run_join_before_next_consumer(
        local_origin, monkeypatch, where):
    f, calls = local_origin, []
    rid, other = new_id('run'), new_id('run')
    stage_facts = ({'id': other if where == 'input' else rid},) + (None,) * 8
    f.inputs['stage_facts'] = stage_facts
    key = f.worker.pa_trial.approval_key
    # Explicit isolated stand-ins stop at the identity join under test. These
    # cannot produce or claim a valid Authority, RunCheck or admitted execution.
    phase = SimpleNamespace(run_id=other if where == 'phase' else rid)
    accepted = SimpleNamespace(approval_key=key)

    def approved(*args, **kwargs):
        calls.append('approval')
        return SimpleNamespace()

    def staged(*args, **kwargs):
        calls.append('phase')
        return phase, stage_facts[0]

    def accepted_join(*args, **kwargs):
        calls.append('accepted-join')

    def locked(*args, **kwargs):
        calls.append('locked-row')
        return {'id': other}

    def row_consumer(*args, **kwargs):
        pytest.fail('Wrong Run identity reached full row consumer')

    # This fixture isolates the original Run joins, not complete Stage proof.
    # New full-cohort boundaries use explicit stand-ins only in this test;
    # actual typed/raw drift is tested separately below without those stubs.
    monkeypatch.setattr(gate, '_graph_trial_stage_raw', lambda *a, **k: None)
    monkeypatch.setattr(gate, '_graph_trial_stage_models', lambda *a, **k: None)
    monkeypatch.setattr(gate, '_graph_trial_produced', lambda *a, **k: None)
    monkeypatch.setattr(gate, '_approved', approved)
    monkeypatch.setattr(gate, '_keys', lambda *a, **k: set())
    monkeypatch.setattr(gate, '_saved', lambda *a, **k: accepted)
    monkeypatch.setattr(gate, '_graph_stage_current', staged)
    monkeypatch.setattr(gate, '_stage_accepted_from_facts', accepted_join)
    monkeypatch.setattr(gate, '_run_context_row', locked)
    monkeypatch.setattr(gate, '_require_run_context_row', row_consumer)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as caught:
            with read_scope(f, c) as guard:
                gate._graph_run_context(guard, f.store, c, f.user,
                    f.worker.pa_trial.contract, key, 'cold', rid, 1, 1, stage_facts)
    assert caught.value.code == 'VERSION_CONFLICT' and not guard.active
    assert calls == {'input': [], 'phase': ['approval', 'phase'],
        'locked-row': ['approval', 'phase', 'accepted-join', 'locked-row']}[where]


@pytest.fixture
def stage_instance(saved):
    f = saved
    f.iid = new_id('instance')
    with f.store.tx() as c:
        c.execute(insert(internal_instances).values(id=f.iid,
            principal_id=f.user, project_id=f.draft['project_id'],
            source_app_id=f.draft['id'], runtime_id=f.draft['runtime_id'],
            release_id=f.rid, revision=1, data_version=0, history=[]))
        f.pointer_release = dict(c.execute(select(internal_releases).where(
            internal_releases.c.id == f.rid)).mappings().one())
    f.pointer_job = dict(project_id=f.draft['project_id'], runtime_id=f.draft['runtime_id'])
    f.pointer_snapshot = dict(instance_id=f.iid)
    f.inputs['pointer'] = (f.pointer_release, f.pointer_job, f.pointer_snapshot)
    return f


def test_trial_stage_release_gate_drift_reads_zero_release_bodies(stage_instance, monkeypatch):
    f, bodies = stage_instance, []

    def drift(*args):
        f.worker.s = copy.copy(f.worker.s)

    def after_sql(c, cursor, statement, params, context, executemany):
        if 'FROM internal_releases' in statement:
            bodies.append(statement)

    monkeypatch.setattr(text_continuations, 'release_gate', drift)
    event.listen(f.store.engine, 'after_cursor_execute', after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError):
                with read_scope(f, c) as guard:
                    def pin():
                        gate._graph_trial_pin(guard, f.store, c)
                    gate._stage_instance_after_bound(f.store, c, f.user,
                        f.draft['project_id'], f.pointer_job, f.pointer_snapshot,
                        f.pointer_release, c.info.get('source_proof_write_epoch', 0),
                        _guard=pin, _graph_read=guard)
        assert not bodies and not guard.active
    finally:
        event.remove(f.store.engine, 'after_cursor_execute', after_sql)


def test_trial_approval_sql_drift_stops_before_any_paired_payload(local_origin, monkeypatch):
    f, bodies, changed = local_origin, [], [False]

    def after_sql(c, cursor, statement, params, context, executemany):
        if 'FROM delivery_graph_requests' in statement:
            f.inputs['history'].append({'id': 'drift', 'body': b'changed'})
            changed[0] = True

    def payload(*args, **kwargs):
        bodies.append('pair')
        pytest.fail('Approval payload was read after the metadata SQL drift')

    # The current material/Goal protocol is outside this boundary test. Keep the
    # actual original _approved -> _keys SQL -> guard -> _saved ordering.
    monkeypatch.setattr(gate, '_current', lambda *a, **k: None)
    monkeypatch.setattr(gate, 'pair', payload)
    event.listen(f.store.engine, 'after_cursor_execute', after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError):
                with read_scope(f, c) as guard:
                    def pin():
                        gate._graph_trial_pin(guard, f.store, c)
                    gate._approved(f.store, c, f.user, f.worker.pa_trial.contract,
                        f.worker.pa_trial.approval_key, _guard=pin)
        assert changed[0] and not bodies and not guard.active
    finally:
        event.remove(f.store.engine, 'after_cursor_execute', after_sql)


def test_archive_decode_guard_preserves_original_valueerror_identity(local_origin, monkeypatch):
    f, decoded = local_origin, [False]
    original = ValueError('synthetic successful-decode guard failure')
    job = dict(id=new_id('run'), principal_id=f.user, project_id=f.draft['project_id'],
        runtime_id=f.draft['runtime_id'])
    aid = new_id('attempt')
    body = archive._body(job, aid, b'{}', True, None, archive.RESPONSE)
    anchors = [dict(attempt_id=aid, archive_fingerprint=fingerprint(body.model_dump()))]
    decode = archive.base64.b64decode

    def observed_decode(*args, **kwargs):
        value = decode(*args, **kwargs)
        decoded[0] = True
        return value

    monkeypatch.setattr(archive.base64, 'b64decode', observed_decode)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with read_scope(f, c) as guard:
                def pin():
                    if decoded[0]:
                        raise original
                    gate._graph_trial_pin(guard, f.store, c)
                archive._body_payload_from_facts(body, anchors, aid, _guard=pin)
    assert decoded[0] and caught.value is original and not guard.active


@pytest.fixture
def typed_trial_inputs(local_origin):
    """Exact typed values for continuity only; no policy or Stage is admitted.

    Adversarial callbacks use object.__setattr__ to exercise the consumer pin
    even though the original EvidenceData values forbid ordinary assignment.
    """
    f = local_origin
    contract, key = f.worker.pa_trial.contract, f.worker.pa_trial.approval_key
    expected = policy.evidence.requirements_for(f.user, contract, key)
    wire = b'{"synthetic_continuity_only":true}'
    identity = policy.ReservationIdentity(
        requirements_fingerprint=fingerprint(expected.model_dump()),
        approval_fingerprint='a' * 64, stage='generate', run_id=new_id('run'),
        runtime_id=contract.runtime_id, version=1, fence=1, worker_id=f.worker.id,
        account_id=f.worker.pa_trial.account_id, quota_subject=expected.quota_subject,
        attempt_id=new_id('attempt'), wire_sha256=hashlib.sha256(wire).hexdigest(),
        wire_bytes=len(wire))
    ledger = policy.Ledger(scope=expected, account_id=identity.account_id)
    cursor = policy.AccountQuotaCursor(account_id=identity.account_id,
        quota_subject=expected.quota_subject)
    return SimpleNamespace(f=f, contract=contract, expected=expected,
        wire=wire, identity=identity, ledger=ledger, cursor=cursor)


@pytest.mark.parametrize('changed', ['none', 'ledger', 'cursor'])
def test_actual_bound_callback_checks_typed_j_before_project_consumption(
        typed_trial_inputs, monkeypatch, changed):
    t, calls = typed_trial_inputs, []
    f = t.f

    class Project(dict):
        def __getitem__(self, key):
            calls.append('project-consumed')
            return super().__getitem__(key)

    with f.store.tx() as c, pb._source_reads(f.store, c):
        def exercise(guard):
            guard.add('cold-trial:journal', dict(ledger=t.ledger.model_dump(),
                cursor=t.cursor.model_dump(), revision=1))
            models = []
            gate._graph_trial_journal_models(guard, f.store, c, models,
                t.ledger, t.cursor)

            def pin():
                gate._graph_trial_models_pin(guard, f.store, c, models)

            pin()  # Equal complete values must be accepted before any mutation.

            def lock_project(*args, **kwargs):
                calls.append('lock-project')
                if changed == 'ledger':
                    object.__setattr__(t.ledger, 'halted', True)
                elif changed == 'cursor':
                    object.__setattr__(t.cursor, 'last_reserved_at', 1.0)
                # Only the actual typed value changed; canonical raw alone
                # still passes. The following consumer guard must reject it.
                gate._graph_trial_pin(guard, f.store, c)
                calls.append('canonical-only-pass')
                return Project(runtime_id=t.contract.runtime_id)

            monkeypatch.setattr(f.store, 'lock_project', lock_project)
            return policy._bound_from_checked_facts(f.store, c, f.user,
                t.contract, t.expected, t.ledger, t.cursor, t.identity, t.wire,
                _guard=pin)

        if changed == 'none':
            with read_scope(f, c) as guard:
                result = exercise(guard)
                assert result == (t.contract, t.ledger, t.cursor, t.identity)
                assert guard.active
            assert calls == ['lock-project', 'canonical-only-pass', 'project-consumed']
        else:
            with pytest.raises(DomainError) as caught:
                with read_scope(f, c) as guard:
                    try:
                        exercise(guard)
                    except DomainError:
                        # Assert sticky cleanup before the context exits; the
                        # context's final invalidation cannot satisfy this.
                        assert not guard.active
                        raise
            assert caught.value.code == 'VERSION_CONFLICT'
            assert calls == ['lock-project', 'canonical-only-pass']


def _typed_accounted_generate(t):
    """Three complete per-aid snapshots, not a verified Generate Run."""
    payload = b'{"synthetic_continuity":"received"}'
    digest = hashlib.sha256(payload).hexdigest()
    actual, chains = [], []
    for index in range(3):
        item = t.identity.model_copy(update=dict(attempt_id=new_id('attempt')))
        outcome = policy.Outcome(outcome='RECEIVED', response_sha256=digest,
            response_ascii_bytes=len(payload), prompt_tokens=0,
            completion_tokens=1, total_tokens=1)
        slot = policy.Slot(identity=item,
            reserved_at=t.contract.expires_at - 240 + index * 60,
            attempted=True, settlement=outcome, accepted=True)
        capture = sender.Capture(provenance='SPEC_PRODUCTION_CONTROLLER',
            raw_sha256=digest, raw_bytes=len(payload),
            body_b64=base64.b64encode(payload).decode('ascii'), complete=True,
            received_response=True, omission='NONE', canonical_sha256=digest,
            canonical_ascii_bytes=len(payload), response_verdict='VALID_PROTOCOL',
            outcome=outcome)
        row = dict(id=item.attempt_id, run_id=item.run_id)
        actual.append(row)
        chains.append((slot, capture, {'synthetic': index}, row, t.wire, payload))
    run = dict(id=t.identity.run_id, principal_id=t.f.user,
        project_id=t.contract.project_id, runtime_id=t.contract.runtime_id)
    return run, tuple(actual), tuple(chains), ()


@pytest.mark.parametrize('changed', ['none', 'slot', 'capture',
    'nested-int-to-bool', 'nested-int-to-float'])
def test_actual_capture_callback_checks_every_accounted_aid_before_digest_consumption(
        typed_trial_inputs, monkeypatch, changed):
    t, calls = typed_trial_inputs, []
    f, value = t.f, _typed_accounted_generate(t)
    real_sha256 = hashlib.sha256

    with f.store.tx() as c, pb._source_reads(f.store, c):
        def exercise(guard):
            raw = gate._graph_trial_accounted_raw(guard, f.store, c, value, [])
            guard.add('cold-trial:accounted-generate', raw)
            models = []  # Exercise a new consumer cohort, not producer locals.
            gate._graph_trial_accounted_models(guard, f.store, c, models,
                value, 'generate')
            assert len(raw['chains']) == len(models) // 2 == 3
            assert tuple(row['id'] for row in raw['actual']) == tuple(
                chain[0].identity.attempt_id for chain in value[2])
            assert all(chain[4] == t.wire and chain[5] == value[2][0][5]
                for chain in raw['chains'])

            def pin():
                gate._graph_trial_models_pin(guard, f.store, c, models)

            pin()

            class Digest:
                def __init__(self, payload):
                    self.inner = real_sha256(payload)

                def hexdigest(self):
                    calls.append('digest-consumed')
                    return self.inner.hexdigest()

            def hashing(payload):
                calls.append('hash-entry')
                # Mutate the third aid while the first aid is being consumed.
                # Tracking only the active/first aid cannot pass this test.
                if changed == 'slot':
                    object.__setattr__(value[2][2][0], 'accepted', False)
                elif changed == 'capture':
                    object.__setattr__(value[2][2][1], 'complete', False)
                elif changed == 'nested-int-to-bool':
                    object.__setattr__(value[2][2][1].outcome, 'prompt_tokens', False)
                    assert value[2][2][1].outcome.prompt_tokens == 0
                    assert type(value[2][2][1].outcome.prompt_tokens) is bool
                elif changed == 'nested-int-to-float':
                    object.__setattr__(value[2][2][0].identity, 'version', 1.0)
                    assert value[2][2][0].identity.version == 1
                    assert type(value[2][2][0].identity.version) is float
                gate._graph_trial_pin(guard, f.store, c)
                calls.append('canonical-only-pass')
                return Digest(payload)

            # Replace only dispatch's alias. Patching hashlib.sha256 globally
            # would also mutate the exact CGR serializer's hashing callback.
            monkeypatch.setattr(dispatch, 'hashlib', SimpleNamespace(sha256=hashing))
            slot, capture, _, _, _, payload = value[2][0]
            dispatch._journal_capture_from_facts(slot, capture, payload, _guard=pin)

        if changed == 'none':
            with read_scope(f, c) as guard:
                exercise(guard)
                assert guard.active
            assert calls == ['hash-entry', 'canonical-only-pass', 'digest-consumed']
        else:
            with pytest.raises(DomainError) as caught:
                with read_scope(f, c) as guard:
                    try:
                        exercise(guard)
                    except DomainError:
                        assert not guard.active
                        raise
            assert caught.value.code == 'VERSION_CONFLICT'
            assert calls == ['hash-entry', 'canonical-only-pass']


def test_stage_raw_detached_view_drift_stops_at_approval_return(
        local_origin, monkeypatch):
    f, calls = local_origin, []
    rid = new_id('run')
    job, source_job = dict(id=rid), dict(id=new_id('run'))
    bound, source_bound = {'stage': 'cold'}, {'stage': 'source'}
    candidate, metadata, gen = {'body': b'complete raw candidate'}, {'version': 1}, {'id': new_id('run')}
    draft, target, goal = {'id': 'synthetic-draft'}, {'resource': 'per-use'}, {'goal': 'complete'}
    extraction = (draft, None, target, goal)
    # This deliberate mutable fixture tests detaching a tuple view from its
    # complete canonical node. It cannot construct an Authority or full Stage.
    stage_facts = [job, bound, candidate, metadata, gen, None, None,
        (source_job, (), (), ()), extraction]

    def approved(*args, **kwargs):
        calls.append('approval')
        stage_facts[2] = dict(candidate)  # Equal bytes, detached actual raw view.
        gate._graph_trial_pin(guard, f.store, c)
        calls.append('canonical-only-pass')
        return object()

    def forbidden_producer(*args, **kwargs):
        pytest.fail('Approval result consumed after Stage raw-view drift')

    # The Stage typed cohort has separate exact-model cases above. Isolate it
    # here; keep the actual raw-view guard and actual approval-return edge.
    monkeypatch.setattr(gate, '_graph_trial_stage_models', lambda *a, **k: None)
    monkeypatch.setattr(gate, '_approved', approved)
    monkeypatch.setattr(gate, '_graph_trial_produced', forbidden_producer)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as caught:
            with read_scope(f, c) as guard:
                guard.add('cold-trial:complete', dict(binding=bound,
                    source_binding=source_bound, cold_job=job,
                    source=dict(run=source_job), generation=dict(raw=candidate,
                        metadata=metadata, run=gen),
                    extraction=dict(draft=draft, target=target, goal=goal)))
                gate._graph_trial_stage_raw(guard, stage_facts)
                try:
                    gate._graph_run_context(guard, f.store, c, f.user,
                        f.worker.pa_trial.contract, f.worker.pa_trial.approval_key,
                        'cold', rid, 1, 1, stage_facts)
                except DomainError:
                    assert not guard.active
                    raise
    assert caught.value.code == 'VERSION_CONFLICT'
    assert calls == ['approval', 'canonical-only-pass']


def test_typed_pin_keeps_parent_valueerror_identity_before_any_model_serialization(
        typed_trial_inputs, monkeypatch):
    t, calls = typed_trial_inputs, []
    f, original = t.f, ValueError('synthetic original typed-parent failure')
    raw = t.cursor.model_dump()

    def failed_parent(*args, **kwargs):
        calls.append('parent-guard')
        raise original

    def forbidden_dump(*args, **kwargs):
        pytest.fail('Typed serialization ran after the original parent guard failed')

    def callback():
        calls.append('callback')
        return 'returned-before-guard'

    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with read_scope(f, c) as guard:
                guard.add('synthetic-cursor-raw', raw)
                models = [(policy.AccountQuotaCursor, t.cursor, raw)]
                monkeypatch.setattr(gate, '_graph_trial_pin', failed_parent)
                monkeypatch.setattr(policy.AccountQuotaCursor, 'model_dump', forbidden_dump)
                try:
                    gate._trial_result(callback(), lambda: gate._graph_trial_models_pin(
                        guard, f.store, c, models))
                except ValueError as error:
                    assert error is original and not guard.active
                    raise
    assert caught.value is original
    assert calls == ['callback', 'parent-guard']


@pytest.mark.parametrize(('actual', 'saved'), [
    ({'reservation': {'ordinal': False}}, {'reservation': {'ordinal': 0}}),
    ({'run_version': 1.0}, {'run_version': 1}),
    ({'items': (1, 2)}, {'items': [1, 2]}),
])
def test_fixed_typed_equal_keeps_nested_numeric_and_sequence_types(actual, saved):
    assert gate._trial_typed_equal(copy.deepcopy(saved), saved)
    assert not gate._trial_typed_equal(actual, saved)


def test_fixed_typed_equal_refuses_unknown_values_without_equality_callbacks():
    calls = []

    class Unknown:
        def __eq__(self, other):
            calls.append('unknown-equality')
            pytest.fail('A fixed typed comparator invoked unknown equality')

    value = Unknown()
    assert not gate._trial_typed_equal({'nested': value}, {'nested': value})
    assert calls == []


def test_cold_model_before_rechecks_clock_after_owned_graph_close_before_w5(
        local_origin, monkeypatch):
    """Synthetic adapter timing only; no complete trial, Authority or model IO."""
    f, calls, writes = local_origin, [], []
    contract = f.worker.pa_trial.contract
    start = contract.expires_at - contract.caps.run_seconds
    clock = [start]
    seen = dict(guard=None, trial=None, armed=False, advanced=False)
    current = dict(id=new_id('run'), principal_id=f.user,
        project_id=f.draft['project_id'], runtime_id=f.draft['runtime_id'],
        created_at=start, lease_until=start + contract.caps.lease_seconds,
        resource_refs=[contract.bindings[1].resource_id])
    inputs = dict(operation_id='synthetic-no-write-boundary', body=b'complete original input',
        meta=dict(deadline=start + contract.caps.run_seconds), node=f.roles['per_use'])
    completed = object()
    original_check = runtime._ColdGraphRead.check
    closing_code = runtime._cold_graph_read.__wrapped__.__code__

    def first_binding(worker, c, guard, job, platform):
        assert worker is f.worker and job is current and platform is f.limits
        assert guard.connection is c and guard.active
        calls.append('first-binding-fixture')
        seen['guard'] = guard
        return completed

    class IsolatedClockTrial:
        def __init__(self, worker, c, guard, *, completed):
            assert worker is f.worker and c is guard.connection
            assert completed is first_completed and guard is seen['guard']
            calls.append('trial-construction-fixture')
            self.guard = guard
            # Full synthetic finite vector is an in-memory continuity input,
            # never a substitute for a successful commit or Stage Authority.
            finite = [current['lease_until'], contract.expires_at,
                inputs['meta']['deadline'], current['created_at'] + inputs['node'].run_seconds]
            finite.extend(start + value.run_seconds
                for value in guard.role_limits.values() if value is not None)
            self.authority_record = dict(deadlines=tuple(finite))
            self.authority_record_key = 'commit:second:trial-output'
            guard.add(self.authority_record_key, self.authority_record)
            seen['trial'] = self

    first_completed = completed

    def checked(guard, store, c):
        # Execute the real exact-CGR check first. Only its normal context exit
        # is slow: constructor/add/body checks cannot trigger this clock jump.
        original_check(guard, store, c)
        frame = inspect.currentframe()
        caller = None if frame is None else frame.f_back
        try:
            closing = caller is not None and caller.f_code is closing_code
        finally:
            del caller
            del frame
        if (closing and seen['armed'] and not seen['advanced']
                and guard is seen['guard']):
            assert guard.active and not f.worker.stop.is_set()
            calls.append('owned-close-check')
            clock[0] = min(seen['trial'].authority_record['deadlines']) + 0.25
            seen['advanced'] = True

    def now():
        calls.append('clock-after-close' if seen['advanced'] else 'clock-before-close')
        return clock[0]

    def five_writes_tripwire():
        writes.append('W5-entered')
        pytest.fail('Expired G0 context returned to the five-write boundary')

    # Keep actual eligibility, roles, _cold_model_before, _cold_graph_read and
    # exact CGR check. Only the semantically unrelated first graph producers
    # are isolated; they cannot create a verified/admitted production graph.
    monkeypatch.setattr(runtime, '_cold_first_binding', first_binding)
    monkeypatch.setattr(runtime, '_ColdTrialGraph', IsolatedClockTrial)
    monkeypatch.setattr(runtime._ColdGraphRead, 'check', checked)
    # Replace this module alias only; global time and DB/source clocks stay real.
    monkeypatch.setattr(runtime, 'time', SimpleNamespace(time=now))
    with f.store.tx() as c, pb._source_reads(f.store, c):
        assert runtime._cold_model_eligible(f.worker, c, current)
        with pytest.raises(DomainError):
            with runtime._cold_model_before(f.worker, c, current, inputs, f.limits) as graph:
                assert graph is seen['trial'] and graph.guard.active
                assert clock[0] < min(graph.authority_record['deadlines'])
                calls.append('G0-body-complete')
                seen['armed'] = True
            five_writes_tripwire()
    assert seen['advanced'] and not seen['guard'].active
    assert not f.worker.stop.is_set() and not writes
    assert clock[0] > min(seen['trial'].authority_record['deadlines'])
    assert calls.index('G0-body-complete') < calls.index('owned-close-check')
    assert calls.index('owned-close-check') < calls.index('clock-after-close')


def test_cold_recheck_full_run_matches_actual_lock_live_prefix_before_context_consumer(
        typed_trial_inputs, env, monkeypatch, tmp_path):
    """One real SQLite full-row boundary, NOT a trial/Stage/permit proof.

    Approval/source/prefix semantics before the row comparison are explicit
    isolated stand-ins. The next original context predicate is a stop sentinel,
    so no fake Stage ACK, RunCheck, Permit, sender or model can be produced.
    Actual lock_live/Store.guard and both fresh runs SELECTs remain unpatched.
    """
    t, f = typed_trial_inputs, typed_trial_inputs.f
    rid, now = new_id('run'), time.time()
    with f.store.tx() as c:
        project_runtime = Store.own_project(f.store, c, f.user, t.contract.project_id)['runtime_id']
    full = dict(id=rid, project_id=t.contract.project_id, principal_id=f.user,
        runtime_id=project_runtime, goal='complete persisted goal outside the 13-column projection',
        resource_refs=[env[-1]], status='RUNNING',
        request_key='synthetic-full-row-only', fingerprint='d' * 64,
        created_at=now - 1, lease_until=now + t.contract.caps.lease_seconds - 1,
        fence=1, worker_id=f.worker.id,
        context=dict(messages=[], tools=0, full={'retained': ['one', 'two', 'two']}),
        result=None, error=None, cancel_intent=False, version=1)
    assert set(full) == set(runs.c.keys())
    with f.store.tx() as c:
        c.execute(insert(runs).values(**full))

    trace, consumers, queries = [], [], []
    stopped = RuntimeError('synthetic stop at original full Run context consumer')
    cold_authority = SimpleNamespace(run_id=rid, stage='cold')
    source_authority = SimpleNamespace(run_id=new_id('run'), stage='source')
    cold = SimpleNamespace(approval_key=f.worker.pa_trial.approval_key,
        authority=cold_authority, expected_authority_fingerprint=fingerprint(vars(cold_authority)))
    source = SimpleNamespace(approval_key=f.worker.pa_trial.approval_key,
        authority=source_authority, expected_authority_fingerprint=fingerprint(vars(source_authority)))

    def requirements(*args, **kwargs):
        trace.append('requirements-standin')
        return t.contract, t.expected

    def approved(*args, **kwargs):
        trace.append('approval-standin')
        return SimpleNamespace(synthetic_not_an_approval=True)

    def saved_phase(c, user, entity, kind, key, model, **kwargs):
        trace.append(key + '-phase-standin')
        return cold if key == 'cold' else source

    def journal_source(*args, **kwargs):
        trace.append('source-standin')
        return SimpleNamespace(synthetic_not_a_verified_source=True)

    def frozen_only(connection, job):
        # Isolate the unrelated frozen/semantic proof. Store.guard must still
        # obtain its own complete actual SQLite row before this fixture edge.
        assert connection is c and set(job) == set(runs.c.keys())
        trace.append('prefix-frozen-standin')
        return None

    def prefix_before_semantics(worker, connection, run, binding, delta=0, **kwargs):
        assert worker is f.worker and connection is c
        job = app_jobs.lock_live(worker.store, connection, run)
        trace.append('actual-lock-live-full-row')
        return job, f.limits

    def consumer(user, contract, stage, actual, version, fence, approval, phase, at, **kwargs):
        assert user == f.user and contract is t.contract and stage == 'cold'
        assert set(actual) == set(runs.c.keys()) and dict(actual) == database_row
        assert runtime._model_inputs(dict(actual)) == runtime._model_inputs(dict(prefix.job))
        assert actual['goal'] == full['goal'] and actual['context'] == full['context']
        consumers.append('original-context-consumer')
        raise stopped

    monkeypatch.setattr(policy, '_requirements', requirements)
    monkeypatch.setattr(gate, '_approved', approved)
    monkeypatch.setattr(gate, '_keys', lambda *a, **k: {'source', 'cold'})
    monkeypatch.setattr(gate, '_saved', saved_phase)
    monkeypatch.setattr(gate, '_graph_trial_produced', lambda *a, **k: None)
    monkeypatch.setattr(dispatch, '_journal_source', journal_source)
    monkeypatch.setattr(gate, '_require_run_context_row', consumer)
    monkeypatch.setattr(f.store, '_frozen_contract_after_scope', frozen_only)
    monkeypatch.setattr(spec, '_commit_guard_prefix', prefix_before_semantics)

    with f.store.tx() as c, pb._source_reads(f.store, c):
        database_row = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        assert set(database_row) == set(runs.c.keys())
        with read_scope(f, c) as guard:
            prefix = spec._cold_commit_prefix(f.worker, c, database_row,
                {'synthetic_not_a_business_binding': True}, guard, 'second')
            assert type(prefix) is spec._ColdCommitPrefix
            assert set(prefix.job) == set(runs.c.keys()) and prefix.job == database_row
            assert 'actual-lock-live-full-row' in trace
            graph = object.__new__(runtime._ColdTrialGraph)
            # These stand-ins only isolate the already-reviewed earlier Stage
            # checks. They deliberately cannot assert a complete graph or ACK.
            graph.__dict__.update(worker=f.worker, c=c, guard=guard,
                cold_authority=dict(vars(cold_authority)), source_authority=dict(vars(source_authority)),
                authorities=set(), check=lambda: gate._graph_trial_pin(guard, f.store, c),
                _dump=lambda value: dict(vars(value)), _fingerprint=fingerprint,
                _source_value=lambda value: trace.append('source-observation-standin'))

            def observe(conn, cursor, statement, params, context, executemany):
                queries.append(statement)

            event.listen(f.store.engine, 'before_cursor_execute', observe)
            try:
                with pytest.raises(RuntimeError) as reached:
                    graph._recheck(prefix.job)
                assert reached.value is stopped
                assert consumers == ['original-context-consumer'] and guard.active
                positive = list(queries)
                queries.clear()
                # Mutate only a top-level field of the actual prefix's job;
                # the canonical copied prefix facts and DB stay unchanged.
                # The old 13-column projection never contained this field.
                prefix.job['goal'] = 'changed complete caller goal'
                gate._graph_trial_pin(guard, f.store, c)
                with pytest.raises(DomainError) as rejected:
                    graph._recheck(prefix.job)
                assert rejected.value.code == 'VERSION_CONFLICT'
                assert consumers == ['original-context-consumer']
                negative = list(queries)
                prefix.job['goal'] = database_row['goal']
            finally:
                event.remove(f.store.engine, 'before_cursor_execute', observe)
            for statements in (positive, negative):
                complete_reads = [s for s in statements if s.startswith('SELECT runs.id,')
                    and 'runs.goal' in s and 'runs.context' in s]
                assert len(complete_reads) == 1
            assert dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one()) == database_row
            proof = dict(classification='ISOLATED_FULL_RUN_RECHECK_BOUNDARY_NO_STAGE_ACK',
                full_columns=list(runs.c.keys()), prefix_job=dict(prefix.job),
                positive_consumer_count=1, drift_consumer_count=0,
                positive_sql=positive, drift_sql=negative, prior_standins=trace,
                actual_worker_claims=0, model_requests=0, admitted_execution=False)
            (tmp_path / 'full-run-recheck-boundary.json').write_text(
                json.dumps(proof, indent=2, ensure_ascii=False) + '\n')
