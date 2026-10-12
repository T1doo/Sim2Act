"""Bounded actual composition, independent arithmetic and unchanged authority."""
import copy
import csv
import hashlib
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

import pytest
from sqlalchemy import select, update
from test_column_patches import setup as source_setup
from test_controlled_branches import condition, proof
from test_csv_dag import NoModel, read_row, step_ids
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits

from sim2act import csv_dag as dag
from sim2act.csv_composition import Composition, compile_closed
from sim2act.db import Store, fingerprint, grants, operation_intents, operations, resources, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def composition(conditional=False):
    nodes = []
    for sid, column in [('a', 'amount'), ('b', 'quantity')]:
        node = dict(step_id=sid, action='data.aggregate_csv', column=column, depends_on=[],
            inputs=dict(resource_id=dict(source='data', ref='source', field='resource_id'),
                        column=dict(source='input', field=sid+'_column')))
        if conditional and sid == 'a':
            node['when'] = condition()
        nodes.append(node)
        nodes.append(dict(step_id=sid+'_report', action='intern.csv_report.v1', depends_on=[sid],
            inputs={field: dict(source='step', ref=sid, field=field) for field in ('resource_id','column','count','sum','source_hash')}))
    return dict(version='csv.composition.v1', nodes=nodes)


def setup(env, conditional=False, value=None):
    aid, rid, anchor, _, _ = source_setup(env)
    base = f'/api/projects/{env[5]}/apps/{aid}/csv-dag'
    body = dict(expected_candidate_fingerprint=anchor['candidate_fingerprint'],
        expected_graph_fingerprint=anchor['graph_fingerprint'], column='amount', request_key='composition',
        composition=value or composition(conditional))
    reply = env[2].post(base, json=body)
    assert reply.status_code == 201, reply.text
    return rid, base, reply.json(), body


def start(env, base, plan, key='composed-run', inputs=None):
    body = dict(expected_plan_fingerprint=plan['plan_fingerprint'], consent='CONFIRM_EXACT_OFFLINE_CSV_DAG', request_key=key)
    if inputs is not None:
        body['branch_inputs'] = inputs
    reply = env[2].post(base+'/'+plan['request_key']+'/runs', json=body)
    assert reply.status_code == 202, reply.text
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job['id'] == reply.json()['run_id']
    return worker, job, body


def oracle():
    with Path('tests/fixtures/column-binding.csv').open() as source:
        rows = list(csv.DictReader(source))
    return {field: sum((Fraction(r[field]) for r in rows), Fraction()) for field in ('amount','quantity')}


def test_four_actual_nodes_two_new_outputs_original_objects_unchanged(env):
    rid, base, plan, body = setup(env)
    before = snapshot(env)
    worker, job, confirmation = start(env, base, plan)
    worker.process(job)
    result = proof(env, job)
    assert result['status'] == 'SUCCEEDED'
    assert len(result['steps']) == 4 and step_ids(env, job) == {'a','b','a_report','b_report'}
    assert oracle() == {'amount': Fraction(30), 'quantity': Fraction(15)}
    for sid, column in [('a','amount'),('b','quantity')]:
        output = result['result']['output_by_step'][sid+'_report']
        assert Fraction(output['sum']) == oracle()[column] and output['column'] == column and output['count'] == 2
        assert output['resource_id'] == rid
        aggregate = next(r for r in result['steps'] if r['step_id'] == sid)
        report = next(r for r in result['steps'] if r['step_id'] == sid+'_report')
        assert report['predecessor_receipts'] == [fingerprint(aggregate)]
        assert report['actual_reads'] == []
        with env[0].engine.connect() as c:
            actual = c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id == aggregate['operation_id'])).scalar_one()
            assert actual['args'] == {'resource_id': rid, 'column': column}
            assert actual['input_sources'] == aggregate['input_sources']
    assert read_row(env, job)['context']['tools'] == 4
    assert result['model_requests'] == result['business_writes'] == 0
    assert result['owner_acceptance'] == 'PENDING' and result['publishable'] is False
    assert env[2].post(base, json=body).json()['cached']
    repeat = env[2].post(base+'/composition/runs', json=confirmation).json()
    assert repeat['cached'] and repeat['run_id'] == job['id']
    after = snapshot(env)
    for name in before:
        if name not in {'runs','run_contracts','events','operations','operation_intents','delivery_graph_requests'}:
            assert fingerprint(after[name]) == fingerprint(before[name]), name


