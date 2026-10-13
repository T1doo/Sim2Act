"""Actual two-model Worker checks, original version preserved; synthetic transport."""
import copy
import json

import pytest
from sqlalchemy import select
from test_natural_spec_apps import ready, setup, transport
from test_pa_spec_apps import enqueue, inspect
from test_pb_natural_specs import drive_to_success

from sim2act import natural_logic_patches as logic
from sim2act.db import internal_instances, internal_releases
from sim2act.worker import Worker


def prepared(env,style='parallel'):
    data=setup(env)
    _,aid,release,inst,_=ready(data,style)
    client=data[2]
    app=client.get('/api/apps/'+aid).json()
    r=client.post(f'/api/projects/{data[4]}/apps/{aid}/delivery-graph/derive',json=dict(
        request_key='logic-baseline',expected_candidate_fingerprint=app['fingerprint']))
    assert r.status_code==201,r.text
    graph=r.json()
    body=dict(request_key='logic-edit',expected_revision=inst['revision'],
        expected_release_fingerprint=release['fingerprint'],expected_graph_fingerprint=graph['graph_fingerprint'],
        consume_prior_feedback=style=='parallel')
    path=f"/api/internal/instances/{inst['id']}/logic-patches"
    r=client.post(path+'/previews',json=body)
    assert r.status_code==201,r.text
    return data,aid,release,inst,graph,path,body,r.json()


def start(data,path,value):
    r=data[2].post(path+'/checks',json=dict(request_key='logic-edit',
        expected_preview_fingerprint=value['preview_fingerprint'],consent=logic.CHECK_CONSENT))
    assert r.status_code==202,r.text
    return r.json()


@pytest.mark.parametrize('style',['parallel','sequential'])
def test_actual_logic_check_then_separate_internal_version(env,style):
    data,aid,release,inst,graph,path,body,value=prepared(env,style)
    assert value['impact']['revalidation_scope']=='APP'
    assert len(value['preserved_action_definitions'])==5
    assert value['effective_candidate']['actions'][2]['revision']==2
    assert [a['action_id'] for a in value['effective_candidate']['actions']]==[
        a['action_id'] for a in release['snapshot']['draft']['candidate']['actions']]
    original=copy.deepcopy(release)
    started=start(data,path,value)
    assert data[2].get(path+'/checks/logic-edit').json()['check_status']=='NOT_PASSED'
    sent=[]
    drive_to_success(data,started['run_id'],transport(sent))
    r=data[2].get(path+'/checks/logic-edit')
    assert r.status_code==200,r.text
    proof=r.json()
    assert proof['status']=='PASS' and proof['semantic_status']=='UNKNOWN'
    assert len(sent)==2
    actual=json.loads(sent[1]['messages'][1]['content'])['current_inputs']
    assert ('prior_items' in actual)==body['consume_prior_feedback']
    with data[0].tx() as c:
        preserved=c.execute(select(internal_instances).where(internal_instances.c.id==inst['id'])).mappings().one()
        assert preserved['data_version']==0 and preserved['revision']==inst['revision']
        assert c.execute(select(internal_releases.c.id)).scalars().all()==[release['id']]
    version_body=dict(request_key='logic-edit',expected_check_fingerprint=proof['check_fingerprint'],consent=logic.VERSION_CONSENT)
    r=data[2].post(path+'/version-approvals',json=version_body)
    assert r.status_code==201,r.text
    approval=r.json()
    assert data[2].get(path+'/version-approvals/logic-edit').json()==approval
    r=data[2].post(f"/api/internal/approvals/{approval['id']}/commit",json=dict(fingerprint=approval['fingerprint']))
    assert r.status_code==200,r.text
    version=r.json()
    assert version['snapshot']['draft']==release['snapshot']['draft']
    assert version['snapshot']['natural_logic_source']['check_fingerprint']==proof['check_fingerprint']
    assert data[2].get(f"/api/internal/releases/{release['id']}").json()==original
    r=data[2].post(f"/api/internal/releases/{version['id']}/instances",json=dict(
        expected_release_fingerprint=version['fingerprint'],request_key='logic-new-version'))
    assert r.status_code==201,r.text
    newinst=r.json()
    jid=enqueue(data,version,newinst,key='new-logic-actual')
    new_sent=[]
    drive_to_success(data,jid,transport(new_sent))
    r=inspect(data,newinst,jid)
    assert r.status_code==200,r.text
    assert r.json()['status']=='SUCCEEDED',r.text
    assert ('prior_items' in json.loads(new_sent[1]['messages'][1]['content'])['current_inputs'])==body['consume_prior_feedback']
    assert data[2].get('/api/apps/'+aid).json()['fingerprint']==release['snapshot']['draft']['fingerprint']


