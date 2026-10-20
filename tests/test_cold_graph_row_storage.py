"""Draft only: full raw-row local-pin coverage; no model/claim/Run execution.

Root must apply/review the candidate and run these tests with the existing codec
module. This file has only been parsed, never imported or executed by the author.
"""
import copy

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from test_cold_graph_fingerprint import no_transports as no_transports

from sim2act import natural_spec_runtime as runtime
from sim2act.errors import DomainError


def row():
    metadata = SimpleResultMetaData([quoted_name('first', True), 'second'])
    return RowMapping(metadata, None, {'first': 0, 'second': 1, 'unused_alias': 2},
                      (dict(value='same'), dict(value='same'), dict(hidden=['complete'])))


def test_payload_retains_original_keys_data_and_complete_safe_index():
    value = row()
    keys, data, index = runtime._cold_graph_row_storage(value)
    assert keys is object.__getattribute__(object.__getattribute__(value, '_parent'), '_keys')
    assert data is object.__getattribute__(value, '_data')
    assert index == {'first': 0, 'second': 1, 'unused_alias': 2}
    assert all(type(key) is str for key in index)
    # Existing pure-cohort consumers retain the visible-pairs API unchanged.
    visible_pairs = runtime._cold_graph_row_values(value)
    assert type(visible_pairs) is tuple and visible_pairs == tuple(value.items())
    runtime._cold_graph_validate_inputs(value)
    # Direct raw-data alias remains part of this complete graph's local pin.
    aliased = dict(row=value, data=data)
    independent = dict(row=value, data=tuple(copy.deepcopy(list(data))))
    assert runtime._cold_graph_inputs(aliased) != runtime._cold_graph_inputs(independent)


def test_hidden_unused_data_mutation_changes_pin_without_changing_visible_mapping():
    value = row()
    before = runtime._cold_graph_inputs(value)
    visible = runtime._model_inputs(value)
    object.__getattribute__(value, '_data')[2]['hidden'].append('changed unused position')
    assert runtime._model_inputs(value) == visible
    runtime._cold_graph_validate_inputs(value)
    assert runtime._cold_graph_inputs(value) != before


@pytest.mark.parametrize('change', ['keys_order', 'visible_equal_position', 'unused_index_position'])
def test_controlled_metadata_mutations_are_bound_even_when_visible_values_are_equal(change):
    value = row()
    before = runtime._cold_graph_inputs(value)
    visible = runtime._model_inputs(value)
    if change == 'keys_order':
        object.__getattribute__(object.__getattribute__(value, '_parent'), '_keys').reverse()
    elif change == 'visible_equal_position':
        object.__getattribute__(value, '_key_to_index')['first'] = 1
    else:
        object.__getattribute__(value, '_key_to_index')['unused_alias'] = 1
    assert runtime._model_inputs(value) == visible
    runtime._cold_graph_validate_inputs(value)
    assert runtime._cold_graph_inputs(value) != before


@pytest.mark.parametrize('position', [True, -1, 3])
def test_invalid_unused_safe_index_position_is_rejected(position):
    value = row()
    object.__getattribute__(value, '_key_to_index')['unused_alias'] = position
    for encode in (runtime._cold_graph_bytes, runtime._cold_graph_validate_inputs):
        with pytest.raises(DomainError):
            encode(value)


def test_unused_data_root_backedge_is_not_hidden_from_incoming_validator():
    root = dict(existing=dict(value='complete'))
    value = RowMapping(SimpleResultMetaData(['visible']), None, {'visible': 0}, ('ordinary', root))
    assert dict(value) == {'visible': 'ordinary'}
    runtime._cold_graph_validate_inputs(value)  # Still acyclic before installation.
    with pytest.raises(DomainError):
        runtime._cold_graph_validate_inputs(value, _forbid_root=root)
    independent = RowMapping(SimpleResultMetaData(['visible']), None, {'visible': 0},
                             ('ordinary', copy.deepcopy(root)))
    runtime._cold_graph_validate_inputs(independent, _forbid_root=root)


def test_unused_data_cycle_and_unknown_reducer_are_rejected_without_callback():
    calls = []
    class Foreign:
        def __reduce__(self):
            calls.append('reduce')
            raise AssertionError('Hidden object must be refused before callback')
        def __reduce_ex__(self, protocol):
            calls.append('reduce_ex')
            raise AssertionError('Hidden object must be refused before callback')
    unknown = RowMapping(SimpleResultMetaData(['visible']), None, {'visible': 0}, ('ordinary', Foreign()))
    for encode in (runtime._cold_graph_bytes, runtime._cold_graph_validate_inputs):
        with pytest.raises(DomainError):
            encode(unknown)
    assert calls == []
    hidden = {}
    cyclic = RowMapping(SimpleResultMetaData(['visible']), None, {'visible': 0}, ('ordinary', hidden))
    hidden['row'] = cyclic
    with pytest.raises(DomainError):
        runtime._cold_graph_validate_inputs(cyclic)


def test_valid_safe_index_does_not_touch_colliding_foreign_key_callbacks():
    calls = []
    armed = [False]
    class ForeignKey:
        def __hash__(self):
            if armed[0]:
                calls.append('hash')
                raise AssertionError('Codec must never hash a foreign index key')
            return hash('visible')
        def __eq__(self, other):
            if armed[0]:
                calls.append('eq')
                raise AssertionError('Codec must never compare a foreign index key')
            return False
    index = {'visible': 0, ForeignKey(): 1}
    value = RowMapping(SimpleResultMetaData(['visible']), None, index, ('ordinary', dict(hidden='complete')))
    armed[0] = True
    runtime._cold_graph_validate_inputs(value)
    runtime._cold_graph_bytes(value)
    assert calls == []
