"""Explicit pre-only joint handoff: real producers/consumers, synthetic SQLite."""
import copy

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from test_cold_accounted_cohort import BOUNDS
from test_cold_accounted_native import NATIVE_LIMITS, native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import resolve
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import cold_accounted as owned
from sim2act import natural_live_admission as gate
from sim2act import pa_trial_dispatch as dispatch
from sim2act._cold_accounted_budget import _Capacity, _Ledger
from sim2act._cold_accounted_values import _node
from sim2act.errors import DomainError


def test_joint_real_producers_consumers_and_closed_scope(sql_facts, monkeypatch):
    f, events, results = sql_facts, [], []
    producer = dispatch._graph_stage_accounted
    def observed(*args, **kwargs):
        events.append(args[7])
        return producer(*args, **kwargs)
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', observed)
    for joint in (False, True):
        with f.store.tx() as c, native_segment(f, c, joint=joint,
                middle=lambda *args: events.append('recipe')) as s:
            assert s.cohort.route == 'OWNED'
            packets = {role: s.mode.scope._issued[family.handle][1]
                       for role, family in (('source', s.source), ('generate', s.generated))}
            assert (packets['source'].nodes is packets['generate'].nodes) is joint
            if joint:
                s.candidate.assert_joint(packets)
            resolved = resolve(s, _owned=s.mode)
            gate._graph_trial_stage_raw(s.graph, s.stage, _owned=s.mode)
            models = []
            gate._graph_trial_stage_models(s.graph, f.store, c, models, s.stage, _owned=s.mode)
            assert models
            dispatch._graph_pb_archive_chain(s.graph, f.store, c, f.binding,
                                             s.state, resolved, s.source, _owned=s.mode)
            results.append((resolved.public_receipt, resolved.request_bodies, resolved.response_bodies))
            old = s.graph.inputs['cold-trial:accounted-source']['actual'][0]['parameters']
            old['exclusive-after-handoff'] = True
            s.mode.assert_current()
            assert 'exclusive-after-handoff' not in dict(s.source.actual[0].parameters._node.items())
            record = s.source.run
            arena = s.candidate.arena
    assert events == ['source', 'recipe', 'generate'] * 2
    assert results[0] == results[1]
    assert not arena.nodes and not arena.reachable
    with pytest.raises(DomainError):
        _ = record.id


def test_joint_capture_common_raw_and_hidden_aliases(sql_facts):
    originals = {}
    def remember(graph, source, generated, candidate):
        originals.update(copy.deepcopy(dict(source=source, generate=generated)))
    with sql_facts.store.tx() as c, native_segment(sql_facts, c, before_choose=remember):
        # Component-only copies: the synthetic aliases below are never issued
        # as original producer facts. Real issuance is checked in the first test.
        shared = {'hidden': ['complete']}
        source, generated = originals['source'], originals['generate']
        source = originals['source'] = (dict(source[0]), *source[1:])
        generated = originals['generate'] = (dict(generated[0]), *generated[1:])
        source[0]['error'] = generated[0]['error'] = shared
        run = source[0]
        keys = list(run)
        data = tuple(run.values()) + (shared,)
        row = RowMapping(SimpleResultMetaData(keys), None,
                         {key: i for i, key in enumerate(keys)}, data)
        originals['source'] = (row, *source[1:])
        capture = source[2][0][1]
        source[2][0][3]['parameters']['joint_leaf'] = capture.raw_sha256
        ledger = _Ledger(BOUNDS, NATIVE_LIMITS)
        try:
            packets, joint = owned._capture_pair_bounded(originals, owned._Context('synthetic', 1024, 'offline'), ledger)
            a, b = (_node(packets[role]).get('value') for role in ('source', 'generate'))
            left, right = a.get('run').get('error'), b.get('run').get('error')
            assert left.packet.nodes is right.packet.nodes is joint.nodes
            assert left.ref == right.ref
            label, storage = _node(packets['source']).get('row_storage').sequence()[0].sequence()
            assert label.sequence()[0].scalar() == 'source'
            hidden = storage.sequence()[1].sequence()[-1]
            assert hidden.packet.nodes is joint.nodes and hidden.ref == left.ref
            chain = a.get('chains').sequence()[0].sequence()
            assert chain[1].get('raw_sha256').ref == chain[3].get('parameters').get('joint_leaf').ref
            shared['hidden'].append('external mutation')
            assert len(left.get('hidden').sequence()) == 1
        finally:
            ledger.close()
        assert not ledger.active and ledger.live == 0


def test_joint_typed_storage_alias_is_legacy_subdomain(sql_facts):
    originals = {}
    def remember(graph, source, generated, candidate):
        originals.update(copy.deepcopy(dict(source=source, generate=generated)))
    with sql_facts.store.tx() as c, native_segment(sql_facts, c, before_choose=remember):
        request = originals['source'][3][0][1]
        generated = originals['generate']
        originals['generate'] = (dict(generated[0]), *generated[1:])
        originals['generate'][0]['error'] = object.__getattribute__(request, '__dict__')
        ledger = _Ledger(BOUNDS, NATIVE_LIMITS)
        try:
            with pytest.raises(_Capacity, match='joint_model_storage_alias'):
                owned._capture_pair_bounded(originals, owned._Context('synthetic', 1024, 'offline'), ledger)
        finally:
            ledger.close()
        assert ledger.live == 0


