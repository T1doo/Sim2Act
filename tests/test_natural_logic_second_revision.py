"""Two explicit local adjustments; new CHECK even for reverse dependency."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_natural_logic_patches import prepared, start
from test_natural_spec_apps import transport
from test_pa_natural_uses import prepare as prepare_use
from test_pa_natural_uses import target_use
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import natural_logic_patches as logic
from sim2act.api import create_app
from sim2act.db import Store, fingerprint, internal_instances


def release_checked(data, path, key, proof):
    response = data[2].post(path + '/version-approvals', json=dict(request_key=key,
        expected_check_fingerprint=proof['check_fingerprint'], consent=logic.VERSION_CONSENT))
    assert response.status_code == 201, response.text
    approval = response.json()
    response = data[2].post('/api/internal/approvals/' + approval['id'] + '/commit',
        json=dict(fingerprint=approval['fingerprint']))
    assert response.status_code == 200, response.text
    release = response.json()
    response = data[2].post('/api/internal/releases/' + release['id'] + '/instances',
        json=dict(expected_release_fingerprint=release['fingerprint'], request_key=key+'-instance'))
    assert response.status_code == 201, response.text
    return release, response.json()


@pytest.mark.parametrize("style", ["parallel", "sequential"])
def test_second_preview_requires_actual_r1_candidate(env, tmp_path, style):
    data, aid, original, instance, graph, path, body, preview = prepared(env, style)
    accepted = start(data, path, preview)
    drive_to_success(data, accepted['run_id'], transport([]))
    proof = data[2].get(path+'/checks/logic-edit').json()
    first, source = release_checked(data, path, 'logic-edit', proof)
    second_path = '/api/internal/instances/' + source['id'] + '/logic-patches'
    response = data[2].get(second_path+'/context')
    assert response.status_code == 200, response.text
    baseline = response.json()
    assert baseline['context']['parent_logic']['depth'] == 1
    assert baseline['base_candidate'] == preview['effective_candidate']
    assert baseline['graph']['graph_fingerprint'] != graph['graph_fingerprint']
    assert {n['id'] for n in baseline['graph']['graph']['nodes']} == {n['id'] for n in graph['graph']['nodes']}
    body2 = {**body, 'request_key':'second-edit', 'expected_revision':source['revision'],
        'expected_release_fingerprint':first['fingerprint'], 'consume_prior_feedback':style=='sequential',
        'expected_graph_fingerprint':baseline['graph']['graph_fingerprint']}
    before = snapshot(data[0])
    stale = data[2].post(second_path+'/previews', json={**body2,
        'request_key':'stale-original-graph', 'expected_graph_fingerprint':graph['graph_fingerprint']})
    assert stale.status_code == 409, stale.text
    assert snapshot(data[0]) == before
    response = data[2].post(second_path+'/previews', json=body2)
    assert response.status_code == 201, response.text
    second = response.json()
    assert second['original_recipe_fingerprint'] == fingerprint(preview['effective_candidate']['spec_recipe'])
    assert second['effective_candidate']['manifest']['revision'] == 3
    assert second['effective_candidate']['logic_revision']['revision'] == 3
    assert second['effective_candidate']['spec_recipe'] == original['snapshot']['draft']['candidate']['spec_recipe']
    assert len(second['preserved_action_definitions']) == 5
    assert second['impact']['graph_fingerprint'] == baseline['graph']['graph_fingerprint']
    assert len(second['impact']['revalidation_nodes']) == len(graph['graph']['nodes'])
    accepted2 = data[2].post(second_path+'/checks',json=dict(request_key='second-edit',
        expected_preview_fingerprint=second['preview_fingerprint'],consent=logic.CHECK_CONSENT))
    assert accepted2.status_code == 202, accepted2.text
    accepted2 = accepted2.json()
    assert accepted2['run_id'] != accepted['run_id'] and accepted2['check_instance_id'] != accepted['check_instance_id']
    assert data[2].post(second_path+'/version-approvals',json=dict(request_key='second-edit',
        expected_check_fingerprint=proof['check_fingerprint'],consent=logic.VERSION_CONSENT)).status_code == 409
    sent = []
    drive_to_success(data,accepted2['run_id'],transport(sent))
    assert len(sent) == 2
    assert ('prior_items' in json.loads(sent[1]['messages'][1]['content'])['current_inputs']) == (style=='sequential')
    response = data[2].get(second_path+'/checks/second-edit')
    assert response.status_code == 200, response.text
    proof2 = response.json()
    second_release, target = release_checked(data,second_path,'second-edit',proof2)
    assert second_release['snapshot']['draft'] == original['snapshot']['draft']
    assert second_release['snapshot']['natural_logic_source']['instance_id'] == source['id']
    assert data[2].get('/api/internal/releases/'+first['id']).json() == first
    final_path = '/api/internal/instances/'+target['id']+'/logic-patches'
    response = data[2].get(final_path+'/context')
    assert response.status_code == 200 and response.json()['remaining_adjustments'] == 0, response.text
    assert response.json()['context']['parent_logic']['depth'] == 2
    before = snapshot(data[0])
    third = data[2].post(final_path+'/previews',json={**body2,'request_key':'third-refused',
        'expected_revision':target['revision'],'expected_release_fingerprint':second_release['fingerprint'],
        'expected_graph_fingerprint':response.json()['graph']['graph_fingerprint']})
    assert third.status_code == 400 and third.json()['error']['code'] == 'UNSUPPORTED_CAPABILITY', third.text
    assert snapshot(data[0]) == before
    app = data[2].get('/api/apps/'+aid).json()
    route = '/api/internal/instances/'+target['id']
    _,_,use_body = target_use(data,app,second_release,target,THIRD,'r2-cold-material')
    use_body['expected_recipe_fingerprint'] = fingerprint(second['effective_candidate']['spec_recipe'])
    reviewed,commit = prepare_use(data,route,use_body)
    assert reviewed['effective_candidate']['manifest']['revision'] == 3
    queued = data[2].post(route+'/pa-use-runs',json=commit)
    assert queued.status_code == 202, queued.text
    cold = Store(data[1].database_url,test_only=True)
    try:
        with TestClient(create_app(cold,data[1])) as client:
            client.headers['Authorization']='Bearer synthetic-test-A'
            current=(cold,data[1],client,*data[3:])
            sent=[]
            drive_to_success(current,queued.json()['run_id'],transport(sent,THIRD))
            assert len(sent)==2 and ('prior_items' in json.loads(sent[1]['messages'][1]['content'])['current_inputs']) == (style=='sequential')
            result=client.get('/api/internal/app-run-jobs/'+queued.json()['run_id']+'/spec-artifact')
            assert result.status_code==200,result.text
            assert json.loads(result.json()['resource']['content'])['source_content']==THIRD
    finally:
        cold.engine.dispose()
    after=snapshot(data[0])
    for table in ('app_drafts','internal_releases','goal_cards','goal_card_versions'):
        assert all(row in after[table] for row in before[table])
    with data[0].tx() as c:
        for old_instance in [instance,source]:
            row=c.execute(select(internal_instances).where(internal_instances.c.id==old_instance['id'])).mappings().one()
            assert row['release_id']==old_instance['release_id'] and row['data_version']==0
    (tmp_path/'r2-proof.json').write_text(json.dumps(dict(style=style,preview1=preview,preview2=second,
        release1=first,release2=second_release,source=source,target=target,check1=accepted,check2=accepted2,
        original=original,body2=body2,synthetic_only=True),indent=2)+'\n')