@pytest.mark.parametrize('fault',['cancel','revoke','goal','instance_version','lock'])
def test_inflight_invalidations_keep_original_and_no_checked_version(env,fault):
    from sqlalchemy import update

    from sim2act.db import goal_cards, grants, internal_instance_data, runs
    data,aid,release,inst,graph,path,body,value=prepared(env)
    started=start(data,path,value)
    sent=[]
    def mutate(raw,payload):
        if fault=='lock':
            node=next(n for n in graph['graph']['nodes'] if n['key']=='action:qualifiers_pick')
            r=data[2].post(f'/api/projects/{data[4]}/apps/{aid}/delivery-graph/manual-locks',json=dict(
                expected_graph_fingerprint=graph['graph_fingerprint'],expected_graph_revision=graph['graph_revision'],
                change=dict(node_id=node['id'],expected_revision=node['revision'],expected_content_fingerprint=node['content_fingerprint']),
                expected_lock_revision=0,locked=True,request_key='inflight-lock',consent='CONFIRM_EXACT_PROJECT_EDIT_LOCK'))
            assert r.status_code==201,r.text
        else:
            with data[0].tx() as c:
                if fault=='cancel':
                    c.execute(update(runs).where(runs.c.id==started['run_id']).values(cancel_intent=True))
                elif fault=='revoke':
                    c.execute(update(grants).where(grants.c.resource_id==data[5]).values(revoked=True))
                elif fault=='goal':
                    c.execute(update(goal_cards).where(goal_cards.c.id==data[6]['id']).values(version=2))
                else:
                    c.execute(update(internal_instances).where(internal_instances.c.id==inst['id']).values(revision=2))
    worker=Worker(data[0],data[1],goal_planner_transport=transport(sent,mutate=mutate))
    assert worker.once()
    assert len(sent)==1
    with data[0].tx() as c:
        state=c.execute(select(runs.c.status).where(runs.c.id==started['run_id'])).scalar()
        assert state in {'FAILED','WAITING_RESOURCE','CANCELLED'},state
        assert not c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id.in_([inst['id'],started['check_instance_id']]))).first()
        assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id==inst['id'])).scalar()==0
        assert c.execute(select(internal_releases.c.id)).scalars().all()==[release['id']]
    r=data[2].post(path+'/version-approvals',json=dict(request_key='logic-edit',expected_check_fingerprint='0'*64,consent=logic.VERSION_CONSENT))
    assert r.status_code in {400,403,409}


def test_natural_lock_unknown_expands_and_preserves_exact_lock(env):
    from sim2act.db import delivery_graph_locks, fingerprint
    data,aid,release,inst,graph,path,body,value=prepared(env)
    node=next(n for n in graph['graph']['nodes'] if n['key']=='action:read_pick')
    r=data[2].post(f'/api/projects/{data[4]}/apps/{aid}/delivery-graph/manual-locks',json=dict(
        expected_graph_fingerprint=graph['graph_fingerprint'],expected_graph_revision=graph['graph_revision'],
        change=dict(node_id=node['id'],expected_revision=node['revision'],expected_content_fingerprint=node['content_fingerprint']),
        expected_lock_revision=0,locked=True,request_key='read-lock',consent='CONFIRM_EXACT_PROJECT_EDIT_LOCK'))
    assert r.status_code==201,r.text
    derived=data[2].post(f'/api/projects/{data[4]}/apps/{aid}/delivery-graph/derive',json=dict(
        request_key='locked-graph',expected_candidate_fingerprint=release['snapshot']['draft']['fingerprint']))
    assert derived.status_code==201,derived.text
    with data[0].tx() as c:
        before=fingerprint([dict(r) for r in c.execute(select(delivery_graph_locks)).mappings()])
    denied=data[2].post(path+'/previews',json={**body,'request_key':'locked-edit','expected_graph_fingerprint':derived.json()['graph_fingerprint']})
    assert denied.status_code==400 and denied.json()['error']['code']=='LOCK_CONFLICT',denied.text
    assert denied.json()['error']['submission_rejection']['acceptance']=='NOT_ACCEPTED'
    with data[0].tx() as c:
        assert before==fingerprint([dict(r) for r in c.execute(select(delivery_graph_locks)).mappings()])
        assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id==inst['id'])).scalar()==0


def test_preview_key_conflict_exact_recovery_and_distinct_consents(env):
    data,aid,release,inst,graph,path,body,value=prepared(env)
    assert data[2].get(path+'/previews/logic-edit').json()==value
    assert data[2].post(path+'/previews',json=body).json()==value
    r=data[2].post(path+'/previews',json={**body,'consume_prior_feedback':False})
    assert r.status_code==409,r.text
    assert data[2].post(path+'/checks',json=dict(request_key='logic-edit',expected_preview_fingerprint=value['preview_fingerprint'],consent=logic.VERSION_CONSENT)).status_code==422
    assert data[2].post(path+'/version-approvals',json=dict(request_key='logic-edit',expected_check_fingerprint='0'*64,consent=logic.CHECK_CONSENT)).status_code==422
    with data[0].tx() as c:
        assert c.execute(select(internal_releases.c.id)).scalars().all()==[release['id']]
        assert c.execute(select(internal_instances.c.id)).scalars().all()==[inst['id']]
