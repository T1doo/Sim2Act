"""Default real SQLite Graph publication lifecycle; no Worker or model calls."""
from contextlib import contextmanager
import gc
import hashlib
import sys
import weakref

import pytest
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_use_manifest_owned import graph_scope
from sim2act import _cold_graph_versions as versions, _cold_graph_structure_guard as structure
from sim2act import natural_spec_runtime as rt
from sim2act.errors import DomainError


def test_versions_hold_original_full_bytes_and_never_rebase_live_mutation(sql_facts,monkeypatch):
    f=sql_facts
    with pytest.raises(DomainError),graph_scope(f) as (graph,limits):
        initial=graph.content_version()
        assert type(initial) is versions.VERSION
        assert initial.raw==graph.input_bytes() and initial.key==hashlib.sha256(initial.raw).hexdigest()
        value={'complete':['one','two'],'alias':[]};value['same']=value['alias']
        graph.add('new-complete-root',value)
        current=graph.content_version();original=current.raw
        assert current is not initial and current.sequence==initial.sequence+1
        assert current.raw==graph.input_bytes() and current.key is graph.key
        assert versions.native.pin_matches(initial,original) is False
        assert sys.getrefcount(initial)==2  # Journal/state do not retain old versions.
        with pytest.raises(AttributeError):current.raw=b'forged'
        with pytest.raises(TypeError):versions.VERSION()
        value['complete'].append('mutation')
        monkeypatch.setattr(structure,'select',lambda graph:None)
        graph.check(f.store,graph.connection)
    assert not graph.active and current.raw==original
    with pytest.raises(DomainError):graph.content_version()


def test_expected_export_is_same_version_and_fresh_projection_remains_live(sql_facts):
    with graph_scope(sql_facts) as (graph,limits):
        value={'shared':['original']};graph.add('export-test',value)
        version,raw,key=graph.export_version()
        assert version is graph.content_version() and raw is version.raw and key is version.key
        projected=graph.input_bytes(_snapshot_values=True)
        assert projected['inputs']['export-test'] is value
        graph.add('next-version',{'new':True})
        assert version is not graph.content_version()
        with pytest.raises(DomainError):graph.export_version(version)


def test_cleanup_allocation_failure_keeps_primary_and_original_issuer_revoked(sql_facts):
    monitor = sys.monitoring
    slot = next(i for i in (3, 5, 4) if monitor.get_tool(i) is None)
    code = rt._ColdGraphRead.invalidate.__code__
    calls = []
    def allocating(code, offset, callee, arg0):
        if callee is versions.OWNED:
            calls.append('lookup')
            raise MemoryError('synthetic cleanup allocation failure')
    monitor.use_tool_id(slot, 'Failure before original cleanup lookup allocation')
    try:
        monitor.register_callback(slot, monitor.events.CALL, allocating)
        monitor.set_local_events(slot, code, monitor.events.CALL)
        with pytest.raises(DomainError) as caught, graph_scope(sql_facts) as (graph, limits):
            graph.inputs['mutated-root'] = True
            graph.check(sql_facts.store, graph.connection)
        assert calls and graph.active is False
        assert caught.value.code == 'VERSION_CONFLICT'
        with pytest.raises(DomainError):graph.content_version()
    finally:
        monitor.set_local_events(slot, code, 0)
        monitor.register_callback(slot, monitor.events.CALL, None)
        monitor.free_tool_id(slot)


@pytest.mark.parametrize('damage',['delete-journal','none-journal','old-key','capability-false'])
def test_issued_version_cannot_downgrade_or_rebind(sql_facts,monkeypatch,damage):
    f=sql_facts
    with pytest.raises(DomainError),graph_scope(f) as (graph,limits):
        old=graph.content_version();graph.add('next-root',{'a':1})
        if damage=='delete-journal':del graph._pin_journal
        if damage=='none-journal':graph._pin_journal=None
        if damage=='old-key':graph.key=old.key
        if damage=='capability-false':monkeypatch.setattr(versions,'AVAILABLE',False)
        graph.check(f.store,graph.connection)
    assert graph.active is False


def test_other_graph_journal_and_same_bytes_never_share_identity(sql_facts):
    from sim2act import pb_natural_specs as pb, natural_live_admission as gate
    f=sql_facts;limits=gate._limits(f.contract)
    roles=dict(source=limits,generate=None,platform=limits,trial=limits,per_use=limits)
    with f.store.tx() as c,pb._source_reads(f.store,c):
        with rt._cold_graph_read(f.worker,c,{'same-complete-input':True},roles,'pre') as first:
            first_version=first.content_version()
            with pytest.raises(DomainError),rt._cold_graph_read(f.worker,c,{'same-complete-input':True},roles,'pre') as second:
                assert second.content_version() is not first_version
                assert second.content_version().raw==first_version.raw
                second._pin_journal=first._pin_journal
                second.check(f.store,c)
            assert first.active
            first.check(f.store,c)


