"""Independent review probes; no author two-sum fixtures or result oracle."""
import copy
import csv
import hashlib
import io
from fractions import Fraction

import pytest
from conftest import env
from fastapi.testclient import TestClient
from sqlalchemy import select, update, func
from test_delivery_graph_apps import path, snapshot
from test_internal_lifecycle import limits

from sim2act.api import create_app
from sim2act import csv_dag as dag, csv_dag_instances as reuse
from sim2act.column_patches import read_pair
from sim2act.db import (Store, fingerprint, grants, internal_app_runs, internal_instance_data, internal_instances,
                        internal_releases, internal_run_bindings, operations, runs)
from sim2act.worker import Worker

NAMES = ['ledger_sum', 'subtotal']
CSV = 'sku,cost,units,tax\na,0.125,-1.50,4\nb,-0.005,2.75,8\nc,7.380,-0.25,16\n'

class NoExternalModel:
    def request(self, *args, **kwargs):
        raise AssertionError('No model adapter may be called')

def reply(client, method, url, data=None, status=200):
    r = getattr(client, method)(url, **({'json':data} if data is not None else {}))
    assert r.status_code == status, (url, r.status_code, r.text)
    return r.json()

def graph(cols=('cost','units'), extra=False):
    nodes = [dict(step_id='origin', action='resource.read', depends_on=[],
        inputs={'resource_id':dict(source='data',ref='source',field='resource_id')})]
    for sid,col in zip(NAMES,cols):
        nodes.append(dict(step_id=sid, action='data.aggregate_csv', column=col,
            depends_on=['origin'], inputs={'resource_id':dict(source='step',ref='origin',field='resource_id'),
            'column':dict(source='input',field=sid+'_column')}))
    if extra:
        n = copy.deepcopy(nodes[-1]); n['step_id']='third'; n['inputs']['column']['field']='third_column';nodes.append(n)
    return dict(version='csv.composition.v1',nodes=nodes)

def process(env, a, cold=False):
    store = Store(env[1].database_url,test_only=True) if cold else env[0]
    try:
        w=Worker(store,env[1],NoExternalModel()); job=store.claim(w.id,env[1].lease_seconds)
        assert job['id']==a['run_id'];w.process(job)
        return job
    finally:
        if cold: store.engine.dispose()

def setup(env, extra=False):
    c,pid=env[2],env[5]
    rid=reply(c,'post',f'/api/projects/{pid}/resources',dict(name='independent.csv',format='csv',content=CSV),201)['id']
    aid=reply(c,'post',f'/api/projects/{pid}/apps/csv-preview',dict(name='review sums',goal='frozen sums',resource_id=rid),201)['id']
    draft=reply(c,'get',f'/api/apps/{aid}')
    anchor=reply(c,'post',path(env,aid)+'/derive',dict(expected_candidate_fingerprint=draft['fingerprint'],request_key='anchor'),201)
    base=f'/api/projects/{pid}/apps/{aid}/csv-dag'
    body=dict(expected_candidate_fingerprint=anchor['candidate_fingerprint'], expected_graph_fingerprint=anchor['graph_fingerprint'],
        column='cost',request_key='review-source',composition=graph(extra=extra))
    return aid,rid,base,body

def source(env, base, body):
    plan=reply(env[2],'post',base,body,201)
    a=reply(env[2],'post',base+'/'+body['request_key']+'/runs',dict(expected_plan_fingerprint=plan['plan_fingerprint'],
        consent='CONFIRM_EXACT_OFFLINE_CSV_DAG',request_key='run-'+body['request_key']),202)
    job=process(env,a)
    p=dag.inspect_job(env[0],env[3],job['id'],limits(env));assert p['status']=='SUCCEEDED',p
    return plan,a

def release(env, plan, a, key='save'):
    ap=reply(env[2],'post',f"/api/csv-dag/runs/{a['run_id']}/release-approvals",dict(expected_plan_fingerprint=plan['plan_fingerprint'],request_key=key),201)
    reply(env[2],'get',f"/api/internal/approvals/{ap['id']}")
    return reply(env[2],'post',f"/api/internal/approvals/{ap['id']}/commit",dict(fingerprint=ap['fingerprint']))

def create(env, rel):
    return reply(env[2],'post',f"/api/internal/releases/{rel['id']}/instances",dict(expected_release_fingerprint=rel['fingerprint'],request_key='make'),201)

def run_body(i,rel,value=None,key='run'):
    return dict(expected_revision=i['revision'],expected_release_fingerprint=rel['fingerprint'],
        input=value if value is not None else dict(columns=dict(ledger_sum='units',subtotal='tax')),request_key=key)

def fixture(env):
    aid,rid,base,body=setup(env);plan,a=source(env,base,body);rel=release(env,plan,a)
    return aid,rid,base,body,plan,a,rel,create(env,rel)

