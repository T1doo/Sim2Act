"""Optional whole-domain fresh comparison; no Worker/model/Mock execution."""

import copy
import json
import struct
import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from test_cold_graph_fingerprint import no_transports as no_transports

from sim2act import _cold_frontier_compare as candidate
from sim2act import natural_spec_runtime as runtime
from sim2act.contracts import Limits
from sim2act.errors import DomainError

BOUNDS = candidate._Limits(nodes=60000, edges=120000, depth=128,
    leaf_bytes=8 * 1024**2, units=128 * 1024**2, work=10**9, integer_bits=16000)


def select(value, bounds=BOUNDS, **changes):
    arguments = dict(row_type=RowMapping, quoted_type=quoted_name, limits_type=Limits,
        row_storage=runtime._cold_graph_row_storage,
        limit_values=runtime._cold_graph_limit_values,
        cursor_meta=runtime._ColdGraphCursorMeta, simple_meta=runtime._ColdGraphSimpleMeta)
    arguments.update(changes)
    return candidate._select(value, bounds, **arguments)


def limits():
    return Limits(max_requests=4, max_tools=4, max_repairs=1,
        max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)


def graph():
    shared = {'complete': ['all', 'fields'], 'bytes': b'original raw response'}
    keys = [quoted_name('visible', True)]
    data = (shared, {'hidden': [1, 2]})
    row = RowMapping(SimpleResultMetaData(keys), None,
        {'visible': 0, 'hidden_alias': 1}, data)
    return dict(inputs=dict(row=row, raw=data, source=shared, again=[shared]),
        role_limits=dict(source=limits(), generate=limits()),
        phase='pre', binding=dict(contract=dict(value=shared), key='original-key'))


@pytest.mark.parametrize('change', ['field', 'row_hidden', 'key_order', 'index',
    'alias_split', 'alias_join', 'string_alias', 'bytes_alias', 'bool_int',
    'list_tuple', 'binding', 'limits', 'signed_zero', 'nan_bits'])
def test_every_supported_field_order_type_and_alias_change_is_rejected(change):
    value = graph()
    value['floats'] = [0.0, struct.unpack('>d', bytes.fromhex('7ff8000000000001'))[0]]
    first = ('fresh-long-key-for-alias-' * 4)[:-1]
    blob = bytes(bytearray(b'complete raw payload' * 10))
    value['str_alias'] = [first, first]
    value['bytes_alias'] = [blob, blob]
    value['independent'] = [dict(same=1), dict(same=1)]
    before = select(value)
    old = runtime._cold_graph_bytes(value)
    assert before is not None and candidate._same(select(value), before)
    if change == 'field':
        value['inputs']['source']['complete'][1] = 'changed'
    elif change == 'row_hidden':
        value['inputs']['raw'][1]['hidden'].append(3)
    elif change == 'key_order':
        source = value['inputs']['source']
        source['complete'] = source.pop('complete')
    elif change == 'index':
        object.__getattribute__(value['inputs']['row'], '_key_to_index')['hidden_alias'] = 0
    elif change == 'alias_split':
        value['inputs']['again'] = [copy.deepcopy(value['inputs']['source'])]
    elif change == 'alias_join':
        value['independent'][1] = value['independent'][0]
    elif change == 'string_alias':
        replacement = ('prefix-' + first)[7:]
        assert replacement == first and replacement is not first
        value['str_alias'][1] = replacement
    elif change == 'bytes_alias':
        replacement = bytes(bytearray(blob))
        assert replacement == blob and replacement is not blob
        value['bytes_alias'][1] = replacement
    elif change == 'bool_int':
        value['independent'][0]['same'] = True
    elif change == 'list_tuple':
        value['inputs']['source']['complete'] = tuple(value['inputs']['source']['complete'])
    elif change == 'binding':
        value['binding']['key'] += '-changed'
    elif change == 'limits':
        value['role_limits']['source'].__dict__['run_seconds'] -= 1
    elif change == 'signed_zero':
        value['floats'][0] = -0.0
    else:
        value['floats'][1] = struct.unpack('>d', bytes.fromhex('7ff8000000000002'))[0]
    assert runtime._cold_graph_bytes(value) != old
    current = select(value)
    assert current is not None and not candidate._same(current, before)