def test_nonordinary_instance_dict_is_refused_without_foreign_callbacks(sql_facts):
    calls=[]
    class Foreign(dict):
        def get(self,*a):calls.append('get');return super().get(*a)
        def __contains__(self,*a):calls.append('contains');return super().__contains__(*a)
        def __iter__(self):calls.append('iter');return super().__iter__()
        def pop(self,*a):calls.append('pop');return super().pop(*a)
    with pytest.raises(DomainError),graph_scope(sql_facts) as (graph,limits):
        graph.__dict__=Foreign(graph.__dict__)
        graph.check(sql_facts.store,graph.connection)
    assert not graph.active and calls==[]


@contextmanager
def watch_encoder(action):
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    code=rt._cold_graph_bytes.__code__
    def returned(code,offset,value):action()
    monitor.use_tool_id(slot,'Publication callback adversary at original encoder return')
    try:
        monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        monitor.set_local_events(slot,code,monitor.events.PY_RETURN)
        yield
    finally:
        monitor.set_local_events(slot,code,0)
        monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)


def test_reentrant_add_cannot_republish_old_outer_bytes(sql_facts):
    f=sql_facts;state={'triggered':False};versions_seen=[]
    with pytest.raises(DomainError),graph_scope(f) as (graph,limits):
        previous=graph.content_version()
        def reenter():
            # Only the actual publication encoder, not earlier validation pins.
            if not state['triggered'] and 'outer-root' in graph.inputs:
                state['triggered']=True
                pending=graph.inputs.pop('outer-root')
                try:
                    graph.add('inner-root',{'captured':'inner'})
                    versions_seen.append(graph.content_version())
                finally:graph.inputs['outer-root']=pending
        with watch_encoder(reenter):graph.add('outer-root',{'captured':'outer'})
    assert state['triggered'] and versions_seen and not graph.active
    assert versions_seen[0].sequence==previous.sequence+1


def test_foreign_old_key_is_not_decrefed_inside_publication(sql_facts):
    f=sql_facts;state={'injected':False};destroyed=[]
    class ForeignKey:
        def __del__(self):destroyed.append(True)
    with pytest.raises(DomainError),graph_scope(f) as (graph,limits):
        def poison():
            if not state['injected'] and 'publication-root' in graph.inputs:
                state['injected']=True
                graph.key=ForeignKey()
        with watch_encoder(poison):graph.add('publication-root',{'a':1})
    assert state['injected'] and destroyed==[] and not graph.active
    # Release outside the publisher scope, deliberately retained by the test.
    graph.key=None;gc.collect();assert destroyed==[True]


def test_scope_close_collects_journal_cycles(sql_facts):
    with graph_scope(sql_facts) as (graph,limits):
        graph.add('gc-root',{'full':['value']})
        assert type(graph.content_version()) is versions.VERSION
        reference=weakref.ref(graph)
    del graph
    gc.collect()
    assert reference() is None


@pytest.mark.parametrize('entry',['check','add','export_version'])
@pytest.mark.parametrize('kind',['instance','class'])
def test_new_helper_shadow_refuses_before_dispatch(sql_facts,monkeypatch,entry,kind):
    f=sql_facts;calls=[]
    def foreign(*args,**kwargs):calls.append(True)
    with pytest.raises(DomainError),graph_scope(f) as (graph,limits):
        monkeypatch.setattr(graph if kind=='instance' else rt._ColdGraphRead,
            'content_version',foreign)
        if entry=='check':graph.check(f.store,graph.connection)
        elif entry=='add':graph.add('shadow-root',{'a':1})
        else:graph.export_version()
    assert calls==[] and not graph.active


def test_cleanup_defaults_cannot_redirect_sealed_native_entry(sql_facts,monkeypatch):
    f=sql_facts;calls=[]
    def foreign(*args):calls.append(True)
    with pytest.raises(DomainError),graph_scope(f) as (graph,limits):
        monkeypatch.setattr(rt._ColdGraphRead.invalidate,'__defaults__',(foreign,))
        graph.check(f.store,graph.connection)
    assert calls==[] and not graph.active
    monkeypatch.undo()
    with pytest.raises(DomainError):graph.content_version()


