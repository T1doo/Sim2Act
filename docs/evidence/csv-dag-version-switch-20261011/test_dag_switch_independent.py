import copy
import pytest
from sqlalchemy import update,select
from sim2act.db import internal_instances, internal_approvals, internal_releases, fingerprint, runs
from sim2act import csv_dag as dag
from sim2act.errors import DomainError
from test_csv_dag_instances import release,create,enqueue,work
from test_csv_dag_version_switch import next_release,prepare,switch
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
pytest_plugins=['conftest']

@pytest.mark.parametrize('history',[None,[],[None],['created'],[[]],[{'revision':True,'release_id':'CURRENT','kind':'created'}],[{'revision':1.0,'release_id':'CURRENT','kind':'created'}]])
def test_malformed_history_rejected_without_server_exception(env,history):
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    i=create(env,old)
    if isinstance(history,list) and history and isinstance(history[0],dict):history[0]['release_id']=old['id']
    with env[0].tx() as c:
        c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(history=history))
    frozen=fingerprint(snapshot(env))
    response=prepare(env,i,target)
    assert response.status_code==409,response.text
    assert fingerprint(snapshot(env))==frozen

@pytest.mark.parametrize('attack',['later-none','later-string','unconsumed','payload-revision','target-fingerprint','approval-owner','payload-null','later-bool','later-float'])
def test_switched_history_corruption_rejected(env,attack):
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    i=create(env,old)
    first,_=enqueue(env,i,old)
    work(env,first)
    i,a=switch(env,i,target)
    with env[0].tx() as c:
        if attack.startswith('later-'):
            h=copy.deepcopy(i['history'])
            if attack in ['later-none','later-string']:h[1]=None if attack=='later-none' else 'switch'
            else:h[1]['revision']=True if attack=='later-bool' else 2.0
            c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(history=h))
        elif attack=='unconsumed':
            c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(consumed=False))
        elif attack=='payload-null':
            c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(payload=None,fingerprint=fingerprint(None)))
        elif attack=='approval-owner':
            c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(principal_id=env[4]))
        else:
            p=copy.deepcopy(c.execute(select(internal_approvals.c.payload).where(internal_approvals.c.id==a['id'])).scalar_one())
            if attack=='payload-revision':p['revision']=2
            else:p['target_fingerprint']='0'*64
            c.execute(update(internal_approvals).where(internal_approvals.c.id==a['id']).values(payload=p,fingerprint=fingerprint(p)))
    frozen=fingerprint(snapshot(env))
    response=env[2].get(f"/api/internal/instances/{i['id']}/runs/{first['run_id']}")
    assert response.status_code==409,response.text
    assert prepare(env,i,old).status_code==409
    assert fingerprint(snapshot(env))==frozen

@pytest.mark.parametrize('state',['QUEUED','RUNNING','PAUSED','WAITING_RESOURCE','PAUSE_REQUESTED','PARTIAL','OUTCOME_UNKNOWN'])
def test_all_nonterminal_states_block_switch(env,state):
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    i=create(env,old)
    first,_=enqueue(env,i,old)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id==first['run_id']).values(status=state))
    frozen=fingerprint(snapshot(env))
    assert prepare(env,i,target).status_code==409
    assert fingerprint(snapshot(env))==frozen

def test_aba_stale_revision_cannot_execute_or_commit(env):
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    i=create(env,old)
    first,_=enqueue(env,i,old)
    work(env,first)
    stale=prepare(env,i,target).json()
    i,_=switch(env,i,target)
    i,_=switch(env,i,old)
    frozen=fingerprint(snapshot(env))
    with env[0].tx() as c:
        job=dag.row(c,env[3],first['run_id'])
        with pytest.raises(DomainError):dag.binding(env[0],c,job,limits(env),authorize=False)
        assert dag.binding(env[0],c,job,limits(env),authorize=False,historical=True)
    response=env[2].post(f"/api/internal/instances/{i['id']}/switch-approvals/{stale['id']}/commit",json={'fingerprint':stale['fingerprint']})
    assert response.status_code==409
    assert fingerprint(snapshot(env))==frozen

def test_cross_instance_approval_cannot_be_committed(env):
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    a,b=create(env,old),create(env,old,'other')
    approval=prepare(env,a,target).json()
    frozen=fingerprint(snapshot(env))
    reply=env[2].post(f"/api/internal/instances/{b['id']}/switch-approvals/{approval['id']}/commit",json={'fingerprint':approval['fingerprint']})
    assert reply.status_code==403,reply.text
    assert fingerprint(snapshot(env))==frozen

@pytest.mark.parametrize('scope',['project','app','runtime'])
def test_cross_scope_target_rejected_at_switch_policy(env,scope):
    from sim2act import lifecycle
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    i=create(env,old)
    forged=copy.deepcopy(target)
    if scope=='project':forged['project_id']='proj_'+'0'*32
    elif scope=='app':forged['snapshot']['draft']['id']='app_'+'0'*32
    else:forged['snapshot']['draft']['runtime_id']='runtime_'+'0'*32
    frozen=fingerprint(snapshot(env))
    with env[0].tx() as c:
        with pytest.raises(DomainError) as rejected:
            lifecycle.switch_target(env[0],c,env[3],i,old,forged,limits(env))
        assert rejected.value.code=='PERMISSION_DENIED'
    assert fingerprint(snapshot(env))==frozen

def test_foreign_owner_cannot_read_prepare_or_commit(env):
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    i=create(env,old)
    a=prepare(env,i,target).json()
    env[2].headers.update({'Authorization':'Bearer synthetic-test-B'})
    frozen=fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/instances/{i['id']}").status_code==403
    assert prepare(env,i,target).status_code==403
    assert env[2].post(f"/api/internal/instances/{i['id']}/switch-approvals/{a['id']}/commit",json={'fingerprint':a['fingerprint']}).status_code==403
    assert fingerprint(snapshot(env))==frozen

def test_jointly_resealed_typed_ledger_and_app_output_rejected_by_actual_receipt(env):
    from sim2act.db import internal_instance_data,internal_app_runs
    aid,_,plan,_,old=release(env)
    target=next_release(env,aid,plan)
    i=create(env,old)
    first,_=enqueue(env,i,old)
    work(env,first)
    with env[0].tx() as c:
        record=c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==i['id'])).mappings().one()
        value=copy.deepcopy(record['data']);value['result']['sum']='999'
        c.execute(update(internal_instance_data).where(internal_instance_data.c.instance_id==i['id']).values(data=value,fingerprint=fingerprint(value)))
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id==record['run_id']).values(output=value['result']))
    frozen=fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/instances/{i['id']}/runs/{first['run_id']}").status_code==409
    assert prepare(env,i,target).status_code==409
    assert fingerprint(snapshot(env))==frozen
