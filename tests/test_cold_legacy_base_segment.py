"""Legacy typed collector pure closure, real SQLite/CGR but no Worker/model."""

import sys
from contextlib import contextmanager

import pytest
from accounted_sqlite_fixture import seed_cold, segment
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import _cold_base_segment as code
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as rt
from sim2act._cold_producer_segment import _ProducerSegment
from sim2act.errors import DomainError


@contextmanager
def legacy(f, enabled):
    if not hasattr(f, 'cold_job'):
        seed_cold(f)
    with f.store.tx() as c, segment(f, c, phase='post') as s:
        t = object.__new__(rt._ColdTrialGraph)
        t.__dict__.update(worker=f.worker, c=c, guard=s.graph, accounted_prewrite=None,
            _owned_models=None, platform=None, trial=None, audit_seed=None,
            journal=(s.state, s.cursor, s.graph.inputs['cold-trial:journal']['revision']),
            source_accounted=s.source, generate_accounted=s.generated,
            cold_stage_facts=s.cold_stage, source_stage_facts=s.stage,
            sealed_fields=None, live_source=None, context_record=None, phase='COMPLETE')
        if enabled:
            _ProducerSegment(s.graph, legacy_base=True)
        yield t, s


def test_legacy_post_two_to_one_codec_same_complete_collector_and_no_escape(sql_facts, monkeypatch):
    # One issued scope, alternate selector only; every _base remains fresh.
    with legacy(sql_facts, True) as (t, s):
        assert code.eligible(t)
        encode = rt._cold_graph_bytes
        calls, traces, observations = [], [], []
        targets = {fn.__code__: fn.__name__ for fn in
                   (gate._graph_trial_accounted_models_from_raw,
                    gate._graph_trial_stage_raw_from_raw,
                    gate._graph_trial_stage_models_from_raw,
                    gate._trial_typed_hold, gate._trial_typed_values,
                    rt._ColdGraphRead._check_dynamic)}

        def encoded(value):
            calls.append(1)
            return encode(value)

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code in targets:
                traces.append(targets[frame.f_code])

        monkeypatch.setattr(rt, '_cold_graph_bytes', encoded)
        for enabled in (False, True):
            s.graph._producer_segment_candidate.legacy_base = enabled
            calls.clear()
            traces.clear()
            before_keys = set(vars(t))
            sys.setprofile(profile)
            try:
                t._base()
            finally:
                sys.setprofile(None)
            assert set(vars(t)) == before_keys
            observations.append((len(calls), tuple(traces)))
        assert [o[0] for o in observations] == [2, 1]
        assert observations[0][1] == observations[1][1]


@pytest.mark.parametrize('damage', ['hidden', 'alias', 'epoch', 'scope'])
def test_legacy_inside_damage_cannot_escape(sql_facts, damage):
    f = sql_facts
    fired = []
    with pytest.raises(DomainError):
        with legacy(f, True) as (t, s):
            shared = ['original']
            data = ('visible', shared)
            row = RowMapping(SimpleResultMetaData(['visible']), None, {'visible': 0}, data)
            s.graph.add('extra-hidden', row)
            s.graph.add('extra-alias', shared)
            assert code.eligible(t)

            def profile(frame, event, arg):
                if frame.f_code is gate._trial_typed_values.__code__ and event == 'return' and not fired:
                    fired.append(True)
                    if damage == 'hidden':
                        shared.append('changed')
                    elif damage == 'alias':
                        s.graph.inputs['extra-alias'] = ['original']
                    elif damage == 'epoch':
                        s.c.info['source_proof_write_epoch'] = s.graph.epoch + 1
                    else:
                        s.graph.scope.clear()
            sys.setprofile(profile)
            try:
                t._base()
            finally:
                sys.setprofile(None)
    assert fired == [True] and not s.graph.active and t.phase == 'INVALID'


