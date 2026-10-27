"""Fixed check composite: real SQLite/CGR; unit seed fields remain explicit stub."""
import sys

import pytest
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_legacy_base_segment import legacy

from sim2act import natural_spec_runtime as rt
from sim2act.errors import DomainError


def prepare(t, s, monkeypatch):
    # Exercise the ORIGINAL seed.check full pin and comparison. This controlled
    # fields hook is after the late full pin in both routes, never called early.
    seed = object.__new__(rt._ColdAuditSeed)
    object.__setattr__(seed, 'guard', s.graph)
    monkeypatch.setattr(rt._ColdAuditSeed, 'fields', lambda self: {'unit': 'seed'})
    s.graph.add('post-audit-seed', {'unit': 'seed'})
    t.audit_seed = seed
    t.authorities, t.authority_record, t.authority_fields = set(), None, None
    s.graph._producer_segment_candidate.post_check = True


def test_post_check_keeps_dynamic_predicates_and_late_full(sql_facts, monkeypatch):
    with legacy(sql_facts, True) as (t, s):
        prepare(t, s, monkeypatch)
        selector = s.graph._producer_segment_candidate
        original = rt._cold_graph_bytes
        encodes, traces = [], []
        def encode(value):
            encodes.append(1)
            return original(value)
        monkeypatch.setattr(rt, '_cold_graph_bytes', encode)
        watched = {rt._ColdGraphRead._check_dynamic.__code__: 'dynamic',
                   rt._ColdTrialGraph._check_links.__code__: 'links',
                   rt._ColdAuditSeed.check.__code__: 'seed'}
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code in watched:
                traces.append(watched[frame.f_code])
        results = []
        for enabled in (False, True):
            selector.post_check = enabled
            encodes.clear()
            traces.clear()
            sys.setprofile(profile)
            try:
                t.check()
            finally:
                sys.setprofile(None)
            results.append((len(encodes), tuple(traces)))
        assert [x[0] for x in results] == [2, 1]
        assert results[0][1] == results[1][1]
        assert selector.post_qualified == 1
        # Standalone entries retain their independent full pin.
        encodes.clear()
        t._base()
        assert len(encodes) == 1
        encodes.clear()
        t.audit_seed.check(t.worker.store, t.c, s.graph)
        assert len(encodes) == 1


@pytest.mark.parametrize('candidate', [False, True])
@pytest.mark.parametrize('damage', ['raw', 'epoch', 'scope'])
def test_post_check_late_damage_rejected(sql_facts, monkeypatch, candidate, damage):
    with pytest.raises(DomainError):
        with legacy(sql_facts, True) as (t, s):
            prepare(t, s, monkeypatch)
            s.graph._producer_segment_candidate.post_check = candidate
            fired = []
            def profile(frame, event, arg):
                if frame.f_code is rt._ColdTrialGraph._check_links.__code__ and event == 'return' and not fired:
                    fired.append(True)
                    if damage == 'raw':
                        s.graph.inputs['synthetic-offline-integration'] = False
                    elif damage == 'epoch':
                        s.c.info['source_proof_write_epoch'] = s.graph.epoch + 1
                    else:
                        s.graph.scope.clear()
            sys.setprofile(profile)
            try:
                t.check()
            finally:
                sys.setprofile(None)
    assert fired == [True] and not s.graph.active and t.phase == 'INVALID'


def test_unknown_middle_retains_original_route(sql_facts, monkeypatch):
    with legacy(sql_facts, True) as (t, s):
        prepare(t, s, monkeypatch)
        original = rt._ColdTrialGraph._check_links
        calls = []
        def replaced(self):
            calls.append(1)
            return original(self)
        monkeypatch.setattr(rt._ColdTrialGraph, '_check_links', replaced)
        t.check()
        assert calls == [1] and s.graph._producer_segment_candidate.post_qualified == 0


@pytest.mark.parametrize('target', ['_base', '_check_links', 'seed'])
def test_receiver_shadow_falls_back_once(sql_facts, monkeypatch, target):
    with legacy(sql_facts, True) as (t, s):
        prepare(t, s, monkeypatch)
        receiver, name = (t.audit_seed, 'check') if target == 'seed' else (t, target)
        original = getattr(receiver, name)
        calls = []
        def wrapped(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)
        object.__setattr__(receiver, name, wrapped)
        t.check()
        assert calls == [1] and s.graph._producer_segment_candidate.post_qualified == 0


def test_foreign_trial_no_descriptor(sql_facts):
    with legacy(sql_facts, True) as (t, s):
        selector = s.graph._producer_segment_candidate
        selector.post_check = True
        class Foreign:
            def __getattribute__(self, name):
                raise AssertionError('foreign descriptor must not execute')
        assert selector.check_trial(Foreign()) is False
