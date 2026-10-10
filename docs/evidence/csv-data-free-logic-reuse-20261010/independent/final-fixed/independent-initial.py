import base as h
import json,pathlib,hashlib,subprocess,secrets,copy,traceback,time,csv,io
from contextlib import contextmanager
from decimal import Decimal
from sqlalchemy import text,event
from sim2act import csv_logic_reuse as logic
from sim2act import csv_dag_instances as ins
from sim2act import csv_dag as dag
from sim2act.errors import DomainError
ROOT=pathlib.Path(__file__).parent; REPO=pathlib.Path('/workspace/Sim2Act'); SHA='4a4b6949fd159bd35c1ed1ed9d111426a27b706f'
TARGET='tag,revenue,quantity\r\n"新,甲",3.125,9\r\n乙,-1.50,-2\r\n丙,6.000,5\r\n'
records=[];checks=[]
def ck(v,msg):
 assert v,msg;checks.append(msg)
def freeze(name):
 m=json.loads(pathlib.Path('/tmp/sim2act-csv-data-free-logic-20261010/source-freeze-fixed.json').read_text());ck(m['source_sha']==SHA and len(m['files'])==378,'exact freeze source/count');out={}
 for f in m['files']:
  p=f['path'];b=(REPO/p).read_bytes();g=subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO);assert b==g and hashlib.sha256(b).hexdigest()==f['sha256'] and len(b)==f['bytes'],p;out[p]=f
 ck(sum(p.startswith('src/') for p in out)==72,'72 source files exact');d={'source_sha':SHA,'count':378,'products':72,'Git_worktree_manifest_match':True,'files':out};(ROOT/('source-'+name+'.json')).write_text(json.dumps(d,indent=2));return d

def env(folder,backend):
 folder.mkdir(parents=True,exist_ok=True)
 if backend=='sqlite':return h.env(folder),None
 url='postgresql+psycopg://postgres@/logic_reuse_fixture?host=/tmp/sim2act-csv-data-free-logic-20261010/pg-socket';st=h.Store(url,test_only=True);schema='test_'+secrets.token_hex(16)
 with st.engine.begin() as c:c.execute(text('CREATE SCHEMA "'+schema+'"'))
 st.engine=st.engine.execution_options(schema_translate_map={None:schema});st.initialize(fresh_test_schema=schema);a=st.user('Review A','review-A');b=st.user('Review B','review-B');s=h.Settings(url,folder,mode='mock');cl=h.TestClient(h.create_app(st,s));cl.headers['Authorization']='Bearer review-A';pid=cl.post('/api/projects',json={'name':'Independent data-free logic'}).json()['id'];return [st,s,cl,a,b,pid,None],schema

def req(e,m,p,b=None,status=200):return h.request(e,m,p,b,status)
def release(e,report):
 pid=e[5];rid=req(e,'POST',f'/api/projects/{pid}/resources',{'name':'Private original.csv','format':'csv','content':h.RAW},201)['id'];e[6]=rid
 app=req(e,'POST',f'/api/projects/{pid}/apps/csv-preview',{'name':'Old sealed source','goal':'private original secret old-column goal','resource_id':rid},201)
 alias=req(e,'POST',f'/api/projects/{pid}/apps/csv-preview',{'name':'Old data alias must be excluded','goal':'Alias not a fresh source','resource_id':rid},201)
 app=req(e,'GET','/api/apps/'+app['id']);g=req(e,'POST',f'/api/projects/{pid}/apps/{app["id"]}/delivery-graph/derive',{'expected_candidate_fingerprint':app['fingerprint'],'request_key':'own-old-graph'},201)
 nodes=[dict(step_id='readbook',action='resource.read',depends_on=[],inputs={'resource_id':dict(source='data',ref='source',field='resource_id')}),dict(step_id='summarize',action='data.aggregate_csv',column='amount',depends_on=['readbook'],inputs={'resource_id':dict(source='step',ref='readbook',field='resource_id'),'column':dict(source='input',field='summarize_column')})]
 if report:nodes.append(dict(step_id='notes',action='intern.csv_report.v1',depends_on=['summarize'],inputs={k:dict(source='step',ref='summarize',field=k) for k in ['resource_id','column','count','sum','source_hash']}))
 p=req(e,'POST',f'/api/projects/{pid}/apps/{app["id"]}/csv-dag',{'expected_candidate_fingerprint':app['fingerprint'],'expected_graph_fingerprint':g['graph_fingerprint'],'column':'amount','composition':{'version':'csv.composition.v1','nodes':nodes},'request_key':'own-source-plan'},201)
 a=req(e,'POST',f'/api/projects/{pid}/apps/{app["id"]}/csv-dag/{p["request_key"]}/runs',{'expected_plan_fingerprint':p['plan_fingerprint'],'request_key':'own-source-run','consent':'CONFIRM_EXACT_OFFLINE_CSV_DAG'},202);h.work(e,a['run_id'])
 _,_,_,_,rel=h.make_release(e,(app['id'],rid,p,a['run_id']));return {'app':app,'alias':alias,'rid':rid,'run':a['run_id'],'plan':p,'release':rel}
