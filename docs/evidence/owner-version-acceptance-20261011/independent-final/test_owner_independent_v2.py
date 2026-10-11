"""Independent SQLite/HTTP/normal-Worker probes; declarations are SIMULATED.

Source writes are confined to disposable SQLite fixtures. No live provider or
semantic owner signoff is exercised. History files are written only to /tmp.
"""
import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import delete, event, select, update

import test_owner_acceptance as author
from test_goal_text_applications import run_input
from sim2act.db import (
    grants, internal_app_runs, internal_owner_records, internal_owner_seals,
    operations, runs,
)

OUT = Path('/tmp/owner-version-acceptance-review-20261011/independent-v2')
OUT.mkdir(exist_ok=True)


def accept(data, release, instance, job):
    review, _ = author.prepare(data, release, instance, job)
    body = author.choice_body(review)
    response = data[2].post(author.path(instance) + '-requests', json=body)
    assert response.status_code == 201, response.text
    assert author.state(data, instance)['owner_acceptance'] == 'ACCEPTED'
    return review, response.json()['record'], body


def edit_goal(data, content, expected):
    response = data[2].put(
        '/api/goal-cards/' + data[-1]['id'],
        json={**content, 'expected_version': expected},
    )
    assert response.status_code == 200, response.text
    restored = data[2].get('/api/goal-cards/' + data[-1]['id'])
    assert restored.status_code == 200, restored.text
    return restored.json()


def switch(data, instance, release, revision):
    url = '/api/internal/instances/' + instance['id'] + '/switch-approvals'
    prepared = data[2].post(url, json={
        'target_release_id': release['id'],
        'expected_target_fingerprint': release['fingerprint'],
        'expected_revision': revision,
    })
    assert prepared.status_code == 201, prepared.text
    a = prepared.json()
    response = data[2].post(url + '/' + a['id'] + '/commit', json={'fingerprint': a['fingerprint']})
    assert response.status_code == 200, response.text
    return response.json()


def second_release(data, instance):
    client = data[2]
    aid = instance['source_app_id']
    draft = client.get('/api/apps/' + aid).json()
    response = client.post('/api/internal/apps/' + aid + '/release-approvals', json={
        'expected_draft_fingerprint': draft['fingerprint'], 'sample_input': {'term': 'owner'},
    })
    assert response.status_code == 201, response.text
    a = response.json()
    response = client.post('/api/internal/approvals/' + a['id'] + '/commit', json={'fingerprint': a['fingerprint']})
    assert response.status_code == 200, response.text
    return response.json()


def recover_stale(data, instance, accepted):
    current = author.state(data, instance, accepted['request_key'])
    assert current['owner_acceptance'] == 'STALE', current
    assert current['sequence'] == accepted['sequence']
    assert current['content_access'] is False and 'record' not in current and 'current' not in current
    assert current['recovered']['id'] == accepted['id']
    assert current['recovered']['status'] == 'ACCEPTED'
    assert 'payload' not in current['recovered']
    assert current['formal_publication_enabled'] is False
    assert current['technical_semantic_status'] == 'UNKNOWN'
    return current


@pytest.mark.parametrize('stage', ['prepared', 'accepted'])
def test_goal_head_real_http_aba(env, stage):
    data, release, instance, job = author.flow(env)
    if stage == 'accepted':
        review, accepted, body = accept(data, release, instance, job)
    else:
        review, _ = author.prepare(data, release, instance, job)
        body = author.choice_body(review)
    original = copy.deepcopy(data[-1]['content'])
    middle = edit_goal(data, {**original, 'title': 'Independent B'}, data[-1]['version'])
    restored = edit_goal(data, original, middle['version'])
    assert restored['content'] == original
    assert restored['version'] == data[-1]['version'] + 2
    assert author.state(data, instance)['owner_acceptance'] == 'STALE'
    if stage == 'accepted':
        recover_stale(data, instance, accepted)
        replay = data[2].post(author.path(instance) + '-requests', json=body)
        assert replay.status_code == 201 and replay.json()['record']['id'] == accepted['id']
        recover_stale(data, instance, accepted)
    else:
        rejected = data[2].post(author.path(instance) + '-requests', json=body)
        assert rejected.status_code == 409, rejected.text
        assert author.state(data, instance, 'prepare')['recovered']['id'] == review['id']
        assert author.state(data, instance)['sequence'] == 1


