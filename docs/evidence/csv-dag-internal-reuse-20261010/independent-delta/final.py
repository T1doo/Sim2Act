from common import *
import time,traceback
freeze('d716-before');old=json.loads((ROOT/'source-before.json').read_text())['files'];new=json.loads((ROOT/'source-d716-before.json').read_text())['files'];changes=[p for p in new if new[p]!=old[p]];assert changes==['tests/test_csv_dag_instances.py'];assert all(new[p]==old[p] for p in new if p.startswith('src/'));(ROOT/'039-d716-byte-bridge.json').write_text(json.dumps({'old_sha':'039b74cf03ea5926b0b02b1b81dc684fa639a46d','new_sha':SHA,'count':357,'unchanged_files':356,'product_count':69,'unchanged_product_files':69,'changed_files':changes},indent=2));out=[]
for case in ['normal-cold','039-joint-cold']:
 folder=ROOT/('d716-'+case);folder.mkdir(exist_ok=True);checks=[];start=time.monotonic()
 if case=='normal-cold':e=env(folder)
 else:
  origin=ROOT/'joint-new';url='sqlite:///'+str(origin/'db.sqlite');store=Store(url,test_only=True);s=Settings(url,origin,mode='mock');cl=TestClient(create_app(store,s));cl.headers['Authorization']='Bearer review-A'
  with store.engine.connect() as c:i=dict(c.execute(select(internal_instances)).mappings().one());owner=i['principal_id'];pid=i['project_id'];source=next(x['run_id'] for x in c.execute(select(events)).mappings() if x['kind']=='CSV_DAG_ACCEPTED' and 'internal_instance' not in x['data'])
  e=[store,s,cl,owner,None,pid,None]
 try:
  if case=='normal-cold':
   aid,_,_,source,rel=make_release(e);i=make_instance(e,rel)
   # Use a second real column Run; keep one unrelated instance as a scope control.
   sibling=make_instance(e,rel,'independent-sibling');a,_=enqueue(e,i,rel,'other','independent-cold-result');work(e,a['run_id']);e[2].close();e[0].engine.dispose();cold=Store(e[1].database_url,test_only=True);cl=TestClient(create_app(cold,e[1]));cl.headers['Authorization']='Bearer review-A';e[0]=cold;e[2]=cl
  before=fingerprint(snapshot(e));r=e[2].get('/api/internal/instances/'+i['id']);proto=e[2].get('/api/runs/'+source);assert proto.status_code==200 and proto.json()['status']=='SUCCEEDED',proto.text;checks.append('same-source prototype Run remains normal without instance marker')
  if case=='normal-cold':
   assert r.status_code==200,r.text;detail=r.json();assert detail['data_version']==1 and Decimal(detail['data'][0]['data']['result']['sum'])==Decimal('1.5') and len(detail['runs'])==1;checks.append('fresh cold Store reconstructs actual typed result and Run')
   ar=e[2].get('/api/runs/'+a['run_id']);assert ar.status_code==200 and ar.json()['business_writes']==1;checks.append('independent bound actual Run cold read remains normal')
   rr=e[2].get('/api/internal/instances/'+sibling['id']);assert rr.status_code==200 and rr.json()['data_version']==0 and rr.json()['runs']==[];checks.append('same-source sibling does not inherit another instance acceptance')
  else:
   assert r.status_code==409 and r.json()['error']['message']=='Accepted instance Run history is incomplete',r.text;checks.append('039 exact joint attack cold d716 read refused by new event gate')
  assert fingerprint(snapshot(e))==before;checks.append('all cold status and instance GETs zero durable writes');(folder/'responses.json').write_text(json.dumps({'instance_http':r.status_code,'instance_body':r.json(),'prototype_http':proto.status_code,'prototype_body':proto.json()},indent=2));out.append({'case':case,'status':'PASS','checks':checks,'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);out.append({'case':case,'status':'FAIL','checks':checks,'error':err});print(err,flush=True)
 finally:(folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
 print(out[-1],flush=True)
(ROOT/'final-results.json').write_text(json.dumps(out,indent=2));freeze('d716-after');assert all(x['status']=='PASS' for x in out)
