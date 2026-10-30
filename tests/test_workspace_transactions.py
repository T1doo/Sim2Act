"""Real SQLite transactions and HTTP/ordinary spec Worker; no delayed fake work."""

import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError, TimeoutError as PoolTimeout
from test_pa_spec_apps import SOURCE, confirm, generate, instance, material

from sim2act import synthetic_workspace as workspace
from sim2act.db import Store, WorkspaceWriterAdmissionTimeout, internal_instance_data, internal_instances, operations, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def test_workspace_writer_timeout_rollback_and_pragma_restore(tmp_path):
    _, store, _ = workspace.open_workspace(tmp_path/'gate', new=True)
    gate = store._workspace_writer_gate
    with store.engine.connect() as c:
        original = c.exec_driver_sql('PRAGMA busy_timeout').scalar()
    with store.tx(wait_seconds=.2, _cap_wait=True) as c:
        assert 0 <= c.exec_driver_sql('PRAGMA busy_timeout').scalar() <= min(200, original)
    with store.engine.connect() as c:
        assert c.exec_driver_sql('PRAGMA busy_timeout').scalar() == original
    with pytest.raises(DomainError):
        with store.tx() as c:
            c.exec_driver_sql('CREATE TABLE rollback_probe (value INTEGER)')
            raise DomainError('VERSION_CONFLICT')
    with store.tx() as c:
        assert not c.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='rollback_probe'").first()
    # A real separate SQLite writer forces BEGIN to fail within the same wait
    # budget; it must release FIFO ownership as well as its connection.
    other = Store(str(store.engine.url), test_only=True)
    with other.tx():
        started = time.monotonic()
        with pytest.raises(OperationalError):
            with store.tx(wait_seconds=.05):
                pytest.fail('Competing writer admitted')
        assert time.monotonic()-started < 1
    assert gate.snapshot()['waiters'] == 0 and not gate.snapshot()['active']
    with store.tx():
        pass
    other.engine.dispose()
    store.engine.dispose()


def test_workspace_fifo_timeout_has_no_queue_hole(tmp_path):
    _, store, _ = workspace.open_workspace(tmp_path/'fifo', new=True)
    gate, entered, release, order = store._workspace_writer_gate, threading.Event(), threading.Event(), []
    def first():
        with store.tx():
            entered.set()
            assert release.wait(2)
    def waiter(label, budget):
        with store.tx(wait_seconds=budget):
            order.append(label)
    with ThreadPoolExecutor(max_workers=3) as pool:
        held = pool.submit(first)
        assert entered.wait(2)
        expired = pool.submit(waiter, 'expired', .05)
        with pytest.raises(DomainError):
            expired.result(timeout=1)
        next_waiter = pool.submit(waiter, 'next', 1)
        deadline = time.monotonic()+1
        while gate.snapshot()['waiters'] != 1 and time.monotonic() < deadline:
            time.sleep(.005)
        assert gate.snapshot()['waiters'] == 1
        release.set()
        held.result(timeout=2)
        next_waiter.result(timeout=2)
    assert order == ['next']
    assert gate.snapshot()['waiters'] == 0 and not gate.snapshot()['active']
    store.engine.dispose()


def test_workspace_nested_and_exhausted_pool_release_admission(tmp_path):
    _, store, _ = workspace.open_workspace(tmp_path/'release', new=True)
    gate = store._workspace_writer_gate
    with store.tx() as c:
        c.exec_driver_sql('CREATE TABLE nested_probe (value INTEGER)')
        with pytest.raises(DomainError, match='Nested workspace'):
            with store.tx():
                pytest.fail('Nested writer admitted')
        c.exec_driver_sql('INSERT INTO nested_probe VALUES (1)')
    connections = []
    try:
        for _ in range(15):
            connections.append(store.engine.connect())
        started = time.monotonic()
        with pytest.raises(PoolTimeout):
            with store.tx(wait_seconds=.2):
                pytest.fail('Exhausted pool admitted')
        assert time.monotonic()-started < .5
        assert gate.snapshot()['waiters'] == 0 and not gate.snapshot()['active']
    finally:
        for connection in connections:
            connection.close()
    with store.tx() as c:
        assert c.exec_driver_sql('SELECT value FROM nested_probe').scalar_one() == 1
    store.engine.dispose()


