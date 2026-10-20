"""Real local new-material plans, worker, dual source proof and cold instances."""

import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create, work
from test_csv_material_reuse import accepted_target, path
from test_csv_two_sum_instances import STEPS, check_output, enqueue, release
from test_delivery_graph_apps import snapshot

from sim2act import csv_material_reuse as material
from sim2act.api import create_app
from sim2act.db import (
    Store,
    delivery_graph_requests,
    fingerprint,
    grants,
    internal_instance_data,
    runs,
)
from sim2act.worker import Worker

TARGET = 'label,price,units\nnew-A,0.125,3\nnew-B,19.375,8\nnew-C,20.5,6\n'


@pytest.fixture(autouse=True)
def no_model_transport(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('CSV material reuse must not call a model transport')
    for cls in (httpx.HTTPTransport, httpx.AsyncHTTPTransport, httpx.MockTransport):
        for name in ('handle_request', 'handle_async_request'):
            if hasattr(cls, name):
                monkeypatch.setattr(cls, name, denied)


def setup_material(env):
    client, pid = env[2], env[5]
    target = client.post(f'/api/projects/{pid}/resources', json=dict(
        name='already-authorized.csv', format='csv', content=TARGET)).json()['id']
    app = client.post(f'/api/projects/{pid}/apps/csv-preview', json=dict(
        name='Existing new-material CSV', goal='Two new sums', resource_id=target)).json()
    _, old_resource, _, _, rel = release(env)
    old = create(env, rel)
    accepted, _ = enqueue(env, old, rel)
    work(env, accepted)
    app = client.get(f'/api/apps/{app["id"]}').json()
    anchor = client.post(f'/api/projects/{pid}/apps/{app["id"]}/delivery-graph/derive', json=dict(
        expected_candidate_fingerprint=app['fingerprint'], request_key='target-anchor')).json()
    body = dict(expected_release_fingerprint=rel['fingerprint'], target_app_id=app['id'],
        expected_candidate_fingerprint=app['fingerprint'], expected_graph_fingerprint=anchor['graph_fingerprint'],
        expected_resource_id=target, expected_source_hash=app['candidate']['source_hash'],
        columns=dict(total_a='price', total_b='units'), request_key='two-sum-material')
    return rel, old, old_resource, app, body


def target_release(env, plan, accepted):
    job = work(env, accepted)
    detail = env[2].get(f'/api/csv-dag/runs/{job["id"]}')
    assert detail.status_code == 200, detail.text
    assert detail.json()['status'] == 'SUCCEEDED', detail.text
    reply = env[2].post(f'/api/csv-dag/runs/{job["id"]}/release-approvals', json=dict(
        expected_plan_fingerprint=plan['plan_fingerprint'], request_key='target-release'))
    assert reply.status_code == 201, reply.text
    a = reply.json()
    reply = env[2].post(f'/api/internal/approvals/{a["id"]}/commit', json=dict(fingerprint=a['fingerprint']))
    assert reply.status_code == 200, reply.text
    return reply.json(), detail.json()


def test_real_dual_new_csv_release_instance_cold_swap_and_immutable_history(env, tmp_path):
    rel, old, old_resource, target, body = setup_material(env)
    before = snapshot(env)
    options = env[2].get(f'/api/internal/releases/{rel["id"]}/csv-materials')
    assert options.status_code == 200, options.text
    assert options.json()['namespace'] == material.TWO_SUM_VERSION
    assert [x['resource_id'] for x in options.json()['items']] == [body['expected_resource_id']]
    value, accepted, url, confirm = accepted_target(env, rel, body)
    assert value['namespace'] == material.TWO_SUM_VERSION
    assert value['binding']['columns'] == body['columns'] and 'column' not in value['binding']
    assert env[2].post(path(rel), json=body).json()['plan']['plan_fingerprint'] == value['plan']['plan_fingerprint']
    assert env[2].post(url, json=confirm).json()['run_id'] == accepted['run_id']
    changed = copy.deepcopy(body)
    changed['columns']['total_b'] = 'price'
    frozen = fingerprint(snapshot(env))
    assert env[2].post(path(rel), json=changed).status_code == 409
    assert fingerprint(snapshot(env)) == frozen
    new, job = target_release(env, value['plan'], accepted)
    check_output(job['result']['output_by_step'], TARGET, body['expected_resource_id'], body['columns'])
    e = new['snapshot']['execution_source']
    assert e['default_columns'] == body['columns'] and 'default_column' not in e
    assert set(new['snapshot']['data_schema']['properties']['result']['properties']) == set(STEPS)
    instance = create(env, new)
    cold = Store(env[1].database_url, test_only=True)
    if not cold.sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers['Authorization'] = 'Bearer synthetic-test-A'
            swapped = dict(total_a='units', total_b='price')
            request = dict(expected_revision=1, expected_release_fingerprint=new['fingerprint'],
                input={'columns': swapped}, request_key='cold-swapped')
            reply = client.post(f'/api/internal/instances/{instance["id"]}/runs', json=request)
            assert reply.status_code == 202, reply.text
            rid = reply.json()['run_id']
            assert rid != job['id']
            worker = Worker(cold, env[1], NoModel())
            queued = cold.claim(worker.id, env[1].lease_seconds)
            assert queued['id'] == rid
            worker.process(queued)
            detail = client.get(f'/api/internal/instances/{instance["id"]}')
            assert detail.status_code == 200, detail.text
            d = detail.json()
            assert d['data_version'] == 1 and d['runs'][0]['status'] == 'SUCCEEDED'
            check_output(d['data'][0]['data']['result'], TARGET, body['expected_resource_id'], swapped)
            assert d['runs'][0]['proof']['model_requests'] == 0
    finally:
        cold.engine.dispose()
    after = snapshot(env)
    for table in ('principals', 'grants', 'app_drafts', 'resources'):
        assert before[table] == after[table], table
    for table in ('internal_instances', 'internal_releases', 'internal_instance_data', 'internal_app_runs'):
        for row in before[table]:
            assert row in after[table], table
    assert old_resource != body['expected_resource_id']
    # Material-derived versions cannot be transferred again.
    assert env[2].post(path(new), json=body).status_code == 400
    (tmp_path / 'dual-new-material-proof.json').write_text(json.dumps(dict(
        source_release=rel, material=value, new_release=new, target_run=job,
        cold_instance=d, old_history_unchanged=True, models=0), ensure_ascii=False, indent=2))


@pytest.mark.parametrize('columns', [None, {}, {'total_a': 'price'},
    {'total_a': 'price', 'wrong': 'units'}, {'total_a': 'price', 'total_b': 'units', 'extra': 'price'},
    {'total_a': True, 'total_b': 'units'}, {'total_a': 'label', 'total_b': 'units'},
    {'total_a': {'column': 'price'}, 'total_b': 'units'}])
def test_dual_material_rejects_scalar_or_wrong_node_mapping_without_writes(env, columns):
    rel, _, _, _, body = setup_material(env)
    if columns is None:
        del body['columns']
        body['column'] = 'price'
    else:
        body['columns'] = columns
    before = fingerprint(snapshot(env))
    reply = env[2].post(path(rel), json=body)
    assert reply.status_code in (400, 409, 422), reply.text
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize('attack', ['source-grant', 'target-grant', 'hash', 'owner', 'mixed-input'])
def test_dual_material_current_authority_and_exact_input_rejection_atomic(env, attack):
    rel, _, _, target, body = setup_material(env)
    if attack.endswith('grant'):
        runtime = target['runtime_id'] if attack == 'target-grant' else rel['snapshot']['draft']['runtime_id']
        with env[0].tx() as c:
            c.execute(update(grants).where(grants.c.principal_id == runtime).values(revoked=True))
    elif attack == 'hash':
        body['expected_source_hash'] = '0' * 64
    elif attack == 'owner':
        env[2].headers['Authorization'] = 'Bearer synthetic-test-B'
    else:
        body['column'] = 'price'
    before = fingerprint(snapshot(env))
    reply = env[2].post(path(rel), json=body)
    assert reply.status_code in (400, 403, 409, 422), reply.text
    assert fingerprint(snapshot(env)) == before


@pytest.mark.parametrize('runtime_role', ['source', 'target'])
def test_cold_dual_instance_rechecks_material_source_and_target_authority(env, runtime_role):
    rel, _, _, target, body = setup_material(env)
    value, accepted, _, _ = accepted_target(env, rel, body)
    new, _ = target_release(env, value['plan'], accepted)
    i = create(env, new)
    runtime = target['runtime_id'] if runtime_role == 'target' else rel['snapshot']['draft']['runtime_id']
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == runtime).values(revoked=True))
    before = fingerprint(snapshot(env))
    reply = env[2].post(f'/api/internal/instances/{i["id"]}/runs', json=dict(
        expected_revision=1, expected_release_fingerprint=new['fingerprint'],
        input={'columns': body['columns']}, request_key='must-refuse'))
    assert reply.status_code in (403, 409), reply.text
    assert fingerprint(snapshot(env)) == before


