import copy
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import time
import traceback
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.pop('SIM2ACT_TEST_DATABASE_URL', None)
from conftest import env as fixture
from test_project_column_material_reuse import setup, accept, work
from test_csv_logic_reuse import retire_old
from test_delivery_graph_apps import snapshot
from test_csv_dag import NoModel
from sim2act import csv_dag as dag, csv_dag_instances as instances, csv_logic_reuse as logic
from sim2act.api import create_app
from sim2act.db import Store, fingerprint, internal_approvals, internal_releases, delivery_graph_requests, operations, internal_instance_data, internal_instances, internal_app_runs, runs
from sim2act.worker import Worker
from fastapi.testclient import TestClient
from sqlalchemy import select, update, delete, insert, event

ROOT = Path('/tmp/project-csv-reuse-independent-20261011')
REPO = Path('/workspace/Sim2Act')
FROZEN = json.loads((REPO/'docs/evidence/project-column-material-reuse-20261011/frozen-before.json').read_text())
SOURCE = {f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in FROZEN if f.startswith('src/')}
assert all(FROZEN[f] == h for f,h in SOURCE.items()), 'product differs from freeze'
result = dict(source_sha256=SOURCE, checks=[], failures=[], skip=0, not_run=['PG','Windows','native browser','old source upgrade','real models','paid APIs','full P-A/P-B','remote CI'])
DIRECT = 'label,amount,quantity\nind-A,101,7.5\nind-B,202,-2.25\nind-C,-13,1.25\n'
FREE = 'label,units,net\nind-X,41,2.125\nind-Y,3,-0.125\nind-Z,-4,7.5\n'

@contextmanager
def env():
    path=Path(tempfile.mkdtemp(prefix='backend-',dir=ROOT));g=fixture.__wrapped__(path);e=next(g)
    try: yield e
    finally: g.close()

def passed(name, **details):
    result['checks'].append(dict(name=name,status='PASS',**details));print('PASS',name,flush=True)

def scenario(name, fn):
    try: fn()
    except Exception:
        error=traceback.format_exc();result['failures'].append(dict(name=name,status='FAIL',error=error));print(error,flush=True)

def oracle(content, column):
    rows=list(csv.DictReader(io.StringIO(content)))
    return sum((Fraction(row[column]) for row in rows),Fraction()),len(rows)

def release_instance(e, plan, job, key):
    r=e[2].post('/api/csv-dag/runs/'+job['id']+'/release-approvals',json=dict(expected_plan_fingerprint=plan['plan_fingerprint'],request_key=key));assert r.status_code==201,r.text
    r=e[2].post('/api/internal/approvals/'+r.json()['id']+'/commit',json=dict(fingerprint=r.json()['fingerprint']));assert r.status_code==200,r.text
    rel=r.json();r=e[2].post('/api/internal/releases/'+rel['id']+'/instances',json=dict(expected_release_fingerprint=rel['fingerprint'],request_key=key+'-instance'));assert r.status_code==201,r.text
    return rel,r.json()

def input_run(e, client, rel, instance, column, key, execute=True):
    r=client.post('/api/internal/instances/'+instance['id']+'/runs',json=dict(expected_revision=instance['revision'],expected_release_fingerprint=rel['fingerprint'],input={'column':column},request_key=key));assert r.status_code==202,r.text
    if execute: work(e,r.json())
    return r.json()

def rejection(e, r, before):
    assert r.status_code in (400,403,409),r.text;assert snapshot(e)==before,'partial mutation';return r.json()['error']['code']

def proof(e, rid, content, column, target):
    r=e[2].get('/api/csv-dag/runs/'+rid);assert r.status_code==200,r.text;p=r.json();assert p['status']=='SUCCEEDED' and len(p['steps'])==3
    actual=p['result']['output_by_step']['report'];total,count=oracle(content,column)
    assert Fraction(actual['sum'])==total and actual['count']==count and actual['column']==column and actual['resource_id']==target
    with e[0].tx() as c:
        ops=c.execute(select(operations).where(operations.c.run_id==rid)).mappings().all();assert len(ops)==3
        contract=e[0].frozen_contract(c,dag.row(c,e[3],rid));assert [v.resource_id for v in contract.resources]==[target]
    return p

