import dis,gc,importlib.util,json,signal,sys
from pathlib import Path
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import quoted_name
from sim2act import natural_spec_runtime as r
from sim2act.contracts import Limits
root=Path('/workspace/scratch/graph-edge-candidate-20261030')
def load(name):
 p=next((root/name).glob('*.so'));s=importlib.util.spec_from_file_location('_signal_'+name+'._cold_graph_structure',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
args=(RowMapping,Limits,quoted_name,r._cold_graph_row_storage,r._cold_graph_limit_values);scope=(object(),object(),'owned-signal-proof',0,'post')
def limit():return Limits(max_requests=2,max_tools=4,max_repairs=0,max_total_tokens=64000,max_output_tokens=1024,run_seconds=300)
def run_match(m,c,v,s):return m.matches_fast(c,v,s)
call_offset=next(i.offset for i in dis.get_instructions(run_match) if i.opname=='CALL')
results={}
for name in ('baseline','candidate'):
 m=load(name);shared={'v':[1]};other={'v':[1]};model=limit();v=[shared,model,other];cap=m.snapshot(v,*args,scope)
 previous=signal.signal(signal.SIGUSR1,lambda signum,frame:v.__setitem__(2,shared));original=r._cold_graph_limit_values
 def change(obj):signal.raise_signal(signal.SIGUSR1);return original(obj)
 r._cold_graph_limit_values=change
 try:assert m.matches_fast(cap,v,scope) is False
 finally:r._cold_graph_limit_values=original;signal.signal(signal.SIGUSR1,previous);v[2]=other
 assert m.matches_fast(cap,v,scope) is True
 # Repeated memo hits must STILL dispatch real pending signals.
 v=['synthetic immutable repeated memo']*100000;cap=m.snapshot(v,*args,scope);refs=sys.getrefcount(v);events=[]
 def raised(signum,frame):
  events.append(dict(in_match_frame=frame.f_code is run_match.__code__,offset=frame.f_lasti,expected_call_offset=call_offset))
  raise RuntimeError('Owned comparator signal checkpoint')
 previous=signal.signal(signal.SIGALRM,raised);observed=False
 try:
  for _ in range(5):
   try:
    signal.setitimer(signal.ITIMER_REAL,.0001)
    run_match(m,cap,v,scope)
   except RuntimeError as error:
    assert str(error)=='Owned comparator signal checkpoint'
   finally:signal.setitimer(signal.ITIMER_REAL,0)
   if events and events[-1]['in_match_frame'] and events[-1]['offset']>=call_offset:
    observed=True;break
  assert observed,events
 finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
 gc.collect();assert sys.getrefcount(v)==refs
 assert m.matches_fast(cap,v,scope) is True
 results[name]=dict(signal_changes_later_alias='REJECTED_THEN_REUSABLE',memo_signal_events=events,cleanup_refcounts_unchanged=True)
(root/'signal-check.json').write_text(json.dumps(dict(status='PASS',classification='REAL_OWN_PROCESS_POSIX_SIGNALS_DIFFERENTIAL_NO_MODEL_CALLS',results=results),indent=2)+'\n');print(json.dumps(results))
