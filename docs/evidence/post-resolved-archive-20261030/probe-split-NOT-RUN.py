"""Passive return counters only. No callee, data, clock or SQL replacement."""
import importlib.util,json,sys,weakref
from pathlib import Path
import pytest

@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
 if item.name!='test_same_large_cold_snapshot_control[complete]':
  yield;return
 from sim2act import natural_spec_runtime as r,natural_live_admission as gate,_cold_graph_structure_guard as g,_cold_archive_packet as a
 from sim2act._sqlite_run_control import active_epochs
 path=next(Path('/workspace/scratch/graph-shape-diagnostic-20261030').glob('*.so'))
 spec=importlib.util.spec_from_file_location('_shape_diagnostic._cold_graph_structure',path);diag=importlib.util.module_from_spec(spec);spec.loader.exec_module(diag)
 epochs=weakref.WeakKeyDictionary();graphs=weakref.WeakKeyDictionary();records=[];totals={}
 target={r._ColdGraphRead.input_bytes.__code__:'input_bytes',g.select.__code__:'select',
  g.select_frontier.__code__:'select_frontier',gate._trial_typed_values.__code__:'typed_values',
  a.capture.__code__:'archive_capture',a.read.__code__:'archive_read',a.bound.__code__:'archive_bound'}
 monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
 def returned(code,offset,value):
  live=[e for s,e in active_epochs() if s.engine.url.database==item.funcargs['env'][0].engine.url.database and not e.closed]
  if not live:return
  assert len(live)==1
  epoch=live[0]
  if epoch not in epochs:epochs[epoch]=len(epochs)+1
  ordinal=epochs[epoch];name=target[code]
  key=(ordinal,epoch.phase,name);row=totals.setdefault(key,dict(calls=0,total_bytes=0));row['calls']+=1
  if name=='input_bytes':
   label='bytes_returns' if type(value) is bytes else 'dict_projection_returns' if type(value) is dict else 'other_returns'
   row[label]=row.get(label,0)+1
  if name=='input_bytes' and type(value) is bytes:row['total_bytes']+=len(value)
  if name=='archive_capture' and a.is_packet(value):
   row['metadata_bytes']=len(value[1]);row['immutable_leaves']=len(value[2])
  if name not in ('select','select_frontier') or value is not True:return
  frame=sys._getframe(1);assert frame.f_code is code
  graph=frame.f_locals.get('graph');state=frame.f_locals.get('state');scope=frame.f_locals.get('scope')
  if graph is None or state is None or state.capsule is None:return
  by_scope=graphs.setdefault(graph,{})
  shape_key=(ordinal,epoch.phase,scope[2],name)
  record=by_scope.get(shape_key)
  if record is None:
   record=dict(epoch=ordinal,phase=epoch.phase,selector=name,calls=0,
    archive_present=a.KEY in graph.inputs,shape=diag.shape(state.capsule))
   by_scope[shape_key]=record;records.append(record)
  record['calls']+=1
 monitor.use_tool_id(slot,'Post archive actual passive counts')
 try:
  monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
  for code in target:monitor.set_local_events(slot,code,monitor.events.PY_RETURN)
  yield
 finally:
  for code in target:monitor.set_local_events(slot,code,0)
  monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
  (item.funcargs['tmp_path']/'archive-actual-counts.json').write_text(json.dumps(dict(
   classification='ACTUAL_ORIGINAL_LARGE_COLD_PASSIVE_COUNTS_NO_EXTRA_COMPARISONS',
   totals=[dict(epoch=k[0],phase=k[1],name=k[2],**v) for k,v in totals.items()],shapes=records,
   limits='Observer overhead included, no extra comparison. Native shape reader only reads Tree metadata; unchanged native C ABI. input_bytes counts exclude other direct codec paths. No content or authority cached/saved.'),indent=2)+'\n')
