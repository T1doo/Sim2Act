"""Real issued SQLite _base only; no prepare, commit, Worker or Mock."""

import ast
import json
from pathlib import Path

import pytest
from accounted_sqlite_fixture import seed_cold
from sqlalchemy import update
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import cold_accounted as owned
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as rt
from sim2act.db import grants
from sim2act.errors import DomainError


def trial(s):
    value = object.__new__(rt._ColdTrialGraph)
    value.__dict__.update(worker=s.f.worker, c=s.c, guard=s.graph,
        accounted_prewrite=s.mode, platform=None, trial=None, audit_seed=None,
        journal=(s.state, s.cursor, s.revision), source_accounted=s.source,
        generate_accounted=s.generated, cold_stage_facts=s.cold_stage,
        source_stage_facts=s.stage, sealed_fields=s.mode.complete, source_proof=s.f.proof,
        original=s.f.contract, live_source=None, context_record=None, phase='COMPLETE')
    return value


def test_complete_base_two_full_pins_same_family_run_and_typed_sequence(sql_facts, monkeypatch):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        codec, family_calls, run_calls, holds, values, trace = [], [], [], [], [], []
        encode = rt._cold_graph_bytes
        family = owned._OwnedPrewriteMode._OwnedPrewriteMode__family_current
        run = owned._OwnedPrewriteMode._OwnedPrewriteMode__run_current
        hold, typed = gate._trial_typed_hold, gate._trial_typed_values

        def encoding(value):
            codec.append(1)
            return encode(value)

        def family_join(self, graph, value, role):
            family_calls.append((role, id(value)))
            trace.append(('family', role, id(value)))
            return family(self, graph, value, role)

        def run_join(self, value, record):
            run_calls.append((value.role, id(record)))
            trace.append(('run', value.role, id(record)))
            return run(self, value, record)

        def holding(models, kind, model, raw):
            holds.append((kind, id(model), id(raw)))
            trace.append(('hold', kind, id(model), id(raw)))
            return hold(models, kind, model, raw)

        def checking(models):
            values.append(tuple((kind, id(model), id(raw)) for kind, model, raw in models))
            trace.append(('typed-values', values[-1]))
            return typed(models)

        monkeypatch.setattr(rt, '_cold_graph_bytes', encoding)
        monkeypatch.setattr(owned._OwnedPrewriteMode, '_OwnedPrewriteMode__family_current', family_join)
        monkeypatch.setattr(owned._OwnedPrewriteMode, '_OwnedPrewriteMode__run_current', run_join)
        monkeypatch.setattr(gate, '_trial_typed_hold', holding)
        monkeypatch.setattr(gate, '_trial_typed_values', checking)
        observed = []
        for old in (True, False):
            codec.clear()
            family_calls.clear()
            run_calls.clear()
            holds.clear()
            values.clear()
            trace.clear()
            with monkeypatch.context() as m:
                if old:
                    # Original public assertions and independent stage_models
                    # reader reproduce the old thirteen internal full checks.
                    m.setattr(owned._OwnedPrewriteMode, '_base_parameters_current', lambda *args: None)
                    m.setattr(owned._OwnedPrewriteMode, '_base_family_current',
                              owned._OwnedPrewriteMode.assert_family)
                    m.setattr(owned._OwnedPrewriteMode, '_base_stage_current',
                              owned._OwnedPrewriteMode.assert_stage)
                    def old_models(mode, models, facts, inputs):
                        return gate._graph_trial_stage_models_from_raw(models, facts, inputs, _owned=mode)
                    m.setattr(owned._OwnedPrewriteMode, '_base_stage_models', old_models)
                t._base()
            observed.append((len(codec), tuple(family_calls), tuple(run_calls), tuple(holds), tuple(values), tuple(trace)))
        assert observed[0][0] == 15 and observed[1][0] == 2
        assert observed[0][1:] == observed[1][1:]
        assert len(observed[1][1]) == 11 and len(observed[1][2]) == 3
        assert len(observed[1][4]) == 1
        print(json.dumps(dict(old_codec=15, new_codec=2, family_predicates=11, run_predicates=3,
            typed_hold_calls=len(observed[1][3]), typed_value_passes=1,
            complete_predicate_and_typed_sequence_equal=True)))
        for call in (lambda: s.mode.assert_family(s.graph, s.source, 'source'),
                     lambda: s.mode.assert_run('source', s.source.run),
                     lambda: s.mode.assert_stage(s.cold_stage),
                     lambda: gate._graph_trial_stage_models_from_raw([], s.cold_stage,
                                                                      s.graph.inputs, _owned=s.mode)):
            codec.clear()
            call()
            assert codec


