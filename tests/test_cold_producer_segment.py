"""Real SQLite/CGR, no Worker/transport: isolated fixed producer candidate."""

import sys
import warnings
from contextlib import contextmanager

import pytest
from sqlalchemy import update
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act._cold_producer_segment import _ProducerSegment
from sim2act.db import grants
from sim2act.errors import DomainError


@contextmanager
def case(f, enabled):
    with f.store.tx() as c, pb._source_reads(f.store, c):
        roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
        with runtime._cold_graph_read(f.worker, c, {'synthetic': ['original']}, roles, 'pre') as graph:
            mode = _ProducerSegment(graph) if enabled else None
            model = gate._approved(f.store, c, f.user, f.contract, f.binding.approval_key)
            yield c, graph, mode, model


def test_same_full_output_and_three_typed_passes_with_two_fresh_content_pins(sql_facts, monkeypatch):
    original = runtime._cold_graph_bytes
    observations = []
    codecs = []

    def encode(value):
        codecs.append(1)
        return original(value)

    monkeypatch.setattr(runtime, '_cold_graph_bytes', encode)
    for enabled in (False, True):
        with case(sql_facts, enabled) as (c, graph, mode, model):
            events = []

            def profile(frame, event, arg, events=events):
                if event == 'call' and frame.f_code is gate._trial_typed_values.__code__:
                    events.append('typed')

            codecs.clear()
            models = []
            sys.setprofile(profile)
            try:
                raw = gate._graph_trial_produced(graph, sql_facts.store, c, models,
                                                 gate.Approval, model)
            finally:
                sys.setprofile(None)
            observations.append((raw, len(codecs), events))
            assert models == [(gate.Approval, model, raw)]
            assert mode is None or (mode.qualified == 1 and mode.fallback == 0)
    assert observations[0][0] == observations[1][0]
    assert [o[1] for o in observations] == [3, 2]
    assert [o[2] for o in observations] == [['typed'] * 3] * 2


def test_warning_input_uses_original_once_and_keeps_same_raw(sql_facts):
    outputs = []
    for enabled in (False, True):
        with case(sql_facts, enabled) as (c, graph, mode, model):
            model.approved_at = 'synthetic-invalid-field'
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                raw = gate._graph_trial_produced(graph, sql_facts.store, c, [],
                                                 gate.Approval, model)
            outputs.append((raw, len(caught)))
            if enabled:
                assert mode.qualified == 0 and mode.fallback == 1
    assert outputs[0] == outputs[1] and outputs[0][1] == 1


def test_broken_entry_cannot_reach_warning_callback_or_return(sql_facts):
    for enabled in (False, True):
        with pytest.raises(DomainError), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with case(sql_facts, enabled) as (c, graph, _, model):
                model.approved_at = 'synthetic-invalid-field'
                graph.inputs['synthetic'].append('damaged')
                gate._graph_trial_produced(graph, sql_facts.store, c, [], gate.Approval, model)
        assert caught == []


@pytest.mark.parametrize('drift', ['content', 'stop_identity', 'epoch', 'scope', 'write'])
def test_mid_segment_drift_cannot_escape(sql_facts, drift):
    fired = []
    with pytest.raises(DomainError):
        with case(sql_facts, True) as (c, graph, _, model):
            def profile(frame, event, arg):
                if event == 'c_return' and getattr(arg, '__name__', '') == 'to_python' and not fired:
                    fired.append(True)
                    if drift == 'content':
                        graph.inputs['synthetic'].append('damaged')
                    elif drift == 'stop_identity':
                        sql_facts.worker.stop = object()
                    elif drift == 'epoch':
                        c.info['source_proof_write_epoch'] = graph.epoch + 1
                    elif drift == 'write':
                        c.execute(update(grants).values(revoked=True))
                    else:
                        graph.scope.clear()
            old_stop = sql_facts.worker.stop
            sys.setprofile(profile)
            try:
                gate._graph_trial_produced(graph, sql_facts.store, c, [], gate.Approval, model)
            finally:
                sys.setprofile(None)
                sql_facts.worker.stop = old_stop
    assert fired == [True] and not graph.active


def test_two_invocations_remain_fresh_and_scope_close_refuses(sql_facts):
    with pytest.raises(DomainError):
        with case(sql_facts, True) as (c, graph, mode, model):
            models = []
            gate._graph_trial_produced(graph, sql_facts.store, c, models, gate.Approval, model)
            models[0][2]['approved_at'] -= 1
            gate._graph_trial_produced(graph, sql_facts.store, c, models, gate.Approval, model)
    assert not graph.active
    with pytest.raises(DomainError):
        mode.current(graph, sql_facts.store, c)


def test_modified_serializer_keeps_original_callback_count(sql_facts, monkeypatch):
    results = []
    for enabled in (False, True):
        with case(sql_facts, enabled) as (c, graph, mode, model):
            calls = []
            original = gate.Approval.model_dump

            def callback(self, *args, calls=calls, original=original, **kwargs):
                calls.append(1)
                return original(self, *args, **kwargs)

            with monkeypatch.context() as patch:
                patch.setattr(gate.Approval, 'model_dump', callback)
                raw = gate._graph_trial_produced(graph, sql_facts.store, c, [],
                                                 gate.Approval, model)
            results.append((raw, len(calls)))
            assert mode is None or mode.fallback == 1
    assert results[0] == results[1] and results[0][1] == 2
