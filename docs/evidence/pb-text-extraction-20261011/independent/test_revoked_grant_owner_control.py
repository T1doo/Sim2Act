"""Actual resource grant revocation must preserve owner stop controls, LIVE0."""
import json, os
from pathlib import Path
from sqlalchemy import select
from test_registered_text_extraction import prepared, request, release_instance
from sim2act.db import runs, internal_app_runs, internal_instance_data, attempts, operations
from sim2act.worker import Worker

OUT = Path('/tmp/pb-text-extraction-review-20261011')

def test_owner_can_stop_extracted_run_after_actual_grant_revocation(env):
    data, _, _, _, _, target, _, url = prepared(env)
    _, body = request(data, url, target)
    accepted = data[2].post(url + '/extract', json=body)
    assert accepted.status_code == 201, accepted.text
    release, instance = release_instance(data, accepted.json()['id'])
    base = '/api/internal/instances/' + instance['id']
    queued = data[2].post(base + '/runs', json={
        'expected_revision': instance['revision'],
        'expected_release_fingerprint': release['fingerprint'],
        'input': {'term': 'Gamma'}, 'request_key': 'independent-after-revoke-stop',
    })
    assert queued.status_code == 202, queued.text
    rid = queued.json()['run_id']; base += '/runs/' + rid
    target_app = data[2].get('/api/apps/' + target).json()
    grant = next(g for g in data[2].get('/api/projects/' + data[4] + '/grants').json()
                 if g['principal_id'] == target_app['runtime_id'] and not g['revoked'])
    revoked = data[2].post('/api/grants/' + grant['id'] + '/revoke',
                          json={'command': 'revoke', 'version': grant['revision']})
    assert revoked.status_code == 200, revoked.text
    status = data[2].get(base + '/control-status')
    assert status.status_code == 200, status.text
    assert status.json()['content_access'] is False
    assert status.json()['status'] == 'QUEUED'
    cancelled = data[2].post(base + '/commands', json={
        'command': 'cancel', 'version': status.json()['version'],
    })
    assert cancelled.status_code == 200, cancelled.text
    current = data[2].get(base + '/control-status')
    assert current.status_code == 200, current.text
    assert current.json()['status'] == 'CANCELLED' and current.json()['cancel_intent'] is True
    worker_selected = Worker(data[0], data[1]).once()
    with data[0].tx() as c:
        job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        actual = dict(c.execute(select(internal_app_runs).where(internal_app_runs.c.id == queued.json()['app_run_id'])).mappings().one())
        records = list(c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == instance['id'])))
        attempt_ids = list(c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).scalars())
        op_ids = list(c.execute(select(operations.c.id).where(operations.c.run_id == rid)).scalars())
    assert job['status'] == actual['status'] == 'CANCELLED'
    assert job['result'] is None and actual['output'] is None
    assert not records and not attempt_ids and not op_ids
    p = OUT / (os.environ.get('PB_CONTROL_PREFIX', 'candidate3-') + 'revoked-grant-owner-stop.json')
    assert not p.exists()
    p.write_text(json.dumps({
        'classification': 'ACTUAL_SQLITE_AUTHENTICATED_API_NORMAL_WORKER',
        'grant_revoke': {'status': revoked.status_code, 'body': revoked.json()},
        'control_before': {'status': status.status_code, 'body': status.json()},
        'cancel': {'status': cancelled.status_code, 'body': cancelled.json()},
        'control_after': {'status': current.status_code, 'body': current.json()},
        'worker_once_selected': worker_selected,
        'worker_source_status': job['status'], 'app_run_status': actual['status'],
        'output_is_none': actual['output'] is None, 'result_is_none': job['result'] is None,
        'data_record_count': len(records), 'attempt_count': len(attempt_ids), 'operation_count': len(op_ids),
        'scope': 'Queued extracted run after actual target resource grant revoke; owner metadata stop remains available. No claim all SQL reads are private-cell-free for the authorized owner.',
        'real_model': 'NOT_RUN', 'native_browser': 'NOT_RUN',
    }, ensure_ascii=False, indent=2) + '\n')
