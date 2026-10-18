"""Non-author bounded actual NoModel run and original-key integrity readback."""
import hashlib
import json
from pathlib import Path
import time

from fastapi.testclient import TestClient
from sqlalchemy import delete, insert, select

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, fingerprint, internal_instance_data, meta, operations
from sim2act.worker import Worker

HERE = Path(__file__).parent
store = Store('sqlite:///' + str(HERE / 'fixture.db'), test_only=True)
store.initialize()
store.user('synthetic independent', 'synthetic-independent-local-record')
settings = Settings('sqlite:///' + str(HERE / 'fixture.db'), HERE, mode='mock')
client = TestClient(create_app(store, settings))
client.headers['Authorization'] = 'Bearer synthetic-independent-local-record'
trace, results = [], []

def call(method, path, body=None, expected=200):
    response = client.request(method, path, json=body)
    trace.append({'method': method, 'path': path, 'request': body,
        'status': response.status_code, 'response': response.text})
    assert response.status_code == expected, response.text
    return response.json()

def snapshot():
    with store.tx() as c:
        return {table.name: sorted((dict(row) for row in c.execute(select(table)).mappings()),
            key=fingerprint) for table in meta.sorted_tables}

class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError('No model call authorized')

started = time.monotonic()
try:
    project = call('POST', '/api/projects', {'name': 'Synthetic integrity probe'}, 200)['id']
    app = call('POST', f'/api/projects/{project}/record-apps', {
        'name': 'Synthetic local records', 'goal': 'Store and re-read a typed record',
        'consent': 'SAVE_LOCAL_RECORD_FORM', 'request_key': 'independent-app'}, 201)
    approval = call('POST', f"/api/apps/{app['id']}/record-release-approvals", {
        'expected_definition_fingerprint': app['fingerprint'], 'request_key': 'freeze',
        'consent': 'FREEZE_RECORD_FORM_AND_WRITE_BOUNDARY'}, 201)
    release = call('POST', f"/api/apps/{app['id']}/record-release-requests/freeze/commit", {
        'fingerprint': approval['approval']['fingerprint']})['release']
    instance = call('POST', f"/api/internal/record-releases/{release['id']}/instances", {
        'expected_release_fingerprint': release['fingerprint'], 'request_key': 'instance'}, 201)['instance']
    path = f"/api/internal/record-instances/{instance['id']}"
    preview = call('POST', path + '/previews', {
        'command': 'CREATE', 'request_key': 'original-create', 'expected_revision': 1,
        'expected_data_version': 0, 'expected_release_fingerprint': release['fingerprint'],
        'title': 'Independent original-key proof', 'details': 'Synthetic stored record'}, 201)
    accepted = call('POST', path + '/previews/original-create/commit', {
        'expected_preview_fingerprint': preview['preview_fingerprint'],
        'consent': 'WRITE_THIS_EXACT_LOCAL_RECORD_EVENT'}, 202)
    assert Worker(store, settings, NoModel()).once()
    original = call('GET', path + '/record-requests/original-create')
    assert original['run']['status'] == 'SUCCEEDED'
    actual = call('GET', path)
    assert len(actual['records']) == 1 and actual['records'][0]['state'] == 'OPEN'
    with store.tx() as c:
        typed = dict(c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == instance['id'])).mappings().one())
        operation = dict(c.execute(select(operations).where(
            operations.c.run_id == accepted['run']['run_id'])).mappings().one())
    baseline = snapshot()
    for name, table, column, identity, row in [
        ('missing_typed_event', internal_instance_data, internal_instance_data.c.run_id, typed['run_id'], typed),
        ('missing_operation', operations, operations.c.id, operation['id'], operation),
    ]:
        with store.tx() as c:
            c.execute(delete(table).where(column == identity))
        try:
            before_get = snapshot()
            error = call('GET', path + '/record-requests/original-create', expected=409)
            assert error['error']['code'] == 'VERSION_CONFLICT'
            assert snapshot() == before_get
            results.append({'fault': name, 'status': 'PASS', 'http': 409,
                'error': error['error']['code'], 'original_key_read_only': True})
        finally:
            with store.tx() as c:
                c.execute(insert(table).values(**row))
        assert snapshot() == baseline
    result = {'classification': 'NON_AUTHOR_ACTUAL_ISOLATED_SQLITE_NORMAL_NOMODEL_WORKER_BOUNDED_PROBE',
        'status': 'PASS', 'actual_worker_runs': 1, 'model_requests': 0,
        'mutations': results, 'original_key': 'original-create',
        'accepted': accepted, 'original_successful_recovery': original,
        'restored_all_fixture_rows_exact': True,
        'source_module_sha256': hashlib.sha256(Path(__import__('sim2act.local_record_apps', fromlist=['x']).__file__).read_bytes()).hexdigest(),
        'elapsed_seconds': time.monotonic() - started}
except BaseException as error:
    result = {'status': 'FAIL', 'error': repr(error), 'mutations': results,
        'elapsed_seconds': time.monotonic() - started}
    raise
finally:
    (HERE / 'recovery-probe-http.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2) + '\n')
    (HERE / 'recovery-probe-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    client.close()
    store.engine.dispose()
print(json.dumps({k: v for k, v in result.items() if k not in {'accepted', 'original_successful_recovery'}}, indent=2))
