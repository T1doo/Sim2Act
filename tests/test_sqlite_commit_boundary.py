"""Commit callbacks cannot spend or replace the original finite interval."""
import threading
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import event

from sim2act import _sqlite_model_snapshot as snapshots
from sim2act.errors import DomainError
from test_sqlite_model_snapshot import opened


def test_real_clock_commit_callback_expiry_rolls_back_and_pool_has_no_stale_guard(tmp_path):
    store=opened(tmp_path);token=(time.monotonic()+.15,time.time()+.15)
    callback=[]
    try:
        with pytest.raises(snapshots.SnapshotChanged,match='expired before commit'):
            with snapshots.transaction(store,settlement_interval=token) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
                def delayed(c):
                    callback.append(time.monotonic()<token[0])
                    threading.Event().wait(.2)
                event.listen(c,'commit',delayed)
        assert callback==[True]
        assert store._local_model_snapshot_records[-1]['outcome']=='ROLLED_BACK'
        with store.tx() as c:
            assert c.connection.driver_connection.in_transaction
            assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
            c.exec_driver_sql("UPDATE probe SET value='ordinary-commit'")
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='ordinary-commit'
    finally:store.engine.dispose()


def test_commit_callback_cannot_replace_delegate_to_bypass_finite_check(tmp_path,monkeypatch):
    store=opened(tmp_path);called=[];original=store.engine.dialect.do_commit
    def foreign(proxy):called.append(True);return original(proxy)
    try:
        with monkeypatch.context() as patch:
            with pytest.raises(DomainError,match='delegate changed'):
                with snapshots.transaction(store,settlement_interval=(time.monotonic()+1,time.time()+1)) as c:
                    snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='bypass'")
                    event.listen(c,'commit',lambda _:patch.setattr(store.engine.dialect,'do_commit',foreign))
        assert called==[]
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_guard_callback_cannot_consume_deadline_after_early_check(tmp_path):
    store=opened(tmp_path);token=(time.monotonic()+.15,time.time()+.15)
    try:
        with pytest.raises(snapshots.SnapshotChanged,match='expired before commit'):
            with snapshots.transaction(store,settlement_interval=token,
                    _commit_check=lambda:threading.Event().wait(.2)) as c:
                snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='late-check'")
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_admission_30_seconds_is_not_a_new_writer_lifetime_limit(tmp_path,monkeypatch):
    store=opened(tmp_path)
    try:
        with snapshots.transaction(store,settlement_interval=(time.monotonic()+120,time.time()+120)) as c:
            snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='valid-late-writer'")
            scope=c.info['local_model_snapshot'];after_admission=scope.admission_deadline+.1
            # Contract boundary test only; never a real-clock performance claim.
            monkeypatch.setattr(snapshots,'time',SimpleNamespace(time=time.time,monotonic=lambda:after_admission))
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='valid-late-writer'
    finally:store.engine.dispose()


def test_non_snapshot_worker_check_runs_after_commit_callback(tmp_path):
    store=opened(tmp_path);store._local_model_snapshots=False;stop=threading.Event()
    error=DomainError('BUDGET_EXHAUSTED','original stop at commit')
    def check():
        if stop.is_set():raise error
    try:
        with pytest.raises(DomainError) as caught:
            with snapshots.transaction(store,_commit_check=check) as c:
                c.exec_driver_sql("UPDATE probe SET value='stopped'")
                event.listen(c,'commit',lambda _:stop.set())
        assert caught.value is error
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


