from common import *
from sim2act import csv_material_reuse as material
from sim2act.contracts import validate_value
import shutil,traceback,time
TARGET='label,net,units\r\n"新,材",-2.125,11\r\n南,8.50,-4\r\n尾,0.625,2\r\n'
checks=[];cases=[];started=time.monotonic();freeze('before')
def ck(v,label):assert v,label;checks.append(label)
def target(e,raw=TARGET,suffix='one'):
 rid=request(e,'POST',f'/api/projects/{e[5]}/resources',{'name':'Independent target '+suffix+'.csv','format':'csv','content':raw},201)['id'];app=request(e,'POST',f'/api/projects/{e[5]}/apps/csv-preview',{'name':'Target '+suffix,'goal':'Different finite authorized material','resource_id':rid},201);app=request(e,'GET','/api/apps/'+app['id']);g=request(e,'POST',f'/api/projects/{e[5]}/apps/{app["id"]}/delivery-graph/derive',{'expected_candidate_fingerprint':app['fingerprint'],'request_key':'target-'+suffix},201);return app,rid,g
def body(rel,a,rid,g):return dict(expected_release_fingerprint=rel['fingerprint'],target_app_id=a['id'],expected_candidate_fingerprint=a['fingerprint'],expected_graph_fingerprint=g['graph_fingerprint'],expected_resource_id=rid,expected_source_hash=a['candidate']['source_hash'],column='net',request_key='independent-material')
def openclone(base,folder):
 folder.mkdir(exist_ok=True);shutil.copy2(base/'db.sqlite',folder/'db.sqlite');url='sqlite:///'+str(folder/'db.sqlite');st=Store(url,test_only=True);s=Settings(url,folder,mode='mock');cl=TestClient(create_app(st,s));cl.headers['Authorization']='Bearer review-A';return [st,s,cl,None,None,None,None]