def test_legacy_collector_error_still_prefers_damaged_complete_input(sql_facts):
    errors = []
    for enabled in (False, True):
        with pytest.raises(DomainError):
            with legacy(sql_facts, enabled) as (t, s):
                # Break both a typed identity join and an independent full pin.
                t.source_accounted = ('wrong family',)
                s.graph.inputs['synthetic-offline-integration'] = False
                try:
                    t._base()
                except DomainError as error:
                    errors.append((error.code, error.message))
                    raise
    assert errors[0] == errors[1]


def test_unknown_serializer_keeps_entry_full_before_callback(sql_facts, monkeypatch):
    from sim2act.production_trial_policy import Ledger

    calls = []
    with pytest.raises(DomainError):
        with legacy(sql_facts, True) as (t, s):
            original = Ledger.model_dump

            def callback(self, **kwargs):
                calls.append(1)
                return original(self, **kwargs)

            monkeypatch.setattr(Ledger, 'model_dump', callback)
            s.graph.inputs['synthetic-offline-integration'] = False
            t._base()
    assert calls == []


def test_changed_legacy_helper_selects_original_entry(sql_facts, monkeypatch):
    with legacy(sql_facts, True) as (t, _):
        assert code.eligible(t)
        monkeypatch.setattr(gate, '_graph_trial_stage_raw_from_raw', lambda *args: None)
        assert not code.eligible(t)


def test_foreign_receiver_is_ineligible_without_callback():
    class Foreign:
        def __getattr__(self, name):
            pytest.fail('foreign eligibility descriptor must not execute')
    assert code.eligible(Foreign()) is False


def test_fixed_legacy_stage_parent_keeps_dynamic_and_joins_but_not_duplicate_codec(sql_facts, monkeypatch):
    with legacy(sql_facts, True) as (_, s):
        encode = rt._cold_graph_bytes
        calls, traces, observations = [], [], []
        targets = {fn.__code__: fn.__name__ for fn in
                   (gate._graph_trial_stage_raw_from_raw, gate._trial_pure_mapping,
                    gate._trial_pure_data, rt._ColdGraphRead._check_dynamic)}

        def encoded(value):
            calls.append(1)
            return encode(value)

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code in targets:
                traces.append(targets[frame.f_code])

        monkeypatch.setattr(rt, '_cold_graph_bytes', encoded)
        for enabled in (False, True):
            s.graph._producer_segment_candidate.legacy_base = enabled
            calls.clear()
            traces.clear()
            sys.setprofile(profile)
            try:
                gate._graph_trial_stage_parent_pin(s.graph, sql_facts.store, s.c, s.stage)
            finally:
                sys.setprofile(None)
            observations.append((len(calls), tuple(traces)))
        assert [r[0] for r in observations] == [2, 1]
        assert observations[0][1] == observations[1][1]
        calls.clear()
        gate._graph_trial_stage_raw(s.graph, s.stage)
        assert len(calls) == 1  # Independent entry still pins itself.


def test_unknown_stage_wrapper_keeps_original_callback(sql_facts, monkeypatch):
    with legacy(sql_facts, True) as (_, s):
        original = gate._graph_trial_stage_raw
        calls = []

        def callback(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)

        monkeypatch.setattr(gate, '_graph_trial_stage_raw', callback)
        gate._graph_trial_stage_parent_pin(s.graph, sql_facts.store, s.c, s.stage)
        assert calls == [1]


def test_second_stage_dynamic_failure_invalidates_in_both_modes(sql_facts):
    messages = []
    for enabled in (False, True):
        with pytest.raises(DomainError):
            with legacy(sql_facts, enabled) as (_, s):
                calls = []

                def profile(frame, event, arg, calls=calls, s=s):
                    if event == 'call' and frame.f_code is rt._ColdGraphRead._check_dynamic.__code__:
                        calls.append(1)
                        if len(calls) == 2:
                            s.c.info['source_proof_write_epoch'] = s.graph.epoch + 1

                sys.setprofile(profile)
                try:
                    gate._graph_trial_stage_parent_pin(s.graph, sql_facts.store, s.c, s.stage)
                except DomainError as error:
                    messages.append((error.code, error.message))
                    assert not s.graph.active
                    raise
                finally:
                    sys.setprofile(None)
    assert messages[0] == messages[1]