def test_actual_fifo_contention_keeps_original_fenced_heartbeat_recovery(tmp_path):
    from sim2act.text_workflows import _sqlite_heartbeat_contention
    _, store, marker = workspace.open_workspace(tmp_path/'heartbeat', new=True)
    pid = store.project(marker['principal_id'], 'Synthetic heartbeat')
    rid = store.submit(marker['principal_id'], pid, 'No model invoked', [], 'heartbeat-contention')
    worker = Worker(store, workspace.settings_for(tmp_path/'heartbeat'), workspace.NeverModel())
    store.heartbeat(worker.id)
    claimed = store.claim(worker.id, worker.s.lease_seconds)
    assert claimed['id'] == rid
    entered, release = threading.Event(), threading.Event()
    def holder():
        with store.tx() as c:
            c.exec_driver_sql('SELECT 1')
            entered.set()
            assert release.wait(2)
    with ThreadPoolExecutor(max_workers=1) as pool:
        held = pool.submit(holder)
        assert entered.wait(2)
        try:
            with pytest.raises(WorkspaceWriterAdmissionTimeout) as caught:
                store.heartbeat(worker.id, rid, claimed['fence'], worker.s.lease_seconds,
                    _deadline=time.time()+5, _wait_seconds=.05, _running_only=True)
            assert _sqlite_heartbeat_contention(store, caught.value)
            assert not _sqlite_heartbeat_contention(store, DomainError('RESOURCE_UNAVAILABLE'))
            _, other, _ = workspace.open_workspace(tmp_path/'different', new=True)
            assert not _sqlite_heartbeat_contention(other, caught.value)
            other.engine.dispose()
            with store.engine.connect() as c:
                assert c.execute(select(runs.c.lease_until).where(runs.c.id == rid)).scalar_one() == claimed['lease_until']
        finally:
            release.set(); held.result(timeout=2)
    # Recovery still performs the real ownership/lease/Run checks and commits
    # the actual renewal; classifying contention cannot manufacture success.
    renewed = store.heartbeat(worker.id, rid, claimed['fence'], worker.s.lease_seconds,
        _deadline=time.time()+5, _wait_seconds=1, _running_only=True)
    with store.engine.connect() as c:
        live = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert live['lease_until'] == renewed > claimed['lease_until']
        assert live['status'] == 'RUNNING' and live['fence'] == claimed['fence']
    store.engine.dispose()


@pytest.mark.parametrize('url', ['sqlite://', 'sqlite:///:memory:', 'sqlite:///local.db?timeout=1',
    'postgresql+psycopg://invalid/not-used'])
def test_fifo_selection_does_not_expand_to_other_store_modes(url):
    with pytest.raises(ValueError):
        Store(url, test_only=True, workspace_serialized=True)


