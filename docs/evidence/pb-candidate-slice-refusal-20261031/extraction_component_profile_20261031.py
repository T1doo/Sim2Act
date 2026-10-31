"""Passive exact fixture observer; no replaced product function or virtual time."""
import hashlib,json,sys,time,weakref,importlib.util
from pathlib import Path
import pytest
@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
 if item.name!='test_plain_pb_first_binding_producer_equals_public_complete_ancestry':yield;return
 from sim2act import natural_spec_runtime as r,_cold_source_packet as owned,_cold_graph_structure_guard as structural
 path=next(Path('/workspace/scratch/use-effective-shape-20261031').glob('*.so'))
 ds=importlib.util.spec_from_file_location('_extraction_shape._cold_graph_structure',path);diag=importlib.util.module_from_spec(ds);ds.loader.exec_module(diag)
 assert diag.SOURCE_SHA256==hashlib.sha256(path.with_name('_cold_graph_structure.c').read_bytes()).hexdigest()
 production=Path(r.__file__).with_name('_cold_graph_structure.c').read_text();diagnostic=path.with_name('_cold_graph_structure.c').read_text()
 for suffix in ('Entry;','Map;','Encoder;','Node;','Tree;'):
  assert next(x for x in production.splitlines() if x.startswith('typedef struct') and x.endswith(suffix))==next(x for x in diagnostic.splitlines() if x.startswith('typedef struct') and x.endswith(suffix))
 monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
 init=r._ColdGraphRead.__init__.__code__;encode=r._cold_graph_bytes.__code__;publish=owned.own_fact.__code__
 select=structural.select.__code__;frontier=structural.select_frontier.__code__
 graphs={};rows=[];factories=[];errors=[];shape_maps={};shapes=[]
 def start(code,offset):
  try:
   f=sys._getframe(1);inputs=f.f_locals['inputs'];ordinal=len(rows)+1
   rows.append(dict(graph=ordinal,phase=f.f_locals['phase'],encodings=0,encoded_bytes=0));graphs[id(inputs)]=ordinal
  except Exception as e:errors.append(type(e).__name__)
 def end(code,offset,value):
  try:
   f=sys._getframe(1)
   if code is encode:
    values=f.f_locals['values'];inputs=values.get('inputs') if type(values) is dict else None;ordinal=graphs.get(id(inputs))
    if ordinal is not None and type(value) is bytes:rows[ordinal-1]['encodings']+=1;rows[ordinal-1]['encoded_bytes']+=len(value)
   elif code is publish:
    name=f.f_locals['name']
    if name.endswith(':review:inputs:candidate'):
     row=dict(name=name,is_view=type(value) is owned.image.View)
     if row['is_view']:
      data=owned.native.owned_data(value.owner());row.update(owned_nodes=len(data[1]),boundary_anchors=len(data[3]))
     factories.append(row)
   elif code in (select,frontier) and value is True:
    graph=f.f_locals.get('graph');state=f.f_locals.get('state');scope=f.f_locals.get('scope')
    if graph is None or state is None or state.capsule is None:return
    ordinal=graphs.get(id(graph.inputs));key=(id(graph),scope[2],code is frontier)
    entry=shape_maps.get(key)
    if entry is None:
     entry=dict(graph=ordinal,phase=graph.phase,frontier=code is frontier,calls=0,shape=diag.shape(state.capsule));shape_maps[key]=entry;shapes.append(entry)
    entry['calls']+=1
  except Exception as e:errors.append(type(e).__name__)
 monitor.use_tool_id(slot,'Matched extraction binding default-path counts');a=time.monotonic();cpu=time.thread_time()
 try:
  monitor.register_callback(slot,monitor.events.PY_START,start);monitor.register_callback(slot,monitor.events.PY_RETURN,end)
  monitor.set_local_events(slot,init,monitor.events.PY_START)
  for c in (encode,publish,select,frontier):monitor.set_local_events(slot,c,monitor.events.PY_RETURN)
  yield
 finally:
  for c in (init,encode,publish,select,frontier):monitor.set_local_events(slot,c,0)
  monitor.register_callback(slot,monitor.events.PY_START,None);monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
  result=dict(classification='DEFAULT_ORIGINAL_FIVE_MOCK_TWO_INDEPENDENT_BINDINGS_NOT_COLD_SETTLEMENT',seconds=time.monotonic()-a,owner_thread_seconds=time.thread_time()-cpu,graphs=rows,factories=factories,shapes=shapes,errors=errors,profiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),runtime_module=r.__file__,limits='Count observer overhead included. Same fixture/hashseed/interpreter/binaries/observer; real UUIDs/time differ. No business clock substitution; no Cold commit/live/PG/Windows/SLA claim.')
  (item.funcargs['tmp_path']/'extraction-component-profile.json').write_text(json.dumps(result,indent=2)+'\n')
