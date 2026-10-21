"""Pre-projection qualification; no Worker/transport/Mock/G0."""

import gc
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

import pytest
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_typed_native import backend as backend
from test_cold_typed_storage_alias_contract import contract as contract

from sim2act import _cold_typed_native_candidate as candidate
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime


@pytest.fixture
def selected(backend):
    result = candidate.load_candidate(backend.__file__)
    assert result is not None
    return result


def exact(left, right):
    assert gate._trial_typed_equal(left, right)
    assert runtime._cold_graph_bytes(left) == runtime._cold_graph_bytes(right)


def test_actual_pb_selects_c_and_net_cost_includes_qualification(selected, contract, tmp_path):
    old = gate._trial_typed_storage(gate.PBTrialContract, contract)
    actual = selected.select(gate.PBTrialContract, contract)
    print('selection', selected.last)
    assert actual is not None and selected.native_calls == 1
    exact(old, actual)
    measurements = []
    for index in range(5):
        row = {}
        for mode in (('python', 'qualified') if index % 2 == 0 else ('qualified', 'python')):
            start = time.thread_time_ns()
            for _ in range(1000):
                value = None
                if mode == 'qualified':
                    value = selected.select(gate.PBTrialContract, contract)
                if value is None:
                    value = gate._trial_typed_storage(gate.PBTrialContract, contract)
                runtime._cold_graph_bytes(value)
            row[mode] = (time.thread_time_ns() - start) / 1e9
        measurements.append(row)
    report = dict(samples=measurements, calls_per_sample=1000,
        medians={name: statistics.median(row[name] for row in measurements)
            for name in ('python', 'qualified')},
        native_calls=selected.native_calls, python_selections=selected.python_calls,
        selection=selected.last, reasons=selected.reasons)
    (tmp_path / 'net-cost.json').write_text(json.dumps(report, indent=2))
    print('net-cost', report)


def test_mixed_native_containers_dag_and_fresh_call(selected, contract):
    shared = [True, 1, 1.0, b's', None]
    contract.__dict__['quota_subject'] = ([shared], (shared, {'key': shared}))
    actual = selected.select(gate.PBTrialContract, contract)
    assert actual is not None
    exact(actual, gate._trial_typed_storage(gate.PBTrialContract, contract))
    shared.append('fresh')
    following = selected.select(gate.PBTrialContract, contract)
    exact(following, gate._trial_typed_storage(gate.PBTrialContract, contract))
    assert actual['quota_subject'][0][0] is actual['quota_subject'][1][0]
    assert len(following['quota_subject'][0][0]) > len(actual['quota_subject'][0][0])


def test_deep_and_scan_excess_select_original_before_projection(selected, contract):
    deep = []
    for _ in range(1500):
        deep = (deep,)
    contract.__dict__['quota_subject'] = deep
    assert selected.select(gate.PBTrialContract, contract) is None
    assert selected.native_calls == 0
    assert selected.last['reason'] in ('remaining-stack', 'scan-budget')
    with pytest.raises(RecursionError):
        gate._trial_typed_storage(gate.PBTrialContract, contract)
    contract.__dict__['quota_subject'] = [None] * 500
    assert selected.select(gate.PBTrialContract, contract) is None
    assert len(gate._trial_typed_storage(gate.PBTrialContract, contract)['quota_subject']) == 500


def test_current_remaining_python_stack_not_just_limit(selected, contract):
    limit = sys.getrecursionlimit()
    def descend():
        frame, depth = sys._getframe(), 0
        while frame is not None:
            depth += 1
            frame = frame.f_back
        if limit - depth > 80:
            return descend()
        value = selected.select(gate.PBTrialContract, contract)
        return value, selected.last
    value, report = descend()
    assert value is None and report['reason'] == 'remaining-stack'
    assert report['python_remaining'] < report['stack_need']
    assert report['c_remaining'] > 0 and sys.getrecursionlimit() == limit
    assert selected.select(gate.PBTrialContract, contract) is not None


def test_unknown_descriptor_once_partial_model_and_recovery(selected, contract, monkeypatch):
    cls = type(contract.caps)
    error = ValueError('original callback once')
    calls = []
    def unknown(model):
        calls.append(model)
        raise error
    with monkeypatch.context() as patch:
        patch.setattr(cls, '__pydantic_private__', property(unknown))
        assert selected.select(gate.PBTrialContract, contract) is None
        assert calls == []
        with pytest.raises(ValueError) as caught:
            gate._trial_typed_storage(gate.PBTrialContract, contract)
        assert caught.value is error and calls == [contract.caps]
    assert selected.select(gate.PBTrialContract, contract) is not None
    partial = object.__new__(type(contract))
    assert selected.select(gate.PBTrialContract, partial) is None
    with pytest.raises(AttributeError):
        gate._trial_typed_storage(gate.PBTrialContract, partial)
    assert selected.select(gate.PBTrialContract, contract) is not None


