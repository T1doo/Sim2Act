import copy, hashlib, json, os, tempfile, traceback
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
os.environ.pop('SIM2ACT_TEST_DATABASE_URL', None)
from conftest import env as fixture
from test_project_column_patches import start, work
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
from test_csv_dag import NoModel
from test_run_dispatch_owner import statements, assert_no_ledger_read
from sim2act import lifecycle, project_column_patches as parent, project_column_versions as versions
from sim2act.api import create_app
from sim2act.db import Store, grants, fingerprint, internal_approvals
from sim2act.worker import Worker
from fastapi.testclient import TestClient
from sqlalchemy import select, update

ROOT=Path('/tmp/project-column-versions-independent')
REPO=Path('/workspace/Sim2Act')
frozen=json.loads((REPO/'docs/evidence/project-column-versions-20261011/frozen-before.json').read_text())
hashes={f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in frozen if f.startswith('src/')}
assert all(hashes[f]==frozen[f] for f in hashes), 'source not frozen'
result={'source_sha256':hashes,'checks':[],'failures':[],'skip':0,'not_run':['PG','Windows','native browser','real models','paid APIs','old source upgrade','full P-A/P-B','remote CI','deployment']}
@contextmanager
def env():
    d=Path(tempfile.mkdtemp(prefix='backend-',dir=ROOT));g=fixture.__wrapped__(d);e=next(g)
    try:yield e
    finally:g.close()
def passed(name,**details):
    result['checks'].append({'name':name,'status':'PASS',**details});print('PASS',name,flush=True)
def scenario(name,fn):
    try:fn()
    except Exception:
        error=traceback.format_exc();result['failures'].append({'name':name,'status':'FAIL','error':error});print(error,flush=True)
def ready(e):
    vals,p,b,a=start(e);work(e,a);r=e[2].post(vals[0]+'/project-binding/finalize',json=b);assert r.status_code==201,r.text
    base=vals[0]+'/project-binding/internal-versions';r=e[2].post(base,json={'expected_receipt_fingerprint':r.json()['receipt_fingerprint'],'request_key':'project-binding'});assert r.status_code==201,r.text
    pv=r.json();cf={'expected_preview_fingerprint':pv['preview_fingerprint'],'request_key':'project-binding','consent':'CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS'}
    return vals,p,base,pv,cf
def create(e):
    vals,p,base,pv,cf=ready(e);r=e[2].post(base+'/commit',json=cf);assert r.status_code==201,r.text
    return vals,p,base,pv,cf,r.json()
def reject(r,e,before):
    assert r.status_code in (400,403,409),(r.status_code,r.text);assert snapshot(e)==before,'partial writes'
    return r.json()['error']['code']
def final_fault(fault):
    with env() as e:
        vals,p,base,pv,cf=ready(e);before=snapshot(e);original=versions.patches.save_pair;clock=[versions.time.time()]
        def inject(c,user,aid,kind,key,body,value):
            original(c,user,aid,kind,key,body,value)
            if kind==versions.COMMIT:
                if fault=='grant':c.execute(update(grants).where(grants.c.resource_id==vals[5]).values(expires_at=0))
                elif fault=='expiry':clock[0]=pv['expires_at']
                else:
                    cancel=versions.Cancellation(expected_preview_fingerprint=pv['preview_fingerprint'],request_key=key,consent='CANCEL_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS')
                    original(c,user,aid,versions.CANCEL,key,cancel,dict(namespace=versions.NAMESPACE,request_key=key,preview_fingerprint=pv['preview_fingerprint'],state='CANCELLED'))
        with patch.object(versions.patches,'save_pair',inject),patch.object(versions.time,'time',lambda:clock[0]):r=e[2].post(base+'/commit',json=cf)
        passed('after final group insertion '+fault+' rolls back',error=reject(r,e,before),zero_partial_changes=True)
if not os.environ.get('INDEPENDENT_ONLY_COLD'):
    for f in ('grant','expiry','cancel'):scenario('final '+f,lambda f=f:final_fault(f))
def true_cancel():
    with env() as e:
        _,_,base,pv,cf=ready(e);cancel={**cf,'consent':'CANCEL_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS'}
        assert e[2].post(base+'/cancel',json=cancel).status_code==200;before=snapshot(e)
        assert e[2].get(base).json()['state']=='CANCELLED';reject(e[2].post(base+'/commit',json=cf),e,before)
        passed('real controller cancellation blocks later exact commit and GET has zero writes')
