import copy,hashlib,io,csv,itertools,json,os,re,tempfile,time,traceback
from fractions import Fraction
from pathlib import Path
from contextlib import contextmanager
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None)
from conftest import env as fixture
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import select,update,insert,delete,event,text
from sqlalchemy.exc import DatabaseError
from sim2act.db import Store,runs,run_contracts,operations,operation_intents,events,protocol_jobs,attempts,internal_instance_data,internal_instances,grants,resources,fingerprint,new_id
from sim2act import protocol_jobs as pjobs,protocol_pool as pool
from sim2act.worker import Worker
from sim2act.api import create_app
from test_csv_dag import NoModel
from test_csv_dag_instances import create,enqueue
from test_csv_logic_reuse import authorize
from test_project_column_material_reuse import source,register,binding,accept,work
from fastapi.testclient import TestClient
ROOT=Path('/tmp/run-private-read-independent-20261011');REPO=Path('/workspace/Sim2Act')
freeze=json.loads((REPO/'docs/evidence/run-private-read-scope-20261011/frozen-before.json').read_text());F=freeze['files']
assert F and all(hashlib.sha256((REPO/k).read_bytes()).hexdigest()==h for k,h in F.items()),'freeze mismatch'
(ROOT/'freeze-before.json').write_text(json.dumps(freeze,indent=2)+'\n')
R=dict(checks=[],failures=[],not_run=['PG','Windows','native/browser/socket-device','old source upgrade','real/paid models','full P-A/P-B/AT10','semantic/owner acceptance','remote CI'],source_sha256={k:h for k,h in F.items() if k.startswith('src/')})
@contextmanager
def env():
 d=Path(tempfile.mkdtemp(prefix='fixture-',dir=ROOT));g=fixture.__wrapped__(d);e=next(g)
 try:yield e
 finally:g.close()
def ok(name,**facts):R['checks'].append(dict(name=name,status='PASS',**facts));print('PASS',name,flush=True)
def ordinary(e,key):return e[0].submit(e[3],e[5],'independent scheduler material scope',[e[6]],key)
def row(e,rid):
 with e[0].tx() as c:return copy.deepcopy(dict(c.execute(select(runs).where(runs.c.id==rid)).mappings().one()))
def historical(e):
 rid=ordinary(e,'ind-history')
 with e[0].tx() as c:
  c.execute(update(runs).where(runs.c.id==rid).values(status='SUCCEEDED',context={'messages':[{'role':'user','content':'independent old private context witness'}]},result={'content':'independent old successful result witness'}))
  oid=new_id('op');c.execute(insert(operations).values(id=oid,run_id=rid,call_id='old-private-operation',tool_ref='resource.read',status='VERIFIED',receipt={'data':{'content':'independent old private operation witness'}}));c.execute(insert(operation_intents).values(operation_id=oid,request={'input':{'column':'old-secret-column'}}))
 return rid,oid,row(e,rid)
def barrier_dump(name,b,**facts):
 (ROOT/(name+'.json')).write_text(json.dumps(dict(**facts,blocked=b.blocked,evaluated=b.evaluated,sql=b.statements),indent=2)+'\n')
def scenario(name,fn):
 try:fn()
 except Exception:
  R['failures'].append(dict(name=name,error=traceback.format_exc()));print(traceback.format_exc(),flush=True)

