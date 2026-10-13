"""Synthetic human reasons, actual saved history and bounded normal Worker."""
import copy
import json

import pytest
from sqlalchemy import select, update
from test_natural_spec_apps import transport
from test_natural_spec_owner_acceptance import decision, flow, preview, state
from test_pb_natural_specs import drive_to_success
from test_spec_app_operations import snapshot

from sim2act import natural_spec_corrections as correction
from sim2act.db import fingerprint, grants, internal_app_runs, internal_instance_data, natural_owner_records, runs


def rejected(env,family='pa'):
    data,inst,rid,resource,goal,content,path=flow(env,family)
    p,_=preview(data,path)
    body=decision(p,True)
    body['choices'][0]['reason']='SIMULATED: reconsider exception linkage; keep all original standards'
    r=data[2].post(path+'-requests',json=body)
    assert r.status_code==201,r.text
    s=state(data,path)
    review_body=dict(request_key='explicit-correction',expected_owner_sequence=s['sequence'],
        declaration_id=s['latest']['id'],declaration_fingerprint=s['latest']['fingerprint'],
        expected_context_fingerprint=fingerprint(s['current']))
    base=path.replace('/spec-owner-review','')
    return data,inst,rid,resource,goal,content,path,base,review_body


def prepare_correction(data,base,body):
    r=data[2].post(base+'/correction-reviews',json=body)
    assert r.status_code==200,r.text
    value=r.json()
    commit=dict(request_key=body['request_key'],expected_review_fingerprint=value['review_fingerprint'],consent=correction.CONSENT)
    return value,commit


@pytest.mark.parametrize('family',['pa','pb'])
def test_explicit_rejection_to_actual_new_result_and_fresh_owner(env,tmp_path,family):
    data,inst,parent,resource,goal,content,path,base,body=rejected(env,family)
    old=snapshot(data[0])
    review,commit=prepare_correction(data,base,body)
    before_queue=snapshot(data[0])
    r=data[2].post(base+'/correction-runs',json=commit)
    assert r.status_code==202,r.text
    child=r.json()['run_id']
    queued=snapshot(data[0])
    assert queued['grants']==before_queue['grants']
    for table in ['app_drafts','internal_releases','goal_cards','goal_card_versions','natural_owner_records','natural_owner_seals','internal_instance_data']:
        assert queued[table]==before_queue[table]
    sent=[]
    def mutate(raw,payload):
        value=json.loads(raw['choices'][0]['message']['content'])
        value['items'][0]['summary']='SIMULATED revised wording with the same exact cited evidence'
        raw['choices'][0]['message']['content']=json.dumps(value)
    drive_to_success(data,child,transport(sent,content,mutate))
    assert sent
    correction_input=json.loads(sent[0]['messages'][1]['content'])['human_correction']
    assert correction_input['reference']['parent_run_id']==parent
    assert correction_input['original_goal']==goal['content']
    assert correction_input['original_criteria']==review['context']['items']
    assert 'SIMULATED: reconsider' in correction_input['issues'][0]['reason']
    recovered=data[2].get(base+'/correction-requests/'+body['request_key'])
    assert recovered.status_code==200,recovered.text
    receipt=recovered.json()
    assert receipt['run_id']==child and receipt['result_version']==2 and receipt['owner_acceptance']=='PENDING'
    after=snapshot(data[0])
    for table in ['internal_instance_data','natural_owner_records','natural_owner_seals']:
        assert all(x in after[table] for x in old[table])
    oldrun=next(x for x in old['internal_app_runs'] if x['id']==review['context']['app_run_id'])
    assert oldrun in after['internal_app_runs']
    assert data[2].post(base+'/correction-runs',json=commit).json()['cached'] is True
    newpath=path.replace(parent,child)
    s=state(data,newpath)
    assert s['owner_acceptance']=='PENDING' and s['sequence']==0
    assert s['current']['goal']==review['context']['goal'] and s['current']['items']==review['context']['items']
    assert s['current']['human_correction']['issues']==correction_input['issues']
    p,_=preview(data,newpath,'new-independent-owner')
    assert data[2].post(newpath+'-requests',json=decision(p)).status_code==201
    assert state(data,newpath)['owner_acceptance']=='ACCEPTED'
    assert data[2].get(f'/api/internal/app-run-jobs/{child}/spec-artifact').json()['owner_acceptance']=='PENDING'
    (tmp_path/'proof.json').write_text(json.dumps(dict(review=review,receipt=receipt,new_owner=state(data,newpath),wire=sent),ensure_ascii=False,indent=2))


@pytest.mark.parametrize('fault',['revoke','goal','expired','wrong-fp','withdraw'])
def test_preconfirm_invalid_source_no_partial_run(env,fault):
    from sim2act.db import goal_cards
    from unittest.mock import patch
    data,inst,parent,resource,goal,_,path,base,body=rejected(env)
    review,commit=prepare_correction(data,base,body)
    if fault=='wrong-fp':commit['expected_review_fingerprint']='0'*64
    if fault=='withdraw':
        s=state(data,path);r=data[2].post(path+'-requests',json=dict(command='REVOKE',request_key='withdraw',expected_sequence=2,
            target_id=s['latest']['id'],target_fingerprint=s['latest']['fingerprint'],reason='Withdraw rejected declaration'))
        assert r.status_code==201
    if fault in ['revoke','goal']:
        with data[0].tx() as c:
            if fault=='revoke':c.execute(update(grants).where(grants.c.resource_id==resource).values(revoked=True))
            else:c.execute(update(goal_cards).where(goal_cards.c.id==goal['id']).values(version=goal['version']+1))
    before=snapshot(data[0])
    if fault=='expired':
        with patch.object(correction.time,'time',return_value=review['expires_at']+1):
            response=data[2].post(base+'/correction-runs',json=commit)
    else:response=data[2].post(base+'/correction-runs',json=commit)
    assert response.status_code in [403,409],response.text
    assert snapshot(data[0])==before
    assert response.json()['error']['submission_rejection']['previous_request']=='ABSENT'