@pytest.mark.parametrize('stage', ['prepared', 'accepted'])
def test_real_instance_release_switch_aba(env, stage):
    data, release, instance, job = author.flow(env)
    if stage == 'accepted':
        review, accepted, body = accept(data, release, instance, job)
    else:
        review, _ = author.prepare(data, release, instance, job)
        body = author.choice_body(review)
    alternate = second_release(data, instance)
    assert alternate['fingerprint'] != release['fingerprint']
    b = switch(data, instance, alternate, 1)
    a = switch(data, instance, release, 2)
    assert b['revision'] == 2 and a['revision'] == 3
    assert a['release_id'] == release['id']
    assert author.state(data, instance)['owner_acceptance'] == 'STALE'
    if stage == 'accepted':
        recover_stale(data, instance, accepted)
    else:
        denied = data[2].post(author.path(instance) + '-requests', json=body)
        assert denied.status_code == 400, denied.text
        assert denied.json()['error']['code'] == 'VERIFICATION_FAILED'
        assert author.state(data, instance)['sequence'] == 1


@pytest.mark.parametrize('mutation', ['unknown_op', 'cancel_intent', 'job_error', 'app_error', 'output'])
def test_accepted_evidence_stale_exact_key_cannot_restore(env, mutation):
    data, release, instance, job = author.flow(env)
    _, accepted, body = accept(data, release, instance, job)
    store = data[0]
    with store.tx() as c:
        if mutation == 'unknown_op':
            c.execute(update(operations).where(operations.c.run_id == job['id']).values(status='OUTCOME_UNKNOWN'))
        elif mutation == 'cancel_intent':
            c.execute(update(runs).where(runs.c.id == job['id']).values(cancel_intent=True))
        elif mutation == 'job_error':
            c.execute(update(runs).where(runs.c.id == job['id']).values(error={'code': 'INDEPENDENT_CONTROLLED_ERROR'}))
        elif mutation == 'app_error':
            c.execute(update(internal_app_runs).where(internal_app_runs.c.instance_id == instance['id']).values(error={'code': 'INDEPENDENT_CONTROLLED_ERROR'}))
        else:
            c.execute(update(internal_app_runs).where(internal_app_runs.c.instance_id == instance['id']).values(output={}))
    recover_stale(data, instance, accepted)
    replay = data[2].post(author.path(instance) + '-requests', json=body)
    assert replay.status_code == 201 and replay.json()['record']['id'] == accepted['id']
    recover_stale(data, instance, accepted)