def direct():
    with env() as e:
        source,old,group,_,body,path=setup(e,False,content=DIRECT);before=snapshot(e)
        r=e[2].post(path,json={**body,'column':'amount','request_key':'ind-wrong-approved-column'})
        passed('fixed direct refuses a different valid target numeric column with zero writes',error=rejection(e,r,before))
        value,accepted,url,confirmation=accept(e,path,body,'ind-target-direct');unchanged=snapshot(e)
        assert e[2].post(path,json=body).json()['plan']['plan_fingerprint']==value['plan']['plan_fingerprint']
        assert e[2].post(url,json=confirmation).json()['run_id']==accepted['run_id'];assert snapshot(e)==unchanged
        passed('original material key and run key replay exactly without extra writes')
        job=work(e,accepted);p=proof(e,job['id'],DIRECT,'quantity',body['expected_resource_id']);assert p['result']['output_by_step']['report']['sum']=='6.5'
        passed('actual direct target worker independently computes unseen quantity 6.5 with only target resource')
        rel,i=release_instance(e,value['plan'],job,'ind-direct-release');assert rel['snapshot']['execution_source']['default_column']=='quantity'
        passed('new target immutable release freezes proven quantity default despite first amount column')
        coldstore=Store(e[1].database_url,test_only=True);cold=TestClient(create_app(coldstore,e[1]));cold.headers['Authorization']='Bearer synthetic-test-A'
        try:
            assert cold.get('/api/internal/releases/'+rel['id']).json()['snapshot']['execution_source']['default_column']=='quantity'
            for col in ('amount','quantity'): input_run(e,cold,rel,i,col,'ind-cold-'+col)
            d=cold.get('/api/internal/instances/'+i['id']).json();assert d['data_version']==2 and {v['data']['result']['sum'] for v in d['data']}=={'290','6.5'} and len({v['run_id'] for v in d['runs']})==2
            passed('cold Store executes two independent unseen target inputs and retains typed history',sums=['290','6.5'])
        finally: cold.close();coldstore.engine.dispose()
        after=snapshot(e)
        for table in ('resources','principals','grants','app_drafts','delivery_graph_locks'):assert after[table]==before[table],table
        for table in ('internal_releases','internal_instances','internal_instance_data'):assert all(row in after[table] for row in before[table]),table
        assert source['snapshot']['execution_source']['default_column']=='quantity' and len(group['entries'])==2
        passed('original group versions instances canonical objects and human locks remain unchanged')
        with e[0].tx() as c:
            a=c.execute(select(internal_approvals).where(internal_approvals.c.id==rel['approval_id'])).mappings().one();payload=copy.deepcopy(a['payload']);payload['snapshot']['execution_source']['default_column']='amount';fp=fingerprint(payload['snapshot'])
            c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(payload=payload,fingerprint=fingerprint(payload)));c.execute(update(internal_releases).where(internal_releases.c.id==rel['id']).values(snapshot=payload['snapshot'],fingerprint=fp))
        before=snapshot(e);r=e[2].get('/api/internal/releases/'+rel['id']);assert r.status_code==409,r.text;assert snapshot(e)==before
        passed('coherently re-signed release and approval wrong default rejected by actual plan receipts')

@contextmanager
def sql_trace(store):
    seen=[]
    def capture(conn,cursor,sql,params,ctx,many):seen.append(dict(sql=sql,parameters=repr(params)))
    event.listen(store.engine,'before_cursor_execute',capture)
    try: yield seen
    finally: event.remove(store.engine,'before_cursor_execute',capture)

