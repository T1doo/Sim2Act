"""Independent bounded review; shared isolated fixture only, no author tests."""
import copy
import json
from itertools import permutations
import pytest
from conftest import env
from test_column_patches import setup as source_setup
from sqlalchemy import select, update
from sim2act import csv_dag as dag
from sim2act.db import Store, events, fingerprint, operations, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker
from sim2act.preflight import preflight

class RejectModel:
    def generate(self, *_a, **_k):
        raise AssertionError('No model authorization')

def atom(op, field, value=None, ref=None):
    a={'op':op,'source':{'source':'step' if ref else 'input','field':field}}
    if ref:a['source']['ref']=ref
    if op!='exists':a['value']=value
    return a

def plan(env, expression, target='report', extra=None):
    aid,rid,anchor,*_=source_setup(env)
    base=f'/api/projects/{env[5]}/apps/{aid}/csv-dag'
    branches=[{'step_id':target,'when':expression}]
    if extra:branches.append(extra)
    body={'expected_candidate_fingerprint':anchor['candidate_fingerprint'],
          'expected_graph_fingerprint':anchor['graph_fingerprint'],'column':'quantity',
          'request_key':'independent','branch_patch':branches}
    r=env[2].post(base,json=body)
    assert r.status_code==201,r.text
    return base,r.json(),body

def execute(env,base,p,values=None):
    body={'expected_plan_fingerprint':p['plan_fingerprint'],'consent':'CONFIRM_EXACT_OFFLINE_CSV_DAG',
          'request_key':'independent-run','branch_inputs':values or {}}
    r=env[2].post(base+'/independent/runs',json=body)
    assert r.status_code==202,r.text
    w=Worker(env[0],env[1],RejectModel());job=env[0].claim(w.id,env[1].lease_seconds)
    return w,job,body

def read(env,job):
    r=env[2].get('/api/csv-dag/runs/'+job['id'])
    assert r.status_code==200,r.text
    return r.json()

@pytest.mark.parametrize('op', ['all','any'])
@pytest.mark.parametrize('order', [(0,1,2,3),(3,2,1,0)])
def test_four_leaf_types_order_and_cold_read(env,op,order):
    leaves=[atom('in','include_report',[False]),atom('exists','count',ref='aggregate'),
            atom('in','count',[2,7],ref='aggregate'),atom('eq','sum','15',ref='aggregate')]
    base,p,_=plan(env,{'op':op,'conditions':[leaves[i] for i in order]})
    assert p['branch_semantics']=='typed-conditions.v2'
    w,j,b=execute(env,base,p,{'include_report':False});w.process(j)
    r=read(env,j)
    assert r['status']=='SUCCEEDED'
    d=r['steps'][2]['branch_decision']
    assert len(d['observation']['conditions'])==4 and all(v['passed'] for v in d['observation']['conditions'])
    assert d['condition']==p['definition']['manifest']['workflow'][2]['when']
    assert r['model_requests']==r['business_writes']==0 and not r['publishable']
    cold=Store(env[1].database_url,test_only=True)
    try:
        assert fingerprint(dag.inspect_job(cold,env[3],j['id'],None))==fingerprint(r)
    finally:cold.engine.dispose()
    same=env[2].post(base+'/independent/runs',json=b)
    assert same.status_code==202 and same.json()['cached'] and same.json()['run_id']==j['id']
    with env[0].tx() as c:
        assert len(c.execute(select(operations).where(operations.c.run_id==j['id'])).all())==3

@pytest.mark.parametrize('op,first_value',[('all',3),('any',2)])
@pytest.mark.parametrize('missing_op',['eq','in'])
def test_missing_last_leaf_not_hidden(env,op,first_value,missing_op):
    leaves=[atom('eq','count',first_value,ref='aggregate'),
            atom(missing_op,'include_report',[True] if missing_op=='in' else True)]
    base,p,_=plan(env,{'op':op,'conditions':leaves})
    w,j,_=execute(env,base,p);w.process(j);r=read(env,j)
    assert r['status']=='FAILED' and r['error']['code']=='INVALID_INPUT'
    assert [s['step_id'] for s in r['steps']]==['preview','aggregate']

@pytest.mark.parametrize('op',['all','any'])
def test_skipped_predecessor_preempts_missing_group_without_operations(env,op):
    base,p,_=plan(env,{'op':op,'conditions':[atom('eq','include_report',True),
              atom('eq','count',2,ref='aggregate')]},extra={'step_id':'aggregate','when':atom('exists','include_report')})
    w,j,_=execute(env,base,p);w.process(j);r=read(env,j)
    assert r['status']=='PARTIAL'
    assert [s['status'] for s in r['steps']]==['VERIFIED','SKIPPED','SKIPPED']
    assert r['steps'][2]['branch_decision']['reason']=='DEPENDENCY_SKIPPED'
    assert r['steps'][2]['branch_decision']['observation']=={'evaluated':False}
    assert r['steps'][2]['branch_decision']['skipped_predecessors']==['aggregate']
    with env[0].tx() as c:
        assert [v[0] for v in c.execute(select(operations.c.call_id).where(operations.c.run_id==j['id']))]==['preview']