def authorize(e,src):
 body={'expected_release_fingerprint':src['release']['fingerprint'],'consent':logic.CONSENT,'request_key':'independent-explicit-authority'};obj=req(e,'POST',f'/api/internal/releases/{src["release"]["id"]}/csv-logic-authorizations',body,201)['logic'];ck(obj['id']=='csvlogic_'+h.fingerprint([e[3],src['release']['id'],body['request_key']])[:32],'authority id independently derived');return obj,body

def target_setup(e,src,obj):
 pid=e[5];rid=req(e,'POST',f'/api/projects/{pid}/resources',{'name':'Independent brand-new.csv','format':'csv','content':TARGET},201)['id'];app=req(e,'POST',f'/api/projects/{pid}/apps/csv-preview',{'name':'Current new data','goal':'Current independently authorized target','resource_id':rid},201)
 # Register first, then actual public grant revocations; derive target last.
 for g in req(e,'GET',f'/api/projects/{pid}/grants'):
  if g['resource_id']==src['rid'] and not g['revoked']:req(e,'POST',f'/api/grants/{g["id"]}/revoke',{'command':'revoke','version':g['revision']})
 r=e[2].get('/api/resources/'+src['rid']);ck(r.status_code==403,'original actual data access still denied before deletion')
 with e[0].engine.begin() as c:c.execute(h.delete(h.resources).where(h.resources.c.id==src['rid']))
 app=req(e,'GET','/api/apps/'+app['id']);g=req(e,'POST',f'/api/projects/{pid}/apps/{app["id"]}/delivery-graph/derive',{'expected_candidate_fingerprint':app['fingerprint'],'request_key':'own-new-current-graph'},201)
 body={'expected_logic_fingerprint':obj['fingerprint'],'target_app_id':app['id'],'expected_candidate_fingerprint':app['fingerprint'],'expected_graph_fingerprint':g['graph_fingerprint'],'expected_resource_id':rid,'expected_source_hash':app['candidate']['source_hash'],'column':'revenue','request_key':'own-fresh-material'}
 return app,body

def watch(e,src):
 logs=[]
 def observe(conn,cursor,statement,parameters,context,executemany):
  if statement.lstrip().upper().startswith('SELECT'):logs.append({'sql':statement,'parameters':repr(parameters)})
 event.listen(e[0].engine,'before_cursor_execute',observe);return logs,observe

def seal_rows(e,kind,key,change):
 t=h.delivery_graph_requests
 with e[0].engine.begin() as c:
  rows=c.execute(h.select(t).where(t.c.kind.in_([kind,kind+'_seal']),t.c.request_key==key)).mappings().all();assert len(rows)==2
  for r in rows:
   s=copy.deepcopy(r['snapshot']);change(s);c.execute(h.update(t).where(t.c.app_id==r['app_id'],t.c.principal_id==r['principal_id'],t.c.kind==r['kind'],t.c.request_key==r['request_key']).values(snapshot=s,fingerprint=h.fingerprint(s),request_fingerprint=h.fingerprint(s['request'])))

