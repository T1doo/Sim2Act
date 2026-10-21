"""Native candidate edges/consumers only: never _prepare or trial.commit.

Fresh isolated SQL synthetic facts; no Worker, model or transport constructor.
The harness mirrors original mid-edge validations, not an acceptance run.
"""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from accounted_sqlite_fixture import seed_cold
from sqlalchemy import select, update
from test_cold_accounted_cohort import BOUNDS, LIMITS
from test_cold_accounted_sqlite import (
    forbid_execution as forbid_execution,
)
from test_cold_accounted_sqlite import resolve
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import _cold_accounted_native as native
from sim2act import cold_accounted as owned
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act import pa_trial_dispatch as dispatch
from sim2act import pb_natural_specs as pb
from sim2act._cold_accounted_budget import _Ledger
from sim2act.db import attempts, grants, runs
from sim2act.errors import DomainError
from sim2act.spec_production import VERSION

# Deliberately conservative logical reservations; not physical allocation or a
# production configuration. A packet-only allowance must choose original mode.
NATIVE_LIMITS = LIMITS._replace(resident=10**30, peak=10**32, work=10**40)


@contextmanager
def native_segment(f, c, *, limits=NATIVE_LIMITS, middle=None, before_choose=None, receipt_setup=None):
    inputs = {'synthetic-native-candidate': True}
    roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
    with pb._source_reads(f.store, c), runtime._cold_graph_read(
        f.worker, c, inputs, roles, 'pre'
    ) as graph, native._native_candidate(graph, native._NativeConfig(BOUNDS, limits)) as candidate:
        state, cursor, revision = dispatch._graph_journal_state(graph, f.store, c, f.binding)
        graph.add('trial-generated-model-facet', dict(frozen=f.frozen.model_dump()))
        graph.add('cold-trial:bound', dict(binding=getattr(f, 'cold_bound', f.bound), source_binding=f.bound))
        # Producer calls remain on their original sides of the recipe/version
        # validations. choose() consumes these exact complete batches only.
        source = dispatch._graph_stage_accounted(
            graph, f.store, c, f.binding, state, cursor, f.source_id, 'source')
        candidate.stage('source', source)
        if middle is not None:
            middle(graph, source)
        versions = c.execute(select(attempts.c.parameters['pa_trial_binding']['version'].as_string())
                             .where(attempts.c.run_id == f.gen_id)).scalars().all()
        graph.check(f.store, c)
        gate.require(versions == [VERSION] * 3)
        generated = dispatch._graph_stage_accounted(
            graph, f.store, c, f.binding, state, cursor, f.gen_id, 'generate')
        candidate.stage('generate', generated)
        if before_choose is not None:
            before_choose(graph, source, generated, candidate)
        platform = receipt_setup(graph) if receipt_setup is not None else None
        selected = candidate.choose(state, receipt_platform=platform)
        source, generated, mode = selected.source, selected.generated, selected.mode
        full = dict(binding=getattr(f, 'cold_bound', {}), cold_job=getattr(f, 'cold_job', {}),
                    source_binding=f.bound, source=source if mode else dict(run=source[0]),
                    generated=generated if mode else None,
                    generation=dict(raw=f.raw, metadata=f.metadata,
                                    run=generated.run if mode else generated[0]),
                    source_proof=f.proof,
                    extraction=dict(draft=f.extraction[0], request=f.extraction[1].model_dump(),
                                    target=f.extraction[2], goal=f.extraction[3]))
        if mode:
            mode.seal(full)
            mode.pin_legacy_complete(mode.complete)
        else:
            graph.add('cold-trial:complete', full)
        stage = (source.run if mode else source[0], f.bound, f.raw, f.metadata,
                 generated.run if mode else generated[0], f.frozen, generated, None, None)
        cold = ((f.cold_job, f.cold_bound, f.raw, f.metadata,
                 generated.run if mode else generated[0], f.frozen, generated, source, f.extraction)
                if hasattr(f, 'cold_job') else None)
        s = SimpleNamespace(f=f, c=c, graph=graph, candidate=candidate, cohort=selected,
                            state=state, cursor=cursor, revision=revision, source=source,
                            generated=generated, mode=mode, stage=stage, cold_stage=cold)
        yield s
        if mode:
            mode.assert_current()
        else:
            graph.check(f.store, c)


