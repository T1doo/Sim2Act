"""Single complete G1 under explicit virtual business time; CPU diagnosis only."""
import hashlib,json,sys,threading,time
from pathlib import Path
import pytest
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import MockCap,build_prefix,restore_case,close_case
from cold_semantic_clock import SemanticClock
from test_cold_configured_semantic_tail import TailStop
from sim2act import natural_spec_runtime as r,natural_live_admission as gate,pa_spec_apps as spec,pa_trial_dispatch as dispatch,_cold_graph_structure_guard as structure,natural_specs as natural
from sim2act.db import attempts,operations
from sqlalchemy import select
from sqlalchemy.engine import Connection

def test_one_original_g1_breakdown(tmp_path,monkeypatch):
 clock=SemanticClock(monkeypatch);cap=MockCap(monkeypatch);cap.exchange_limit,cap.method_limit=6,8;threads=set(threading.enumerate())
 with monkeypatch.context() as patch:template=build_prefix(tmp_path/'prefix',patch,clock,cap)
 with monkeypatch.context() as patch:
  case=restore_case(template,tmp_path/'case',patch,clock);case.store._enable_local_model_snapshots();cap.new_case()
  targets={fn.__code__:name for fn,name in [(r._ColdTrialGraph._prepare,'prepare'),(r._ColdTrialGraph.commit,'trial.commit'),(r._cold_audit_seed,'audit.seed'),(r._cold_first_binding,'first.binding'),(r._cold_binding_limits_facet,'binding.facet'),(r._ColdGraphRead.check,'graph.check'),(r._ColdGraphRead._check_dynamic,'graph.dynamic'),(r._cold_graph_bytes,'graph.bytes'),(structure.select,'structure.select'),(structure.select_frontier,'structure.frontier'),(gate._trial_typed_values,'typed.values'),(spec._cold_receipts,'receipts'),(dispatch._graph_journal_chain,'journal.chain'),(r._ModelSettlementRead.check,'proof.check'),(r._ModelSettlementRead.live,'proof.live'),(Connection.execute,'sql.execute'),(Connection.commit,'sql.commit'),(natural.expand,'pure.expand'),(natural.compile_candidate,'pure.compile')]}
  outer=r._model_settlement_read.__wrapped__.__code__;advance=r.advance_model.__code__;targets[outer]='whole.G1'
  monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None);thread=threading.get_ident();active=False;closed=False;stack=[];rows={};errors=[];started=None
  def start(code,offset):
   nonlocal active,started
   if threading.get_ident()!=thread:return
   if code is outer:
    assert not active;active=True;started=time.monotonic()
   if active and code in targets:stack.append([id(sys._getframe(1)),targets[code],time.monotonic_ns(),time.thread_time_ns(),0,0])
  def end(code,offset,value=None):
   nonlocal active,closed
   if threading.get_ident()!=thread:return
   f=sys._getframe(1)
   if code in targets and active:
    if not stack or stack[-1][0]!=id(f):errors.append('unmatched:'+targets[code]);return
    _,name,a,c,child,childcpu=stack.pop();wall=time.monotonic_ns()-a;cpu=time.thread_time_ns()-c
    row=rows.setdefault(name,dict(calls=0,inclusive_wall_ns=0,exclusive_wall_ns=0,inclusive_thread_ns=0,exclusive_thread_ns=0));row['calls']+=1;row['inclusive_wall_ns']+=wall;row['exclusive_wall_ns']+=wall-child;row['inclusive_thread_ns']+=cpu;row['exclusive_thread_ns']+=cpu-childcpu
    if stack:stack[-1][4]+=wall;stack[-1][5]+=cpu
    if code is outer:
     proof=f.f_locals['proof'];assert proof is not None and proof.state=='CLOSED' and not proof.active;closed=True
   if code is advance and active and closed:
    assert value is True;active=False;raise TailStop()
  monitor.use_tool_id(slot,'One complete G1 CPU structure diagnostic; explicit virtual business time')
  try:
   monitor.register_callback(slot,monitor.events.PY_START,start);monitor.register_callback(slot,monitor.events.PY_RETURN,end)
   for code in targets:monitor.set_local_events(slot,code,monitor.events.PY_START|monitor.events.PY_RETURN)
   monitor.set_local_events(slot,advance,monitor.events.PY_RETURN)
   worker=case.factory(case.store,case.data[1],goal_planner_transport=apps.transport([],apps.COLD))
   with pytest.raises(TailStop):worker.once()
   assert closed and not active and not errors and not stack
   assert (cap.exchanges,cap.methods,cap.case_exchanges,cap.case_methods)==(6,8,1,1)
   assert len(case.store._local_model_snapshot_records)==1 and case.store._local_model_snapshot_records[0]['outcome']=='COMMITTED'
   with case.store.tx() as c:
    actual=[dict(v) for v in c.execute(select(attempts).where(attempts.c.run_id==template.cold_id)).mappings()]
    ops=[dict(v) for v in c.execute(select(operations).where(operations.c.run_id==template.cold_id)).mappings()]
   assert len(actual)==1 and actual[0]['status']=='VERIFIED'
   assert any(v['status']=='VERIFIED' and v['receipt'] is not None for v in ops)
  finally:
   for code in (*targets,advance):monitor.set_local_events(slot,code,0)
   monitor.register_callback(slot,monitor.events.PY_START,None);monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
   (tmp_path/'g1-structure-profile.json').write_text(json.dumps(dict(classification='ONE_ORIGINAL_G1_VIRTUAL_BUSINESS_CLOCK_CPU_DIAGNOSIS_NOT_LEASE_EVIDENCE',timings=rows,errors=errors,open_stack=len(stack),closed=closed,active=active,mock_exchanges=cap.exchanges,real_model_calls=0,profiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limits='Original business and graph callees unchanged. Synthetic source/environment/software fixture substitutes and virtual time explicit. One Cold only, stop after original transaction return. Passive observer overhead included; exclusive is only among targets.'),indent=2)+'\n')
   close_case(case,clock)
 assert not any(t.is_alive() for t in threading.enumerate() if t not in threads)