def calibration():
 with env() as e:
  rid,oid,prior=historical(e)
  shapes=[('unscoped-context','SELECT context FROM runs',()),('IN-result','SELECT result FROM runs WHERE id IN (?,?)',(rid,'missing')),('join','SELECT r.context FROM runs r JOIN run_contracts c ON c.run_id=r.id WHERE c.run_id=?',(rid,)),('quoted-alias','SELECT "old"."result" FROM "runs" AS "old" WHERE "old"."id"=?',(rid,)),('subquery','SELECT result FROM runs WHERE id IN (SELECT run_id FROM run_contracts WHERE run_id=?)',(rid,)),('aggregate','SELECT max(context) FROM runs',()),('predicate-count','SELECT count(*) FROM runs WHERE result IS NOT NULL',()),('CTE','WITH saved AS (SELECT context FROM runs WHERE id=?) SELECT * FROM saved',(rid,)),('explicit-main','SELECT main.runs.context FROM main.runs WHERE id=?',(rid,)),('source-name-CTE','WITH private_read_runs AS (SELECT context FROM main.runs WHERE id=?) SELECT * FROM private_read_runs',(rid,)),('comment-source-CTE','/* independent reader */ WITH private_read_runs AS (SELECT context FROM main.runs WHERE id=?) SELECT * FROM private_read_runs',(rid,)),('receipt','SELECT receipt FROM operations WHERE run_id=?',(rid,)),('intent-request','SELECT request FROM operation_intents WHERE operation_id=?',(oid,)),('contract-snapshot','SELECT snapshot FROM run_contracts WHERE run_id=?',(rid,)),('old-resource','SELECT content,hash FROM resources WHERE id=?',(e[6],))]
  for name,sql,params in shapes:
   with PrivateReadBarrier(e[0],{rid},{e[6]}) as b:
    with e[0].engine.connect() as c:assert c.execute(select(runs.c.id,runs.c.status)).first()
    assert not b.evaluated and not b.blocked
    try:
     denied=False
     try:
      with e[0].engine.connect() as c:c.exec_driver_sql(sql,params).all()
     except DatabaseError:denied=True
     assert denied and b.blocked,'cell barrier allowed protected '+name
     ok('SQLite actual private-cell calibration '+name,blocked=b.blocked)
    finally:barrier_dump('calibration-'+name,b)
  assert row(e,rid)==prior
  target=ordinary(e,'ind-current-ordinary-target')
  with PrivateReadBarrier(e[0],{rid},{e[6]}) as b:
   try:
    got=e[0].claim('ind-private-scope-worker',30);assert got['id']==target and not b.blocked
    ok('actual claim loads current payload while unrelated successful history remains private')
   finally:barrier_dump('ordinary-claim',b,protected_run=rid,current_run=target)
  assert row(e,rid)==prior

def markers():
 with env() as e:
  rids=[];mask_by_id={}
  for mask in range(1,32):
   rid=ordinary(e,'ind-marker-'+str(mask));rids.append(rid);mask_by_id[rid]=mask
   with e[0].tx() as c:
    r=dict(c.execute(select(runs).where(runs.c.id==rid)).mappings().one());ctx=dict(r['context']);ctx.pop('kind',None)
    if mask&4:ctx['kind']=pjobs.NAMESPACE
    result={'protocol_result':{'kind':'model-protocol.v1'}} if mask&8 else None
    c.execute(update(runs).where(runs.c.id==rid).values(status='RUNNING',lease_until=0,context=ctx,result=result))
    if mask&1:c.execute(insert(protocol_jobs).values(run_id=rid,project_id=e[5],principal_id=e[3],runtime_id=r['runtime_id'],kind='source',accepted_snapshot={},fingerprint=fingerprint({}),created_at=time.time()))
    if mask&2:e[0].event(c,rid,'PROTOCOL_ACCEPTED',{'independent':'residual-marker'})
    sc=copy.deepcopy(c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==rid)).scalar_one());sc['goal']['constraints']=[pjobs.NAMESPACE] if mask&16 else []
    c.execute(update(run_contracts).where(run_contracts.c.run_id==rid).values(snapshot=sc,fingerprint=fingerprint(sc)))
  with e[0].tx() as c:
   assert pjobs.protocol_run_ids(c,candidates=rids)==set(rids)
   assert pjobs.protocol_run_ids(c,candidates=[])==set()
   try:pjobs.protocol_run_ids(c);raise AssertionError('unscoped oracle accepted')
   except ValueError:pass
  assert e[0].claim('ind-no-protocol-downgrade',30) is None
  with e[0].tx() as c:
   assert not c.execute(select(events.c.id).where(events.c.run_id.in_(rids),events.c.kind=='RECONCILED')).first()
  for rid in rids:
   r=row(e,rid);assert r['status']=='WAITING_RESOURCE' and r['fence']>0
   ok('residual protocol marker mask '+str(mask_by_id[rid])+' blocks generic recovery')
  ok('candidate oracle rejects unscoped call and explicit empty scope remains empty')
  # Specific damaged SQLite JSON uses any residual kind conservatively; no duplicate text reserialization.
  raws=[('context','{"kind":"plain","kind":"protocol_jobs.v1"}'),('result','{"protocol_result":{"kind":"plain"},"protocol_result":{"kind":"model-protocol.v1"}}')]
  for field,raw in raws:
   rid=ordinary(e,'ind-duplicate-'+field)
   with e[0].tx() as c:
    c.exec_driver_sql('UPDATE runs SET '+field+'=?, status=\'RUNNING\', lease_until=0 WHERE id=?',(raw,rid));assert pjobs.protocol_run_ids(c,rid)=={rid}
   assert e[0].claim('ind-stop-duplicate-'+field,30) is None and row(e,rid)['status']=='WAITING_RESOURCE'
   ok('damaged repeated '+field+' namespace cannot downgrade')
  # Candidate-local nonprotocol types and mismatched seals must not become protocol.
  cases=[('context',None),('context',[pjobs.NAMESPACE]),('context',pjobs.NAMESPACE),('context',{'kind':[pjobs.NAMESPACE]}),('result',{'protocol_result':[{'kind':'model-protocol.v1'}]}),('result',{'protocol_result':{'kind':['model-protocol.v1']}}),('constraints',pjobs.NAMESPACE),('constraints',{pjobs.NAMESPACE:pjobs.NAMESPACE}),('constraints',[[pjobs.NAMESPACE]]),('constraints',True),('bad-contract',[pjobs.NAMESPACE])]
  for i,(field,value) in enumerate(cases):
   rid=ordinary(e,'ind-invalid-kind-'+str(i))
   with e[0].tx() as c:
    if field in ('context','result'):c.execute(update(runs).where(runs.c.id==rid).values({field:value}))
    else:
     sc=copy.deepcopy(c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==rid)).scalar_one());sc['goal']['constraints']=value;c.execute(update(run_contracts).where(run_contracts.c.run_id==rid).values(snapshot=sc,fingerprint='0'*64 if field=='bad-contract' else fingerprint(sc)))
    assert not pjobs.protocol_run_ids(c,rid)
  ok('11 wrong JSON marker types or contract seals remain outside protocol classification')

