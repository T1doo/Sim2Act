"""Real isolated SQLite scope/owned frontier; no prepare/Worker/Mock calls."""

from dataclasses import replace

import pytest
from sqlalchemy import update
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_frontier_compare import BOUNDS

from sim2act import natural_spec_runtime as runtime
from sim2act.db import grants
from sim2act.errors import DomainError


def configured(graph, source, generated, candidate):
    candidate.config = replace(candidate.config, frontier_compare=BOUNDS)


def test_native_complete_envelope_baseline_keeps_old_bytes_and_scope(sql_facts):
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c, before_choose=configured) as s:
        frontier = s.graph._accounted_frontier
        assert frontier.compare_limits is BOUNDS
        s.graph.check(f.store, c)
        baseline = frontier.compare_baseline
        assert baseline is not None
        for _ in range(2):
            s.graph.check(f.store, c)
        assert frontier.compare_counts['selected'] >= 2
        assert frontier.compare_baseline is baseline
        values = s.graph.input_bytes(_frontier_inputs=frontier.values(), _return_frontier_values=True)
        assert s.graph.input_bytes(_frontier_inputs=frontier.values()) == runtime._cold_graph_bytes(values)
        with pytest.raises(DomainError, match='legacy origin'):
            s.graph.input_bytes()
        with pytest.raises(DomainError):
            s.graph.input_bytes(_return_frontier_values=True)
        with pytest.raises(DomainError):
            s.graph.input_bytes(_frontier_inputs=dict(frontier.values()), _return_frontier_values=True)
    assert not s.graph.active and not s.mode.active
    with pytest.raises(DomainError):
        s.graph.check(f.store, c)


def test_complete_read_alias_mutation_still_invalidates(sql_facts):
    f = sql_facts
    def setup(graph, source, generated, candidate):
        shared = ['full fresh content']
        graph.add('independent-aliases', dict(first=shared, second=shared))
        configured(graph, source, generated, candidate)
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c, before_choose=setup) as s:
        s.graph.check(f.store, c)
        value = s.graph.inputs['independent-aliases']
        value['second'] = list(value['first'])
        s.graph.check(f.store, c)
    assert not s.graph.active and not s.mode.active


def test_new_root_does_not_bless_old_root_drift(sql_facts, monkeypatch):
    f = sql_facts
    with pytest.raises(DomainError, match='while adding'), f.store.tx() as c:
        with native_segment(f, c, before_choose=configured) as s:
            s.graph.check(f.store, c)
            original = runtime._cold_graph_validate_inputs
            def incoming(value, **kwargs):
                result = original(value, **kwargs)
                if value == {'test-new-root': True}:
                    s.graph.inputs['synthetic-native-candidate'] = False
                return result
            monkeypatch.setattr(runtime, '_cold_graph_validate_inputs', incoming)
            s.graph.add('settlement-parsed', {'test-new-root': True})
    assert not s.graph.active and not s.mode.active


def test_exact_new_root_discards_old_baseline_and_rebinds_original_sha(sql_facts):
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c, before_choose=configured) as s:
        frontier = s.graph._accounted_frontier
        s.graph.check(f.store, c)
        before, old_hash = frontier.compare_baseline, frontier.expected
        s.graph.add('settlement-parsed', dict(shared=s.graph.inputs['trial-generated-model-facet']))
        assert frontier.compare_baseline is None and frontier.expected != old_hash
        s.graph.check(f.store, c)
        assert frontier.compare_baseline is not before
        assert frontier.compare_baseline[2] == frontier.expected
        assert frontier.key() == frontier.expected


def test_capacity_selection_is_independent_of_issued_owned_ledger(sql_facts):
    f = sql_facts
    def setup(graph, source, generated, candidate):
        candidate.config = replace(candidate.config, frontier_compare=BOUNDS._replace(units=1))
    with f.store.tx() as c, native_segment(f, c, before_choose=setup) as s:
        before = s.mode.scope._allocation.resident, s.mode.scope._allocation.work
        s.graph.check(f.store, c)
        frontier = s.graph._accounted_frontier
        assert frontier.compare_declined and frontier.compare_baseline is None
        assert s.mode.active and s.graph.active
        assert (s.mode.scope._allocation.resident, s.mode.scope._allocation.work) == before
        assert frontier.key() == frontier.expected


