"""Actual SQLite heartbeat/writer tails; small clocks are not Cold performance."""

import threading
import time
from dataclasses import replace

import pytest
from sqlalchemy import event, select, update

from sim2act import _sqlite_model_snapshot as snapshots
from sim2act import model_settlement as settlement
from sim2act import natural_spec_runtime as runtime
from sim2act.db import runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def started(env, lease=.6):
    store, settings, client, _, _, pid, resource = env
    rid = client.post(f'/api/projects/{pid}/runs',json={
        'goal':'Synthetic finite writer tail only','resource_refs':[resource],
        'request_key':'finite-tail'}).json()['run_id']
    worker = Worker(store, replace(settings, lease_seconds=lease))
    job = store.claim(worker.id, 30)
    assert job['id'] == rid
    return worker, job


@pytest.mark.parametrize('snapshot', [False, True])
@pytest.mark.parametrize('with_state', [False, True])
@pytest.mark.parametrize('fault', ['none','lease','node','stop','replace'])
def test_original_lease_reaches_actual_writer_commit_and_rolls_back_after_callback(env,snapshot,with_state,fault):
    worker, job = started(env)
    store=worker.store
    if snapshot:
        store._enable_local_model_snapshots()
    deadline = time.time() + (.3 if fault=='node' else 5)
    state = dict(lock=threading.Lock(),lease_until=job['lease_until'],deadline=deadline) if with_state else None
    entered=[]
    def write():
        with runtime._model_settlement_writer(worker,job,deadline,state):
            token=worker._settlement_interval
            with runtime._model_writer_connection(worker,None,None) as (c,plan):
                assert plan is None
                current=store.guard(c,job['id'],job['fence'])
                assert token[1]==min(current['lease_until'],deadline,job['created_at']+worker.s.run_seconds)
                assert time.monotonic()<token[0]<=time.monotonic()+worker.s.lease_seconds
                if snapshot:snapshots.promote(c)
                c.execute(update(runs).where(runs.c.id==job['id']).values(result={'tail':'complete'}))
                if fault!='none':
                    def callback(connection):
                        entered.append(time.time()<token[1])
                        if fault in {'lease','node'}:
                            threading.Event().wait(max(0,token[1]-time.time())+.03)
                        elif fault=='stop':worker.stop.set()
                        else:worker._settlement_interval=(time.monotonic()+120,time.time()+120)
                    event.listen(c,'commit',callback)
    if fault=='none':
        write()
    else:
        with pytest.raises((DomainError,snapshots.SnapshotChanged)):
            write()
        assert entered==[True]
    with store.engine.connect() as c:
        actual=c.execute(select(runs.c.result).where(runs.c.id==job['id'])).scalar_one()
    assert actual==({'tail':'complete'} if fault=='none' else None)
    assert not worker._settlement_lock.locked()
    if fault=='replace':
        assert worker.stop.is_set()  # Keep foreign metadata; never silently clear it.
    else:
        assert not hasattr(worker,'_settlement_interval')
    if snapshot:
        assert store._local_model_snapshot_records[-1]['outcome']==('COMMITTED' if fault=='none' else 'ROLLED_BACK')


def test_sqlite_writer_without_original_lifetime_fails_before_user_dml(env):
    worker,job=started(env)
    with pytest.raises(DomainError,match='Original finite settlement writer scope'):
        with runtime._model_writer_connection(worker,None,None):
            pytest.fail('No unbounded model writer')


def test_actual_heartbeat_cannot_commit_after_original_owner_expires(env):
    worker,job=started(env)
    with worker.store.tx() as c:
        c.execute(update(runs).where(runs.c.id==job['id']).values(lease_until=time.time()+.3))
    with worker.store.engine.connect() as c:
        before=c.execute(select(runs.c.lease_until).where(runs.c.id==job['id'])).scalar_one()
    armed=[True];entered=[]
    def callback(connection):
        if armed[0]:
            armed[0]=False;entered.append(time.time()<before)
            threading.Event().wait(max(0,before-time.time())+.03)
    def connected(connection):event.listen(connection,'commit',callback)
    event.listen(worker.store.engine,'engine_connect',connected)
    try:
        with pytest.raises(DomainError,match='Original heartbeat interval ended before commit'):
            worker.store.heartbeat(worker.id,job['id'],job['fence'],30)
    finally:event.remove(worker.store.engine,'engine_connect',connected)
    assert entered==[True]
    with worker.store.engine.connect() as c:
        assert c.execute(select(runs.c.lease_until).where(runs.c.id==job['id'])).scalar_one()==before