@pytest.mark.parametrize('enabled', [False, True])
def test_branch_skip_does_not_block_independent_branch(env, enabled):
    _, base, plan, _ = setup(env, True)
    worker, job, _ = start(env, base, plan, inputs={'include_report': enabled})
    worker.process(job)
    saved = proof(env, job)
    assert saved['status'] == ('SUCCEEDED' if enabled else 'PARTIAL')
    assert saved['result']['output_status'] == ('PRODUCED' if enabled else 'PARTIAL')
    assert saved['result']['output_by_step']['b_report']['sum'] == '15'
    a = next(p for p in saved['steps'] if p['step_id'] == 'a')
    r = next(p for p in saved['steps'] if p['step_id'] == 'a_report')
    if enabled:
        assert a['status'] == r['status'] == 'VERIFIED'
    else:
        assert a['status'] == r['status'] == 'SKIPPED'
        assert a['branch_decision']['reason'] == 'CONDITION_FALSE'
        assert r['branch_decision']['reason'] == 'DEPENDENCY_SKIPPED'
        assert saved['result']['output_by_step']['a_report'] is None
    assert read_row(env, job)['context']['tools'] == (4 if enabled else 2)


@pytest.mark.parametrize('count', [1,2,3,4])
def test_cold_four_node_receipts_and_old_fence(env, count):
    _, base, plan, _ = setup(env)
    worker, job, body = start(env, base, plan)
    for _ in range(count):
        assert dag.advance(worker, job)
    with env[0].tx() as c:
        old = {r['call_id']: r['id'] for r in c.execute(select(operations).where(operations.c.run_id == job['id'])).mappings()}
        c.execute(update(runs).where(runs.c.id == job['id']).values(lease_until=0))
    cold = Store(env[1].database_url, test_only=True)
    cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        w = Worker(cold, env[1], NoModel())
        claimed = cold.claim(w.id, env[1].lease_seconds)
        assert claimed['fence'] > job['fence']
        with pytest.raises(DomainError):
            dag.advance(worker, job)
        w.process(claimed)
        assert dag.inspect_job(cold, env[3], job['id'], limits(env))['status'] == 'SUCCEEDED'
        assert dag.enqueue(cold, env[3], env[5], plan['app_id'], plan['request_key'], dag.RunInput(**body), limits(env))['cached']
        with cold.engine.connect() as c:
            new = {r['call_id']: r['id'] for r in c.execute(select(operations).where(operations.c.run_id == job['id'])).mappings()}
        assert len(new) == 4 and old.items() <= new.items()
    finally:
        cold.engine.dispose()


@pytest.mark.parametrize('attack', ['fifth','cycle','unknown','self','duplicate','port','semantic','column','mixed','action','source','when','code','legacy'])
def test_closed_schema_topology_rejection_writes_nothing(env, attack):
    _, base, _, body = setup(env)
    bad = copy.deepcopy(body)
    bad['request_key'] = 'reject'
    n = bad['composition']['nodes']
    if attack == 'fifth':
        n.append(copy.deepcopy(n[0]))
    elif attack == 'cycle':
        n[0]['depends_on'] = ['a_report']
    elif attack == 'unknown':
        n[0]['depends_on'] = ['missing']
    elif attack == 'self':
        n[0]['depends_on'] = ['a']
    elif attack == 'duplicate':
        n[2]['step_id'] = 'a'
    elif attack == 'port':
        n[0]['inputs']['extra'] = {'source':'input','field':'a_column'}
    elif attack == 'semantic':
        n[0]['inputs']['resource_id'] = {'source':'step','ref':'b','field':'sum'}
        n[0]['depends_on'] = ['b']
    elif attack == 'column':
        n[0]['inputs']['column']['field'] = 'b_column'
    elif attack == 'mixed':
        n[1]['inputs']['count']['ref'] = 'b'
        n[1]['depends_on'].append('b')
    elif attack == 'action':
        n[0]['action'] = 'artifact.save_text'
    elif attack == 'source':
        n[0]['inputs']['resource_id']['ref'] = 'another-resource'
    elif attack == 'when':
        n[0]['when'] = condition(source='step', ref='b', field='count', value=True)
        n[0]['depends_on'] = ['b']
    elif attack == 'code':
        n[0]['code'] = 'eval(1)'
    else:
        bad['branch_patch'] = [{'step_id':'report','when':condition()}]
    before = snapshot(env)
    reply = env[2].post(base, json=bad)
    assert reply.status_code in {400,409,422}, reply.text
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_four_node_conservative_budget_and_exact_confirmation(env):
    _, base, plan, _ = setup(env)
    candidate = env[2].get(f"/api/apps/{plan['app_id']}").json()['candidate']
    low = limits(env).model_copy(update={'max_tools':3})
    with pytest.raises(DomainError) as exc:
        compile_closed(candidate, Composition(**composition()), low, dag.READ_OUTPUT)
    assert exc.value.code == 'BUDGET_EXHAUSTED'
    before = snapshot(env)
    reply = env[2].post(base+'/composition/runs', json=dict(expected_plan_fingerprint='0'*64,
        consent='CONFIRM_EXACT_OFFLINE_CSV_DAG', request_key='wrong'))
    assert reply.status_code == 409 and fingerprint(snapshot(env)) == fingerprint(before)


