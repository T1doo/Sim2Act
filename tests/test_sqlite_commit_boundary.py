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


def test_driver_commit_then_error_is_unknown_not_confirmed_rollback(tmp_path,monkeypatch):
    import sqlite3
    from sim2act import db
    original_engine = db.create_engine
    class Driver(sqlite3.Connection):
        fail = False
        commits = 0
        def commit(self):
            result = super().commit()
            if type(self).fail:
                type(self).commits += 1
                raise RuntimeError("synthetic error after actual driver commit")
            return result
    def make_engine(*args, **kwargs):
        kwargs["connect_args"] = {**kwargs.get("connect_args", {}), "factory": Driver}
        return original_engine(*args, **kwargs)
    monkeypatch.setattr(db, "create_engine", make_engine)
    store = opened(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="after actual driver commit"):
            with snapshots.transaction(store, _commit_check=lambda: None) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='actually-committed'")
                Driver.fail = True
        Driver.fail = False
        assert Driver.commits == 1
        assert store._local_model_snapshot_records[-1]["outcome"] == "UNKNOWN"
        # Actual fresh physical connection, not a remembered callback result.
        with sqlite3.connect(str(store.engine.url.database)) as fresh:
            assert fresh.execute("SELECT value FROM probe").fetchone() == ("actually-committed",)
    finally:
        Driver.fail = False
        store.engine.dispose()


def test_commit_return_is_recorded_before_outer_bookkeeping_error(tmp_path, monkeypatch):
    store = opened(tmp_path)
    captured = []
    original = store._sqlite_commit_boundary
    def observed(c, check, *args):
        scope = original(c, check, *args)
        captured.append(scope)
        return scope
    monkeypatch.setattr(store, "_sqlite_commit_boundary", observed)
    try:
        with pytest.raises(RuntimeError, match="after raw delegate returned"):
            with snapshots.transaction(store, _commit_check=lambda: None) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='known-committed'")
                original_commit = c.commit
                def after_commit():
                    original_commit()
                    assert captured[0].committed and captured[0].commit_invoked
                    raise RuntimeError("synthetic error after raw delegate returned")
                monkeypatch.setattr(c, "commit", after_commit)
        assert store._local_model_snapshot_records[-1]["outcome"] == "COMMITTED"
        with store.engine.connect() as fresh:
            assert fresh.exec_driver_sql("SELECT value FROM probe").scalar_one() == "known-committed"
    finally:
        store.engine.dispose()


def test_callback_cannot_label_rejected_commit_as_success(tmp_path, monkeypatch):
    store = opened(tmp_path)
    captured = []
    original = store._sqlite_commit_boundary
    def observed(c, check, *args):
        scope = original(c, check, *args)
        captured.append(scope)
        return scope
    monkeypatch.setattr(store, "_sqlite_commit_boundary", observed)
    def forged():
        with pytest.raises(AttributeError):
            captured[0].committed = True
        with pytest.raises(AttributeError):
            captured[0].commit_invoked = True
        raise DomainError("VERSION_CONFLICT", "original validation rejection")
    try:
        with pytest.raises(DomainError, match="original validation rejection"):
            with snapshots.transaction(store, _commit_check=forged) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        assert not captured[0].committed and not captured[0].commit_invoked
        assert store._local_model_snapshot_records[-1]["outcome"] == "ROLLED_BACK"
        with store.engine.connect() as fresh:
            assert fresh.exec_driver_sql("SELECT value FROM probe").scalar_one() == "before"
    finally:
        store.engine.dispose()


