"""Original _cold_receipts integration, synthetic SQL facts; no Worker/G0.

Counter-proof is a synthetic precondition recorded by the original reader,
not a claim of complete Cold/accounted admission or model counter acceptance.
"""

import copy
from types import SimpleNamespace

import pytest
from accounted_sqlite_fixture import seed_cold
from sqlalchemy import insert, update
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import natural_spec_runtime as rt
from sim2act import pa_spec_apps as spec
from sim2act.app_jobs import _ColdBindingPrefix
from sim2act.contracts import AppManifest
from sim2act.db import fingerprint, grants, new_id, operation_intents, operations, runs
from sim2act.errors import DomainError


def seed_receipts(f):
    seed_cold(f)
    binding = f.cold_bound
    binding['source']['format'] = 'txt'
    plan = spec._bound_plan_from_facts(binding['draft'], {'input': {}}, binding['source'])
    binding['plan'] = plan
    steps, actions = plan['definition']['manifest']['workflow'], plan['definition']['actions']
    first, pending = new_id('op'), new_id('op')
    intent = spec.intent_for(steps[0], actions[0], plan, {}, [])
    value = copy.deepcopy(binding['source'])
    proof = spec.receipt_for(first, steps[0], actions[0], plan, intent, value)
    second = spec.intent_for(steps[1], actions[1], plan, {steps[0]['step_id']: value}, [proof])
    context = dict(kind='INTERNAL_APPRUN', messages=[], requests=0, repairs=0,
                   reserved_tokens=0, tools=1, spec_family=plan['definition']['namespace'])
    f.cold_job['context'] = context
    with f.store.tx() as c:
        c.execute(update(runs).where(runs.c.id == f.cold_job['id']).values(context=context))
        # Insert reverse SQL order; qualification must follow the plan.
        for oid, index, request, status, receipt in (
            (pending, 1, second, 'DISPATCHED', None), (first, 0, intent, 'VERIFIED', proof)
        ):
            c.execute(insert(operations).values(id=oid, run_id=f.cold_job['id'],
                call_id=steps[index]['step_id'], tool_ref=actions[index]['executor']['ref'],
                fingerprint=fingerprint(request), status=status, receipt=receipt))
            c.execute(insert(operation_intents).values(operation_id=oid, request=request))
        f.store.event(c, f.cold_job['id'], 'SPEC_STEP_VERIFIED',
                      dict(step_id=steps[0]['step_id'], operation_id=first, fence=1))
        f.store.event(c, f.cold_job['id'], 'CLAIMED', dict(fence=1))
    return SimpleNamespace(pending=pending, first=first, proof=proof,
        meta=dict(operation_id=pending, ordinal=0, step_id=steps[1]['step_id']))


def setup(f, c, r, *, prior=False):
    def prepare(graph):
        graph.add('call', dict(meta=r.meta))
        reader = rt._ColdRunFacts(f.store, c, f.cold_job, graph)
        reader.record_counters(AppManifest.model_validate(f.cold_bound['plan']['definition']['manifest']))
        prefix = _ColdBindingPrefix(graph, 'synthetic-platform-binding', f.user, f.cold_job,
            AppManifest.model_validate(f.cold_bound['plan']['definition']['manifest']).runtime_limits,
            'cold', {}, None, None)
        graph.add(prefix.key + ':bound:complete', f.cold_bound)
        platform = object.__new__(rt._ColdBindingGraph)
        for key, value in dict(guard=graph, counter_reader=reader,
                               binding=f.cold_bound, binding_prefix=prefix).items():
            object.__setattr__(platform, key, value)
        r.reader, r.platform = reader, platform
        if prior:
            r.original = spec._cold_receipts(f.store, c, f.cold_job, f.cold_bound,
                                            reader, pending_id=r.pending)
        return platform
    return prepare


@pytest.mark.parametrize('prior', [False, True])
def test_real_receipt_pass_exact_pair_original_bytes_and_dynamic_m(sql_facts, prior):
    f = sql_facts
    r = seed_receipts(f)
    with f.store.tx() as c, native_segment(f, c, receipt_setup=setup(f, c, r, prior=prior)) as s:
        assert s.cohort.route == 'OWNED'
        closure = s.candidate.receipt
        m = len(r.reader._receipt_proofs)
        assert m == int(prior) and closure.m == m
        before = set(s.graph.inputs)
        result = spec._cold_receipts(f.store, c, f.cold_job, f.cold_bound,
                                    r.reader, pending_id=r.pending)
        assert set(s.graph.inputs) - before == set(closure.names)
        assert closure.phase == 'DONE' and len(r.reader._receipt_proofs) == m + 1
        saved = r.reader._raw['receipts:' + str(m)]
        assert saved['outputs'] is result[0] and saved['proved'] is result[1]
        assert fingerprint(result[1][0]) == fingerprint(r.proof)
        assert not any('node-input:' in name or 'node-proof:' in name or ':effect:' in name
                       for name in s.graph.inputs)
        r.saved, r.graph = saved, s.graph
    assert not s.mode.active and not r.graph.active