def pool_scope():
 with env() as e:
  old,oid,prior=historical(e);current=ordinary(e,'ind-pool-candidate')
  with e[0].tx() as c:
   e[0].event(c,current,'PROTOCOL_ACCEPTED',{'independent':'pool metadata witness'})
   c.execute(insert(attempts).values(id=new_id('att'),run_id=current,mode='MOCK',status='DONE',parameters={'current':'mock protocol candidate'}))
   c.execute(insert(attempts).values(id=new_id('att'),run_id=None,mode='MOCK',status='DONE',parameters={'orphan':'never select as protocol'}))
  columns=[]
  def returned(conn,cursor,statement,parameters,ctx,many):columns.append({'sql':statement,'columns':[x[0] for x in cursor.description or ()]})
  event.listen(e[0].engine,'after_cursor_execute',returned)
  try:
   with PrivateReadBarrier(e[0],{old},{e[6]}) as b:
    try:
     with e[0].tx() as c:got=pool._protocol_attempts(c)
     assert len(got)==1 and got[0]['run_id']==current and not b.blocked
     assert all(not {'context','result','goal','resource_refs','error'}.intersection(q['columns']) for q in columns if re.search(r'FROM\s+"?private_read_runs',q['sql'],re.I))
     ok('pool classifies actual Attempt Run IDs only, projects no Run payload, ignores NULL orphan')
    finally:barrier_dump('pool-scope',b,protected_run=old,candidate_run=current,returned_columns=columns)
  finally:event.remove(e[0].engine,'after_cursor_execute',returned)
  assert row(e,old)==prior

