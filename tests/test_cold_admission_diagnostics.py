"""Local synthetic diagnostics only; no Stage proof, Worker, sender or PB run.

The coordinator fixture replaces semantic/SQL producers with explicit stand-ins
to reach the actual rejection expression. A separate real SQLite/CGR test keeps
the original complete input serialization and mutation rejection.
"""

import json
from contextlib import contextmanager
from types import SimpleNamespace as NS

import pytest
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport

from sim2act import natural_live_admission as gate
from sim2act import natural_source_archives as archive
from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as dispatch
from sim2act import pb_natural_specs as pb
from sim2act import production_trial_policy as policy
from sim2act.errors import DomainError


STAGES = ('_prepare', '_graph_run_context', '_graph_pb_accounting',
    '_graph_resolve_trial_source', '_graph_pb_archive_chain')


@pytest.fixture
def synthetic_commit(monkeypatch):
    trace = []
    state = NS(stop=False, stop_calls=0, clock_calls=0, end=1040.0,
        pin_failure=None, stage_failure=None)
    guard = object.__new__(runtime._ColdGraphRead)
    guard.__dict__.update(active=True, _diagnostic_counts=[0, 0],
        inputs={'call': {'meta': {'deadline': 1118.0}, 'node': NS(run_seconds=119)},
            'cold-trial:complete': {}},
        role_limits=dict(source=NS(run_seconds=101), generate=None,
            platform=NS(run_seconds=103), trial=NS(run_seconds=104), per_use=NS(run_seconds=105)))

    def add(name, value):
        trace.append(('add', name))
        guard.inputs[name] = value

    guard.add = add  # Explicit stand-in, not a verified graph or permission.

    def pin():
        trace.append('pin')
        guard._diagnostic_counts[0] += 1
        guard._diagnostic_counts[1] += 1
        if state.pin_failure is not None and 'end' in trace:
            raise state.pin_failure

    def stopped():
        trace.append('stop')
        state.stop_calls += 1
        return state.stop

    @contextmanager
    def authorities(c):
        trace.append('authorities-enter')
        try:
            yield set()
        finally:
            trace.append('authorities-exit')

    def frozen(c, job):
        trace.append('frozen')
        return NS(limits=NS(run_seconds=106))

    store = NS(proof_authorities=authorities, _frozen_contract_after_scope=frozen)
    worker = NS(id='SENSITIVE_WORKER', store=store, stop=NS(is_set=stopped))
    binding = NS(contract=NS(principal_id='SENSITIVE_USER', project_id='SENSITIVE_PROJECT'),
        approval_key='SENSITIVE_APPROVAL')
    guard.binding = binding
    job = dict(id='SENSITIVE_RUN', principal_id=binding.contract.principal_id,
        project_id=binding.contract.project_id, created_at=1000.0, version=2, fence=3)
    actual = dict(job, lease_until=1030.0, worker_id=worker.id)
    context = NS(checked_at=1001.0, deadline=1030.0,
        approval_fingerprint='SENSITIVE_APPROVAL_FINGERPRINT',
        stage_fingerprint='SENSITIVE_STAGE_FINGERPRINT',
        requirements_fingerprint='SENSITIVE_REQUIREMENTS_FINGERPRINT')
    authority = NS(synthetic=True)
    source = NS(expires_at=1080.0)
    graph = object.__new__(runtime._ColdTrialGraph)
    graph.__dict__.update(worker=worker, c=object(), guard=guard,
        phase='EMPTY', boundaries=set(), audit_seed=None,
        platform=NS(binding={'audit_fingerprint': 'SENSITIVE_FINGERPRINT'}),
        check=pin, original=object(), expected=object(), cold_stage_facts=(),
        source_stage_facts=(), source_proof=None, source_accounted=({'id': 'source'},),
        extraction=(), journal=(None,), authorities=set(),
        trial=NS(generation_reader=NS(run={}), source_binding={'draft': {'candidate': {}},
            'snapshot': {'input': {}}}, binding={
                'snapshot': {'natural_spec_clock': {'deadline': 1090.0}},
                'draft': {'candidate': {'manifest': {'runtime_limits': {'run_seconds': 107}}}}}),
        _source_value=lambda value: trace.append('source-value'),
        _dump=lambda value: dict(vars(value)))

    def save_context(key, value):
        trace.append('context')
        graph.context = value

    graph._context = save_context

    def stage(name, result):
        def call(*args, **kwargs):
            trace.append(name)
            ordinal = STAGES.index(name) + 1
            guard._diagnostic_counts[0] += ordinal
            guard._diagnostic_counts[1] += ordinal * 2
            if state.stage_failure == name:
                raise state.sentinel
            if name == '_graph_pb_archive_chain':
                # The retained row must be the earlier RunCheck snapshot,
                # not a later final-database substitute.
                actual['lease_until'] = 999.0
            return result
        return call

    graph._prepare = stage('_prepare', None)
    monkeypatch.setattr(gate, '_trial_typed_guard', lambda *a: pin)
    monkeypatch.setattr(spec, '_cold_commit_from_audit', lambda *a: (trace.append('audit') or job))
    monkeypatch.setattr(dispatch, '_binding', lambda *a: (trace.append('binding') or binding))
    monkeypatch.setattr(gate, '_approved', lambda *a, **k: trace.append('approval'))
    monkeypatch.setattr(gate, '_graph_run_context', stage('_graph_run_context', (authority, authority, actual, 1001.0)))
    monkeypatch.setattr(gate, '_graph_trial_produced', lambda *a, **k: trace.append('produced'))
    monkeypatch.setattr(policy, '_run_check_from_facts', lambda *a, **k: (trace.append('run-check') or context))
    monkeypatch.setattr(dispatch, '_graph_pb_accounting', stage('_graph_pb_accounting', 'source'))
    monkeypatch.setattr(runtime.codec, 'compile_candidate', lambda *a: (NS(input_schema={}), None, None))
    monkeypatch.setattr(runtime, 'validate_value', lambda *a: trace.append('schema'))
    monkeypatch.setattr(archive, '_graph_resolve_trial_source', stage('_graph_resolve_trial_source', NS(
        public_receipt={}, request_bodies=(), response_bodies=())))
    monkeypatch.setattr(dispatch, '_graph_pb_archive_chain', stage('_graph_pb_archive_chain', None))
    monkeypatch.setattr(gate, 'entity', lambda *a, **k: 'synthetic-entity')
    monkeypatch.setattr(gate, '_saved', lambda *a, **k: NS(authority=authority))
    monkeypatch.setattr(dispatch, '_journal_source', lambda *a, **k: (trace.append('source') or source))
    monkeypatch.setattr(runtime, '_model_source_key', lambda *a: 'synthetic-source-key')

    def clock():
        state.clock_calls += 1
        return float(state.clock_calls)

    def end():
        trace.append('end')
        return state.end

    monkeypatch.setattr(runtime, '_cold_diagnostic_clock', clock)
    monkeypatch.setattr(runtime, 'time', NS(time=end))
    prefix = spec._ColdCommitPrefix(guard, 'commit:first', job, job, {}, None, 0)
    return NS(graph=graph, guard=guard, prefix=prefix, state=state, trace=trace, job=job)


