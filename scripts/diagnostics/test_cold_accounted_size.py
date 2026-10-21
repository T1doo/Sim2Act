"""Pure data only: no Worker, producer, SQLite, transport, Mock or G0."""

import random
import sys
import tracemalloc
from dataclasses import replace

import pytest
from cold_accounted_size import Limits, _digits, measure_prepared
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name

from sim2act._cold_accounted_values import _Bounds, _freeze
from sim2act.production_trial_policy import Outcome

# Explicit diagnostics for these finite test data only, not production allowances.
LIMITS = Limits(10000, 20000, 200, 1000000, 2000000, 20000)


def same_packet(value):
    result = measure_prepared(value, LIMITS)
    expected = _freeze(value, _Bounds(
        LIMITS.nodes, LIMITS.edges, LIMITS.depth, LIMITS.leaf_bytes, LIMITS.encoded_bytes
    ))
    assert result.complete, result
    assert result.nodes == len(expected.nodes)
    assert result.edges == expected.edges
    assert result.encoded_bytes == len(expected.encoded)
    return result


@pytest.mark.parametrize('value', [
    None, False, True, 0, 1, -1, 9, 10, -(10**100), 0.0, -0.0, 1.5,
    '', b'', {}, [], (), b'a', b'ab', b'abc', b'abcd',
    quoted_name('quoted\ud800', True),
    ''.join(map(chr, range(256))) + '\u07ff\u0800\uffff\U00010000\U0010ffff\ud800\udfff',
    {'string': '中文😀', 'bytes': b'\x00\xff', 'mixed': [True, 1, 1.0, None]},
])
def test_exact_size_against_real_component_encoder(value):
    same_packet(value)


def test_utf8_escape_and_base64_are_distinct_exact_metrics():
    value = ['a\"\\\n\x00\x7f\u0080\u0800😀\ud800', b'abcde']
    result = same_packet(value)
    text = value[0]
    import json
    assert result.string_utf8_bytes == len(text.encode('utf8', errors='surrogatepass'))
    assert result.string_ascii_bytes == len(json.dumps(text, ensure_ascii=True)) - 2
    assert result.base64_ascii_bytes == 8
    assert result.leaf_bytes == result.string_utf8_bytes + len(value[1])


def test_deterministic_mixed_dags_match_actual_encoding():
    rng = random.Random(20261021)
    pool = [None, False, True, 0, 1000, -1000, 1.25, 'leaf\ud800', b'wire']
    for i in range(120):
        parts = [rng.choice(pool) for _ in range(rng.randrange(5))]
        value = parts if i % 3 == 0 else tuple(parts) if i % 3 == 1 else {
            str(k): v for k, v in enumerate(parts)
        }
        same_packet(value)
        pool.append(value)


def test_shared_dag_not_expanded_per_path_and_longest_path_is_checked():
    value = b'x'
    for _ in range(80):
        value = [value, value]
    result = same_packet(value)
    assert (result.nodes, result.edges, result.depth, result.leaf_bytes) == (81, 160, 80, 1)
    tail = [['x']]
    root = [tail, [tail]]
    assert same_packet(root).depth == 4
    rejected = measure_prepared(root, replace(LIMITS, depth=3))
    assert not rejected.complete and rejected.reason == 'depth' and rejected.depth == 4


@pytest.mark.parametrize('field', ['nodes', 'edges', 'depth', 'leaf_bytes', 'encoded_bytes'])
def test_exact_boundary_and_one_below(field):
    value = {'first': [b'abcdef', ['中文']], 'second': (1234, False)}
    exact = same_packet(value)
    caps = replace(LIMITS, **{
        name: getattr(exact, name) for name in
        ('nodes', 'edges', 'depth', 'leaf_bytes', 'encoded_bytes')
    })
    assert measure_prepared(value, caps).complete
    result = measure_prepared(value, replace(caps, **{field: getattr(caps, field) - 1}))
    assert not result.complete and result.reason == field


def test_deep_input_uses_explicit_stack_not_python_recursion():
    value = None
    for _ in range(1500):
        value = [value]
    result = measure_prepared(value, replace(LIMITS, depth=1600))
    assert result.complete and result.depth == 1500
    assert measure_prepared(value, replace(LIMITS, depth=50)).reason == 'depth'


def test_cycles_unknowns_nonfinite_and_fixed_models_do_not_get_capabilities():
    cycle = []
    cycle.append(cycle)
    assert measure_prepared(cycle, LIMITS).reason == 'cycle'
    calls = []

    class Foreign:
        def __iter__(self):
            calls.append('iter')
            raise AssertionError('no callback')
        def __reduce_ex__(self, protocol):
            calls.append('reduce')
            raise AssertionError('no callback')

    outcome = Outcome(outcome='UNKNOWN', response_sha256='0'*64,
                      response_ascii_bytes=0, prompt_tokens=None,
                      completion_tokens=None, total_tokens=None)
    for value in (Foreign(), {1: 'key'}, float('inf'), float('nan'), outcome):
        assert not measure_prepared(value, LIMITS).complete
    assert calls == []


def test_rowmapping_is_explicitly_ineligible_not_a_visible_column_projection():
    hidden = object()
    row = RowMapping(SimpleResultMetaData(['visible']), None, {'visible': 0}, ('ok', hidden))
    result = measure_prepared(row, LIMITS)
    assert not result.complete and result.reason == 'unsupported_type'
    assert result.nodes == 0
    # Supplying an already prepared, complete storage tuple is different: it is
    # measurable, but building it is not covered by this meter's resource claim.
    assert same_packet((['visible'], ('ok', 'hidden'), {'visible': 0})).complete


def test_unknown_metaclass_equality_is_never_called_for_values_or_keys():
    calls = []

    class ForeignType(type):
        def __eq__(self, other):
            calls.append('type equality')
            return True

    class Foreign(metaclass=ForeignType):
        def __len__(self):
            calls.append('len')
            raise AssertionError('no foreign callback')

    for value in (Foreign(), {Foreign(): 'value'}):
        assert not measure_prepared(value, LIMITS).complete
    assert calls == []


def test_huge_leaf_and_wide_input_stop_without_body_or_container_copy():
    values = [('x' * 1000000, 'leaf_bytes'), (b'x' * 1000000, 'encoded_bytes'),
              ([None] * 1000000, 'edges')]
    for value, reason in values:
        caps = replace(LIMITS, leaf_bytes=1000001, encoded_bytes=1000, edges=1000)
        if type(value) is str:
            caps = replace(caps, leaf_bytes=1000)
        tracemalloc.start()
        try:
            result = measure_prepared(value, caps)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert not result.complete and result.reason == reason
        assert peak < 128 * 1024  # Input allocated before tracking, bounded diagnostic state.


def test_integer_digits_exact_and_runtime_limit_is_respected_without_str_conversion():
    for n in [0, 1, 9, 10, 99, 100] + [10**n + delta for n in range(1, 500, 17)
                                      for delta in (-1, 0, 1)]:
        assert _digits(n) == len(str(n))
    assert measure_prepared(2**100, replace(LIMITS, integer_bits=100)).reason == 'integer_bits'
    if sys.get_int_max_str_digits():
        n = 10**sys.get_int_max_str_digits()
        assert measure_prepared(n, replace(LIMITS, integer_bits=n.bit_length())).reason == 'runtime_integer_digits'


def test_explicit_positive_exact_caps_only():
    for caps in (None, tuple(vars(LIMITS).values()), replace(LIMITS, nodes=0),
                 replace(LIMITS, edges=True)):
        with pytest.raises(ValueError):
            measure_prepared(None, caps)