def test_real_spec_http_read_and_cancel_between_atomic_steps(tmp_path):
    root, store, marker = workspace.open_workspace(tmp_path/'workspace', new=True)
    settings = replace(workspace.settings_for(root), goal_planner_provider='intern-s2')
    app = workspace.workspace_app(store, settings)
    with TestClient(app) as seed:
        seed.headers['Authorization'] = 'Bearer '+workspace.TOKEN
        pid = seed.post('/api/projects', json={'name':'Concurrent synthetic spec'}).json()['id']
        resource, card = material(seed, pid, SOURCE)
        data = store, settings, seed, marker['principal_id'], pid, resource, card
        generation, result, sent = generate(data)
        assert len(sent) == 3
        made = confirm(data, generation, result)
        assert made.status_code == 200, made.text
        release, inst = instance(data, made.json()['id'])
    prefix = f"/api/internal/instances/{inst['id']}"
    failures, measurements, lease_margins = [], {}, []
    worker = Worker(store, settings, workspace.NeverModel())
    def work():
        start = time.monotonic()
        try:
            assert worker.once()
        except BaseException as exc:
            failures.append(exc)
        finally:
            measurements['last_worker_seconds'] = time.monotonic()-start
    def committed(rid):
        with store.engine.connect() as c:
            return dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    def wait_running(rid, thread):
        end = time.monotonic()+20
        while time.monotonic() < end:
            value = committed(rid)
            if value['status'] == 'RUNNING':
                return
            assert thread.is_alive() and not failures, failures
            time.sleep(.005)
        pytest.fail('Actual Worker did not claim Run')
    def timed(method, path, **kwargs):
        start = time.monotonic()
        with httpx.Client(base_url=base, headers={'Authorization':'Bearer '+workspace.TOKEN}, timeout=30) as client:
            response = client.request(method, path, **kwargs)
        return response, time.monotonic()-start
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0)); listener.listen(128)
    base = 'http://127.0.0.1:'+str(listener.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False))
    server_thread = threading.Thread(target=server.run, kwargs={'sockets':[listener]}, daemon=True)
    running = None
    server_thread.start()
    try:
        end = time.monotonic()+5
        while not server.started and time.monotonic() < end:
            time.sleep(.01)
        assert server.started
        request = dict(expected_revision=inst['revision'], expected_release_fingerprint=release['fingerprint'], input={})
        accepted, _ = timed('POST', prefix+'/runs', json=dict(request, request_key='concurrent-cancel'))
        assert accepted.status_code == 202, accepted.text
        rid = accepted.json()['run_id']; version = committed(rid)['version']
        wall = time.time()
        running = threading.Thread(target=work, daemon=True); running.start(); wait_running(rid, running)
        with ThreadPoolExecutor(max_workers=3) as pool:
            read = pool.submit(timed, 'GET', prefix+'/spec-run-requests/concurrent-cancel')
            cancel = pool.submit(timed, 'POST', f'/api/runs/{rid}/commands', json=dict(command='cancel', version=version))
            invalid = pool.submit(timed, 'POST', prefix+'/runs', json=dict(request, expected_revision=0, request_key='invalid-concurrent'))
            health, health_seconds = timed('GET', '/health')
            assert health.status_code == 200 and health_seconds < 2
            observed, read_seconds = read.result(timeout=30)
            cancelled, cancel_seconds = cancel.result(timeout=30)
            rejected, rejected_seconds = invalid.result(timeout=30)
        assert observed.status_code == 200, observed.text
        assert observed.json()['status'] in {'RUNNING','CANCEL_REQUESTED'}
        assert cancelled.status_code == 200 and cancelled.json()['status'] == 'CANCEL_REQUESTED', cancelled.text
        assert rejected.status_code == 422 and rejected.json()['submission_rejection']['phase'] == 'VALIDATION_NOT_STARTED', rejected.text
        running.join(30); assert not running.is_alive() and not failures, failures
        terminal = committed(rid)
        assert terminal['status'] == 'CANCELLED' and terminal['cancel_intent']
        with store.engine.connect() as c:
            assert c.execute(select(func.count()).select_from(internal_instance_data).where(internal_instance_data.c.instance_id == inst['id'])).scalar_one() == 0
            assert c.execute(select(func.count()).select_from(operations).where(operations.c.run_id == rid, operations.c.tool_ref == 'artifact.save_text')).scalar_one() == 0
        measurements['cancel'] = dict(read_seconds=read_seconds, read_status=observed.json()['status'], cancel_seconds=cancel_seconds, cancel_status=cancelled.json()['status'], final_status=terminal['status'], worker_seconds=measurements['last_worker_seconds'], health_seconds=health_seconds, validation_seconds=rejected_seconds)
        # A distinct accepted Run still completes all original guards and one
        # atomic save. No test callback or pause is injected into execution.
        accepted, _ = timed('POST', prefix+'/runs', json=dict(request, request_key='concurrent-success'))
        assert accepted.status_code == 202, accepted.text
        good = accepted.json()['run_id']
        running = threading.Thread(target=work, daemon=True); running.start(); wait_running(good, running)
        observed, read_seconds = timed('GET', prefix+'/spec-run-requests/concurrent-success')
        assert observed.status_code == 200 and observed.json()['status'] == 'RUNNING', observed.text
        while running.is_alive():
            value = committed(good)
            if value['status'] == 'RUNNING':
                lease_margins.append(value['lease_until']-time.time())
            running.join(.01)
        assert not failures, failures
        assert committed(good)['status'] == 'SUCCEEDED'
        assert lease_margins and min(lease_margins) > 0
        actual, _ = timed('GET', prefix+'/runs/'+good)
        assert actual.status_code == 200 and actual.json()['status'] == 'SUCCEEDED' and actual.json()['result_version'] == 1, actual.text
        stale, _ = timed('POST', f'/api/runs/{good}/commands', json=dict(command='cancel', version=version))
        assert stale.status_code == 409
        metrics = [x for x in store._workspace_writer_gate.snapshot()['completed'] if x['started_at'] >= wall]
        measurements['success'] = dict(read_seconds=read_seconds, read_status=observed.json()['status'], worker_seconds=measurements['last_worker_seconds'], minimum_observed_committed_lease_margin=min(lease_margins), result_version=1)
        measurements['transactions'] = dict(count=len(metrics), max_hold_seconds=max(x['hold_seconds'] for x in metrics), max_wait_seconds=max(x['wait_seconds'] for x in metrics), samples=metrics)
        measurements.update(model='3 fixed Mock definition calls, runtime NeverModel, zero real model requests', database='file SQLite; actual HTTP/ordinary Worker', cold_trial_g0='NOT_RUN; atomic transaction still nonpreemptible')
        (tmp_path/'concurrency-result.json').write_text(json.dumps(measurements, indent=2))
    finally:
        worker.stop.set()
        if running is not None:
            running.join(30)
        server.should_exit = True; server_thread.join(10); listener.close()
        assert not server_thread.is_alive() and (running is None or not running.is_alive())
        store.engine.dispose()
    _, reopened, _ = workspace.open_workspace(root)
    with reopened.engine.connect() as c:
        assert c.execute(select(internal_instances.c.data_version).where(internal_instances.c.id == inst['id'])).scalar_one() == 1
        assert c.execute(select(func.count()).select_from(internal_instance_data).where(internal_instance_data.c.instance_id == inst['id'])).scalar_one() == 1
    reopened.engine.dispose()