@contextmanager
def restore(e,tables):
 saved={t.name:h.snapshot(e)[t.name] for t in tables}
 try:yield
 finally:
  with e[0].engine.begin() as c:
   for t in tables:
    c.execute(h.delete(t))
    if saved[t.name]:c.execute(h.insert(t),saved[t.name])

def denied(e,label,m,path,b=None,expected=None):
 before=h.snapshot(e);r=e[2].request(m,path,json=b) if b is not None else e[2].request(m,path);after=h.snapshot(e);ck(r.status_code in (400,403,409,422),label+' fails closed');ck(before==after,label+' entire database zero write')
 if expected:ck(r.status_code==expected,label+' exact expected status')
 out={'backend':e[7],'case':label,'method':m,'path':path,'body':b,'status':r.status_code,'response':r.json(),'all_tables_zero_write':True};records.append(out);return r

def material_plan(e,obj,body):return req(e,'POST',f'/api/internal/csv-logics/{obj["id"]}/material-plans',body,201)
def run_plan(e,m,key):
 p=m['plan'];a=req(e,'POST',f'/api/projects/{e[5]}/apps/{p["app_id"]}/csv-dag/{p["request_key"]}/runs',{'expected_plan_fingerprint':p['plan_fingerprint'],'consent':'CONFIRM_EXACT_OFFLINE_CSV_DAG','request_key':key},202);h.work(e,a['run_id']);return a

def business(e,src,obj,auth,app,body,report):
 log,observer=watch(e,src);before=h.snapshot(e)
 got=req(e,'GET',f'/api/projects/{e[5]}/csv-logics');ck(got['items']==[obj],'project-global cold registry canonical exact')
 opts=req(e,'GET',f'/api/internal/csv-logics/{obj["id"]}/materials');ck([x['target_app_id'] for x in opts['items']]==[app['id']],'old app and old data alias excluded before loads');ck(h.snapshot(e)==before,'registry/options all-table read-only')
 txt=json.dumps(obj,ensure_ascii=False)
 for s in [src['rid'],src['app']['id'],src['run'],src['release']['id'],src['release']['fingerprint'],src['release']['snapshot']['execution_source']['source_hash'],'private_audit','amount','summarize','secret']:ck(s not in txt,'public logic omits original private '+s)
 m=material_plan(e,obj,body);p=m['plan'];ck(p['request_key']==logic.PREFIX+h.fingerprint([obj['id'],body['request_key']])[:48],'new deterministic plan key');ck(p['logical_reuse']['logic_fingerprint']==obj['fingerprint'],'new plan logically bound');a=run_plan(e,m,'own-new-run')
 proof=req(e,'GET','/api/csv-dag/runs/'+a['run_id']);expected=sum(Decimal(r['revenue']) for r in csv.DictReader(io.StringIO(TARGET)));out=proof['result']['output_by_step']['aggregate'];ck(Decimal(out['sum'])==expected and out['count']==3 and type(out['count']) is int,'independent Decimal target7.625/count3 actual aggregate');ck(out['resource_id']==body['expected_resource_id'] and out['source_hash']==hashlib.sha256(TARGET.encode()).hexdigest(),'new source actual bytes bound');ck(len(proof['steps'])==(3 if report else 2),'all new 2/3 step receipts');
 if report:ck(proof['result']['output_by_step']['report']['text']=='列 revenue；行数 3；合计 7.625','new report exact full tuple text')
 _,_,_,_,rel=h.make_release(e,(app['id'],body['expected_resource_id'],p,a['run_id']));i=h.make_instance(e,rel);made,ib=h.enqueue(e,i,rel,'quantity','own-cold-quantity');h.work(e,made['run_id']);cold=req(e,'GET','/api/internal/instances/'+i['id']);v=cold['data'][0]['data']['result'];ck(v['count']==3 and type(v['count']) is int and Decimal(v['sum'])==sum(Decimal(r['quantity']) for r in csv.DictReader(io.StringIO(TARGET))),'cold instance second input quantity12 typed result');ck(cold['data_version']==1,'new independent instance ledger1');ck(cold['release_id']==rel['id'] and rel['id']!=src['release']['id'],'new immutable Release and Instance');ck(cold['runs'][0]['plan_key'].startswith(logic.INSTANCE_PREFIX),'derived reserved logical instance plan prefix');ck(cold['runs'][0]['proof']['plan']['logical_reuse']['logic_id']==obj['id'],'derived plan exact logical inheritance')
 with e[0].engine.connect() as c:ck(c.execute(h.select(h.attempts)).first() is None,'zero actual/model mock requests')
 event.remove(e[0].engine,'before_cursor_execute',observer)
 bad=[x for x in log if ('resources' in x['sql'] and src['rid'] in x['parameters']) or ('operations' in x['sql'] and src['run'] in x['parameters']) or ('runs.result' in x['sql'] and src['run'] in x['parameters'])];ck(not bad,'all post-mint flows never SELECT old CSV/Operation/Run.result')
 (e[1].data_dir/'source-read-observer.json').write_text(json.dumps({'old_resource':src['rid'],'old_run':src['run'],'SELECTs':log,'forbidden_reads':bad},indent=2))
 records.append({'backend':e[7],'case':'business-report' if report else 'business-two-step','status':'PASS','logic':obj,'source':src,'target':app,'body':body,'material':m,'run':a,'newrelease':rel,'newinstance':i,'cold':cold,'source_csv':h.RAW,'target_csv':TARGET,'independent_sums':['7.625','12'],'old_reads_zero':True})
 return m,rel,i,made,cold