CONTENT='item,units,net\nind-new-a,17,4.125\nind-new-b,2,-0.875\nind-new-c,-1,2.5\n'
def actual_worker():
 with env() as e:
  source_release,old_resource,group=source(e)
  entry=next(x for x in group['entries'] if x['release_id']==source_release['id']);old_instance=e[2].get('/api/internal/instances/'+entry['instance_id']).json();q,_=enqueue(e,old_instance,source_release,column='quantity',key='ind-old-typed');work(e,q)
  obj,_=authorize(e,source_release);aid,target=register(e,CONTENT)
  with e[0].tx() as c:c.execute(update(grants).where(grants.c.resource_id==old_resource).values(revoked=True))
  body=binding(e,aid,target,obj=obj,column='net',key='ind-target-after-revoke');path='/api/internal/csv-logics/'+obj['id']+'/material-plans'
  tables=(runs,run_contracts,operations,operation_intents,resources,internal_instance_data,internal_instances)
  with e[0].tx() as c:before={t.name:copy.deepcopy([dict(x) for x in c.execute(select(t)).mappings()]) for t in tables}
  protected_runs={x['id'] for x in before['runs']};protected_resources={x['id'] for x in before['resources']}-{target}
  cold_store=None
  with PrivateReadBarrier(e[0],protected_runs,protected_resources) as b:
   try:
    value,accepted,_,_=accept(e,path,body,'ind-guarded-target');job=work(e,accepted);proof=e[2].get('/api/csv-dag/runs/'+job['id']).json();v=proof['result']['output_by_step']['report'];rows=list(csv.DictReader(io.StringIO(CONTENT)));oracle=sum((Fraction(x['net']) for x in rows),Fraction());assert proof['status']=='SUCCEEDED' and len(proof['steps'])==3 and Fraction(v['sum'])==oracle==Fraction('5.75') and v['count']==3 and v['resource_id']==target
    ok('actual new-source Worker independently sums net5.75 under every old-cell read barrier')
    a=e[2].post('/api/csv-dag/runs/'+job['id']+'/release-approvals',json=dict(expected_plan_fingerprint=value['plan']['plan_fingerprint'],request_key='ind-guarded-release'));assert a.status_code==201,a.text
    r=e[2].post('/api/internal/approvals/'+a.json()['id']+'/commit',json=dict(fingerprint=a.json()['fingerprint']));assert r.status_code==200,r.text;rel=r.json();i=create(e,rel,key='ind-guarded-instance');assert rel['snapshot']['execution_source']['default_column']=='net'
    cold_store=Store(e[1].database_url,test_only=True);b.attach(cold_store);cold=TestClient(create_app(cold_store,e[1]));cold.headers['Authorization']='Bearer synthetic-test-A'
    try:
     for column in ['net','units']:
      r=cold.post('/api/internal/instances/'+i['id']+'/runs',json=dict(expected_revision=i['revision'],expected_release_fingerprint=rel['fingerprint'],input={'column':column},request_key='ind-guarded-cold-'+column));assert r.status_code==202,r.text;work(e,r.json())
     r=cold.get('/api/internal/instances/'+i['id']);assert r.status_code==200,r.text;detail=r.json();assert detail['data_version']==2 and {Fraction(x['data']['result']['sum']) for x in detail['data']}=={Fraction('5.75'),Fraction(18)}
     ok('cold target Release/Instance actual inputs net5.75 and units18 retain typed history under barrier')
     (ROOT/'actual-worker-proof.json').write_text(json.dumps(dict(target_proof=proof,target_release=rel,cold_instance=detail),indent=2)+'\n')
    finally:cold.close()
    assert not b.blocked
   finally:barrier_dump('actual-worker-barrier',b,protected_old_runs=sorted(protected_runs),protected_old_resources=sorted(protected_resources))
  if cold_store:cold_store.engine.dispose()
  with e[0].tx() as c:after={t.name:[dict(x) for x in c.execute(select(t)).mappings()] for t in tables}
  assert all(all(x in after[name] for x in values) for name,values in before.items())
  ok('all old Run contract receipt intent resource and internal typed/version rows preserved byte-for-byte')

for name,fn in [('cell-barrier calibration and claim',calibration),('31 combinations and damaged types',markers),('protocol Attempt candidate pool',pool_scope),('actual data-free CSV Worker and cold typed history',actual_worker)]:scenario(name,fn)
R.update(status='FAIL' if R['failures'] else 'PASS',pass_checks=len(R['checks']),fail=len(R['failures']),skip=0,source_sha256_after={k:hashlib.sha256((REPO/k).read_bytes()).hexdigest() for k in R['source_sha256']},frozen_all_unchanged=all(hashlib.sha256((REPO/k).read_bytes()).hexdigest()==h for k,h in F.items()))
assert R['source_sha256']==R['source_sha256_after'] and R['frozen_all_unchanged'],'source changed during independent probe'
(ROOT/'result.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=R['status'],pass_checks=R['pass_checks'],fail=R['fail'],skip=0)),flush=True)
raise SystemExit(bool(R['failures']))
