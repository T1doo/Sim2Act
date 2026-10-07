import sys,os,json,copy,hashlib,traceback
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
ROOT=Path('/tmp/natural-goal-planning-independent/e150b06/source');sys.path.insert(0,str(ROOT/'src'))
from dataclasses import replace
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select,update
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, runs,attempts,operations,events,run_contracts,grants,principals,resources,fingerprint
from sim2act.worker import Worker
import sim2act.goal_planner as gp
BASE=ROOT.parent
out=[]
def snapshot(s,ts):
 with s.tx() as c:return {t.name:sorted([dict(r) for r in c.execute(select(t)).mappings()],key=lambda x:json.dumps(x,sort_keys=True,default=str)) for t in ts}
def case(name):
 p=BASE/('db-'+name);p.mkdir(exist_ok=True);s=Store('sqlite:///'+str(p/'fixture.db'),test_only=True);s.initialize();s.user('A','independent-A');s.user('B','independent-B');sett=Settings(s.url if hasattr(s,'url') else 'sqlite:///'+str(p/'fixture.db'),p,mode='mock',goal_planner_provider='intern-s2');cl=TestClient(create_app(s,sett));cl.headers['Authorization']='Bearer independent-A'
 pid=cl.post('/api/projects',json={'name':'independent'}).json()['id'];rid=cl.post(f'/api/projects/{pid}/resources',json={'name':'new.csv','format':'csv','content':'x,quantity_z\na,11\nb,23\n'}).json()['id']
 card=cl.post(f'/api/projects/{pid}/goal-cards',json={'title':'independent','goal':'读取材料并合计 quantity_z，语义待人工确认','known':['合成'], 'assumptions':['单位待确认'],'unresolved':['目的待确认'],'constraints':['只读','不外发'],'acceptance_checks':['实际回读'],'resource_refs':[rid]}).json();card=cl.get('/api/goal-cards/'+card['id']).json()
 au=snapshot(s,[grants,principals]);material=snapshot(s,[resources]);wire=[]
 plan={'version':'natural-goal-plan.v1','source_goal_fingerprint':card['fingerprint'],'interpretation':{'objective':'独立两步','assumptions':['单位未知'],'unresolved':['未签收']},'steps':[{'id':'read_it','tool_ref':'resource.read','resource_id':rid,'depends_on':[]},{'id':'sum_it','tool_ref':'data.aggregate_csv','resource_id':rid,'column':'quantity_z','depends_on':['read_it']}]}
 raw={'model':'Intern-S2','usage':{'prompt_tokens':13,'completion_tokens':31,'total_tokens':44},'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(plan)}}]}
 if name=='finish_toolcalls':raw['choices'][0]['finish_reason']='tool_calls'
 if name=='wrongmodel':raw['model']='wrong'
 if name=='unknownusage':raw.pop('usage')
 if name=='refusal':raw['choices'][0]['message']['refusal']='no'
 if name=='baddep':plan['steps'][0]['depends_on']=['sum_it'];raw['choices'][0]['message']['content']=json.dumps(plan)
 def handler(req):
  wire.append(req.content.decode());
  if name=='timeout':raise httpx.ReadTimeout('synthetic')
  return httpx.Response(200,json=raw)
 req={'expected_version':card['version'],'expected_fingerprint':card['fingerprint'],'request_key':'independent-key'}
 accepted=cl.post(f'/api/projects/{pid}/goal-cards/{card["id"]}/planned-runs',json=req);assert accepted.status_code==202,accepted.text;runid=accepted.json()['run_id']
 worker=Worker(s,sett if name!='disabled' else replace(sett,goal_planner_provider='disabled'),goal_planner_transport=None if name in ['disabled','noadapter'] else httpx.MockTransport(handler));assert worker.once()
 view=cl.get('/api/runs/'+runid);positive=name not in ['wrongmodel','unknownusage','refusal','baddep','timeout','disabled','noadapter'];record={'name':name,'initial_get':view.status_code,'wires':len(wire)}
 if positive:
  assert view.status_code==200 and view.json()['status']=='PARTIAL',view.text
  assert view.json()['result']['receipts'][1]['data']['sum']=='34';assert view.json()['result']['goal_acceptance']=='NOT_RUN'
 if name in ['wrongmodel','unknownusage','refusal','baddep','timeout','disabled','noadapter']:
  assert len(snapshot(s,[operations])['operations'])==0
 if name not in ['positive','disabled','noadapter']:
  with s.tx() as c:
   rr=dict(c.execute(select(runs).where(runs.c.id==runid)).mappings().one());ctx=copy.deepcopy(rr['context'])
   if name=='wire':
    ar=dict(c.execute(select(attempts).where(attempts.c.run_id==runid)).mappings().one());params=copy.deepcopy(ar['parameters']);params['planning_wire']['sha256']='0'*64;c.execute(update(attempts).where(attempts.c.id==ar['id']).values(parameters=params))
   if name=='wireevent':
    ev=dict(c.execute(select(events).where(events.c.run_id==runid,events.c.kind=='NL_PLANNING_WIRE_RESERVED')).mappings().one());data=copy.deepcopy(ev['data']);data['wire']['sha256']='0'*64;c.execute(update(events).where(events.c.id==ev['id']).values(data=data))
   if name=='coherent_unknown':
    bad={'status':'unknown','tokens':None};c.execute(update(attempts).where(attempts.c.run_id==runid).values(usage=bad));ev=dict(c.execute(select(events).where(events.c.run_id==runid,events.c.kind=='NL_PLAN_RECEIVED')).mappings().one());data=copy.deepcopy(ev['data']);data['usage']=bad;c.execute(update(events).where(events.c.id==ev['id']).values(data=data))
   if name=='usage':c.execute(update(attempts).where(attempts.c.run_id==runid).values(usage={'status':'unknown','tokens':None}))
   if name=='result':
    result=copy.deepcopy(rr['result']);result['goal_acceptance']='PASS';c.execute(update(runs).where(runs.c.id==runid).values(result=result))
   if name=='plan':ctx['natural_plan']['plan']['interpretation']['objective']='forged';ctx['natural_plan']['fingerprint']=fingerprint(ctx['natural_plan']['plan']);c.execute(update(runs).where(runs.c.id==runid).values(context=ctx))
   if name=='strip':
    ct=copy.deepcopy(c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==runid)).scalar_one());ct.pop('natural_planning');c.execute(update(run_contracts).where(run_contracts.c.run_id==runid).values(snapshot=ct,fingerprint=fingerprint(ct)))
  before=snapshot(s,[runs,attempts,operations,events,run_contracts]);got=cl.get('/api/runs/'+runid);after=snapshot(s,[runs,attempts,operations,events,run_contracts]);assert before==after;record['tampered_get']=got.status_code
  if positive and got.status_code==200:record['defect']='Tampered completed evidence accepted by GET'
  with s.tx() as c:
   rr=c.execute(select(runs).where(runs.c.id==runid)).mappings().one();ctx=copy.deepcopy(rr['context']);ctx['requests']=0;c.execute(update(runs).where(runs.c.id==runid).values(status='QUEUED',context=ctx))
  n=len(wire);assert Worker(s,sett,goal_planner_transport=httpx.MockTransport(handler)).once();assert len(wire)==n
  end=cl.get('/api/runs/'+runid);record['resumed_get']=end.status_code;record['resumed_status']=end.json().get('status');record['no_resend']=True
  if positive and end.status_code==200 and end.json().get('status')=='PARTIAL':record['resume_defect']='Tampered evidence resumed PARTIAL'
 assert snapshot(s,[grants,principals])==au;assert snapshot(s,[resources])==material
 record['authority_fp']=fingerprint(au);record['authority_after_fp']=fingerprint(snapshot(s,[grants,principals]));record['resource_fp']=fingerprint(material);record['resource_after_fp']=fingerprint(snapshot(s,[resources]));record['attempts']=len(snapshot(s,[attempts])['attempts']);record['operations']=len(snapshot(s,[operations])['operations']);cl.close();s.engine.dispose();return record
for name in ['finish_toolcalls','coherent_unknown']:
 try: r=case(name);out.append(r);print(json.dumps(r),flush=True)
 except Exception as e:out.append({'name':name,'harness_error':type(e).__name__,'trace':traceback.format_exc()});traceback.print_exc()
(BASE/'additional-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
(BASE/'additional-runtime.json').write_text(json.dumps({'goal_planner_file':gp.__file__,'goal_planner_sha':hashlib.sha256(Path(gp.__file__).read_bytes()).hexdigest(),'worker_file':sys.modules['sim2act.worker'].__file__},indent=2))
