"""A finite real local read-only API chain for the grant directory controller."""
import json
import os
import socket
import subprocess
import threading
import time
from collections import Counter

import uvicorn
from sqlalchemy import event, select

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, grants


def test_grant_directory_actual_backend(tmp_path, monkeypatch):
    from sim2act.model import InternModel
    from sim2act.worker import Worker

    def forbidden(*args, **kwargs):
        raise AssertionError('No Worker or model is allowed in this read-only test')

    monkeypatch.setattr(Worker, '__init__', forbidden)
    monkeypatch.setattr(InternModel, '__init__', forbidden)
    url = 'sqlite:///' + str(tmp_path / 'grants.db')
    store = Store(url, test_only=True)
    store.initialize()
    owner_a = store.user('synthetic grant A', 'grant-owner-a')
    owner_b = store.user('synthetic grant B', 'grant-owner-b')
    project_a = store.project(owner_a, 'Grant fixture A')
    project_b = store.project(owner_b, 'Grant fixture B')
    store.resource(owner_a, project_a, 'synthetic text', 'txt', 'synthetic material only')
    with store.engine.connect() as c:
        before = [dict(x) for x in c.execute(select(grants).order_by(grants.c.id)).mappings()]
    app = create_app(store, Settings(url, tmp_path, mode='mock'))
    verbs = Counter()

    def record(c, cursor, statement, parameters, context, many):
        verbs[statement.split()[0].upper()] += 1

    event.listen(store.engine, 'before_cursor_execute', record)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', timeout_graceful_shutdown=2))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        info = tmp_path / 'info.json'
        info.write_text(json.dumps({'base': f'http://127.0.0.1:{port}', 'projectA': project_a,
                                   'projectB': project_b, 'grantCount': len(before)}))
        result = subprocess.run(['node', 'tests/grant_directory_http.cjs', str(info)],
                                capture_output=True, text=True, timeout=15, env=os.environ.copy())
        (tmp_path / 'driver.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        assert report['status'] == 'PASS' and len(report['requests']) == 3
        with store.engine.connect() as c:
            after = [dict(x) for x in c.execute(select(grants).order_by(grants.c.id)).mappings()]
        assert before == after
        assert not set(verbs) & {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'REPLACE'}
        (tmp_path / 'sql.json').write_text(json.dumps(dict(verbs), indent=2))
    finally:
        server.should_exit = True
        thread.join(timeout=3)
        sock.close()
        store.engine.dispose()
        assert not thread.is_alive(), 'owned API must stop normally'