@pytest.mark.parametrize('fault',['rollback','timeout-restore'])
def test_failed_driver_rollback_invalidates_and_preserves_original_guard_error(tmp_path,monkeypatch,fault):
    import sqlite3
    from sim2act import db
    original_engine=db.create_engine
    class Driver(sqlite3.Connection):
        fail=False
        def rollback(self):
            if type(self).fail and fault=='rollback':raise RuntimeError('synthetic driver rollback failure')
            return super().rollback()
        def execute(self, statement, *args, **kwargs):
            if type(self).fail and fault=='timeout-restore' and statement.upper().startswith('PRAGMA BUSY_TIMEOUT ='):
                raise RuntimeError('synthetic timeout restore failure')
            return super().execute(statement,*args,**kwargs)
    def make_engine(*args,**kwargs):
        kwargs['connect_args']={**kwargs.get('connect_args',{}),'factory':Driver}
        return original_engine(*args,**kwargs)
    monkeypatch.setattr(db,'create_engine',make_engine)
    store=opened(tmp_path);original=DomainError('BUDGET_EXHAUSTED','original finite rejection');invalidated=[]
    event.listen(store.engine,'invalidate',lambda raw,record,error:invalidated.append(type(raw)))
    def reject():
        Driver.fail=True
        raise original
    try:
        with pytest.raises(DomainError) as caught:
            with store.tx(wait_seconds=.1,_commit_check=reject) as c:
                c.exec_driver_sql("UPDATE probe SET value='must-not-persist'")
        assert caught.value is original and Driver in invalidated
        Driver.fail=False
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:
        Driver.fail=False;store.engine.dispose()


def test_engine_level_commit_replacement_is_refused_without_dispatch(tmp_path,monkeypatch):
    store=opened(tmp_path);called=[];original=store.engine.dialect.do_commit
    def foreign(proxy):called.append('foreign');return original(proxy)
    def replacement(c):
        called.append('engine');monkeypatch.setattr(store.engine.dialect,'do_commit',foreign)
    event.listen(store.engine,'commit',replacement)
    try:
        with pytest.raises(DomainError,match='Engine commit listeners'):
            with snapshots.transaction(store,settlement_interval=(time.monotonic()+1,time.time()+1)) as c:
                snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='bypass'")
        assert called==[]
    finally:
        event.remove(store.engine,'commit',replacement)
    try:
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_new_engine_callback_from_connection_commit_is_refused(tmp_path):
    store=opened(tmp_path);called=[]
    def foreign(c):called.append(True)
    try:
        with pytest.raises(DomainError,match='Engine commit listeners'):
            with snapshots.transaction(store,settlement_interval=(time.monotonic()+1,time.time()+1)) as c:
                snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='bypass'")
                event.listen(c,'commit',lambda _:event.listen(store.engine,'commit',foreign))
        assert called==[]
        event.remove(store.engine,'commit',foreign)
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_caught_recursive_commit_cannot_revive_rolled_back_transaction(tmp_path):
    store=opened(tmp_path);selected=[];inner=[]
    def check():
        try:selected[0].commit()
        except DomainError:inner.append(True)
    try:
        with pytest.raises(DomainError):
            with snapshots.transaction(store,_commit_check=check) as c:
                selected.append(c);snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='reentered'")
        assert inner==[True] and store._local_model_snapshot_records[-1]['outcome']=='ROLLED_BACK'
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_ordinary_transaction_keeps_engine_callbacks(tmp_path):
    store=opened(tmp_path);called=[]
    def observed(c):called.append(True)
    event.listen(store.engine,'commit',observed)
    try:
        with store.tx() as c:c.exec_driver_sql("UPDATE probe SET value='ordinary'")
        assert called==[True]
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='ordinary'
    finally:
        event.remove(store.engine,'commit',observed);store.engine.dispose()


def test_ordinary_dialect_accepts_its_original_raw_dbapi_protocol(tmp_path):
    store=opened(tmp_path)
    try:
        with store.engine.connect() as c:
            c.exec_driver_sql('BEGIN IMMEDIATE')
            c.exec_driver_sql("UPDATE probe SET value='raw-delegate-compatible'")
            store.engine.dialect.do_commit(c.connection.driver_connection)
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='raw-delegate-compatible'
    finally:store.engine.dispose()