def test_original_order_once_and_packet_only_budget_is_joint_legacy(sql_facts, monkeypatch):
    f, events = sql_facts, []
    original = dispatch._graph_stage_accounted
    def producer(*args, **kwargs):
        events.append(args[7])
        return original(*args, **kwargs)
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', producer)
    def middle(graph, source):
        events.append('recipe')
        assert graph._accounted_frontier is None
    with f.store.tx() as c, native_segment(f, c, limits=LIMITS, middle=middle) as s:
        assert events == ['source', 'recipe', 'generate']
        assert s.cohort.route == 'LEGACY' and s.mode is None
        assert s.graph._accounted_frontier is None and not s.candidate.mode.scope._issued
        assert s.cohort.source is s.source and s.cohort.generated is s.generated
        assert resolve(s).public_receipt['source_run_id'] == f.source_id


def test_middle_error_precedes_generate_and_never_issues(sql_facts, monkeypatch):
    f, events = sql_facts, []
    original = dispatch._graph_stage_accounted
    def producer(*args, **kwargs):
        events.append(args[7])
        return original(*args, **kwargs)
    monkeypatch.setattr(dispatch, '_graph_stage_accounted', producer)
    def middle(graph, source):
        raise DomainError('VERSION_CONFLICT', 'original recipe error')
    with pytest.raises(DomainError, match='original recipe error'), f.store.tx() as c:
        with native_segment(f, c, middle=middle):
            pytest.fail('middle error cannot select')
    assert events == ['source']


def test_owned_frontier_real_consumers_and_two_coordinator_checks(sql_facts, monkeypatch):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        assert s.cohort.route == 'OWNED'
        before = s.cohort.ledger.resident, s.cohort.ledger.work
        # No issuance-afterwards capacity check, new packet, encoder, oracle or
        # accounting spend/view may hide underneath a native continuation.
        def forbidden(*args, **kwargs):
            pytest.fail('post-issuance allocation/oracle replay')
        monkeypatch.setattr(_Ledger, 'snapshot', forbidden)
        monkeypatch.setattr(_Ledger, 'spend', forbidden)
        monkeypatch.setattr(_Ledger, 'view', forbidden)
        monkeypatch.setattr(owned._LegacyOracle, 'assert_current', forbidden)
        monkeypatch.setattr(owned._LegacyOracle, 'assert_run', forbidden)
        monkeypatch.setattr(owned._LegacyOracle, 'assert_stage', forbidden)
        monkeypatch.setattr(owned._LegacyOracle, 'assert_archive', forbidden)
        for _ in range(2):
            s.mode.assert_current()
            _, phase, actual, _ = gate._graph_run_context(
                s.graph, f.store, c, f.user, f.contract, f.binding.approval_key,
                'cold', f.cold_job['id'], 1, 1, s.cold_stage, _owned=s.mode)
            assert actual['id'] == f.cold_job['id'] and phase == f.cold_phase.authority
            resolved = resolve(s, _owned=s.mode)
            dispatch._graph_pb_archive_chain(s.graph, f.store, c, f.binding,
                                              s.state, resolved, s.source, _owned=s.mode)
        assert before == (s.cohort.ledger.resident, s.cohort.ledger.work)
        assert s.source.run is s.source.run and s.source.chains is s.source.chains
        assert resolved.request_bodies == tuple(r.wire for r in s.source.ns_reads)
        assert resolved.response_bodies == tuple(r.payload for r in s.source.ns_reads)
        # Actual _base/check entry, without calling _prepare/commit or inventing
        # completed platform/trial facts.
        graph = object.__new__(runtime._ColdTrialGraph)
        graph.__dict__.update(worker=f.worker, c=c, guard=s.graph,
            accounted_prewrite=s.mode, platform=None, trial=None, audit_seed=None,
            journal=(s.state, s.cursor, s.revision), source_accounted=s.source,
            generate_accounted=s.generated, cold_stage_facts=s.cold_stage,
            source_stage_facts=s.stage, sealed_fields=s.mode.complete, source_proof=f.proof,
            original=f.contract, live_source=None, context_record=None, authority_record=None,
            authority_fields=None, phase='COMPLETE')
        graph.check()
        graph.check()
        record = s.source.run
        arena = s.candidate.arena
    assert not s.mode.active and not arena.nodes
    with pytest.raises(DomainError):
        _ = record.id


