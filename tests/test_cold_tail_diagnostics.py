"""Finite real Run predicate / synthetic tail tests; no Worker/Mock/G0."""

import json
from types import SimpleNamespace as NS

import pytest
from test_cold_accounted_mock_wiring import script
from test_cold_accounted_sqlite import forbid_execution as forbid_execution

from sim2act import natural_live_admission as gate
from sim2act.errors import DomainError


@pytest.fixture
def modules(monkeypatch):
    from test_cold_accounted_mock_wiring import ROOT
    monkeypatch.syspath_prepend(str(ROOT / 'scripts/diagnostics'))
    return script('g0_tail_observer'), script('g0_stage_observer')


def types():
    from sqlalchemy.engine import RowMapping
    from sqlalchemy.sql.elements import quoted_name
    return dict(contract=(gate.TrialContract, gate.TrialContractV2, gate.PBTrialContract),
        caps=(gate.TrialCaps,), binding=(gate.MaterialGoal,), approval=(gate.Approval,),
        keys=(gate.StageKeys,), phase=(gate.StageAuthority, gate.StageAuthorityV2), row=(dict, RowMapping),
        quoted=quoted_name, error=DomainError)


def arguments():
    contract = gate.PBTrialContract.model_construct(project_id='SENSITIVE_PROJECT',
        runtime_id='SENSITIVE_RUNTIME', expires_at=1000.0,
        bindings=[gate.MaterialGoal.model_construct(resource_id='SENSITIVE_SOURCE'),
                  gate.MaterialGoal.model_construct(resource_id='SENSITIVE_COLD')],
        caps=gate.TrialCaps(run_seconds=300),
        stage_keys=gate.StageKeys(generate='generate', source='source', cold='cold'))
    run = dict(principal_id='SENSITIVE_USER', project_id='SENSITIVE_PROJECT',
        runtime_id='SENSITIVE_PHASE_RUNTIME', request_key='cold', resource_refs=['SENSITIVE_COLD'],
        status='RUNNING', cancel_intent=False, version=1, fence=2, created_at=100.0, lease_until=160.0)
    return ['SENSITIVE_USER', contract, 'cold', run, 1, 2,
        gate.Approval.model_construct(approved_at=90.0),
        gate.StageAuthority.model_construct(runtime_id='SENSITIVE_PHASE_RUNTIME'), 150.0]


def damage(args, case):
    run = args[3]
    if case == 'lease':
        run['lease_until'] = args[8]
    elif case == 'run':
        run['lease_until'] = 800.0
        args[8] = 400.0
    elif case == 'contract':
        args[1].expires_at = args[8]
    elif case == 'fence_positive':
        args[5] = run['fence'] = 0
    elif case == 'created_interval':
        run['created_at'] = args[8] + 1
    elif case == 'created_finite':
        run['created_at'] = float('nan')
    elif case == 'lease_finite':
        run['lease_until'] = float('inf')
    elif case == 'run_present':
        args[3] = None
    elif case == 'version_type_int':
        args[4] = 1.0
    elif case == 'fence_type_int':
        args[5] = 2.0
    else:
        key, value = {
            'principal_equal': ('principal_id', 'SENSITIVE_WRONG_USER'),
            'project_equal': ('project_id', 'SENSITIVE_WRONG_PROJECT'),
            'runtime_equal': ('runtime_id', 'SENSITIVE_WRONG_RUNTIME'),
            'resource_refs_equal': ('resource_refs', ['SENSITIVE_WRONG_RESOURCE']),
            'status_running': ('status', 'STOPPING'), 'not_cancelled': ('cancel_intent', True),
            'version_equal': ('version', 2), 'fence_equal': ('fence', 3),
        }[case]
        run[key] = value


