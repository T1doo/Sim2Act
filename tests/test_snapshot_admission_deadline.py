"""Real SQLite/FIFO deadlines use the original interval, without renewal."""

import json
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from sim2act import _sqlite_model_snapshot as snapshots
from sim2act.db import _WorkspaceWriterGate
from sim2act.errors import DomainError
from test_sqlite_model_snapshot import opened


def interval(seconds=1):
    return time.monotonic()+seconds, time.time()+seconds


@pytest.mark.parametrize('bound', ['monotonic', 'wall'])
def test_real_fifo_wait_uses_remaining_original_bound(tmp_path, bound):
    store=opened(tmp_path,workspace_serialized=True)
    gate=store._workspace_writer_gate
    entered,release=threading.Event(),threading.Event()
    def holder():
        with gate.hold(2):
            entered.set()
            release.wait(2)
    thread=threading.Thread(target=holder);thread.start()
    try:
        assert entered.wait(1)
        mono,wall=interval(10)
        token=(time.monotonic()+.12,wall) if bound=='monotonic' else (mono,time.time()+.12)
        started=time.monotonic()
        with pytest.raises(snapshots.SnapshotChanged,match='admission failed'):
            with snapshots.transaction(store,settlement_interval=token) as c:
                assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
                snapshots.promote(c)
        elapsed=time.monotonic()-started
        (tmp_path/'admission-timing.json').write_text(json.dumps(dict(
            classification='REAL_FIFO_REAL_CLOCK_SQLITE_SNAPSHOT',bound=bound,
            original_remaining_seconds=.12,elapsed_seconds=elapsed,
            waiters=gate.snapshot()['waiters'],
            records=list(store._local_model_snapshot_records)),indent=2)+'\n')
        assert .06<elapsed<.8
        assert gate.snapshot()['waiters']==0
        assert store._local_model_snapshot_records[-1]['writer_seconds'] is None
    finally:
        release.set();thread.join(2);store.engine.dispose()
    assert not thread.is_alive() and not gate.snapshot()['active']


@pytest.mark.parametrize('serialized',[False,True],ids=['no-fifo','fifo'])
def test_expiry_after_promotion_prevents_first_dml_and_releases_gate(tmp_path,serialized):
    store=opened(tmp_path,workspace_serialized=serialized)
    try:
        with pytest.raises(snapshots.SnapshotChanged,match='interval expired'):
            with snapshots.transaction(store,settlement_interval=interval(.1)) as c:
                c.exec_driver_sql('SELECT value FROM probe').scalar()
                snapshots.promote(c)
                threading.Event().wait(.13)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        assert store._local_model_snapshot_records[-1]['writer_seconds'] is None
        with store.tx() as c:
            assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
        if serialized:assert not store._workspace_writer_gate.snapshot()['active']
    finally:store.engine.dispose()


def test_expiry_inside_gate_entry_releases_acquired_admission(tmp_path,monkeypatch):
    store=opened(tmp_path,workspace_serialized=True)
    gate=store._workspace_writer_gate;original=gate.hold
    @contextmanager
    def delayed(seconds,**kwargs):
        with original(seconds,**kwargs) as deadline:
            threading.Event().wait(.13)
            yield deadline
    monkeypatch.setattr(gate,'hold',delayed)
    try:
        with pytest.raises(snapshots.SnapshotChanged,match='interval expired'):
            with snapshots.transaction(store,settlement_interval=interval(.1)) as c:
                c.exec_driver_sql('SELECT value FROM probe').scalar()
                snapshots.promote(c)
        assert not gate.snapshot()['active'] and gate.snapshot()['waiters']==0
    finally:store.engine.dispose()


def test_first_dml_busy_timeout_is_capped_and_restored_without_fifo(tmp_path):
    store=opened(tmp_path)
    try:
        with snapshots.transaction(store,settlement_interval=interval(.5)) as c:
            raw=c.connection.driver_connection
            original=raw.execute('PRAGMA busy_timeout').fetchone()[0]
            c.exec_driver_sql('SELECT value FROM probe').scalar()
            snapshots.promote(c)
            c.exec_driver_sql("UPDATE probe SET value='committed'")
            capped=raw.execute('PRAGMA busy_timeout').fetchone()[0]
            assert 0<capped<=500 and capped<original
        with store.engine.connect() as c:
            assert c.connection.driver_connection.execute('PRAGMA busy_timeout').fetchone()[0]==original
            assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='committed'
    finally:store.engine.dispose()


@pytest.mark.parametrize('token',[
    [],(),(1,),('bad',1),(True,1),(float('nan'),1),(1,float('inf')),(10**400,1)
],ids=['list','empty','short','string','bool','nan','infinity','overflow'])
def test_invalid_original_interval_fails_closed_without_mutation(tmp_path,token):
    store=opened(tmp_path)
    try:
        with pytest.raises(snapshots.SnapshotChanged,match='Invalid original'):
            with snapshots.transaction(store,settlement_interval=token):
                pytest.fail('Malformed deadline entered the caller')
        with store.tx() as c:
            assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
            assert 'local_model_snapshot' not in c.info
    finally:store.engine.dispose()


def test_wall_rollback_cannot_revive_monotonic_deadline(tmp_path,monkeypatch):
    store=opened(tmp_path)
    real=time
    try:
        with pytest.raises(snapshots.SnapshotChanged,match='interval expired'):
            with snapshots.transaction(store,settlement_interval=interval(.1)) as c:
                c.exec_driver_sql('SELECT value FROM probe').scalar()
                snapshots.promote(c)
                monkeypatch.setattr(snapshots,'time',SimpleNamespace(monotonic=real.monotonic,time=lambda:real.time()-3600))
                threading.Event().wait(.13)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_gate_does_not_rebase_absolute_deadline_or_change_old_callers():
    gate=_WorkspaceWriterGate()
    with pytest.raises(DomainError,match='admission timed out'):
        with gate.hold(30,deadline=time.monotonic()-1):
            pytest.fail('Expired original absolute bound was rebased')
    assert gate.snapshot()['waiters']==0 and not gate.snapshot()['active']
    with gate.hold(1) as deadline:assert time.monotonic()<deadline<=time.monotonic()+1


def test_non_snapshot_transaction_preserves_existing_behavior(tmp_path):
    store=opened(tmp_path)
    store._local_model_snapshots=False
    try:
        with snapshots.transaction(store,settlement_interval=('irrelevant',)) as c:
            c.exec_driver_sql("UPDATE probe SET value='ordinary'")
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='ordinary'
    finally:store.engine.dispose()


def test_missing_interval_and_no_fifo_preserve_old_timeout_and_admission(tmp_path):
    store=opened(tmp_path)
    try:
        with snapshots.transaction(store) as c:
            raw=c.connection.driver_connection
            raw.execute('PRAGMA busy_timeout=45000')
            c.exec_driver_sql('SELECT value FROM probe').scalar()
            snapshots.promote(c)
            assert c.info['local_model_snapshot'].admission_deadline is None
            c.exec_driver_sql("UPDATE probe SET value='ordinary-snapshot'")
            assert raw.execute('PRAGMA busy_timeout').fetchone()[0]==45000
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='ordinary-snapshot'
    finally:store.engine.dispose()