def test_legacy_monotonic_bound_survives_wall_rollback(env,monkeypatch):
    from types import SimpleNamespace
    worker,job=started(env,30)
    with runtime._model_settlement_writer(worker,job,time.time()+5,None):
        token=worker._settlement_interval
        monkeypatch.setattr(settlement,'time',SimpleNamespace(
            time=lambda:job['created_at']-3600,monotonic=lambda:token[0]+.1))
        with pytest.raises(DomainError,match='Finite model settlement interval ended'):
            settlement.checkpoint(worker)


@pytest.mark.parametrize('run_id',[None,'run_synthetic_interface_only'])
def test_non_sqlite_heartbeat_keeps_original_transaction_interface(run_id):
    # Only the calling contract is checked; this is not a PostgreSQL execution.
    from contextlib import contextmanager
    from types import SimpleNamespace
    from sim2act.db import Store
    store=object.__new__(Store);store.sqlite=False;observed=[]
    @contextmanager
    def transaction(**kwargs):
        observed.append(kwargs)
        assert '_commit_clock_check' not in kwargs
        yield SimpleNamespace(execute=lambda statement:SimpleNamespace(first=lambda:None,rowcount=1))
    store.tx=transaction
    store.guard=lambda *args:{'status':'RUNNING','cancel_intent':False,'lease_until':time.time()+30}
    result=store.heartbeat('synthetic-non-sqlite-interface-only',run_id,1)
    if run_id is None:assert result is None
    else:assert 0<result-time.time()<=30
    assert observed==[{'wait_seconds':None,'_cap_wait':True}]


def test_sqlite_liveness_without_run_keeps_original_commit_callbacks(env):
    seen=[]
    def observed(connection):seen.append(True)
    event.listen(env[0].engine,'commit',observed)
    try:assert env[0].heartbeat('synthetic-liveness-without-run') is None
    finally:event.remove(env[0].engine,'commit',observed)
    assert seen==[True]


def test_expired_publication_state_cannot_fabricate_committed_renewal(env):
    worker,job=started(env,30)
    state=dict(lock=threading.Lock(),lease_until=0,deadline=None)
    with pytest.raises(DomainError,match='Original heartbeat interval ended'):
        runtime.renew(worker,job,job['created_at']+worker.s.run_seconds,_heartbeat_state=state)
    with worker.store.engine.connect() as c:
        assert c.execute(select(runs.c.lease_until).where(runs.c.id==job['id'])).scalar_one()==job['lease_until']
    assert state['lease_until']==0 and 'sync_renewal' not in state


@pytest.mark.parametrize('snapshot',[False,True])
def test_narrower_original_state_deadline_is_not_lost_at_writer_commit(env,snapshot):
    worker,job=started(env,1.5)
    if snapshot:worker.store._enable_local_model_snapshots()
    original_deadline=time.time()+.6
    state=dict(lock=threading.Lock(),lease_until=job['lease_until'],deadline=original_deadline)
    caught=None;callback=[]
    try:
        with runtime._model_settlement_writer(worker,job,time.time()+5,state):
            with runtime._model_writer_connection(worker,None,None) as (c,_):
                if snapshot:snapshots.promote(c)
                c.execute(update(runs).where(runs.c.id==job['id']).values(result={'state-deadline':'must-rollback'}))
                def consume(connection):
                    callback.append(time.time()<original_deadline)
                    threading.Event().wait(max(0,original_deadline-time.time())+.03)
                event.listen(c,'commit',consume)
    except (DomainError,snapshots.SnapshotChanged) as error:caught=type(error).__name__
    with worker.store.engine.connect() as c:
        value=c.execute(select(runs.c.result).where(runs.c.id==job['id'])).scalar_one()
    assert callback==[True]
    assert value is None,{'persisted':value,'caught':caught,'expired_state_deadline':time.time()>original_deadline}
    assert caught is not None
