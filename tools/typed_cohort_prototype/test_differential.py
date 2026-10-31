"""Run original boundary cases against the complete candidate, offline only."""
import gc
import pytest
import test_cold_typed_stream as oracle
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport

from sim2act import _cold_cohort_backend as guarded
from sim2act import natural_live_admission as gate
from tools.typed_cohort_prototype.backend import CohortBackend


@pytest.fixture
def candidate_entry(monkeypatch):
    assert guarded._READY and guarded.native.current() is True
    candidate = CohortBackend()
    prior = gc.isenabled()
    gc.disable()  # Both oracle/candidate in this explicit limited-domain test.
    try:
        with monkeypatch.context() as scope:
            scope.setattr(gate, '_trial_typed_values', candidate)
            yield candidate
    finally:
        if prior:
            gc.enable()


@pytest.mark.parametrize('damage', [
    'none', 'bool-int', 'int-float', 'list-tuple', 'missing-field', 'extra-field',
    'fields-set', 'extra-storage', 'private-storage', 'typed-cycle', 'raw-cycle',
    'unknown-typed', 'unknown-raw', 'raw-key', 'mixed-errors',
])
def test_actual_raw_storage(local_origin, candidate_entry, damage):
    oracle.test_complete_header_storage_and_error_order_matches_reference(local_origin, damage)


@pytest.mark.parametrize('number', [float('nan'),float('inf'),-float('inf'),-0.0,0.0])
def test_scalar_rules(local_origin, candidate_entry, number):
    oracle.test_original_nonfinite_and_signed_zero_rules(local_origin, number)


@pytest.mark.parametrize('case', [
    oracle.test_dag_pair_memo_is_not_an_identity_or_single_node_pass,
    oracle.test_different_actual_nodes_against_same_raw_dag_are_compared,
    oracle.test_full_raw_gate_wins_over_early_value_difference,
    oracle.test_rows_and_quoted_keys_keep_original_visible_projection,
    oracle.test_both_none_omissions_nested_fields_and_random_native_data,
    oracle.test_raw_omitted_none_cannot_replace_another_actual_field,
])
def test_value_graphs(local_origin, candidate_entry, case):
    case(local_origin)


@pytest.mark.parametrize('replacement', ['method','descriptor','same-extension'])
def test_original_serializer_callbacks(local_origin, candidate_entry, monkeypatch, replacement):
    oracle.test_modified_serializer_keeps_original_pre_dump_raw_snapshot(
        local_origin, monkeypatch, replacement)


def test_nested_serializer(local_origin, candidate_entry, monkeypatch):
    oracle.test_nested_any_serializer_replacement_keeps_original_snapshot(local_origin, monkeypatch)


def test_invalid_before_descriptor(local_origin, candidate_entry, monkeypatch):
    oracle.test_invalid_actual_rejects_before_dump_descriptor_dispatch(local_origin, monkeypatch)


def test_unknown_helpers_keep_original_stream(local_origin, candidate_entry, monkeypatch):
    oracle.test_standard_path_never_constructs_actual_or_saved_copies(local_origin, monkeypatch)


def test_guard_and_source_values(sql_facts, candidate_entry):
    oracle.test_fresh_source_unknown_and_runcheck_are_content_only(sql_facts)
