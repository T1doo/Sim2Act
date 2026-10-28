"""Passive clocks and actual SQL writes; no gate/clock/transport substitutions."""
import json,time,threading,sys
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.engine import Engine
records=[]
stage_totals={}
monitor_slot=None
loaded_counts={"calls":0,"eligible":0,"seed_checks":0,"seed_eligible":0,"accessor_calls":0,"accessor_eligible":0,"counter_calls":0,"counter_eligible":0}
first_seed=[]
local=threading.local()
root=Path('/workspace/Sim2Act/docs/evidence/cloud-counter-packet-20261028')
def progress(phase):
 (root/'progress.json').write_text(json.dumps(dict(phase=phase,utc_epoch=time.time(),loaded_raw=loaded_counts))+'\n')
def pytest_configure(config):
 from sim2act import natural_spec_runtime as r
 eligible=r._raw_read_eligible
 def selected(*args):
  caller=sys._getframe(1).f_code.co_name
  is_seed=caller=='check'
  first=is_seed and not first_seed and type(args[0]) is r._ColdRunFacts and vars(args[0].guard).get('phase')=='post'
  def traced(frame,event,arg):
   if frame.f_code.co_name in {'_raw_read_eligible','_raw_dynamic_eligible','_raw_seed_eligible','_raw_seed_plain'}:
    if event=='return' and arg is False:first_seed.append(dict(function=frame.f_code.co_name,line=frame.f_lineno))
    return traced
   return None
  prior=sys.gettrace()
  if first:sys.settrace(traced)
  try:value=eligible(*args)
  finally:
   if first:sys.settrace(prior)
  loaded_counts['calls']+=1;loaded_counts['eligible']+=int(value)
  group='seed' if is_seed else 'counter' if caller=='_cold_counter_loaded' else 'accessor'
  loaded_counts['seed_checks' if is_seed else group+'_calls']+=1
  loaded_counts[group+'_eligible']+=int(value)
  if first:
   if not first_seed:first_seed.append(dict(result=bool(value)))
   (root/'first-seed-selection.json').write_text(json.dumps(first_seed)+'\n')
  if loaded_counts['calls']%256==0:progress('RAW_READ_'+str(vars(args[0].guard).get('phase')))
  return value

 r._raw_read_eligible=selected
 before,commit,after,writer=r._cold_model_before,r._ColdTrialGraph.commit,r._model_settlement_read,r._model_settlement_writer
 @contextmanager
 def observed(*args,**kwargs):
  progress('G0')
  rec=dict(kind='G0',started_at=time.time(),completed=False,commits=[]); started=time.monotonic();local.current=rec;local.phase='G0'
  trial=None
  try:
   with before(*args,**kwargs) as trial:
    rec['selected']=trial is not None
    yield trial
   rec['completed']=True;local.phase='W5'
  except BaseException as error:
   rec['error']=error.public() if hasattr(error,'public') else type(error).__name__;raise
  finally:
   if trial is not None:
    rec['accounted']=trial.accounted_prewrite is not None
   rec['wall_seconds']=time.monotonic()-started;records.append(rec);local.current=None
 @contextmanager
 def settled(*args,**kwargs):
  progress('G1')
  rec=dict(kind='G1',completed=False);started=time.monotonic();local.phase='G1'
  try:
   with after(*args,**kwargs) as result:yield result
   rec['completed']=True
  finally:
   rec['wall_seconds']=time.monotonic()-started;records.append(rec);local.phase='TAIL'
 def committed(self,prefix):
  rec=getattr(local,'current',None);started=time.monotonic();item=dict(key=prefix.key,returned=False)
  try:
   value=commit(self,prefix);item['returned']=True;return value
  finally:
   item['wall_seconds']=time.monotonic()-started
   if rec is not None:rec['commits'].append(item)
 @contextmanager
 def written(*args,**kwargs):
  rec=dict(kind='SETTLEMENT_TRANSACTION_AND_LEASE',completed=False,writes=[]);started=time.monotonic();local.interval=rec
  try:
   with writer(*args,**kwargs):yield
   rec['completed']=True
  finally:
   rec['wall_seconds']=time.monotonic()-started;records.append(rec);local.interval=None;local.phase=None
 def sql(c,cursor,statement,parameters,context,executemany):
  rec=getattr(local,'interval',None)
  if rec is not None and getattr(local,'phase',None)=='W5':
   if statement.lstrip().split(' ',1)[0].upper() in ('UPDATE','INSERT','DELETE'):
    rec['writes'].append(dict(statement=statement,rowcount=cursor.rowcount))
 event.listen(Engine,'after_cursor_execute',sql)
 r._cold_model_before=observed;r._ColdTrialGraph.commit=committed;r._model_settlement_read=settled;r._model_settlement_writer=written