if not os.environ.get('INDEPENDENT_ONLY_COLD'):scenario('true cancellation',true_cancel)
def wait_restore():
    with env() as e:
        with e[0].engine.connect() as c:prior=c.connection.driver_connection.execute('PRAGMA busy_timeout').fetchone()[0]
        for fail in (False,True):
            try:
                with e[0].tx(wait_seconds=.05) as c:
                    assert c.connection.driver_connection.execute('PRAGMA busy_timeout').fetchone()[0]==50
                    if fail:raise RuntimeError('independent intentional rollback')
            except RuntimeError:assert fail
            with e[0].engine.connect() as c:assert c.connection.driver_connection.execute('PRAGMA busy_timeout').fetchone()[0]==prior
        passed('SQLite pooled timeout restored after success and rollback',original_timeout_ms=prior)
if not os.environ.get('INDEPENDENT_ONLY_COLD'):scenario('wait restoration',wait_restore)
def actual_run(e,client,entry,column,key):
    i=client.get('/api/internal/instances/'+entry['instance_id']).json();r=client.post('/api/internal/instances/'+i['id']+'/runs',json=dict(expected_revision=i['revision'],expected_release_fingerprint=i['release_fingerprint'],input={'column':column},request_key=key));assert r.status_code==202,r.text
    worker=Worker(e[0],e[1],NoModel());job=e[0].claim(worker.id,e[1].lease_seconds);assert job['id']==r.json()['run_id'];worker.process(job)
    detail=client.get('/api/internal/instances/'+i['id']);assert detail.status_code==200,detail.text
    run=next(x for x in detail.json()['runs'] if x['run_id']==job['id']);assert run['status']=='SUCCEEDED',run
    assert run['output']['sum']==('15' if column=='quantity' else '30');assert len(run['proof']['steps'])==3 and run['proof']['business_writes']==1
    return run
def cold_and_history():
    with env() as e:
        vals,p,base,pv,cf,group=create(e);entry=next(x for x in group['entries'] if x['app_id']==vals[2]);unrelated_nodes=p['preserved'][0]['nodes']
        before=snapshot(e);assert e[2].get(base).json()['group_fingerprint']==group['group_fingerprint'];assert e[2].post(base+'/commit',json=cf).json()['cached'];assert snapshot(e)==before
        passed('exact group replay and GET return original identities with zero writes',group_entries=len(group['entries']))
        coldstore=Store(e[1].database_url,test_only=True);client=TestClient(create_app(coldstore,e[1]));client.headers['Authorization']='Bearer synthetic-test-A'
        try:
            a=actual_run(e,client,entry,'quantity','ind-cold-quantity');b=actual_run(e,client,entry,'amount','ind-cold-amount');assert a['run_id']!=b['run_id']
            passed('cold Store actual three-operation worker computes two fresh inputs',sums=[a['output']['sum'],b['output']['sum']],typed_writes=2)
            # Second independently checked group, same source app/family, reversed default.
            pb={**vals[1],'request_key':'ind-flip','baseline_column':'quantity','column':'amount'};r=client.post(vals[0],json=pb);assert r.status_code==201,r.text
            pc=dict(expected_patch_fingerprint=r.json()['patch_fingerprint'],request_key='ind-flip',consent='CONFIRM_EXACT_FINITE_PROJECT_COLUMN_PATCH')
            r=client.post(vals[0]+'/ind-flip/runs',json=pc);assert r.status_code==202,r.text;work(e,r.json());r=client.post(vals[0]+'/ind-flip/finalize',json=pc);assert r.status_code==201,r.text
            otherbase=vals[0]+'/ind-flip/internal-versions';r=client.post(otherbase,json=dict(expected_receipt_fingerprint=r.json()['receipt_fingerprint'],request_key='ind-flip'));assert r.status_code==201,r.text
            r=client.post(otherbase+'/commit',json=dict(expected_preview_fingerprint=r.json()['preview_fingerprint'],request_key='ind-flip',consent='CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS'));assert r.status_code==201,r.text
            target=next(x for x in r.json()['entries'] if x['app_id']==entry['app_id']);i=client.get('/api/internal/instances/'+entry['instance_id']).json()
            stale=lifecycle.prepare_switch(e[0],e[3],i['id'],target['release_id'],i['revision'],limits(e),expected_target_fingerprint=target['release_fingerprint'])
            lifecycle.commit_switch(e[0],e[3],stale['id'],stale['fingerprint'],limits(e));before=snapshot(e);assert client.get(base).status_code==200;assert snapshot(e)==before
            passed('original group read validates legal pointer at B without recreating A')
            actual_run(e,client,entry,'amount','ind-on-B');i=client.get('/api/internal/instances/'+entry['instance_id']).json();back=lifecycle.prepare_switch(e[0],e[3],i['id'],entry['release_id'],i['revision'],limits(e),expected_target_fingerprint=entry['release_fingerprint']);lifecycle.commit_switch(e[0],e[3],back['id'],back['fingerprint'],limits(e))
            detail=client.get('/api/internal/instances/'+entry['instance_id']).json();assert detail['revision']==3 and detail['data_version']==3 and len(detail['history'])==3
            assert client.get('/api/internal/instances/'+entry['instance_id']+'/runs/'+a['run_id']).status_code==200
            before=snapshot(e);assert client.get(base).status_code==200;assert snapshot(e)==before
            passed('A to B to A retains typed data and cold original terminal proofs',revision=3,records=3)
            client.headers['Authorization']='Bearer synthetic-test-B';before=snapshot(e)
            for path in (base,'/api/internal/releases/'+entry['release_id']+'/project-column-origin'):
                assert client.get(path).status_code==403
            assert snapshot(e)==before;passed('foreign identity cannot recover group or peer origin')
            client.headers['Authorization']='Bearer synthetic-test-A';new=client.post(f'/api/projects/{e[5]}/apps/csv-preview',json=dict(name='later unrelated draft',goal='independent unrelated growth',resource_id=vals[5]));assert new.status_code==201,new.text
            before=snapshot(e);assert client.get(base).status_code==409
            origin=client.get('/api/internal/releases/'+entry['release_id']+'/project-column-origin');assert origin.status_code==200,origin.text
            assert set(origin.json())=={'namespace','release_id','release_fingerprint','origin','affected','source','execution_source'} and origin.json()['affected']['app_id']==entry['app_id'];assert snapshot(e)==before
            assert origin.json()['execution_source']==client.get('/api/internal/releases/'+entry['release_id']).json()['snapshot']['execution_source']
            actual_run(e,client,entry,'quantity','ind-after-growth');passed('project growth invalidates group proof while peer origin and actual cold worker remain usable')
            with e[0].tx() as c:
                r=c.execute(select(internal_approvals).where(internal_approvals.c.id==pv['entries'][0]['approval']['id'])).mappings().one();payload=copy.deepcopy(r['payload']);payload.pop('project_column_group');c.execute(update(internal_approvals).where(internal_approvals.c.id==r['id']).values(payload=payload,fingerprint=fingerprint(payload)))
            affected=next(x for x in group['entries'] if x['app_id']==pv['entries'][0]['app_id']);before=snapshot(e);assert client.get('/api/internal/releases/'+affected['release_id']).status_code==409;assert snapshot(e)==before;passed('re-signed fixed approval cannot downgrade exact whole-group origin')
        finally:client.close();coldstore.engine.dispose()