def test_commit_callback_cannot_mutate_previously_checked_rows(tmp_path):
    store=opened(tmp_path)
    try:
        with pytest.raises(DomainError,match='protected write'):
            with snapshots.transaction(store,settlement_interval=(time.monotonic()+1,time.time()+1)) as c:
                snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='checked'")
                event.listen(c,'commit',lambda c:c.exec_driver_sql("UPDATE probe SET value='late-unchecked'"))
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_check_cannot_remove_write_sentinel_mutate_then_restore_it(tmp_path,monkeypatch):
    store=opened(tmp_path);entries=[];original=store._sqlite_commit_boundary;selected=[]
    def observed(c,check,*args):
        scope=original(c,check,*args);entries.append(scope);return scope
    monkeypatch.setattr(store,'_sqlite_commit_boundary',observed)
    def changed():
        scope=entries[0];c=selected[0]
        event.remove(c,'before_cursor_execute',scope.no_commit_write)
        c.exec_driver_sql("UPDATE probe SET value='unchecked-guard-write'")
        event.listen(c,'before_cursor_execute',scope.no_commit_write)
    try:
        with pytest.raises(DomainError,match='protected writes'):
            with snapshots.transaction(store,_commit_check=changed) as c:
                selected.append(c);snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='checked'")
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_check_cannot_replace_this_calls_held_clock_or_tail_role(tmp_path,monkeypatch):
    store=opened(tmp_path);entries=[];original=store._sqlite_commit_boundary
    def observed(c,check,*args):
        scope=original(c,check,*args);entries.append(scope);return scope
    monkeypatch.setattr(store,'_sqlite_commit_boundary',observed)
    def changed():
        entries[0].clock_check=None
        entries[0].last_event=lambda c:None
    try:
        with pytest.raises(DomainError,match='held roles'):
            with snapshots.transaction(store,_commit_check=changed,
                    settlement_interval=(time.monotonic()+1,time.time()+1)) as c:
                snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='changed-roles'")
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_removed_snapshot_listener_cleanup_cannot_mask_expiry(tmp_path):
    store=opened(tmp_path);token=(time.monotonic()+.15,time.time()+.15)
    def changed(c):
        scope=c.info['local_model_snapshot']
        event.remove(c,'before_cursor_execute',scope.before)
        threading.Event().wait(.2)
    try:
        with pytest.raises(snapshots.SnapshotChanged,match='expired before commit'):
            with snapshots.transaction(store,settlement_interval=token) as c:
                snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='removed-listener'")
                event.listen(c,'commit',changed)
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


def test_finite_echo_domain_is_explicitly_refused_without_commit(tmp_path):
    store=opened(tmp_path)
    try:
        with pytest.raises(DomainError,match='echo callbacks'):
            with snapshots.transaction(store,settlement_interval=(time.monotonic()+1,time.time()+1)) as c:
                snapshots.promote(c);c.exec_driver_sql("UPDATE probe SET value='echo'")
                c._echo=True
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()


@pytest.mark.parametrize('snapshot',[False,True])
def test_rollback_listener_error_preserves_original_and_discards_connection(tmp_path,snapshot):
    store=opened(tmp_path);original=DomainError('VERSION_CONFLICT','original body failure');invalidated=[]
    event.listen(store.engine,'invalidate',lambda raw,record,error:invalidated.append(True))
    def failed(c):raise RuntimeError('synthetic rollback listener failure')
    scope=(snapshots.transaction(store,settlement_interval=(time.monotonic()+1,time.time()+1))
        if snapshot else store.tx(_commit_check=lambda:None))
    try:
        with pytest.raises(DomainError) as caught:
            with scope as c:
                if snapshot:snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='rollback-error'")
                event.listen(c,'rollback',failed)
                raise original
        assert caught.value is original and invalidated
        with store.tx() as c:assert c.exec_driver_sql('SELECT value FROM probe').scalar()=='before'
    finally:store.engine.dispose()