@pytest.mark.parametrize('damage', ['reader', 'job', 'binding', 'pending', 'm', 'intent', 'rebind', 'mutation', 'twice'])
def test_exact_receipt_protocol_refuses_and_closes(sql_facts, damage):
    f = sql_facts
    r = seed_receipts(f)
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(
        f, c, receipt_setup=setup(f, c, r)
    ) as s:
        job, binding, reader, pending = f.cold_job, f.cold_bound, r.reader, r.pending
        if damage == 'reader':
            reader = copy.copy(reader)
        elif damage == 'job':
            job = dict(job)
        elif damage == 'binding':
            binding = dict(binding)
        elif damage == 'pending':
            pending = 'wrong-operation'
        elif damage == 'm':
            reader._receipt_proofs.append('receipts:foreign')
        elif damage == 'intent':
            reader.intent('extra-operation')
        elif damage == 'rebind':
            s.graph.add(s.candidate.receipt.names[0], binding)
        elif damage == 'mutation':
            reader._raw['intent:' + r.first]['args']['changed'] = True
        elif damage == 'twice':
            spec._cold_receipts(f.store, c, job, binding, reader, pending_id=pending)
        spec._cold_receipts(f.store, c, job, binding, reader, pending_id=pending)
    assert not s.mode.active and not s.graph.active


def test_receipt_capacity_chooses_legacy_before_pair_or_issuance(sql_facts):
    from test_cold_accounted_native import NATIVE_LIMITS
    f = sql_facts
    r = seed_receipts(f)
    with f.store.tx() as c, native_segment(f, c, receipt_setup=setup(f, c, r),
        limits=NATIVE_LIMITS._replace(resident=8_000_000, peak=20_000_000)) as s:
        assert s.cohort.route == 'LEGACY' and s.graph._accounted_frontier is None
        assert s.candidate.qualification_phase == 'native:receipt-budget'
        assert not s.candidate.mode.scope._issued
        result = spec._cold_receipts(f.store, c, f.cold_job, f.cold_bound,
                                    r.reader, pending_id=r.pending)
        assert fingerprint(result[1][0]) == fingerprint(r.proof)


@pytest.mark.parametrize('damage', ['write', 'revoke', 'rollback', 'stop'])
def test_receipt_original_dynamic_guards_remain(sql_facts, damage):
    f = sql_facts
    r = seed_receipts(f)
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(
        f, c, receipt_setup=setup(f, c, r)
    ) as s:
        if damage == 'write':
            c.execute(update(runs).where(runs.c.id == f.cold_job['id']).values(version=2))
        elif damage == 'revoke':
            c.execute(update(grants).values(revoked=True))
        elif damage == 'rollback':
            c.rollback()
        else:
            f.worker.stop.set()
        spec._cold_receipts(f.store, c, f.cold_job, f.cold_bound, r.reader, pending_id=r.pending)
    assert not s.mode.active and not s.graph.active


def test_longer_prefix_legacy_before_any_handle_and_original_failure_not_swallowed(sql_facts):
    f = sql_facts
    r = seed_receipts(f)
    with f.store.tx() as c:
        c.execute(insert(operations).values(id=new_id('op'), run_id=f.cold_job['id'],
            call_id='extra-step', status='DISPATCHED', tool_ref='resource.read'))
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(
        f, c, receipt_setup=setup(f, c, r)
    ) as s:
        assert s.cohort.route == 'LEGACY' and not s.candidate.mode.scope._issued
        assert s.candidate.selection['reason'] == 'receipt_operations'
        spec._cold_receipts(f.store, c, f.cold_job, f.cold_bound, r.reader, pending_id=r.pending)


def test_original_preload_failure_never_becomes_legacy(sql_facts, monkeypatch):
    f = sql_facts
    r = seed_receipts(f)
    marker = DomainError('VERSION_CONFLICT', 'original reader failed')

    def failed(self):
        raise marker

    monkeypatch.setattr(rt._ColdRunFacts, 'receipt_operations', failed)
    with pytest.raises(DomainError) as refusal, f.store.tx() as c:
        with native_segment(f, c, receipt_setup=setup(f, c, r)):
            pytest.fail('original failure cannot issue or fall back')
    assert refusal.value is marker


def test_shared_dag_and_quoted_unicode_cannot_undercharge_receipt_json(sql_facts):
    from sqlalchemy.sql.elements import quoted_name
    from test_cold_accounted_native import NATIVE_LIMITS
    f = sql_facts
    r = seed_receipts(f)
    shared = quoted_name('\U0001f332' * 1000, True)
    for _ in range(18):
        shared = [shared, shared]
    f.cold_bound['plan']['unconsumed-but-pinned'] = shared
    with f.store.tx() as c, native_segment(f, c, receipt_setup=setup(f, c, r),
        limits=NATIVE_LIMITS._replace(resident=512 * 1024**2, peak=1024 * 1024**2)) as s:
        assert s.cohort.route == 'LEGACY' and not s.candidate.mode.scope._issued
        assert s.candidate.selection['reason'] == 'receipt_unfolded_extent'
        result = spec._cold_receipts(f.store, c, f.cold_job, f.cold_bound,
                                    r.reader, pending_id=r.pending)
        assert fingerprint(result[1][0]) == fingerprint(r.proof)


@pytest.mark.parametrize('damage', ['foreign', 'owner', 'pending_type'])
def test_protocol_provenance_never_dispatches_foreign_callbacks(sql_facts, damage):
    f = sql_facts
    r = seed_receipts(f)
    calls = []

    class Foreign:
        def __getattr__(self, key):
            calls.append(key)
            raise AssertionError('foreign protocol')

        def __eq__(self, value):
            calls.append('eq')
            raise AssertionError('foreign pending equality')

    foreign_closure = None
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(
        f, c, receipt_setup=setup(f, c, r)
    ) as s:
        if damage == 'foreign':
            s.candidate.receipt = Foreign()
        elif damage == 'owner':
            s.candidate.receipt.candidate = object()
            foreign_closure = s.candidate.receipt
        spec._cold_receipts(f.store, c, f.cold_job, f.cold_bound, r.reader,
                            pending_id=Foreign() if damage == 'pending_type' else r.pending)
    assert calls == [] and not s.mode.active
    if foreign_closure is not None:
        assert foreign_closure.phase == 'READY'
