from common import *
import traceback,time
from sqlalchemy import insert
OLD=pathlib.Path('/tmp/sim2act-dag-reuse-independent-20261010');freeze('before');old=json.loads((OLD/'source-final-after.json').read_text())['files'];new=json.loads((ROOT/'source-before.json').read_text())['files'];changed=[p for p in old if old[p]!=new[p]];assert set(changed)=={'src/sim2act/csv_dag_instances.py','tests/test_csv_dag_instances.py'};bridge={'old_sha':'807090cf0b9e6f6306f86ed79a64be065a68279c','new_sha':SHA,'total_files':len(new),'unchanged_files':len(new)-len(changed),'changed_files':changed,'product_files':sum(p.startswith('src/') for p in new),'unchanged_product_files':sum(p.startswith('src/') and old[p]==new[p] for p in new)};(ROOT/'byte-bridge.json').write_text(json.dumps(bridge,indent=2));results=[]
def check(v,label,checks):assert v,label;checks.append(label)
for case in ['cold-original-positive','cold-original-block','joint-new','duplicate-event']:
 start=time.monotonic();folder=ROOT/case;folder.mkdir(exist_ok=True);checks=[]
 if case.startswith('cold-original'):
  origin=OLD/('api-business-cold' if case.endswith('positive') else 'api-joint-marker-join-omission');url='sqlite:///'+str(origin/'db.sqlite');st=Store(url,test_only=True);s=Settings(url,folder,mode='mock');cl=TestClient(create_app(st,s));cl.headers['Authorization']='Bearer review-A'
  with st.engine.connect() as c:
   owner=c.execute(select(internal_instances.c.principal_id)).scalar_one();pid=c.execute(select(internal_instances.c.project_id)).scalar_one();iid=c.execute(select(internal_instances.c.id)).scalar_one();source=next(x['run_id'] for x in c.execute(select(events)).mappings() if x['kind']=='CSV_DAG_ACCEPTED' and 'internal_instance' not in x['data']);target=[x['run_id'] for x in c.execute(select(events)).mappings() if x['kind']=='CSV_DAG_ACCEPTED' and 'internal_instance' in x['data']]
  e=[st,s,cl,owner,None,pid,None]
 else:e=env(folder)
 try:
  if case.startswith('cold-original'):
   before=fingerprint(snapshot(e));r=e[2].get('/api/internal/instances/'+iid);(folder/'instance-response.json').write_text(json.dumps({'http':r.status_code,'body':r.json()},indent=2));r0=e[2].get('/api/runs/'+source);check(r0.status_code==200 and r0.json()['status']=='SUCCEEDED','prototype same-source unbound Run remains readable',checks)
   if case.endswith('positive'):
    check(r.status_code==200 and r.json()['data_version']==2 and len(r.json()['runs'])==2,'807 normal persisted instance cold reads on039',checks);check([Decimal(x['data']['result']['sum']) for x in r.json()['data']]==[Decimal(4),Decimal('1.5')],'independent original two results preserved',checks)
    for rid in target:rr=e[2].get('/api/runs/'+rid);check(rr.status_code==200 and rr.json()['business_writes']==1,'actual accepted instance Run remains readable '+rid,checks)
   else:check(r.status_code==409,'exact807 preserved blocking database now refused',checks)
   check(fingerprint(snapshot(e))==before,'cold GET only zero durable writes',checks)
  else:
   aid,_,_,_,rel=make_release(e);i=make_instance(e,rel);a,_=enqueue(e,i,rel);work(e,a['run_id'])
   with e[0].tx() as c:
    if case=='joint-new':
     rows=c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(['csv_dag_run','csv_dag_run_seal']))).mappings().all()
     for row in rows:
      if row['snapshot']['response'].get('run_id')==a['run_id']:
       value=copy.deepcopy(row['snapshot']);value['response'].pop('internal_instance');c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id==row['app_id'],delivery_graph_requests.c.principal_id==row['principal_id'],delivery_graph_requests.c.kind==row['kind'],delivery_graph_requests.c.request_key==row['request_key']).values(snapshot=value,fingerprint=fingerprint(value)))
     c.execute(delete(internal_instance_data).where(internal_instance_data.c.run_id==a['app_run_id']));c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.run_id==a['run_id']));c.execute(delete(internal_app_runs).where(internal_app_runs.c.id==a['app_run_id']));c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(data_version=0))
    else:
     row=dict(c.execute(select(events).where(events.c.run_id==a['run_id'],events.c.kind=='CSV_DAG_ACCEPTED')).mappings().one());row['id']=new_id('independent_duplicate');c.execute(insert(events).values(**row))
   before=fingerprint(snapshot(e));r=e[2].get('/api/internal/instances/'+i['id']);(folder/'instance-response.json').write_text(json.dumps({'http':r.status_code,'body':r.json()},indent=2));check(r.status_code==409,'new-source '+case+' rejects corrupted history',checks);check(fingerprint(snapshot(e))==before,'corruption rejection zero write',checks)
  results.append({'case':case,'status':'PASS','checks':checks,'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);results.append({'case':case,'status':'FAIL','checks':checks,'error':err});print(err,flush=True)
 finally:(folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
 print(case,results[-1]['status'],len(checks),flush=True)
(ROOT/'results.json').write_text(json.dumps(results,indent=2));freeze('after');assert all(r['status']=='PASS' for r in results)
