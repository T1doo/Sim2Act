"""Manual actual large writer cancellation through loopback HTTP, no live model."""
import json
import socket
import sqlite3
import threading
import time
import traceback
from urllib.request import Request, urlopen

import uvicorn
from sim2act.api import create_app
from sim2act.worker import Worker
from sim2act import _lease_control_runtime as adapter
from sim2act.db import Store
from test_authoritative_cold_full_flow import test_large_original_thirty_authoritative_flow as complete


def test_actual_large_writer_cancel_reconciles_without_effect_or_replay(env, tmp_path, monkeypatch):
    finished = threading.Event()
    outcome, errors = {}, []
    database = env[0].engine.url.database
    def observe():
        server = None
        thread = None
        try:
            until = time.monotonic()+660
            while not finished.wait(.04):
                assert time.monotonic() < until, "Bounded large writer observation ended"
                with sqlite3.connect('file:'+database+'?mode=ro', uri=True, timeout=.1) as c:
                    selected = c.execute("""SELECT r.id,r.version,a.instance_id FROM runs r
                        JOIN internal_run_bindings b ON b.run_id=r.id JOIN internal_app_runs a ON a.id=b.app_run_id
                        WHERE r.status='RUNNING' AND EXISTS(SELECT 1 FROM runs prior
                          WHERE prior.status='SUCCEEDED' AND prior.created_at<r.created_at)
                        AND EXISTS(SELECT 1 FROM attempts x WHERE x.run_id=r.id AND x.status='RECEIVED')""").fetchone()
                if selected is None:
                    continue
                rid, version, iid = selected
                probe = sqlite3.connect(database, timeout=.01, isolation_level=None)
                try:
                    probe.execute('BEGIN IMMEDIATE')
                    probe.rollback()
                    continue
                except sqlite3.OperationalError as error:
                    assert error.sqlite_errorcode == sqlite3.SQLITE_BUSY
                finally:
                    probe.close()
                # A real BEGIN IMMEDIATE conflict proves the business writer
                # is held; no worker/graph method or clock is replaced.
                stores = [s for s in adapter._RUNTIMES if s.engine.url == env[0].engine.url
                    and any(h[0] == rid for h in s._authoritative_lease_runtime.authority.sessions)]
                assert len(stores) == 1
                store = stores[0]
                listener = socket.socket()
                listener.bind(('127.0.0.1', 0)); listener.listen(128)
                base = 'http://127.0.0.1:'+str(listener.getsockname()[1])
                server = uvicorn.Server(uvicorn.Config(create_app(store, env[1]), log_level='error', access_log=False))
                thread = threading.Thread(target=server.run, kwargs={'sockets':[listener]}, daemon=True)
                thread.start()
                ready = time.monotonic()+5
                while not server.started:
                    assert thread.is_alive() and time.monotonic() < ready
                    finished.wait(.01)
                path = base+f'/api/internal/instances/{iid}/runs/{rid}'
                headers = {'Authorization':'Bearer synthetic-test-A','Content-Type':'application/json'}
                started = time.monotonic()
                with urlopen(Request(path+'/control-progress', headers=headers), timeout=8) as reply:
                    progress = json.load(reply)
                outcome['progress_seconds'] = time.monotonic()-started
                assert progress['status'] == 'RUNNING' and not progress['content_access']
                started = time.monotonic()
                with urlopen(Request(path+'/commands', data=json.dumps(dict(command='cancel', version=version)).encode(),
                    headers=headers, method='POST'), timeout=12) as reply:
                    value = json.load(reply)
                    outcome['http_status'] = reply.status
                outcome.update(cancel_seconds=time.monotonic()-started, reply=value, run_id=rid, instance_id=iid,
                    observed_phase='ACTUAL_SQLITE_BUSINESS_WRITER_LOCK', store=store)
                (tmp_path/'authoritative-cancel-request.json').write_text(json.dumps(
                    {k:v for k,v in outcome.items() if k != 'store'}, indent=2)+'\n')
                assert value['status'] in {'RECONCILING', 'CANCEL_REQUESTED'}
                break
        except BaseException:
            errors.append(traceback.format_exc())
        finally:
            if server is not None: server.should_exit = True
            if thread is not None:
                thread.join(5)
                if thread.is_alive(): errors.append('Owned loopback server did not exit')
    observer = threading.Thread(target=observe, daemon=True)
    observer.start()
    divergence = None
    try:
        try: complete(env, tmp_path, monkeypatch)
        except AssertionError as error: divergence = str(error)
    finally:
        finished.set(); observer.join(15)
    assert not observer.is_alive() and not errors, errors
    assert divergence is not None and outcome.get('http_status') == 200, (divergence, outcome)
    outcome.pop('store')  # The original controller has disposed its Store.
    store = Store(env[1].database_url, test_only=True)
    store._enable_authoritative_leases(env[1], create=False)
    with store.engine.connect() as c:
        assert c.exec_driver_sql('SELECT count(*) FROM internal_instance_data WHERE instance_id=?',
                                (outcome['instance_id'],)).scalar_one() == 0
    Worker(store, env[1]).once()
    with store.engine.connect() as c:
        assert c.exec_driver_sql('SELECT status FROM runs WHERE id=?', (outcome['run_id'],)).scalar_one() == 'CANCELLED'
        assert c.exec_driver_sql("SELECT count(*) FROM attempts WHERE run_id=? AND status='REJECTED_KNOWN'",
                                (outcome['run_id'],)).scalar_one() == 1
        assert c.exec_driver_sql('SELECT count(*) FROM internal_instance_data WHERE instance_id=?',
                                (outcome['instance_id'],)).scalar_one() == 0
        assert c.exec_driver_sql("SELECT count(*) FROM events WHERE run_id=? AND kind='NS_SETTLED'",
                                (outcome['run_id'],)).scalar_one() == 0
    assert Worker(store, env[1]).once() is False
    assert len((tmp_path/'mock-exchanges.jsonl').read_text().splitlines()) == 6
    outcome.update(terminal='CANCELLED', new_recovery_model_calls=0, business_effects=0, real_model_calls=0,
                   original_lease_seconds=30, divergence=divergence)
    (tmp_path/'authoritative-cancel-result.json').write_text(json.dumps(outcome, indent=2)+'\n')
    store.engine.dispose()
