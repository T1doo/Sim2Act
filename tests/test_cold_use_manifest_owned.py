"""Complete private model/dump transfer with default GC and real SQLite scope.

Upstream rows are synthetic; no Worker constructor, send, model or transport.
"""
from contextlib import contextmanager, nullcontext
import gc
import sys

import pytest
from pydantic import BaseModel
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import _cold_use_manifest as manifest
from sim2act import _cold_source_packet as owned
from sim2act import natural_live_admission as gate, natural_spec_runtime as rt
from sim2act import natural_specs as natural, pb_natural_specs as pb
from sim2act.errors import DomainError


@contextmanager
def graph_scope(f,phase='pre'):
    limits=gate._limits(f.contract)
    roles=dict(source=limits,generate=None,platform=limits,trial=limits,per_use=limits)
    with f.store.tx() as c,pb._source_reads(f.store,c),rt._cold_graph_read(
            f.worker,c,{'synthetic-manifest-only':True},roles,phase) as graph:
        yield graph,limits


def compare_storage(view,value,memo=None):
    """Independent exact storage/type/order/alias oracle, not only model_dump."""
    if memo is None:memo={}
    if isinstance(value,BaseModel):
        assert owned.image.is_kind(view,'m')
        tag,payload=view.node()
        assert view.read(payload[0])==type(value).__module__+'.'+type(value).__qualname__
        assert owned.image.plain(view.read(payload[2]))==value.__pydantic_fields_set__
        assert view.read(payload[3]) is value.__pydantic_extra__ is None
        assert view.read(payload[4]) is value.__pydantic_private__ is None
        compare_storage(view.read(payload[1]),value.__dict__,memo)
        return
    kind=type(value)
    if kind in (dict,list,tuple,set):
        assert owned.image.is_kind(view,{dict:'d',list:'l',tuple:'q',set:'e'}[kind])
        old=memo.get(id(value))
        if old is not None:
            assert owned.image.same(old,view)
            return
        memo[id(value)]=view
        if kind is dict:
            assert tuple(view)==tuple(value)
            for key,child in value.items():compare_storage(view[key],child,memo)
        elif kind is set:
            assert owned.image.plain(view)==value
        else:
            assert len(view)==len(value)
            for left,right in zip(view,value,strict=True):compare_storage(left,right,memo)
    else:
        assert type(view) is kind and view==value


def produce(f,graph,limits,key='test-per-use:manifest'):
    selected=manifest.compiler(graph)
    assert selected is natural.compile_candidate
    model,_,_=selected(f.extraction[0]['candidate'],limits)
    return model,manifest.publish(graph,key,model,selected)


def test_default_owner_retired_alias_full_storage_dump_and_scope(sql_facts):
    f=sql_facts
    assert gc.isenabled()
    with graph_scope(f) as (graph,limits):
        original,value=produce(f,graph,limits)
        assert manifest.is_manifest(value)
        model=manifest.current(graph,value)
        compare_storage(model,original)
        assert owned.image.plain(manifest.dump(graph,value))==original.model_dump()
        expected=owned.image.plain(manifest.dump(graph,value))
        original.input_schema['retired-private-alias']=True
        original.runtime_limits.max_requests=0
        graph.check(f.store,graph.connection)
        assert owned.image.plain(manifest.dump(graph,value))==expected
        assert model.runtime_limits.max_requests>0
        with pytest.raises(TypeError):model['revision']=9
    with pytest.raises(DomainError):manifest.current(graph,value)
    assert gc.isenabled()


def test_live_limits_alias_selects_original_before_publication(sql_facts):
    f=sql_facts
    with graph_scope(f) as (graph,limits):
        selected=manifest.compiler(graph)
        model,_,_=selected(f.extraction[0]['candidate'],limits)
        # This is an explicit alias boundary, never a model class workaround.
        model.runtime_limits=limits
        result=manifest.publish(graph,'test-shared:manifest',model,selected)
        assert result is model
        assert 'test-shared:manifest' not in graph.inputs
        graph.check(f.store,graph.connection)


def test_external_schema_alias_stays_in_complete_graph_pin(sql_facts):
    f=sql_facts
    with pytest.raises(DomainError):
        with graph_scope(f) as (graph,limits):
            selected=manifest.compiler(graph)
            model,_,_=selected(f.extraction[0]['candidate'],limits)
            graph.add('actual-outside-alias',model.input_schema)
            value=manifest.publish(graph,'test-anchored:manifest',model,selected)
            assert manifest.is_manifest(value)
            model.input_schema['outside-mutation']=True
            graph.check(f.store,graph.connection)
    assert graph.active is False


