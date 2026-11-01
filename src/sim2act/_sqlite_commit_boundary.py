"""Finite checks after SQLAlchemy commit callbacks, before SQLite DBAPI commit.

One private registration per exact driver/Connection/Transaction. Ordinary
transactions retain their original delegate; no deadline or permit is created.
"""
import sqlite3
import json
import time
import os
from contextlib import nullcontext
from sqlalchemy import event

from .errors import DomainError


def install(engine):
    entries = {}
    active = set()
    original = engine.dialect.do_commit

    def fail(message):
        raise DomainError('VERSION_CONFLICT', message)

    def held_roles(entry):
        read = "sim2act:commit-outcome-roles.v1"
        return (entry.c, entry.raw, entry.transaction) if read is None else read(entry)

    def restore_owner(entry):
        restore = "sim2act:commit-outcome-owner.v1"
        try:
            if restore is not None:
                restore(entry)
        except BaseException:
            return False
        return True

    def rollback(entry, raw=None, owner=None):
        if raw is None or owner is None:
            owner, raw, _ = held_roles(entry)
        safe_owner = restore_owner(entry)
        try:
            if raw.in_transaction:
                raw.rollback()
        except BaseException as error:
            # Never let a live rejected transaction return to the pool, and
            # never replace the exception which prevented its commit.
            if safe_owner:
                try:owner.invalidate(error)
                except BaseException:pass
        return safe_owner

    def guarded(proxy):
        raw = proxy if isinstance(proxy, sqlite3.Connection) else proxy.driver_connection
        entry = entries.get(raw)
        if entry is None:
            return original(proxy)
        current = "sim2act:commit-outcome-current.v1"
        if current is not None:
            current(entry)
        entered = False
        check, tail, clock = entry.check, entry.last_event, entry.clock_check
        owner, transaction, changes = entry.c, entry.transaction, entry.changes
        try:
            entry.identity()
            if raw in active:fail('Finite commit boundary cannot reenter')
            active.add(raw)
            entered = True
            read_control = "sim2act:commit-control-read.v1"
            control = None if read_control is None else read_control(entry)
            barrier = nullcontext() if control is None else control[1].boundary(entry)
            with barrier:
                check()
                if current is not None:
                    current(entry)
                tail(owner)
                if control is not None:
                    from ._lease_control_runtime import Runtime
                    Runtime._validate_boundary(control[0], entry, owner)
                if (entry.check is not check or entry.clock_check is not clock
                        or entry.c is not owner or entry.raw is not raw
                        or entry.transaction is not transaction or entry.changes != changes
                        or raw.total_changes != changes):
                    fail('Finite commit callback changed held roles or protected data')
                if clock is not None:
                    clock()
                invoke = "sim2act:commit-outcome-invoke.v1"
                return original(proxy) if invoke is None else invoke(entry, proxy)
        except BaseException as error:
            safe_owner = rollback(entry, raw, owner)
            if (type(error) is ValueError and error.args and type(error.args[0]) is str
                    and error.args[0].startswith("Commit outcome provenance changed") and safe_owner):
                # A swapped physical driver must not return to its original
                # pool. Retain the provenance error if cleanup itself fails.
                try:owner.invalidate(error)
                except BaseException:pass
            raise
        finally:
            if entered:active.discard(raw)

    engine.dialect.do_commit = guarded

    class Boundary:
        def __init__(self, c, check, clock_check=None):
            preflight = "sim2act:commit-outcome-preinit.v1"
            if preflight is not None:
                preflight(self)
            self.c, self.check, self.clock_check = c, check, clock_check
            self.raw = c.connection.driver_connection
            self.transaction = c.get_transaction()
            issue = "sim2act:commit-outcome-init.v1"
            if issue is not None:
                issue(self, guarded, original)

        @property
        def committed(self):
            read = "sim2act:commit-outcome-read.v1"
            return False if read is None else read(self)[0]

        @property
        def commit_invoked(self):
            read = "sim2act:commit-outcome-read.v1"
            # Without native provenance a failure is conservatively UNKNOWN,
            # never falsely a durable success or a confirmed rollback.
            return True if read is None else read(self)[1]

        def identity(self):
            if (entries.get(self.raw) is not self or self.c.closed or self.c.invalidated
                    or self.c.engine is not engine
                    or self.c.get_transaction() is not self.transaction
                    or not self.transaction.is_active or not self.raw.in_transaction
                    or self.c.connection.driver_connection is not self.raw
                    or engine.dialect.do_commit is not guarded):
                fail('Finite commit boundary ownership or delegate changed')

        def __enter__(self):
            if (not callable(self.check) or self.clock_check is not None and not callable(self.clock_check)
                    or self.transaction is None or self.raw in entries):
                fail('Invalid or reentered finite commit scope')
            entries[self.raw] = self
            try:self.identity()
            except BaseException:
                entries.pop(self.raw, None)
                raise
            return self

        def last_event(self, c):
            # Appended immediately before commit, after all caller listeners.
            # This prevents a commit callback replacing do_commit to bypass
            # the late check. Mutating listeners during dispatch is refused
            # by SQLAlchemy itself.
            if c is not self.c:fail('Finite commit event owner changed')
            self.identity()
            # SQLAlchemy runs Engine listeners after Connection listeners.
            # Unknown Engine callbacks/echo logging could replace the commit
            # delegate after this sentinel. Refuse that finite-commit domain;
            # ordinary transactions keep their original dispatch behavior.
            if tuple(engine.dispatch.commit) or self.c._echo:
                fail('Finite commit does not support Engine commit listeners or echo callbacks')
            if self.raw.total_changes != self.changes or not event.contains(
                    self.c, 'before_cursor_execute', self.no_commit_write):
                fail('Finite commit callbacks changed protected writes or scope')

        def no_commit_write(self, c, cursor, statement, parameters, context, many):
            if not statement.lstrip().upper().startswith('SELECT '):
                fail('Finite commit callback attempted a protected write')

        def commit(self):
            owner, raw, _ = held_roles(self)
            self.identity()
            read_control = "sim2act:commit-control-read.v1"
            control = None if read_control is None else read_control(self)
            if control is not None:
                from ._lease_control_runtime import Runtime
                Runtime._seed_boundary(control[0], self, owner)
            if tuple(engine.dispatch.commit) or owner._echo:
                fail('Finite commit does not support Engine commit listeners or echo callbacks')
            self.changes = raw.total_changes
            write_guard, last_event = self.no_commit_write, self.last_event
            event.listen(owner, 'before_cursor_execute', write_guard)
            event.listen(owner, 'commit', last_event)
            try:
                owner.commit()
                read = "sim2act:commit-outcome-read.v1"
                if read is not None and not read(self)[0]:
                    fail('Original finite commit delegate did not return through its fixed boundary')
            except BaseException:
                safe_owner = restore_owner(self)
                try:
                    event.remove(owner, 'commit', last_event)
                    event.remove(owner, 'before_cursor_execute', write_guard)
                except BaseException as cleanup:
                    if safe_owner:
                        try:owner.invalidate(cleanup)
                        except BaseException:pass
                raise
            else:
                event.remove(owner, 'commit', last_event)
                event.remove(owner, 'before_cursor_execute', write_guard)

        def __exit__(self, kind, error, tb):
            owner, raw, _ = held_roles(self)
            try:
                if kind is not None:
                    rollback(self, raw, owner)
            finally:
                if entries.get(raw) is self:
                    del entries[raw]
                read_control = "sim2act:commit-control-read.v1"
                facts = "sim2act:commit-outcome-read.v1"
                control = None if read_control is None else read_control(self)
                try:
                    if control is not None and not any(facts(self)):
                        from ._lease_control_runtime import Runtime
                        Runtime._abort_boundary(control[0], self, owner)
                except BaseException:
                    if error is None:
                        raise
                finally:
                    retire = "sim2act:commit-outcome-retire.v1"
                    if retire is not None:
                        retire(self)

    register = "sim2act:commit-factory-register.v1"
    retire = "sim2act:commit-factory-retire.v1"
    if register is not None:
        register(Boundary, _class_state(Boundary), guarded, _function_state(guarded), engine, entries)
        def disposed(engine):
            retire(Boundary)
        event.listen(engine, "engine_disposed", disposed)
    return Boundary