def negatives(e,src,obj,auth,app,body,m,rel,i,made,cold):
 lid=obj['id'];path=f'/api/internal/csv-logics/{lid}';proposal=path+'/material-plans';t=h.delivery_graph_requests
 with restore(e,[t]):
  seal_rows(e,logic.AUTH_KIND,lid,lambda s:s['request'].update(request_key='joint-tampered-key'));denied(e,'joint-authority-requestkey','GET',path,expected=409);denied(e,'joint-authority-proposal','POST',proposal,body,409)
 with restore(e,[t]):
  seal_rows(e,logic.AUTH_KIND,lid,lambda s:s['response'].update(model_requests=False));denied(e,'joint-auth-bool-int','GET',path,expected=409)
 with restore(e,[t]):
  with e[0].engine.begin() as c:c.execute(h.delete(t).where(t.c.kind==logic.AUTH_KIND+'_seal',t.c.request_key==lid))
  denied(e,'missing-authority-seal','GET',path,expected=409)
 for label,tab,pred,mut in [('source-run-version',h.runs,h.runs.c.id==src['run'],lambda row:{'version':row['version']+1}),('source-audit-project',h.internal_releases,h.internal_releases.c.id==src['release']['id'],lambda row:{'project_id':'project_'+'f'*32})]:
  with restore(e,[tab]):
   with e[0].engine.begin() as c:
    row=c.execute(h.select(tab).where(pred)).mappings().one();c.execute(h.update(tab).where(pred).values(**mut(row)))
   denied(e,label,'GET',path,expected=409)
 with restore(e,[t]):
  with e[0].engine.begin() as c:c.execute(h.delete(t).where(t.c.kind=='csv_dag_release_origin_seal',t.c.request_key==src['release']['approval_id']))
  denied(e,'old-source-family-seal-missing','GET',path,expected=409)
 for field,val in [('column','missing'),('expected_resource_id',src['rid']),('expected_source_hash','0'*64),('target_app_id',src['app']['id']),('target_app_id',src['alias']['id'])]:
  denied(e,'bad-'+field+'-'+val,'POST',proposal,{**body,field:val,'request_key':'deny-'+field},None)
 denied(e,'samekey-change-column','POST',proposal,{**body,'column':'quantity'})
 e[2].headers['Authorization']='Bearer review-B';denied(e,'foreign-owner','GET',path,expected=403);e[2].headers['Authorization']='Bearer review-A'
 with restore(e,[h.grants]):
  gs=req(e,'GET',f'/api/projects/{e[5]}/grants');g=next(g for g in gs if g['resource_id']==body['expected_resource_id'] and g['principal_id']==app['runtime_id'] and not g['revoked']);req(e,'POST',f'/api/grants/{g["id"]}/revoke',{'command':'revoke','version':g['revision']});denied(e,'target-current-runtime-grant-revoked','POST',proposal,{**body,'request_key':'revoked-target'})
 with restore(e,[h.app_drafts]):
  with e[0].engine.begin() as c:
   row=c.execute(h.select(h.app_drafts).where(h.app_drafts.c.id==app['id'])).mappings().one();candidate=copy.deepcopy(row['candidate']);candidate['goal']['known']='Changed current target version';c.execute(h.update(h.app_drafts).where(h.app_drafts.c.id==app['id']).values(candidate=candidate,fingerprint=h.fingerprint(candidate)))
  denied(e,'target-current-version-changed','POST',proposal,{**body,'request_key':'changed-version'})
 originalTime=logic.time
 try:
  logic.time=type('IndependentExpiredClock',(),{'time':staticmethod(lambda:obj['expires_at']+1)})
  denied(e,'expired-logic-current-use','POST',proposal,{**body,'request_key':'expired-key'})
 finally:logic.time=originalTime
 with restore(e,[h.internal_approvals,t]):
  req(e,'POST',path+'/revoke',{'expected_logic_fingerprint':obj['fingerprint'],'consent':'REVOKE_DATA_FREE_CSV_LOGIC','request_key':'own-explicit-revoke'});denied(e,'revoked-logic-proposal','POST',proposal,{**body,'request_key':'revoked-key'})
  with e[0].engine.begin() as c:c.execute(h.update(h.internal_approvals).where(h.internal_approvals.c.id==lid).values(consumed=False))
  denied(e,'consumed-reset-still-revoked','POST',proposal,{**body,'request_key':'reset-consumed'})
 with restore(e,[t,h.runs,h.events,h.operations]):
  dp=cold['runs'][0]['proof']['plan'];key=dp['request_key']
  with e[0].engine.begin() as c:
   c.execute(h.delete(t).where(t.c.kind.in_([logic.DERIVED,logic.DERIVED+'_seal']),t.c.request_key==key))
   rows=c.execute(h.select(t).where(t.c.request_key==key,t.c.kind.in_(['csv_dag_plan','csv_dag_plan_seal']))).mappings().all()
   for row in rows:
    s=copy.deepcopy(row['snapshot']);s['request'].pop('logic_origin',None);s['response'].pop('logical_reuse',None);s['response'].pop('plan_fingerprint',None);s['response']['plan_fingerprint']=h.fingerprint(s['response']);c.execute(h.update(t).where(t.c.app_id==row['app_id'],t.c.principal_id==row['principal_id'],t.c.kind==row['kind'],t.c.request_key==key).values(snapshot=s,fingerprint=h.fingerprint(s),request_fingerprint=h.fingerprint(s['request'])))
  denied(e,'derived-prefix-all-origins-marker-stripped','GET',f'/api/projects/{e[5]}/apps/{app["id"]}/csv-dag/{key}',expected=409)
 tight=h.Settings(e[1].database_url,e[1].data_dir,max_tools=1);oldclient=e[2];e[2]=h.TestClient(h.create_app(e[0],tight));e[2].headers['Authorization']='Bearer review-A'
 try:denied(e,'current-platform-budget-tight','POST',proposal,{**body,'request_key':'tight-cap'})
 finally:e[2].close();e[2]=oldclient
 denied(e,'original-release-live-get-denied','GET','/api/internal/releases/'+src['release']['id']);denied(e,'original-source-run-live-get-denied','GET','/api/csv-dag/runs/'+src['run']);denied(e,'unpreauthorized-stale-source-no-new-mint','POST',f'/api/internal/releases/{src["release"]["id"]}/csv-logic-authorizations',{**auth,'request_key':'unpreauthorized-new-key'})


