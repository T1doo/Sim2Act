"""Read recovery uses real authorized HTTP and never mutates persisted task state."""
import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import attempts, events, grants, operations, principals, runs
from sim2act.worker import Worker


def test_task_read_failure_actual_http(env, tmp_path):
    store, settings, client, owner, other_owner, project, resource = env
    if not shutil.which('node'):
        pytest.skip('Developer Node required for HTTP/DOM integration')
    probe = subprocess.run(['node', '-e', "require.resolve('jsdom')"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    if probe.returncode:
        pytest.skip('Developer jsdom required for HTTP/DOM integration')
    first = client.post(f'/api/projects/{project}/runs', json={
        'goal': 'Read recovery verified receipt', 'resource_refs': [resource], 'request_key': 'read-first',
    })
    assert first.status_code == 202
    assert Worker(store, settings).once()
    first_id = first.json()['run_id']
    received = client.get('/api/runs/' + first_id).json()
    assert received['status'] == 'PARTIAL' and received['result']['mode'] == 'MOCK'
    second = client.post(f'/api/projects/{project}/runs', json={
        'goal': 'Second queued task', 'resource_refs': [resource], 'request_key': 'read-second',
    })
    assert second.status_code == 202
    other = store.project(owner, 'Other owned project')
    foreign = store.project(other_owner, 'Other identity project')
    foreign_run = client.post(f'/api/projects/{foreign}/runs', headers={
        'Authorization': 'Bearer synthetic-test-B',
    }, json={'goal': 'Foreign task must remain private', 'resource_refs': [], 'request_key': 'foreign'})
    assert foreign_run.status_code == 202
    assert client.get('/api/runs/' + foreign_run.json()['run_id']).status_code == 403

    def snapshot():
        with store.tx() as connection:
            return {name: [dict(row) for row in connection.execute(select(table)).mappings()]
                    for name, table in [('runs', runs), ('attempts', attempts), ('operations', operations),
                                        ('events', events), ('grants', grants), ('principals', principals)]}

    before = snapshot()
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    (tmp_path / 'info.json').write_text(json.dumps({
        'base': f'http://127.0.0.1:{port}', 'project': project, 'other': other,
        'first': first_id, 'second': second.json()['run_id'], 'foreign': foreign_run.json()['run_id'],
    }))
    server = uvicorn.Server(uvicorn.Config(create_app(store, settings), host='127.0.0.1', port=port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < deadline
            time.sleep(.02)
        result = subprocess.run(['node', 'tests/task_read_failure.cjs', str(tmp_path)],
                                capture_output=True, text=True, timeout=45)
        (tmp_path / 'driver.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        data = json.loads((tmp_path / 'results.json').read_text())
        assert data['status'] == 'PASS' and data['non_get_requests'] == 0
        assert snapshot() == before  # Full rows, not only counts: no commands/attempts/authorization changes.
    finally:
        server.should_exit = True
        thread.join(8)
        assert not thread.is_alive()