@pytest.mark.parametrize('case,false_key', [
    ('lease', 'before_lease'), ('run', 'before_run_deadline'), ('contract', 'before_contract_expiry'),
    ('version_equal', 'version_equal'), ('fence_equal', 'fence_equal'),
    ('not_cancelled', 'not_cancelled'), ('status_running', 'status_running'),
    ('principal_equal', 'principal_equal'), ('project_equal', 'project_equal'),
    ('runtime_equal', 'runtime_equal'), ('resource_refs_equal', 'resource_refs_equal'),
    ('fence_positive', 'fence_positive'), ('created_interval', 'created_in_approval_interval'),
    ('created_finite', 'created_finite'), ('lease_finite', 'lease_finite'),
    ('version_type_int', 'version_type_int'), ('fence_type_int', 'fence_type_int'),
    ('run_present', 'run_present'),
])
def test_real_predicate_each_rejection_keeps_original_order_exception_and_at(modules, monkeypatch, case, false_key):
    tailmod, stagemod = modules
    args = arguments()
    damage(args, case)
    trace, errors = [], []
    original_require = gate.require

    def require(*a, **kw):
        trace.append(('require', a))
        try:
            return original_require(*a, **kw)
        except DomainError as error:
            errors.append(error)
            raise

    def forbidden(*a, **kw):
        pytest.fail('diagnostic cannot sample business time or query SQL')

    monkeypatch.setattr(gate, 'require', require)
    monkeypatch.setattr(gate, 'time', NS(time=forbidden))
    from sqlalchemy.engine import Connection
    monkeypatch.setattr(Connection, 'execute', forbidden)
    def guard():
        trace.append('guard')
    with pytest.raises(DomainError) as baseline:
        gate._require_run_context_row(*args, _guard=guard)
    expected_trace = list(trace)
    trace.clear()
    observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: None)
    observer.active = 'recheck'  # Explicit local span stand-in, no graph permission.
    with pytest.raises(DomainError) as caught:
        observer.run_predicate(gate._require_run_context_row, types())(*args, _guard=guard)
    assert trace == expected_trace and caught.value is errors[-1]
    assert caught.value.public() == baseline.value.public()
    record, = observer.failures
    assert record['predicate_message_matches'] is True
    assert record['comparisons'][false_key] is False
    assert record['evaluation_basis'] == 'POST_EXCEPTION_EXISTING_SAFE_ARGUMENTS_NOT_SHORT_CIRCUIT_TRACE'
    if args[3] is not None:
        assert record['scalars']['at'] == args[8]
    assert 'SENSITIVE_' not in json.dumps(record, allow_nan=False)
    assert not hasattr(caught.value, '_cold_admission_diagnostic')


def test_no_replay_when_original_guard_raises_before_run_predicate_result(modules):
    tailmod, stagemod = modules
    args = arguments()
    sentinel = DomainError('PERMISSION_DENIED', 'SENSITIVE_GUARD_ERROR')
    calls = []

    def guard():
        calls.append('guard')
        raise sentinel

    observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: None)
    observer.active = 'recheck'
    with pytest.raises(DomainError) as caught:
        observer.run_predicate(gate._require_run_context_row, types())(*args, _guard=guard)
    assert caught.value is sentinel and calls == ['guard']
    record, = observer.failures
    assert record['predicate_message_matches'] is False
    assert all(record['comparisons'].values())
    assert 'SENSITIVE_' not in json.dumps(record)