def test_codec_frontier_removes_only_owned_nested_values(sql_facts, monkeypatch):
    f = sql_facts
    def aliases(graph, source, generated, candidate):
        graph.add('independent-full-run', dict(run=generated[0]))
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c, before_choose=aliases) as s:
        seen, original = [], runtime._cold_graph_bytes
        def observe(value):
            seen.append(value)
            return original(value)
        monkeypatch.setattr(runtime, '_cold_graph_bytes', observe)
        s.graph.check(f.store, c)
        projected = seen[-1]['inputs']
        assert type(projected['cold-trial:accounted-source']) is tuple
        assert type(projected['cold-trial:complete']['source']) is tuple
        assert type(projected['cold-trial:complete']['generated']) is tuple
        assert type(projected['cold-trial:complete']['generation']['run']) is tuple
        assert projected['independent-full-run'] is s.graph.inputs['independent-full-run']
        # Detached original accounted raw no longer drives consumers. Its
        # exclusive mutation is ignored, while an independent alias remains live.
        old = s.graph.inputs['cold-trial:accounted-source']['actual'][0]['parameters']
        old['unused-native-proof'] = ['mutated']
        s.mode.assert_current()
        assert 'unused-native-proof' not in dict(s.source.actual[0].parameters._node.items())
        s.graph.inputs['independent-full-run']['run']['context']['bad'] = True
        s.mode.assert_current()


@pytest.mark.parametrize('damage', ['settings', 'model', 'max_tokens', 'stop', 'write', 'rollback', 'commit', 'frontier', 'rebind'])
def test_native_dynamic_and_frontier_invalidation(sql_facts, damage):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        record = s.generated.actual[2]
        if damage == 'settings':
            object.__setattr__(f.settings, 'run_seconds', f.settings.run_seconds - 1)
        elif damage == 'model':
            object.__setattr__(f.contract, 'model', 'changed')
        elif damage == 'max_tokens':
            object.__setattr__(f.contract.caps, 'max_output_tokens', 1)
        elif damage == 'stop':
            f.worker.stop.set()
        elif damage == 'write':
            c.execute(update(grants).values(revoked=True))
        elif damage in ('rollback', 'commit'):
            getattr(c, damage)()
        elif damage == 'rebind':
            s.graph.inputs['cold-trial:complete']['source'] = dict(s.graph.inputs['cold-trial:complete']['source'])
        else:
            s.graph.inputs['cold-trial:complete']['source_proof']['extra'] = 'changed'
        s.mode.assert_current()
        _ = record.id
    assert not s.mode.active and not s.mode.scope._issued


def test_native_cannot_export_or_cross_stage(sql_facts):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        s.graph.input_bytes()
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        s.graph.phase = 'post'
        s.mode.assert_current()


@pytest.mark.parametrize('limits', [LIMITS, NATIVE_LIMITS])
def test_missing_original_entitlement_still_blocks_pb_accounting(sql_facts, limits):
    f = sql_facts
    with pytest.raises(DomainError, match='No reviewed production account evidence'), f.store.tx() as c:
        with native_segment(f, c, limits=limits) as s:
            generation = s.generated.run if s.mode else s.generated[0]
            dispatch._graph_pb_accounting(s.graph, f.store, c, f.binding,
                                          generation, s.state, _owned=s.mode)


