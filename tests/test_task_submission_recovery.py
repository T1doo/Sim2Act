"""Submission recovery through real loopback HTTP, optional protected Chromium."""
import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import func, select

from sim2act.api import create_app
from sim2act.db import attempts, grants, principals, runs
from sim2act.worker import Worker


@pytest.mark.parametrize('engine', ['dom', 'chromium'])
def test_task_submission_recovery_real_http(env, tmp_path, engine):
    store, settings, client, owner, _, project, resource = env
    if not shutil.which('node'):
        pytest.skip('Node required for UI integration')
    dependency = 'jsdom' if engine == 'dom' else 'playwright-core'
    probe = subprocess.run(['node', '-e', f"require.resolve('{dependency}')"], capture_output=True)
    if probe.returncode:
        pytest.skip(f'{dependency} must be available in developer NODE_PATH')
    other = store.project(owner, 'Other owned project')
    with store.tx() as connection:
        before = {
            name: connection.execute(select(func.count()).select_from(table)).scalar_one()
            for name, table in [('grants', grants), ('principals', principals)]
        }
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    info = {'base': f'http://127.0.0.1:{port}', 'project': project, 'other': other, 'resource': resource}
    (tmp_path / 'info.json').write_text(json.dumps(info))
    server = uvicorn.Server(uvicorn.Config(create_app(store, settings), host='127.0.0.1', port=port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    worker_stop = threading.Event()
    worker_errors = []

    def controlled_worker():
        while not worker_stop.wait(.02):
            if (tmp_path / 'worker-once-request').exists():
                try:
                    assert Worker(store, settings).once()
                except Exception as error:
                    worker_errors.append(type(error).__name__)
                return

    worker_thread = threading.Thread(target=controlled_worker, daemon=True)
    worker_thread.start()
    try:
        deadline = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < deadline
            time.sleep(.02)
        result = subprocess.run(['node', 'tests/task_submission_recovery.cjs', str(tmp_path), engine], capture_output=True, text=True, timeout=90)
        (tmp_path / 'driver.log').write_text(result.stdout + result.stderr)
        if result.returncode == 77:
            pytest.skip('Protected Chromium sandbox startup blocked; actual stderr retained in driver.log')
        assert result.returncode == 0, result.stdout + result.stderr
        data = json.loads((tmp_path / 'results.json').read_text())
        assert data['status'] == 'PASS' and len(data['checks']) >= 20
        with store.tx() as connection:
            assert connection.execute(select(func.count()).select_from(runs)).scalar_one() == data['accepted_runs']
            assert connection.execute(select(func.count()).select_from(attempts)).scalar_one() == data['mock_attempts']
            assert not worker_errors
            for name, table in [('grants', grants), ('principals', principals)]:
                assert connection.execute(select(func.count()).select_from(table)).scalar_one() == before[name]
    finally:
        worker_stop.set()
        worker_thread.join(8)
        assert not worker_thread.is_alive()
        server.should_exit = True
        thread.join(8)
        assert not thread.is_alive()