def _seal_commit_code():
    from types import CodeType
    methods = {"sim2act:commit-outcome-init.v1": "init_commit_outcome",
               "sim2act:commit-outcome-read.v1": "read_commit_outcome",
               "sim2act:commit-outcome-invoke.v1": "invoke_commit_outcome",
               "sim2act:commit-outcome-preinit.v1": "preinit_commit_outcome",
               "sim2act:commit-outcome-current.v1": "check_commit_outcome",
               "sim2act:commit-outcome-roles.v1": "read_commit_roles",
               "sim2act:commit-outcome-retire.v1": "retire_commit_roles",
               "sim2act:commit-outcome-owner.v1": "restore_commit_owner",
               "sim2act:commit-factory-register.v1": "register_commit_factory",
               "sim2act:commit-factory-retire.v1": "retire_commit_factory"}
    methods["sim2act:commit-control-read.v1"] = "read_commit_control"
    selected = {key: (None if _outcome_native is None else getattr(_outcome_native, name))
                for key, name in methods.items()}
    def seal(code):
        return code.replace(co_consts=tuple(selected[value] if type(value) is str and value in selected
            else seal(value) if type(value) is CodeType else value for value in code.co_consts))
    install.__code__ = seal(install.__code__)


try:
    from . import _cold_source_owned_impl as _outcome_native
