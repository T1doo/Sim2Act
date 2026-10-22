"""Explicit fresh row leaf, isolated SQLite, no Worker/Mock/HTTP/G0."""

import gc
import inspect
import json
import os
import statistics
import subprocess
import sys
import sysconfig
import time
from types import SimpleNamespace
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
import test_cold_graph_row_storage as original_cases

from sim2act import _cold_row_native_candidate as candidate
from sim2act import natural_spec_runtime as runtime
from sim2act import natural_live_admission as gate
from sim2act.db import runs, attempts, grants

ORIGINAL = runtime._cold_graph_row_storage


@pytest.fixture
def reader():
    directory = os.environ.get('COLD_ROW_TEST_DIR')
    if directory is None:
        pytest.skip('Explicit isolated native row build required')
    path = Path(directory) / ('_cold_row_native_impl' + sysconfig.get_config_var('EXT_SUFFIX'))
    result = candidate.load_candidate(path)
    assert result is not None
    return result


def test_original_keys_data_and_index_key_position_identity(reader):
    key = ('not-interned-' + str(id(reader)))[1:]
    pos = int('257')
    data = tuple(range(300))
    value = RowMapping(SimpleResultMetaData([key]), None, {key: pos, 'hidden': 299}, data)
    before = ORIGINAL(value)
    after = reader.storage(value)
    assert reader.counts() == (1, 0)
    assert after[0] is before[0] and after[1] is before[1] is data
    assert next(iter(after[2])) is key and after[2][key] is pos
    assert after[2] is not before[2]
    assert runtime._cold_graph_bytes(dict(payload=before, key=key, pos=pos, data=data)) == \
        runtime._cold_graph_bytes(dict(payload=after, key=key, pos=pos, data=data))


CASES = [(name, {}) for name in (
    'test_payload_retains_original_keys_data_and_complete_safe_index',
    'test_hidden_unused_data_mutation_changes_pin_without_changing_visible_mapping',
    'test_unused_data_root_backedge_is_not_hidden_from_incoming_validator',
    'test_unused_data_cycle_and_unknown_reducer_are_rejected_without_callback',
    'test_valid_safe_index_does_not_touch_colliding_foreign_key_callbacks',
    'test_shared_row_metadata_is_reread_after_pickle_global_import_callback',
    'test_invalid_hidden_position_precedes_missing_visible_index')]
CASES += [('test_controlled_metadata_mutations_are_bound_even_when_visible_values_are_equal',
    dict(change=value)) for value in ['keys_order', 'visible_equal_position', 'unused_index_position']]
CASES += [('test_invalid_unused_safe_index_position_is_rejected', dict(position=value))
    for value in [True, -1, 3]]


@pytest.mark.parametrize('name,kwargs', CASES)
def test_original_row_safety_regressions_with_same_pickler(reader, monkeypatch, name, kwargs):
    function = getattr(original_cases, name)
    if 'monkeypatch' in inspect.signature(function).parameters:
        kwargs = dict(kwargs, monkeypatch=monkeypatch)
    with monkeypatch.context() as patch:
        patch.setattr(runtime, '_cold_graph_row_storage', reader.storage)
        function(**kwargs)


@pytest.mark.parametrize('position', [True, -1, 3, 10**1000, -(10**1000)])
def test_exact_original_error_category_and_order(reader, position):
    value = RowMapping(SimpleResultMetaData(['missing']), None, {'hidden': position}, ('same',))
    failures = []
    for storage in (ORIGINAL, reader.storage):
        with pytest.raises(Exception) as caught:
            storage(value)
        failures.append((type(caught.value), caught.value.args))
    assert failures[0] == failures[1]
    assert 'index positions' in str(failures[0][1])
    assert reader.counts() == (1, 0)


