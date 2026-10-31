"""Complete owned Release sizing and original raw late SQL continuation."""
import pytest
from sqlalchemy import select
from accounted_sqlite_fixture import seed_cold
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import sql_facts, forbid_execution
from sim2act import lifecycle, _cold_source_packet as source
from sim2act import natural_spec_runtime as rt
from sim2act.db import internal_releases
from sim2act.errors import DomainError


def own_bindings(f,c,observed):
    def prepare(graph):
        for i,bound in enumerate((f.cold_bound,f.bound)):
            row=lifecycle.owned_release_pointer(f.store,c,f.user,bound['snapshot']['release_id'],
                _graph_read=graph,_graph_key='test-initial-release:'+str(i))
            assert source.image.is_kind(row,'r')
            bound['release']=row
            observed.append(row)
    return prepare


def test_owned_full_row_qualifies_and_late_independent_sql_stays_raw(sql_facts):
    from sqlalchemy.engine import RowMapping
    f=sql_facts;seed_cold(f);observed=[]
    with f.store.tx() as c,native_segment(f,c,binding_setup=own_bindings(f,c,observed)) as s:
        assert s.cohort.route=='OWNED'
        assert len(observed)==2 and observed[0].owner() is not observed[1].owner()
        before=set(s.graph.inputs);owners=dict(vars(s.graph)['_source_fact_bindings'])
        for bound,initial in zip((f.cold_bound,f.bound),observed,strict=True):
            rid=bound['snapshot']['release_id'];key='release-pointer:'+f.user+':'+rid
            current=lifecycle.owned_release_pointer(f.store,c,f.user,rid,_graph_read=s.graph)
            assert type(current) is RowMapping and current is not initial
            assert source.image.plain(initial)==dict(current)
            assert s.graph.inputs[key]==dict(current)
        assert set(s.graph.inputs)-before=={'release-pointer:'+f.user+':'+b['snapshot']['release_id'] for b in (f.cold_bound,f.bound)}
        assert vars(s.graph)['_source_fact_bindings']==owners
        s.graph.check(f.store,c)


@pytest.mark.parametrize('damage',['stop','epoch','frontier'])
def test_late_release_keeps_dynamic_scope_rejection(sql_facts,damage):
    f=sql_facts;seed_cold(f);observed=[];entered=False
    with pytest.raises(DomainError):
        with f.store.tx() as c,native_segment(f,c,binding_setup=own_bindings(f,c,observed)) as s:
            assert s.cohort.route=='OWNED';entered=True
            if damage=='stop':f.worker.stop.set()
            elif damage=='epoch':c.info['source_proof_write_epoch']=s.graph.epoch+1
            else:s.graph._accounted_frontier=object()
            lifecycle.owned_release_pointer(f.store,c,f.user,f.cold_bound['snapshot']['release_id'],_graph_read=s.graph)
    assert entered and not s.graph.active


@pytest.mark.parametrize('damage',['qualifier','unmetered-view','copied-rid','oversize-registry'])
def test_after_sizing_rejects_changed_source_without_foreign_callback(sql_facts,monkeypatch,damage):
    import sys
    from sim2act import _cold_accounted_native as native
    f=sql_facts;seed_cold(f);observed=[];calls=[];injected=[];observed_graph=[]
    code=native._SizingProjection.copy.__code__;monitor=sys.monitoring
    slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    def poison(*args,**kwargs):calls.append(True);raise AssertionError('Foreign qualifier executed')
    def returned(actual,offset,value):
        frame=sys._getframe(1);sizing=frame.f_locals['self']
        root=frame.f_locals['value']
        if injected or not (type(root) is dict and 'cold-trial:bound' in root):return
        # Exact top-level complete sizing, after all its ordinary recursive work.
        injected.append(True)
        if damage=='qualifier':monkeypatch.setattr(source,'current',poison)
        elif damage=='unmetered-view':
            root['cold-trial:bound']['binding']['release']=source.native.read_owner(observed[0].owner())
        elif damage=='copied-rid':value['cold-trial:bound']['binding']['snapshot']['release_id']='unrelated-release'
        else:
            # No huge set/scope allocation may precede the cardinality gate.
            registry=vars(observed_graph[0])['_source_fact_bindings']
            for i in range(len(root)+1):registry['unrelated:'+str(i)]=None
    monitor.use_tool_id(slot,'Native full sizing final source probe')
    try:
        monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        monitor.set_local_events(slot,code,monitor.events.PY_RETURN)
        with pytest.raises(DomainError):
            with f.store.tx() as c,native_segment(f,c,binding_setup=lambda graph: (observed_graph.append(graph),own_bindings(f,c,observed)(graph))):
                pytest.fail('Changed sized source must not issue')
    finally:
        monitor.set_local_events(slot,code,0);monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
    assert injected and calls==[]