def test_real_rowmapping_storage_success_control_and_unsafe_field_failure(modules):
    from sqlalchemy import JSON, create_engine, literal, select
    tailmod, stagemod = modules
    args = arguments()
    engine = create_engine('sqlite://')
    try:
        with engine.connect() as c:
            args[3] = c.execute(select(*(literal(v, type_=JSON if type(v) is list else None).label(k)
                for k, v in args[3].items()))).mappings().one()
        callbacks, armed = [], [False]
        class ForeignIndex:
            def __hash__(self):
                if armed[0]:
                    callbacks.append('index_hash')
                    pytest.fail('foreign index hash')
                return hash('status')
            def __eq__(self, other):
                if armed[0]:
                    callbacks.append('index_equality')
                    pytest.fail('foreign index equality')
                return False
        object.__getattribute__(args[3], '_key_to_index')[ForeignIndex()] = 0
        armed[0] = True
        observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: None)
        observer.active = 'recheck'
        assert observer.run_predicate(gate._require_run_context_row, types())(*args) is None
        assert observer.failures == []
        result = tailmod.run_comparisons(args, types())
        assert not result['incomplete'] and all(result['comparisons'].values())
        assert result['scalars'] == dict(at=150.0, lease_until=160.0, run_deadline=400.0,
            contract_expires_at=1000.0, min_deadline=160.0)
        assert callbacks == []
    finally:
        engine.dispose()
    # A foreign model's descriptor must never run just to collect evidence.
    class Foreign:
        @property
        def __dict__(self):
            callbacks.append('foreign_model_descriptor')
            pytest.fail('foreign descriptor')
    args[1] = Foreign()
    sentinel = RuntimeError('original sentinel')
    def fail(*a, **kw):
        raise sentinel
    with pytest.raises(RuntimeError) as caught:
        observer.run_predicate(fail, types())(*args)
    assert caught.value is sentinel and observer.failures[-1]['incomplete']
    assert observer.incomplete
    assert callbacks == []


class Clock:
    now = 0
    def __call__(self):
        return self.now


def test_fixed_tail_spans_nested_metrics_residual_and_exact_target(modules):
    tailmod, stagemod = modules
    clock = Clock()
    metrics = stagemod.StageObserver(clock=clock, thread=lambda: 1, enable_tail=True)
    guard = NS(_diagnostic_counts=[0, 0])
    trial = NS(guard=guard, worker=object(), c=object())
    observer = tailmod.TailObserver(metrics, lambda: trial, wall=clock, cpu=clock, thread=lambda: 1,
        prefix_type=NS)
    events = []
    def work(n):
        clock.now += n
        guard._diagnostic_counts[0] += 1
        guard._diagnostic_counts[1] += 2
        return b'abc'
    encoded = metrics.wrapper(work, 'codec', (0,))
    check = observer.recheck(lambda current: encoded(5))
    def commit(current, prefix):
        encoded(3)
        check(current)
        return encoded(7)
    commit = observer.commit(commit)
    prefix = observer.prefix(lambda *a: encoded(2))
    class Context:
        def __enter__(self):
            events.append('enter')
            return trial
        def __exit__(self, *exc):
            events.append(('exit', exc))
            encoded(11)
            return False
    with observer.context(Context)() as actual:
        assert actual is trial
        prefix(trial.worker, trial.c, {}, {}, guard, 'second')
        assert commit(trial, NS(key='commit:second')) == b'abc'
    report = observer.report()
    assert report['status'] == 'COMPLETE_OBSERVATION'
    assert [report['regions'][k]['wall_ns'] for k in tailmod.NAMES] == [2, 15, 5, 11]
    assert report['second_commit_minus_observed_recheck'] == dict(wall_ns=10, cpu_ns=10, check_calls=2, input_key_calls=4)
    rows = {s['stage']: s for s in metrics.report()['stages']}
    assert [rows[k]['metrics']['codec']['calls'] for k in tailmod.NAMES] == [1, 2, 1, 1]
    assert events == ['enter', ('exit', (None, None, None))]
    before = json.dumps(observer.report(), sort_keys=True)
    commit(NS(guard=guard), NS(key='commit:second'))
    prefix(object(), trial.c, {}, {}, guard, 'second')
    prefix(trial.worker, trial.c, {}, {}, guard, 'first')
    assert json.dumps(observer.report(), sort_keys=True) == before  # Foreign work not attributed.


