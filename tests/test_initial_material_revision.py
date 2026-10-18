"""Original Release directly replaces an already App-authorized CSV.

The two App/B grants are a declared synthetic PRECONDITION, not product writes.
No Goal PUT, column revision or prior adoption prepares this first Release.
"""
import json

import pytest
from sqlalchemy import insert, select, update
from test_csv_goal_revisions import baseline
from test_internal_lifecycle import limits
from test_local_record_apps import snapshot

from sim2act import csv_material_revisions as material
from sim2act import delivery_graph_apps as graph
from sim2act.db import grants, new_id, resources
from sim2act.errors import DomainError


def prepared(env):
    data, aid, release, instance, _cid, _content, app = baseline(env)
    client = data[2]
    sources = []
    for name in ['existing-B.csv', 'project-only-C.csv']:
        r = client.post(f'/api/projects/{data[5]}/resources', json=dict(
            name=name, format='csv', content='amount,quantity\n100,7\n250,8\n'))
        assert r.status_code == 201, r.text
        sources.append(r.json())
    with data[0].tx() as c:
        original = list(c.execute(select(grants).where(grants.c.principal_id == instance['runtime_id'],
            grants.c.resource_id == data[6])).mappings())
        assert len(original) == 2 and {r['tool_ref'] for r in original} == {'resource.read', 'data.aggregate_csv'}
        for row in original:
            c.execute(insert(grants).values(**{**row, 'id': new_id('grant'), 'resource_id': sources[0]['id']}))
    response = client.post(f'/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive', json=dict(
        request_key='first-material-authority-precondition', expected_candidate_fingerprint=app['fingerprint']))
    assert response.status_code == 201, response.text
    path = f"/api/internal/instances/{instance['id']}/csv-material-revisions"
    response = client.get(path + '/context')
    assert response.status_code == 200, response.text
    ctx = response.json()['context']
    assert ctx['initial_material'] is True and ctx['parent']['spec_revision'] == 1
    assert ctx['parent']['kind'] == 'ORIGINAL_CSV_RELEASE' and ctx['parent']['column'] is None
    assert ctx['goal']['version'] == ctx['original_goal_version'] == 1 and instance['revision'] == 1
    assert [r['resource_id'] for r in response.json()['materials']] == [sources[0]['id']]
    body = dict(request_key='direct-first-material', expected_revision=1, expected_data_version=0,
        expected_release_fingerprint=release['fingerprint'], expected_graph_fingerprint=ctx['graph_fingerprint'],
        goal_version=1, goal_fingerprint=ctx['goal']['fingerprint'], baseline_column='amount', column='amount',
        resource_id=sources[0]['id'], source_hash=response.json()['materials'][0]['hash'])
    return data, aid, path, ctx, body, sources


def test_direct_original_material_preview_authority_hash_and_exact_history(env, tmp_path):
    data, _aid, path, ctx, body, sources = prepared(env)
    client = data[2]
    before = snapshot(data[0])
    rejected = []
    for change, status in [(dict(source_hash='0' * 64), 409), (dict(resource_id=sources[1]['id']), 403)]:
        response = client.post(path + '/previews', json={**body, **change})
        assert response.status_code == status, response.text
        assert response.json()['error']['submission_rejection']['acceptance'] == 'NOT_ACCEPTED'
        assert snapshot(data[0]) == before
        rejected.append(response.json())
    response = client.post(path + '/previews', json=body)
    assert response.status_code == 201, response.text
    value = response.json()
    changed = {n['key'] for n in value['parent_graph']['graph']['nodes'] if n['id'] in value['impact']['changed_nodes']}
    assert changed == {'source:' + ctx['source']['resource_id'], 'action:aggregate'}
    assert value['impact']['revalidation_scope'] == 'APP' and value['spec_revision'] == 2
    assert value['effective_candidate']['manifest']['data_bindings'][0]['resource_ref'] == sources[0]['id']
    assert value['effective_candidate']['manifest']['input_schema']['properties']['column']['enum'] == ['amount']
    assert value['effective_candidate']['generation']['goal_snapshot'] == ctx['goal']['snapshot']
    assert value['effective_candidate']['goal'] == ctx['goal']['snapshot']['content']
    assert client.post(path + '/previews', json=body).json() == value
    after = snapshot(data[0])
    assert [t for t in before if before[t] != after[t]] == ['delivery_graph_requests']
    assert len(after['delivery_graph_requests']) == len(before['delivery_graph_requests']) + 2
    (tmp_path / 'direct-material-preview.json').write_text(json.dumps(dict(
        precondition='existing App/B two Grants explicitly provisioned before derive and measurement',
        before=before, after=after, context=ctx, preview=value, rejected=rejected,
        rejection_all55_equal=True), ensure_ascii=False, indent=2))


