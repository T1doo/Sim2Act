"""Full fresh schema witness equivalence, no Mock or model execution."""

import math

import pytest

from sim2act import _cold_base_segment as base
from sim2act import _cold_policy_segment as schema
from sim2act.errors import DomainError


def oracle(value, expected):
    return schema._schema_shape(value, None) == expected


def clone(value):
    if type(value) is dict:
        return {key: clone(child) for key, child in value.items()}
    if type(value) is list:
        return [clone(child) for child in value]
    if type(value) is tuple:
        return tuple(clone(child) for child in value)
    return value


def test_every_live_production_schema_and_each_top_level_field_change():
    for kind, live, expected, _, _ in schema._SCHEMAS:
        assert oracle(live, expected) is schema._schema_matches(live, expected) is True
        assert schema._fixed_schema(kind)
        for key in live:
            changed = clone(live)
            changed[key] = object()
            assert oracle(changed, expected) is schema._schema_matches(changed, expected) is False
        assert oracle(dict(reversed(list(live.items()))), expected) is False
        assert schema._schema_matches(dict(reversed(list(live.items()))), expected) is False


@pytest.mark.parametrize('left,right', [
    (True, 1), (1, 1.0), ([1], (1,)), (None, ''),
    ({'a': 1, 'b': 2}, {'b': 2, 'a': 1}),
    ([{'callback': object()}], [{'callback': object()}]),
    (b'wire', b'other'), (0.0, -0.0),
])
def test_strict_scalar_container_order_and_callback_identity(left, right):
    expected = schema._schema_shape(right, [])
    assert schema._schema_matches(left, expected) is oracle(left, expected)


def test_nan_identity_dag_and_repeated_fresh_mutation():
    nan = float('nan')
    shared = {'value': [nan, True, 1, 1.0, None, b'bytes']}
    live = [shared, shared]
    expected = schema._schema_shape(live, [])
    assert math.isnan(nan)
    assert oracle(live, expected) is schema._schema_matches(live, expected) is True
    shared['value'][0] = float('nan')
    assert oracle(live, expected) is schema._schema_matches(live, expected) is False
    shared['value'][0] = nan
    assert oracle(live, expected) is schema._schema_matches(live, expected) is True
    shared['new'] = []
    assert oracle(live, expected) is schema._schema_matches(live, expected) is False


def test_shared_live_dag_is_compared_to_each_distinct_expected_subtree():
    shared = [1]
    live = [shared, shared]
    expected = schema._schema_shape([[1], [2]], [])
    assert oracle(live, expected) is schema._schema_matches(live, expected) is False


@pytest.mark.parametrize('prefix', ['type', 'length', 'order'])
@pytest.mark.parametrize('bad', ['cycle', 'key'])
def test_structural_mismatch_still_visits_later_invalid_child(prefix, bad):
    invalid = []
    if bad == 'cycle':
        invalid.append(invalid)
    else:
        invalid = {object(): 1}
    if prefix == 'type':
        live, saved = (1, invalid), [1, []]
    elif prefix == 'length':
        live, saved = [1, invalid], [1]
    else:
        live, saved = {'b': 1, 'a': invalid}, {'a': 1, 'b': []}
    expected = schema._schema_shape(saved, [])
    errors = []
    for implementation in (oracle, schema._schema_matches):
        with pytest.raises(DomainError) as caught:
            implementation(live, expected)
        errors.append((caught.value.code, caught.value.message))
    assert errors[0] == errors[1]


@pytest.mark.parametrize('damage', ['cycle', 'key', 'mismatch-then-cycle', 'mismatch-then-key'])
def test_complete_gate_even_after_earlier_mismatch(damage):
    expected = schema._schema_shape([False, []], [])
    value = []
    if damage.endswith('cycle'):
        value.append(value)
    else:
        value = {object(): []}
    live = [True, value] if damage.startswith('mismatch') else value
    errors = []
    for implementation in (oracle, schema._schema_matches):
        with pytest.raises(DomainError) as caught:
            implementation(live, expected)
        errors.append((caught.value.code, caught.value.message))
    assert errors[0] == errors[1]


def test_foreign_objects_are_only_identity_leaves_not_callbacks():
    class Foreign(dict):
        def __iter__(self):
            raise AssertionError('foreign iteration')

        def __eq__(self, other):
            raise AssertionError('foreign equality')

        def __reduce__(self):
            raise AssertionError('foreign reduction')

    foreign = Foreign()
    expected = schema._schema_shape({'leaf': foreign}, [])
    assert oracle({'leaf': foreign}, expected) is schema._schema_matches({'leaf': foreign}, expected) is True
    assert oracle({'leaf': Foreign()}, expected) is schema._schema_matches({'leaf': Foreign()}, expected) is False


def test_replaced_matcher_is_ineligible_before_it_can_execute(monkeypatch):
    kind = schema._SCHEMAS[0][0]
    def forbidden(*args):
        raise AssertionError('unknown matcher called')
    monkeypatch.setattr(schema, '_schema_matches', forbidden)
    assert not schema._fixed_schema(kind)
    assert schema._schema_matches is not base._SCHEMA_MATCHES