@pytest.mark.parametrize('suppress,exit_error', [(False, False), (True, False), (False, True)])
def test_original_exit_exception_triple_return_and_suppression_survive_bad_observer(modules, suppress, exit_error):
    tailmod, stagemod = modules
    error, final_error = ValueError('body'), RuntimeError('exit')
    trial = NS(guard=NS(_diagnostic_counts=[0, 0]))
    observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: trial,
        wall=lambda: (_ for _ in ()).throw(RuntimeError('diagnostic clock')))
    events = []
    class Context:
        def __enter__(self):
            events.append('enter')
            return trial
        def __exit__(self, *exc):
            events.append(exc)
            if exit_error:
                raise final_error
            return suppress
    def run():
        with observer.context(Context)():
            raise error
    if suppress and not exit_error:
        run()
    else:
        with pytest.raises((ValueError, RuntimeError)) as caught:
            run()
        assert caught.value is (final_error if exit_error else error)
    assert events[0] == 'enter' and len(events) == 2
    assert events[1][0] is ValueError and events[1][1] is error
    assert observer.report()['status'] == 'INCOMPLETE'


def test_diagnostic_storage_thread_and_report_faults_cannot_replace_original(modules):
    tailmod, stagemod = modules
    observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: None)
    observer.active = 'recheck'
    class Broken(list):
        def append(self, value):
            raise RuntimeError('diagnostic list')
    observer.failures = Broken()
    error = DomainError('VERSION_CONFLICT', 'original sentinel')
    def fail(*a, **kw):
        raise error
    with pytest.raises(DomainError) as caught:
        observer.run_predicate(fail, types())(*arguments())
    assert caught.value is error and observer.incomplete
    observer.rows = None
    assert observer.report()['status'] == 'INCOMPLETE'
    # If diagnostic identity selection fails, originals still execute once.
    observer.trial = lambda: (_ for _ in ()).throw(RuntimeError('diagnostic selection'))
    calls = []
    result = object()
    assert observer.prefix(lambda *a: (calls.append('original') or result))(None, None, None, None, None, 'second') is result
    assert calls == ['original']


def test_thread_bypass_failed_end_sample_and_raw_exit_return(modules):
    tailmod, stagemod = modules
    observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: None, thread=lambda: 1)
    observer.active = 'recheck'
    observer.thread = lambda: 2
    sentinel = BaseException('original cancellation')
    cause, context = ValueError('cause'), TypeError('context')
    sentinel.__cause__, sentinel.__context__, sentinel.__suppress_context__ = cause, context, True
    def fail(*a, **kw):
        raise sentinel
    with pytest.raises(BaseException) as caught:
        observer.run_predicate(fail, types())(*arguments())
    assert caught.value is sentinel and observer.failures == []
    assert sentinel.__cause__ is cause and sentinel.__context__ is context
    assert sentinel.__suppress_context__ is True
    clock_calls = []
    def clock():
        clock_calls.append('clock')
        if len(clock_calls) == 2:
            raise BaseException('diagnostic end clock')
        return 0
    guard = NS(_diagnostic_counts=[0, 0])
    trial = NS(guard=guard)
    observer = tailmod.TailObserver(stagemod.StageObserver(enable_tail=True), lambda: trial,
        wall=clock)
    result, triple, calls = object(), (None, None, None), []
    class Context:
        def __enter__(self):
            calls.append('enter')
            return trial
        def __exit__(self, *exc):
            calls.append(exc)
            return result
    proxy = observer.context(Context)()
    assert proxy.__enter__() is trial
    assert proxy.__exit__(*triple) is result
    assert calls == ['enter', triple] and clock_calls == ['clock', 'clock']
    assert observer.report()['status'] == 'INCOMPLETE'


