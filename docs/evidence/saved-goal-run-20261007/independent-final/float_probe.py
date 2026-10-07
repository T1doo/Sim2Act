import sys,pathlib,json,copy,hashlib,contextlib
sys.dont_write_bytecode=True
ROOT=pathlib.Path(sys.argv[1]);OUT=pathlib.Path(sys.argv[2]);OUT.mkdir(exist_ok=True,parents=True);sys.path.insert(0,str(ROOT/'src'))
from fastapi.testclient import TestClient
from sqlalchemy import select,update,insert,func
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,meta,fingerprint,runs,run_contracts,events,grants,principals,attempts,operations,new_id
from sim2act.model import MockModel,SYSTEM_PROMPT
from sim2act.worker import Worker
import sim2act.goal_runs,sim2act.worker
CONTENT={'title':'独立来源','goal':'读取文本并保留证据','known':['只是合成资料'],'assumptions':['待确认案例'],'unresolved':['语义未验收'],'constraints':['只读取','不得发布'],'acceptance_checks':['真实读取回执'],'resource_refs':[]}
def rows(store,t):
 with store.engine.connect() as c:return sorted([dict(x) for x in c.execute(select(t)).mappings()],key=fingerprint)
def auth(store):return {t.name:rows(store,t) for t in [grants,principals]}
def allfp(store):return fingerprint({t.name:rows(store,t) for t in meta.tables.values()})
results=[]
for case in ['accepted_event_version_float','resumed_source_version_float']:
 d=OUT/case;d.mkdir(exist_ok=True);store=Store('sqlite:///'+str(d/'fixture.db'),test_only=True);store.initialize();store.user('A','synthetic-independent-A');store.user('B','synthetic-independent-B');settings=Settings('sqlite:///'+str(d/'fixture.db'),d);client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer synthetic-independent-A';calls=[]
 original=MockModel.request
 def request(m,messages,tools):calls.append(copy.deepcopy({'messages':messages,'tools':tools}));return original(m,messages,tools)
 MockModel.request=request
 try:
  pid=client.post('/api/projects',json={'name':'independent'}).json()['id'];resource=client.post(f'/api/projects/{pid}/resources',json={'name':'proof.txt','format':'txt','content':'独立合成内容'}).json()['id'];refs=[] if case=='cross_project_empty_relabel' else [resource];content={**CONTENT,'resource_refs':refs};a=client.post(f'/api/projects/{pid}/goal-cards',json=content).json();bpid=client.post('/api/projects',json={'name':'other'}).json()['id'] if case=='cross_project_empty_relabel' else pid;b=client.post(f'/api/projects/{bpid}/goal-cards',json=content).json();body={'expected_version':1,'expected_fingerprint':a['fingerprint'],'request_key':'independent-key'}
  if case=='legacy_source_none':
   response=client.post(f'/api/projects/{pid}/runs',json={'goal':CONTENT['goal'],'resource_refs':refs,'request_key':'legacy'});assert response.status_code==202,response.text;rid=response.json()['run_id']
  else:
   response=client.post(f'/api/projects/{pid}/goal-cards/{a["id"]}/runs',json=body);assert response.status_code==202,response.text;rid=response.json()['run_id']
  with store.tx() as c:
   raw=dict(c.execute(select(runs).where(runs.c.id==rid)).mappings().one());saved=dict(c.execute(select(run_contracts).where(run_contracts.c.run_id==rid)).mappings().one());snapshot=copy.deepcopy(saved['snapshot']);ctx=copy.deepcopy(raw['context'])
   if case in ['same_project_relabel','cross_project_empty_relabel','rewritten_request_anchor']:
    snapshot['source_goal_card']['card_id']=b['id'];snapshot['goal']['goal_id']=b['id'];c.execute(update(run_contracts).where(run_contracts.c.run_id==rid).values(snapshot=snapshot,fingerprint=fingerprint(snapshot)))
    if case=='rewritten_request_anchor':
     fp=fingerprint({'goal':snapshot['goal']['goal'],'resource_refs':snapshot['goal']['resource_refs'],'policy':{k:snapshot[k] for k in ['limits','mode','request_model']},'goal_source':snapshot['source_goal_card']});ctx['saved_goal_input']=fp;c.execute(update(runs).where(runs.c.id==rid).values(fingerprint=fp,context=ctx))
   if case in ['stripped_source','stripped_source_and_marker']:
    snapshot.pop('source_goal_card');c.execute(update(run_contracts).where(run_contracts.c.run_id==rid).values(snapshot=snapshot,fingerprint=fingerprint(snapshot)))
    if case.endswith('_and_marker'):ctx.pop('saved_goal_input');c.execute(update(runs).where(runs.c.id==rid).values(context=ctx))
   if case=='accepted_event_tamper':c.execute(update(events).where(events.c.run_id==rid,events.c.kind=='ACCEPTED').values(data={'input_fingerprint':'0'*64}))
   if case=='accepted_event_version_float':
    data=copy.deepcopy(c.execute(select(events.c.data).where(events.c.run_id==rid,events.c.kind=='ACCEPTED')).scalar_one());data['goal_source']['version']=1.0;c.execute(update(events).where(events.c.run_id==rid,events.c.kind=='ACCEPTED').values(data=data))
   if case=='duplicate_accepted_event':store.event(c,rid,'ACCEPTED',{'input_fingerprint':raw['fingerprint']})
   if case in ['resumed_conditions_tamper','resumed_source_version_float']:
    payload={'goal':raw['goal'],'resource_refs':raw['resource_refs'],'saved_goal':copy.deepcopy(snapshot['source_goal_card'])};
    if case=='resumed_conditions_tamper':payload['saved_goal']['snapshot']['content']['constraints']=[]
    else:payload['saved_goal']['version']=1.0
    ctx['messages']=[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}];c.execute(update(runs).where(runs.c.id==rid).values(context=ctx))
   if case=='current_grant_revoked':c.execute(update(grants).where(grants.c.resource_id==resource).values(revoked=True))
   if case=='current_resource_changed':
    from sim2act.db import resources
    c.execute(update(resources).where(resources.c.id==resource).values(content='changed'))
  if case=='same_key_after_revision':
   revised={**content,'goal':'另一个目标','constraints':['更新硬条件'],'expected_version':1};assert client.put('/api/goal-cards/'+a['id'],json=revised).status_code==200;again=client.post(f'/api/projects/{pid}/goal-cards/{a["id"]}/runs',json=body);assert again.status_code==202 and again.json()['run_id']==rid
  beforeauth=auth(store);before_read=allfp(store);get=client.get('/api/runs/'+rid);assert allfp(store)==before_read;store.test_only=False;worked=Worker(store,settings).once();afterauth=auth(store);assert beforeauth==afterauth
  with store.engine.connect() as c:
   final=dict(c.execute(select(runs).where(runs.c.id==rid)).mappings().one());acount=c.execute(select(func.count()).select_from(attempts)).scalar_one();ocount=c.execute(select(func.count()).select_from(operations)).scalar_one()
  expected_zero=case not in ['baseline','same_key_after_revision','legacy_source_none'];ok=(len(calls)==0 and acount==0 and ocount==0) if expected_zero else (len(calls)==2 and final['status']=='PARTIAL')
  record={'case':case,'oracle':'PASS' if ok else 'SOURCE_DEFECT_CONFIRMED','get_before_worker':get.status_code,'get_error':(get.json().get('error') or {}).get('code'),'worker_claimed':worked,'provider_calls':len(calls),'actual_attempts':acount,'actual_operations':ocount,'final_status':final['status'],'error_code':(final['error'] or {}).get('code'),'goal_acceptance':(final['result'] or {}).get('goal_acceptance'),'authority_equal':True,'authority_before_fp':fingerprint(beforeauth),'authority_after_fp':fingerprint(afterauth),'get_all_tables_equal':True}
  if not expected_zero and case!='legacy_source_none':record['all_saved_content_actual_prompt']=json.loads(calls[0]['messages'][1]['content'])['saved_goal']['snapshot']['content']==content
  results.append(record)
 finally:
  MockModel.request=original;client.close();store.engine.dispose()
manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'src/sim2act/goal_runs.py',ROOT/'src/sim2act/db.py',ROOT/'src/sim2act/worker.py',ROOT/'src/sim2act/web/app.js']}
report={'decision':'SOURCE_DEFECT_CONFIRMED' if any(r['oracle']!='PASS' for r in results) else 'LIMITED_HTTP_WORKER_PASS','cases':results,'runtime_modules':{'goal_runs':sim2act.goal_runs.__file__,'worker':sim2act.worker.__file__},'source_hashes':manifest,'live_requests':0,'native':'NOT_RUN','pg_concurrency':'NOT_RUN','remaining':'UI oracle not executed; ordinary PARTIAL is not P-B success or semantic acceptance; Mock sends only'}
(OUT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False));sys.exit(0)
