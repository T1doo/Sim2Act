import sys,os,json,copy,hashlib,traceback,shutil
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
B=Path('/tmp/natural-plan-confirmation-independent/0cab734');ROOT=B/'source';sys.path.insert(0,str(ROOT/'src'))
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select,update
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store,runs,attempts,operations,events,run_contracts,grants,principals,resources,fingerprint
from sim2act.worker import Worker
from sim2act.goal_planner import policy
import sim2act.goal_planner as module

def snap(s,tables=None):
 with s.tx() as c:return {t.name:sorted([dict(x) for x in c.execute(select(t)).mappings()],key=lambda x:json.dumps(x,sort_keys=True,default=str)) for t in (tables if tables else runs.metadata.sorted_tables)}
def run_case(name):
 p=B/('db-'+name);p.mkdir(exist_ok=True);url='sqlite:///'+str(p/'fixture.db');s=Store(url,test_only=True);s.initialize();owner=s.user('independent A','own-A');s.user('B','own-B');sett=Settings(url,p,mode='mock',goal_planner_provider='intern-s2');cl=TestClient(create_app(s,sett));cl.headers['Authorization']='Bearer own-A';pid=cl.post('/api/projects',json={'name':'independent'}).json()['id'];res=cl.post(f'/api/projects/{pid}/resources',json={'name':'fresh.csv','format':'csv','content':'label,units_q\nz,14\ny,29\n'}).json()['id'];card=cl.post(f'/api/projects/{pid}/goal-cards',json={'title':'new','goal':'读取并合计 units_q，先确认受限计划','known':[],'assumptions':['单位待定'],'unresolved':['语义待审'],'constraints':['只读不外发'],'acceptance_checks':['回读'],'resource_refs':[res]}).json();card=cl.get('/api/goal-cards/'+card['id']).json();auth=snap(s,[grants,principals]);content=snap(s,[resources]);calls=[]
 proposal={'version':'natural-goal-plan.v1','source_goal_fingerprint':card['fingerprint'],'interpretation':{'objective':'手写独立规划','assumptions':['未知单位'],'unresolved':['人工确认意义']},'steps':[{'id':'read','tool_ref':'resource.read','resource_id':res,'depends_on':[]},{'id':'sum','tool_ref':'data.aggregate_csv','resource_id':res,'column':'units_q','depends_on':['read']}]}
 def send(req):calls.append(req.content.decode());return httpx.Response(200,json={'model':'Intern-S2','usage':{'prompt_tokens':10,'completion_tokens':25,'total_tokens':35},'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(proposal)}}]})
 def enqueue(key):
  if name=='legacy':
   lim=Limits(**{k:getattr(sett,k) for k in Limits.model_fields}).model_dump();return s.submit(owner,pid,'',[],key,policy={'limits':{**lim,'max_requests':1,'max_repairs':0},'mode':'mock','request_model':'intern-s2','natural_planning':policy('intern-s2',require_confirmation=False)},goal_source={'card_id':card['id'],'version':card['version'],'fingerprint':card['fingerprint']})
  x=cl.post(f'/api/projects/{pid}/goal-cards/{card["id"]}/planned-runs',json={'expected_version':card['version'],'expected_fingerprint':card['fingerprint'],'request_key':key});assert x.status_code==202,x.text;return x.json()['run_id']
 worker=lambda:Worker(s,sett,goal_planner_transport=httpx.MockTransport(send))
 rid=enqueue('own');assert worker().once();v=cl.get('/api/runs/'+rid);assert v.status_code==200,v.text;v=v.json();record={'case':name,'before_state':v['status'],'initial_attempts':len(snap(s,[attempts])['attempts']),'initial_operations':len(snap(s,[operations])['operations'])}
 if name=='legacy':
  assert v['status']=='PARTIAL' and v['natural_plan']['confirmation_required'] is False;assert v['result']['receipts'][1]['data']['sum']=='43';record['compatible_absent_flag']=True
 else:
  assert v['status']=='WAITING_APPROVAL' and record['initial_operations']==0 and record['initial_attempts']==1;assert v['natural_plan']['confirmed'] is False
  body={'expected_version':v['version'],'expected_plan_fingerprint':v['natural_plan']['fingerprint'],'request_key':'own-confirm'};ep='/api/runs/'+rid+'/confirm-natural-plan';otherid=None
  if name=='foreign':cl.headers['Authorization']='Bearer own-B'
  if name=='stale':body['expected_version']-=1
  if name=='boolversion':body['expected_version']=True
  if name=='callerPASS':body['decision']='PASS'
  if name=='cancel':s.command(owner,rid,'cancel',v['version'])
  if name=='two_run':
   first=cl.post(ep,json=body);assert first.status_code==200;otherid=enqueue('other');assert worker().once();assert worker().once();vv=cl.get('/api/runs/'+otherid).json();
   with s.tx() as c:
    one=c.execute(select(runs).where(runs.c.id==rid)).mappings().one();two=c.execute(select(runs).where(runs.c.id==otherid)).mappings().one();seal=copy.deepcopy(one['context']['natural_plan_confirmation']);ctx=copy.deepcopy(two['context']);ctx['natural_plan_confirmation']=seal;c.execute(update(runs).where(runs.c.id==otherid).values(context=ctx));s.event(c,otherid,'NL_PLAN_CONFIRMED',seal)
   rid=otherid;ep='/api/runs/'+rid+'/confirm-natural-plan';body['expected_version']=vv['version'];body['expected_plan_fingerprint']=vv['natural_plan']['fingerprint']
  if name in ['stripflag','queued','revoke','sealbool','sealplan']:
   if name in ['sealbool','sealplan']:assert cl.post(ep,json=body).status_code==200
   with s.tx() as c:
    rr=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
    if name=='stripflag':
     f=copy.deepcopy(c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==rid)).scalar_one());f['natural_planning'].pop('require_confirmation');c.execute(update(run_contracts).where(run_contracts.c.run_id==rid).values(snapshot=f,fingerprint=fingerprint(f)))
    if name=='queued':c.execute(update(runs).where(runs.c.id==rid).values(status='QUEUED'))
    if name=='revoke':c.execute(update(grants).where(grants.c.resource_id==res).values(revoked=True))
    if name in ['sealbool','sealplan']:
     ctx=copy.deepcopy(rr['context']);seal=ctx['natural_plan_confirmation'];seal['expected_version']=True if name=='sealbool' else seal['expected_version'];
     if name=='sealplan':seal['plan_fingerprint']='0'*64
     ev=c.execute(select(events).where(events.c.run_id==rid,events.c.kind=='NL_PLAN_CONFIRMED')).mappings().one();c.execute(update(events).where(events.c.id==ev['id']).values(data=seal));c.execute(update(runs).where(runs.c.id==rid).values(context=ctx))
  before=snap(s);answer=cl.post(ep,json=body);after=snap(s);record['confirm_http']=answer.status_code;record['confirm_before_fp']=fingerprint(before);record['confirm_after_fp']=fingerprint(after)
  if name in ['normal','replay']:
   assert answer.status_code==200 and answer.json()['status']=='QUEUED';assert len(snap(s,[operations])['operations'])==0
   # replay accepted confirmation on same key, including after durable completion
   before2=snap(s);rep=cl.post(ep,json=body);assert rep.status_code==200 and before2==snap(s);assert worker().once();done=cl.get('/api/runs/'+rid).json();assert done['status']=='PARTIAL' and done['result']['receipts'][1]['data']['sum']=='43';assert len(calls)==1
   record['result_status']=done['status'];record['sum']=done['result']['receipts'][1]['data']['sum'];record['same_key_read_only']=True
   old=snap(s);different=cl.post(ep,json={**body,'request_key':'wrong-key'});assert different.status_code==409 and old==snap(s);assert cl.post(ep,json=body).status_code==200
  elif name=='queued':
   # explicit confirm on forged queued must fail; worker can only return to approval
   assert answer.status_code==409 and before==after;assert worker().once();now=cl.get('/api/runs/'+rid).json();assert now['status']=='WAITING_APPROVAL' and len(calls)==1 and not snap(s,[operations])['operations'];record['worker_no_bypass']=True
  else:
   assert answer.status_code in [400,403,409,422] and before==after,(name,answer.text)
   if name in ['sealbool','sealplan']:assert worker().once();assert not snap(s,[operations])['operations'];assert len(calls)==1
  record['full_table_confirm_zero_write']=before==after
 expected_auth=snap(s,[grants,principals]);assert expected_auth==auth or name=='revoke';assert snap(s,[resources])==content;record['authority_after_fp']=fingerprint(expected_auth);record['authority_original_fp']=fingerprint(auth);record['resource_before_fp']=fingerprint(content);record['resource_after_fp']=fingerprint(snap(s,[resources]));record['provider_calls']=len(calls);record['final_operations']=len(snap(s,[operations])['operations']);cl.close();s.engine.dispose();return record
out=[run_case('two_run')]
(B/'two-run-results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