@pytest.mark.parametrize('damage',['bounds','root-and-bounds'])
def test_prepublication_refusal_is_scope_checked_without_replay(sql_facts,damage):
    f=sql_facts
    with (pytest.raises(DomainError) if damage=='root-and-bounds' else nullcontext()),graph_scope(f) as (graph,limits):
        selected=manifest.compiler(graph)
        model,_,_=selected(f.extraction[0]['candidate'],limits)
        monitoring=sys.monitoring
        slot=next(i for i in (3,5,4) if monitoring.get_tool(i) is None)
        code=owned.image.capture.__code__
        calls=[]
        def entering(code,offset):
            frame=sys._getframe(1)
            incoming=frame.f_locals['incoming']
            if type(incoming) is not tuple or len(incoming)!=2 or incoming[0] is not model:return
            calls.append(True)
            if damage=='root-and-bounds':graph.inputs['test-refusal:manifest']=None
            raise owned.image.Bounds('synthetic manifest prepublication capacity')
        monitoring.use_tool_id(slot,'Complete manifest prepublication refusal')
        try:
            monitoring.register_callback(slot,monitoring.events.PY_START,entering)
            monitoring.set_local_events(slot,code,monitoring.events.PY_START)
            if damage=='bounds':
                assert manifest.publish(graph,'test-refusal:manifest',model,selected) is model
                graph.check(f.store,graph.connection)
            else:
                manifest.publish(graph,'test-refusal:manifest',model,selected)
        finally:
            monitoring.set_local_events(slot,code,0)
            monitoring.register_callback(slot,monitoring.events.PY_START,None)
            monitoring.free_tool_id(slot)
    assert calls==[True]
    if damage=='root-and-bounds':assert graph.active is False


def test_independent_scope_cannot_reuse_equal_manifest_owner(sql_facts):
    f=sql_facts
    limits=gate._limits(f.contract)
    roles=dict(source=limits,generate=None,platform=limits,trial=limits,per_use=limits)
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with rt._cold_graph_read(f.worker,c,{'same-complete-input':True},roles,'pre') as first:
            _,left=produce(f,first,limits)
            with pytest.raises(DomainError):
                with rt._cold_graph_read(f.worker,c,{'same-complete-input':True},roles,'pre') as second:
                    _,right=produce(f,second,limits)
                    assert owned.image.plain(left[3])==owned.image.plain(right[3])
                    assert left[2].owner() is not right[2].owner()
                    manifest.current(second,left)
            assert second.active is False
            first.check(f.store,c)


@pytest.mark.parametrize('method',['current','publish'])
def test_wrong_scope_rejects_without_foreign_cleanup_callbacks(method):
    calls=[]
    class Foreign:
        def __getattr__(self,name):
            calls.append(name)
            raise AssertionError('Foreign cleanup must never execute')
    for graph in (None,Foreign()):
        with pytest.raises(DomainError):
            if method=='current':manifest.current(graph,None)
            else:manifest.publish(graph,'unused',None,None)
    assert calls==[]

    foreign=lambda *args:calls.append('explicit-kind')
    with pytest.raises(TypeError):
        if method=='current':manifest.current(None,None,_kind=foreign)
        else:manifest.publish(None,'unused',None,None,_kind=foreign)
    assert calls==[]


@pytest.mark.parametrize('name',['_TYPE','_LEN'])
def test_predicate_builtin_roles_cannot_dispatch_foreign(monkeypatch,name):
    calls=[]
    monkeypatch.setattr(manifest,name,lambda *args:calls.append(True))
    assert manifest.is_manifest(None) is False
    assert manifest.is_manifest((manifest.TAG,'synthetic',None,None)) is True
    assert calls==[]


def test_trial_dump_qualifies_new_helper_before_dispatch(sql_facts,monkeypatch):
    from types import SimpleNamespace
    calls=[]
    monkeypatch.setattr(manifest,'is_manifest',lambda *args:calls.append(True))
    with pytest.raises(DomainError):
        rt._ColdTrialGraph._dump(SimpleNamespace(_owned_models=None),None)
    assert calls==[]


@pytest.mark.parametrize('name',['_TYPE','_ALL','_DICT','DomainError'])
def test_changed_helper_role_rejected_before_foreign_dispatch(monkeypatch,name):
    calls=[]
    monkeypatch.setattr(manifest,name,lambda *args:calls.append(True))
    with pytest.raises(DomainError):owned.current()
    assert calls==[]