for mode in [False,True]:
 name='report' if mode else 'v1';folder=ROOT/('positive-'+name);e=env(folder);begin=len(checks)
 try:
  aid,oldrid,p,source,rel=make_release(e,fixture(e,mode));oldi=make_instance(e,rel);oldrun,_=enqueue(e,oldi,rel);work(e,oldrun['run_id']);a,rid,g=target(e);a2,rid2,g2=target(e,TARGET.replace('8.50','9.50'),'two');b=body(rel,a,rid,g);baseline=snapshot(e);(folder/'fixture.json').write_text(json.dumps(dict(source_app=aid,source_run=source,release=rel,old_instance=oldi,oldrun=oldrun,target_app=a,target_resource=rid,target_graph=g,second_app=a2,second_resource=rid2,second_graph=g2,body=b,project=e[5],owner=e[3]),indent=2));e[2].close();e[0].engine.dispose();shutil.copy2(folder/'db.sqlite',folder/'baseline.sqlite');e=openclone(folder,ROOT/('business-'+name));e[5]=b['project'] if 'project' in b else rel['project_id']
  opts=request(e,'GET',f'/api/internal/releases/{rel["id"]}/csv-materials');ck(set(x['resource_id'] for x in opts['items'])=={rid,rid2},'only distinct registered current materials '+name);ck(fingerprint(snapshot(e))==fingerprint(baseline),'options zero allDB writes '+name)
  url=f'/api/internal/releases/{rel["id"]}/csv-material-plans';m=request(e,'POST',url,b,201);key=m['plan']['request_key'];ck(key==material.plan_key(rel['id'],material.MaterialInput(**b)),'deterministic material key '+name);ck(m['binding']['limits']==rel['snapshot']['execution_source']['limits'],'source frozen cap preserved '+name)
  rp=request(e,'GET',url+'/'+a['id']+'/'+key);ck(rp['binding']==m['binding'],'new plan cold origin reconstruction '+name);confirm={'expected_plan_fingerprint':m['plan']['plan_fingerprint'],'consent':'CONFIRM_EXACT_OFFLINE_CSV_DAG','request_key':'actual-target-run'};accepted=request(e,'POST',f'/api/projects/{e[5]}/apps/{a["id"]}/csv-dag/{key}/runs',confirm,202);work(e,accepted['run_id']);proof=request(e,'GET','/api/csv-dag/runs/'+accepted['run_id']);out=next(iter(proof['result']['output_by_step'].values()));oracle=sum((Decimal(x['net']) for x in csv.DictReader(io.StringIO(TARGET))),Decimal(0));ck(proof['status']=='SUCCEEDED' and len(proof['steps'])==(3 if mode else 2) and proof['model_requests']==0,'actual target Operations zero models '+name);ck(out['resource_id']==rid!=oldrid and out['source_hash']==hashlib.sha256(TARGET.encode()).hexdigest() and Decimal(out['sum'])==oracle and out['count']==3,'new raw target Decimal oracle '+name)
  f=(a['id'],rid,m['plan'],accepted['run_id']);_,_,_,_,newrel=make_release(e,f);i=make_instance(e,newrel,'target-instance');e[2].close();e[0].engine.dispose();st=Store(e[1].database_url,test_only=True);cl=TestClient(create_app(st,e[1]));cl.headers['Authorization']='Bearer review-A';e[0]=st;e[2]=cl;accepted2,_=enqueue(e,i,newrel,'units','cold-unseen-target-column');work(e,accepted2['run_id']);d=request(e,'GET','/api/internal/instances/'+i['id']);v=d['data'][0]['data']['result'];ck(v['resource_id']==rid and Decimal(v['sum'])==sum(Decimal(x['units']) for x in csv.DictReader(io.StringIO(TARGET))) and v['count']==3 and type(v['count']) is int,'new Store instance fresh unseen units9 '+name);validate_value(newrel['snapshot']['data_schema'],d['data'][0]['data']);ck(True,'strict fivefield schema '+name)
  before=fingerprint(snapshot(e));cold=Store(e[1].database_url,test_only=True)
  try:dd=lifecycle.inspect_instance(cold,baseline['projects'][0]['owner_id'],i['id'],Limits(**{k:getattr(e[1],k) for k in Limits.model_fields}))
  finally:cold.engine.dispose()
  ck(fingerprint(snapshot(e))==before,'second cold read zeroDB writes '+name);after=snapshot(e)
  for tab in ['principals','grants','app_drafts','resources']:ck(after[tab]==baseline[tab],'no '+tab+' expansion '+name)
  for tab,ids in [('internal_releases',[rel['id']]),('internal_instances',[oldi['id']]),('internal_app_runs',[oldrun['app_run_id']])]:ck([x for x in after[tab] if x['id'] in ids]==[x for x in baseline[tab] if x['id'] in ids],'old '+tab+' preserved '+name)
  (ROOT/('business-'+name)/'response.json').write_text(json.dumps(dict(material=m,targetproof=proof,newrelease=newrel,newinstance=dd),indent=2,default=str));cases.append({'case':'business-'+name,'status':'PASS','checks':checks[begin:]})
 finally:e[2].close();e[0].engine.dispose()
 print({'case':cases[-1]['case'],'checks':len(cases[-1]['checks'])},flush=True)