def test_first_rejection_retains_original_named_values_and_fixed_stage_deltas(synthetic_commit, tmp_path):
    f = synthetic_commit
    with pytest.raises(DomainError) as caught:
        f.graph.commit(f.prefix)
    error = caught.value
    assert error.code == 'VERSION_CONFLICT'
    assert str(error) == 'Production admission expired during verification'
    assert error.public() == DomainError(error.code, error.message).public()
    d = error._cold_admission_diagnostic
    assert d['end'] == 1040.0 and d['stop'] is False and not d['incomplete']
    assert d['run_context'] == dict(checked_at=1001.0, deadline=1030.0,
        actual_run=dict(lease_until=1030.0, version=2, fence=3))
    assert [(v['name'], v['value']) for v in d['finite']] == [
        ('run_check.deadline', 1030.0), ('source.expires_at', 1080.0),
        ('natural_spec_clock.deadline', 1090.0), ('role.source.run_seconds', 1101.0),
        ('role.platform.run_seconds', 1103.0), ('role.trial.run_seconds', 1104.0),
        ('role.per_use.run_seconds', 1105.0), ('frozen.run_seconds', 1106.0),
        ('draft.run_seconds', 1107.0), ('call.meta.deadline', 1118.0), ('call.node.run_seconds', 1119.0)]
    assert [v['stage'] for v in d['stages']] == list(STAGES)
    assert [(v['wall_seconds'], v['check_calls'], v['input_key_calls']) for v in d['stages']] == [
        (1.0, n, 2 * n) for n in range(1, 6)]
    assert f.state.clock_calls == 10 and f.state.stop_calls == 1
    assert f.trace[f.trace.index('end'):f.trace.index('end') + 3] == ['end', 'pin', 'stop']
    assert not f.guard.active and f.graph.phase == 'INVALID'
    assert 'commit:first:trial-output' not in f.guard.inputs
    assert 'SENSITIVE_' not in json.dumps(d) and 'diagnostic' not in json.dumps(error.public())
    from test_spec_production_controller import failure_observation
    observation = failure_observation(f.job, error)
    assert observation['cold_admission_diagnostic'] is d
    assert observation['error'] == error.public()
    (tmp_path / 'synthetic-admission-rejection.json').write_text(json.dumps(observation, indent=2) + '\n')


def test_stop_short_circuits_original_min_and_is_not_read_again(synthetic_commit, monkeypatch):
    f = synthetic_commit
    f.state.stop = True
    monkeypatch.setattr(runtime, 'min', lambda *a: pytest.fail('stop must short-circuit min'), raising=False)
    with pytest.raises(DomainError) as caught:
        f.graph.commit(f.prefix)
    assert caught.value._cold_admission_diagnostic['stop'] is True
    assert f.state.stop_calls == 1 and not f.guard.active