@pytest.mark.parametrize('change', ['descriptor', 'row-descriptor', 'require', 'leaf', 'codec', 'str', 'quote-slot', 'code'])
def test_unknown_callback_selected_before_projection_once(reader, monkeypatch, change):
    calls = []
    value = original_cases.row()
    error = ValueError('original callback')
    def callback(*args):
        calls.append(sys._getframe(1).f_code)
        raise error
    with monkeypatch.context() as patch:
        if change == 'descriptor':
            patch.setattr(SimpleResultMetaData, '_keys', property(callback))
        elif change == 'row-descriptor':
            patch.setattr(RowMapping, '_parent', property(callback))
        elif change == 'require':
            patch.setattr(runtime, 'require', callback)
        elif change == 'leaf':
            patch.setattr(runtime.codec, 'require', callback)
        elif change == 'codec':
            patch.setattr(runtime, 'codec', SimpleNamespace(require=callback))
        elif change == 'str':
            name = quoted_name('quoted', True)
            value = RowMapping(SimpleResultMetaData([name]), None, {name: 0}, ('same',))
            patch.setattr(runtime, 'str', callback, raising=False)
        elif change == 'quote-slot':
            patch.setattr(quoted_name, '__str__', callback)
        else:
            def changed(value):
                return _row_test_callback(value)
            patch.setattr(runtime, '_row_test_callback', callback, raising=False)
            patch.setattr(ORIGINAL, '__code__', changed.__code__)
        with pytest.raises(ValueError) as caught:
            reader.storage(value)
        assert caught.value is error
    assert len(calls) == 1 and reader.counts() == (0, 1)
    assert reader.storage(value) == ORIGINAL(value)


@pytest.mark.parametrize('oversize', ['keys', 'foreign-index', 'strings'])
def test_optimization_budget_does_not_narrow_accepted_rows(reader, oversize):
    if oversize == 'keys':
        names = [f'key{i}' for i in range(65)]
        value = RowMapping(SimpleResultMetaData(names), None, dict.fromkeys(names, 0), ('same',))
    elif oversize == 'strings':
        key = 'x' * 8193
        value = RowMapping(SimpleResultMetaData([key]), None, {key: 0}, ('same',))
    else:
        class Foreign:
            def __hash__(self):
                if armed[0]:
                    pytest.fail('Foreign hash forbidden after index construction')
                return id(self)
            def __eq__(self, other):
                pytest.fail('Foreign equality forbidden')
        armed = [False]
        index = {Foreign(): object() for _ in range(65)}
        index['visible'] = 0
        value = RowMapping(SimpleResultMetaData(['visible']), None, index, ('same',))
        armed[0] = True
    actual = reader.storage(value)
    expected = ORIGINAL(value)
    assert actual[0] is expected[0] and actual[1] is expected[1]
    assert runtime._cold_graph_bytes(actual) == runtime._cold_graph_bytes(expected)
    assert reader.counts() == (0, 1)


def test_sparse_index_with_large_deleted_history_selects_legacy(reader):
    index = {str(i): 0 for i in range(20000)}
    for key in list(index):
        if key != '0':
            del index[key]
    assert len(index) == 1 and dict.__sizeof__(index) > 8192
    value = RowMapping(SimpleResultMetaData(['0']), None, index, ('same',))
    actual, expected = reader.storage(value), ORIGINAL(value)
    assert runtime._cold_graph_bytes(actual) == runtime._cold_graph_bytes(expected)
    assert reader.counts() == (0, 1)