def install_stage_monitor():
 global monitor_slot
 from sim2act import natural_spec_runtime as r,pa_spec_apps as spec,pa_trial_dispatch as dispatch
 monitoring=sys.monitoring
 monitor_slot=next(i for i in (4,3,5) if monitoring.get_tool(i) is None)
 monitoring.use_tool_id(monitor_slot,'read-only G1 stage timing')
 targets=[(r._ColdTrialGraph.commit,'graph.commit'),(r._cold_binding_limits_facet,'platform_facet'),
  (spec._cold_receipts,'receipts'),(dispatch._graph_journal_chain,'journal_chain'),
  (r._ModelSettlementRead.live,'proof.live'),(r._ModelSettlementRead.check,'proof.check'),
  (r._counters,'counters'),(r._cold_counter_loaded,'counter.selector'),(r._counter_packet_core,'counter.packet_core'),
  (r._cold_graph_bytes,'graph.encode'),(r._model_inputs,'model.inputs')]
 codes={fn.__code__:label for fn,label in targets}
 def enter(code,offset):
  if getattr(local,'phase',None)!='G1':return
  stacks=getattr(local,'monitor_stacks',None)
  if stacks is None:local.monitor_stacks=stacks={}
  stacks.setdefault(code,[]).append(time.perf_counter())
 def leave(code,offset,value):
  stacks=getattr(local,'monitor_stacks',{})
  starts=stacks.get(code)
  if not starts:return
  started=starts.pop();label=codes[code]
  row=stage_totals.setdefault(label,dict(calls=0,seconds=0,bytes=0))
  row['calls']+=1;row['seconds']+=time.perf_counter()-started
  if label=='graph.encode' and type(value) is bytes:row['bytes']+=len(value)
  if label in {'graph.commit','platform_facet','receipts','proof.live','counter.packet_core'}:
   (root/'g1-stage-timings.json').write_text(json.dumps(dict(classification='REAL_CLOCK_OVERLAPPING_CALL_TIMES_NOT_ADDITIVE',stages=stage_totals),indent=2)+'\n')
 monitoring.register_callback(monitor_slot,monitoring.events.PY_START,enter)
 monitoring.register_callback(monitor_slot,monitoring.events.PY_RETURN,leave)
 monitoring.register_callback(monitor_slot,monitoring.events.PY_UNWIND,leave)
 for code in codes:monitoring.set_local_events(monitor_slot,code,monitoring.events.PY_START|monitoring.events.PY_RETURN)
 monitoring.set_events(monitor_slot,monitoring.events.PY_UNWIND)

def pytest_sessionstart(session):
 install_stage_monitor()

def pytest_sessionfinish(session,exitstatus):
 progress('FINISHED')
 (root/'g1-stage-timings.json').write_text(json.dumps(dict(classification='REAL_CLOCK_OVERLAPPING_CALL_TIMES_NOT_ADDITIVE',stages=stage_totals),indent=2)+'\n')
 if monitor_slot is not None:
  sys.monitoring.set_events(monitor_slot,0)
  sys.monitoring.free_tool_id(monitor_slot)
 (root/'full-timings.json').write_text(json.dumps(dict(exitstatus=int(exitstatus),records=records,loaded_raw=loaded_counts,first_seed=first_seed,stage_totals=stage_totals),indent=2)+'\n')