def test_metaclass_data_descriptor_does_not_execute_during_selection(selected, contract, monkeypatch):
    calls = []
    error = ValueError('original fields descriptor once')
    def changed(cls):
        calls.append(cls)
        raise error
    with monkeypatch.context() as patch:
        patch.setattr(type(type(contract)), '__pydantic_fields__', property(changed), raising=False)
        assert selected.select(gate.PBTrialContract, contract) is None
        assert calls == []
        with pytest.raises(ValueError) as caught:
            gate._trial_typed_storage(gate.PBTrialContract, contract)
        assert caught.value is error and calls == [type(contract)]
    assert selected.select(gate.PBTrialContract, contract) is not None


def test_unknown_build_rejected_before_extension_import(selected, tmp_path, monkeypatch):
    source = Path(selected.module.__file__)
    binary = tmp_path / source.name
    binary.write_bytes(source.read_bytes())
    manifest = json.loads(source.with_suffix(source.suffix + '.json').read_text())
    manifest['output'] = str(binary)
    manifest['python'] = '3.12.99 unknown build'
    binary.with_suffix(binary.suffix + '.json').write_text(json.dumps(manifest))
    def forbidden(*args, **kwargs):
        pytest.fail('Unknown build must not load native code')
    monkeypatch.setattr(importlib.util, 'module_from_spec', forbidden)
    assert candidate.load_candidate(binary) is None


def test_foreign_namespace_is_gated_without_hash_or_equality(selected, contract):
    cls = type(contract.caps)
    space = next(value for value in gc.get_referents(cls)
        if type(value) is dict and value.get('__module__') == cls.__module__)
    calls = []
    class Foreign:
        def __hash__(self):
            calls.append('hash')
            return hash('__pydantic_private__')
        def __eq__(self, other):
            calls.append('equal')
            return False
    key = Foreign()
    space[key] = None
    try:
        calls.clear()
        assert selected.select(gate.PBTrialContract, contract) is None
        assert calls == []
    finally:
        del space[key]
    assert selected.select(gate.PBTrialContract, contract) is not None


def test_instance_and_class_dispatch_cannot_bypass_qualification(selected, contract, monkeypatch):
    with pytest.raises(AttributeError):
        selected.select = lambda *args: pytest.fail('instance callback')
    fake = object.__new__(candidate._QualifiedBackend)
    assert candidate.select_candidate(fake, gate.PBTrialContract, contract) is None
    def forbidden(*args):
        pytest.fail('unknown class method callback')
    monkeypatch.setattr(candidate._QualifiedBackend, 'select', forbidden)
    assert candidate.select_candidate(selected, gate.PBTrialContract, contract) is None


def test_qualification_does_not_retain_model_or_namespace_references(selected, contract):
    space = next(value for value in gc.get_referents(type(contract))
        if type(value) is dict and value.get('__module__') == type(contract).__module__)
    before = sys.getrefcount(space), sys.getrefcount(contract)
    for _ in range(100):
        assert selected.select(gate.PBTrialContract, contract) is not None
    assert (sys.getrefcount(space), sys.getrefcount(contract)) == before


def test_input_bytes_selected_and_default_bytes_same_original_fallback_frame(sql_facts, selected, monkeypatch):
    f = sql_facts
    graph = object.__new__(runtime._ColdGraphRead)
    graph._accounted_frontier = None
    graph.binding = f.binding
    graph.inputs, graph.role_limits, graph.phase = {}, {}, 'pre'
    graph._typed_native_candidate = None
    original = graph.input_bytes()
    graph._typed_native_candidate = selected
    assert graph.input_bytes() == original
    assert selected.native_calls > 0
    calls = []
    saved = gate._trial_typed_storage
    def unknown(expected, model):
        calls.append(sys._getframe(1).f_code.co_name)
        return saved(expected, model)
    monkeypatch.setattr(gate, '_trial_typed_storage', unknown)
    assert graph.input_bytes() == original
    assert calls == ['input_bytes']


def test_extreme_remaining_stack_partial_input_keeps_original_error(sql_facts, selected):
    f = sql_facts
    graph = object.__new__(runtime._ColdGraphRead)
    graph._accounted_frontier = None
    graph.binding = f.binding
    graph.inputs, graph.role_limits, graph.phase = {}, {}, 'pre'
    original = f.binding.contract
    object.__setattr__(f.binding, 'contract', object.__new__(type(original)))
    limit = sys.getrecursionlimit()
    def descend():
        frame, depth = sys._getframe(), 0
        while frame is not None:
            depth += 1
            frame = frame.f_back
        if limit - depth > 12:
            return descend()
        try:
            graph.input_bytes()
        except Exception as error:
            return type(error), error.args
        pytest.fail('partial input cannot succeed')
    try:
        graph._typed_native_candidate = None
        old = descend()
        graph._typed_native_candidate = selected
        new = descend()
        assert old == new and old[0] is AttributeError
        assert selected.native_calls == selected.python_calls == 0
    finally:
        object.__setattr__(f.binding, 'contract', original)
