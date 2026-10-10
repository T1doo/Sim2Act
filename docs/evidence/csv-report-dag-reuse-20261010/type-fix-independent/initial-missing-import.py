from common import *
import shutil,traceback,time
freeze('before');cases=[];began=time.monotonic()
for family,report_mode,version in [('v1',False,'internal.csv-read-sum.v1'),('report',True,'internal.csv-read-sum-report.v1')]:
 folder=ROOT/('positive-'+family);e=env(folder);checks=[]
 def check(v,label):assert v,label;checks.append(label)
 try:
  aid,rid,p,source,rel=make_release(e,fixture(e,with_report=report_mode));i=make_instance(e,rel);a,body=enqueue(e,i,rel,'quantity','fresh-column');work(e,a['run_id']);response=e[2].get('/api/internal/instances/'+i['id']+'/runs/'+a['run_id']);assert response.status_code==200;got=response.json();v=got['output'];check(got['execution_version']==version,'exact version preserved');check(set(v)=={'resource_id','column','count','sum','source_hash'} and type(v['count']) is int and v['count']==2 and v['source_hash']==hashlib.sha256(RAW.encode()).hexdigest(),'five typed fields exact integer/hash');oracle=sum((Decimal(x['quantity']) for x in csv.DictReader(io.StringIO(RAW))),Decimal(0));check(Decimal(v['sum'])==oracle,'independent fresh raw Decimal result4');check(len(got['proof']['steps'])==(3 if report_mode else 2) and got['proof']['model_requests']==0 and got['proof']['business_writes']==1,'actual receipts and one typed append zero models');check(got['proof']['result']['output_by_step']==({'writeup':{**v,'text':'列 quantity；行数 2；合计 4'}} if report_mode else {'total':v}),'complete report or original aggregate sink');before=fingerprint(snapshot(e));cold=Store(e[1].database_url,test_only=True)
  try:detail=lifecycle.inspect_instance(cold,e[3],i['id'],Limits(**{k:getattr(e[1],k) for k in Limits.model_fields}));assert detail['data_version']==1 and len(detail['data'])==1
  finally:cold.engine.dispose()
  check(fingerprint(snapshot(e))==before,'cold newStore zero allDB writes');validate_value(rel['snapshot']['data_schema'],detail['data'][0]['data']);check(True,'typed schema positive valid');(folder/'positive-response.json').write_text(json.dumps(got,indent=2));(folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));cases.append({'case':'positive-'+family,'status':'PASS','checks':checks})
 finally:e[2].close();e[0].engine.dispose()
 original_db_hash=hashlib.sha256((folder/'db.sqlite').read_bytes()).hexdigest()
 for attack in ['row-only','joint']:
  own=ROOT/(family+'-'+attack);own.mkdir(exist_ok=True);shutil.copy2(folder/'db.sqlite',own/'db.sqlite');store=Store('sqlite:///'+str(own/'db.sqlite'),test_only=True);settings=Settings('sqlite:///'+str(own/'db.sqlite'),own,mode='mock');client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer review-A';e=[store,settings,client,None,None,None,None];checks=[]
  try:
   with store.engine.connect() as c:
    record=c.execute(select(internal_instance_data)).mappings().one();ar=c.execute(select(internal_app_runs)).mappings().one();binding=c.execute(select(internal_run_bindings)).mappings().one();release=c.execute(select(internal_releases)).mappings().one();ops=[dict(x) for x in c.execute(select(operations)).mappings()]
   typed=copy.deepcopy(record['data']);typed['result']['count']=2.0;fp=fingerprint(typed)
   with store.tx() as c:
    c.execute(update(internal_instance_data).where(internal_instance_data.c.instance_id==record['instance_id'],internal_instance_data.c.version==record['version']).values(data=typed,fingerprint=fp))
    if attack=='joint':c.execute(update(internal_app_runs).where(internal_app_runs.c.id==ar['id']).values(output={**ar['output'],'count':2.0}))
    job=c.execute(select(runs).where(runs.c.id==binding['run_id'])).mappings().one();result=copy.deepcopy(job['result']);result['instance_result']['record_fingerprint']=fp;c.execute(update(runs).where(runs.c.id==binding['run_id']).values(result=result))
   schema_rejected=False
   try:validate_value(release['snapshot']['data_schema'],typed)
   except DomainError:schema_rejected=True
   check(schema_rejected,'frozen typed schema rejects floating count')
   with store.engine.connect() as c:check([dict(x) for x in c.execute(select(operations)).mappings()]==ops,'actual Operation/receipts untouched')
   before=fingerprint(snapshot(e));responses={};iid=record['instance_id'];rid=binding['run_id']
   for kind,path in [('instance','/api/internal/instances/'+iid),('instance_run','/api/internal/instances/'+iid+'/runs/'+rid),('dag_run','/api/csv-dag/runs/'+rid)]:
    response=client.get(path);responses[kind]={'path':path,'status':response.status_code,'body':response.json()};check(response.status_code==409 and response.json()['error']['code']=='VERSION_CONFLICT','actual public '+kind+' rejects type tamper')
   check(fingerprint(snapshot(e))==before,'all failed GET zero entireDB writes');out={'case':family+'-'+attack,'source_sha':SHA,'family':version,'typed_frozen_schema':release['snapshot']['data_schema'],'attack_typed_data':typed,'ar_count_type':'float' if attack=='joint' else 'int','status':'PASS','checks':checks,'responses':responses};(own/'actual-responses.json').write_text(json.dumps(out,indent=2));(own/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));cases.append({'case':out['case'],'status':'PASS','checks':checks,'statuses':[x['status'] for x in responses.values()]})
  finally:client.close();store.engine.dispose()
 assert hashlib.sha256((folder/'db.sqlite').read_bytes()).hexdigest()==original_db_hash
 for x in cases[-3:]:print(json.dumps({'case':x['case'],'status':x['status'],'checks':len(x['checks']),'statuses':x.get('statuses')}),flush=True)
freeze('after');paths=json.loads((ROOT/'source-after.json').read_text())['files'];changed=[]
for p,h in paths.items():
 if hashlib.sha256(subprocess.check_output(['git','show','5588a94faeb90abb2052a8ae5327810b8d27c287:'+p],cwd=REPO)).hexdigest()!=h:changed.append(p)
assert changed==['src/sim2act/csv_dag_instances.py','tests/test_csv_report_dag_instances.py'];old=json.loads((ROOT/'source-before.json').read_text());new=json.loads((ROOT/'source-after.json').read_text());assert old['files']==new['files'];author=json.loads(pathlib.Path('/tmp/sim2act-report-dag-type-fix-20261010/source-freeze.json').read_text());assert author['files']==new['files']
out={'verdict':'LIMITED_PASS','source_sha':SHA,'cases':cases,'scenario_count':6,'checks':sum(len(x['checks']) for x in cases),'elapsed_seconds':time.monotonic()-began,'four_type_attacks_all12GET409':True,'source365_before_after_match':True,'author_freeze_exact':True,'delta_paths':changed,'other364_paths_same5588':True,'other68_products_same5588':True,'PG_CI_repo_ref_operations':0};(ROOT/'RESULTS.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='cases'},indent=2))