def test_joint_root_swap_rejected_before_handles(sql_facts, monkeypatch):
    original = owned._capture_pair_bounded
    def swapped(*args, **kwargs):
        packets, joint = original(*args, **kwargs)
        return dict(source=packets['generate'], generate=packets['source']), joint
    monkeypatch.setattr(owned, '_capture_pair_bounded', swapped)
    with pytest.raises(DomainError, match='Joint accounted role/root changed'):
        with sql_facts.store.tx() as c, native_segment(sql_facts, c, joint=True):
            pytest.fail('swapped role roots cannot issue')


def test_joint_insufficient_budget_is_one_legacy_choice(sql_facts):
    from test_cold_accounted_cohort import LIMITS
    with sql_facts.store.tx() as c, native_segment(sql_facts, c, joint=True, limits=LIMITS) as s:
        assert s.cohort.route == 'LEGACY' and s.mode is None
        assert not s.candidate.mode.scope._issued
        assert s.candidate.joint_packet is None
        assert resolve(s).public_receipt['source_run_id'] == sql_facts.source_id


def test_legacy_header_error_precedes_any_budget_allocation():
    from sim2act._cold_accounted_budget import _Limits
    ledger = _Ledger(BOUNDS, _Limits(1, 1, 1, 1))
    try:
        with pytest.raises(DomainError) as error:
            owned._capture_bounded(None, 'source', owned._Context('synthetic', 1, 'offline'), ledger)
        assert not isinstance(error.value, _Capacity) and ledger.work == 0
    finally:
        ledger.close()


def test_joint_foreign_reference_never_hashes():
    from sim2act._cold_accounted_native import _Arena
    from sim2act._cold_accounted_values import _Packet
    calls = []
    class Foreign:
        def __hash__(self):
            calls.append('hash')
            raise AssertionError('foreign reference hash')
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign reference equality')
    packet = _Packet(Foreign(), (('none', None),), b'[]', 'synthetic', 0)
    ledger = _Ledger(BOUNDS, NATIVE_LIMITS)
    try:
        with pytest.raises(DomainError):
            _Arena(ledger, {'source': packet, 'generate': packet}, joint=True)
        assert calls == []
    finally:
        ledger.close()


def test_post_arena_capacity_failure_releases_before_legacy(sql_facts, monkeypatch):
    from sim2act._cold_accounted_native import _Arena
    seen = []
    def too_small(self, packets):
        seen.append(self)
        raise _Capacity('test_post_arena_before_issue')
    monkeypatch.setattr(_Arena, 'classify', too_small)
    with sql_facts.store.tx() as c, native_segment(sql_facts, c, joint=True) as s:
        assert s.cohort.route == 'LEGACY' and not s.candidate.mode.scope._issued
        assert len(seen) == 1 and not seen[0].nodes and not seen[0].reachable
        assert s.candidate.joint_packet is None and s.candidate.joint_views == ()
        assert s.cohort.ledger.live == 0
        assert resolve(s).public_receipt['source_run_id'] == sql_facts.source_id


def test_joint_mutation_before_issuance_rejects(sql_facts, monkeypatch):
    original = owned._capture_pair_bounded
    observed = []
    def mutate(completed, *args):
        result = original(completed, *args)
        slot = completed['source'][2][0][0]
        object.__setattr__(slot, 'reserved_at', slot.reserved_at + 1)
        observed.append(True)
        return result
    monkeypatch.setattr(owned, '_capture_pair_bounded', mutate)
    with pytest.raises(DomainError), sql_facts.store.tx() as c:
        with native_segment(sql_facts, c, joint=True):
            pytest.fail('drift before issue cannot become owned')
    assert observed == [True]


@pytest.mark.parametrize('damage', ['model', 'max_tokens', 'stop', 'write', 'rollback', 'views'])
def test_joint_dynamic_and_registered_view_failure_closes(sql_facts, damage):
    from sqlalchemy import update

    from sim2act.db import grants
    with pytest.raises(DomainError), sql_facts.store.tx() as c:
        with native_segment(sql_facts, c, joint=True) as s:
            record = s.generated.actual[2]
            if damage == 'model':
                object.__setattr__(sql_facts.contract, 'model', 'different')
            elif damage == 'max_tokens':
                object.__setattr__(sql_facts.contract.caps, 'max_output_tokens', 1)
            elif damage == 'stop':
                sql_facts.worker.stop.set()
            elif damage == 'write':
                c.execute(update(grants).values(revoked=True))
            elif damage == 'rollback':
                c.rollback()
            else:
                handle = s.generated.handle
                role, packet = s.mode.scope._issued[handle]
                wrong = s.candidate.joint_views[0]
                s.mode.scope._issued[handle] = (role, wrong)
            s.mode.assert_current()
            _ = record.id
    assert not s.mode.active and not s.mode.scope._issued