def test_native_cache_and_arena_keep_original_source_and_reference_gates(sql_facts):
    f, calls = sql_facts, []
    class Foreign:
        def __index__(self):
            calls.append('index')
            raise AssertionError('foreign index')
        def __hash__(self):
            calls.append('hash')
            raise AssertionError('foreign hash')
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError('foreign attr')
    with f.store.tx() as c, native_segment(f, c) as s:
        aid = s.source.actual[0].id
        with pytest.raises(DomainError):
            owned._source_exchange(s.generated, aid)
        with pytest.raises(DomainError):
            owned._source_exchange(s.source, Foreign())
        packet = s.source._root().packet
        for ref in (-1, True, len(packet.nodes), Foreign()):
            with pytest.raises(DomainError):
                s.candidate.arena.node(packet, ref)
        fake = owned._Family(Foreign(), owned._Handle(), 'source')
        for name in ('run', 'actual', 'chains', 'ns_reads'):
            with pytest.raises(DomainError):
                getattr(fake, name)
        assert calls == []


def test_native_archive_full_foreign_cycle_and_scalar_domain(sql_facts):
    from dataclasses import replace
    f, calls = sql_facts, []
    class Foreign:
        def __getitem__(self, key):
            calls.append('index')
            raise AssertionError('foreign index')
        def __eq__(self, other):
            calls.append('eq')
            raise AssertionError('foreign equality')
    with f.store.tx() as c, native_segment(f, c) as s:
        resolved = resolve(s, _owned=s.mode)
        owned._archive_chain(s.source, s.state, resolved)
        for altered in (replace(resolved, request_bodies=Foreign()),
                        replace(resolved, request_bodies=(Foreign(), resolved.request_bodies[1])),
                        replace(resolved, public_receipt=dict(resolved.public_receipt, unused=Foreign())),
                        replace(resolved, public_receipt=dict(resolved.public_receipt, verification=Foreign()))):
            with pytest.raises(DomainError):
                owned._archive_chain(s.source, s.state, altered)
        cyc = []
        cyc.append(cyc)
        for extra in (cyc, float('inf')):
            altered = replace(resolved, public_receipt=dict(resolved.public_receipt, unused=extra))
            with pytest.raises(DomainError):
                owned._archive_chain(s.source, s.state, altered)
        assert calls == []


def test_native_foreign_frontier_cannot_exempt_current_graph(sql_facts):
    f, calls = sql_facts, []
    class Foreign:
        def check(self):
            calls.append('check')
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        s.graph._accounted_frontier = Foreign()
        s.graph.check(f.store, c)
    assert calls == []


def test_copy_to_issuance_keeps_original_typed_mutation_guard(sql_facts, monkeypatch):
    f, captured = sql_facts, []
    original = owned._capture_bounded
    def mutate_after_copy(facts, role, context, ledger):
        result = original(facts, role, context, ledger)
        if role == 'source':
            captured.append(facts)
            object.__setattr__(facts[2][0][0], 'reserved_at', facts[2][0][0].reserved_at + 1)
        return result
    monkeypatch.setattr(owned, '_capture_bounded', mutate_after_copy)
    with pytest.raises(DomainError), f.store.tx() as c:
        with native_segment(f, c):
            pytest.fail('mutated original typed proof cannot issue')
    assert len(captured) == 1


def test_cross_graph_frontier_swap_cannot_skip_other_mutable_inputs(sql_facts):
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c) as s:
        roles = dict.fromkeys(('source', 'generate', 'platform', 'trial', 'per_use'))
        with pytest.raises(DomainError), runtime._cold_graph_read(
            f.worker, c, {'unowned-other-graph': {}}, roles, 'pre'
        ) as other:
            other._accounted_frontier = s.graph._accounted_frontier
            other.inputs['unowned-other-graph']['modified'] = True
            other.check(f.store, c)
        s.mode.assert_current()


