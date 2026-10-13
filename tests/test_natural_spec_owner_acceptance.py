"""Actual Worker/HTTP; choices are simulated, never real semantic acceptance."""
import copy
import json
import time

import pytest
from sqlalchemy import select, update
from test_natural_spec_apps import SOURCE, enqueue, ready, setup, transport
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD, prepared_use
from test_spec_app_operations import snapshot as all_rows

from sim2act import pb_natural_uses as use
from sim2act.db import fingerprint, grants, internal_run_bindings, natural_owner_records, natural_owner_seals
from sim2act.owner_acceptance import NATURAL_VERSION


def snapshot(store):
    return {k:v for k,v in all_rows(store).items() if k not in {"natural_owner_records","natural_owner_seals"}}


def flow(env, family='pa'):
    if family == 'pa':
        data = setup(env)
        _, _, release, inst, _ = ready(data)
        rid = enqueue(data, release, inst)
        drive_to_success(data, rid, transport([]))
        resource, goal, content = data[5], data[6], SOURCE
    else:
        data, _, release, inst, resource, goal, body, route = prepared_use(env)
        checked = data[2].post(route+'/pb-use-reviews', json=body)
        assert checked.status_code == 200, checked.text
        queued = data[2].post(route+'/pb-use-runs', json=dict(review=body,
            expected_review_fingerprint=checked.json()['review_fingerprint'], consent=use.CONSENT))
        assert queued.status_code == 202, queued.text
        rid = queued.json()['run_id']
        drive_to_success(data, rid, transport([], THIRD))
        content = THIRD
    path = f"/api/internal/instances/{inst['id']}/runs/{rid}/spec-owner-review"
    return data, inst, rid, resource, goal, content, path


def state(data, path, key=None):
    r = data[2].get(path, params={'request_key':key} if key else {})
    assert r.status_code == 200, r.text
    return r.json()


def preview(data, path, key='prepare'):
    s = state(data, path)
    assert s['content_access'], s
    body = dict(command='PREPARE', request_key=key, expected_sequence=s['sequence'],
        expected_contract_fingerprint=fingerprint(s['current']))
    r = data[2].post(path+'-requests', json=body)
    assert r.status_code == 201, r.text
    return state(data,path,key)['recovered'], body


def decision(review, reject=False):
    return dict(command='DECIDE', request_key='decision', expected_sequence=review['sequence'],
        review_id=review['id'], review_fingerprint=review['fingerprint'], choices=[
            dict(item_id=i['id'], decision='REJECT' if reject and n==0 else 'ACCEPT',
                reason='SIMULATED human declaration; not real semantic signoff')
            for n,i in enumerate(review['payload']['contract']['items'])])


@pytest.mark.parametrize('family', ['pa','pb'])
@pytest.mark.parametrize('reject', [False,True])
def test_exact_goal_result_explicit_human_declaration(env,tmp_path,family,reject):
    data, inst, rid, resource, goal, content, path = flow(env,family)
    before = snapshot(data[0])
    review, prepared = preview(data,path)
    frozen = review['payload']['contract']
    assert frozen['version']==NATURAL_VERSION and frozen['run_id']==rid
    assert frozen['source_goal']['card_id']==goal['id'] and frozen['goal']==goal['content']
    assert frozen['material']['resource_id']==resource
    assert frozen['output']['checklist']['source_content']==content
    assert {i['kind'] for i in frozen['output']['checklist']['items']}=={'requirement','condition','exception','open_question'}
    body = decision(review,reject)
    r = data[2].post(path+'-requests',json=body)
    assert r.status_code==201,r.text
    accepted=state(data,path,'decision')
    assert accepted['owner_acceptance']==('REJECTED' if reject else 'ACCEPTED')
    assert accepted['technical_semantic_status']=='UNKNOWN' and not accepted['formal_publication_enabled']
    assert snapshot(data[0])==before
    assert data[2].post(path+'-requests',json=body).json()['record']==r.json()['record']
    changed=copy.deepcopy(body);changed['choices'][0]['reason']='different intent'
    assert data[2].post(path+'-requests',json=changed).status_code==409
    artifact=data[2].get(f'/api/internal/app-run-jobs/{rid}/spec-artifact')
    assert artifact.status_code==200 and artifact.json()['owner_acceptance']=='PENDING'
    assert artifact.json()['semantic_goal_acceptance']=='NOT_RUN'
    (tmp_path/'proof.json').write_text(json.dumps(dict(preview=review,receipt=r.json(),state=accepted,artifact=artifact.json()),ensure_ascii=False,indent=2))


