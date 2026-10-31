"""One real synthetic W5/post endpoint shadow; original G1 remains the oracle.

Explicit virtual business time: never real-clock performance/lease acceptance.
Whole-DB diagnostic reads are restricted to this new synthetic test database.
"""
import hashlib,json,sys,threading,time
from pathlib import Path
import pytest
from sqlalchemy import event,select
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import MockCap,build_prefix,restore_case,close_case
from cold_semantic_clock import SemanticClock
from test_cold_configured_semantic_tail import TailStop
from sim2act import natural_spec_runtime as runtime,_sqlite_model_snapshot as snapshot
from sim2act.db import attempts
from sim2act._immutable_settlement import OwnedValue
from sim2act._owned_sqlite import _CATALOG
from tools.expected_post_prototype.plan import Context,Decline,Observation,schema

def test_one_actual_w5_shadow_and_complete_g1(tmp_path,monkeypatch):
 clock=SemanticClock(monkeypatch);cap=MockCap(monkeypatch);cap.exchange_limit,cap.method_limit=6,8;threads=set(threading.enumerate())
 with monkeypatch.context() as patch:template=build_prefix(tmp_path/'prefix',patch,clock,cap)
 with monkeypatch.context() as patch:
  case=restore_case(template,tmp_path/'case',patch,clock);case.store._enable_local_model_snapshots();cap.new_case()
  assert case.store.test_only and case.store.sqlite and Path(case.store.engine.url.database).is_relative_to(tmp_path)
  state=dict(captured=False,w5_end=False,oracle_ready=False,oracle_closed=False,active=False,pending=None,listeners=False,result=None,timings={})
  observed=None;selected=None;worker=None
  def inputs(frame):return {k:frame.f_locals[k] for k in ('raw','wire','meta','response')}
  def context(c,job):
   token=vars(worker).get('_settlement_interval')
   if type(token) is not tuple or len(token)!=2:raise Decline('original finite settlement token required')
   return Context(job['worker_id'],job['version'],c.info.get('source_proof_write_epoch',0),job['fence'],token[0],token[1],bool(job['cancel_intent']),False)
  def decline(error):
   state['result']={'status':'DECLINE','reason':type(error).__name__+': '+str(error),'eligible_for_reuse':False}
   if observed is not None:observed.close()
  def before(c,cursor,statement,parameters,execution,many):
   if not state['active']:return
   try:
    if c is not selected or state['pending'] is not None:raise Decline('reentrant or rebound actual write')
    if statement.lstrip().upper().startswith('SELECT '):
     state['intermediate_selects']=state.get('intermediate_selects',0)+1;return
    if not statement.lstrip().upper().startswith(('UPDATE ','INSERT ')):raise Decline('unexpected W5 statement')
    if type(parameters) is not tuple or many:raise Decline('nonprimitive/multiple actual binding')
    state['pending']=(statement,OwnedValue.capture(parameters),c.connection.driver_connection.total_changes)
   except Exception as error:decline(error);state['active']=False
  def after(c,cursor,statement,parameters,execution,many):
   if not state['active']:return
   if statement.lstrip().upper().startswith('SELECT '):return
   try:
    sql,args,changes=state['pending'];state['pending']=None
    if sql!=statement or not args.matches(parameters):raise Decline('statement/binding changed between observers')
    observed.record(statement,parameters,cursor.rowcount,c.connection.driver_connection.total_changes-changes,executemany=many)
   except Exception as error:decline(error);state['active']=False
  promote=snapshot.promote.__code__;post=runtime._model_settlement_read.__wrapped__.__code__;advance=runtime.advance_model.__code__
  monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None);thread=threading.get_ident()
  def start(code,offset):
   nonlocal observed,selected
   if threading.get_ident()!=thread:return
   f=sys._getframe(1)
   if code is promote:
    parent=f.f_back
    if parent.f_code is not advance:return
    selected=f.f_locals['c'];scope=selected.info.get('local_model_snapshot')
    try:
     assert not state['captured'] and scope is not None and scope.phase=='READ'
     definition=schema(selected.connection.driver_connection)
     if tuple(r for r in definition if not r[1].startswith('sqlite_'))!=tuple(tuple(r) for r in _CATALOG['schema']):raise Decline('not the fixed project schema')
     if any(r[1].startswith('sqlite_') and not (r[0]=='index' and r[3] is None and r[1].startswith('sqlite_autoindex_'+r[2]+'_')) for r in definition):raise Decline('unknown internal schema')
     a=time.monotonic();observed=Observation(selected.connection.driver_connection,selected.get_transaction(),context(selected,parent.f_locals['current']),inputs(parent),definition,('attempts','events','operations','internal_app_runs','events'),connection=selected)
     state['timings']['g0_capture_seconds']=time.monotonic()-a;state['input_frame']=parent;state['captured']=True;state['active']=True
     event.listen(selected,'before_cursor_execute',before);event.listen(selected,'after_cursor_execute',after);state['listeners']=True
    except Exception as error:decline(error)
   elif code is post and selected is not None:
    state['active']=False;state['w5_end']=True
    if state['listeners']:
     event.remove(selected,'before_cursor_execute',before);event.remove(selected,'after_cursor_execute',after);state['listeners']=False
  def yielded(code,offset,value):
   if threading.get_ident()!=thread or code is not post:return
   f=sys._getframe(1);proof=f.f_locals['proof'];assert proof is not None and proof.state=='READY'
   state['oracle_ready']=True
   # The original G1 performed its protected-read/authority checks before
   # this diagnostic collector. Its journal settlement writes follow yield.
   if observed is not None and observed.active:
    try:
     a=time.monotonic();result=observed.compare(selected.connection.driver_connection,selected.get_transaction(),context(selected,f.f_locals['fresh']),inputs(state['input_frame']))
     state['timings']['post_compare_seconds']=time.monotonic()-a;state['result']={k:getattr(result,k) for k in ('status','reason','eligible_for_reuse','closed_dependencies','missing_dependencies')}
    except Exception as error:decline(error)
  def returned(code,offset,value):
   if threading.get_ident()!=thread:return
   f=sys._getframe(1)
   if code is post:
    proof=f.f_locals['proof'];assert proof is not None and proof.state=='CLOSED' and not proof.active;state['oracle_closed']=True
   elif code is advance and state['oracle_closed']:
    assert value is True;raise TailStop()
  monitor.use_tool_id(slot,'Expected-post data shadow only; original G1 always required')
  try:
   monitor.register_callback(slot,monitor.events.PY_START,start);monitor.register_callback(slot,monitor.events.PY_YIELD,yielded);monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
   monitor.set_local_events(slot,promote,monitor.events.PY_START);monitor.set_local_events(slot,post,monitor.events.PY_START|monitor.events.PY_YIELD|monitor.events.PY_RETURN);monitor.set_local_events(slot,advance,monitor.events.PY_RETURN)
   worker=case.factory(case.store,case.data[1],goal_planner_transport=apps.transport([],apps.COLD))
   with pytest.raises(TailStop):worker.once()
   assert state['captured'] and state['w5_end'] and state['oracle_ready'] and state['oracle_closed']
   assert state['result']['status']=='DATA_MATCH' and state['result']['eligible_for_reuse'] is False,state['result']
   assert len(observed.writes)==5 and not observed.active
   assert (cap.exchanges,cap.methods,cap.case_exchanges,cap.case_methods)==(6,8,1,1)
   assert len(case.store._local_model_snapshot_records)==1 and case.store._local_model_snapshot_records[0]['outcome']=='COMMITTED'
   with case.store.tx() as c:
    rows=[dict(r) for r in c.execute(select(attempts).where(attempts.c.run_id==template.cold_id)).mappings()]
   assert len(rows)==1 and rows[0]['status']=='VERIFIED'
  finally:
   for code in (promote,post,advance):monitor.set_local_events(slot,code,0)
   for ev in (monitor.events.PY_START,monitor.events.PY_YIELD,monitor.events.PY_RETURN):monitor.register_callback(slot,ev,None)
   monitor.free_tool_id(slot)
   if state['listeners']:
    event.remove(selected,'before_cursor_execute',before);event.remove(selected,'after_cursor_execute',after)
   if observed is not None:observed.close()
   state.pop('input_frame',None);state.pop('pending',None)
   state.update(classification='SYNTHETIC_ONE_COLD_VIRTUAL_BUSINESS_TIME_DATA_SHADOW_NOT_G1_REUSE',mock_calls=cap.exchanges,real_model_calls=0,source_file_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),writes=[] if observed is None else [dict(sql=w.sql,rowcount=w.rowcount,changes=w.changes,parameter_types=[type(v).__name__ for v in w.parameters],parameters_sha256=hashlib.sha256(OwnedValue.capture(w.parameters)._data).hexdigest()) for w in observed.writes],limits='No Graph/PASS/authority handoff. Full SQL logical endpoint and selected raw/wire/meta/response only. Full Python/file/callback/ordered-query/transaction provenance remains unclosed. Whole project DB is new synthetic test data; no production diagnostic read entrypoint.')
   (tmp_path/'actual-shadow-report.json').write_text(json.dumps(state,indent=2)+'\n');close_case(case,clock)
 assert not any(t.is_alive() for t in threading.enumerate() if t not in threads)
