"""Real controller + three real local backend GETs; no native browser/model."""

import json
import os
import socket
import subprocess
import threading
import time

import uvicorn

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store


def test_api_response_feedback_actual_local_backend(tmp_path, monkeypatch):
    from sim2act.model import InternModel
    from sim2act.worker import Worker

    def forbidden(*args, **kwargs):
        raise AssertionError('API feedback test cannot run Worker or models')

    monkeypatch.setattr(Worker, '__init__', forbidden)
    monkeypatch.setattr(InternModel, '__init__', forbidden)
    url = 'sqlite:///' + str(tmp_path / 'feedback.db')
    store = Store(url, test_only=True)
    store.initialize()
    actor = store.user('synthetic feedback actor', 'synthetic-response-actor')
    project = store.project(actor, 'API feedback fixture')
    settings = Settings(url, tmp_path, mode='mock')
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(store, settings),
        host='127.0.0.1', port=port, log_level='error', timeout_graceful_shutdown=2))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        info = tmp_path / 'info.json'
        info.write_text(json.dumps({'base': f'http://127.0.0.1:{port}', 'project': project}))
        result = subprocess.run(['node', 'tests/api_response_feedback.cjs',
            'src/sim2act/web/app.js', str(info)], capture_output=True, text=True,
            timeout=15, env=os.environ.copy())
        (tmp_path / 'driver.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        assert report['status'] == 'PASS' and report['actual_http'] is True
        assert report['models'] == 0 and report['native_browser'] is False
    finally:
        server.should_exit = True
        thread.join(timeout=3)
        sock.close()
        store.engine.dispose()
        assert not thread.is_alive(), 'owned local API must stop normally'


def test_goal_execution_unreadable_receipt_keeps_original_key(tmp_path):
    result = subprocess.run(['node', 'tests/goal_card_run_ui.cjs', str(tmp_path),
        'API_FAULT'], capture_output=True, text=True, timeout=15, env=os.environ.copy())
    (tmp_path / 'driver.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / 'results.json').read_text())
    assert report['status'] == 'PASS' and len(report['checks']) == 32
