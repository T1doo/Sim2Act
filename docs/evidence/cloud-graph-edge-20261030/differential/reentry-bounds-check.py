import gc,importlib.util,json,signal,sys
from pathlib import Path
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import quoted_name
from sim2act import natural_spec_runtime as r
from sim2act.contracts import Limits
root=Path('/workspace/scratch/graph-edge-candidate-20261030')
def load(name):
 p=next((root/name).glob('*.so'));s=importlib.util.spec_from_file_location('_boundary_'+name+'._cold_graph_structure',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
args=(RowMapping,Limits,quoted_name,r._cold_graph_row_storage,r._cold_graph_limit_values);scope=(object(),object(),'boundary-proof',0,'post');modules=[load(n) for n in ('baseline','candidate')]
results={}
for m,name in zip(modules,('baseline','candidate')):
 v=['synthetic memo']*100000;cap=m.snapshot(v,*args,scope);nested=[];refs=sys.getrefcount(v)
 def reenter(signum,frame):nested.append(m.matches_fast(cap,v,scope))
 previous=signal.signal(signal.SIGALRM,reenter)
 try:
  signal.setitimer(signal.ITIMER_REAL,.0001)
  assert m.matches_fast(cap,v,scope) is True
  assert nested==[True]
 finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
 gc.collect();assert sys.getrefcount(v)==refs
 results[name]=dict(real_signal_reentrant_same_capsule=True,refcounts_unchanged=True)
checks=[]
for depth in (63,64,65):
 v=1
 for _ in range(depth):v=[v]
 row=[]
 for m in modules:
  cap=m.snapshot(v,*args,scope)
  row.append('UNSUPPORTED' if cap is m.UNSUPPORTED else m.matches_fast(cap,v,scope))
 assert row[0]==row[1];checks.append(dict(depth=depth,results=row))
for length in (99998,99999,100000):
 v=list(range(length));row=[]
 for m in modules:
  cap=m.snapshot(v,*args,scope);row.append('UNSUPPORTED' if cap is m.UNSUPPORTED else m.matches_fast(cap,v,scope))
 assert row[0]==row[1];checks.append(dict(unique_node_input_length=length,results=row))
for length in (999998,999999,1000000):
 v=['synthetic memo']*length;row=[]
 for m in modules:
  cap=m.snapshot(v,*args,scope);row.append('UNSUPPORTED' if cap is m.UNSUPPORTED else m.matches_fast(cap,v,scope))
 assert row[0]==row[1];checks.append(dict(edge_input_length=length,results=row))
result=dict(status='PASS',classification='REAL_SIGNAL_REENTRY_AND_ORIGINAL_RESOURCE_BOUNDARY_DIFFERENTIAL_NO_MODEL_CALLS',reentry=results,boundaries=checks)
(root/'reentry-bounds-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
