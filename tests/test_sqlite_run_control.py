"""Control boundary tests. Large Cold timings live in a separate full-flow test."""

import threading
import time
import sqlite3

import pytest
from sqlalchemy import select
from test_pa_spec_apps import claim, enqueue, prepared, setup

from sim2act._sqlite_run_control import Interrupted, projection
from sim2act.db import events, runs
from sim2act.errors import DomainError
from sim2act.model_settlement import checkpoint


def test_current_owner_command_rolls_back_before_original_cas_and_notifies(env):
    data = setup(env)
    store, _, client, user, *_ = data
    _, _, release, inst = prepared(data)
    rid = enqueue(data, release, inst)
    worker, run, _ = claim(data, rid)
    active, finished = threading.Event(), threading.Event()
    errors, observations = [], {}
    def writer():
        try:
            try:
                with store.local_model_settlement(worker, run, time.time()+20) as epoch:
                    observations['epoch'] = epoch
                    with store.tx() as c:
                        store.event(c, rid, 'CONTROL_TEST_UNCOMMITTED', {})
                        active.set()
                        end = time.monotonic()+10
                        while time.monotonic() < end:
                            checkpoint(worker)
                            finished.wait(.005)
                        raise AssertionError('Original cancel did not interrupt transaction')
            except Interrupted as interrupted:
                with store.engine.connect() as c:
                    assert not c.execute(select(events.c.id).where(events.c.run_id == rid,
                        events.c.kind == 'CONTROL_TEST_UNCOMMITTED')).first()
                assert interrupted.epoch.closed
                interrupted.wait_commands()
                with store.engine.connect() as c:
                    observations['command_state'] = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
        except BaseException as error:
            errors.append(error)
        finally:
            finished.set()
    thread = threading.Thread(target=writer, daemon=True)
    thread.start()
    try:
        assert active.wait(5)
        progress = client.get(f"/api/internal/instances/{inst['id']}/runs/{rid}/control-progress")
        assert progress.status_code == 200, progress.text
        value = progress.json()
        assert value['status'] == 'RUNNING' and value['consistency'] == 'COMMITTED_METADATA_ONLY'
        assert value['content_access'] is False
        assert not any(key in value for key in ['result','input','context','goal','source','events','worker_id','lease_until'])
        wrong = client.get(f"/api/internal/instances/iinstance_{'0'*32}/runs/{rid}/control-progress")
        assert wrong.status_code == 403
        with store.local_model_command(user, rid, 'cancel', run['version']+1, iid=inst['id']):
            assert not observations['epoch'].commands
        with store.local_model_command(user, rid, 'cancel', run['version'], iid='iinstance_'+'0'*32):
            assert not observations['epoch'].commands
        with store.local_model_command(env[4], rid, 'cancel', run['version'], iid=inst['id']):
            assert not observations['epoch'].commands
        accepted = client.post(f"/api/internal/instances/{inst['id']}/runs/{rid}/commands",
            json=dict(command='cancel',version=run['version']))
        assert accepted.status_code == 200 and accepted.json()['status'] == 'CANCEL_REQUESTED', accepted.text
        thread.join(10)
        assert not thread.is_alive() and not errors, errors
        assert observations['command_state'] == 'CANCEL_REQUESTED'
        assert store._local_model_control.active == {}
        wrong = client.post(f"/api/internal/instances/{inst['id']}/runs/{rid}/commands",
            json=dict(command='cancel',version=run['version']+1))
        assert wrong.status_code == 409
        rejected = client.post(f"/api/internal/instances/iinstance_{'0'*32}/runs/{rid}/commands",
            json=dict(command='cancel',version=run['version']))
        assert rejected.status_code == 403
    finally:
        finished.set(); thread.join(10)


def test_failed_formal_command_still_notifies_but_is_not_cancel_ack(env):
    data = setup(env)
    store, _, _, user, *_ = data
    _, _, release, inst = prepared(data)
    rid = enqueue(data, release, inst)
    worker, run, _ = claim(data, rid)
    with pytest.raises(Interrupted) as stopped:
        with store.local_model_settlement(worker, run, time.time()+10):
            with store.local_model_command(user, rid, 'cancel', run['version'], iid=inst['id']):
                checkpoint(worker)
    # The context's exception is a completion notification, never an ACK:
    # no original command transaction ran, and the real Run stays RUNNING.
    assert stopped.value.wait_commands()
    with store.engine.connect() as c:
        actual = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    assert actual['status'] == 'RUNNING' and not actual['cancel_intent']
    assert not isinstance(stopped.value, DomainError)
    assert projection(store,user,rid,iid=inst['id'])['version'] == run['version']


def test_unfinished_control_does_not_authorize_early_error_settlement(env):
    data = setup(env)
    store, _, _, user, *_ = data
    _, _, release, inst = prepared(data)
    rid = enqueue(data, release, inst)
    worker, run, _ = claim(data, rid)
    with store.local_model_settlement(worker, run, time.time()+.05) as epoch:
        epoch.commands.add(threading.Event())
    started = time.monotonic()
    assert not Interrupted(epoch).wait_commands()
    assert time.monotonic()-started < 1
    with store.engine.connect() as c:
        live = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    assert live['status'] == run['status'] and live['version'] == run['version']
    assert not live['cancel_intent']


def test_unreadable_hint_is_optional_and_progress_read_fails_bounded(env):
    data = setup(env)
    store, _, client, user, *_ = data
    _, _, release, inst = prepared(data)
    rid = enqueue(data, release, inst)
    worker, run, _ = claim(data, rid)
    with store.local_model_settlement(worker, run, time.time()+5) as epoch:
        connection = sqlite3.connect(store.engine.url.database, timeout=.2)
        try:
            connection.execute('BEGIN EXCLUSIVE')
            started = time.monotonic()
            with store.local_model_command(user, rid, 'cancel', run['version'], iid=inst['id']):
                assert not epoch.commands  # Original body is still entered.
            assert time.monotonic()-started < 1
            started = time.monotonic()
            result = client.get(f"/api/internal/instances/{inst['id']}/runs/{rid}/control-progress")
            assert result.status_code == 400 and result.json()['error']['code'] == 'RESOURCE_UNAVAILABLE'
            assert time.monotonic()-started < 1
        finally:
            connection.rollback(); connection.close()
    # Original authorization/CAS remains available after the lock clears.
    result = client.post(f"/api/internal/instances/{inst['id']}/runs/{rid}/commands",
        json=dict(command='cancel', version=run['version']))
    assert result.status_code == 200 and result.json()['status'] == 'CANCEL_REQUESTED', result.text
