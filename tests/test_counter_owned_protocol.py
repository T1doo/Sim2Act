"""Default native ownership and the still-supported mutable counter domain."""
import sys
import time

import pytest
from sqlalchemy import event
from counter_loaded_cases import local_origin as local_origin
from counter_loaded_cases import no_external_transport as no_external_transport
from counter_loaded_cases import prepared,observe_core,scope
import counter_loaded_cases as original

from sim2act import natural_spec_runtime as r,pb_natural_specs as pb
from sim2act.errors import DomainError


@pytest.mark.parametrize('marker',[False,True])
@pytest.mark.parametrize('count',[0,2])
def test_owned_seed_full_counter_fallback_and_node_identity(local_origin,monkeypatch,marker,count):
    f=local_origin
    with f.store.tx() as c,pb._source_reads(f.store,c),scope(f,c) as guard:
        facts,seed=prepared(f,c,guard,count=count,marker=marker)
        assert facts._source_owned is True and r._source_owned_code.image.is_kind(seed.job,'d')
        queries=[]
        def sql(*args):queries.append(True)
        event.listen(f.store.engine,'before_cursor_execute',sql)
        try:
            with observe_core() as calls:
                actual=r._counters(c,facts.job,f.origin[0],_facts=facts)
            # The original raw segment is deliberately exact-dict/list only.
            assert calls==[] and queries==[]
            with monkeypatch.context() as patch:
                patch.setattr(r,'_cold_counter_loaded',lambda *args:r._RAW_READ_MISS)
                expected=r._counters(c,facts.job,f.origin[0],_facts=facts)
            assert actual==expected and len(actual)==count
            assert all(r._source_owned_code.image.same(a,b) for a,b in zip(actual,expected,strict=True))
            assert all(any(r._source_owned_code.image.same(row,source) for source in seed.attempt_rows) for row in actual)
            assert len(facts._manifests)==1 and queries==[]
            facts.check(f.store,c,facts.job)
        finally:event.remove(f.store.engine,'before_cursor_execute',sql)


@pytest.mark.parametrize('mapping_job',[True,'cursor'])
@pytest.mark.parametrize('marker',[False,True])
def test_owned_seed_rejects_independent_sql_mapping_identity(local_origin,mapping_job,marker):
    f=local_origin
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError,match='Cold Run raw facts changed identity'):
            with scope(f,c) as guard:
                with observe_core() as calls:
                    prepared(f,c,guard,count=2,use_seed=True,mapping_job=mapping_job,marker=marker)
        assert calls==[] and not guard.active


@pytest.mark.parametrize('mapping_job',[False,True,'cursor'])
def test_default_native_mutable_job_still_hits_original_core(local_origin,monkeypatch,mapping_job):
    f=local_origin
    with f.store.tx() as c,pb._source_reads(f.store,c),scope(f,c) as guard:
        facts,seed=prepared(f,c,guard,count=2,use_seed=False,mapping_job=mapping_job)
        assert seed is None and facts._source_owned is False
        queries=[]
        def sql(*args):queries.append(True)
        event.listen(f.store.engine,'before_cursor_execute',sql)
        try:
            with observe_core() as calls:
                actual=r._counters(c,facts.job,f.origin[0],_facts=facts)
            assert calls==[1] and queries==[]
            start=guard._diagnostic_counts[0]
            assert r._counters(c,facts.job,f.origin[0],_facts=facts)==actual
            fast=guard._diagnostic_counts[0]-start
            with monkeypatch.context() as patch:
                patch.setattr(r,'_cold_counter_loaded',lambda *args:r._RAW_READ_MISS)
                start=guard._diagnostic_counts[0]
                expected=r._counters(c,facts.job,f.origin[0],_facts=facts)
                slow=guard._diagnostic_counts[0]-start
            assert fast<slow and len(actual)==2 and queries==[]
            assert all(a is b for a,b in zip(actual,expected,strict=True))
        finally:event.remove(f.store.engine,'before_cursor_execute',sql)


@pytest.mark.parametrize('damage',['mutate','raise'])
def test_default_mutable_core_retains_late_pin_and_original_exception(local_origin,damage):
    f=local_origin;error=ValueError('synthetic original counter execution failure')
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError if damage=='mutate' else ValueError) as caught:
            with scope(f,c) as guard:
                facts,_=prepared(f,c,guard,use_seed=False,mapping_job=True)
                def changed():
                    if damage=='raise':raise error
                    facts.job['context']['messages'].append('synthetic live alias drift')
                with observe_core(changed) as calls:
                    r._counters(c,facts.job,f.origin[0],_facts=facts)
        assert calls==[1] and not guard.active
        if damage=='raise':assert caught.value is error