@pytest.mark.parametrize('mode', ['pause','cancel','grant','source'])
def test_composition_controls_and_invalidation_keep_prefix(env, mode):
    rid, base, plan, _ = setup(env)
    worker, job, body = start(env, base, plan)
    assert dag.advance(worker, job)
    if mode in {'pause','cancel'}:
        reply = env[2].post(f"/api/runs/{job['id']}/commands", json=dict(command=mode,version=job['version']))
        assert reply.status_code == 200, reply.text
        worker.process(job)
        saved = proof(env, job)
        assert saved['status'] == ('PAUSED' if mode=='pause' else 'CANCELLED')
        assert len(saved['steps']) == 1
        if mode == 'pause':
            reply = env[2].post(f"/api/runs/{job['id']}/commands", json=dict(command='resume',version=saved['version']))
            assert reply.status_code == 200
            claimed = env[0].claim(worker.id, env[1].lease_seconds)
            worker.process(claimed)
            assert proof(env, job)['status'] == 'SUCCEEDED'
        return
    with env[0].tx() as c:
        if mode == 'grant':
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
        else:
            content = 'item,amount,quantity\nX,11,4\n'
            c.execute(update(resources).where(resources.c.id == rid).values(content=content,hash=hashlib.sha256(content.encode()).hexdigest()))
    worker.process(job)
    assert read_row(env, job)['status'] == 'WAITING_RESOURCE' and len(step_ids(env, job)) == 1
    assert env[2].get(f"/api/csv-dag/runs/{job['id']}").status_code in {403,409}
    assert env[2].post(base+'/composition/runs',json=body).status_code in {403,409}
    metadata = env[2].get(f"/api/csv-dag/runs/{job['id']}/status").json()
    assert metadata['proof_status']=='NOT_VALIDATED' and metadata['result'] is None and metadata['steps']==[]
    assert env[2].post(f"/api/runs/{job['id']}/commands",json=dict(command='cancel',version=metadata['version'])).status_code==200


@pytest.mark.parametrize('count', [1,2,3])
def test_editable_one_to_three_node_composition(env, count):
    nodes = [dict(step_id='read',action='resource.read',depends_on=[],inputs=dict(resource_id=dict(source='data',ref='source',field='resource_id')))]
    if count >= 2:
        nodes.append(dict(step_id='a',action='data.aggregate_csv',column='quantity',depends_on=['read'],
            inputs=dict(resource_id=dict(source='step',ref='read',field='resource_id'),column=dict(source='input',field='a_column'))))
    if count == 3:
        nodes.append(composition()['nodes'][1])
    _, base, plan, _ = setup(env,value=dict(version='csv.composition.v1',nodes=nodes))
    worker, job, _ = start(env,base,plan)
    worker.process(job)
    saved = proof(env,job)
    assert saved['status']=='SUCCEEDED' and len(saved['steps'])==count


def test_concurrent_repeat_is_one_acceptance_and_four_operations(env):
    _, _, plan, _ = setup(env)
    body=dag.RunInput(expected_plan_fingerprint=plan['plan_fingerprint'],consent='CONFIRM_EXACT_OFFLINE_CSV_DAG',request_key='race')
    def enqueue(_):
        return dag.enqueue(env[0],env[3],env[5],plan['app_id'],plan['request_key'],body,limits(env))
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers=list(pool.map(enqueue,range(2)))
    assert len({a['run_id'] for a in answers})==1 and sum(a['cached'] for a in answers)==1
    worker=Worker(env[0],env[1],NoModel())
    job=env[0].claim(worker.id,env[1].lease_seconds)
    worker.process(job)
    assert proof(env,job)['status']=='SUCCEEDED' and len(step_ids(env,job))==4


