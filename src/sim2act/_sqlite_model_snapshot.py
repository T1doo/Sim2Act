"""Local WAL read-to-write settlement; never an authority/PASS handoff.

G0 retains its original SQLite transaction and complete guards. WAL permits
other commits while it reads. SQLite itself rejects upgrading an obsolete
snapshot; the caller must preserve received evidence rather than retry writes.
"""

import math
import sqlite3
import sys
import time
from contextlib import contextmanager, nullcontext

from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from .errors import DomainError


class SnapshotChanged(BaseException):
    """Roll back before the original receive evidence can be reconciled."""


class _Read:
    def __init__(self, store, c, settlement_interval=None):
        if settlement_interval is not None:
            try:
                valid = (type(settlement_interval) is tuple and len(settlement_interval) == 2
                    and all(type(value) in (int, float) and math.isfinite(value)
                        for value in settlement_interval))
            except OverflowError:
                valid = False
            if not valid:
                raise SnapshotChanged('Invalid original model settlement interval')
        # This is the existing interval's immutable pair, never a new lease,
        # authorization result, or now+120 renewal. None preserves old callers.
        self.settlement_interval = settlement_interval
        self.store, self.c = store, c
        self.driver, self.transaction = c.connection.driver_connection, c.get_transaction()
        self.phase = 'READ'
        self.started = time.monotonic()
        self.promoted = self.first_write = None
        self.admission = None
        self.admission_deadline = None
        self.prior_timeout = None

    def remaining(self):
        remaining = 30.
        if self.settlement_interval is not None:
            mono, wall = self.settlement_interval
            remaining = min(remaining, mono-time.monotonic(), wall-time.time())
        if self.admission_deadline is not None:
            remaining = min(remaining, self.admission_deadline-time.monotonic())
        if remaining <= 0:
            raise SnapshotChanged('Original model writer admission interval expired')
        return remaining

    def promote(self):
        if (self.phase != 'READ' or self.c.closed
                or self.c.get_transaction() is not self.transaction
                or self.c.connection.driver_connection is not self.driver):
            raise SnapshotChanged('Local model snapshot lifecycle changed')
        gate = self.store._workspace_writer_gate
        remaining = self.remaining()
        if gate is not None or self.settlement_interval is not None:
            self.admission_deadline = time.monotonic()+remaining
            if self.settlement_interval is not None:
                self.admission_deadline = min(self.admission_deadline, self.settlement_interval[0])
        admission = (gate.hold(remaining, deadline=self.admission_deadline)
            if gate is not None else nullcontext(None))
        try:
            deadline = admission.__enter__()
        except DomainError as error:
            raise SnapshotChanged('Local model writer admission failed') from error
        self.admission = admission
        if deadline is not None:
            self.admission_deadline = min(self.admission_deadline, deadline)
        self.remaining()
        self.phase = 'WRITE'
        self.promoted = time.monotonic()

    def before(self, c, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT '):
            return
        if self.phase != 'WRITE':
            raise SnapshotChanged('A callback attempted mutation during the read-only G0 snapshot')
        if self.first_write is None:
            self.remaining()  # Also mandatory for a Store with no FIFO gate.
            if self.admission_deadline is not None:
                self.prior_timeout = self.driver.execute('PRAGMA busy_timeout').fetchone()[0]
                remaining = self.remaining()
                self.driver.execute('PRAGMA busy_timeout='+str(min(self.prior_timeout, int(remaining*1000))))
            self.first_write = time.monotonic()


def promote(c):
    scope = c.info.get('local_model_snapshot')
    if scope is not None:
        if type(scope) is not _Read or scope.c is not c:
            raise SnapshotChanged('Local model snapshot ownership changed')
        scope.promote()


@contextmanager
def transaction(store, *, settlement_interval=None):
    if not store._local_model_snapshots:
        with store.tx() as c:
            yield c
        return
    with store.engine.connect() as c:
        raw = c.connection.driver_connection
        if raw.execute('PRAGMA journal_mode').fetchone()[0].lower() != 'wal':
            raise SnapshotChanged('Local model snapshot requires the configured WAL database')
        c.exec_driver_sql('BEGIN DEFERRED')
        scope = _Read(store, c, settlement_interval)
        c.info['local_model_snapshot'] = scope
        event.listen(c, 'before_cursor_execute', scope.before)
        committed = rolled_back = False
        try:
            try:
                yield c
                if scope.phase != 'WRITE':
                    raise SnapshotChanged('Local model snapshot did not reach its original write boundary')
                c.commit()
                committed = True
            except BaseException as error:
                c.rollback()
                rolled_back = True
                if (isinstance(error, OperationalError)
                        and getattr(error.orig, 'sqlite_errorcode', None) in
                        (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_BUSY_SNAPSHOT, sqlite3.SQLITE_LOCKED)):
                    raise SnapshotChanged('Concurrent SQLite writer invalidated the read-to-write settlement') from error
                raise
        finally:
            try:
                event.remove(c, 'before_cursor_execute', scope.before)
            finally:
                try:
                    c.info.pop('local_model_snapshot', None)
                    for key in ('correction_scope_segment', 'project_scope_segments', 'pb_source_reads'):
                        c.info.pop(key, None)
                    if scope.prior_timeout is not None:
                        raw.execute('PRAGMA busy_timeout='+str(scope.prior_timeout))
                finally:
                    try:
                        if scope.admission is not None:
                            scope.admission.__exit__(*sys.exc_info())
                    finally:
                        end = time.monotonic()
                        store._local_model_snapshot_records.append(dict(
                            seconds=end-scope.started, g0_read_seconds=(scope.promoted or end)-scope.started,
                            writer_seconds=None if scope.first_write is None else end-scope.first_write,
                            outcome='COMMITTED' if committed else 'ROLLED_BACK' if rolled_back else 'UNKNOWN'))