@pytest.mark.parametrize('command', ['CANCEL', 'REVOKE'])
def test_stop_after_revocation_reads_only_owner_metadata(env, command):
    data, release, instance, job = author.flow(env)
    if command == 'REVOKE':
        _, target, _ = accept(data, release, instance, job)
    else:
        target, _ = author.prepare(data, release, instance, job)
    store, _, client, user, pid, source, _ = data
    with store.tx() as c:
        c.execute(update(grants).where(
            grants.c.project_id == pid, grants.c.principal_id == user, grants.c.resource_id == source,
        ).values(revoked=True, revision=2))
    statements = []
    def observe(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(store.engine, 'before_cursor_execute', observe)
    try:
        response = client.post(author.path(instance) + '-requests', json={
            'command': command, 'request_key': 'independent-stop',
            'expected_sequence': target['sequence'], 'target_id': target['id'],
            'target_fingerprint': target['fingerprint'], 'reason': 'SIMULATED stopping after revoke',
        })
    finally:
        event.remove(store.engine, 'before_cursor_execute', observe)
    (OUT / ('metadata-' + command.lower() + '-sql.json')).write_text(json.dumps(statements, indent=2) + '\n')
    assert response.status_code == 201, response.text
    reads = [s.lower() for s in statements if s.lstrip().upper().startswith('SELECT')]
    assert reads and all('internal_owner_records.payload' not in s for s in reads)
    assert all('from runs' not in s and 'from resources' not in s and 'from run_contracts' not in s for s in reads)
    current = author.state(data, instance, 'independent-stop')
    assert current['owner_acceptance'] == ('CANCELLED' if command == 'CANCEL' else 'REVOKED')
    assert not current['content_access'] and 'payload' not in current['recovered']
    assert current['sequence'] == target['sequence'] + 1


@pytest.mark.parametrize('kind', ['other_instance', 'generation_run', 'missing'])
def test_prepare_foreign_or_non_app_run_is_denied(env, kind):
    data, release, instance, job = author.flow(env)
    client = data[2]
    if kind == 'other_instance':
        response = client.post('/api/internal/releases/' + release['id'] + '/instances', json={
            'expected_release_fingerprint': release['fingerprint'], 'request_key': 'independent-second-instance',
        })
        assert response.status_code == 201, response.text
        other = response.json()
        wrong = run_input(data, release, other, {'term': 'Beta'}, 'independent-foreign-job')['id']
    elif kind == 'generation_run':
        wrong = release['snapshot']['draft']['candidate']['goal_application']['run_id']
    else:
        wrong = 'run_nonexistent_independent'
    response = client.post(author.path(instance) + '-requests', json={
        'command': 'PREPARE', 'request_key': 'independent-foreign', 'expected_sequence': 0,
        'expected_revision': 1, 'expected_release_fingerprint': release['fingerprint'], 'run_ids': [wrong],
    })
    assert response.status_code == 403, response.text
    assert author.state(data, instance)['sequence'] == 0
    assert author.state(data, instance)['owner_acceptance'] == 'PENDING'


@pytest.mark.parametrize('table,position', [('record', 'first'), ('seal', 'first'), ('record', 'last'), ('seal', 'last')])
def test_one_sided_anchor_loss_denies_read_and_stop(env, table, position):
    data, release, instance, job = author.flow(env)
    review, accepted, _ = accept(data, release, instance, job)
    newer, _ = author.prepare(data, release, instance, job, key='independent-new-review')
    target = review if position == 'first' else newer
    with data[0].tx() as c:
        if table == 'record':
            c.execute(delete(internal_owner_records).where(internal_owner_records.c.id == target['id']))
        else:
            c.execute(delete(internal_owner_seals).where(internal_owner_seals.c.record_id == target['id']))
    assert data[2].get(author.path(instance), params={'request_key': accepted['request_key']}).status_code == 409
    stop = data[2].post(author.path(instance) + '-requests', json={
        'command': 'CANCEL', 'request_key': 'stop-after-loss', 'expected_sequence': 3,
        'target_id': newer['id'], 'target_fingerprint': newer['fingerprint'], 'reason': 'SIMULATED',
    })
    assert stop.status_code == 409, stop.text


@pytest.mark.parametrize('stop', ['CANCEL', 'REVOKE'])
def test_old_key_after_stop_and_new_prepare_never_restores_acceptance(env, stop):
    data, release, instance, job = author.flow(env)
    review, _ = author.prepare(data, release, instance, job)
    old_body = author.choice_body(review)
    target = review
    if stop == 'REVOKE':
        response = data[2].post(author.path(instance) + '-requests', json=old_body)
        assert response.status_code == 201
        target = response.json()['record']
    response = data[2].post(author.path(instance) + '-requests', json={
        'command': stop, 'request_key': 'stopped', 'expected_sequence': target['sequence'],
        'target_id': target['id'], 'target_fingerprint': target['fingerprint'], 'reason': 'SIMULATED',
    })
    assert response.status_code == 201, response.text
    before_sequence = response.json()['record']['sequence']
    newest, _ = author.prepare(data, release, instance, job, key='new-review')
    assert newest['sequence'] == before_sequence + 1
    if stop == 'REVOKE':
        recovered = author.state(data, instance, 'decision')
        assert recovered['recovered']['id'] == target['id'] and recovered['recovered']['status'] == 'ACCEPTED'
        replay = data[2].post(author.path(instance) + '-requests', json=old_body)
        assert replay.status_code == 201 and replay.json()['record']['id'] == target['id']
    else:
        late = data[2].post(author.path(instance) + '-requests', json=old_body)
        assert late.status_code == 409, late.text
    assert author.state(data, instance)['owner_acceptance'] == 'PENDING'
    assert author.state(data, instance)['sequence'] == newest['sequence']


def test_actual_release_sample_input_cannot_be_owner_new_input(env):
    data, release, instance, _ = author.flow(env)
    job = run_input(data, release, instance, {'term': 'Alpha'}, 'same-as-release-sample')
    assert job['status'] == 'SUCCEEDED'
    response = data[2].post(author.path(instance) + '-requests', json={
        'command': 'PREPARE', 'request_key': 'reject-sample', 'expected_sequence': 0,
        'expected_revision': 1, 'expected_release_fingerprint': release['fingerprint'], 'run_ids': [job['id']],
    })
    assert response.status_code == 400, response.text
    assert response.json()['error']['code'] == 'VERIFICATION_FAILED'
    assert author.state(data, instance)['sequence'] == 0