def test_sparse_class_namespace_budget_in_isolated_readonly_child(reader):
    # Class dictionary capacity cannot be restored portably after deletion.
    # Keep this own read-only component process isolated from later timings.
    script = '''
import os,sysconfig
from pathlib import Path
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sim2act import _cold_row_native_candidate as candidate
path=Path(os.environ['COLD_ROW_TEST_DIR'])/('_cold_row_native_impl'+sysconfig.get_config_var('EXT_SUFFIX'))
reader=candidate.load_candidate(path)
assert reader is not None
value=RowMapping(SimpleResultMetaData(['visible']),None,{'visible':0},('same',))
assert reader.entry(value) is not None
for i in range(2000): setattr(RowMapping,'_offline_churn_'+str(i),None)
for i in range(2000): delattr(RowMapping,'_offline_churn_'+str(i))
assert reader.entry(value) is None
assert reader.storage(value)[2]=={'visible':0}
assert reader.counts()==(1,2)
print('sparse class namespace rejected before scanning/projecting; original accepted')
'''
    env = dict(os.environ, PYTHONPATH=str(Path(runtime.__file__).parents[1]))
    completed = subprocess.run([sys.executable, '-c', script], env=env,
        capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_partial_construction_failure_preserves_error_and_recovery(reader):
    partial = RowMapping.__new__(RowMapping)
    failures = []
    for storage in (ORIGINAL, reader.storage):
        with pytest.raises(Exception) as caught:
            storage(partial)
        failures.append((type(caught.value), caught.value.args))
    assert failures[0] == failures[1]
    assert reader.storage(original_cases.row()) == ORIGINAL(original_cases.row())


def test_partial_metadata_getter_error_never_retries(reader, monkeypatch):
    metadata = SimpleResultMetaData.__new__(SimpleResultMetaData)
    value = RowMapping(metadata, None, {'visible': 0}, ('same',))
    with pytest.raises(AttributeError) as expected:
        ORIGINAL(value)
    def forbidden(value):
        pytest.fail('Native getter exception must not retry original')
    with monkeypatch.context() as patch:
        patch.setattr(candidate, '_ORIGINAL', forbidden)
        with pytest.raises(AttributeError) as actual:
            reader.storage(value)
    assert actual.value.args == expected.value.args
    assert reader.storage(original_cases.row()) == ORIGINAL(original_cases.row())


def test_foreign_index_value_is_not_inspected_or_converted(reader):
    armed = [False]
    class Foreign:
        def __hash__(self):
            if armed[0]:
                pytest.fail('Foreign key must not be hashed')
            return hash('visible')
        def __eq__(self, other):
            if armed[0]:
                pytest.fail('Foreign key must not be compared')
            return False
    class Position:
        def __index__(self):
            pytest.fail('Foreign position must not be converted')
    index = {'visible': 0, Foreign(): Position()}
    value = RowMapping(SimpleResultMetaData(['visible']), None, index, ('same', 'hidden'))
    armed[0] = True
    actual = reader.storage(value)
    assert actual[2] == {'visible': 0} and reader.counts() == (1, 0)
    assert actual[1] is object.__getattribute__(value, '_data')


def test_unknown_duck_layout_uses_original_single_argument_function_once(reader):
    calls = []
    class Unknown:
        _data = ('complete',)
        _key_to_index = {'visible': 0}
        @property
        def _parent(self):
            calls.append(sys._getframe(1).f_code)
            return SimpleResultMetaData(['visible'])
    value = Unknown()
    actual = reader.storage(value)
    assert calls == [ORIGINAL.__code__] and reader.counts() == (0, 1)
    assert actual[2] == {'visible': 0}


def test_native_error_never_retries_original_and_allows_next_call(reader, monkeypatch):
    value = RowMapping(SimpleResultMetaData(['visible']), None, {'hidden': True}, ('same',))
    def forbidden(value):
        pytest.fail('Native validation failure must not retry original')
    with monkeypatch.context() as patch:
        patch.setattr(candidate, '_ORIGINAL', forbidden)
        with pytest.raises(runtime.DomainError):
            reader.storage(value)
    assert reader.counts() == (1, 0)
    assert reader.storage(original_cases.row()) == ORIGINAL(original_cases.row())


def test_loader_rejects_unknown_binary_before_extension_initialization(reader, tmp_path, monkeypatch):
    path = Path(reader.module.__file__)
    binary = tmp_path / path.name
    binary.write_bytes(path.read_bytes() + b'unknown binary')
    proof = json.loads(path.with_suffix(path.suffix + '.json').read_text())
    proof['output'] = str(binary)
    binary.with_suffix(binary.suffix + '.json').write_text(json.dumps(proof))
    def forbidden(*args, **kwargs):
        pytest.fail('Unknown source/binary must be rejected before native import')
    monkeypatch.setattr(candidate.importlib.util, 'module_from_spec', forbidden)
    assert candidate.load_candidate(binary) is None


@pytest.mark.parametrize('change', ['row-slot', 'metadata-slot', 'kind-alias'])
def test_unknown_initial_layout_rejected_without_loading_or_callback(reader, monkeypatch, change):
    path = Path(reader.module.__file__)
    def forbidden(*args, **kwargs):
        pytest.fail('Unknown initial layout must not execute descriptor or import extension')
    with monkeypatch.context() as patch:
        patch.setattr(candidate.importlib.util, 'module_from_spec', forbidden)
        if change == 'row-slot':
            patch.setattr(RowMapping, '_parent', property(forbidden))
        elif change == 'metadata-slot':
            patch.setattr(SimpleResultMetaData, '_keys', SimpleResultMetaData._unique_filters)
        else:
            patch.setattr(runtime, '_ColdGraphSimpleMeta', type('UnknownMeta', (), {}))
        assert candidate.load_candidate(path) is None


def test_actual_sqlite_wire_aliases_freshness_and_net_cpu(reader, sql_facts, monkeypatch, tmp_path):
    f = sql_facts
    with f.store.tx() as c:
        values = {table.name: list(c.execute(select(table)).mappings().all()) for table in (runs, attempts, grants)}
        values['contract'] = gate._trial_typed_storage(gate.PBTrialContract, f.contract)
        row = values['runs'][0]
        values['run-data-alias'] = object.__getattribute__(row, '_data')
        values['run-keys-alias'] = object.__getattribute__(object.__getattribute__(row, '_parent'), '_keys')
        expected = runtime._cold_graph_bytes(values)
        pickler = runtime._ColdGraphPickler
        with monkeypatch.context() as patch:
            patch.setattr(runtime, '_cold_graph_row_storage', reader.storage)
            assert runtime._cold_graph_bytes(values) == expected
        assert runtime._ColdGraphPickler is pickler
        assert reader.counts()[0] > 0
        samples = []
        for index in range(7):
            sample = {}
            for name in (('python', 'candidate') if index % 2 == 0 else ('candidate', 'python')):
                with monkeypatch.context() as patch:
                    patch.setattr(runtime, '_cold_graph_row_storage', ORIGINAL if name == 'python' else reader.storage)
                    start = time.thread_time_ns()
                    for _ in range(1000):
                        actual = runtime._cold_graph_bytes(values)
                    sample[name] = (time.thread_time_ns() - start) / 1e9
                assert actual == expected
            samples.append(sample)
        gc.collect()
        objects = [runtime._ColdGraphRowMapping, runtime._ColdGraphCursorMeta,
            runtime._ColdGraphSimpleMeta, runtime._ColdGraphQuotedName, ORIGINAL]
        before = [sys.getrefcount(obj) for obj in objects]
        for _ in range(100):
            reader.storage(row)
        assert before == [sys.getrefcount(obj) for obj in objects]
        report = dict(samples=samples, calls_per_sample=1000, wire_bytes=len(expected),
            medians={name: statistics.median(sample[name] for sample in samples) for name in ('python', 'candidate')},
            shape={key: len(value) for key,value in values.items() if type(value) is list},
            dispatch=reader.counts(), same_pickler=True, default_switch=False,
            limits='isolated actual SQLite rows, includes wrapper/static qualification/fresh lookup; not G0/full Cold graph')
        (tmp_path / 'row-cost.json').write_text(json.dumps(report, indent=2)+'\n')
        print('row-cost', report)