scenario('cold worker and historical replay',cold_and_history)
def actual_source_endpoint():
    with env() as e:
        vals,p,base,pv,cf=ready(e);a=pv['entries'][0];path='/api/internal/approvals/'+a['approval']['id']+'/project-column-origin';before=snapshot(e)
        r=e[2].get(path);assert r.status_code==200,r.text
        assert r.json()['execution_source']==a['snapshot']['execution_source'] and r.json()['approval_fingerprint']==a['approval']['fingerprint'];assert snapshot(e)==before
        passed('preapproval source endpoint derives exact full actual Run source with zero writes')
        e[2].headers['Authorization']='Bearer synthetic-test-B'
        with statements(e[0]) as seen:r=e[2].get(path)
        assert r.status_code==403,r.text;assert_no_ledger_read(seen);assert snapshot(e)==before
        e[2].headers['Authorization']='Bearer synthetic-test-A'
        with e[0].tx() as c:c.execute(update(grants).where(grants.c.resource_id==vals[5]).values(expires_at=0))
        before=snapshot(e)
        with statements(e[0]) as seen:r=e[2].get(path)
        assert r.status_code==403,r.text;assert_no_ledger_read(seen);assert snapshot(e)==before
        passed('foreign and expired source authority deny preapproval origin before protected ledger read with zero writes')
if not os.environ.get('INDEPENDENT_ONLY_COLD'):scenario('actual source endpoint',actual_source_endpoint)
result['source_sha256_after']={f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in hashes}
assert result['source_sha256_after']==hashes,'product source changed during review'
result['pass']=len(result['checks']);result['fail']=len(result['failures']);result['status']='FAIL' if result['fail'] else 'PASS'
(ROOT/'backend-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'pass':result['pass'],'fail':result['fail'],'skip':0}),flush=True)
raise SystemExit(bool(result['fail']))