def test_withdraw_after_queue_prevents_worker_result(env):
    from sim2act.worker import Worker
    data,inst,parent,_,_,content,path,base,body=rejected(env)
    _,commit=prepare_correction(data,base,body)
    r=data[2].post(base+'/correction-runs',json=commit);assert r.status_code==202,r.text
    child=r.json()['run_id'];s=state(data,path)
    assert s['owner_acceptance']=='STALE'
    latest=s['latest']
    assert data[2].post(path+'-requests',json=dict(command='REVOKE',request_key='withdraw-after-queue',expected_sequence=2,
        target_id=latest['id'],target_fingerprint=latest['fingerprint'],reason='Explicitly withdraw this correction basis')).status_code==201
    sent=[];assert not Worker(data[0],data[1],goal_planner_transport=transport(sent,content)).once()
    assert not sent
    with data[0].tx() as c:
        status=c.execute(select(runs.c.status).where(runs.c.id==child)).scalar()
        assert status=='FAILED'
        assert len(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==inst['id'])).all())==1


def test_duplicate_consent_keys_and_cancel_control(env):
    data,_,parent,_,_,_,_,base,body=rejected(env)
    _,commit=prepare_correction(data,base,body)
    assert data[2].post(base+'/correction-runs',json={**commit,'consent':'AUTO'}).status_code==422
    r=data[2].post(base+'/correction-runs',json=commit);assert r.status_code==202,r.text
    child=r.json()['run_id']
    assert data[2].post(base+'/correction-runs',json=commit).json()['run_id']==child
    wrong={**commit,'expected_review_fingerprint':'0'*64}
    assert data[2].post(base+'/correction-runs',json=wrong).status_code==409


@pytest.mark.parametrize('fault',['binding','attempt','receipt'])
def test_original_worker_proof_pollution_stops_correction(env,fault):
    from sim2act.db import attempts, internal_run_bindings, operations
    from sim2act.worker import Worker
    data,inst,parent,_,_,content,_,base,body=rejected(env)
    _,commit=prepare_correction(data,base,body)
    r=data[2].post(base+'/correction-runs',json=commit);assert r.status_code==202,r.text
    child=r.json()['run_id']
    with data[0].tx() as c:
        if fault=='binding':
            old=c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id==parent)).scalar_one()
            c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id==parent).values(snapshot={**old,'limits':{**old['limits'],'run_seconds':old['limits']['run_seconds']+1}}))
        elif fault=='attempt':
            row=c.execute(select(attempts).where(attempts.c.run_id==parent)).mappings().first()
            c.execute(update(attempts).where(attempts.c.id==row['id']).values(response={**row['response'],'polluted':True}))
        else:
            row=c.execute(select(operations).where(operations.c.run_id==parent)).mappings().first()
            c.execute(update(operations).where(operations.c.id==row['id']).values(receipt={**row['receipt'],'polluted':True}))
    sent=[];assert not Worker(data[0],data[1],goal_planner_transport=transport(sent,content)).once()
    assert not sent
    with data[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id==child)).scalar_one()=='FAILED'
        assert len(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==inst['id'])).all())==1


def test_late_model_reply_after_declaration_withdrawal_cannot_commit(env):
    from sim2act.worker import Worker
    data,inst,parent,_,_,content,path,base,body=rejected(env)
    _,commit=prepare_correction(data,base,body)
    r=data[2].post(base+'/correction-runs',json=commit);assert r.status_code==202,r.text
    child=r.json()['run_id'];sent=[];withdrawn=[]
    def withdraw(raw,payload):
        if withdrawn:return
        response=data[2].post(path+'-requests',json=dict(command='REVOKE',request_key='during-model-reply',expected_sequence=2,
            target_id=body['declaration_id'],target_fingerprint=body['declaration_fingerprint'],reason='Withdraw before model reply commits'))
        assert response.status_code==201,response.text
        withdrawn.append(response.json())
    Worker(data[0],data[1],goal_planner_transport=transport(sent,content,withdraw)).once()
    assert sent and withdrawn
    with data[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id==child)).scalar_one()!='SUCCEEDED'
        assert len(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==inst['id'])).all())==1


def test_cancelled_correction_keeps_original_result(env):
    from sim2act.worker import Worker
    data,inst,_,_,_,content,_,base,body=rejected(env)
    _,commit=prepare_correction(data,base,body)
    r=data[2].post(base+'/correction-runs',json=commit);assert r.status_code==202,r.text
    child=r.json()['run_id'];route=f"/api/internal/instances/{inst['id']}/runs/{child}"
    current=data[2].get(route+'/control-status');assert current.status_code==200,current.text
    stop=data[2].post(route+'/commands',json=dict(command='cancel',version=current.json()['version']))
    assert stop.status_code==200,stop.text
    sent=[];Worker(data[0],data[1],goal_planner_transport=transport(sent,content)).once()
    assert not sent
    with data[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id==child)).scalar_one()=='CANCELLED'
        assert len(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==inst['id'])).all())==1