def test_dual_origin_joint_reseal_cannot_change_bound_second_column(env):
    rel, _, _, _, body = setup_material(env)
    value, accepted, _, _ = accepted_target(env, rel, body)
    with env[0].tx() as c:
        row = c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.kind == material.KIND,
            delivery_graph_requests.c.request_key == value['plan']['request_key'])).mappings().one()
        changed = copy.deepcopy(row['snapshot'])
        changed['response']['columns']['total_b'] = 'price'
        c.execute(update(delivery_graph_requests).where(
            delivery_graph_requests.c.kind.in_([material.KIND, material.KIND + '_seal']),
            delivery_graph_requests.c.request_key == value['plan']['request_key']).values(
                snapshot=changed, fingerprint=fingerprint(changed)))
    before = fingerprint(snapshot(env))
    assert env[2].get(f'/api/csv-dag/runs/{accepted["run_id"]}').status_code == 409
    assert fingerprint(snapshot(env)) == before


def test_two_nodes_may_choose_same_new_numeric_column_without_collapsing_sinks(env):
    rel, _, _, _, body = setup_material(env)
    body['columns'] = dict(total_a='price', total_b='price')
    value, accepted, _, _ = accepted_target(env, rel, body)
    new, proof = target_release(env, value['plan'], accepted)
    check_output(proof['result']['output_by_step'], TARGET, body['expected_resource_id'], body['columns'])
    assert new['snapshot']['execution_source']['default_columns'] == body['columns']
    assert set(new['snapshot']['data_schema']['properties']['result']['properties']) == set(STEPS)


@pytest.mark.parametrize('runtime_role', ['source', 'target'])
def test_revoke_after_first_sum_prevents_second_sum_and_partial_typed_append(env, runtime_role):
    from sim2act import csv_dag as dag

    rel, _, _, target, body = setup_material(env)
    value, accepted, _, _ = accepted_target(env, rel, body)
    new, _ = target_release(env, value['plan'], accepted)
    instance = create(env, new)
    accepted, _ = enqueue(env, instance, new, body['columns'])
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job['id'] == accepted['run_id']
    assert dag.advance(worker, job) and dag.advance(worker, job)
    runtime = target['runtime_id'] if runtime_role == 'target' else rel['snapshot']['draft']['runtime_id']
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == runtime).values(revoked=True))
    worker.process(job)
    with env[0].engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == job['id'])).mappings().one()
        assert saved['status'] == 'WAITING_RESOURCE' and saved['result'] is None
        assert saved['context']['tools'] == 2
        assert not c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == instance['id'])).first()