def free():
    with env() as e:
        source,old,group,obj,body,path=setup(e,True,content=FREE)
        public=json.dumps(obj,sort_keys=True);forbidden=['amount','quantity','column_overlay','default_column',old,source['id'],source['snapshot']['execution_source']['run_id'],source['snapshot']['execution_source']['source_hash']]
        assert all(x not in public for x in forbidden);assert len(obj['recipe']['nodes'])==3 and [x['action'] for x in obj['recipe']['nodes']]==['resource.read','data.aggregate_csv','intern.csv_report.v1'];assert 'column' not in obj['recipe']['nodes'][1]
        with e[0].tx() as c:
            raw=c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id==obj['id'])).scalar_one();assert set(raw['private_audit'])=={'release_id','release_fingerprint','approval_id','approval_fingerprint','run_id','app_id'}
        passed('fixed logic public whitelist carries no original CSV columns hash overlay default or result')
        retire_old(e,old);oldrun=source['snapshot']['execution_source']['run_id']
        assert e[2].get('/api/internal/releases/'+source['id']).status_code!=200 and e[2].get('/api/csv-dag/runs/'+oldrun).status_code!=200
        app=e[2].get('/api/apps/'+body['target_app_id']).json();r=e[2].post(f"/api/projects/{e[5]}/apps/{app['id']}/delivery-graph/derive",json=dict(expected_candidate_fingerprint=app['fingerprint'],request_key='ind-retired-current-target'));assert r.status_code==201,r.text;body={**body,'expected_graph_fingerprint':r.json()['graph_fingerprint']}
        with sql_trace(e[0]) as seen:
            assert e[2].get('/api/internal/csv-logics/'+obj['id']).status_code==200
            value,accepted,_,_=accept(e,path,body,'ind-free-target');job=work(e,accepted)
        for t in seen:
            sql=t['sql'].lower();params=t['parameters']
            if not sql.lstrip().startswith('select'):continue
            assert not ('from resources' in sql and old in params),t
            assert not ('from operations' in sql and oldrun in params),t
            assert not ('from runs' in sql and oldrun in params and re.search(r'runs\.(context|result)',sql)),t
        (ROOT/'data-free-sql-trace.json').write_text(json.dumps(seen,indent=2)+'\n')
        p=proof(e,job['id'],FREE,'net',body['expected_resource_id']);assert p['result']['output_by_step']['report']['sum']=='9.5'
        passed('deleted old CSV logic execution uses target only and no old Run context result or operation projection',sql_statements=len(seen))
        rel,i=release_instance(e,value['plan'],job,'ind-free-release');assert rel['snapshot']['execution_source']['default_column']=='net'
        input_run(e,e[2],rel,i,'units','ind-free-unseen-units');d=e[2].get('/api/internal/instances/'+i['id']).json();assert d['data_version']==1 and d['data'][0]['data']['result']['sum']=='40'
        passed('fixed-origin logic target saves its selected net default and new units 40 typed result')
        # Both immutable authorization seals can be re-signed, but the original key still binds the ID.
        with e[0].tx() as c:
            seals=[dict(x) for x in c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.request_key==obj['id'],delivery_graph_requests.c.kind.in_([logic.AUTH_KIND,logic.AUTH_KIND+'_seal']))).mappings()];assert len(seals)==2
            for x in seals:
                v=copy.deepcopy(x['snapshot']);v['request']['request_key']='ind-forged-original-key';c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id==x['app_id'],delivery_graph_requests.c.principal_id==x['principal_id'],delivery_graph_requests.c.kind==x['kind'],delivery_graph_requests.c.request_key==x['request_key']).values(snapshot=v,fingerprint=fingerprint(v),request_fingerprint=fingerprint(v['request'])))
        before=snapshot(e);r=e[2].get('/api/internal/csv-logics/'+obj['id']);assert r.status_code==409,r.text;assert snapshot(e)==before
        with e[0].tx() as c:
            for x in seals:c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.app_id==x['app_id'],delivery_graph_requests.c.principal_id==x['principal_id'],delivery_graph_requests.c.kind==x['kind'],delivery_graph_requests.c.request_key==x['request_key']).values(**x))
        passed('joint authorization seals re-signing cannot change original key without logic ID conflict')
        # Final expiry occurs after the actual typed insert, so the trailing gate must roll it back.
        accepted=input_run(e,e[2],rel,i,'net','ind-expire-after-typed-insert',False);w=Worker(e[0],e[1],NoModel());claimed=e[0].claim(w.id,e[1].lease_seconds);assert claimed['id']==accepted['run_id'];clock=[time.time()];orig=instances.commit_result;hit=[]
        def expire_after(*args,**kw):
            value=orig(*args,**kw);hit.append(True);clock[0]=obj['expires_at'];return value
        with patch.object(logic,'time',SimpleNamespace(time=lambda:clock[0])),patch.object(instances,'commit_result',expire_after):w.process(claimed)
        with e[0].tx() as c:
            j=c.execute(select(runs).where(runs.c.id==claimed['id'])).mappings().one();assert j['status']!='SUCCEEDED' and j['result'] is None;assert len(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==i['id'])).all())==1;assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id==i['id'])).scalar_one()==1
        assert hit
        passed('fixed-origin internal Run expiry after real typed insertion rolls back record and data version',fault_injection='logic clock at exact expiry after commit_result')
        accepted=input_run(e,e[2],rel,i,'net','ind-revoke-between-report-and-typed',False);w=Worker(e[0],e[1],NoModel());claimed=e[0].claim(w.id,e[1].lease_seconds);assert claimed['id']==accepted['run_id']
        for _ in range(3):assert dag.advance(w,claimed)
        r=e[2].post('/api/internal/csv-logics/'+obj['id']+'/revoke',json=dict(expected_logic_fingerprint=obj['fingerprint'],consent='REVOKE_DATA_FREE_CSV_LOGIC',request_key='ind-durable-stop'));assert r.status_code==200,r.text
        w.process(claimed)
        with e[0].tx() as c:
            j=c.execute(select(runs).where(runs.c.id==claimed['id'])).mappings().one();assert j['status']!='SUCCEEDED' and j['result'] is None;assert len(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==i['id'])).all())==1;assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id==i['id'])).scalar_one()==1;assert len(c.execute(select(operations).where(operations.c.run_id==claimed['id'])).all())==3
        passed('durable logic revocation after three real instance receipts prevents final typed commit and retains earlier result')

scenario('direct material and cold default',direct)
scenario('content-free audit and fixed-origin typed commit guards',free)
result['source_sha256_after']={f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in SOURCE};assert result['source_sha256_after']==SOURCE,'product changed during probe'
result.update(status='FAIL' if result['failures'] else 'PASS',pass_checks=len(result['checks']),fail=len(result['failures']))
(ROOT/'backend-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],pass_checks=result['pass_checks'],fail=result['fail'],skip=0)),flush=True)
raise SystemExit(bool(result['fail']))
