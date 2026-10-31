"""Real first-SQL boundary probes, with the original complete ancestry oracle."""
import copy
import sys
from contextlib import contextmanager

import pytest
from sqlalchemy.engine import RowMapping
from test_cold_binding_graph_integration import test_plain_pb_first_binding_producer_equals_public_complete_ancestry as original
from sim2act import _cold_source_packet as owned, lifecycle as life, natural_spec_runtime as rt
from sim2act import apps, natural_specs as natural, pa_spec_apps as spec
from sim2act.errors import DomainError


@contextmanager
def observe_release(patch, probe):
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    checkpoint=life._checkpoint_release_read.__code__;producer=life.owned_release_pointer.__code__;publish=owned.own_fact.__code__
    probe.update(callbacks=[],rows=[],publications=0)
    def poison(*args,**kwargs):
        probe['callbacks'].append(True)
        raise AssertionError('Unknown Release producer/configuration executed')
    class Holder:
        def __iter__(self):return poison()
        def __len__(self):return poison()
        def __bool__(self):return poison()
    def entering(code,offset):
        frame=sys._getframe(1)
        if ':complete-row:' not in frame.f_locals['name']:return
        raw,graph=frame.f_locals['value'],frame.f_locals['graph']
        assert type(raw) is RowMapping
        probe['graph']=graph;probe['rows'].append((raw,copy.deepcopy(dict(raw))))
        if probe['mode']=='early-bounds' and not probe.get('injected'):
            probe['injected']=True
            raise probe['error']
    def returned(code,offset,value):
        frame=sys._getframe(1)
        if code is checkpoint:
            caller=frame.f_back
            if (caller is None or caller.f_code is not producer or probe.get('injected')
                    or caller.f_locals.get('_graph_read') is None
                    or type(caller.f_locals.get('r')) is not RowMapping):return
            mode=probe['mode'];probe['graph']=caller.f_locals['_graph_read']
            if mode in ('producer','entry','holder','class','model','require','inputs','active','pa-model','runtime-model'):
                probe['injected']=True
                if mode=='producer':patch.setattr(rt,'_cold_release_row',poison)
                elif mode=='entry':patch.setattr(rt,'_COLD_RELEASE_ROW_ENTRY',Holder())
                elif mode=='holder':patch.setattr(life,'_RELEASE_OWNED_CHECK',Holder())
                elif mode=='class':patch.setattr(apps,'_ColdCandidatePrefix',poison)
                elif mode=='model':patch.setattr(natural.Recipe,'model_validate',classmethod(poison))
                elif mode=='require':patch.setattr(rt,'require',poison)
                elif mode=='pa-model':patch.setattr(spec,'AppManifest',poison)
                elif mode=='runtime-model':patch.setattr(rt,'AppManifest',poison)
                elif mode=='inputs':probe['graph'].inputs=Holder()
                elif mode=='active':probe['graph'].active=Holder()
            return
        if ':complete-row:' not in frame.f_locals['name']:return
        graph,raw=frame.f_locals['graph'],frame.f_locals['value']
        expected=next(saved for item,saved in probe['rows'] if item is raw)
        assert owned.image.is_kind(value,'r')
        assert owned.image.plain(value)==expected
        assert owned.native.match_node(value.owner(),value.ref(),raw,owned._config(graph))
        probe['publications']+=1
        probe.setdefault('owners',[]).append(value.owner())
        if probe.get('injected'):return
        if probe['mode']=='late-bounds':
            probe['injected']=True
            raise probe['error']
        if probe['mode']=='producer-alias':
            probe['injected']=True
            raw['snapshot']['draft']['candidate']['old_producer_only']='synthetic mutation'
            assert owned.image.plain(value)==expected
            graph.check(graph.store,graph.connection)
    monitor.use_tool_id(slot,'Real Release SQL/complete ownership probe')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,entering)
        monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        monitor.set_local_events(slot,publish,monitor.events.PY_START|monitor.events.PY_RETURN)
        monitor.set_local_events(slot,checkpoint,monitor.events.PY_RETURN)
        yield
    finally:
        for code in (publish,checkpoint):monitor.set_local_events(slot,code,0)
        for event in (monitor.events.PY_START,monitor.events.PY_RETURN):monitor.register_callback(slot,event,None)
        monitor.free_tool_id(slot)


def invoke(tmp_path,monkeypatch,probe):
    import cold_use_base_probe
    monkeypatch.setattr(cold_use_base_probe,'observe_base',observe_release)
    original(tmp_path,monkeypatch,_base_probe=probe)


def test_complete_sql_image_and_old_producer_alias_are_retained(tmp_path,monkeypatch):
    probe={'mode':'producer-alias'}
    invoke(tmp_path,monkeypatch,probe)
    assert probe['injected'] and probe['callbacks']==[] and probe['publications']>=4
    # Separate SELECT results never collapse to an owner by release ID.
    assert len({id(owner) for owner in probe['owners']})==len(probe['owners'])
    assert not probe['graph'].active


@pytest.mark.parametrize('mode',['producer','entry','holder','class','model','require','inputs','active','pa-model','runtime-model'])
def test_sql_checkpoint_rejects_unknown_dispatch_before_any_callback(tmp_path,monkeypatch,mode):
    probe={'mode':mode}
    with pytest.raises(DomainError):invoke(tmp_path,monkeypatch,probe)
    assert probe['injected'] and probe['callbacks']==[] and not probe['graph'].active
    assert probe['publications']==0


def test_late_capacity_keeps_exception_and_invalidates_without_replay(tmp_path,monkeypatch):
    error=owned.image.Bounds('synthetic late Release capacity')
    probe={'mode':'late-bounds','error':error}
    with pytest.raises(owned.image.Bounds) as caught:invoke(tmp_path,monkeypatch,probe)
    assert caught.value is error and probe['injected'] and probe['callbacks']==[]
    assert probe['publications']==1 and len(probe['rows'])==1 and not probe['graph'].active


def test_prepublication_bound_retains_original_complete_path(tmp_path,monkeypatch):
    probe={'mode':'early-bounds','error':owned.image.Bounds('synthetic early Release capacity')}
    invoke(tmp_path,monkeypatch,probe)
    assert probe['injected'] and probe['callbacks']==[] and probe['publications']>=3
    assert not probe['graph'].active
