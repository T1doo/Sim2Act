"""Existing fixed read segment accepts fully owned data, never a stored PASS."""
import sys

import pytest
from counter_loaded_cases import local_origin as local_origin
from counter_loaded_cases import no_external_transport as no_external_transport
from counter_loaded_cases import prepared,scope,observe_core
from sim2act import natural_spec_runtime as r,pb_natural_specs as pb
from sim2act.errors import DomainError


def test_owned_loaded_read_qualifies_and_reduces_complete_pins(local_origin,monkeypatch,tmp_path):
    import json
    f=local_origin
    with f.store.tx() as c,pb._source_reads(f.store,c),scope(f,c) as guard:
        facts,seed=prepared(f,c,guard,count=2,marker=True)
        assert r._raw_read_eligible(facts,'model-reserved') is True
        monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
        dynamic=[];code=r._ColdGraphRead._check_dynamic.__code__
        def entering(code,offset):dynamic.append(True)
        monitor.use_tool_id(slot,'Count every original live boundary, not only full pins')
        monitor.register_callback(slot,monitor.events.PY_START,entering)
        monitor.set_local_events(slot,code,monitor.events.PY_START)
        start=guard._diagnostic_counts[0]
        actual=facts.model_reserved()
        fast=guard._diagnostic_counts[0]-start
        fast_dynamic=len(dynamic);dynamic.clear()
        with monkeypatch.context() as patch:
            patch.setattr(r,'_raw_read_eligible',lambda *args:False)
            start=guard._diagnostic_counts[0]
            expected=facts.model_reserved()
            slow=guard._diagnostic_counts[0]-start
        slow_dynamic=len(dynamic)
        monitor.set_local_events(slot,code,0)
        monitor.register_callback(slot,monitor.events.PY_START,None)
        monitor.free_tool_id(slot)
        assert r._source_owned_code.image.same(actual,expected)
        assert fast<slow
        assert fast_dynamic==slow_dynamic==8
        with observe_core() as calls:
            assert len(r._counters(c,facts.job,f.origin[0],_facts=facts))==2
        assert calls==[]  # No new View counter/snapshot backend.
        assert r._raw_read_eligible(facts,'model-reserved') is True
        (tmp_path/'owned-read-pins.json').write_text(json.dumps(dict(fast=fast,original=slow,
            fast_dynamic=fast_dynamic,original_dynamic=slow_dynamic,
            same_owned_node=True,counter_core_calls=0,classification='SYNTHETIC_EXISTING_READ_SEGMENT_NOT_WHOLE_FLOW_PERFORMANCE'),indent=2)+'\n')


def test_fixed_seed_still_has_late_complete_mutable_graph_check(local_origin):
    f=local_origin;calls=[];monitor=sys.monitoring
    slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    code=r._cold_seed_fixed_check.__code__
    def entering(code,offset):
        calls.append(True)
        f.inputs['history'][0]['body']+=b' synthetic actual live input mutation'
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError):
            with scope(f,c) as guard:
                facts,_=prepared(f,c,guard)
                assert r._raw_read_eligible(facts,'model-reserved') is True
                monitor.use_tool_id(slot,'Mutate only after entry complete pin')
                try:
                    monitor.register_callback(slot,monitor.events.PY_START,entering)
                    monitor.set_local_events(slot,code,monitor.events.PY_START)
                    facts.model_reserved()
                finally:
                    monitor.set_local_events(slot,code,0)
                    monitor.register_callback(slot,monitor.events.PY_START,None)
                    monitor.free_tool_id(slot)
        assert calls==[True] and not guard.active


