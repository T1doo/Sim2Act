"""Real SQLite lifecycle counterexamples; not large-Cold performance claims."""

import json
import threading
import time

import pytest
from sqlalchemy import event, select, update
from test_model_settlement_interval import received as received
from test_legacy_settlement_interval import started

from sim2act import _sqlite_model_snapshot as snapshots
from sim2act import model_settlement as settlement
from sim2act import natural_spec_runtime as runtime
from sim2act.db import events, runs
from sim2act.errors import DomainError


def test_signed_interval_cannot_book_after_earlier_state_deadline(received,tmp_path):
    worker,job,aid,deadline,state=received
    state['deadline']=0
    with worker.store.engine.connect() as c:
        before=c.execute(select(runs.c.lease_until).where(runs.c.id==job['id'])).scalar_one()
    caught=None;entered=False
    try:
        with runtime._model_settlement_writer(worker,job,deadline,state,attempt_id=aid):
            entered=True
    except DomainError as error:caught=error
    with worker.store.engine.connect() as c:
        after=c.execute(select(runs.c.lease_until).where(runs.c.id==job['id'])).scalar_one()
        booked=c.execute(select(events.c.id).where(events.c.run_id==job['id'],
            events.c.kind==settlement.RESERVED)).all()
    (tmp_path/'expired-state-booking.json').write_text(json.dumps(dict(
        entered=entered,rejected=caught is not None,lease_unchanged=before==after,
        reserved_events=len(booked),real_model_requests=0),indent=2)+'\n')
    assert caught is not None and not entered
    assert before==after and booked==[]


@pytest.mark.parametrize('snapshot',[False,True])
def test_signed_writer_commit_keeps_earliest_state_deadline(received,tmp_path,snapshot):
    worker,job,aid,deadline,state=received
    if snapshot:worker.store._enable_local_model_snapshots()
    cutoff=time.time()+.4
    state['deadline']=cutoff
    entered=[];caught=None;actual_token=None
    try:
        with runtime._model_settlement_writer(worker,job,deadline,state,attempt_id=aid):
            actual_token=worker._settlement_interval
            with runtime._model_writer_connection(worker,None,None) as (c,plan):
                assert plan is None
                snapshots.promote(c)
                c.execute(update(runs).where(runs.c.id==job['id']).values(result={'expired-state':'must-not-commit'}))
                def callback(connection):
                    entered.append(time.time()<cutoff)
                    threading.Event().wait(max(0,cutoff-time.time())+.03)
                event.listen(c,'commit',callback)
    except (DomainError,snapshots.SnapshotChanged) as error:caught=error
    with worker.store.engine.connect() as c:
        result=c.execute(select(runs.c.result).where(runs.c.id==job['id'])).scalar_one()
    (tmp_path/'earliest-state-writer.json').write_text(json.dumps(dict(
        snapshot=snapshot,callback_entered_before_deadline=entered,
        original_state_deadline=cutoff,actual_token_wall_deadline=actual_token[1],
        rejected=caught is not None,persisted_result=result,real_model_requests=0),indent=2)+'\n')
    assert entered==[True]
    assert caught is not None and result is None
    assert actual_token[1]==cutoff
    assert not worker._settlement_lock.locked() and not hasattr(worker,'_settlement_interval')


def test_heartbeat_after_g0_read_cannot_reuse_old_snapshot(env):
    worker,job=started(env,lease=30)
    store=worker.store;store._enable_local_model_snapshots()
    previous=[];renewed=[]
    with pytest.raises(snapshots.SnapshotChanged):
        with runtime._model_settlement_writer(worker,job,time.time()+60,None):
            with runtime._model_writer_connection(worker,None,None) as (c,plan):
                assert plan is None
                old=store.guard(c,job['id'],job['fence'])
                previous.append(old['lease_until'])
                # This is a real second committed transaction, not a clock mock.
                renewed.append(store.heartbeat(worker.id,job['id'],job['fence'],30))
                assert renewed[0]>previous[0]
                snapshots.promote(c)
                c.execute(update(runs).where(runs.c.id==job['id']).values(result={'stale':'must-not-commit'}))
    with store.engine.connect() as c:
        current=c.execute(select(runs).where(runs.c.id==job['id'])).mappings().one()
    assert current['result'] is None and current['lease_until']==renewed[0]
    assert store._local_model_snapshot_records[-1]['outcome']=='ROLLED_BACK'


def test_same_snapshot_cannot_renew_itself_before_promotion(env):
    worker,job=started(env,lease=30)
    store=worker.store;store._enable_local_model_snapshots()
    original=[]
    with pytest.raises(snapshots.SnapshotChanged,match='mutation during the read-only G0'):
        with runtime._model_settlement_writer(worker,job,time.time()+60,None):
            with runtime._model_writer_connection(worker,None,None) as (c,plan):
                old=store.guard(c,job['id'],job['fence']);original.append(old['lease_until'])
                c.execute(update(runs).where(runs.c.id==job['id']).values(lease_until=time.time()+30))
    with store.engine.connect() as c:
        assert c.execute(select(runs.c.lease_until).where(runs.c.id==job['id'])).scalar_one()==original[0]
    assert store._local_model_snapshot_records[-1]['outcome']=='ROLLED_BACK'


@pytest.mark.parametrize('bound',[None,'later'])
def test_signed_interval_keeps_original_bound_for_none_or_later_state(received,bound):
    worker,job,aid,deadline,state=received
    state['deadline']=None if bound is None else deadline+300
    with settlement.interval(worker,job,aid,deadline,state):
        token=worker._settlement_interval
        assert 110<token[1]-time.time()<=120
        assert token[1]<=deadline


@pytest.mark.parametrize('bound',[True,float('nan'),float('inf'),'not-a-clock','missing'])
def test_signed_interval_rejects_unknown_state_deadline_before_booking(received,bound):
    worker,job,aid,deadline,state=received;state['deadline']=bound
    if bound=='missing':state.pop('deadline')
    with pytest.raises(DomainError,match='Finite original state deadline required'):
        with settlement.interval(worker,job,aid,deadline,state):
            pytest.fail('Unknown clock cannot issue a lease')
    with worker.store.engine.connect() as c:
        assert c.execute(select(events.c.id).where(events.c.run_id==job['id'],
            events.c.kind==settlement.RESERVED)).first() is None


@pytest.mark.parametrize('missing',[False,True])
def test_original_fatal_error_precedes_state_deadline_validation(received,missing):
    worker,job,aid,deadline,state=received
    original=DomainError('OUTCOME_UNKNOWN','Original fatal heartbeat')
    state.update(deadline='not-a-clock',fatal_heartbeat=original)
    if missing:state.pop('deadline')
    with pytest.raises(DomainError) as caught:
        with settlement.interval(worker,job,aid,deadline,state):
            pytest.fail('A fatal original heartbeat cannot continue')
    assert caught.value is original