def test_foreign_active_is_retained_without_cleanup_callback(sql_facts):
    calls=[]
    class Foreign:
        def __bool__(self):calls.append('bool');return True
        def __del__(self):calls.append('del')
    with pytest.raises(DomainError),graph_scope(sql_facts) as (graph,limits):
        graph.active=Foreign()
        graph.invalidate()
        assert calls==[]
        graph.content_version()  # C issuer is closed, regardless of foreign flag.
    assert calls==[]
    graph.active=False
    gc.collect()
    assert calls==['del']


def test_declined_graph_still_rejects_new_method_shadow(sql_facts,monkeypatch):
    calls=[]
    def foreign(*args):calls.append(True)
    with monkeypatch.context() as patch:
        patch.setattr(structure,'_qualified',lambda graph,**kw:False)
        with pytest.raises(DomainError),graph_scope(sql_facts) as (graph,limits):
            assert graph.content_version() is None
            graph.content_version=foreign
            graph.check(sql_facts.store,graph.connection)
    assert calls==[] and not graph.active


def test_dead_weak_journal_cannot_revive_or_leave_active_graph(sql_facts):
    with pytest.raises(DomainError),graph_scope(sql_facts) as (graph,limits):
        assert graph.content_version() is not None
        del graph._pin_journal
        vars(graph).pop('_structure_state',None)
        gc.collect()
        graph.check(sql_facts.store,graph.connection)
    assert graph.active is False


@pytest.mark.parametrize('damage',['driver','thread'])
def test_version_binds_original_driver_and_thread(sql_facts,damage):
    with pytest.raises(DomainError),graph_scope(sql_facts) as (graph,limits):
        if damage=='driver':graph.driver=object()
        else:graph.thread=-(1<<200)
        graph.check(sql_facts.store,graph.connection)
    assert not graph.active


def test_frontier_unknown_key_refuses_before_new_keyword_or_callback(sql_facts):
    from test_cold_accounted_native import native_segment
    calls=[]
    with sql_facts.store.tx() as c,native_segment(sql_facts,c) as s:
        frontier=s.graph._accounted_frontier
        frontier.key=lambda:calls.append(True)
        try:
            with pytest.raises(DomainError):frontier.check()
            assert calls==[]
        finally:del frontier.key


def test_native_optional_absence_preserves_original_complete_path(tmp_path):
    import os,subprocess
    code=r'''
import importlib.abc,sys
from pathlib import Path
class MissingNative(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname=='sim2act._cold_graph_structure':raise ImportError('synthetic missing optional graph accelerator')
sys.meta_path.insert(0,MissingNative())
from test_cold_accounted_sqlite import sql_facts
from test_cold_use_manifest_owned import graph_scope
from sim2act.errors import DomainError
from sim2act import _cold_graph_versions as versions
fixture=sql_facts.__wrapped__(Path(sys.argv[1]));f=next(fixture)
try:
 assert versions.AVAILABLE is False
 with graph_scope(f) as (graph,limits):
  assert graph.content_version() is None
  value={'full':['original']};graph.add('original-fallback',value)
  version,raw,key=graph.export_version()
  assert version is None and raw==graph.input_bytes() and key==graph.key
  value['full'].append('mutation')
  try:graph.check(f.store,graph.connection)
  except DomainError:pass
  else:raise AssertionError('Legacy complete mutation gate was lost')
except DomainError:
 assert not graph.active
finally:
 try:next(fixture)
 except StopIteration:pass
print('PASS_OPTIONAL_NATIVE_ABSENCE_ORIGINAL_V2')
'''
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path)],capture_output=True,text=True,timeout=25)
    assert result.returncode==0,(result.stdout,result.stderr)


def test_three_fresh_import_orders_bind_original_reducer():
    import subprocess
    orders=[('sim2act._cold_accounted_values','sim2act.natural_spec_runtime'),
        ('sim2act._cold_accounted_native','sim2act.natural_spec_runtime'),
        ('sim2act.natural_spec_runtime','sim2act._cold_accounted_native')]
    for order in orders:
        code='import importlib\n'+''.join('importlib.import_module('+repr(n)+')\n' for n in order)+r'''
from sim2act import natural_spec_runtime as rt,_cold_accounted_values as values
assert values._ROW_ROLE[0] is rt._cold_graph_row_storage
from sim2act import _cold_graph_versions as versions
assert versions.AVAILABLE and versions._REGISTERED
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
        assert result.returncode==0,(order,result.stdout,result.stderr)