@pytest.mark.parametrize('role',['current','is_kind','fact','view-alias','plain-helper','dynamic-helper','seed-helper'])
def test_changed_source_role_never_dispatches_foreign_callback(local_origin,monkeypatch,role):
    f=local_origin;calls=[]
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError):
            with scope(f,c) as guard:
                facts,_=prepared(f,c,guard)
                with monkeypatch.context() as patch:
                    foreign=lambda *args,**kwargs:calls.append(True)
                    if role=='current':patch.setattr(r._source_owned_code,'current',foreign)
                    elif role=='is_kind':patch.setattr(r._source_owned_code.image,'is_kind',foreign)
                    elif role=='fact':patch.setattr(r._source_owned_code,'fact',foreign)
                    elif role=='view-alias':patch.setattr(r,'_SOURCE_VIEW_TYPE',None)
                    elif role=='plain-helper':patch.setattr(r,'_raw_seed_plain',foreign)
                    elif role=='dynamic-helper':patch.setattr(r,'_raw_dynamic_eligible',foreign)
                    else:patch.setattr(r,'_raw_seed_eligible',foreign)
                    facts.model_reserved()
        assert calls==[] and not guard.active


def test_prewrite_remains_original_read_domain(local_origin):
    f=local_origin
    with f.store.tx() as c,pb._source_reads(f.store,c),r._cold_graph_read(f.worker,c,f.inputs,f.roles,'pre') as guard:
        facts,_=prepared(f,c,guard)
        assert r._raw_read_eligible(facts,'model-reserved') is False
        assert facts.model_reserved()==[]


def test_unknown_control_mutate_then_restore_keeps_original_full_order(local_origin):
    f=local_origin;calls=[];saved=f.inputs['history'][0]['body']
    class UnknownControl:
        def checkpoint(self,worker):
            calls.append(True)
            f.inputs['history'][0]['body']=(saved+b' transient drift') if len(calls)==1 else saved
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError):
            with scope(f,c) as guard:
                facts,_=prepared(f,c,guard)
                f.store._local_model_control=UnknownControl()
                assert r._raw_read_eligible(facts,'model-reserved') is False
                facts.model_reserved()
        assert calls==[True] and not guard.active


def test_exact_local_registry_active_epoch_is_callback_free_read_domain(local_origin):
    import time
    from sim2act._sqlite_run_control import Registry
    f=local_origin
    with f.store.tx() as c,pb._source_reads(f.store,c),scope(f,c) as guard:
        facts,_=prepared(f,c,guard,count=2,job_extra={'lease_until':time.time()+60})
        control=Registry(f.store);f.store._local_model_control=control
        with control.settlement(f.worker,facts.job,time.time()+60) as epoch:
            assert r._raw_read_eligible(facts,'model-reserved') is True
            before=epoch.checks
            value=facts.model_reserved()
            assert len(value)==2 and r._source_owned_code.image.same(value,facts._raw['model-reserved'])
            assert epoch.checks-before==8
            assert r._raw_read_eligible(facts,'model-reserved') is True
        assert epoch.closed


def test_real_registry_instance_shadow_is_not_fused(local_origin):
    from sim2act._sqlite_run_control import Registry
    f=local_origin;calls=[];saved=f.inputs['history'][0]['body']
    def changed(worker):
        calls.append(True)
        f.inputs['history'][0]['body']=(saved+b' transient shadow') if len(calls)==1 else saved
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError):
            with scope(f,c) as guard:
                facts,_=prepared(f,c,guard)
                control=Registry(f.store);control.checkpoint=changed
                f.store._local_model_control=control
                assert r._raw_read_eligible(facts,'model-reserved') is False
                facts.model_reserved()
        assert calls==[True] and not guard.active


def test_shadowed_settlement_getattr_keeps_original_full_order(local_origin,monkeypatch):
    import builtins
    original=builtins.getattr;f=local_origin;calls=[];saved=f.inputs['history'][0]['body']
    def shadow(value,name,default=None):
        if name=='_local_model_control':
            calls.append(True)
            f.inputs['history'][0]['body']=(saved+b' transient getter') if len(calls)==1 else saved
        return original(value,name,default)
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with pytest.raises(DomainError):
            with scope(f,c) as guard:
                facts,_=prepared(f,c,guard)
                with monkeypatch.context() as patch:
                    patch.setattr(r._raw_read_settlement,'getattr',shadow,raising=False)
                    assert r._raw_read_eligible(facts,'model-reserved') is False
                    facts.model_reserved()
        assert calls==[True] and not guard.active
