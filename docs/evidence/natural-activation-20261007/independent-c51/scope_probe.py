import sys,os,json,copy,hashlib,traceback,time,threading
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
B=Path('/tmp/natural-activation-independent/c51eb29');R=B/'source';sys.path.insert(0,str(R/'src'))
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select,update,event
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from sim2act.api import create_app
from sim2act.db import Store,runs,attempts,operations,events,grants,principals,resources,natural_activations,fingerprint
from sim2act.config import Settings
from sim2act.worker import Worker
from sim2act import natural_activations as a,goal_planner as gp

def rows(s,t):
 with s.tx() as c:return [dict(x) for x in c.execute(select(t)).mappings()]
def snap(s,ts=None):return {t.name:sorted(rows(s,t),key=lambda x:json.dumps(x,sort_keys=True,default=str)) for t in (ts or runs.metadata.sorted_tables)}
def one(name):
 p=B/('db-'+name);p.mkdir(exist_ok=True);url='sqlite:///'+str(p/'fixture.db');s=Store(url,test_only=True);s.initialize();s.user('A','ind-A');s.user('B','ind-B');sett=Settings(url,p,mode='mock',goal_planner_provider='intern-s2',natural_activation_enabled=name!='default',rpm=30);cl=TestClient(create_app(s,sett));cl.headers['Authorization']='Bearer ind-A';pid=cl.post('/api/projects',json={'name':'own'}).json()['id'];rid=cl.post(f'/api/projects/{pid}/resources',json={'name':'fixed','format':'csv','content':'item,quantity_z\na,7\nb,12\n'}).json()['id'];cards={}
 for kind in a.KINDS:
  cid=cl.post(f'/api/projects/{pid}/goal-cards',json=a.synthetic_goal(rid,kind)).json()['id'];cards[kind]=cl.get('/api/goal-cards/'+cid).json()
 au=snap(s,[grants,principals]);rs=snap(s,[resources]);before=snap(s);sql=[]
 def listener(c,cu,st,pa,co,m):sql.append(st.split()[0].upper())
 event.listen(s.engine,'before_cursor_execute',listener);other=TestClient(create_app(s,sett));other.close();event.remove(s.engine,'before_cursor_execute',listener);assert all(x=='SELECT' for x in sql),sql
 draft={'goal_bindings':[{'kind':k,'card_id':v['id'],'expected_version':v['version'],'expected_fingerprint':v['fingerprint']} for k,v in cards.items()],'request_key':'draft-ind'};d=cl.post(f'/api/projects/{pid}/natural-activations',json=draft);rec={'case':name,'api_init_sql_verbs':sql}
 if name=='default':assert d.status_code==400 and before==snap(s);rec['zero_write']=True
 else:
  assert d.status_code==201,d.text;session=d.json();aid=session['id'];ab={'expected_version':session['version'],'expected_scope_fingerprint':session['scope_fingerprint'],'request_key':'approve-ind','consent':a.CONSENT}
  if name=='closedclock':
   old=snap(s);response=cl.post('/api/natural-activations/'+aid+'/approve',json={**ab,'clock':1,'caps':{'requests':3}});assert response.status_code==422 and old==snap(s);rec['http']=422;rec['full_before_fp']=fingerprint(old);rec['full_after_fp']=fingerprint(snap(s))
  else:
   session=cl.post('/api/natural-activations/'+aid+'/approve',json=ab).json();assert session['status']=='APPROVED',session
   if name in ['foreign_scope','coherent_caps','coherent_expiry','current_card_version','account_changed']:
    if name=='foreign_scope':cl.headers['Authorization']='Bearer ind-B'
    if name in ['coherent_caps','coherent_expiry','current_card_version']:
     with s.tx() as c:
      row=c.execute(select(natural_activations).where(natural_activations.c.id==aid)).mappings().one()
      if name=='coherent_caps':
       scope=copy.deepcopy(row['scope']);scope['caps']['requests']=3;c.execute(update(natural_activations).where(natural_activations.c.id==aid).values(scope=scope,scope_fingerprint=fingerprint(scope)))
      if name=='coherent_expiry':
       ap=copy.deepcopy(row['approval']);ap['expires_at']+=1;c.execute(update(natural_activations).where(natural_activations.c.id==aid).values(approval=ap,approval_fingerprint=fingerprint(ap)))
      if name=='current_card_version':
       from sim2act.db import goal_cards
       c.execute(update(goal_cards).where(goal_cards.c.id==cards['sum_quantity_z']['id']).values(version=2))
    if name=='account_changed':
     cl.close();cl=TestClient(create_app(s,replace(sett,quota_subject='different-subject')));cl.headers['Authorization']='Bearer ind-A'
    old=snap(s)
    if name in ['account_changed','current_card_version']:
     ca=cards['sum_quantity_z'];response=cl.post(f"/api/natural-activations/{aid}/goal-cards/{ca['id']}/planned-runs",json={'expected_version':ca['version'],'expected_fingerprint':ca['fingerprint'],'request_key':'deny-current'})
    else:response=cl.get('/api/natural-activations/'+aid)
    assert response.status_code in [400,403,409] and old==snap(s),response.text
    rec.update(http=response.status_code,code=response.json()['error']['code'],full_before_fp=fingerprint(old),full_after_fp=fingerprint(snap(s)),provider_calls=0,attempts=0,operations=0)
    assert au==snap(s,[grants,principals]) and rs==snap(s,[resources]);rec['authority_original_fp']=fingerprint(au);rec['authority_after_fp']=fingerprint(snap(s,[grants,principals]));rec['resource_before_fp']=fingerprint(rs);rec['resource_after_fp']=fingerprint(snap(s,[resources]));cl.close();s.engine.dispose();return rec
   oldnow=a.now;originalprovider=gp.configured_provider;originaldispatch=gp.dispatch;count=[]
   def submit(kind,key):
    c=cards[kind];return cl.post(f'/api/natural-activations/{aid}/goal-cards/{c["id"]}/planned-runs',json={'expected_version':c['version'],'expected_fingerprint':c['fingerprint'],'request_key':key})
   def revoke():
    x=cl.post('/api/natural-activations/'+aid+'/revoke',json={'expected_version':session['version'],'expected_scope_fingerprint':session['scope_fingerprint'],'request_key':'revoke-ind'});assert x.status_code==200,x.text
   def plan(kind):return {'version':'natural-goal-plan.v1','source_goal_fingerprint':cards[kind]['fingerprint'],'interpretation':{'objective':'独立手写受限方案','assumptions':['假设字段含义未验收'],'unresolved':['真实目标意义仍待确认']},'steps':[{'id':'material','tool_ref':'resource.read' if kind=='read_preview' else 'data.aggregate_csv','resource_id':rid,'depends_on':[],**({'column':'quantity_z'} if kind=='sum_quantity_z' else {})}]}
   kindbox=['sum_quantity_z']
   def handler(req):
    count.append(req.content.decode());obj=json.loads(req.content);assert obj['max_tokens']==512 and obj['tools']==[]
    if name=='secret':raise RuntimeError('PRIVATE_SENTINEL_4321')
    response={'model':'Intern-S2','usage':{'prompt_tokens':12,'completion_tokens':28,'total_tokens':40},'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(plan(kindbox[0]))}}]}
    if name=='partial':response['usage']={'completion_tokens':28}
    if name=='truncated':response['choices'][0]['finish_reason']='length';response['private_metadata']='PRIVATE_SENTINEL_4321'
    if name=='invalidUnicode':response['choices'][0]['message']['content']='\ud800';response['model']='\ud800'
    if name=='mismatch':response['choices'][0]['message']['content']=json.dumps(plan('read_preview'))
    return httpx.Response(200,content=json.dumps(response).encode('ascii'))
   worker=lambda:Worker(s,sett,goal_planner_transport=httpx.MockTransport(handler))
   if name=='revoke_guard':
    def provider(w):
     v=originalprovider(w);orig=v.request_serialized
     def call(body,guard):revoke();return orig(body,guard)
     v.request_serialized=call;return v
    gp.configured_provider=provider
   response=submit('sum_quantity_z','run-ind');assert response.status_code==202,response.text;runid=response.json()['run_id']
   if name=='duplicatekind':
    second=submit('sum_quantity_z','parallel-ind');assert second.status_code==202;bar=threading.Barrier(2)
    def execute(_):bar.wait();return worker().once()
    with ThreadPoolExecutor(max_workers=2) as ex:list(ex.map(execute,range(2)))
    assert len(count)==len(rows(s,attempts))==1 and not rows(s,operations);rec['concurrent_slot_count']=1
   else:assert worker().once()
   view=cl.get('/api/runs/'+runid);assert view.status_code==200,view.text;view=view.json()
   if name in ['normal2','revoke_effect','expired_confirm','ledgerclear','grantrevoke']:
    assert view['status']=='WAITING_APPROVAL' and not rows(s,operations);body={'expected_version':view['version'],'expected_plan_fingerprint':view['natural_plan']['fingerprint'],'request_key':'confirm-ind'}
    if name=='expired_confirm':a.now=lambda:session['approval']['expires_at'];old=snap(s);den=cl.post('/api/runs/'+runid+'/confirm-natural-plan',json=body);assert den.status_code==403 and old==snap(s);rec['full_before_fp']=fingerprint(old);rec['full_after_fp']=fingerprint(snap(s));assert cl.get('/api/runs/'+runid).status_code==200
    elif name=='ledgerclear':
     with s.tx() as c:c.execute(update(natural_activations).where(natural_activations.c.id==aid).values(ledger=[]))
     old=snap(s);den=cl.get('/api/natural-activations/'+aid);assert den.status_code==409 and old==snap(s);rec['full_before_fp']=fingerprint(old);rec['full_after_fp']=fingerprint(snap(s))
    elif name=='grantrevoke':
     with s.tx() as c:c.execute(update(grants).where(grants.c.resource_id==rid).values(revoked=True))
     old=snap(s);den=cl.post('/api/runs/'+runid+'/confirm-natural-plan',json=body);assert den.status_code==403 and old==snap(s);rec['full_before_fp']=fingerprint(old);rec['full_after_fp']=fingerprint(snap(s))
    else:
     ok=cl.post('/api/runs/'+runid+'/confirm-natural-plan',json=body);assert ok.status_code==200,ok.text
     if name=='revoke_effect':
      def dispatch(*args,**kwargs):revoke();return originaldispatch(*args,**kwargs)
      gp.dispatch=dispatch
     assert worker().once()
     if name=='normal2':
      result=cl.get('/api/runs/'+runid).json();assert result['result']['receipts'][0]['data']['sum']=='19' and result['status']=='PARTIAL';kindbox[0]='read_preview';second=submit('read_preview','second-ind');assert second.status_code==202,second.text;rr=second.json()['run_id'];assert worker().once();v=cl.get('/api/runs/'+rr).json();bb={'expected_version':v['version'],'expected_plan_fingerprint':v['natural_plan']['fingerprint'],'request_key':'confirm-read-ind'};assert cl.post('/api/runs/'+rr+'/confirm-natural-plan',json=bb).status_code==200;assert worker().once();assert len(count)==len(rows(s,attempts))==len(rows(s,operations))==2
      third=submit('sum_quantity_z','third-ind');assert third.status_code==202;assert worker().once();assert len(count)==len(rows(s,attempts))==2;rec['at_most_two_actual_sends']=True
     else:assert not rows(s,operations) and len(count)==1
   elif name!='duplicatekind':
    assert not rows(s,operations)
    if name in ['partial','secret']:
     nxt=submit('read_preview','unknown-next');assert nxt.status_code==400 and nxt.json()['error']['code']=='OUTCOME_UNKNOWN',nxt.text
    if name=='truncated':
     ar=rows(s,attempts)[0];assert ar['response']['content'] and ar['response_model']=='Intern-S2' and ar['usage']['tokens']['total_tokens']==40;assert len(ar['parameters']['planning_received_response_fingerprint'])==64
    if name=='invalidUnicode':ar=rows(s,attempts)[0];assert ar['response'] is None and ar['response_model'] is None and len(ar['parameters']['planning_received_response_fingerprint'])==64
   assert 'PRIVATE_SENTINEL_4321' not in json.dumps(snap(s),ensure_ascii=True)
   rec['provider_calls']=len(count);rec['attempts']=len(rows(s,attempts));rec['operations']=len(rows(s,operations));rec['run_state']=view['status'];rec['activation_slot_count']=len(rows(s,natural_activations)[0]['ledger']);rec['attempt_usage']=[x['usage'] for x in rows(s,attempts)];a.now=oldnow;gp.configured_provider=originalprovider;gp.dispatch=originaldispatch
 rec['authority_original_fp']=fingerprint(au);rec['authority_after_fp']=fingerprint(snap(s,[grants,principals]));assert au==snap(s,[grants,principals]) or name=='grantrevoke';assert rs==snap(s,[resources]);rec['resource_before_fp']=fingerprint(rs);rec['resource_after_fp']=fingerprint(snap(s,[resources]));cl.close();s.engine.dispose();return rec
out=[]
for name in ['foreign_scope','coherent_caps','coherent_expiry','current_card_version','account_changed']:
 try:x=one(name);out.append(x);print(json.dumps(x),flush=True)
 except Exception:out.append({'case':name,'harness_error':traceback.format_exc()});traceback.print_exc()
(B/'scope-results.json').write_text(json.dumps(out,indent=2));(B/'scope-runtime.json').write_text(json.dumps({'module':a.__file__,'module_sha256':hashlib.sha256(Path(a.__file__).read_bytes()).hexdigest(),'planner':gp.__file__,'worker':sys.modules['sim2act.worker'].__file__},indent=2))
