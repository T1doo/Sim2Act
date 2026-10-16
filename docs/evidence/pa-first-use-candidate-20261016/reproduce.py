"""One fresh exact 0f first-use fixture; read-only instrumentation, no retries."""
import functools
import importlib.util
import json
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event
from sim2act import natural_spec_runtime as runtime, pa_spec_apps as spec, goal_applications as ga
from sim2act.worker import Worker
from sim2act.db import Store

ROOT=Path(__file__).resolve().parent
load=importlib.util.spec_from_file_location('frozen_0f_demo',ROOT/'local_candidate_demo.py')
demo=importlib.util.module_from_spec(load);load.loader.exec_module(demo)

class Trace:
 def __init__(self,store):
  self.store=store;self.rows=[];self.seq=0;self.lock=threading.Lock();self.local=threading.local();self.restore=[]
 def add(self,kind,**fields):
  with self.lock:
   self.seq+=1
   self.rows.append(dict(sequence=self.seq,kind=kind,wall=time.time(),monotonic=time.monotonic(),thread=threading.current_thread().name,thread_id=threading.get_ident(),tx=getattr(self.local,'tx',None),**fields))
 def error(self,e):
  orig=getattr(e,'orig',e)
  return dict(error_type=type(e).__name__,error=str(e),domain_code=getattr(e,'code',None),sqlite_code=getattr(orig,'sqlite_errorcode',None))
 def wrap(self,obj,name,label=None):
  original=getattr(obj,name)
  @functools.wraps(original)
  def call(*args,**kwargs):
   start=time.monotonic();self.add((label or name)+'_enter')
   try:result=original(*args,**kwargs)
   except BaseException as e:
    self.add((label or name)+'_error',elapsed=time.monotonic()-start,**self.error(e));raise
   else:
    fields={}
    if name=='guard':fields={key:result[key] for key in ['id','status','lease_until','fence']}
    if name=='heartbeat':fields={'renewed_until':result,'worker_id':args[0] if args else None,'run_id':args[1] if len(args)>1 else None}
    self.add((label or name)+'_exit',elapsed=time.monotonic()-start,**fields)
    return result
  setattr(obj,name,call);self.restore.append(lambda:setattr(obj,name,original))
 def install(self):
  original=self.store.tx
  @contextmanager
  def tx(*args,**kwargs):
   prior=getattr(self.local,'tx',None);self.local.tx=len(self.rows)+1
   self.add('tx_enter',options=kwargs)
   try:
    with original(*args,**kwargs) as c:
     self.add('tx_acquired',connection=id(c));yield c;self.add('tx_body_done')
   except BaseException as e:self.add('tx_failed',**self.error(e));raise
   else:self.add('tx_committed')
   finally:self.add('tx_exit');self.local.tx=prior
  self.store.tx=tx;self.restore.append(lambda:setattr(self.store,'tx',original))
  for obj,name,label in [(self.store,'heartbeat',None),(self.store,'guard',None),(spec,'bound','spec_bound'),(spec,'commit_guard','spec_commit_guard'),(spec,'receipts','spec_receipts'),(runtime,'advance_model',None),(runtime,'renew',None),(ga,'source_scope_gate',None),(Worker,'once','worker_once')]:self.wrap(obj,name,label)
  original_fail=runtime.fail_owned
  def fail(worker,run,error):
   self.add('fail_owned_reason',run_id=run['id'],**self.error(error));return original_fail(worker,run,error)
  runtime.fail_owned=fail;self.restore.append(lambda:setattr(runtime,'fail_owned',original_fail))
  def before(c,cursor,statement,parameters,ctx,many):
   if statement.strip().upper()=='BEGIN IMMEDIATE':self.add('sqlite_begin_enter',connection=id(c))
  def after(c,cursor,statement,parameters,ctx,many):
   if statement.strip().upper()=='BEGIN IMMEDIATE':self.add('sqlite_begin_acquired',connection=id(c))
  def error(ctx):self.add('sql_error',statement=ctx.statement,**self.error(ctx.original_exception))
  for name,fn in [('before_cursor_execute',before),('after_cursor_execute',after),('handle_error',error)]:
   event.listen(self.store.engine,name,fn);self.restore.append(lambda name=name,fn=fn:event.remove(self.store.engine,name,fn))
 def close(self):
  for undo in reversed(self.restore):undo()
  (ROOT/'baseline-first-pa-trace.json').write_text(json.dumps(self.rows,indent=2)+'\n')

root=ROOT/'fresh-baseline-first-pa'
assert not root.exists();root.mkdir();demo.write_json(root/'fixture.json',demo.MARKER)
settings=demo.settings_for(root);assert settings.lease_seconds==30 and settings.run_seconds==300
store=Store(settings.database_url,test_only=True);store.initialize();store.user('PUBLIC synthetic mock identity',demo.PUBLIC_TOKEN)
try:
 with demo.loopback(store,settings) as (client,url):
  driver=demo.Demo(store,settings,client,root)
  # Execute original 0f prefix, stopping after first PA use; no PB/matrix.
  import ast
  tree=ast.parse((ROOT/'local_candidate_demo.py').read_text())
  method=next(n for n in next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Demo').body if isinstance(n,ast.FunctionDef) and n.name=='run')
  cut=next(i for i,n in enumerate(method.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pa_result' for t in n.targets))
  prefix=ast.Module(body=method.body[:cut],type_ignores=[])
  values={'self':driver,'require':demo.require,'dict':dict,'natural':demo.natural}
  exec(compile(ast.fix_missing_locations(prefix),'frozen-0f-run-prefix','exec'),values)
  trace=Trace(store);trace.install()
  try:
   result=driver.natural_use(values['project'],values['pa_app'],values['pa_release'],values['pa_instance'],'pa','pa_use')
   demo.write_json(ROOT/'baseline-first-pa-outcome.json',dict(status='PASS',result=result))
  except BaseException as error:
   demo.write_json(ROOT/'baseline-first-pa-outcome.json',dict(status='FAIL',error_type=type(error).__name__,error=str(error),worker_receipts=driver.claims,mock_calls=driver.mock_calls))
   raise
  finally:trace.close()
finally:store.engine.dispose()