@pytest.mark.parametrize('change',['extra_slot','duplicate_anchor','wrong_anchor','wrong_mode','context','repeated_ordinal'])
def test_owned_bad_loaded_values_retain_original_rejection(local_origin,monkeypatch,change):
    original.test_bad_loaded_values_keep_original_rejection(local_origin,monkeypatch,change)


def test_owned_missing_collection_preserves_real_query(local_origin):
    original.test_missing_raw_key_uses_original_query_without_packet(local_origin)


def test_unseeded_unsuitable_snapshot_still_falls_back(local_origin):
    original.test_unsuitable_snapshot_falls_back_before_core(local_origin)


def test_unsupported_canonical_seed_value_is_rejected_before_counter(local_origin):
    from sqlalchemy.sql.elements import quoted_name
    f=local_origin
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError,match='Unsupported model proof value'):
            with scope(f,c) as guard:
                with observe_core() as calls:
                    prepared(f,c,guard,job_extra=dict(result=quoted_name('synthetic',None)))
        assert calls==[] and not guard.active


@pytest.mark.parametrize('name',['_Comparison','standard_serializers'])
def test_default_source_rejects_changed_code_before_foreign_callback(local_origin,monkeypatch,name):
    f=local_origin;foreign=[]
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError,match='Complete Source code changed'):
            with scope(f,c) as guard:
                facts,_=prepared(f,c,guard)
                with monkeypatch.context() as patch:
                    if name=='_Comparison':patch.setattr(r._policy_segments,name,lambda *args:foreign.append(True))
                    else:patch.setattr(r._RAW_READ_COMPARISON,name,lambda *args:foreign.append(True))
                    with observe_core() as calls:
                        r._counters(c,facts.job,f.origin[0],_facts=facts)
        assert calls==[] and foreign==[] and not guard.active


def test_default_unknown_json_dependency_keeps_original_fallback(local_origin,monkeypatch):
    original.test_unknown_copy_or_json_dependencies_use_old_path(local_origin,monkeypatch,'json_defaults')


@pytest.mark.parametrize('damage',['job-copy','attempt-root','audit-alias','epoch','owner','role-limits','scope','stop'])
def test_owned_scope_mutation_and_dynamic_stop_remain_sticky(local_origin,damage):
    f=local_origin
    if damage=='stop':
        # A pure read scope is not itself a running model. Exercise the real
        # finite-interval checkpoint, which is where stop is a live condition.
        f.worker._settlement_interval=(time.monotonic()+60,time.time()+60)
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError):
            with scope(f,c) as guard:
                facts,seed=prepared(f,c,guard,count=2)
                if damage=='job-copy':facts.job=r._source_owned_code.image.plain(seed.job)
                elif damage=='attempt-root':facts._raw['attempts']=[]
                elif damage=='audit-alias':seed.audit.rows['attempts'].append({'unproved':True})
                elif damage=='epoch':guard.epoch+=1
                elif damage=='owner':vars(guard.binding.contract)['principal_id']='different-synthetic-owner'
                elif damage=='role-limits':guard.role_limits['per_use'].max_requests+=1
                elif damage=='scope':guard.scope[0]=object()
                else:f.worker.stop.set()
                r._counters(c,facts.job,f.origin[0],_facts=facts)
        assert not guard.active


def test_owned_retired_producer_alias_is_not_a_live_input(local_origin):
    f=local_origin;aliases=[];monitor=sys.monitoring
    slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    code=r._source_owned_code.own_fact.__code__
    def entering(code,offset):
        frame=sys._getframe(1)
        if frame.f_locals['name'].startswith('run-raw-seed:'):
            aliases.append(frame.f_locals['value']['job'])
    monitor.use_tool_id(slot,'Hold original private producer alias without changing it')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,entering)
        monitor.set_local_events(slot,code,monitor.events.PY_START)
        with f.store.tx() as c,pb._source_reads(f.store,c),scope(f,c) as guard:
            facts,seed=prepared(f,c,guard,count=2)
            assert len(aliases)==1 and type(aliases[0]) is dict
            before=r._source_owned_code.image.plain(seed.job)
            aliases[0]['context']['messages'].append('retired synthetic private alias')
            aliases[0]['context']['requests']=999
            assert r._source_owned_code.image.plain(seed.job)==before
            with pytest.raises(AttributeError):seed.job['context']['messages'].append('cannot mutate View')
            assert len(r._counters(c,facts.job,f.origin[0],_facts=facts))==2
            facts.check(f.store,c,facts.job)
            assert guard.active
    finally:
        monitor.set_local_events(slot,code,0)
        monitor.register_callback(slot,monitor.events.PY_START,None)
        monitor.free_tool_id(slot)