@pytest.mark.parametrize('damage', ['frontier', 'revoke', 'settings', 'stop', 'model', 'max_tokens', 'links'])
def test_second_complete_base_pin_rejects_change_after_typed_values(sql_facts, monkeypatch, damage):
    f = sql_facts
    seed_cold(f)
    original = gate._trial_typed_values
    fired = []
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        def changed(models):
            original(models)
            fired.append(True)
            if damage == 'frontier':
                s.graph.inputs['cold-trial:complete']['source_proof']['changed'] = True
            elif damage == 'revoke':
                c.execute(update(grants).values(revoked=True))
            elif damage == 'settings':
                object.__setattr__(f.settings, 'run_seconds', f.settings.run_seconds - 1)
            elif damage == 'model':
                object.__setattr__(f.contract, 'model', 'changed')
            elif damage == 'max_tokens':
                object.__setattr__(f.contract.caps, 'max_output_tokens', 1)
            elif damage == 'links':
                s.mode.scope._prewrite_mode = None
            else:
                f.worker.stop.set()
        monkeypatch.setattr(gate, '_trial_typed_values', changed)
        t._base()
    assert fired == [True] and not s.mode.active and t.phase == 'INVALID'


@pytest.mark.parametrize('damage', ['frontier', 'revoke', 'typed', 'links'])
def test_two_base_calls_have_no_cached_pass(sql_facts, damage):
    f = sql_facts
    seed_cold(f)
    second = None
    with pytest.raises(DomainError) as cleanup, f.store.tx() as c, native_segment(f, c) as s:
        t = trial(s)
        t._base()
        if damage == 'frontier':
            s.graph.inputs['cold-trial:complete']['source_proof']['between'] = True
        elif damage == 'revoke':
            c.execute(update(grants).values(revoked=True))
        elif damage == 'typed':
            object.__setattr__(f.frozen.limits, 'run_seconds', f.frozen.limits.run_seconds - 1)
        else:
            s.mode.scope._prewrite_mode = None
        with pytest.raises(DomainError) as refused:
            t._base()
        second = refused.value
        raise second
    assert second is not None and cleanup.value is second
    assert not s.mode.active and t.phase == 'INVALID'


def test_private_parameter_collector_only_base_caller_and_two_outer_checks():
    root = Path(__file__).resolve().parents[1] / 'src/sim2act'
    calls = []
    for path in root.glob('*.py'):
        tree = ast.parse(path.read_text())
        for function in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            if any(isinstance(n, ast.Call) and getattr(n.func, 'attr', None) == '_typed_parameters'
                   for n in ast.walk(function)):
                calls.append((path.name, function.name))
    assert calls == [('natural_spec_runtime.py', '_base')]
    tree = ast.parse((root/'natural_spec_runtime.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == '_ColdTrialGraph')
    base = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_base')
    try_body = base.body[0].body
    boundary = [n for n in try_body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)]
    assert [getattr(n.value.func, 'attr', None) for n in boundary] == [None, 'check', None, '_typed_parameters', 'check']


def test_unissued_default_and_unissued_mode_keep_original_collector(sql_facts, monkeypatch):
    f = sql_facts
    calls = []

    def forbidden(*args):
        pytest.fail('unissued collector cannot use native pure members')

    monkeypatch.setattr(owned._OwnedPrewriteMode, '_base_parameters_current', forbidden)

    def before(graph, source, generated, candidate):
        t = object.__new__(rt._ColdTrialGraph)
        t.__dict__.update(worker=f.worker, c=graph.connection, guard=graph,
            accounted_prewrite=None, journal=None, source_accounted=source,
            generate_accounted=generated, trial=None, cold_stage_facts=None,
            source_stage_facts=None, sealed_fields=None, live_source=None,
            context_record=None, phase='BUILDING')
        t._base()
        calls.append('default-real-producers')
        with owned._owned_prewrite(graph, candidate.config.bounds) as unissued:
            t.accounted_prewrite = unissued
            t.source_accounted = t.generate_accounted = None
            t._base()
            calls.append('unissued-mode')

    with f.store.tx() as c, native_segment(f, c, before_choose=before):
        assert calls == ['default-real-producers', 'unissued-mode']