# Self-designed attacks use same already-authorized report baseline; fixtures isolated each.
base=ROOT/'positive-report';meta0=json.loads((base/'fixture.json').read_text())
for attack in ['bad-column','samekey-column','samekey-target','target-grant','source-grant','target-bytes','source-bytes','foreign-owner','low-budget','missing-seal','joint-origin-strip','selfsign-binding']:
 folder=ROOT/('negative-'+attack);e=openclone(base,folder);e[5]=meta0['project'];b=copy.deepcopy(meta0['body']);rel=meta0['release'];url=f'/api/internal/releases/{rel["id"]}/csv-material-plans';begin=len(checks);responses=[]
 try:
  existing=None
  if attack in ['samekey-column','samekey-target','missing-seal','joint-origin-strip','selfsign-binding']:existing=request(e,'POST',url,b,201)
  if attack=='bad-column':b['column']='label'
  if attack=='samekey-column':b['column']='units'
  if attack=='samekey-target':b=body(rel,meta0['second_app'],meta0['second_resource'],meta0['second_graph'])
  if attack in ['target-grant','source-grant']:
   aid=meta0['target_app']['id'] if attack=='target-grant' else meta0['source_app']
   with e[0].tx() as c:
    runtime=c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id==aid)).scalar_one();c.execute(delete(grants).where(grants.c.principal_id==runtime,grants.c.tool_ref=='data.aggregate_csv'))
  if attack in ['target-bytes','source-bytes']:
   rid=meta0['target_resource'] if attack=='target-bytes' else rel['snapshot']['draft']['candidate']['manifest']['data_bindings'][0]['resource_ref']
   with e[0].tx() as c:c.execute(update(resources).where(resources.c.id==rid).values(content='changed,number\nnew,99\n'))
  if attack=='foreign-owner':e[2].headers['Authorization']='Bearer review-B'
  if attack=='low-budget':e[2].close();e[1].max_tools=2;e[2]=TestClient(create_app(e[0],e[1]));e[2].headers['Authorization']='Bearer review-A'
  if attack in ['missing-seal','joint-origin-strip','selfsign-binding']:
   key=existing['plan']['request_key'];aid=b['target_app_id']
   with e[0].tx() as c:
    if attack=='missing-seal':c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id==aid,delivery_graph_requests.c.kind==material.KIND+'_seal',delivery_graph_requests.c.request_key==key))
    elif attack=='joint-origin-strip':
     c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id==aid,delivery_graph_requests.c.kind.in_([material.KIND,material.KIND+'_seal']),delivery_graph_requests.c.request_key==key))
     for row in c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.app_id==aid,delivery_graph_requests.c.kind.in_(['csv_dag_plan','csv_dag_plan_seal']),delivery_graph_requests.c.request_key==key)).mappings():
      v=copy.deepcopy(row['snapshot']);v['response'].pop('material_reuse');v['response'].pop('plan_fingerprint');v['response']['plan_fingerprint']=fingerprint(v['response']);c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id==aid,delivery_graph_requests.c.kind==row['kind'],delivery_graph_requests.c.principal_id==row['principal_id'],delivery_graph_requests.c.request_key==key).values(snapshot=v,fingerprint=fingerprint(v)))
    else:
     for row in c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.app_id==aid,delivery_graph_requests.c.kind.in_([material.KIND,material.KIND+'_seal']),delivery_graph_requests.c.request_key==key)).mappings():
      v=copy.deepcopy(row['snapshot']);v['response']['target']['source_hash']='0'*64;c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id==aid,delivery_graph_requests.c.kind==row['kind'],delivery_graph_requests.c.principal_id==row['principal_id'],delivery_graph_requests.c.request_key==key).values(snapshot=v,fingerprint=fingerprint(v)))
  before=fingerprint(snapshot(e));paths=[('POST',url,b)]
  if attack in ['missing-seal','joint-origin-strip','selfsign-binding']:paths=[('GET',url+'/'+b['target_app_id']+'/'+key,None),('GET',f'/api/projects/{e[5]}/apps/{b["target_app_id"]}/csv-dag/'+key,None),('POST',f'/api/projects/{e[5]}/apps/{b["target_app_id"]}/csv-dag/{key}/runs',{'expected_plan_fingerprint':existing['plan']['plan_fingerprint'],'consent':'CONFIRM_EXACT_OFFLINE_CSV_DAG','request_key':'attack-run'})]
  for method,path,req in paths:
   response=e[2].request(method,path,json=req) if req else e[2].request(method,path);responses.append({'method':method,'path':path,'status':response.status_code,'body':response.json()});ck(response.status_code in [400,403,409,422],attack+' actual API rejects '+method)
  ck(fingerprint(snapshot(e))==before,attack+' entireDB zero writes');(folder/'responses.json').write_text(json.dumps(responses,indent=2));cases.append({'case':attack,'status':'PASS','checks':checks[begin:]});print({'case':attack,'statuses':[x['status'] for x in responses]},flush=True)
 finally:(folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
freeze('backend-after');assert json.loads((ROOT/'source-before.json').read_text())['files']==json.loads((ROOT/'source-backend-after.json').read_text())['files'];out={'source_sha':SHA,'cases':cases,'scenario_count':len(cases),'checks':len(checks),'seconds':time.monotonic()-started};(ROOT/'BACKEND_RESULTS.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='cases'}))