@pytest.mark.parametrize('damage',['bool_count','self','undeclared','unknown_field','nested'])
def test_invalid_last_leaf_no_short_circuit_preflight(env,damage):
    base,p,b=plan(env,{'op':'any','conditions':[atom('exists','include_report'),atom('eq','count',2,ref='aggregate')]})
    bad=copy.deepcopy(b);bad['request_key']='invalid'
    leaf=bad['branch_patch'][0]['when']['conditions'][1]
    if damage=='bool_count':leaf['value']=True
    elif damage=='nested':leaf.clear();leaf.update({'op':'all','conditions':[atom('exists','include_report')]*2})
    elif damage=='unknown_field':leaf['source']['field']='missing'
    else:leaf['source']['ref']='report' if damage=='self' else 'preview'
    with env[0].tx() as c:
        before=[c.execute(select(t)).mappings().all() for t in [events,operations,runs]]
    r=env[2].post(base,json=bad)
    assert r.status_code in [400,409,422],r.text
    with env[0].tx() as c:
        assert [c.execute(select(t)).mappings().all() for t in [events,operations,runs]]==before

@pytest.mark.parametrize('passed',[True,False])
def test_cold_reconstruction_rejects_observation_value_tamper(env,passed):
    base,p,_=plan(env,{'op':'all','conditions':[atom('eq','include_report',True),atom('eq','count',2,ref='aggregate')]})
    w,j,_=execute(env,base,p,{'include_report':passed});w.process(j)
    with env[0].tx() as c:
        table=operations if passed else events
        row=c.execute(select(table).where(table.c.run_id==j['id'],
            table.c.call_id=='report' if passed else table.c.kind=='CSV_DAG_STEP_SKIPPED')).mappings().one()
        key='receipt' if passed else 'data';receipt=copy.deepcopy(row[key])
        receipt['branch_decision']['observation']['conditions'][1]['value']=999
        c.execute(update(table).where(table.c.id==row['id']).values(**{key:receipt}))
    cold=Store(env[1].database_url,test_only=True)
    try:
        with pytest.raises(DomainError) as e:dag.inspect_job(cold,env[3],j['id'],None)
        assert e.value.code in ['VERIFICATION_FAILED','VERSION_CONFLICT']
    finally:cold.engine.dispose()

def test_number_schema_leaf_preflight_and_evaluation_does_not_coerce(env):
    base,p,_=plan(env,{'op':'all','conditions':[atom('exists','include_report'),atom('eq','count',2,ref='aggregate')]})
    m=copy.deepcopy(p['definition']['manifest'])
    m['input_schema']['properties']['threshold']={'type':'number'}
    m['workflow'][2]['when']={'op':'all','conditions':[atom('eq','threshold',1.5),atom('in','threshold',[1.5,2.5])]}
    from test_internal_lifecycle import limits
    preflight(json.dumps(m),p['definition']['actions'],limits(env))
    d=dag.decision({'branch_semantics':'typed-conditions.v2'},m['workflow'][2],{'threshold':1.5},{},[])
    assert d['branch_decision']['passed']
    for v in [True,'1.5']:
        bad=copy.deepcopy(m);bad['workflow'][2]['when']['conditions'][1]['value']=[v]
        with pytest.raises(DomainError):preflight(json.dumps(bad),p['definition']['actions'],limits(env))

@pytest.mark.parametrize('enabled',[False,True])
def test_cold_fence_recovery_after_grouped_aggregate_preserves_prefix(env,enabled):
    base,p,_=plan(env,{'op':'all','conditions':[atom('exists','include_report'),atom('eq','include_report',True)]},
        target='aggregate',extra={'step_id':'report','when':{'op':'any','conditions':[
            atom('eq','include_report',False),atom('exists','count',ref='aggregate')]}})
    w,j,body=execute(env,base,p,{'include_report':enabled})
    assert dag.advance(w,j) and dag.advance(w,j)
    with env[0].tx() as c:
        prefix=c.execute(select(operations.c.id,operations.c.call_id).where(operations.c.run_id==j['id'])).all()
        c.execute(update(runs).where(runs.c.id==j['id']).values(lease_until=0))
    cold=Store(env[1].database_url,test_only=True)
    try:
        recovered=Worker(cold,env[1],RejectModel());new=cold.claim(recovered.id,env[1].lease_seconds)
        assert new['id']==j['id'] and new['fence']>j['fence']
        with pytest.raises(DomainError):dag.advance(w,j)
        recovered.process(new)
        r=dag.inspect_job(cold,env[3],j['id'],None)
        assert r['status']==('SUCCEEDED' if enabled else 'PARTIAL')
        assert r['steps'][2]['branch_decision']['reason']==('CONDITION_TRUE' if enabled else 'DEPENDENCY_SKIPPED')
        with cold.tx() as c:
            after=c.execute(select(operations.c.id,operations.c.call_id).where(operations.c.run_id==j['id'])).all()
            assert all(row in after for row in prefix)
            assert len(after)==(3 if enabled else 1)
    finally:cold.engine.dispose()

def test_group_preserves_v1_authority_budget_and_zero_requests(env):
    base,p,b=plan(env,{'op':'any','conditions':[atom('exists','include_report'),atom('eq','count',2,ref='aggregate')]})
    b=copy.deepcopy(b);b['request_key']='v1';b['branch_patch'][0]['when']=atom('exists','include_report')
    r=env[2].post(base,json=b);assert r.status_code==201,r.text
    v1=r.json();assert v1['branch_semantics']=='typed-conditions.v1'
    for key in ['runtime_limits','permission_requirements','dependency_lock','runtime_identity_requirements']:
        assert p['definition']['manifest'][key]==v1['definition']['manifest'][key]
    assert p['definition']['actions']==v1['definition']['actions']
    assert p['preflight']['budget_envelope']==v1['preflight']['budget_envelope']
    assert p['model_requests']==p['business_writes']==0
