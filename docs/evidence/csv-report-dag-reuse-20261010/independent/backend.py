from common import *
import traceback,time
from sim2act.errors import DomainError
checks=[];results=[]
def check(v,label):assert v,label;checks.append(label)
def denied_no_write(e,path,body=None):
 before=fingerprint(snapshot(e));r=e[2].post(path,json=body) if body is not None else e[2].get(path);check(r.status_code in (403,409),f'rejected {r.status_code} {path}');check(fingerprint(snapshot(e))==before,'rejection zero entireDB writes');return r
for case in ['business-cold','legacy-v1','joint-promotion','joint-downgrade','report-self-sign','joint-omission','cross-owner','same-key-changed','source-third-missing','budget-two','final-deadline-rollback','old-fence']:
 folder=ROOT/('api-'+case);e=env(folder);checks=[];start=time.monotonic()
 try:
  if case in ['joint-promotion','joint-downgrade']:
   aid,rid,p,source=fixture(e,with_report=case=='joint-downgrade');a=request(e,'POST',f'/api/csv-dag/runs/{source}/release-approvals',{'expected_plan_fingerprint':p['plan_fingerprint'],'request_key':'joint-version'},201)
   with e[0].tx() as c:
    row=c.execute(select(internal_approvals).where(internal_approvals.c.id==a['id'])).mappings().one();payload=copy.deepcopy(row['payload']);ex=payload['snapshot']['execution_source'];check(ex['version']==('internal.csv-read-sum.v1' if case=='joint-promotion' else 'internal.csv-read-sum-report.v1'),'real structure picked initial exactversion')
    ex['version']='internal.csv-read-sum-report.v1' if case=='joint-promotion' else 'internal.csv-read-sum.v1'
    if case=='joint-promotion':ex['report_step']='writeup';ex['receipt_fingerprints'].append(ex['receipt_fingerprints'][-1])
    else:ex.pop('report_step');ex['receipt_fingerprints']=ex['receipt_fingerprints'][:2]
    fp=fingerprint(payload);c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(payload=payload,fingerprint=fp))
    rows=c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.request_key==a['id'],delivery_graph_requests.c.kind.in_(['csv_dag_release_origin','csv_dag_release_origin_seal']))).mappings().all();check(len(rows)==2,'both independent origin rows attacked')
    for row in rows:
     stored=copy.deepcopy(row['snapshot']);stored['request']['version']=ex['version'];stored['request']['snapshot_fingerprint']=fingerprint(payload['snapshot']);stored['response']=copy.deepcopy(stored['request']);c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.principal_id==row['principal_id'],delivery_graph_requests.c.app_id==row['app_id'],delivery_graph_requests.c.kind==row['kind'],delivery_graph_requests.c.request_key==row['request_key']).values(snapshot=stored,fingerprint=fingerprint(stored),request_fingerprint=fingerprint(stored['request'])))
   denied_no_write(e,'/api/internal/approvals/'+a['id']+'/commit',{'fingerprint':fp})
  else:
   f=fixture(e,with_report=case!='legacy-v1');aid,rid,p,source,rel=make_release(e,f);i=make_instance(e,rel);base='/api/internal/instances/'+i['id'];lim=Limits(**{k:getattr(e[1],k) for k in Limits.model_fields})
   if case=='business-cold':
    check(rel['snapshot']['execution_source']['version']=='internal.csv-read-sum-report.v1' and p['composition']['sinks']==['writeup'],'new version exact unique report sink')
    for n,col in enumerate(['quantity','other'],1):
     a,body=enqueue(e,i,rel,col,col);work(e,a['run_id']);got=request(e,'GET',base+'/runs/'+a['run_id']);oracle=sum((Decimal(row[col]) for row in csv.DictReader(io.StringIO(RAW))),Decimal(0));v=got['output'];check(Decimal(v['sum'])==oracle and v['count']==2,'independent raw Decimal oracle '+col);check(set(v)=={'resource_id','column','count','sum','source_hash'} and v['source_hash']==hashlib.sha256(RAW.encode()).hexdigest(),'typed fivefields exactbytes '+col);proof=got['proof'];check(len(proof['steps'])==3 and proof['steps'][2]['actual_reads']==[] and proof['model_requests']==0 and proof['business_writes']==1,'three actual operations / pure report / one append '+col);check(proof['steps'][2]['predecessor_receipts']==[fingerprint(proof['steps'][1])],'complete aggregate predecessor '+col);check(proof['result']['output_by_step']=={'writeup':{**v,'text':f"列 {col}；行数 2；合计 {v['sum']}"}},'full deterministic report remains sink '+col);check(got['result_version']==n and a['run_id']!=source,'newrun and continuous typed version '+col);repeat=request(e,'POST',base+'/runs',body,202);check(repeat['run_id']==a['run_id'] and repeat['cached'],'samekey returns original '+col)
    before=fingerprint(snapshot(e));cold=Store(e[1].database_url,test_only=True)
    try:d=lifecycle.inspect_instance(cold,e[3],i['id'],lim);check(d['data_version']==2 and [row['version'] for row in d['data']]==[1,2],'new Store cold durable ledger')
    finally:cold.engine.dispose()
    check(fingerprint(snapshot(e))==before,'cold allDB zero writes')
   elif case=='legacy-v1':
    ex=rel['snapshot']['execution_source'];check(ex['version']=='internal.csv-read-sum.v1' and 'report_step' not in ex and len(ex['receipt_fingerprints'])==2,'oldv1 unchanged fields/count');a,_=enqueue(e,i,rel);work(e,a['run_id']);got=request(e,'GET',base+'/runs/'+a['run_id']);check(len(got['proof']['steps'])==2 and got['output']['sum']=='4','oldv1 actual2steps result')
   elif case=='source-third-missing':
    with e[0].tx() as c:c.execute(delete(operations).where(operations.c.run_id==source,operations.c.call_id=='writeup'))
    denied_no_write(e,base+'/runs',{'expected_revision':i['revision'],'expected_release_fingerprint':rel['fingerprint'],'input':{'column':'quantity'},'request_key':'missing-source-third'})
   elif case=='budget-two':
    small=lim.model_copy(update={'max_tools':2});before=fingerprint(snapshot(e))
    try:
     with e[0].tx() as c:instances.enqueue_tx(e[0],c,e[3],i,rel,i['revision'],rel['fingerprint'],{'column':'quantity'},'budget2',small)
     raise AssertionError('budget2 accepted 3tool plan')
    except DomainError:pass
    check(fingerprint(snapshot(e))==before,'budget2 zero writes, report consumes third budget')
   else:
    a,body=enqueue(e,i,rel);rid2=a['run_id']
    if case=='same-key-changed':body['input']['column']='other';denied_no_write(e,base+'/runs',body)
    elif case=='cross-owner':e[2].headers['Authorization']='Bearer review-B';denied_no_write(e,base+'/runs/'+rid2)
    elif case in ['report-self-sign','joint-omission']:
     work(e,rid2)
     with e[0].tx() as c:
      if case=='report-self-sign':
       row=c.execute(select(operations).where(operations.c.run_id==rid2,operations.c.call_id=='writeup')).mappings().one();receipt=copy.deepcopy(row['receipt']);receipt['data']['text']='forged deterministic report';receipt['output_fingerprint']=fingerprint(receipt['data']);c.execute(update(operations).where(operations.c.id==row['id']).values(receipt=receipt));run=c.execute(select(runs).where(runs.c.id==rid2)).mappings().one();result=copy.deepcopy(run['result']);result['steps'][2]=receipt;result['output_by_step']['writeup']['text']=receipt['data']['text'];result['output']['writeup_text']=receipt['data']['text'];c.execute(update(runs).where(runs.c.id==rid2).values(result=result));evs=c.execute(select(events).where(events.c.run_id==rid2,events.c.kind=='CSV_DAG_STEP_VERIFIED')).mappings().all()
       for ev in evs:
        if ev['data']['step_id']=='writeup':c.execute(update(events).where(events.c.id==ev['id']).values(data={**ev['data'],'receipt_fingerprint':fingerprint(receipt)}))
      else:
       rows=c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind.in_(['csv_dag_run','csv_dag_run_seal']))).mappings().all();keys={x['request_key'] for x in rows if x['snapshot']['response'].get('run_id')==rid2};check(len(keys)==1,'accepted pair key independently located');c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.request_key.in_(keys),delivery_graph_requests.c.kind.in_(['csv_dag_run','csv_dag_run_seal'])));c.execute(delete(internal_instance_data).where(internal_instance_data.c.instance_id==i['id']));c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.run_id==rid2));c.execute(delete(internal_app_runs).where(internal_app_runs.c.id==a['app_run_id']));c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(data_version=0))
     denied_no_write(e,base)
    elif case=='old-fence':
     w=Worker(e[0],e[1],ForbiddenModel());old=e[0].claim(w.id,e[1].lease_seconds);dag.advance(w,old);dag.advance(w,old)
     with e[0].tx() as c:c.execute(update(runs).where(runs.c.id==rid2).values(lease_until=0))
     nw=Worker(e[0],e[1],ForbiddenModel());job=e[0].claim(nw.id,e[1].lease_seconds);check(job['fence']>old['fence'],'cold higher fence before thirdreport');before=fingerprint(snapshot(e))
     try:dag.advance(w,old);raise AssertionError('old fence accepted report')
     except DomainError:pass
     check(fingerprint(snapshot(e))==before,'old fence no report/typed writes');nw.process(job);got=request(e,'GET',base);check(got['data_version']==1 and len(got['data'])==1,'new fence finishes one typed row')
    else:
     w=Worker(e[0],e[1],ForbiddenModel());job=e[0].claim(w.id,e[1].lease_seconds)
     for _ in range(3):check(dag.advance(w,job),'actual step before final transaction')
     original=instances.commit_result
     def expire(st,c,live,bound,value,limits):
      out=original(st,c,live,bound,value,limits);c.execute(update(runs).where(runs.c.id==rid2).values(created_at=0));return out
     instances.commit_result=expire;before=fingerprint(snapshot(e))
     try:
      try:dag.advance(w,job);raise AssertionError('expired afterappend committed')
      except DomainError as ex:check(ex.code=='BUDGET_EXHAUSTED','final deadline after actual typed append refused')
     finally:instances.commit_result=original
     check(fingerprint(snapshot(e))==before,'whole final append/pointer/status rollback');check(dag.advance(w,job) is False,'valid final retry');check(request(e,'GET',base)['data_version']==1,'exactly1 typed row after retry')
  results.append({'case':case,'status':'PASS','checks':checks,'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);results.append({'case':case,'status':'FAIL','checks':checks,'error':err});print(err,flush=True)
 finally:
  (folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()
 print(case,results[-1]['status'],len(checks),flush=True)
(ROOT/'backend-results.json').write_text(json.dumps(results,indent=2));freeze('backend-after');assert all(r['status']=='PASS' for r in results)
