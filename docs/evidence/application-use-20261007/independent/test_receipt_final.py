import sys
sys.path.insert(0,'/workspace/Sim2Act-application-use/tests')
from conftest import env
"""Existing CSV instance -> business parameter -> normal persisted worker -> cold history."""
import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import select
from test_internal_lifecycle import release

from sim2act.api import create_app
from sim2act.db import app_drafts, grants, internal_app_runs, internal_instance_data, principals
from sim2act.lifecycle import create_instance
from sim2act.worker import Worker


def test_mismatched_accepted_receipt_stays_locked(env, tmp_path):
    store, settings, client, owner, other_owner, project, _ = env
    if not shutil.which('node'):
        pytest.skip('Developer Node required')
    if subprocess.run(['node', '-e', "require.resolve('jsdom')"], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, timeout=10).returncode:
        pytest.skip('Developer jsdom required')
    resource = client.post(f'/api/projects/{project}/resources', json={
        'name': 'synthetic-use.csv', 'format': 'csv', 'content': 'amount,tax,memo\n5,1,x\n7,2,y\n',
    }).json()['id']
    app_id = client.post(f'/api/projects/{project}/apps/csv-preview', json={
        'name': 'Saved synthetic sum', 'resource_id': resource, 'goal': 'Sum either numeric column',
    }).json()['id']
    with store.tx() as c:
        fp = c.execute(select(app_drafts.c.fingerprint).where(app_drafts.c.id == app_id)).scalar_one()
    from test_internal_lifecycle import limits
    rel, _, _ = release(env, app_id, fp)
    instance = create_instance(store, owner, rel['id'], rel['fingerprint'], limits(env), request_key='existing-use-instance')
    other = store.project(owner, 'Other owned project')
    store.project(other_owner, 'Other identity project')
    with store.tx() as c:
        before = {name: [dict(r) for r in c.execute(select(table)).mappings()]
                  for name, table in [('grants', grants), ('principals', principals)]}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    (tmp_path / 'info.json').write_text(json.dumps({'base': f'http://127.0.0.1:{port}',
        'project': project, 'other': other, 'app': app_id, 'instance': instance['id']}))
    app = create_app(store, settings)

    @app.post('/test-only-worker')
    def work():
        class NoProvider:
            def complete(self, *_args, **_kwargs):
                raise AssertionError('No model allowed')
        assert Worker(store, settings, NoProvider()).once()
        return {'test_only': True}

    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < end
            time.sleep(.01)
        outcome = subprocess.run(['node', '/tmp/sim2act-app-use-independent/receipt-final-driver.cjs', str(tmp_path)], capture_output=True, text=True, timeout=45)
        (tmp_path / 'driver.log').write_text(outcome.stdout + outcome.stderr)
        assert outcome.returncode == 0, outcome.stdout + outcome.stderr
        result = json.loads((tmp_path / 'results.json').read_text())
        assert result['status'] == 'PASS'
        with store.tx() as c:
            for name, table in [('grants', grants), ('principals', principals)]:
                assert [dict(r) for r in c.execute(select(table)).mappings()] == before[name]
            assert len(c.execute(select(internal_app_runs)).all()) == 1
            assert len(c.execute(select(internal_instance_data)).all()) == 0
    finally:
        server.should_exit = True
        thread.join(8)
        assert not thread.is_alive()