@pytest.mark.parametrize('damage', ['version', 'fence', 'lease'])
def test_native_original_run_context_rejects_separate_current_scalar_damage(sql_facts, damage):
    import time
    f = sql_facts
    seed_cold(f)
    # Deliberately incorrect synthetic current row before read scope starts;
    # this reaches original context predicates, not merely a write-epoch guard.
    with f.store.tx() as c:
        field = 'lease_until' if damage == 'lease' else damage
        value = time.time() - 1 if damage == 'lease' else 2
        c.execute(update(runs).where(runs.c.id == f.cold_job['id']).values(**{field: value}))
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        gate._graph_run_context(s.graph, f.store, c, f.user, f.contract,
            f.binding.approval_key, 'cold', f.cold_job['id'], 1, 1,
            s.cold_stage, _owned=s.mode)


def test_structural_classes_match_complete_domain_equality():
    from sqlalchemy.sql.elements import quoted_name

    from sim2act._cold_accounted_values import _equal, _freeze
    shared = {'all': [1, True, -0.0, b'bytes', quoted_name('q', False)]}
    values = [shared, {'all': [1, True, 0.0, b'bytes', quoted_name('q', True)]},
              {'all': [True, True, 0.0, b'bytes', 'q']},
              [shared, shared], [dict(shared), dict(shared)],
              {'b': 2, quoted_name('a', True): 1}, {'a': 1, 'b': 2},
              ['a'], ('a',), None, 1, True, 1.0, quoted_name('q', True), 'q']
    packets = {str(i): _freeze(v, BOUNDS) for i, v in enumerate(values)}
    ledger = _Ledger(BOUNDS, NATIVE_LIMITS)
    arena = native._Arena(ledger, packets)
    arena.classify(packets)
    for a in packets.values():
        for b in packets.values():
            left, right = arena.node(a, a.root), arena.node(b, b.root)
            assert arena.equal(left, right) == _equal(left, right)
    other_ledger = _Ledger(BOUNDS, NATIVE_LIMITS)
    other = native._Arena(other_ledger, packets)
    first = next(iter(packets.values()))
    with pytest.raises(DomainError):
        arena.equal(arena.node(first, first.root), other.node(first, first.root))
    ledger.close()
    other_ledger.close()


def test_issued_arena_tables_are_readonly_and_nodes_shape_gate_precedes_callbacks(sql_facts):
    from sim2act._cold_accounted_values import _Packet
    f, calls = sql_facts, []
    class Foreign:
        def __len__(self):
            calls.append('len')
            raise AssertionError('foreign nodes')
    with f.store.tx() as c, native_segment(f, c) as s:
        arena, node = s.candidate.arena, s.source._root()
        with pytest.raises(TypeError):
            arena.scalars[id(node.packet), node.ref] = 'replace'
        with pytest.raises(AttributeError):
            arena.scalars = {}
        with pytest.raises(AttributeError):
            arena.usage.add(('source', 'fake'))
        with pytest.raises(DomainError):
            arena.node(_Packet(0, Foreign(), b'', '', 0), 0)
        assert calls == []


def test_sizing_rows_keep_depth_and_completed_shared_path_budget():
    from sqlalchemy.engine import RowMapping
    from sqlalchemy.engine.result import SimpleResultMetaData
    row = RowMapping(SimpleResultMetaData(['a']), None, {'a': 0},
                     ([['depth']],))
    ledger = _Ledger(BOUNDS._replace(depth=21), NATIVE_LIMITS)
    ticket = ledger.reserve()
    p = native._SizingProjection(ledger, ticket)
    p.copy(row)
    with pytest.raises(DomainError):
        p.copy([[[row]]])  # Shared row's entire height, not height=1.
    ticket.close()
    ledger.close()