def test_reflection_cannot_forge_native_outcome_or_invoke_original_delegate(tmp_path, monkeypatch):
    import gc
    import weakref
    from sim2act import _cold_source_owned_impl as native
    store = opened(tmp_path)
    captured = []
    original = store._sqlite_commit_boundary
    def observed(c, check, *args):
        scope = original(c, check, *args)
        captured.append(scope)
        return scope
    monkeypatch.setattr(store, "_sqlite_commit_boundary", observed)
    def forged():
        scope = captured[0]
        assert type(scope).committed.fget.__closure__ is None
        for candidate in gc.get_objects():
            if type(candidate) is dict:
                assert candidate.get(scope) != [False, False]
        for reference in weakref.getweakrefs(scope):
            callback = reference.__callback__
            if callback is not None:
                callback(reference)
        with pytest.raises(ValueError, match="Commit outcome provenance changed"):
            native.invoke_commit_outcome(scope, scope.raw)
        with pytest.raises(ValueError, match="Commit outcome provenance changed"):
            native.init_commit_outcome(scope, lambda: None, lambda: None)
        assert native.read_commit_outcome(scope) == (False, False)
        vars(scope)["committed"] = True
        assert not scope.committed
        raise DomainError("VERSION_CONFLICT", "original rejection after reflection")
    try:
        with pytest.raises(DomainError, match="original rejection after reflection"):
            with snapshots.transaction(store, _commit_check=forged) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        assert store._local_model_snapshot_records[-1]["outcome"] == "ROLLED_BACK"
        with store.engine.connect() as fresh:
            assert fresh.exec_driver_sql("SELECT value FROM probe").scalar_one() == "before"
    finally:
        store.engine.dispose()


def test_borrowed_constructor_rejected_before_foreign_instance_dispatch(tmp_path):
    store = opened(tmp_path)
    called = []
    class Fake:
        __init__ = store._sqlite_commit_boundary.__init__
        def __setattr__(self, key, value):
            called.append(key)
            return object.__setattr__(self, key, value)
    try:
        with store.engine.connect() as c:
            c.exec_driver_sql("BEGIN IMMEDIATE")
            with pytest.raises(ValueError, match="Commit outcome provenance changed"):
                Fake(c, lambda: None)
            c.rollback()
        assert called == []
    finally:
        store.engine.dispose()


def test_final_clock_cannot_swap_physical_driver_and_commit_another_connection(tmp_path):
    import sqlite3
    store = opened(tmp_path)
    other = sqlite3.connect(str(tmp_path / "other-driver.db"))
    other.execute("CREATE TABLE probe(value TEXT)")
    other.commit()
    other.execute("INSERT INTO probe VALUES('not-committed')")
    selected = []
    original_drivers, discarded = [], []
    event.listen(store.engine, "invalidate", lambda raw, record, error: discarded.append(raw))
    def swap():
        selected[0].connection.dbapi_connection = other
    try:
        with pytest.raises(ValueError, match="driver/transaction slots"):
            with snapshots.transaction(store, _commit_clock_check=swap) as c:
                selected.append(c)
                original_drivers.append(c.connection.driver_connection)
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        assert other.in_transaction
        with sqlite3.connect(str(tmp_path / "other-driver.db")) as fresh:
            assert fresh.execute("SELECT count(*) FROM probe").fetchone() == (0,)
        with sqlite3.connect(str(store.engine.url.database)) as fresh:
            assert fresh.execute("SELECT value FROM probe").fetchone() == ("before",)
        # Connection.close resets the public invalidated property. The real
        # pool event proves the original physical handle was discarded.
        assert discarded == original_drivers
    finally:
        other.rollback();other.close();store.engine.dispose()


def test_check_cannot_replace_tail_code_before_tail_dispatch(tmp_path):
    store = opened(tmp_path)
    function = store._sqlite_commit_boundary.last_event
    original = function.__code__
    def foreign_code(engine, fail):
        def foreign(c):
            if engine is fail:
                pass
            raise AssertionError("Foreign tail was dispatched")
        return foreign.__code__
    changed = foreign_code(None, None)
    assert len(changed.co_freevars) == len(original.co_freevars)
    def mutate():
        function.__code__ = changed
    try:
        with pytest.raises(ValueError, match="Commit outcome provenance changed"):
            with snapshots.transaction(store, _commit_check=mutate) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
    finally:
        function.__code__ = original
    try:
        with store.tx() as fresh:
            assert fresh.exec_driver_sql("SELECT value FROM probe").scalar_one() == "before"
    finally:
        store.engine.dispose()


@pytest.mark.parametrize("role", ["raw", "c"])
def test_rejected_fields_never_dispatch_foreign_cleanup(tmp_path, monkeypatch, role):
    store = opened(tmp_path)
    captured, called = [], []
    original = store._sqlite_commit_boundary
    def observed(c, check, *args):
        scope = original(c, check, *args)
        captured.append(scope)
        return scope
    monkeypatch.setattr(store, "_sqlite_commit_boundary", observed)
    class Foreign:
        @property
        def in_transaction(self):
            called.append("in_transaction")
            return True
        def rollback(self):called.append("rollback")
        def invalidate(self, *args):called.append("invalidate")
    def mutate():setattr(captured[0], role, Foreign())
    try:
        with pytest.raises(ValueError, match="Commit outcome provenance changed"):
            with snapshots.transaction(store, _commit_check=mutate) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        assert called == []
        assert store._local_model_snapshot_records[-1]["outcome"] == "ROLLED_BACK"
        with store.engine.connect() as fresh:
            assert fresh.exec_driver_sql("SELECT value FROM probe").scalar_one() == "before"
    finally:store.engine.dispose()


