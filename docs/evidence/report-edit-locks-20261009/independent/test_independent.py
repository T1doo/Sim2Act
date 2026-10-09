"""Independent Report-lock review cases; synthetic archived fixture only."""
import copy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_report_presentations import prepared
from conftest import env as base_env
from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import snapshot
from sim2act import manual_locks as ml
from sim2act.api import create_app
from sim2act.db import Store, app_drafts, fingerprint, grants, resources, runs
from sim2act.db import delivery_graph_requests as requests, delivery_graph_locks as locks
from sim2act.errors import DomainError

@pytest.fixture
def env(tmp_path):
    source=base_env.__wrapped__(tmp_path)
    try:
        yield bounded_env.__wrapped__(next(source))
    finally:source.close()

def prepared_case(env,tmp_path,peer=False):
    app,g,url,definition,output,wires=prepared(env,tmp_path,peer=peer)
    return app,g,url.removesuffix('/report-presentations'),definition,output,wires

def lock_body(g,key='independent-lock',locked=True,rev=0,node_key='view:text:decision'):
    n=next(v for v in g['graph']['nodes'] if v['key']==node_key)
    return dict(expected_graph_fingerprint=g['graph_fingerprint'],expected_graph_revision=g['graph_revision'],
                change=dict(node_id=n['id'],expected_revision=n['revision'],expected_content_fingerprint=n['content_fingerprint']),
                expected_lock_revision=rev,locked=locked,request_key=key,consent='CONFIRM_EXACT_PROJECT_EDIT_LOCK')

def derive(env,base,app,key):
    r=env[2].post(base+'/derive',json={'expected_candidate_fingerprint':app['fingerprint'],'request_key':key})
    assert r.status_code==201,r.text
    return r.json()

def post_lock(env,base,b):
    r=env[2].post(base+'/manual-locks',json=b)
    assert r.status_code==201,r.text
    return r.json()

@pytest.mark.parametrize('key',['view:text:decision','action:report'])
def test_report_public_lock_cold_receipt_aba_and_immutable_scope(env,tmp_path,key):
    app,g,base,_,_,wires=prepared_case(env,tmp_path)
    before=snapshot(env)
    request=lock_body(g,node_key=key);response=post_lock(env,base,request)
    after=snapshot(env)
    assert all(before[t]==after[t] for t in before if t not in ['delivery_graph_locks','delivery_graph_requests'])
    assert response['lock']['logical_key']==key and response['lock']['revision']==1
    cold=Store(env[1].database_url,test_only=True)
    try:
        with TestClient(create_app(cold,env[1])) as client:
            client.headers['Authorization']='Bearer synthetic-test-A'
            reply=client.post(base+'/manual-locks',json=request)
            assert reply.status_code==201 and reply.json()['cached'] and reply.json()['is_current']
            assert client.get(base+'/manual-locks/receipt',params={'request_key':request['request_key']}).status_code==200
    finally:cold.engine.dispose()
    assert snapshot(env)==after
    current=derive(env,base,app,'independent-locked')
    post_lock(env,base,lock_body(current,key='independent-unlock',locked=False,rev=1,node_key=key))
    fresh=derive(env,base,app,'independent-unlocked')
    before=snapshot(env)
    stale=lock_body(g,key='aba-new-key',node_key=key)
    r=env[2].post(base+'/manual-locks',json=stale)
    assert r.status_code==409 and snapshot(env)==before
    history=env[2].get(base+'/manual-locks').json()
    assert {v['receipt_status'] for v in history['history']}=={'CURRENT','SUPERSEDED'}
    assert history['graph_fingerprint']==fresh['graph_fingerprint'] and not history['needs_derive']
    original=env[2].get('/api/apps/'+app['id']).json()
    assert original['fingerprint']==app['fingerprint'] and original['candidate']==app['candidate']
    assert len(wires)==4

def test_lock_conflict_unlock_new_presentation_preserves_every_original(env,tmp_path):
    app,g,base,b,output,wires=prepared_case(env,tmp_path)
    post_lock(env,base,lock_body(g))
    locked=derive(env,base,app,'locked-edit')
    before=snapshot(env)
    plan={'expected_graph_fingerprint':locked['graph_fingerprint'],'request_key':'denied-plan','changes':[lock_body(locked)['change']]}
    r=env[2].post(base+'/plans',json=plan)
    assert r.status_code==400 and r.json()['error']['code']=='LOCK_CONFLICT'
    assert snapshot(env)==before
    post_lock(env,base,lock_body(locked,key='unlock-edit',locked=False,rev=1))
    fresh=derive(env,base,app,'unlocked-edit')
    plan.update(expected_graph_fingerprint=fresh['graph_fingerprint'],request_key='new-edit-plan',changes=[lock_body(fresh)['change']])
    r=env[2].post(base+'/plans',json=plan);assert r.status_code==201,r.text
    b.update(expected_graph_fingerprint=fresh['graph_fingerprint'],plan_key='new-edit-plan',expected_plan_fingerprint=r.json()['native_outer_fingerprint'],request_key='independent-explanation')
    before=snapshot(env)
    patch=env[2].post(base+'/report-presentations',json=b);assert patch.status_code==201,patch.text
    r=env[2].post(base+'/report-presentations/independent-explanation/checks',json={'expected_patch_fingerprint':patch.json()['patch_fingerprint'],'request_key':'independent-text-check'})
    assert r.status_code==201 and r.json()['text']==output['explanation']
    assert r.json()['semantic_status']=='UNKNOWN' and r.json()['owner_acceptance']=='PENDING' and r.json()['actual_material_verification']=='PENDING'
    assert all(before[t]==snapshot(env)[t] for t in before if t!='delivery_graph_requests')
    assert len(wires)==4