def expiry_after_typed(e,src,obj,rel,i):
 prior=req(e,'GET','/api/internal/instances/'+i['id']);made,_=h.enqueue(e,prior,rel,'revenue','own-posttyped-expiry');old=ins.commit_result;oldTime=logic.time;observed={}
 def final_guard_attack(store,c,job,bound,result,limits):
  value=old(store,c,job,bound,result,limits)
  row=c.execute(h.select(h.internal_instance_data).where(h.internal_instance_data.c.instance_id==i['id'],h.internal_instance_data.c.version==2)).mappings().first();assert row is not None;observed['typed_insert_seen']=dict(row);observed['operations_at_final']=[dict(r) for r in c.execute(h.select(h.operations).where(h.operations.c.run_id==made['run_id'])).mappings()];logic.time=type('IndependentExpiredClock',(),{'time':staticmethod(lambda:obj['expires_at']+1)});return value
 ins.commit_result=final_guard_attack
 try:h.work(e,made['run_id'])
 finally:ins.commit_result=old;logic.time=oldTime
 ck(bool(observed.get('typed_insert_seen')),'actual typed insert observed before expiry transition')
 with e[0].engine.connect() as c:
  ds=[dict(r) for r in c.execute(h.select(h.internal_instance_data).where(h.internal_instance_data.c.instance_id==i['id'])).mappings()];instance=c.execute(h.select(h.internal_instances).where(h.internal_instances.c.id==i['id'])).mappings().one();op=[dict(r) for r in c.execute(h.select(h.operations).where(h.operations.c.run_id==made['run_id'])).mappings()];job=c.execute(h.select(h.runs).where(h.runs.c.id==made['run_id'])).mappings().one()
 ck(len(ds)==1 and instance['data_version']==1,'post-typed expired authority rolls back all final typed/version writes');ck(h.fingerprint(op)==h.fingerprint(observed['operations_at_final']),'all previously committed Operation receipts retained');ck(job['status']!='SUCCEEDED','expired final commit cannot mark success');records.append({'backend':e[7],'case':'post-typed-expiry-atomic-rollback','run_id':made['run_id'],'status':'PASS','job_status':job['status'],'job_result':job['result'],'observed':observed,'remaining_typed':ds,'operations_unchanged':True})