def test_direct_material_action_input_fix_respects_existing_manual_lock(env, tmp_path):
    data, aid, path, ctx, body, _sources = prepared(env)
    with data[0].tx() as c:
        saved = graph.current(data[0], c, data[3], data[5], aid, limits(data))
    node = next(n for n in saved['graph']['nodes'] if n['key'] == 'action:aggregate')
    graph.set_lock(data[0], data[3], data[5], aid, dict(request_key='lock-first-material-action',
        expected_graph_fingerprint=ctx['graph_fingerprint'], locked=True,
        change=dict(node_id=node['id'], expected_revision=node['revision'],
                    expected_content_fingerprint=node['content_fingerprint'])), limits(data))
    r = data[2].post(f'/api/projects/{data[5]}/apps/{aid}/delivery-graph/derive', json=dict(
        request_key='locked-first-material-anchor', expected_candidate_fingerprint=saved['candidate_fingerprint']))
    assert r.status_code == 201, r.text
    ctx = data[2].get(path + '/context').json()['context']
    before = snapshot(data[0])
    response = data[2].post(path + '/previews', json={**body, 'expected_graph_fingerprint': ctx['graph_fingerprint']})
    assert response.status_code == 400 and response.json()['error']['code'] == 'LOCK_CONFLICT', response.text
    assert snapshot(data[0]) == before
    (tmp_path / 'direct-material-locked.json').write_text(json.dumps(dict(
        context=ctx, before=before, after=snapshot(data[0]), response=response.json()), ensure_ascii=False, indent=2))


def test_original_proof_reuse_retains_write_transaction_and_authority_boundaries(env, monkeypatch, tmp_path):
    data, aid, _path, ctx, _body, _sources = prepared(env)
    store, user, cap = data[0], data[3], limits(data)
    original, calls = material._original_definition, []

    def counted(*args):
        calls.append(True)
        return original(*args)

    monkeypatch.setattr(material, '_original_definition', counted)
    with store.tx() as c:
        saved = graph.current(store, c, user, data[5], aid, cap)
        value = material.source_definition(store, c, user, ctx, saved, cap)
        value[1]['candidate']['source_hash'] = 'caller-mutation'
        again = material.source_definition(store, c, user, ctx, saved, cap)
        assert len(calls) == 1 and again[1]['candidate']['source_hash'] == ctx['source']['hash']
        c.execute(update(resources).where(resources.c.id == data[6]).values(name=resources.c.name))
        material.source_definition(store, c, user, ctx, saved, cap)
        assert len(calls) == 2
    with store.tx() as c:
        material.source_definition(store, c, user, ctx, saved, cap)
        assert len(calls) == 3
        c.execute(update(grants).where(grants.c.principal_id == ctx['runtime_id'],
            grants.c.resource_id == data[6]).values(revoked=True))
    before = snapshot(store)
    with store.tx() as c, pytest.raises(DomainError) as rejected:
        material.source_definition(store, c, user, ctx, saved, cap)
    assert rejected.value.code == 'GRANT_REVOKED' and snapshot(store) == before
    (tmp_path / 'direct-material-proof-boundaries.json').write_text(json.dumps(dict(
        full_reconstructions=3, same_transaction_hit_deepcopy=True, every_write_invalidates=True,
        new_transaction_reconstructs=True, revoked_original_source_error=rejected.value.public(),
        before=before, after=snapshot(store)), ensure_ascii=False, indent=2))
