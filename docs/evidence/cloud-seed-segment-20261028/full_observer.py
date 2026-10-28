"""Passive clocks and actual SQL writes; no gate/clock/transport substitutions."""
import json,time,threading,sys
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.engine import Engine
records=[]
loaded_counts={"calls":0,"eligible":0,"seed_checks":0,"seed_eligible":0,"accessor_calls":0,"accessor_eligible":0}
first_seed=[]
local=threading.local()
root=Path('/workspace/Sim2Act/docs/evidence/cloud-seed-segment-20261028')
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
  group='seed' if is_seed else 'accessor'
  loaded_counts['seed_checks' if is_seed else 'accessor_calls']+=1
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

def pytest_sessionfinish(session,exitstatus):
 progress('FINISHED')
 (root/'full-timings.json').write_text(json.dumps(dict(exitstatus=int(exitstatus),records=records,loaded_raw=loaded_counts,first_seed=first_seed),indent=2)+'\n')
