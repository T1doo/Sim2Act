"""Read-only synthetic failed-DB background; local cost, never acceptance."""
from pathlib import Path
import hashlib,json,time,statistics
from sqlalchemy import create_engine,select,event
from test_cold_binding_fact_leaves import local_origin,no_external_transport
from test_counter_loaded_segment import prepared,observe_core
from test_loaded_raw_segment import scope
from sim2act import natural_spec_runtime as r,pb_natural_specs as pb,db


def test_cost(local_origin,monkeypatch):
 f=local_origin
 source=Path('/workspace/scratch/seed-real-clock-89b928d5/test_pb_production_original_so0/fixture.db')
 e=create_engine('sqlite:///file:'+str(source)+'?mode=ro&uri=true')
 background={}
 with e.connect() as c:
  for table in db.meta.tables.values():
   rows=c.execute(select(table)).mappings().all()
   if rows:background[table.name]=rows
 e.dispose()
 f.inputs['read_only_synthetic_failed_fixture']=background
 results=[];queries=[]
 with f.store.tx() as c,pb._source_reads(f.store,c),scope(f,c) as g:
  facts,seed=prepared(f,c,g,count=2,marker=True)
  with observe_core() as calls:expected=r._counters(c,facts.job,f.origin[0],_facts=facts)
  assert calls==[1]
  footprint=len(r._cold_graph_bytes(dict(inputs=g.inputs,role_limits=g.role_limits,phase=g.phase)))
  def sql(*args):queries.append(args[2])
  event.listen(f.store.engine,'before_cursor_execute',sql)
  try:
   for label in ['fast','legacy','legacy','fast','fast','legacy']:
    with monkeypatch.context() as patch:
     if label=='legacy':patch.setattr(r,'_cold_counter_loaded',lambda *a:r._RAW_READ_MISS)
     before=g._diagnostic_counts[1];started=time.perf_counter()
     for _ in range(10):
      rows=r._counters(c,facts.job,f.origin[0],_facts=facts)
      assert all(a is b for a,b in zip(rows,expected,strict=True))
     elapsed=time.perf_counter()-started
     results.append(dict(path=label,calls=10,seconds=elapsed,complete_pins=g._diagnostic_counts[1]-before))
  finally:event.remove(f.store.engine,'before_cursor_execute',sql)
 assert queries==[]
 report=dict(classification='LOCAL_COUNTER_SEGMENT_REAL_CLOCK_SYNTHETIC_READONLY_FAILED_DB_BACKGROUND_NOT_FULL_ACCEPTANCE',rows=2,marker=True,background_tables=len(background),graph_payload_bytes=footprint,source_fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),runtime_sha256=hashlib.sha256(Path(r.__file__).read_bytes()).hexdigest(),batches=results,sql_calls=len(queries),row_identity_unchanged=True)
 report['median_fast_seconds']=statistics.median(x['seconds'] for x in results if x['path']=='fast')
 report['median_legacy_seconds']=statistics.median(x['seconds'] for x in results if x['path']=='legacy')
 Path('/workspace/scratch/counter-packet-cost.json').write_text(json.dumps(report,indent=2)+'\n')
