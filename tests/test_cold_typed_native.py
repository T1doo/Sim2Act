"""Explicit native candidate only. No Worker, model, transport or G0.

Build with scripts/build_cold_typed_native.py and pass COLD_NATIVE_TEST_DIR.
The binary is never installed or discovered by production code.
"""

import gc
import importlib.util
import os
import signal
import sysconfig
import time
from pathlib import Path

import pytest
import test_cold_typed_storage_alias_contract as alias_cases
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_typed_storage_alias_contract import contract as contract

from sim2act import _cold_typed_native_candidate as candidate
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act.contracts import BranchCondition, WorkflowStep


@pytest.fixture(scope='module')
def backend():
    directory = os.environ.get('COLD_NATIVE_TEST_DIR')
    if directory is None:
        pytest.skip('Explicit native test build not requested')
    path = Path(directory) / ('_cold_typed_native_impl' + sysconfig.get_config_var('EXT_SUFFIX'))
    spec = importlib.util.spec_from_file_location('_cold_typed_native_impl', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def native(backend, model):
    return candidate.project(backend, gate.PBTrialContract, model)


def identical(left, right):
    """Strict values/order plus the original alias-sensitive C pickle bytes."""
    assert gate._trial_typed_equal(left, right)
    assert runtime._cold_graph_bytes(left) == runtime._cold_graph_bytes(right)


@pytest.mark.parametrize('case', [value for name, value in vars(alias_cases).items()
    if name.startswith('test_')])
def test_original_four_counterexamples(backend, contract, monkeypatch, case):
    monkeypatch.setattr(alias_cases, 'project', lambda model: native(backend, model))
    case(contract)


def test_actual_contract_fresh_bytes_key_identity_and_aliases(backend, contract):
    raw = object.__getattribute__(contract, '__dict__')
    py = gate._trial_typed_storage(gate.PBTrialContract, contract)
    c = native(backend, contract)
    inputs = {'root-key': next(iter(raw)), 'shared-caps': contract.caps.__dict__}
    identical({'inputs': inputs, 'contract': py}, {'inputs': inputs, 'contract': c})
    for key in raw:
        assert next(item for item in c if item == key) is key
    assert c['caps'] is not contract.caps.__dict__
    contract.caps.__dict__['run_seconds'] -= 1
    changed = native(backend, contract)
    assert c['caps']['run_seconds'] != changed['caps']['run_seconds']
    identical(gate._trial_typed_storage(gate.PBTrialContract, contract), changed)


def test_original_row_hidden_storage_and_index_alias_wire(backend, contract):
    shared = contract.caps.__dict__
    data = ('visible', shared, shared)
    index = {'visible': 0, 'hidden-alias': 2}
    row = RowMapping(SimpleResultMetaData(['visible']), None, index, data)
    def encoded(call):
        return runtime._cold_graph_bytes({'rows': [row], 'inputs': shared,
            'contract': call()})
    def py():
        return gate._trial_typed_storage(gate.PBTrialContract, contract)
    def c():
        return native(backend, contract)
    original = encoded(c)
    assert original == encoded(py)
    shared['run_seconds'] -= 1
    assert encoded(c) == encoded(py) != original
    index['hidden-alias'] = 1
    assert encoded(c) == encoded(py)


class Fact:
    __pydantic_fields__ = {'value': None}

    def __init__(self, value):
        self.value = value
        object.__setattr__(self, '__pydantic_fields_set__', {'value'})
        object.__setattr__(self, '__pydantic_extra__', None)
        object.__setattr__(self, '__pydantic_private__', None)

    # Match the separate Pydantic slots; only value belongs in __dict__.
    __slots__ = ('__dict__', '__pydantic_fields_set__', '__pydantic_extra__',
        '__pydantic_private__')


def projections(monkeypatch, backend, extra=()):
    allowed = (Fact, BranchCondition, WorkflowStep, *extra)
    monkeypatch.setattr(gate, '_trial_typed_classes', lambda: (Fact,))
    monkeypatch.setattr(gate, '_trial_typed_nested_classes', lambda: allowed)
    def py(model):
        return gate._trial_typed_storage(Fact, model)
    def c(model):
        return backend.project(Fact, model, (Fact,), allowed,
            BranchCondition, WorkflowStep, gate.require)
    return py, c


def failure(call, value):
    try:
        call(value)
    except Exception as error:
        return type(error), error.args, getattr(error, 'code', None)
    pytest.fail('Expected rejection')


def test_strict_types_dag_omissions_and_cycles(backend, monkeypatch):
    py, c = projections(monkeypatch, backend)
    shared = ['s', 1, True, 1.0, b'b', None]
    fact = Fact({'list': shared, 'dag': shared, 'tuple': tuple(shared),
        'branch': BranchCondition.model_construct(op='eq', source='synthetic', value=None),
        'workflow': WorkflowStep.model_construct(step_id='x', binding_id='x',
            depends_on=[], when=None)})
    left, right = py(fact), c(fact)
    identical(left, right)
    assert right['value']['list'] is right['value']['dag']
    assert right['value']['list'] is not shared
    assert type(right['value']['tuple']) is tuple
    assert 'value' not in right['value']['branch']
    assert 'when' not in right['value']['workflow']
    shared.append(shared)
    assert failure(py, fact) == failure(c, fact)


@pytest.mark.parametrize('value', [object(), {1: object()}, {True: 1}, set(),
    type('ListSubclass', (list,), {})(), type('IntSubclass', (int,), {})(1)])
def test_unknown_types_and_mixed_error_priority(backend, monkeypatch, value):
    py, c = projections(monkeypatch, backend)
    fact = Fact(value)
    assert failure(py, fact) == failure(c, fact)


@pytest.mark.parametrize('change', [
    lambda fact: fact.__dict__.update(extra=1),
    lambda fact: setattr(fact, '__pydantic_fields_set__', ['value']),
    lambda fact: setattr(fact, '__pydantic_fields_set__', {'unknown'}),
    lambda fact: setattr(fact, '__pydantic_extra__', {}),
    lambda fact: setattr(fact, '__pydantic_private__', {}),
])
def test_incomplete_storage(backend, monkeypatch, change):
    py, c = projections(monkeypatch, backend)
    fact = Fact(1)
    change(fact)
    assert failure(py, fact) == failure(c, fact)


def test_descriptor_exception_once_and_short_circuit(backend, monkeypatch):
    error = ValueError('same descriptor exception')
    events = []
    class Broken:
        @property
        def __dict__(self):
            events.append('raw')
            return {}
        @property
        def __pydantic_fields_set__(self):
            events.append('selected')
            raise error
        __pydantic_fields__ = {'missing': None}
    py, c = projections(monkeypatch, backend, (Broken,))
    for call in (py, c):
        events.clear()
        with pytest.raises(ValueError) as caught:
            call(Fact(Broken()))
        assert caught.value is error
        assert events == ['raw', 'selected']


def test_builtin_getters_and_metadata_order(backend, monkeypatch):
    events = []
    broken = [False]
    class Fields:
        def __get__(self, instance, owner):
            events.append('fields')
            return {'value': None}
    class Meta(type):
        def __getattribute__(self, name):
            if name == '__pydantic_fields__':
                pytest.fail('Overridden metaclass getter called')
            return super().__getattribute__(name)
    class Descriptors(metaclass=Meta):
        __pydantic_fields__ = Fields()
        def __getattribute__(self, name):
            pytest.fail('Overridden instance getter called')
        @property
        def __dict__(self):
            events.append('raw')
            return {'bad' if broken[0] else 'value': 1}
        @property
        def __pydantic_fields_set__(self):
            events.append('selected')
            return {'value'}
        @property
        def __pydantic_extra__(self):
            events.append('extra')
            return None
        @property
        def __pydantic_private__(self):
            events.append('private')
            return None
    py, c = projections(monkeypatch, backend, (Descriptors,))
    for call in (py, c):
        events.clear()
        assert call(Fact(Descriptors())) == {'value': {'value': 1}}
        assert events == ['raw', 'fields', 'selected', 'extra', 'private']
    broken[0] = True
    for call in (py, c):
        events.clear()
        failure(call, Fact(Descriptors()))
        assert events == ['raw', 'fields', 'selected']


def test_foreign_omission_key_after_original_gate(backend, monkeypatch):
    events = []
    literal = 'value'
    class Key:
        def __hash__(self):
            return 917
        def __eq__(self, other):
            events.append(other is literal)
            return other is literal
    py, c = projections(monkeypatch, backend)
    outputs = []
    for call in (py, c):
        events.clear()
        branch = BranchCondition.model_construct(op='eq', source='synthetic', value=None)
        raw = object.__getattribute__(branch, '__dict__')
        key = Key()
        def mutate(self, raw=raw, key=key, branch=branch):
            if self is branch:
                del raw['value']
                raw[key] = None
            return None
        with monkeypatch.context() as local:
            local.setattr(BranchCondition, '__pydantic_private__', property(mutate))
            outputs.append(call(Fact(branch)))
        assert events == [True]
    identical(*outputs)


def test_real_iterators_observe_child_callback_mutations(backend, monkeypatch):
    events = []
    class Callback(Fact):
        @property
        def __pydantic_extra__(self):
            events.append('callback')
            action()
            return None
        @__pydantic_extra__.setter
        def __pydantic_extra__(self, value):
            pass
    py, c = projections(monkeypatch, backend, (Callback,))
    for mode in ('append', 'replace', 'resize'):
        outputs = []
        for call in (py, c):
            events.clear()
            callback = Callback(0)
            if mode == 'append':
                values = [callback]
                def action(values=values):
                    values.append(9)
            else:
                values = {'first': callback, 'second': 1}
                def action(values=values, mode=mode):
                    values['second' if mode == 'replace' else 'third'] = 9
            if mode == 'resize':
                outputs.append(failure(call, Fact(values)))
            else:
                outputs.append(call(Fact(values)))
            assert events == ['callback']
        if mode == 'resize':
            assert outputs[0] == outputs[1]
        else:
            identical(*outputs)
            assert (outputs[1]['value'][-1] if mode == 'append'
                else outputs[1]['value']['second']) == 9


def test_bad_native_abi_and_require_fail_closed(backend):
    for args in [(Fact, Fact(1), [], (), Fact, Fact, gate.require),
            (Fact, Fact(1), (Fact,), (None,), Fact, Fact, gate.require),
            (Fact, Fact(1), (Fact,), (), Fact, Fact, None)]:
        with pytest.raises(TypeError, match='ABI'):
            backend.project(*args)
    with pytest.raises(RuntimeError, match='did not raise'):
        backend.project(Fact, None, (Fact,), (), Fact, Fact, lambda *args: None)


def test_adapter_unknown_helpers_retains_python_before_native(backend, monkeypatch):
    calls = []
    def changed(expected, model):
        calls.append((expected, model))
        return 'python'
    monkeypatch.setattr(gate, '_trial_typed_storage', changed)
    assert candidate.project(backend, Fact, None) == 'python'
    assert calls == [(Fact, None)]


def test_repeated_cleanup_and_recursion_safety(backend, monkeypatch):
    py, c = projections(monkeypatch, backend)
    for _ in range(200):
        value = Fact([[], (), {'x': [1]}])
        identical(py(value), c(value))
        cycle = []
        cycle.append(cycle)
        assert failure(py, Fact(cycle)) == failure(c, Fact(cycle))
    gc.collect()
    deep = []
    # This installed CPython build has a 10000 C recursion budget, separate
    # from Python's frame limit. Do not assert equal boundary depths.
    for _ in range(20000):
        deep = [deep]
    assert failure(c, Fact(deep))[0] is RecursionError


def test_recursion_difference_blocks_runtime_qualification(backend, monkeypatch):
    py, c = projections(monkeypatch, backend)
    deep = []
    for _ in range(1500):
        deep = [deep]
    assert failure(py, Fact(deep))[0] is RecursionError
    # Separate C and Python budgets are an explicit unresolved qualification,
    # not a claim that the native function is a universal drop-in replacement.
    assert type(c(Fact(deep))) is dict


def test_signal_failure_propagates_and_next_call_is_fresh(backend, monkeypatch):
    _, c = projections(monkeypatch, backend)
    class Interrupt(BaseException):
        pass
    error = Interrupt('native interrupted')
    def handler(signum, frame):
        raise error
    previous = signal.signal(signal.SIGALRM, handler)
    value = Fact([None] * 300000)
    try:
        signal.setitimer(signal.ITIMER_REAL, 0.002)
        with pytest.raises(Interrupt) as caught:
            c(value)
        assert caught.value is error
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    assert c(Fact([1])) == {'value': [1]}


def test_actual_pb_component_cost(backend, contract, record_property):
    """Same real contract, fresh copy and C pickle on both sides; no G0 claim."""
    def py():
        return gate._trial_typed_storage(gate.PBTrialContract, contract)
    def c():
        return native(backend, contract)
    identical(py(), c())
    counts = 1000
    rows = []
    for _ in range(3):
        row = {}
        for name, call in (('python', py), ('native', c)):
            start = time.thread_time_ns()
            for _ in range(counts):
                runtime._cold_graph_bytes(call())
            row[name] = (time.thread_time_ns() - start) / 1e9
        rows.append(row)
    record_property('cost', {'calls_per_sample': counts, 'samples': rows})
    print({'calls_per_sample': counts, 'samples': rows})