def test_default_capture_bytes_match_frozen_oracle_and_joint_capacity(sql_facts):
    import hashlib
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'docs/evidence/cold-joint-handoff-20261027/baseline-capture.py.txt').read_bytes()
    assert hashlib.sha256(source).hexdigest() == '669dcc569a570c69ebc08d66381ebdef12784352d8598b2cc488ec6139fa9508'
    namespace = dict(vars(owned))
    exec(compile(source, '<frozen-local-capture-oracle>', 'exec'), namespace)
    oracle = namespace['_capture_bounded']
    originals = {}
    def remember(graph, source, generated, candidate):
        originals.update(source=source, generate=generated)
    with sql_facts.store.tx() as c, native_segment(sql_facts, c, before_choose=remember):
        context = owned._Context(sql_facts.contract.model, sql_facts.contract.caps.max_output_tokens, 'controller')
        maximum = 0
        for role in ('source', 'generate'):
            a, b = _Ledger(BOUNDS, NATIVE_LIMITS), _Ledger(BOUNDS, NATIVE_LIMITS)
            try:
                old, _ = oracle(originals[role], role, context, a)
                new, _ = owned._capture_bounded(originals[role], role, context, b)
                assert old.encoded == new.encoded and old.digest == new.digest
                maximum = max(maximum, len(old.nodes))
            finally:
                a.close()
                b.close()
        small = _Ledger(BOUNDS._replace(nodes=maximum), NATIVE_LIMITS)
        try:
            with pytest.raises(_Capacity):
                owned._capture_pair_bounded(originals, context, small)
        finally:
            small.close()
        assert small.live == 0


def test_one_bounded_capture_and_arena_cost_comparison(sql_facts, tmp_path):
    import json
    import time

    from sim2act._cold_accounted_native import _Arena
    originals, observations = {}, []
    def remember(graph, source, generated, candidate):
        originals.update(source=source, generate=generated)
    with sql_facts.store.tx() as c, native_segment(sql_facts, c, before_choose=remember):
        context = owned._Context(sql_facts.contract.model, sql_facts.contract.caps.max_output_tokens, 'controller')
        for joint in (False, True, True, False):
            ledger = _Ledger(BOUNDS, NATIVE_LIMITS)
            started, wall = time.thread_time(), time.monotonic()
            if joint:
                packets, joint_packet = owned._capture_pair_bounded(originals, context, ledger)
            else:
                packets = {role: owned._capture_bounded(originals[role], role, context, ledger)[0]
                           for role in ('source', 'generate')}
                joint_packet = None
            arena = _Arena(ledger, packets, joint=joint)
            arena.classify(packets)
            elapsed, elapsed_wall = time.thread_time() - started, time.monotonic() - wall
            observations.append(dict(joint=joint, thread_cpu=elapsed, wall=elapsed_wall,
                unique_encoded_bytes=sum(len(v) for v in {id(p.encoded): p.encoded for p in packets.values()}.values()),
                materialized_nodes=sum(sum(n is not None for n in nodes) for nodes in arena.nodes.values()),
                logical_peak=ledger.peak, logical_work=ledger.work))
            arena.release()
            ledger.close()
            del packets, joint_packet, arena
            assert ledger.live == 0
    (tmp_path / 'capture-cost.json').write_text(json.dumps(dict(scope='capture+arena/classify only; not full issuer/consumer/G0',
        order='ABBA once, includes new qualification; no performance threshold assertion', observations=observations), indent=2))


def test_joint_real_coordinator_uses_prepaid_owned_consumers(sql_facts, monkeypatch):
    import test_cold_accounted_native as fixture

    original = fixture.native_segment
    def joint_segment(*args, **kwargs):
        kwargs['joint'] = True
        return original(*args, **kwargs)
    # Reuse the original real coordinator/Source/archive check without changing
    # any product callable or eligibility witness. It forbids all later ledger
    # spend/view/snapshot and legacy-oracle replay, and calls graph.check twice.
    monkeypatch.setattr(fixture, 'native_segment', joint_segment)
    fixture.test_owned_frontier_real_consumers_and_two_coordinator_checks(sql_facts, monkeypatch)


@pytest.mark.parametrize('damage', ['root_type', 'edge_count'])
def test_joint_view_metadata_rejected_before_issuance(sql_facts, monkeypatch, damage):
    original, calls = owned._capture_pair_bounded, []
    class Foreign:
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign root equality')
    def damaged(*args, **kwargs):
        packets, joint = original(*args, **kwargs)
        fields = dict(root=Foreign()) if damage == 'root_type' else dict(edges=0)
        packets['source'] = packets['source']._replace(**fields)
        return packets, joint
    monkeypatch.setattr(owned, '_capture_pair_bounded', damaged)
    with pytest.raises(DomainError), sql_facts.store.tx() as c:
        with native_segment(sql_facts, c, joint=True):
            pytest.fail('bad view metadata cannot issue')
    assert calls == []