def test_original_pin_error_precedes_stop_and_has_no_expiry_diagnostic(synthetic_commit):
    f = synthetic_commit
    f.state.pin_failure = DomainError('PERMISSION_DENIED', 'original pin sentinel')
    with pytest.raises(DomainError) as caught:
        f.graph.commit(f.prefix)
    assert caught.value is f.state.pin_failure
    assert f.state.stop_calls == 0 and not hasattr(caught.value, '_cold_admission_diagnostic')
    assert not f.guard.active and f.graph.phase == 'INVALID'


def test_stage_error_survives_failed_diagnostic_clock(synthetic_commit, monkeypatch):
    f = synthetic_commit
    f.state.stage_failure = '_graph_pb_accounting'
    f.state.sentinel = RuntimeError('original accounting sentinel')
    monkeypatch.setattr(runtime, '_cold_diagnostic_clock', lambda: (_ for _ in ()).throw(ValueError('clock')))
    with pytest.raises(RuntimeError) as caught:
        f.graph.commit(f.prefix)
    assert caught.value is f.state.sentinel
    assert f.state.stop_calls == 0 and not f.guard.active
    assert '_graph_resolve_trial_source' not in f.trace


def test_diagnostic_failure_cannot_change_expiry_rejection(synthetic_commit, monkeypatch):
    f = synthetic_commit
    monkeypatch.setattr(runtime, '_cold_diagnostic_clock', lambda: (_ for _ in ()).throw(ValueError('clock')))
    with pytest.raises(DomainError) as caught:
        f.graph.commit(f.prefix)
    assert caught.value.message == 'Production admission expired during verification'
    assert caught.value._cold_admission_diagnostic['incomplete'] is True
    assert caught.value._cold_admission_diagnostic['stages'] == []


def test_synthetic_success_keeps_output_and_does_not_export_diagnostics(synthetic_commit):
    f = synthetic_commit
    f.state.end = 1020.0
    assert f.graph.commit(f.prefix) is f.job
    assert f.graph.phase == 'COMPLETE' and f.guard.active
    output = f.guard.inputs['commit:first:trial-output']
    assert set(output) == {'run', 'context', 'source', 'authorities', 'admission', 'deadlines', 'archive'}
    assert len(output['deadlines']) == 11
    assert 'diagnostic' not in json.dumps(output) and 'stages' not in output
    assert f.state.clock_calls == 10 and f.state.stop_calls == 2


def test_existing_complete_graph_checks_and_bytes_remain_uncached(local_origin, monkeypatch):
    f, calls = local_origin, []
    original = runtime._cold_graph_bytes

    def serialized(value):
        calls.append('complete-bytes')
        return original(value)

    monkeypatch.setattr(runtime, '_cold_graph_bytes', serialized)
    with f.store.tx() as c, pb._source_reads(f.store, c), pytest.raises(DomainError):
        with runtime._cold_graph_read(f.worker, c, f.inputs, f.roles, 'pre') as guard:
            before = list(guard._diagnostic_counts)
            calls.clear()
            guard.check(f.store, c)
            assert guard._diagnostic_counts == [before[0] + 1, before[1] + 1]
            assert calls == ['complete-bytes']
            key = guard.key
            guard._diagnostic_counts[0] += 100  # Diagnostic state is not authority/input.
            assert guard.input_key() == key
            f.inputs['history'][0]['body'] = b'mutated original input'
            with pytest.raises(DomainError):
                guard.check(f.store, c)
            assert not guard.active
            before = list(guard._diagnostic_counts)
            with pytest.raises(DomainError):
                guard.check(f.store, c)
            assert guard._diagnostic_counts == [before[0] + 1, before[1]]
            # The context exit also rejects this sticky invalid graph; it is
            # never reset or revived to make the synthetic test succeed.


@pytest.mark.parametrize('index', [0, 1])
def test_broken_diagnostic_counter_cannot_replace_full_check_or_drift_error(
        local_origin, monkeypatch, index):
    f, calls = local_origin, []
    original = runtime._cold_graph_bytes

    def serialized(value):
        calls.append('complete-bytes')
        return original(value)

    monkeypatch.setattr(runtime, '_cold_graph_bytes', serialized)
    with f.store.tx() as c, pb._source_reads(f.store, c), pytest.raises(DomainError):
        with runtime._cold_graph_read(f.worker, c, f.inputs, f.roles, 'pre') as guard:
            guard._diagnostic_counts[index] = None
            calls.clear()
            diagnostic = runtime._ColdCommitDiagnostics(guard)
            with diagnostic.stage('_prepare'):
                guard.check(f.store, c)
            assert guard.active and calls == ['complete-bytes']
            assert diagnostic.incomplete
            f.inputs['history'][0]['body'] = b'changed original bytes'
            with pytest.raises(DomainError) as caught:
                guard.check(f.store, c)
            assert caught.value.code == 'VERSION_CONFLICT' and not guard.active
            assert calls == ['complete-bytes', 'complete-bytes']