def oracle(out, rid, cols):
    rows=list(csv.DictReader(io.StringIO(CSV)));assert set(out)==set(NAMES)
    for sid,col in cols.items():
        expected=dict(resource_id=rid,column=col,count=len(rows),source_hash=hashlib.sha256(CSV.encode()).hexdigest())
        value=dict(out[sid]);total=value.pop('sum');assert value==expected
        assert Fraction(total)==sum((Fraction(row[col]) for row in rows),Fraction())

def test_cold_new_worker_decimal_oracle_and_idempotency(env):
    aid,rid,base,body,plan,original,rel,i=fixture(env)
    assert rel['snapshot']['execution_source']['aggregate_steps']==NAMES
    assert all(n['columns']==['cost','units','tax'] for n in rel['snapshot']['execution_source']['aggregate_nodes'].values())
    ids=[]
    for j,cols in enumerate([dict(ledger_sum='units',subtotal='cost'),dict(ledger_sum='cost',subtotal='units')]):
        request=run_body(i,rel,dict(columns=cols),str(j));url=f"/api/internal/instances/{i['id']}/runs"
        a=reply(env[2],'post',url,request,202);ids.append(a['run_id'])
        assert reply(env[2],'post',url,request,202)['run_id']==a['run_id']
        changed=copy.deepcopy(request);changed['input']['columns']['subtotal']='tax'
        before=fingerprint(snapshot(env));reply(env[2],'post',url,changed,409);assert fingerprint(snapshot(env))==before
        process(env,a,cold=True)
        p=reply(env[2],'get',url+'/'+a['run_id']);assert p['status']=='SUCCEEDED';oracle(p['output'],rid,cols)
        assert p['proof']['model_requests']==0 and p['proof']['business_writes']==1
        with env[0].engine.connect() as c:
            assert c.execute(select(func.count()).select_from(operations).where(operations.c.run_id==a['run_id'])).scalar()==3
    assert len(set(ids+[original['run_id']]))==3
    cold=Store(env[1].database_url,test_only=True)
    try:
        client=TestClient(create_app(cold,env[1]));client.headers['Authorization']='Bearer synthetic-test-A'
        before=fingerprint(snapshot(env));detail=reply(client,'get',f"/api/internal/instances/{i['id']}")
        assert detail['data_version']==2 and len(detail['runs'])==2 and len(detail['data'])==2
        assert fingerprint(snapshot(env))==before;client.close()
    finally: cold.engine.dispose()

@pytest.mark.parametrize('bad',[
    None,[],{'columns':None},{'columns':[]},{'columns':{'ledger_sum':'cost'}},
    {'columns':{'ledger_sum':'cost','subtotal':'units','third':'tax'}},
    {'columns':{'ledger_sum':'cost','subtotal':False}},
    {'columns':{'ledger_sum':'cost','subtotal':'sku'}},
    {'columns':{'ledger_sum':'cost','subtotal':'units'},'limits':{'max_tools':999}},
])
def test_input_rejection_atomic(env,bad):
    *_,rel,i=fixture(env); request=run_body(i,rel,bad);request['input']=bad
    before=fingerprint(snapshot(env));r=env[2].post(f"/api/internal/instances/{i['id']}/runs",json=request)
    assert r.status_code in (409,422),r.text;assert fingerprint(snapshot(env))==before

def test_two_sum_version_switch_roundtrip_preserves_data(env):
    aid,rid,base,body,plan,original,rel,i=fixture(env)
    req=run_body(i,rel);a=reply(env[2],'post',f"/api/internal/instances/{i['id']}/runs",req,202);process(env,a)
    original_data=reply(env[2],'get',f"/api/internal/instances/{i['id']}")['data']
    body['request_key']='changed-source';body['column']='tax';body['composition']=graph(('tax','cost'))
    p,b=source(env,base,body);second=release(env,p,b,'second')
    for rel_target in (second,rel):
        ap=reply(env[2],'post',f"/api/internal/instances/{i['id']}/switch-approvals",dict(target_release_id=rel_target['id'],
            expected_target_fingerprint=rel_target['fingerprint'],expected_revision=i['revision']),201)
        reply(env[2],'post',f"/api/internal/instances/{i['id']}/switch-approvals/{ap['id']}/commit",dict(fingerprint=ap['fingerprint']))
        i=reply(env[2],'get',f"/api/internal/instances/{i['id']}");assert i['data']==original_data
    assert i['revision']==3

def test_three_sums_not_mislabeled_as_two(env):
    aid,rid,base,body=setup(env,extra=True);plan,a=source(env,base,body)
    before=fingerprint(snapshot(env));reply(env[2],'post',f"/api/csv-dag/runs/{a['run_id']}/release-approvals",dict(
        expected_plan_fingerprint=plan['plan_fingerprint'],request_key='reject-four'),409)
    assert fingerprint(snapshot(env))==before

