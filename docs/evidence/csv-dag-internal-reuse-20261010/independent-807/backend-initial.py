from common import *
import time,traceback
from sim2act.errors import DomainError
freeze('before');results=[]
def check(v,label,checks):assert v,label;checks.append(label)
for case in ['business-cold','coherent-output','cross-owner','cross-project','origin-only','seal-only','both-origins-missing','accepted-pair-delete','joins-and-data-delete','unknown-input','samekey-change','deadline-final','old-fence']:
 folder=ROOT/('api-'+case);e=env(folder);checks=[];start=time.monotonic()
 try:
  aid,rid,p,source,rel=make_release(e);i=make_instance(e,rel);lim=Limits(**{k:getattr(e[1],k) for k in Limits.model_fields});base='/api/internal/instances/'+i['id']
  if case=='business-cold':
   for col in ['quantity','other']:
    accepted,body=enqueue(e,i,rel,col,col);work(e,accepted['run_id']);got=request(e,'GET',base+'/runs/'+accepted['run_id']);expected=sum((Decimal(r[col]) for r in csv.DictReader(io.StringIO(RAW))),Decimal(0));check(Decimal(got['output']['sum'])==expected,'actual raw Decimal oracle '+col,checks);check(got['run_id']!=source and got['proof']['business_writes']==1 and got['proof']['model_requests']==0,'new real two operations and typed write '+col,checks);check(got['proof']['steps'][1]['predecessor_receipts']==[fingerprint(got['proof']['steps'][0])],'predecessor receipt binding '+col,checks);again=request(e,'POST',base+'/runs',body,202);check(again['run_id']==accepted['run_id'] and again['cached'],'samekey exact accepted '+col,checks)
   before=fingerprint(snapshot(e));cold=Store(e[1].database_url,test_only=True)
   try:d=lifecycle.inspect_instance(cold,e[3],i['id'],lim);check(d['data_version']==2 and [r['version'] for r in d['data']]==[1,2],'cold continuous versions 1,2',checks)
   finally:cold.engine.dispose()
   check(fingerprint(snapshot(e))==before,'cold inspection zero durable mutation',checks)
  elif case in ['origin-only','seal-only','both-origins-missing']:
   kinds=['csv_dag_release_origin_seal'] if case=='origin-only' else ['csv_dag_release_origin'] if case=='seal-only' else ['csv_dag_release_origin','csv_dag_release_origin_seal']
   with e[0].tx() as c:c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(kinds),delivery_graph_requests.c.request_key==rel['approval_id']))
   before=fingerprint(snapshot(e));r=e[2].get('/api/internal/releases/'+rel['id']);check(r.status_code==409,'incomplete independent family anchor refused',checks);r=e[2].post(base+'/runs',json={'expected_revision':1,'expected_release_fingerprint':rel['fingerprint'],'input':{'column':'quantity'},'request_key':'after-origin-loss'});check(r.status_code==409,'no plain family fallback',checks);check(fingerprint(snapshot(e))==before,'failed family writes zero',checks)
  elif case in ['unknown-input','samekey-change']:
   a,body=enqueue(e,i,rel);body['input']={'column':'not_numeric'} if case=='unknown-input' else {'column':'other'};before=fingerprint(snapshot(e));r=e[2].post(base+'/runs',json=body);check(r.status_code in [400,409,422],'strict changed input refused',checks);check(fingerprint(snapshot(e))==before,'bad input no writes',checks)
  else:
   a,body=enqueue(e,i,rel);rid2=a['run_id']
   if case in ['cross-owner','cross-project']:
    if case=='cross-owner':e[2].headers['Authorization']='Bearer review-B'
    else:
     other=request(e,'POST','/api/projects',{'name':'Other same owner project'},201)['id']
     with e[0].tx() as c:c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(project_id=other))
    before=fingerprint(snapshot(e))
    for suffix in ['', '/control-status']:
     r=e[2].get(base+'/runs/'+rid2+suffix);check(r.status_code in [403,409],'scope denied '+suffix,checks)
    check(fingerprint(snapshot(e))==before,'cross scope metadata no writes',checks)
   elif case in ['coherent-output','accepted-pair-delete','joins-and-data-delete']:
    work(e,rid2)
    with e[0].tx() as c:
     if case=='coherent-output':
      ar=c.execute(select(internal_app_runs).where(internal_app_runs.c.id==a['app_run_id'])).mappings().one();out={**ar['output'],'sum':'999'};data={'result':out};c.execute(update(internal_app_runs).where(internal_app_runs.c.id==ar['id']).values(output=out));c.execute(update(internal_instance_data).where(internal_instance_data.c.run_id==ar['id']).values(data=data,fingerprint=fingerprint(data)))
     if case=='accepted-pair-delete':
      rows=c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(['csv_dag_run','csv_dag_run_seal']))).mappings().all();keys=[x['request_key'] for x in rows if x['response'].get('run_id')==rid2];check(len(keys)==2,'target accepted independent pair located',checks);c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.request_key.in_(keys),delivery_graph_requests.c.kind.in_(['csv_dag_run','csv_dag_run_seal'])))
     if case=='joins-and-data-delete':
      c.execute(delete(internal_instance_data).where(internal_instance_data.c.instance_id==i['id']));c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.run_id==rid2));c.execute(delete(internal_app_runs).where(internal_app_runs.c.id==a['app_run_id']));c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(data_version=0))
    before=fingerprint(snapshot(e));r=e[2].get(base);check(r.status_code==409,'actual proof rejects coherent tamper / omitted history',checks);check(fingerprint(snapshot(e))==before,'tamper read failure zero writes',checks);lst=request(e,'GET',f'/api/internal/apps/{aid}/dag-instances');check(all('data' not in x for x in lst['items']),'list contains no unverified cells',checks)
   elif case=='old-fence':
    w=Worker(e[0],e[1],ForbiddenModel());old=e[0].claim(w.id,e[1].lease_seconds);dag.advance(w,old)
    with e[0].tx() as c:c.execute(update(runs).where(runs.c.id==rid2).values(lease_until=0))
    newer=Worker(e[0],e[1],ForbiddenModel());job=e[0].claim(newer.id,e[1].lease_seconds);check(job['fence']>old['fence'],'cold reclaim higher fence',checks);before=fingerprint(snapshot(e))
    try:dag.advance(w,old);raise AssertionError('old fence accepted')
    except DomainError:pass
    check(fingerprint(snapshot(e))==before,'stale fenced advance zero writes',checks);newer.process(job);d=request(e,'GET',base);check(d['data_version']==1 and len(d['data'])==1,'new fence appends exactly once',checks)
   else:
    w=Worker(e[0],e[1],ForbiddenModel());job=e[0].claim(w.id,e[1].lease_seconds);dag.advance(w,job);dag.advance(w,job)
    original=instances.commit_result
    def expire_after_append(store,c,live,bound,value,limits):
     out=original(store,c,live,bound,value,limits);c.execute(update(runs).where(runs.c.id==rid2).values(created_at=0));return out
    instances.commit_result=expire_after_append;before=fingerprint(snapshot(e))
    try:
     try:dag.advance(w,job);raise AssertionError('deadline accepted')
     except DomainError as ex:check(ex.code=='BUDGET_EXHAUSTED','fresh final deadline guard rejects after typed append',checks)
    finally:instances.commit_result=original
    check(fingerprint(snapshot(e))==before,'entire typed append and pointer rollback',checks);dag.advance(w,job);d=request(e,'GET',base);check(d['data_version']==1,'valid retry finalizes only one typed row',checks)
  results.append({'case':case,'status':'PASS','checks':checks,'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);results.append({'case':case,'status':'FAIL','checks':checks,'error':err});print(err,flush=True)
 finally:
  (folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
 print(case,results[-1]['status'],len(checks),flush=True)
(ROOT/'backend-results.json').write_text(json.dumps(results,indent=2));freeze('backend-after');assert all(r['status']=='PASS' for r in results)