def test_dynamic_write_revocation_still_invalidates(sql_facts):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c, before_choose=configured) as s:
        s.graph.check(f.store, c)
        c.execute(update(grants).where(grants.c.principal_id == f.user).values(expires_at=0))
        s.graph.check(f.store, c)
    assert not s.graph.active and not s.mode.active


@pytest.mark.parametrize('change', ['caps', 'key_identity'])
def test_actual_pb_fresh_projection_retains_independent_source_aliases(sql_facts, change):
    f = sql_facts
    raw = object.__getattribute__(f.contract, '__dict__')
    key = next(key for key in raw if key == 'principal_id')
    def setup(graph, source, generated, candidate):
        graph.add('independent-pb-alias', dict(key=key,
            caps=object.__getattribute__(f.contract.caps, '__dict__')))
        configured(graph, source, generated, candidate)
    try:
        with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c, before_choose=setup) as s:
            s.graph.check(f.store, c)
            if change == 'caps':
                f.contract.caps.__dict__['run_seconds'] -= 1
            else:
                replacement = ('fresh-' + key)[6:]
                assert replacement == key and replacement is not key
                object.__setattr__(f.contract, '__dict__',
                    {replacement if k is key else k: v for k, v in raw.items()})
            s.graph.check(f.store, c)
        assert not s.graph.active and not s.mode.active
    finally:
        object.__setattr__(f.contract, '__dict__', raw)


def test_unknown_adapter_selects_old_verifier_before_comparison(sql_facts, monkeypatch):
    from sim2act import _cold_frontier_compare as comparison
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c, before_choose=configured) as s:
        s.graph.check(f.store, c)
        frontier = s.graph._accounted_frontier
        selected, legacy = frontier.compare_counts['selected'], frontier.compare_counts['legacy']
        original = runtime._cold_graph_row_storage
        def changed(value):
            return original(value)
        def forbidden(*args):
            pytest.fail('unknown adapter entered optional verifier')
        monkeypatch.setattr(runtime, '_cold_graph_row_storage', changed)
        monkeypatch.setattr(comparison, '_same', forbidden)
        s.graph.check(f.store, c)
        assert frontier.compare_counts['selected'] == selected
        assert frontier.compare_counts['legacy'] == legacy + 1


def test_sha_cannot_endorse_snapshot_changed_then_restored_during_build(sql_facts, monkeypatch):
    f = sql_facts
    with pytest.raises(DomainError, match='constructing comparison baseline'), f.store.tx() as c:
        with native_segment(f, c, before_choose=configured) as s:
            frontier = s.graph._accounted_frontier
            # Retain the exact expected SHA, but force a new optional baseline.
            frontier.compare_baseline = None
            original_snapshot = frontier._comparison_snapshot
            original_codec = runtime._cold_graph_bytes
            calls = []
            def snapshot(values):
                calls.append('select')
                if calls == ['select']:
                    s.graph.inputs['synthetic-native-candidate'] = False
                    frontier.projected['synthetic-native-candidate'] = False
                return original_snapshot(values)
            def restored(values):
                calls.append('sha')
                # projected aliases this complete original input value table;
                # restore both before the original SHA reads it.
                s.graph.inputs['synthetic-native-candidate'] = True
                frontier.projected['synthetic-native-candidate'] = True
                return original_codec(values)
            monkeypatch.setattr(frontier, '_comparison_snapshot', snapshot)
            monkeypatch.setattr(runtime, '_cold_graph_bytes', restored)
            s.graph.check(f.store, c)
    assert not s.graph.active and not s.mode.active
    assert frontier.compare_baseline is None