@pytest.mark.parametrize('attack',['cancel','revoke','budget','release-type'])
def test_partial_worker_never_saves_two_result_record(env,attack):
    aid,rid,base,body,plan,original,rel,i=fixture(env)
    a=reply(env[2],'post',f"/api/internal/instances/{i['id']}/runs",run_body(i,rel),202)
    w=Worker(env[0],env[1],NoExternalModel());job=env[0].claim(w.id,env[1].lease_seconds)
    assert dag.advance(w,job)
    if attack=='cancel':
        j=dag.inspect_job(env[0],env[3],job['id'],limits(env))
        reply(env[2],'post',f"/api/internal/instances/{i['id']}/runs/{job['id']}/commands",dict(command='cancel',version=j['version']))
    elif attack=='budget': w.s=type(env[1])(**{**vars(env[1]),'max_tools':2})
    elif attack=='revoke':
        with env[0].tx() as c:c.execute(update(grants).where(grants.c.resource_id==rid).values(revoked=True))
    else:
        with env[0].tx() as c:
            snap=copy.deepcopy(rel['snapshot']);snap['execution_source']['aggregate_nodes']['subtotal']['limits']['max_tools']=True
            c.execute(update(internal_releases).where(internal_releases.c.id==rel['id']).values(snapshot=snap,fingerprint=fingerprint(snap)))
    w.process(job)
    with env[0].engine.connect() as c:
        saved=c.execute(select(runs).where(runs.c.id==job['id'])).mappings().one()
        assert saved['status'] in ('FAILED','WAITING_RESOURCE','CANCELLED') and saved['result'] is None
        assert not c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==i['id'])).first()

def test_consistent_ledger_operation_run_result_rewrite_rejected(env):
    *_,rel,i=fixture(env)
    a=reply(env[2],'post',f"/api/internal/instances/{i['id']}/runs",run_body(i,rel),202);process(env,a)
    with env[0].tx() as c:
        ar=c.execute(select(internal_app_runs).where(internal_app_runs.c.id==a['app_run_id'])).mappings().one()
        output=copy.deepcopy(ar['output']);output['subtotal']['sum']='29'
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id==ar['id']).values(output=output))
        data={'result':output};c.execute(update(internal_instance_data).where(internal_instance_data.c.run_id==ar['id']).values(data=data,fingerprint=fingerprint(data)))
        op=c.execute(select(operations).where(operations.c.run_id==a['run_id'],operations.c.receipt['step_id'].as_string()=='subtotal')).mappings().one()
        receipt=copy.deepcopy(op['receipt']);receipt['data']=output['subtotal']
        c.execute(update(operations).where(operations.c.id==op['id']).values(receipt=receipt))
        row=c.execute(select(runs).where(runs.c.id==a['run_id'])).mappings().one()
        result=copy.deepcopy(row['result']);result['output_by_step']['subtotal']=output['subtotal']
        for p in result['steps']:
            if p['step_id']=='subtotal': p['data']=output['subtotal']
        if 'instance_result' in result:result['instance_result']['record_fingerprint']=fingerprint(data)
        c.execute(update(runs).where(runs.c.id==a['run_id']).values(result=result))
    before=fingerprint(snapshot(env));error=reply(env[2],'get',f"/api/internal/instances/{i['id']}",status=400)
    assert error['error']['code']=='VERIFICATION_FAILED'
    assert fingerprint(snapshot(env))==before

def test_foreign_identity_and_same_owner_wrong_project_rejected(env):
    *_,rel,i=fixture(env)
    before=fingerprint(snapshot(env));env[2].headers['Authorization']='Bearer synthetic-test-B'
    reply(env[2],'get',f"/api/internal/instances/{i['id']}",status=403)
    reply(env[2],'post',f"/api/internal/instances/{i['id']}/runs",run_body(i,rel),403)
    assert fingerprint(snapshot(env))==before
    env[2].headers['Authorization']='Bearer synthetic-test-A'
    pid=reply(env[2],'post','/api/projects',dict(name='other owned project'),201)['id']
    with env[0].tx() as c:c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(project_id=pid))
    r=env[2].get(f"/api/internal/instances/{i['id']}");assert r.status_code in (403,409),r.text

def test_readback_release_node_column_limit_tamper_closed(env):
    *_,rel,i=fixture(env)
    with env[0].tx() as c:
        snap=copy.deepcopy(rel['snapshot']);snap['execution_source']['aggregate_nodes']['subtotal']['columns'].append('sku')
        c.execute(update(internal_releases).where(internal_releases.c.id==rel['id']).values(snapshot=snap,fingerprint=fingerprint(snap)))
    before=fingerprint(snapshot(env));reply(env[2],'get',f"/api/internal/instances/{i['id']}",status=409)
    assert fingerprint(snapshot(env))==before