@pytest.mark.parametrize('target', ['material','artifact'])
@pytest.mark.parametrize('fault', ['revoke','expiry'])
def test_revoked_target_before_private_body_and_stop(env,tmp_path,target,fault):
    from test_pb_natural_use_read_gates import TypedPrivateBarrier
    data, inst, rid, resource, _, _, path=flow(env,'pb')
    review,_=preview(data,path)
    contract=review['payload']['contract'];aid=contract['app_run_id']
    victim=resource if target=='material' else contract['output']['resource_id']
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id==victim,grants.c.tool_ref=='resource.read').values(
            **({'revoked':True,'revision':2} if fault=='revoke' else {'expires_at':time.time()-1})))
    with TypedPrivateBarrier(data[0],rid,aid,victim) as barrier:
        barrier.rules['natural_owner_records']=(natural_owner_records,'id',{review['id']},{'payload'})
        s=state(data,path,'prepare')
        assert s['owner_acceptance']=='STALE' and not s['content_access']
        assert 'payload' not in s['recovered']
        assert data[2].post(path+'-requests',json=decision(review)).status_code in [403,409]
        stop=dict(command='CANCEL',request_key='stop',expected_sequence=1,target_id=review['id'],
            target_fingerprint=review['fingerprint'],reason='Stop after revoked target')
        r=data[2].post(path+'-requests',json=stop)
        assert r.status_code==201,r.text
        assert state(data,path)['owner_acceptance']=='CANCELLED'
        assert not barrier.blocked,barrier.blocked
    (tmp_path/'private-barrier.json').write_text(json.dumps(dict(blocked=barrier.blocked,evaluated=barrier.evaluated),indent=2))


def test_invalid_choices_corrupt_seal_expiry_and_foreign_scope(env):
    data,inst,rid,_,_,_,path=flow(env)
    review,_=preview(data,path)
    body=decision(review)
    for wrong in [[],body['choices'][1:],body['choices']+[body['choices'][0]],
        [{**i,'reason':' '} for i in body['choices']]]:
        r=data[2].post(path+'-requests',json={**body,'choices':wrong})
        assert r.status_code in [422,409],r.text
        assert state(data,path)['sequence']==1
    assert data[2].get(path,params={'request_key':'unknown'}).status_code==409
    original=data[2].headers['Authorization'];data[2].headers['Authorization']='Bearer synthetic-test-B'
    assert data[2].get(path).status_code==403
    data[2].headers['Authorization']=original
    from sim2act import owner_acceptance as owner
    from unittest.mock import patch
    with patch.object(owner.time,'time',return_value=review['created_at']+901):
        assert state(data,path)['owner_acceptance']=='EXPIRED'
        assert data[2].post(path+'-requests',json=body).status_code==409
    with data[0].tx() as c:
        c.execute(update(natural_owner_seals).where(natural_owner_seals.c.record_id==review['id']).values(metadata_fingerprint='0'*64))
    assert data[2].get(path).status_code==409


def test_new_result_never_inherits_old_declaration(env):
    data,inst,rid,_,_,_,path=flow(env)
    review,_=preview(data,path)
    assert data[2].post(path+'-requests',json=decision(review)).status_code==201
    release=data[2].get(f"/api/internal/apps/{inst['source_app_id']}/releases").json()['items'][0]
    rid2=enqueue(data,release,inst,key='new-owner-result')
    drive_to_success(data,rid2,transport([]))
    assert state(data,path,'decision')['owner_acceptance']=='STALE'
    newpath=path.replace(rid,rid2)
    s=state(data,newpath)
    assert s['owner_acceptance']=='PENDING' and s['sequence']==0
    assert s['current']['result_version']==2
    review2,_=preview(data,newpath)
    assert review2['payload']['contract']['run_id']==rid2