def suite(backend,report):
 folder=ROOT/(backend+('-report' if report else '-two'));e,schema=env(folder,backend);e.append(backend);begin=len(checks)
 try:
  src=release(e,report);obj,auth=authorize(e,src);app,body=target_setup(e,src,obj);m,rel,i,made,cold=business(e,src,obj,auth,app,body,report)
  (folder/'fixture.json').write_text(json.dumps({'source':src,'logic':obj,'authbody':auth,'target':app,'material_body':body,'material':m,'release':rel,'instance':i,'cold':cold},indent=2,ensure_ascii=False,default=str))
  if report:negatives(e,src,obj,auth,app,body,m,rel,i,made,cold);expiry_after_typed(e,src,obj,rel,i)
  print(json.dumps({'backend':backend,'family':'report' if report else 'two','status':'PASS','checks':len(checks)-begin}),flush=True)
 except Exception:
  (folder/'HARNESS_OR_CASE_FAILURE.log').write_text(traceback.format_exc());raise
 finally:
  e[2].close()
  if schema:
   with e[0].engine.begin() as c:c.execute(text('DROP SCHEMA "'+schema+'" CASCADE'));assert c.execute(text('SELECT count(*) FROM pg_namespace WHERE nspname=:n'),{'n':schema}).scalar_one()==0
   (folder/'own-schema-cleanup.json').write_text(json.dumps({'schema':schema,'own_schema_absent':True,'parent_fixtures_untouched':True}))
  e[0].engine.dispose()
if __name__=='__main__':
 freeze('before')
 try:
  for backend in ['sqlite','pg']:
   for report in [False,True]:suite(backend,report)
 finally:(ROOT/'BACKEND_RESULTS.json').write_text(json.dumps({'records':records,'checks':checks,'check_count':len(checks)},indent=2,ensure_ascii=False,default=str));freeze('after')
