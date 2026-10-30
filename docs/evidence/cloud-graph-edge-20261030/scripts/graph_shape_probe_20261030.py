"""Test-only passive counters on real current graph objects; no saved input."""
import importlib.util,json,sys,time,weakref
from pathlib import Path
import pytest

@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    if item.name!='test_original_large_cold_scoped_profile':
        yield
        return
    from sim2act import natural_spec_runtime as r,_cold_graph_structure_guard as g
    path=next(Path('/workspace/scratch/graph-shape-diagnostic-20261030').glob('*.so'))
    spec=importlib.util.spec_from_file_location('_shape_diagnostic._cold_graph_structure',path)
    diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
    records=[];graphs=weakref.WeakKeyDictionary();epochs=weakref.WeakKeyDictionary();encodings={}
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    code=r._ColdGraphRead.input_bytes.__code__
    selectors={g.select.__code__,g.select_frontier.__code__}
    def selected(graph):
        if type(graph) is not r._ColdGraphRead or not graph.store._local_model_snapshots:return
        control=graph.store._local_model_control
        return getattr(control.local,'epoch',None) if control is not None else None
    def returned(c,offset,value):
        frame=sys._getframe(1);assert frame.f_code is c
        local=frame.f_locals;graph=local.get('self') if c is code else local.get('graph')
        epoch=selected(graph)
        if epoch is None:return
        if epoch not in epochs:epochs[epoch]=len({row['epoch'] for row in records})+1
        ordinal=epochs[epoch]
        if c is code:
            if type(value) is bytes:
                rec=encodings.setdefault((ordinal,epoch.phase),dict(calls=0,total_bytes=0,min_bytes=len(value),max_bytes=0))
                rec['calls']+=1;rec['total_bytes']+=len(value);rec['min_bytes']=min(rec['min_bytes'],len(value));rec['max_bytes']=max(rec['max_bytes'],len(value))
            return
        if value is not True:return
        state=local.get('state');scope=local.get('scope')
        if state is None or state.capsule is None:return
        if graph not in graphs:graphs[graph]={}
        key=(scope[2],c.co_name,epoch.phase)
        entry=graphs[graph].get(key)
        if entry is None:
            entry=dict(epoch=ordinal,phase=epoch.phase,graph_phase=graph.phase,selector=c.co_name,calls=0,shape=diag.shape(state.capsule))
            if c is g.select.__code__:
                current=local.get('current');assert type(current) is dict
                started=time.monotonic();entry['sample_comparison']=diag.matches_fast(state.capsule,current,scope);entry['sample_comparison_seconds']=time.monotonic()-started
                assert entry['sample_comparison']['match'] is True
            graphs[graph][key]=entry;records.append(entry)
        entry['calls']+=1
    monitor.use_tool_id(slot,'Owned actual Cold shape counters')
    try:
        monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        for c in selectors|{code}:monitor.set_local_events(slot,c,monitor.events.PY_RETURN)
        yield
    finally:
        for c in selectors|{code}:monitor.set_local_events(slot,c,0)
        monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
        root=item.funcargs['tmp_path']
        (root/'actual-graph-shapes.json').write_text(json.dumps(dict(classification='ACTUAL_ORIGINAL_LARGE_RUNTIME_GRAPH_DIAGNOSTIC_NOT_AUTHORITY',records=records,encodings=[dict(epoch=k[0],phase=k[1],**v) for k,v in encodings.items()],limitations='Extra diagnostic comparison once per observed shape included in elapsed business clock. Native allocation bytes are sampled requested bytes, not measured allocator wall time. No graph/input values saved; weak graph/epoch keys only.'),indent=2)+'\n')
