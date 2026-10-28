"""Complete Graph.check cost including current projection/qualification/dynamics."""
import hashlib,json,pickle,statistics,time,sys
from pathlib import Path
from test_cold_extract_parse import local_origin as local_origin,no_external_transport as no_external_transport
from test_loaded_raw_segment import scope
from sim2act import natural_spec_runtime as r,pb_natural_specs as pb
from sim2act import _cold_graph_structure_guard as code

def test_complete_scope_cost(local_origin,monkeypatch):
 f=local_origin
 # Own synthetic capture only. Ordinary pickle reconstructs aliases differently,
 # so the benchmark explicitly does not claim the original G1 object graph.
 background=pickle.loads(Path('/workspace/scratch/actual-g1-graph/values-own-synthetic.pickle').read_bytes())
 source=Path(r.__file__);batches=[];dynamic=[]
 monitoring=sys.monitoring;slot=next(i for i in (4,3,5) if monitoring.get_tool(i) is None);monitoring.use_tool_id(slot,'complete scope cost dynamic witness')
 monitoring.register_callback(slot,monitoring.events.PY_START,lambda *a:dynamic.append(1));monitoring.set_local_events(slot,r._ColdGraphRead._check_dynamic.__code__,monitoring.events.PY_START)
 try:
  with f.store.tx() as c,pb._source_reads(f.store,c),scope(f,c) as graph:
   graph.add('complete-synthetic-background',background)
   for _ in range(5):graph.check(f.store,c)
   assert vars(graph)['_structure_state'].capsule is not None
   graph_bytes=len(graph.input_bytes())
   for batch in range(5):
    row={}
    for name in ('fast','legacy') if batch%2==0 else ('legacy','fast'):
     with monkeypatch.context() as patch:
      if name=='legacy':patch.setattr(code,'select',lambda graph:None)
      start=time.perf_counter();pins=graph._diagnostic_counts[1];current_dynamic=len(dynamic)
      for _ in range(100):graph.check(f.store,c)
      row[name]=dict(seconds=time.perf_counter()-start,full_encodes=graph._diagnostic_counts[1]-pins,dynamic_checks=len(dynamic)-current_dynamic)
    batches.append(row)
   report=dict(classification='COMPLETE_GRAPH_CHECK_RECONSTRUCTED_SYNTHETIC_BACKGROUND_NOT_FULL_CHAIN_NOT_ORIGINAL_G1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),native_sha256=hashlib.sha256(Path(code.native.__file__).read_bytes()).hexdigest(),graph_bytes=graph_bytes,batches=batches,median_fast=statistics.median(x['fast']['seconds'] for x in batches),median_legacy=statistics.median(x['legacy']['seconds'] for x in batches))
   assert all(x['fast']['full_encodes']==0 and x['fast']['dynamic_checks']==100 and x['legacy']['full_encodes']==100 and x['legacy']['dynamic_checks']==100 for x in batches)
   import cProfile,pstats
   profiler=cProfile.Profile();profiler.enable()
   for _ in range(100):graph.check(f.store,c)
   profiler.disable()
   with open('/workspace/scratch/structure-cost-profile.txt','w') as output:pstats.Stats(profiler,stream=output).sort_stats('cumtime').print_stats(25)
   Path('/workspace/scratch/complete-structure-cost.json').write_text(json.dumps(report,indent=2)+'\n')
 finally:
  monitoring.set_local_events(slot,r._ColdGraphRead._check_dynamic.__code__,0);monitoring.free_tool_id(slot)
