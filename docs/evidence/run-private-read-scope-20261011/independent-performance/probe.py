import ast,cProfile,functools,hashlib,inspect,json,os,pstats,sqlite3,subprocess,time,traceback
from pathlib import Path
from collections import Counter
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None)
from sqlalchemy import event
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from sim2act.api import create_app
from sim2act.db import Store,fingerprint
from sim2act.config import Settings
from sim2act import protocol_jobs as pjobs
ROOT=Path('/tmp/run-private-read-performance-independent-20261011');REPO=Path('/workspace/Sim2Act');SOURCE=Path('/tmp/run-private-current-ui/test_actual_new_material_page_0')
freeze=json.loads((REPO/'docs/evidence/run-private-read-scope-20261011/frozen-before.json').read_text())
assert all(hashlib.sha256((REPO/k).read_bytes()).hexdigest()==v for k,v in freeze.items())
(ROOT/'frozen-before.json').write_text(json.dumps(freeze,indent=2)+'\n')
source_db=SOURCE/'fixture.db';dest=ROOT/'fixture.db'
assert not dest.exists(),'fresh copy required'
source_db_sha=hashlib.sha256(source_db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(source_db)+'?mode=ro',uri=True) as src,sqlite3.connect(dest) as dst:src.backup(dst)
failure=json.loads((SOURCE/'FAILURE.json').read_text());info=json.loads((SOURCE/'info.json').read_text())
# All observations use our isolated SQLite copy, never the retained original.
with sqlite3.connect(dest) as c:
 before_db={name:[list(x) for x in c.execute('SELECT * FROM '+name)] for name in ['runs','run_contracts','operations','operation_intents','internal_app_runs','internal_instances','internal_instance_data','internal_releases']}
 original_run=next(x for x in failure['requests'] if x['method']=='POST' and '/internal/instances/' in x['path'] and x['path'].endswith('/runs'))
 iid=original_run['path'].split('/')[-2]
 instance=c.execute('SELECT release_id FROM internal_instances WHERE id=?',(iid,)).fetchone();rid=instance[0]
 rel=json.loads(c.execute('SELECT snapshot FROM internal_releases WHERE id=?',(rid,)).fetchone()[0]);e=rel['execution_source']
 srun=e['run_id'];material_key=e['plan_key']
 bindings=c.execute('SELECT run_id,snapshot FROM internal_run_bindings WHERE instance_id=?',(iid,)).fetchall() if False else c.execute('SELECT run_id,snapshot FROM internal_run_bindings').fetchall()
 binding=next((j,json.loads(raw)) for j,raw in bindings if json.loads(raw)['instance_id']==iid)
 irun,bs=binding;instance_key=bs['plan_key']
 status=c.execute('SELECT status FROM runs WHERE id=?',(irun,)).fetchone()[0];assert status=='SUCCEEDED',status
pid,aid=info['project'],info['targetapp'];base='/api/projects/'+pid+'/apps/'+aid+'/csv-dag/'
sequence=[('instance', '/api/internal/instances/'+iid),('source-run', '/api/csv-dag/runs/'+srun),('source-plan',base+material_key),('source-run-again','/api/csv-dag/runs/'+srun),('source-plan-again',base+material_key),('instance-plan',base+instance_key)]
R={'status':'RUNNING','fixture_origin':'SQLite backup into independent /tmp fixture of exact retained material/report post-True failure, after actual successful worker; source remains read-only','failure_source_checks':failure['checks'],'scope':'in-process TestClient cold SUCCEEDED instance/read-release/DAG proofs; no browser/network; current/baseline oracle A/B/A only read GETs','source_database_sha256_before':source_db_sha,'frozen_file_count':len(freeze),'samples':[],'namespace_calls':[],'sql_summary':[],'errors':[],'NOT_RUN':['original JSDOM/socket UI case','UI timeout causality','PG','Windows/native/browser','real models','old source upgrade','full regression']}
settings=Settings('sqlite:///'+str(dest),SOURCE,mode='mock');store=Store(settings.database_url,test_only=True);app=create_app(store,settings)
PROFILE=False;PHASE='initialize';prof_ids=[]
for route in app.routes:
 if isinstance(route,APIRoute) and not inspect.iscoroutinefunction(route.dependant.call):
  original_endpoint=route.dependant.call
  def build(orig,name):
   @functools.wraps(orig)
   def call(*a,**kw):
    if not PROFILE:return orig(*a,**kw)
    pr=cProfile.Profile();pr.enable()
    try:return orig(*a,**kw)
    finally:
     pr.disable();index=len(prof_ids);path=ROOT/('profile-'+str(index)+'-'+name+'.pstats');pr.dump_stats(path);prof_ids.append(str(path))
   return call
  route.dependant.call=build(original_endpoint,route.name)
