"""Two-request maximum real fixed Intern route; synthetic API/SQLite basic flow only."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from dataclasses import replace
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,attempts,operations
from sim2act.errors import DomainError
from sim2act.model import InternModel,normalize_usage,returned_model_identity,require_returned_model
from sim2act.production_evidence import configured_token,FREE_SERVICE_POLICY
from sim2act.worker import Worker

out=Path('/workspace/scratch/live-f1-basic-20261031')
out.mkdir(exist_ok=False)
source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
report={'source_commit':source,'classification':'REAL_INTERN_F1_API_WORKER_SYNTHETIC_SQLITE_NOT_NATURAL_COLD_PG_WINDOWS','max_requests':2,'max_repairs':0,'max_tools':1,'paid_cap':0,'fallback':'STOP','endpoint':InternModel.ENDPOINT,'model':'intern-s2','token_nonempty':bool(configured_token()),'prior_live_mode_set':bool(os.getenv('SIM2ACT_MODEL_MODE')),'prior_live_enabled_set':bool(os.getenv('SIM2ACT_LIVE_ENABLED')),'explicit_invocation_live':True,'requests':[],'fee_basis':FREE_SERVICE_POLICY,'started_utc':time.time()}
assert configured_token()
url='sqlite:///'+str(out/'fixture.db')
s=Settings(url,out,mode='live',live_enabled=True,token=configured_token(),max_requests=2,max_tools=1,max_repairs=0,max_total_tokens=16384,max_output_tokens=1024,run_seconds=90)
store=Store(url,test_only=True);store.initialize()
# Standard synthetic fixture identity only; no production credential is created.
store.user('synthetic existing test identity','synthetic-test-A')
start=time.monotonic()
class BoundedIntern(InternModel):
 def request(self,messages,tools):
  if len(report['requests'])>=2:raise DomainError('BUDGET_EXHAUSTED','Two-request verification cap')
  if time.monotonic()-start>=60:raise DomainError('BUDGET_EXHAUSTED','Verification envelope ended')
  wire=httpx.Request('POST',self.ENDPOINT,json={'model':s.model,'messages':messages,'tools':tools,'stream':False,'max_tokens':s.max_output_tokens}).content
  if sum(r['reserved_envelope'] for r in report['requests'])+len(wire)+s.max_output_tokens>16384:raise DomainError('BUDGET_EXHAUSTED','Verification total envelope')
  rec={'request_sha256':hashlib.sha256(wire).hexdigest(),'reserved_envelope':len(wire)+s.max_output_tokens,'request_bytes':len(wire),'status':'STARTED'};report['requests'].append(rec)
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
  sent=time.monotonic()
  def guard(request):
   assert request.content==wire and str(request.url)==self.ENDPOINT and request.method=='POST'
   return {'deadline':time.time()+min(30,max(.001,60-(time.monotonic()-start)))}
  try:
   captured=self.request_serialized_captured(wire,guard)
   identity=returned_model_identity(s.model,captured.parsed.get('model'));require_returned_model(identity)
   rec.update(status='RECEIVED',http_status=200,response_sha256=hashlib.sha256(captured.body).hexdigest(),response_bytes=len(captured.body),usage=normalize_usage(captured.parsed),identity=identity)
   return captured.parsed
  except DomainError as e:
   rec.update(status='STOPPED',error=e.public(),http_status=getattr(e,'_received_status_code',None));raise
  finally:
   rec['seconds']=time.monotonic()-sent;(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
try:
 with TestClient(create_app(store,s)) as client:
  client.headers['Authorization']='Bearer synthetic-test-A'
  p=client.post('/api/projects',json={'name':'Synthetic real Intern basic read'});assert p.status_code==201,p.text
  pid=p.json()['id']
  resource=client.post(f'/api/projects/{pid}/resources',json={'name':'synthetic42.txt','format':'txt','content':'42'});assert resource.status_code==201,resource.text
  rid=resource.json()['id']
  body={'goal':f'Use resource.read exactly once to read the sole authorized resource {rid}. After the tool succeeds, answer with only the exact resource content. Do not call other tools.','resource_refs':[rid],'request_key':'bounded-real-intern-basic'}
  q=client.post(f'/api/projects/{pid}/runs',json=body);assert q.status_code==202,q.text
  run=q.json()['run_id'];report['run_id']=run
  report['worker_once']=Worker(store,s,BoundedIntern(s)).once()
  got=client.get(f'/api/runs/{run}');assert got.status_code==200,got.text
  value=got.json();(out/'user-result.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
  duplicate=client.post(f'/api/projects/{pid}/runs',json=body)
  report.update(run_status=value['status'],user_http=got.status_code,duplicate_http=duplicate.status_code,duplicate_same_run=duplicate.json().get('run_id')==run,model_requests=len(report['requests']))
  with store.engine.connect() as c:
   aa=[dict(x) for x in c.execute(select(attempts).where(attempts.c.run_id==run)).mappings()]
   oo=[dict(x) for x in c.execute(select(operations).where(operations.c.run_id==run)).mappings()]
  report['attempt_states']=[x['status'] for x in aa];report['operations']=[{'tool_ref':x['tool_ref'],'status':x['status']} for x in oo]
  expected=bool(value.get('result')) and value['result'].get('answer','').strip()=='42' and len(oo)==1 and oo[0]['tool_ref']=='resource.read' and oo[0]['status']=='VERIFIED'
  report['exact_read_output_and_receipt']=expected
  report['goal_acceptance']=value.get('result',{}).get('goal_acceptance') if value.get('result') else None
 store.engine.dispose()
 code='''import json,sys\nfrom pathlib import Path\nfrom fastapi.testclient import TestClient\nfrom sim2act.api import create_app\nfrom sim2act.config import Settings\nfrom sim2act.db import Store\ns=Settings(sys.argv[1],Path(sys.argv[2]))\nst=Store(s.database_url,test_only=True)\nwith TestClient(create_app(st,s)) as c:\n c.headers['Authorization']='Bearer synthetic-test-A'\n r=c.get('/api/runs/'+sys.argv[3]);assert r.status_code==200\n assert r.json()==json.loads(Path(sys.argv[2],'user-result.json').read_text())\n print('REOPEN_IDENTICAL')\nst.engine.dispose()\n'''
 reopen=subprocess.run([sys.executable,'-c',code,url,str(out),report['run_id']],capture_output=True,text=True,timeout=15)
 report['fresh_process_reopen_identical']=reopen.returncode==0 and reopen.stdout.strip()=='REOPEN_IDENTICAL'
 report['status']='PASS' if expected and report['duplicate_same_run'] and report['fresh_process_reopen_identical'] else 'FAIL'
except Exception as e:
 report['status']='STOPPED';report['error']=e.public() if isinstance(e,DomainError) else {'type':type(e).__name__}
finally:
 report['seconds']=time.monotonic()-start;report['ended_utc']=time.time();(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report.get(k) for k in ['status','source_commit','model_requests','run_status','attempt_states','operations','exact_read_output_and_receipt','fresh_process_reopen_identical','seconds','error']},indent=2),flush=True)
sys.exit(0 if report['status']=='PASS' else 1)