@pytest.mark.parametrize('case', ['foreign_metaclass', 'colliding_key', 'string_time', 'large_integer'])
def test_unsupported_diagnostic_fields_do_not_add_callbacks_or_unbounded_arithmetic(modules, case):
    tailmod, stagemod = modules
    args = arguments()
    args[3]['status'] = 'STOPPING'  # Original short-circuits before these fields.
    callbacks = []
    class ForeignMeta(type):
        def __eq__(self, other):
            callbacks.append('metaclass_equality')
            pytest.fail('foreign metaclass equality')
    class Foreign(metaclass=ForeignMeta):
        pass
    class Collision:
        def __hash__(self):
            return hash('run_seconds')
        def __eq__(self, other):
            callbacks.append('dictionary_equality')
            pytest.fail('foreign dictionary key equality')
    if case == 'foreign_metaclass':
        args[3]['created_at'] = Foreign()
    elif case == 'colliding_key':
        object.__setattr__(args[1].caps, '__dict__', {Collision(): 300})
    elif case == 'string_time':
        args[3]['created_at'] = '100'
    else:
        args[3]['created_at'] = 1 << 4096
    observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: None)
    observer.active = 'recheck'
    with pytest.raises(DomainError) as caught:
        observer.run_predicate(gate._require_run_context_row, types())(*args)
    assert caught.value.message == tailmod.RUN_MESSAGE
    assert observer.incomplete and observer.failures[0]['incomplete']
    assert callbacks == []


def test_foreign_prefix_boundary_and_exception_descriptors_are_never_read(modules):
    tailmod, stagemod = modules
    trial = NS(guard=NS(_diagnostic_counts=[0, 0]), worker=object(), c=object())
    observer = tailmod.TailObserver(stagemod.StageObserver(), lambda: trial, prefix_type=NS)
    callbacks = []
    class ForeignPrefix:
        @property
        def key(self):
            callbacks.append('prefix_getter')
            pytest.fail('foreign prefix getter')
    class ForeignBoundary:
        def __eq__(self, other):
            callbacks.append('boundary_equality')
            pytest.fail('foreign boundary equality')
    class ForeignError(BaseException):
        @property
        def __dict__(self):
            callbacks.append('error_descriptor')
            pytest.fail('foreign exception descriptor')
    error = ForeignError('original')
    calls = []
    def fail(*a):
        calls.append('original')
        raise error
    with pytest.raises(ForeignError) as caught:
        observer.commit(fail)(trial, ForeignPrefix())
    assert caught.value is error and calls == ['original']
    with pytest.raises(ForeignError) as caught:
        observer.prefix(fail)(trial.worker, trial.c, {}, {}, trial.guard, ForeignBoundary())
    assert caught.value is error and calls == ['original', 'original']
    observer.active = 'recheck'
    with pytest.raises(ForeignError) as caught:
        observer.run_predicate(fail, types())(*arguments())
    assert caught.value is error
    assert observer.failures[0]['predicate_message_matches'] is False
    assert callbacks == []


@pytest.mark.parametrize('fault', ['incomplete', 'throw', 'unsafe_keys'])
def test_tail_evidence_fault_forces_unknown_only_in_report(modules, fault):
    prefix = script('g0_prefix')
    # Classification is changed only after original work has already returned.
    diagnostic = dict(classification='G0_COMPLETED_NO_W5')
    callbacks = []
    class Key:
        def __hash__(self):
            return hash('status')
        def __eq__(self, other):
            callbacks.append('report_equality')
            pytest.fail('foreign report equality')
    def report():
        if fault == 'throw':
            raise BaseException('diagnostic report fault')
        return {Key(): 'COMPLETE_OBSERVATION'} if fault == 'unsafe_keys' else dict(status='INCOMPLETE')
    prefix.record_tail(diagnostic, NS(report=report))
    assert diagnostic['classification'] == 'UNKNOWN'
    assert callbacks == []
    default = dict(classification='G0_COMPLETED_NO_W5')
    prefix.record_tail(default, None)
    assert default == dict(classification='G0_COMPLETED_NO_W5', tail_observer=dict(status='NOT_ENABLED'))