def test_rejected_class_property_cannot_forge_snapshot_commit_fact(tmp_path):
    store = opened(tmp_path)
    cls = store._sqlite_commit_boundary
    original = cls.committed
    called = []
    def foreign(self):
        called.append(True)
        return True
    def mutate():cls.committed = property(foreign)
    try:
        with pytest.raises(ValueError, match="Commit outcome provenance changed"):
            with snapshots.transaction(store, _commit_check=mutate) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        assert called == []
        assert store._local_model_snapshot_records[-1]["outcome"] == "ROLLED_BACK"
    finally:cls.committed = original
    try:
        with store.engine.connect() as fresh:
            assert fresh.exec_driver_sql("SELECT value FROM probe").scalar_one() == "before"
    finally:store.engine.dispose()


def test_delegate_start_proxy_swap_cannot_redirect_actual_commit(tmp_path):
    import sqlite3
    import sys
    from sqlalchemy.engine.default import DefaultDialect
    store = opened(tmp_path)
    other = sqlite3.connect(str(tmp_path / "late-other.db"))
    other.execute("CREATE TABLE probe(value TEXT)");other.commit()
    other.execute("INSERT INTO probe VALUES('not-committed')")
    held, seen = [], []
    code = DefaultDialect.do_commit.__code__
    def injected(active, offset):
        if active is code and held:
            proxy, raw = held[0]
            # The documented dialect parameter now binds the actual DBAPI
            # object, preserving one original hook call and its physical target.
            seen.append(sys._getframe(1).f_locals["dbapi_connection"] is raw)
            proxy.dbapi_connection = other
    slot = next(i for i in (3, 5, 4) if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(slot, "late physical driver swap")
    try:
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_START, injected)
        sys.monitoring.set_local_events(slot, code, sys.monitoring.events.PY_START)
        with pytest.raises(ValueError, match="driver/transaction slots"):
            with snapshots.transaction(store, _commit_check=lambda: None) as c:
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='known-main-commit'")
                held.append((c.connection, c.connection.driver_connection))
        assert seen == [True]
        assert store._local_model_snapshot_records[-1]["outcome"] == "COMMITTED"
        assert other.in_transaction
        with sqlite3.connect(str(tmp_path / "late-other.db")) as fresh:
            assert fresh.execute("SELECT count(*) FROM probe").fetchone() == (0,)
        with sqlite3.connect(str(store.engine.url.database)) as fresh:
            assert fresh.execute("SELECT value FROM probe").fetchone() == ("known-main-commit",)
    finally:
        sys.monitoring.set_local_events(slot, code, 0)
        sys.monitoring.register_callback(slot, sys.monitoring.events.PY_START, None)
        sys.monitoring.free_tool_id(slot)
        other.rollback();other.close();store.engine.dispose()


def test_check_cannot_dispatch_foreign_owner_class_properties_or_cleanup(tmp_path):
    from sqlalchemy.engine import Connection
    store = opened(tmp_path)
    selected, called = [], []
    class Foreign(Connection):
        __slots__ = ()
        @property
        def closed(self):called.append("closed");return False
        @property
        def invalidated(self):called.append("invalidated");return False
        def invalidate(self, *args):called.append("invalidate")
    def mutate():selected[0].__class__ = Foreign
    try:
        with pytest.raises(ValueError, match="physical types"):
            with snapshots.transaction(store, _commit_check=mutate) as c:
                selected.append(c)
                snapshots.promote(c)
                c.exec_driver_sql("UPDATE probe SET value='must-not-commit'")
        assert called == []
        assert store._local_model_snapshot_records[-1]["outcome"] == "ROLLED_BACK"
        with store.engine.connect() as fresh:
            assert fresh.exec_driver_sql("SELECT value FROM probe").scalar_one() == "before"
    finally:store.engine.dispose()
