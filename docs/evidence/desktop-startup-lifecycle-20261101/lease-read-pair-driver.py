import sys,time,json,types,statistics
from pathlib import Path
sys.path.insert(0,'/workspace/Sim2Act/tests')
from conftest import env
from test_authoritative_commit_flow import owner
from sim2act import _lease_control as control
from sim2act import _lease_control_runtime as adapter
root=Path('/workspace/scratch/lease-single-read-benchmark-20261101');root.mkdir(exist_ok=False)
fixture=env.__wrapped__(root);data=next(fixture)
try:
 store,runtime,row,stop=owner(data)
 seen=set();codes=set()
 def collect(fn):
  if not isinstance(fn,types.FunctionType) or id(fn) in seen:return
  seen.add(id(fn))
  if fn.__code__.co_name=='connection' and fn.__code__.co_flags & 32:codes.add(fn.__code__)
  for cell in fn.__closure__ or ():
   try:collect(cell.cell_contents)
   except ValueError:pass
 collect(control.Authority.connection);assert len(codes)==1
 slot=next(i for i in (3,4,5) if sys.monitoring.get_tool(i) is None);sys.monitoring.use_tool_id(slot,'lease-read-count')
 count=[0]
 def started(code,offset):count[0]+=1
 sys.monitoring.register_callback(slot,sys.monitoring.events.PY_START,started)
 for code in codes:sys.monitoring.set_local_events(slot,code,sys.monitoring.events.PY_START)
 results=[]
 try:
  for label in ['old','new','new','old']:
   count[0]=0;wall=time.perf_counter();cpu=time.process_time()
   for _ in range(30):
    got=adapter.Runtime.session(runtime,row).check() if label=='old' else adapter.Runtime.lease(runtime,row)
    assert got==runtime.authority.session(row).wall
   results.append({'path':label,'calls':30,'control_connections':count[0],'wall_seconds':time.perf_counter()-wall,'cpu_seconds':time.process_time()-cpu})
 finally:
  for code in codes:sys.monitoring.set_local_events(slot,code,0)
  sys.monitoring.register_callback(slot,sys.monitoring.events.PY_START,None);sys.monitoring.free_tool_id(slot)
 assert all(r['control_connections']==(60 if r['path']=='old' else 30) for r in results)
 report={'classification':'REAL_FILE_SQLITE_CONTROL_CALL_PAIR_NOT_LARGE_FLOW','results':results,'models':0}
 (root/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
 try:next(fixture)
 except StopIteration:pass
