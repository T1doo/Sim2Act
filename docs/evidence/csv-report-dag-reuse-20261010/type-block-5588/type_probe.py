from common import *
import shutil,traceback
freeze('before');source=pathlib.Path('/tmp/sim2act-report-dag-reuse-independent-20261010/api-business-cold/db.sqlite');original_sha=hashlib.sha256(source.read_bytes()).hexdigest();results=[]
for case in ['joint-row-app-output-float','row-float-only-app-int']:
 folder=ROOT/case;folder.mkdir(exist_ok=True);shutil.copy2(source,folder/'db.sqlite');url='sqlite:///'+str(folder/'db.sqlite');store=Store(url,test_only=True);settings=Settings(url,folder,mode='mock');client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer review-A';e=[store,settings,client,None,None,None,None]
 try:
  with store.engine.connect() as c:
   record=c.execute(select(internal_instance_data).order_by(internal_instance_data.c.version)).mappings().first();ar=c.execute(select(internal_app_runs).where(internal_app_runs.c.id==record['run_id'])).mappings().one();bind=c.execute(select(internal_run_bindings).where(internal_run_bindings.c.app_run_id==ar['id'])).mappings().one();rel=c.execute(select(internal_releases).where(internal_releases.c.id==record['release_id'])).mappings().one()
  iid=record['instance_id'];rid=bind['run_id'];initial={}
  for name,path in [('instance','/api/internal/instances/'+iid),('instance_run','/api/internal/instances/'+iid+'/runs/'+rid),('dag_run','/api/csv-dag/runs/'+rid)]:
   response=client.get(path);assert response.status_code==200;initial[name]=response.json()
  assert type(record['data']['result']['count']) is int and record['data']['result']['count']==2
  typed=copy.deepcopy(record['data']);typed['result']['count']=2.0;newfp=fingerprint(typed)
  with store.tx() as c:
   c.execute(update(internal_instance_data).where(internal_instance_data.c.instance_id==iid,internal_instance_data.c.version==record['version']).values(data=typed,fingerprint=newfp))
   if case=='joint-row-app-output-float':
    output=copy.deepcopy(ar['output']);output['count']=2.0;c.execute(update(internal_app_runs).where(internal_app_runs.c.id==ar['id']).values(output=output))
   job=c.execute(select(runs).where(runs.c.id==rid)).mappings().one();result=copy.deepcopy(job['result']);result['instance_result']['record_fingerprint']=newfp;c.execute(update(runs).where(runs.c.id==rid).values(result=result))
  before=fingerprint(snapshot(e));responses={}
  for name,path in [('instance','/api/internal/instances/'+iid),('instance_run','/api/internal/instances/'+iid+'/runs/'+rid),('dag_run','/api/csv-dag/runs/'+rid)]:
   response=client.get(path);responses[name]={'path':path,'status':response.status_code,'body':response.json()}
  after=fingerprint(snapshot(e));schema=rel['snapshot']['data_schema'];schema_rejected=False
  from sim2act.contracts import validate_value
  try:validate_value(schema,typed)
  except DomainError:schema_rejected=True
  out={'case':case,'source_sha':SHA,'initial_3GET200':True,'typed_original_count_type':type(record['data']['result']['count']).__name__,'typed_attacked_count_type':type(typed['result']['count']).__name__,'app_output_count_original_type':type(ar['output']['count']).__name__,'app_output_attacked_type':'float' if case=='joint-row-app-output-float' else 'int','frozen_typed_schema':schema,'frozen_schema_rejects_attacked_typed_value':schema_rejected,'Operation_receipts_untouched':True,'Run_changed_only_instance_record_fingerprint':True,'allDB_zero_GET_writes':before==after,'responses':responses,'verdict':'BLOCK' if any(x['status']==200 for x in responses.values()) and schema_rejected else 'REJECTED'}
  assert schema_rejected and before==after
  (folder/'actual-responses.json').write_text(json.dumps(out,indent=2));(folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));results.append(out);print(json.dumps({'case':case,'statuses':{k:v['status'] for k,v in responses.items()},'verdict':out['verdict'],'schema_rejects':schema_rejected,'zero_GET_writes':before==after}),flush=True)
 finally:client.close();store.engine.dispose()
assert hashlib.sha256(source.read_bytes()).hexdigest()==original_sha;freeze('after');(ROOT/'TYPE_PROBE_RESULTS.json').write_text(json.dumps(results,indent=2))