except ImportError:
    _outcome_native = None
if _outcome_native is not None and not all(hasattr(_outcome_native, name) for name in (
        "register_commit_outcomes", "register_commit_factory", "retire_commit_factory",
        "init_commit_outcome", "preinit_commit_outcome", "check_commit_outcome",
        "read_commit_outcome", "read_commit_roles", "restore_commit_owner", "retire_commit_roles", "invoke_commit_outcome",
        "read_commit_control", "bind_commit_control", "find_commit_boundary", "enter_commit_control", "leave_commit_control")):
    _outcome_native = None
_seal_commit_code()
if _outcome_native is not None:
    from sqlalchemy.engine.default import DefaultDialect
    from sqlalchemy.engine.base import Connection as _sa_connection, RootTransaction as _sqlite_transaction
    from sqlalchemy.pool.base import _ConnectionFairy as _sqlite_proxy
    from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite as _sqlite_dialect
    from ._lease_code_witness import function_state as _function_state, class_state as _class_state
    from . import _lease_code_witness as _witness_module
    _sqlite_do_commit = DefaultDialect.do_commit
    _fairy_dbapi = _sqlite_proxy.dbapi_connection
    _tx_connection = _sqlite_transaction.connection
    _tx_active = _sqlite_transaction.is_active
    _object_class = object.__dict__["__class__"]
    _sqlite_dbapi = sqlite3.Connection
    _sqlite_execute = sqlite3.Connection.execute
    _sqlite_fetchone = sqlite3.Cursor.fetchone
    _sqlite_commit = sqlite3.Connection.commit
    _commit_wall, _commit_mono = time.time, time.monotonic
    _control_stat = os.lstat
    _receipt_load = json.loads
    _outcome_items = tuple(globals().copy().items())
    _outcome_native.register_code(12, (((globals(), (
        ("install", install, (_function_state(install),)),
        ("_sqlite_do_commit", _sqlite_do_commit, (_function_state(_sqlite_do_commit),)),
        ("_function_state", _function_state, (_function_state(_function_state),)),
        ("_class_state", _class_state, (_function_state(_class_state),)))),),
        tuple(_class_state(cls) for cls in (_sa_connection, _sqlite_transaction, _sqlite_proxy)),
        ((globals(), _outcome_items),
         (vars(_witness_module), tuple(vars(_witness_module).items())),
         (vars(_outcome_native), tuple((name, getattr(_outcome_native, name)) for name in (
             "register_commit_outcomes", "register_commit_factory", "retire_commit_factory",
             "init_commit_outcome", "preinit_commit_outcome", "check_commit_outcome",
             "read_commit_outcome", "read_commit_roles", "restore_commit_owner", "retire_commit_roles", "invoke_commit_outcome",
             "read_commit_control", "bind_commit_control", "find_commit_boundary", "enter_commit_control", "leave_commit_control"))))))
    _outcome_native.register_commit_outcomes(install, _sqlite_do_commit, _sqlite_dialect)
