"""Passive two-epoch real binding component; no changed callee/SQL/clock."""
import hashlib,json,sys,threading,time
from pathlib import Path
import pytest
@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
 if item.name!='test_plain_pb_first_binding_producer_equals_public_complete_ancestry':yield;return
 from sim2act import natural_spec_runtime as r,natural_specs as natural,natural_live_admission as gate,_cold_graph_structure_guard as structure
 from sqlalchemy.engine import Connection
 thread=threading.get_ident();monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
 targets={fn.__code__:name for fn,name in [(r._ColdGraphRead.check,'graph.check'),(r._cold_graph_bytes,'graph.bytes'),(structure.select,'structure.select'),(structure.select_frontier,'structure.frontier'),(gate._trial_typed_values,'typed.values'),(natural.expand,'pure.expand'),(natural.compile_candidate,'pure.compile'),(r._cold_first_binding,'first_binding'),(r._cold_binding_limits_facet,'binding_facet'),(Connection.execute,'sql.execute')]}
 init=r._ColdGraphRead.__init__.__code__;invalidate=r._ColdGraphRead.invalidate.__code__;graphs={};rows=[];active=None;stack=[];errors=[]
 def start(code,offset):
  nonlocal active
  if threading.get_ident()!=thread:return
  f=sys._getframe(1)
  if code is init:
   active=len(rows);graphs[id(f.f_locals['self'])]=active;rows.append(dict(phase=f.f_locals['phase'],timings={}))
  if code in targets and active is not None:stack.append([id(f),active,targets[code],time.monotonic_ns(),time.thread_time_ns(),0,0])
 def end(code,offset,value=None):
  nonlocal active
  if threading.get_ident()!=thread:return
  f=sys._getframe(1)
  if code in targets and active is not None:
   if not stack or stack[-1][0]!=id(f):errors.append('unmatched-return:'+targets[code]);return
   _,ordinal,name,a,c,child,childcpu=stack.pop();wall=time.monotonic_ns()-a;cpu=time.thread_time_ns()-c
   row=rows[ordinal]['timings'].setdefault(name,dict(calls=0,inclusive_wall_ns=0,exclusive_wall_ns=0,inclusive_thread_ns=0,exclusive_thread_ns=0))
   row['calls']+=1;row['inclusive_wall_ns']+=wall;row['exclusive_wall_ns']+=wall-child;row['inclusive_thread_ns']+=cpu;row['exclusive_thread_ns']+=cpu-childcpu
   if stack:stack[-1][5]+=wall;stack[-1][6]+=cpu
  if code is invalidate and graphs.get(id(f.f_locals['self']))==active:active=None
 monitor.use_tool_id(slot,'Bounded component pure-computation vs graph-work profile');a=time.monotonic()
 try:
  monitor.register_callback(slot,monitor.events.PY_START,start);monitor.register_callback(slot,monitor.events.PY_RETURN,end)
  for code in (*targets,init):monitor.set_local_events(slot,code,monitor.events.PY_START | (monitor.events.PY_RETURN if code in targets else 0))
  monitor.set_local_events(slot,invalidate,monitor.events.PY_RETURN)
  yield
 finally:
  for code in (*targets,init,invalidate):monitor.set_local_events(slot,code,0)
  monitor.register_callback(slot,monitor.events.PY_START,None);monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
  (item.funcargs['tmp_path']/'lock-structure-component-profile.json').write_text(json.dumps(dict(classification='REAL_ORIGINAL_FIVE_FIXED_MOCK_PRE_POST_BINDING_COMPONENT_NOT_FULL_G1',seconds=time.monotonic()-a,graphs=rows,errors=errors,open_stack=len(stack),profiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limits='Same original component and full ancestry oracle. Passive observer overhead included. Nested inclusive times cannot be added; exclusive only among named targets. Small component not Cold transaction or live/PG/Windows evidence.'),indent=2)+'\n')
