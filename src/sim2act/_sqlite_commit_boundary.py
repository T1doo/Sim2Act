"""Finite checks after SQLAlchemy commit callbacks, before SQLite DBAPI commit.

One private registration per exact driver/Connection/Transaction. Ordinary
transactions retain their original delegate; no deadline or permit is created.
"""
import sqlite3
from sqlalchemy import event

from .errors import DomainError


def install(engine):
    entries = {}
    active = set()
    original = engine.dialect.do_commit

    def fail(message):
        raise DomainError('VERSION_CONFLICT', message)

    def rollback(entry):
        try:
            if entry.raw.in_transaction:
                entry.raw.rollback()
        except BaseException as error:
            # Never let a live rejected transaction return to the pool, and
            # never replace the exception which prevented its commit.
            try:entry.c.invalidate(error)
            except BaseException:pass

    def guarded(proxy):
        raw = proxy if isinstance(proxy, sqlite3.Connection) else proxy.driver_connection
        entry = entries.get(raw)
        if entry is None:
            return original(proxy)
        entered = False
        check, tail, clock = entry.check, entry.last_event, entry.clock_check
        owner, transaction, changes = entry.c, entry.transaction, entry.changes
        try:
            entry.identity()
            if raw in active:fail('Finite commit boundary cannot reenter')
            active.add(raw)
            entered = True
            check()
            tail(owner)
            if (entry.check is not check or entry.clock_check is not clock
                    or entry.c is not owner or entry.raw is not raw
                    or entry.transaction is not transaction or entry.changes != changes
                    or raw.total_changes != changes):
                fail('Finite commit callback changed held roles or protected data')
            if clock is not None:
                clock()
            return original(proxy)
        except BaseException:
            rollback(entry)
            raise
        finally:
            if entered:active.discard(raw)

    engine.dialect.do_commit = guarded

    class Boundary:
        def __init__(self, c, check, clock_check=None):
            self.c, self.check, self.clock_check = c, check, clock_check
            self.raw = c.connection.driver_connection
            self.transaction = c.get_transaction()
            self.committed = False

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
            self.identity()
            if tuple(engine.dispatch.commit) or self.c._echo:
                fail('Finite commit does not support Engine commit listeners or echo callbacks')
            self.changes = self.raw.total_changes
            event.listen(self.c, 'before_cursor_execute', self.no_commit_write)
            event.listen(self.c, 'commit', self.last_event)
            try:
                self.c.commit()
                self.committed = True
            except BaseException:
                try:
                    event.remove(self.c, 'commit', self.last_event)
                    event.remove(self.c, 'before_cursor_execute', self.no_commit_write)
                except BaseException as cleanup:
                    try:self.c.invalidate(cleanup)
                    except BaseException:pass
                raise
            else:
                event.remove(self.c, 'commit', self.last_event)
                event.remove(self.c, 'before_cursor_execute', self.no_commit_write)

        def __exit__(self, kind, error, tb):
            if kind is not None:
                rollback(self)
            if entries.get(self.raw) is self:
                del entries[self.raw]

    return Boundary