@pytest.mark.parametrize('damage',['graph_rev_bool','lock_rev','node_revision','consent','key_change','unknown_node'])
def test_report_cas_and_exact_request_seal_reject_with_no_writes(env,tmp_path,damage):
    _,g,base,_,_,_=prepared_case(env,tmp_path)
    b=lock_body(g)
    if damage=='key_change':post_lock(env,base,b);b['locked']=False
    elif damage=='graph_rev_bool':b['expected_graph_revision']=True
    elif damage=='lock_rev':b['expected_lock_revision']=1
    elif damage=='node_revision':b['change']['expected_revision']+=1
    elif damage=='unknown_node':b['change']['node_id']='node_'+'9'*32
    else:b['consent']='AUTOMATIC'
    before=snapshot(env);r=env[2].post(base+'/manual-locks',json=b)
    assert r.status_code in [400,409,422] and snapshot(env)==before

@pytest.mark.parametrize('damage',['other_user','source_hash_changed','target_grant','source_run_result','candidate_kind','seal'])
def test_source_authority_and_canonical_family_checked_before_lock_history(env,tmp_path,damage):
    app,g,base,b,_,_=prepared_case(env,tmp_path)
    request=lock_body(g);post_lock(env,base,request)
    if damage=='other_user':env[2].headers['Authorization']='Bearer synthetic-test-B'
    else:
        with env[0].tx() as c:
            if damage=='source_hash_changed':
                proof=app['candidate']['report_proof'];rid=proof['target_resource_id']
                import hashlib
                c.execute(update(resources).where(resources.c.id==rid).values(content='changed material',hash=hashlib.sha256(b'changed material').hexdigest()))
            elif damage=='target_grant':
                c.execute(update(grants).where(grants.c.principal_id==env[3],grants.c.resource_id==app['candidate']['report_proof']['target_resource_id']).values(revoked=True))
            elif damage=='source_run_result':
                c.execute(update(runs).where(runs.c.id==app['candidate']['report_proof']['source_run_id']).values(result={'damaged':True}))
            elif damage=='candidate_kind':
                value=copy.deepcopy(app['candidate']);value['actions'][0]['executor']['kind']='bounded_agent'
                c.execute(update(app_drafts).where(app_drafts.c.id==app['id']).values(candidate=value,fingerprint=fingerprint(value)))
            else:
                row=c.execute(select(requests).where(requests.c.app_id==app['id'],requests.c.kind=='manual_edit_lock_seal')).mappings().one()
                value=copy.deepcopy(row['snapshot']);value['response']['lock']['revision']=9
                c.execute(update(requests).where(requests.c.app_id==app['id'],requests.c.kind=='manual_edit_lock_seal').values(snapshot=value,fingerprint=fingerprint(value)))
    before=snapshot(env)
    for route in [base+'/manual-locks',base+'/manual-locks/receipt?request_key=independent-lock']:
        r=env[2].get(route);assert r.status_code in [400,403,409],r.text
        assert snapshot(env)==before

def test_real_accepted_plan_replay_can_return_lock_conflict_after_peer_lock(env,tmp_path):
    app,g,base,b,_,_=prepared_case(env,tmp_path,peer=True)
    with env[0].tx() as c:
        peer=dict(next(row for row in c.execute(select(app_drafts).where(app_drafts.c.project_id==env[5])).mappings()
             if row['id']!=app['id'] and row['candidate'].get('manifest',{}).get('workflow',[{}])[0].get('step_id')=='aggregate'))
    peer_base=f'/api/projects/{env[5]}/apps/{peer["id"]}/delivery-graph'
    peer_g=env[2].get(peer_base).json()
    node=next(n for n in peer_g['graph']['nodes'] if n['kind']=='VIEW')
    peer_request=lock_body(peer_g,key='peer-lock',node_key=node['key'])
    post_lock(env,peer_base,peer_request)
    derive(env,peer_base,peer,'peer-lock-anchor')
    before=snapshot(env)
    original_plan={'expected_graph_fingerprint':g['graph_fingerprint'],'request_key':'presentation-plan','changes':[lock_body(g)['change']]}
    r=env[2].post(base+'/plans',json=original_plan)
    assert r.status_code==400 and r.json()['error']['code']=='LOCK_CONFLICT',r.text
    assert snapshot(env)==before
    with env[0].tx() as c:
        persisted=c.execute(select(requests).where(requests.c.app_id==app['id'],requests.c.kind=='plan',requests.c.request_key=='presentation-plan')).mappings().one()
    assert persisted['snapshot']['request']==original_plan
    Path('/tmp/sim2act-report-edit-locks-independent-20261009/accepted-replay-lock.json').write_text(json.dumps({'status':r.status_code,'error':r.json()['error'],'accepted_request_preserved':True},indent=2))

def test_save_real_page_fixture_for_independent_dom(env,tmp_path):
    app,g,base,b,output,wires=prepared_case(env,tmp_path)
    history=env[2].get(f'/api/projects/{env[5]}/apps/{app["id"]}/history')
    assert history.status_code==200,history.text
    unlocked_state=env[2].get(base+'/manual-locks')
    assert unlocked_state.status_code==200,unlocked_state.text
    Path('/tmp/sim2act-report-edit-locks-independent-20261009/page-fixture.json').write_text(json.dumps({'app':app,'graph':g,'history':history.json(),'manual_state':unlocked_state.json()},ensure_ascii=False,indent=2))