@pytest.mark.parametrize('enabled', [False, True])
def test_actual_pg_crud_role_four_node_composition(env, runtime_role, enabled):
    from dataclasses import replace

    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    _, _, source, body = setup(env, True)
    body['request_key'] = 'role-composition'
    before = snapshot(env)
    store = Store(runtime_role, test_only=True)
    try:
        plan = dag.propose(store,env[3],env[5],source['app_id'],dag.PlanInput(**body),limits(env))
        confirmation = dag.RunInput(expected_plan_fingerprint=plan['plan_fingerprint'],consent='CONFIRM_EXACT_OFFLINE_CSV_DAG',request_key='role-run',branch_inputs={'include_report':enabled})
        accepted = dag.enqueue(store,env[3],env[5],plan['app_id'],plan['request_key'],confirmation,limits(env))
        settings = replace(env[1],database_url=runtime_role)
        worker = Worker(store,settings,NoModel())
        job = store.claim(worker.id,settings.lease_seconds)
        assert job['id']==accepted['run_id']
        assert dag.advance(worker,job)
        cold = Store(runtime_role,test_only=True)
        try:
            Worker(cold,settings,NoModel()).process(job)
            saved = dag.inspect_job(cold,env[3],job['id'],limits(env))
            assert saved['status']==('SUCCEEDED' if enabled else 'PARTIAL')
            assert saved['result']['output_by_step']['b_report']['sum']=='15'
            assert dag.enqueue(cold,env[3],env[5],plan['app_id'],plan['request_key'],confirmation,limits(env))['cached']
        finally:
            cold.engine.dispose()
        with store.engine.connect() as c:
            assert c.execute(text('select rolsuper from pg_roles where rolname=current_user')).scalar() is False
        with pytest.raises(ProgrammingError),store.tx() as c:
            c.execute(text('CREATE TABLE forbidden_composition_ddl (id integer)'))
        after=snapshot(env)
        for name in ['grants','principals','app_drafts','resources']:
            assert fingerprint(after[name])==fingerprint(before[name]),name
    finally:
        store.engine.dispose()


@pytest.mark.parametrize('kind', ['input','receipt','missing','status','counter','acceptance'])
def test_four_node_persisted_proof_tamper_is_never_certified(env, kind):
    from sim2act.db import events

    _, base, plan, _ = setup(env)
    worker, job, _ = start(env,base,plan)
    worker.process(job)
    assert proof(env,job)['status']=='SUCCEEDED'
    with env[0].tx() as c:
        ops=c.execute(select(operations).where(operations.c.run_id==job['id'])).mappings().all()
        op=next(o for o in ops if o['call_id']=='b')
        if kind=='input':
            saved=c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id==op['id'])).scalar_one()
            saved['args']['column']='amount'
            c.execute(update(operation_intents).where(operation_intents.c.operation_id==op['id']).values(request=saved))
        elif kind=='receipt':
            value=copy.deepcopy(op['receipt'])
            value['data']['count']=True
            c.execute(update(operations).where(operations.c.id==op['id']).values(receipt=value))
        elif kind=='missing':
            c.execute(operations.delete().where(operations.c.id==op['id']))
        elif kind=='status':
            c.execute(update(runs).where(runs.c.id==job['id']).values(status='PARTIAL'))
        elif kind=='counter':
            context=read_row(env,job)['context']
            c.execute(update(runs).where(runs.c.id==job['id']).values(context={**context,'tools':3}))
        else:
            c.execute(update(events).where(events.c.run_id==job['id'],events.c.kind=='CSV_DAG_ACCEPTED').values(data={'invalid':True}))
    reply=env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert reply.status_code in {400,409},reply.text


def test_composition_same_key_different_unused_legacy_column_rejected(env):
    _,base,_,body=setup(env)
    before=snapshot(env)
    body['column']='quantity'
    reply=env[2].post(base,json=body)
    assert reply.status_code==409 and fingerprint(snapshot(env))==fingerprint(before)


@pytest.mark.parametrize('column', ['missing','item'])
def test_composition_rejects_absent_or_non_numeric_columns_before_save(env, column):
    _,base,_,body=setup(env)
    body['request_key']='wrong-column'
    body['composition']['nodes'][0]['column']=column
    before=snapshot(env)
    reply=env[2].post(base,json=body)
    assert reply.status_code==400 and fingerprint(snapshot(env))==fingerprint(before)


def test_input_node_order_is_compiled_topologically(env):
    value=composition()
    value['nodes'].reverse()
    _,base,plan,_=setup(env,value=value)
    assert plan['preflight']['topological_order']==['b','a','b_report','a_report']
    worker,job,_=start(env,base,plan)
    worker.process(job)
    saved=proof(env,job)
    assert saved['status']=='SUCCEEDED'
    assert {key:data['sum'] for key,data in saved['result']['output_by_step'].items()}=={'a_report':'30','b_report':'15'}