def test_snapshot_owns_only_recursive_immutable_values_and_no_live_container():
    value = graph()
    before = select(value)
    stack = [before.events]
    while stack:
        item = stack.pop()
        assert type(item) in (tuple, str, bytes, int, bool)
        if type(item) is tuple:
            stack.extend(item)
    value['inputs']['source']['complete'].clear()
    assert not candidate._same(select(value), before)
    # Equivalent fresh source containers are allowed when their complete alias
    # topology is unchanged; identity itself is not a cached validation result.
    original = dict(first=dict(values=['all', 'fields']), typed=(1, False, None))
    original['again'] = original['first']
    copied = copy.deepcopy(original)
    assert runtime._cold_graph_bytes(original) == runtime._cold_graph_bytes(copied)
    assert candidate._same(select(original), select(copied))


def test_active_before_completed_and_unsupported_never_invoke_user_hooks():
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(DomainError, match='Cyclic'):
        select(cyclic)
    calls = []
    class Foreign:
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign equality')
        def __reduce_ex__(self, protocol):
            calls.append('reduce')
            raise AssertionError('foreign reducer')
    assert select([Foreign()]) is None
    assert calls == []


def test_foreign_index_is_metered_without_hash_or_equality_and_before_copy():
    calls, armed = [], [False]
    class Foreign:
        def __hash__(self):
            if armed[0]:
                calls.append('hash')
                raise AssertionError('foreign hash')
            return 0
        def __eq__(self, other):
            if armed[0]:
                calls.append('eq')
                raise AssertionError('foreign equality')
            return False
    row = RowMapping(SimpleResultMetaData(['visible']), None,
        {'visible': 0, Foreign(): 1}, ('visible', dict(hidden='all')))
    armed[0] = True
    assert select(row) is not None
    def forbidden(value):
        raise AssertionError('adapter allocated after failed preselection')
    assert select(row, BOUNDS._replace(units=800), row_storage=forbidden) is None
    assert calls == []


@pytest.mark.parametrize('field,limit', [('nodes', 1), ('edges', 1), ('depth', 1),
    ('leaf_bytes', 1), ('units', 1), ('work', 1), ('integer_bits', 1)])
def test_capacity_only_selects_original_verifier_before_validation(field, limit):
    value = graph()
    old = runtime._cold_graph_bytes(value)
    assert select(value, BOUNDS._replace(**{field: limit})) is None
    assert runtime._cold_graph_bytes(value) == old


def test_real_sqlite_row_graph_alternating_inclusive_projection_cost(tmp_path):
    """A rejection screen, not an estimate of G0 or the complete tail."""
    engine = create_engine('sqlite:///:memory:')
    try:
        with engine.connect() as connection:
            rows = connection.execute(text('select :a as first, :b as second'),
                dict(a='complete real SQLite payload ' * 250,
                     b='another complete SQLite field ' * 250)).mappings().all()
            value = dict(rows=rows, independent=rows[0], hidden=object.__getattribute__(rows[0], '_data'),
                         limits=limits(), phase='pre')
            before = select(value)
            expected = runtime._cold_graph_bytes(value)
            assert before is not None and candidate._same(select(value), before)
            # Selection + constructing all immutable events + comparison are
            # included. No helper-only percentage is promoted to whole-chain.
            cpu = dict(original=[], fresh_compare=[])
            for turn in range(20):
                order = ('original', 'fresh_compare') if turn % 2 == 0 else ('fresh_compare', 'original')
                for mode in order:
                    started = time.thread_time_ns()
                    for _ in range(20):
                        if mode == 'original':
                            assert runtime._cold_graph_bytes(value) == expected
                        else:
                            assert candidate._same(select(value), before)
                    cpu[mode].append(time.thread_time_ns() - started)
            report = dict(classification='COMPONENT_REJECTION_SCREEN_NOT_COMPLETE_TAIL_OR_G0',
                repetitions_per_mode=400, alternating_batches=20,
                bytes_per_original=len(expected), counters=dict(nodes=before.nodes,
                    edges=before.edges, leaf_bytes=before.leaf_bytes, units=before.units, work=before.work),
                thread_cpu_ns=cpu, sums_ns={key: sum(items) for key, items in cpu.items()})
            (tmp_path / 'comparison-screen.json').write_text(json.dumps(report, indent=2))
    finally:
        engine.dispose()