client=TestClient(app);client.headers['Authorization']='Bearer synthetic-test-A'
current_oracle=pjobs.protocol_run_ids
old_text=(Path('/tmp/run-private-2b-baseline/src/sim2act/protocol_jobs.py')).read_text()
assert hashlib.sha256(old_text.encode()).hexdigest()==hashlib.sha256(subprocess.check_output(['git','show','2b53572ded47f83d51898356dae0e99a97a61bc9:src/sim2act/protocol_jobs.py'],cwd=REPO)).hexdigest()
node=next(n for n in ast.parse(old_text).body if isinstance(n,ast.FunctionDef) and n.name=='protocol_run_ids');old_fn_src=ast.get_source_segment(old_text,node);space=dict(pjobs.__dict__);exec(compile(old_fn_src,'<2b53572-read-only-oracle>','exec'),space);old_oracle=space['protocol_run_ids']
R['baseline_protocol_jobs_sha256']=hashlib.sha256(old_text.encode()).hexdigest();R['baseline_function_sha256']=hashlib.sha256(old_fn_src.encode()).hexdigest()
def wrapper(fn,label):
 def observed(c,rid=None,*,candidates=None):
  if label=='2b-oracle':assert rid is not None and candidates is None,'baseline comparison prohibits unscoped private reads'
  a=time.perf_counter();cpu=time.process_time()
  try:return fn(c,rid) if candidates is None else fn(c,candidates=candidates)
  finally:R['namespace_calls'].append({'phase':PHASE,'oracle':label,'rid':rid,'candidate_count':None if candidates is None else len(candidates),'wall':time.perf_counter()-a,'cpu':time.process_time()-cpu})
 return observed
sql=[]
def before(c,cursor,statement,parameters,context,many):context._ind_perf=(time.perf_counter(),time.process_time())
def after(c,cursor,statement,parameters,context,many):
 a,cpu=context._ind_perf;sql.append({'phase':PHASE,'wall':time.perf_counter()-a,'cpu':time.process_time()-cpu,'verb':statement.lstrip().split(' ',1)[0].upper(),'namespace_sql':('json_each' in statement or 'protocol_jobs' in statement or 'PROTOCOL_ACCEPTED' in str(parameters)),'sql':statement})
event.listen(store.engine,'before_cursor_execute',before);event.listen(store.engine,'after_cursor_execute',after)
expected={}
def sample(label,oracle,profile=False):
 global PHASE,PROFILE
 PHASE=label;PROFILE=profile;pjobs.protocol_run_ids=wrapper(oracle,'2b-oracle' if oracle is old_oracle else 'current')
 a=time.perf_counter();cpu=time.process_time();calls0=len(R['namespace_calls']);sql0=len(sql);items=[]
 for name,path in sequence:
  b=time.perf_counter();bcpu=time.process_time();resp=client.get(path);assert resp.status_code==200,(name,resp.status_code,resp.text)
  value=resp.json();fp=fingerprint(value)
  if path in expected:assert expected[path]==fp,'read reply differs across oracle comparison'
  else:expected[path]=fp
  items.append({'endpoint':name,'path':path,'wall':time.perf_counter()-b,'cpu':time.process_time()-bcpu,'reply_fingerprint':fp})
 R['samples'].append({'phase':label,'profiled':profile,'wall':time.perf_counter()-a,'cpu':time.process_time()-cpu,'endpoints':items,'namespace_calls':len(R['namespace_calls'])-calls0,'sql_count':len(sql)-sql0,'load_average':os.getloadavg()})
 print(json.dumps(R['samples'][-1]),flush=True)
try:
 sample('current-A1',current_oracle)
 sample('2b-B',old_oracle)
 sample('current-A2',current_oracle)
 sample('current-profile',current_oracle,True)
except Exception:R['errors'].append(traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 pjobs.protocol_run_ids=current_oracle;PROFILE=False
 event.remove(store.engine,'before_cursor_execute',before);event.remove(store.engine,'after_cursor_execute',after);client.close();store.engine.dispose()
for phase in sorted({x['phase'] for x in sql}):
 ss=[x for x in sql if x['phase']==phase];R['sql_summary'].append({'phase':phase,'count':len(ss),'namespace_count':sum(x['namespace_sql'] for x in ss),'total_wall':sum(x['wall'] for x in ss),'total_cpu':sum(x['cpu'] for x in ss),'verbs':dict(Counter(x['verb'] for x in ss))})
(ROOT/'sql-trace.json').write_text(json.dumps(sql,indent=2)+'\n')
if prof_ids:
 st=pstats.Stats(*prof_ids);lines=[]
 for (f,l,n),(cc,nc,tt,ct,callers) in sorted(st.stats.items(),key=lambda x:x[1][3],reverse=True)[:70]:lines.append({'file':f,'line':l,'name':n,'primitive_calls':cc,'calls':nc,'self_seconds':tt,'cumulative_seconds':ct})
 R['profile_top70']=lines
R['frozen_all_unchanged']=all(hashlib.sha256((REPO/k).read_bytes()).hexdigest()==v for k,v in freeze.items());assert R['frozen_all_unchanged']
R['original_fixture_bytes_unchanged']=hashlib.sha256(source_db.read_bytes()).hexdigest()==source_db_sha;assert R['original_fixture_bytes_unchanged']
with sqlite3.connect(dest) as c:after_db={name:[list(x) for x in c.execute('SELECT * FROM '+name)] for name in before_db}
R['all_business_history_unchanged']=before_db==after_db;assert R['all_business_history_unchanged']
R['status']='FAIL' if R['errors'] else 'PASS';(ROOT/'result.json').write_text(json.dumps(R,indent=2)+'\n');print(json.dumps({'status':R['status'],'samples':len(R['samples']),'namespace_calls':len(R['namespace_calls']),'frozen_all_unchanged':R['frozen_all_unchanged']}),flush=True)
raise SystemExit(bool(R['errors']))
