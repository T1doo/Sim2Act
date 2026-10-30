"""Real WAL lock, snapshot conflict and original atomic rollback boundaries."""

import sqlite3
import threading
import time

import pytest

from sim2act.db import Store
from sim2act._sqlite_model_snapshot import SnapshotChanged, promote, transaction
from sim2act import _sqlite_model_snapshot as snapshots
from sim2act import synthetic_workspace as workspace


def opened(tmp_path, **kwargs):
    store = Store('sqlite:///'+str(tmp_path/'snapshot.db')+('?timeout=30' if kwargs.get('workspace_serialized') else '?timeout=1'),
                  test_only=True, local_model_snapshots=True, **kwargs)
    with store.tx() as c:
        c.exec_driver_sql('CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT)')
        c.exec_driver_sql("INSERT INTO probe VALUES (1,'before')")
    return store


@pytest.mark.parametrize('aba', [False, True])
def test_other_writer_commits_during_g0_and_stale_upgrade_rolls_back(tmp_path, aba):
    store = opened(tmp_path)
    other = sqlite3.connect(store.engine.url.database, timeout=.2)
    try:
        with pytest.raises(SnapshotChanged) as error:
            with transaction(store) as c:
                assert c.exec_driver_sql('SELECT value FROM probe WHERE id=1').scalar() == 'before'
                started = time.monotonic()
                other.execute("UPDATE probe SET value='concurrent' WHERE id=1")
                other.commit()
                assert time.monotonic()-started < 1
                if aba:
                    other.execute("UPDATE probe SET value='before' WHERE id=1")
                    other.commit()
                # Immutable read snapshot remains consistent. It is NOT fresh
                # permission: the same snapshot can never now commit a write.
                assert c.exec_driver_sql('SELECT value FROM probe WHERE id=1').scalar() == 'before'
                promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit' WHERE id=1")
        assert error.value.__cause__.orig.sqlite_errorcode == sqlite3.SQLITE_BUSY_SNAPSHOT
        with store.tx() as c:
            assert c.exec_driver_sql('SELECT value FROM probe WHERE id=1').scalar() == ('before' if aba else 'concurrent')
        assert store._local_model_snapshot_records[-1]['outcome'] == 'ROLLED_BACK'
    finally:
        other.close(); store.engine.dispose()


def test_original_write_group_is_atomic_and_other_reads_do_not_invalidate(tmp_path):
    store = opened(tmp_path)
    other = sqlite3.connect(store.engine.url.database, timeout=.2)
    try:
        for fails in [True, False]:
            try:
                with transaction(store) as c:
                    assert c.exec_driver_sql('SELECT value FROM probe WHERE id=1').scalar() == 'before'
                    assert other.execute('SELECT value FROM probe WHERE id=1').fetchone()[0] == 'before'
                    promote(c)
                    c.exec_driver_sql("UPDATE probe SET value='committed' WHERE id=1")
                    c.exec_driver_sql("INSERT INTO probe VALUES (2,'second-write')")
                    if fails:
                        raise ValueError('Original postwrite guard failed')
            except ValueError:
                assert fails
            with store.tx() as c:
                rows=c.exec_driver_sql('SELECT id,value FROM probe ORDER BY id').all()
                assert rows == ([(1,'before')] if fails else [(1,'committed'),(2,'second-write')])
        assert [r['outcome'] for r in store._local_model_snapshot_records] == ['ROLLED_BACK','COMMITTED']
    finally:
        other.close(); store.engine.dispose()


def test_read_phase_rejects_callback_mutation_and_cleans_up(tmp_path):
    store = opened(tmp_path)
    try:
        with pytest.raises(SnapshotChanged, match='callback attempted mutation'):
            with transaction(store) as c:
                c.exec_driver_sql("UPDATE probe SET value='not-read-only'")
        with store.tx() as c:
            assert 'local_model_snapshot' not in c.info
            assert c.exec_driver_sql('SELECT value FROM probe').scalar() == 'before'
    finally:
        store.engine.dispose()


def test_snapshot_capability_requires_explicit_file_selection_and_wal(tmp_path):
    with pytest.raises(ValueError, match='file SQLite'):
        Store('sqlite:///:memory:', test_only=True, local_model_snapshots=True)
    store = opened(tmp_path)
    try:
        with store.engine.connect() as c:
            assert c.exec_driver_sql('PRAGMA journal_mode=DELETE').scalar() == 'delete'
        with pytest.raises(SnapshotChanged, match='configured WAL'):
            with transaction(store):
                pytest.fail('Mode downgrade must not silently fall back')
    finally:
        store.engine.dispose()


def test_fifo_timeout_is_snapshot_interruption_not_response_rejection(tmp_path,monkeypatch):
    store=opened(tmp_path,workspace_serialized=True)
    gate=store._workspace_writer_gate
    entered,release=threading.Event(),threading.Event()
    original=gate.hold
    def held():
        with original(2):
            entered.set();assert release.wait(2)
    thread=threading.Thread(target=held);thread.start()
    try:
        assert entered.wait(1)
        monkeypatch.setattr(gate,'hold',lambda seconds,**kwargs:original(.03,**kwargs))
        with pytest.raises(SnapshotChanged,match='admission failed'):
            with transaction(store) as c:
                assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
                promote(c)
        assert gate.snapshot()['waiters']==0
    finally:
        release.set();thread.join(2);store.engine.dispose()
    assert not thread.is_alive() and not gate.snapshot()['active']


def test_cleanup_failure_cannot_leave_fifo_owned(tmp_path,monkeypatch):
    store=opened(tmp_path,workspace_serialized=True)
    original=snapshots.event.remove
    def failed(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('Synthetic cleanup failure after listener removed')
    try:
        monkeypatch.setattr(snapshots.event,'remove',failed)
        with pytest.raises(RuntimeError,match='cleanup failure'):
            with transaction(store) as c:
                c.exec_driver_sql('SELECT value FROM probe').scalar()
                promote(c)
                c.exec_driver_sql("UPDATE probe SET value='committed'")
        assert not store._workspace_writer_gate.snapshot()['active']
        with store.tx() as c:
            assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='committed'
    finally:
        store.engine.dispose()


def test_unknown_workspace_is_not_migrated_to_wal(tmp_path):
    root,store,_=workspace.open_workspace(tmp_path/'owned',new=True)
    try:
        with store.tx() as c:
            c.exec_driver_sql('CREATE TABLE unknown_extra (value TEXT)')
        with store.engine.connect() as c:
            assert c.exec_driver_sql('PRAGMA journal_mode=DELETE').scalar()=='delete'
    finally:
        store.engine.dispose()
    before=(root/workspace.DATABASE).read_bytes()
    with pytest.raises(workspace.WorkspaceError,match='SCHEMA_CHANGED'):
        workspace.open_workspace(root)
    assert (root/workspace.DATABASE).read_bytes()==before
    with sqlite3.connect(root/workspace.DATABASE) as c:
        assert c.execute('PRAGMA journal_mode').fetchone()[0]=='delete'
