"""Bounded correction: B authority predates the genuinely adopted A2 origin."""
from conftest import env as env
from sqlalchemy import insert, select
from test_csv_column_revisions import adopt
from test_csv_goal_revisions import approve, drive, ready, start
from test_csv_goal_revisions import raw_trace as raw_trace
from test_csv_material_revisions import B_CONTENT, B_HASH, dump, proposal, reject_without_writes
from test_internal_lifecycle import limits

from sim2act import app_jobs as jobs
from sim2act.db import grants, internal_instances, new_id


def prepared_authority_before_adoption(env):
    data, aid, base, instance, path, _, _, goal = ready(env, prior=True)
    response = data[2].post(f'/api/projects/{data[5]}/resources', json={
        'name': 'existing-authority-before-A2.csv', 'format': 'csv', 'content': B_CONTENT})
    assert response.status_code == 201, response.text
    bid = response.json()['id']
    # Exact test-only B authority, before accepting either the A2 or M CHECK.
    with data[0].tx() as c:
        originals = [dict(row) for row in c.execute(select(grants).where(
            grants.c.principal_id == instance['runtime_id'], grants.c.resource_id == data[6])).mappings()]
        assert len(originals) == 2 and {row['tool_ref'] for row in originals} == {'resource.read', 'data.aggregate_csv'}
        for row in originals:
            c.execute(insert(grants).values(**{**row, 'id': new_id('grant'), 'resource_id': bid}))
    refreshed = data[2].post(f'/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive', json={
        'request_key': 'cas-B-authority-before-A2',
        'expected_candidate_fingerprint': base['snapshot']['draft']['fingerprint']})
    assert refreshed.status_code == 201, refreshed.text
    response = data[2].get(path + '/context')
    assert response.status_code == 200, response.text
    ctx = response.json()
    a2_body = dict(request_key='cas-A2-after-existing-B-authority',
        expected_revision=instance['revision'], expected_release_fingerprint=base['fingerprint'],
        expected_graph_fingerprint=ctx['graph_fingerprint'], goal_version=ctx['goal']['version'],
        goal_fingerprint=ctx['goal']['fingerprint'], baseline_column='amount', column='quantity')
    response = data[2].post(path + '/previews', json=a2_body)
    assert response.status_code == 201, response.text
    old_value = response.json()
    old_check = start(data, path, old_value)
    drive(data, old_check['run_id'])
    v2 = approve(data, path, old_value)
    current = adopt(data, instance, path, old_value, v2)
    assert current['revision'] == 2 and current['data_version'] == 1
    material_path = f'/api/internal/instances/{current["id"]}/csv-material-revisions'
    response = data[2].get(material_path + '/context')
    assert response.status_code == 200, response.text
    ctx = response.json()['context']
    assert any(row['resource_id'] == bid and row['hash'] == B_HASH for row in response.json()['materials'])
    body = dict(request_key='replace-material-B-cas', expected_revision=2, expected_data_version=1,
        expected_release_fingerprint=v2['fingerprint'], expected_graph_fingerprint=ctx['graph_fingerprint'],
        goal_version=2, goal_fingerprint=ctx['goal']['fingerprint'],
        baseline_column='quantity', column='quantity', resource_id=bid, source_hash=B_HASH)
    return data, aid, base, current, path, material_path, body, v2, old_value, goal


def test_material_stale_cas_after_real_A_run_with_preexisting_B_authority(env, tmp_path):
    seed = prepared_authority_before_adoption(env)
    data, _, _, current, path, _, body, v2, *_ = seed
    value = proposal(seed)
    accepted = start(data, path, value)
    drive(data, accepted['run_id'])
    version = approve(data, path, value)
    response = data[2].post(path + '/adoption-approvals', json=dict(
        request_key=body['request_key'], expected_revision=current['revision'],
        target_release_id=version['id'], expected_target_fingerprint=version['fingerprint']))
    assert response.status_code == 201, response.text
    approval = data[2].get(path + '/adoption-approvals/' + body['request_key'])
    assert approval.status_code == 200, approval.text
    approval = approval.json()
    intervening = jobs.enqueue(data[0], data[3], current['id'], 2, v2['fingerprint'],
        {'column': 'quantity'}, 'actual-A-after-B-approval-corrected-fixture', limits(data),
        csv_review='FREEZE_SUM_ONLY_WITHOUT_MD')
    drive(data, intervening['run_id'])
    result = jobs.inspect_job(data[0], data[3], intervening['run_id'])
    assert result['result']['sum'] == '5' and result['result_version'] == 2
    rejected = reject_without_writes(data,
        lambda: data[2].post(f'/api/internal/instances/{current["id"]}/switch-approvals/{approval["id"]}/commit',
            json={'fingerprint': approval['fingerprint']}), 409)
    with data[0].tx() as c:
        state = dict(c.execute(select(internal_instances).where(internal_instances.c.id == current['id'])).mappings().one())
    assert state['release_id'] == v2['id'] and state['revision'] == 2 and state['data_version'] == 2
    dump(tmp_path / 'actual-independent-material-stale-cas.json', dict(
        fixture='B authority and canonical derive precede exact public A2 proposal/CHECK/adoption; no later grant changes',
        value=value, check=accepted, target=version, approval=approval, intervening=result,
        rejected=rejected, actual_instance=state))