def test_artifact_pointer_pollution_rejected_before_private_reads(env,tmp_path):
    from test_pb_natural_use_read_gates import TypedPrivateBarrier
    from sim2act.db import events, local_effects
    data,inst,rid,_,_,_,path=flow(env)
    review,_=preview(data,path)
    contract=review['payload']['contract'];victim=contract['output']['resource_id']
    fake=data[2].post(f"/api/projects/{data[4]}/resources",json=dict(name='fake.json',format='json',content='{}')).json()['id']
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id==victim,grants.c.tool_ref=='resource.read').values(revoked=True,revision=2))
        committed=c.execute(select(events).where(events.c.run_id==rid,events.c.kind=='SPEC_COMMITTED')).mappings().one()
        c.execute(update(events).where(events.c.id==committed['id']).values(data={**committed['data'],'artifact_resource':fake}))
        c.execute(update(local_effects).where(local_effects.c.resource_id==victim).values(resource_id=fake))
    with TypedPrivateBarrier(data[0],rid,contract['app_run_id'],victim) as barrier:
        barrier.rules['natural_owner_records']=(natural_owner_records,'id',{review['id']},{'payload'})
        assert not state(data,path)['content_access']
        assert data[2].post(path+'-requests',json=decision(review)).status_code==409
        assert not barrier.blocked,barrier.blocked
    (tmp_path/'pointer-barrier.json').write_text(json.dumps(dict(blocked=barrier.blocked,evaluated=barrier.evaluated),indent=2))


def test_precommit_revoke_rolls_back_record_and_seal(env,monkeypatch):
    from sim2act import owner_acceptance as owner
    data,_,_,resource,_,_,path=flow(env)
    review,_=preview(data,path)
    original=owner.natural_append
    before=all_rows(data[0])
    def append_then_revoke(c,*args,**kwargs):
        row=original(c,*args,**kwargs)
        c.execute(update(grants).where(grants.c.resource_id==resource,grants.c.tool_ref=='resource.read').values(revoked=True,revision=2))
        return row
    monkeypatch.setattr(owner,'natural_append',append_then_revoke)
    body=decision(review)
    r=data[2].post(path+'-requests',json=body)
    assert r.status_code==403,r.text
    proof=r.json()['error']['submission_rejection']
    assert proof['request_fingerprint']==fingerprint(body) and proof['previous_request']=='ABSENT'
    assert all_rows(data[0])==before
    assert data[2].get(path,params={'request_key':'decision'}).status_code==409


def test_goal_version_change_invalidates_exact_review(env):
    from sim2act.db import goal_cards
    data,_,_,_,goal,_,path=flow(env)
    review,_=preview(data,path)
    with data[0].tx() as c:
        c.execute(update(goal_cards).where(goal_cards.c.id==goal['id']).values(version=goal['version']+1))
    s=state(data,path,'prepare')
    assert s['owner_acceptance']=='STALE' and 'payload' not in s['recovered']
    r=data[2].post(path+'-requests',json=decision(review))
    assert r.status_code==409 and r.json()['error']['submission_rejection']['previous_request']=='ABSENT'


def test_precommit_typed_change_rolls_back_declaration(env,monkeypatch):
    from sim2act import owner_acceptance as owner
    from sim2act.db import internal_instance_data
    data,_,_,_,_,_,path=flow(env)
    review,_=preview(data,path)
    original=owner.natural_append;before=all_rows(data[0])
    def append_then_mutate(c,*args,**kwargs):
        row=original(c,*args,**kwargs)
        c.execute(update(internal_instance_data).where(
            internal_instance_data.c.run_id==review['payload']['contract']['app_run_id']).values(fingerprint='0'*64))
        return row
    monkeypatch.setattr(owner,'natural_append',append_then_mutate)
    body=decision(review);r=data[2].post(path+'-requests',json=body)
    assert r.status_code==409,r.text
    assert all_rows(data[0])==before
    assert r.json()['error']['submission_rejection']['previous_request']=='ABSENT'
