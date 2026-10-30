"""Cooperative abort of a local SQLite model writer, never commit authority.

Only a committed owner/version projection can arm the active exact epoch.
The original command still validates and commits independently. Interrupting
computation rolls back its entire transaction and preserves received evidence.
"""

import sqlite3
import hashlib
import threading
import time
import weakref
from contextlib import closing, contextmanager
from pathlib import Path

from .errors import DomainError

_REGISTRIES = weakref.WeakSet()
_REGISTRY_LOCK = threading.Lock()
FIELDS = ("id", "principal_id", "project_id", "runtime_id", "worker_id", "fence", "version")


class Interrupted(BaseException):
    """Internal rollback request; deliberately not a DomainError/rejection."""

    def __init__(self, epoch):
        super().__init__("Local owner control interrupted model computation")
        self.epoch = epoch

    def wait_commands(self):
        # Called only after SQL/renewal/settlement locks and epoch are closed.
        deadline = min(time.monotonic()+30, self.epoch.deadline)
        if not self.epoch.closed:
            return False
        commands = tuple(self.epoch.commands)
        if not commands:
            return False
        for command in commands:
            if not command.wait(max(0, deadline-time.monotonic())):
                return False
        return True


class Epoch:
    def __init__(self, worker, job, deadline):
        self.worker = worker
        self.header = {key: job[key] for key in FIELDS}
        self.deadline = time.monotonic()+max(0, deadline-time.time())
        self.commands = set()
        self.started = time.monotonic()
        self.phase = "G0"
        self.checks = 0
        self.last_check = self.started
        self.max_check_gap = 0.
        self.g0_seconds = None
        interval = getattr(worker, '_settlement_interval', None)
        self.lease_wall = interval[1] if type(interval) is tuple else job['lease_until']
        self.seconds = self.lease_margin = None
        self.finished_normally = False
        self.closed = False

    def postwrite(self):
        self.g0_seconds = time.monotonic()-self.started
        self.phase = 'G1'


class Registry:
    def __init__(self, store):
        self.store = store
        self.lock = threading.Lock()
        self.local = threading.local()
        self.active = {}
        with _REGISTRY_LOCK:
            _REGISTRIES.add(self)

    @contextmanager
    def settlement(self, worker, job, deadline):
        epoch = Epoch(worker, job, deadline)
        rid = epoch.header["id"]
        with self.lock:
            if rid in self.active or getattr(self.local, "epoch", None) is not None:
                raise DomainError("VERSION_CONFLICT", "Local model control cannot reenter")
            self.active[rid] = epoch
            self.local.epoch = epoch
        try:
            yield epoch
            epoch.finished_normally = True
        finally:
            with self.lock:
                epoch.seconds = time.monotonic()-epoch.started
                epoch.max_check_gap = max(epoch.max_check_gap, time.monotonic()-epoch.last_check)
                epoch.lease_margin = epoch.lease_wall-time.time()
                epoch.closed = True
                self.active.pop(rid, None)
                del self.local.epoch

    def checkpoint(self, worker):
        epoch = getattr(self.local, "epoch", None)
        if epoch is None:
            return
        with self.lock:
            if epoch.worker is not worker or epoch.closed:
                raise DomainError("VERSION_CONFLICT", "Local model control epoch changed")
            epoch.checks += 1
            now = time.monotonic()
            epoch.max_check_gap = max(epoch.max_check_gap, now-epoch.last_check)
            epoch.last_check = now
            commands = tuple(epoch.commands)
        if commands:
            raise Interrupted(epoch)

    @contextmanager
    def command(self, principal, rid, command, version, iid=None):
        done = None
        try:
            if command == "cancel" and type(version) is int:
                with self.lock:
                    epoch = self.active.get(rid)
                if epoch is not None:
                    # This projection is only an abort hint. Never use it to skip
                    # scope_run/command_job, their original CAS, or permissions.
                    try:
                        row = projection(self.store, principal, rid, iid=iid)
                    except DomainError:
                        row = None  # A hint is never an extra command gate.
                    with self.lock:
                        if (self.active.get(rid) is epoch and not epoch.closed
                                and row is not None and row["status"] == "RUNNING"
                                and row["version"] == version
                                and all(row[key] == epoch.header[key] for key in FIELDS)
                                and row["lease_until"] > time.time() and len(epoch.commands) < 32):
                            done = threading.Event()
                            epoch.commands.add(done)
            yield
        finally:
            if done is not None:
                # Success, original validation failure and thread exit all
                # release the worker handshake. This event is not an ACK.
                done.set()


def supported(store):
    return (store.test_only and store.sqlite and store.engine.url.drivername == "sqlite"
        and bool(store.engine.url.database) and store.engine.url.database != ":memory:"
        and not store.engine.url.database.startswith("file:"))


def projection(store, principal, rid, *, iid=None):
    """Bounded committed owner metadata only; no content or validation claim."""
    if not supported(store):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Local SQLite control projection only")
    path = Path(store.engine.url.database).resolve()
    # Read-only independent handle: no writer admission, dirty-read setting,
    # SQLite retry, provider, or new database when the path is missing.
    try:
        with closing(sqlite3.connect(path.as_uri()+"?mode=ro", uri=True, timeout=.2,
                                     isolation_level=None)) as c:
            row = c.execute("""SELECT r.id,r.principal_id,r.project_id,r.runtime_id,
                r.worker_id,r.fence,r.version,r.status,r.cancel_intent,r.lease_until,
                a.instance_id,json_extract(b.snapshot,'$.instance_id')
                FROM runs r JOIN projects p ON p.id=r.project_id
                JOIN internal_run_bindings b ON b.run_id=r.id
                JOIN internal_app_runs a ON a.id=b.app_run_id
                JOIN internal_instances i ON i.id=a.instance_id
                WHERE r.id=? AND r.principal_id=? AND p.owner_id=?
                  AND a.principal_id=? AND i.principal_id=?
                  AND i.project_id=r.project_id AND i.runtime_id=r.runtime_id
                  AND (? IS NULL OR i.id=?)""",
                (rid,principal,principal,principal,principal,iid,iid)).fetchone()
    except sqlite3.Error as error:
        raise DomainError("RESOURCE_UNAVAILABLE", "Committed control metadata is temporarily unreadable") from error
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    # The accepted instance scalar remains a separate association boundary.
    if row[11] != row[10]:
        raise DomainError("PERMISSION_DENIED")
    keys = (*FIELDS, "status", "cancel_intent", "lease_until", "instance_id")
    value = dict(zip(keys, row[:11], strict=True))
    value["cancel_intent"] = bool(value["cancel_intent"])
    return value


def authenticate(store, token):
    """Same token-hash lookup, bounded when an active local writer exists."""
    path = Path(store.engine.url.database).resolve()
    try:
        with closing(sqlite3.connect(path.as_uri()+"?mode=ro", uri=True, timeout=.2,
                                     isolation_level=None)) as c:
            row = c.execute('SELECT id FROM principals WHERE token_hash=?',
                (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    except sqlite3.Error as error:
        raise DomainError("RESOURCE_UNAVAILABLE", "Local authentication is temporarily unreadable") from error
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    return row[0]


def active_epochs():
    """In-process diagnostics for bounded synthetic regression, never HTTP."""
    with _REGISTRY_LOCK:
        registries = tuple(_REGISTRIES)
    result = []
    for registry in registries:
        with registry.lock:
            result.extend((registry.store, epoch) for epoch in registry.active.values())
    return result
