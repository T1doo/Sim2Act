"""Versioned, separately committed local lease authority.

No business data, authorization or validation PASS lives here. Provisioning and
activation are explicit. A business transaction still owns all of its writes;
the control writer is held only across its final, original DBAPI commit.
"""

import json
import math
import os
import secrets
import sqlite3
import stat
import sys
import threading
import time
from builtins import type, dict, tuple, list, str, int, float, bool, len, all, any, set, zip, vars, getattr, hasattr, setattr, classmethod, staticmethod, object
from contextlib import contextmanager
from pathlib import Path
from types import FunctionType

from .errors import DomainError

VERSION = "sim2act-local-lease-control.v1"
CONTEXT = "local_lease_control"
HEADER = ("id", "principal_id", "project_id", "runtime_id", "worker_id", "fence", "version")
_DDL = (
    "CREATE TABLE metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1),protocol TEXT NOT NULL,control_id TEXT NOT NULL,main_id TEXT NOT NULL)",
    "CREATE TABLE leases(run_id TEXT PRIMARY KEY,header TEXT NOT NULL,nonce TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('PENDING','ACTIVE','CLOSED')),lease_wall REAL NOT NULL,absolute_deadline REAL NOT NULL,sequence INTEGER NOT NULL,intent TEXT CHECK(intent IN ('pause','cancel')),pending_commit TEXT,acked_commit TEXT)",
    "CREATE TABLE commits(commit_id TEXT PRIMARY KEY,run_id TEXT NOT NULL,header TEXT NOT NULL,nonce TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('PREPARED','ACKED','ABORTED')))",
)


class CommittedAckPending(BaseException):
    """The business commit returned successfully; never report/replay rollback."""


class CommitOutcomeUnknown(BaseException):
    """The original commit delegate raised; inspect durable data, never replay."""


def require(ok, message):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _path(path):
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)),
            "Linked lease control path")
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            require(not sidecar.is_symlink() and stat.S_ISREG(sidecar.stat().st_mode),
                    "Invalid lease control sidecar")
    return path


def _identity(path):
    try:
        value = _path(path).stat()
    except OSError as error:
        raise DomainError("RESOURCE_UNAVAILABLE", "Authoritative lease storage unavailable") from error
    require(stat.S_ISREG(value.st_mode), "Ordinary lease control file required")
    return (value.st_dev, value.st_ino)


def _header(row):
    values = tuple(row[k] for k in HEADER)
    require(all(type(v) is str and v for v in values[:5])
            and all(type(v) is int and v >= 1 for v in values[5:]),
            "Exact lease owner header required")
    return values


def _wire(values):
    return json.dumps(values, ensure_ascii=True, separators=(",", ":"))


def _schema(c):
    values = c.execute("SELECT name,sql FROM sqlite_schema WHERE sql IS NOT NULL ORDER BY name").fetchall()
    require(values == sorted(zip(("metadata", "leases", "commits"), _DDL)),
            "Unknown lease control schema, trigger or view")
    require(c.execute("PRAGMA user_version").fetchone() == (1,), "Unknown lease control schema version")


class Authority:
    """Exact file/generation binding; every current read uses a new snapshot."""

    def __init__(self, path, binding):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        self.path = _path(path)
        require(type(binding) is dict and set(binding) == {
            "protocol", "control_id", "main_id", "device", "inode"}, "Invalid lease control binding")
        require(binding["protocol"] == VERSION, "Unknown lease control protocol")
        self.binding = dict(binding)
        self.file_identity = (binding["device"], binding["inode"])
        self.sessions = {}
        self.session_states = {}
        self.pending_claims = {}
        self.lock = threading.RLock()
        with self.connection() as c:
            meta = c.execute("SELECT protocol,control_id,main_id FROM metadata WHERE singleton=1").fetchone()
            require(meta == (VERSION, binding["control_id"], binding["main_id"]),
                    "Lease control generation changed")

    @classmethod
    def provision(cls, path, main_id):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        require(type(main_id) is str and len(main_id) == 64, "Exact main workspace identity required")
        path = _path(path)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(fd)
        control_id = secrets.token_hex(32)
        # rw prevents a missing/replaced file from silently becoming a new DB.
        c = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, isolation_level=None)
        try:
            c.execute("PRAGMA journal_mode=DELETE")
            c.execute("PRAGMA synchronous=FULL")
            c.execute("BEGIN IMMEDIATE")
            for statement in _DDL:
                c.execute(statement)
            c.execute("PRAGMA user_version=1")
            c.execute("INSERT INTO metadata VALUES(1,?,?,?)", (VERSION, control_id, main_id))
            c.commit()
        finally:
            c.close()
        device, inode = _identity(path)
        binding = dict(protocol=VERSION, control_id=control_id, main_id=main_id, device=device, inode=inode)
        return cls(path, binding)

    @contextmanager
    def connection(self, *, write=False, until=None):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        require(_identity(self.path) == self.file_identity, "Lease control file identity changed")
        timeout = .2 if until is None else min(.2, max(0., until - time.monotonic()))
        c = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True,
                            isolation_level=None, timeout=timeout)
        c.row_factory = None
        try:
            require(_identity(self.path) == self.file_identity, "Lease control file changed during open")
            if write:
                c.execute("PRAGMA synchronous=FULL")
                c.execute("BEGIN IMMEDIATE")
            else:
                c.execute("BEGIN DEFERRED")
            _schema(c)
            meta = c.execute("SELECT protocol,control_id,main_id FROM metadata WHERE singleton=1").fetchone()
            require(meta == (VERSION, self.binding["control_id"], self.binding["main_id"]),
                    "Lease control generation changed")
            yield c
            require(_identity(self.path) == self.file_identity, "Lease control file changed during operation")
            if write:
                c.commit()
            else:
                c.rollback()
        except BaseException:
            if c.in_transaction:
                c.rollback()
            raise
        finally:
            c.close()

    def row(self, c, run_id):
        value = c.execute("SELECT header,nonce,state,lease_wall,absolute_deadline,sequence,intent,pending_commit,acked_commit FROM leases WHERE run_id=?", (run_id,)).fetchone()
        require(value is not None, "Missing authoritative lease row")
        return dict(zip(("header", "nonce", "state", "lease_wall", "deadline", "sequence",
                         "intent", "pending", "acked"), value, strict=True))

    def marker(self, row):
        value = row["context"].get(CONTEXT)
        require(type(value) is dict and set(value) == {"protocol", "control_id", "nonce"}
                and value["protocol"] == VERSION
                and value["control_id"] == self.binding["control_id"]
                and type(value["nonce"]) is str and len(value["nonce"]) == 64,
                "Missing or foreign authoritative lease marker")
        return value

    def _match(self, row, value):
        marker = self.marker(row)
        require(value["header"] == _wire(_header(row)) and value["nonce"] == marker["nonce"],
                "Authoritative lease owner/version/fence changed")
        return marker

    def check(self, row, *, live=True, allow_intent=False):
        with self.connection() as c:
            value = self.row(c, row["id"])
            self._match(row, value)
        if live:
            require(value["state"] == "ACTIVE" and time.time() < min(value["lease_wall"], value["deadline"])
                    and (allow_intent or value["intent"] is None), "Authoritative lease expired or stopped")
        return value

    def prepare_claim(self, row, seconds, deadline):
        require(finite(seconds) and 0 < seconds <= 30 and finite(deadline), "Finite ordinary lease required")
        header = _header(row);nonce = secrets.token_hex(32)
        started_mono, started_wall = time.monotonic(), time.time()
        lease = min(started_wall + seconds, deadline)
        require(started_wall < lease, "Claim deadline ended")
        with self.connection(write=True, until=started_mono + min(seconds, deadline-started_wall)) as c:
            prior = c.execute("SELECT state,lease_wall,intent FROM leases WHERE run_id=?", (row["id"],)).fetchone()
            # An unpublished pending claim may only be resolved by its main
            # receipt recovery, never overwritten based on elapsed time alone.
            require(prior is None or prior[0] == "CLOSED", "Unreconciled prior lease claim")
            c.execute("INSERT OR REPLACE INTO leases VALUES(?,?,?,'PENDING',?,?,0,NULL,NULL,NULL)",
                      (row["id"], _wire(header), nonce, lease, deadline))
            require(time.time() < lease and time.monotonic() < started_mono + seconds,
                    "Claim expired before control commit")
        with self.lock:
            self.pending_claims[(header, nonce)] = (started_mono, started_wall, lease, seconds)
        return dict(protocol=VERSION, control_id=self.binding["control_id"], nonce=nonce)

    def activate(self, committed_row, seconds):
        marker = self.marker(committed_row)
        header = _header(committed_row)
        with self.lock:
            prior = self.sessions.get(header)
            issued = self.pending_claims.get((header, marker["nonce"]))
        if prior is not None:
            require(prior.nonce == marker["nonce"], "Local claim generation changed")
            prior.check()
            return prior
        require(issued is not None and issued[3] == seconds,
                "A new process cannot reissue an old owner's lease clock")
        began, claimed_wall, claimed_lease, _ = issued
        require(time.monotonic() < began + min(seconds, claimed_lease-claimed_wall),
                "Claim activation exceeded original monotonic interval")
        with self.connection(write=True, until=began + .2) as c:
            value = self.row(c, committed_row["id"]);self._match(committed_row, value)
            require(committed_row["status"] == "RUNNING" and not committed_row["cancel_intent"]
                    and value["state"] == "PENDING" and value["intent"] is None
                    and time.time() < min(value["lease_wall"], value["deadline"]),
                    "Committed claim cannot activate")
            c.execute("UPDATE leases SET state='ACTIVE' WHERE run_id=?", (committed_row["id"],))
        # Mono is issued only in this process after the actual control commit;
        # persisted mono absolute values are never reused across restart.
        session = Session(self, _header(committed_row), marker["nonce"], seconds,
                          value["deadline"], value["lease_wall"], began)
        with self.lock:
            self.sessions[session.header] = session
            self.session_states[session] = session._state()
            self.pending_claims.pop((header, marker["nonce"]), None)
        return session

    def session(self, row):
        with self.lock:
            session = self.sessions.get(_header(row))
        require(type(session) is Session and session.authority is self
                and session.nonce == self.marker(row)["nonce"], "No local issued lease session")
        return session

    def command(self, row, command):
        require(command in {"pause", "cancel"}, "Unknown lease control command")
        with self.connection(write=True) as c:
            value = self.row(c, row["id"]);self._match(row, value)
            require(value["state"] == "ACTIVE" and time.time() < min(value["lease_wall"], value["deadline"]),
                    "Command lease expired")
            require(value["intent"] in {None, command}, "Conflicting lease control intent")
            c.execute("UPDATE leases SET intent=? WHERE run_id=?", (command, row["id"]))
        # No main lock or transaction is acquired while holding this lock.

    def close(self, row):
        with self.connection(write=True) as c:
            value = self.row(c, row["id"]);self._match(row, value)
            require(value["pending"] is None or value["pending"] == value["acked"],
                    "Unreconciled durable business commit")
            c.execute("UPDATE leases SET state='CLOSED' WHERE run_id=?", (row["id"],))


class Session:
    """Process-local rolling clock, issued from a committed exact claim."""

    def __init__(self, authority, header, nonce, seconds, deadline, wall, began):
        self.authority, self.header, self.nonce = authority, header, nonce
        self.seconds, self.deadline = seconds, deadline
        self.wall, self.mono = wall, began + min(seconds, wall-time.time())
        self.lock = threading.RLock()
        self.failure = None

    def _current(self, c, *, intent=False):
        self._issued()
        value = self.authority.row(c, self.header[0])
        require(value["header"] == _wire(self.header) and value["nonce"] == self.nonce
                and value["state"] == "ACTIVE" and (intent or value["intent"] is None),
                "Lease session owner/version/fence or control intent changed")
        require(self.failure is None and time.monotonic() < self.mono
                and time.time() < min(self.wall, value["lease_wall"], self.deadline, value["deadline"]),
                "Issued lease session expired")
        return value

    def _state(self):
        return (self.authority, self.header, self.nonce, self.seconds, self.deadline,
                self.wall, self.mono, self.lock, self.failure)

    def _issued(self):
        require(type(self) is Session and type(self.authority) is Authority,
                "Exact issued lease session required")
        with self.authority.lock:
            prior = self.authority.session_states.get(self)
        current = self._state()
        require(prior is not None and len(prior) == len(current)
                and all(a is b for a, b in zip(prior, current)),
                "Lease session fields or issuance changed")
        with self.authority.lock:
            require(self.authority.sessions.get(prior[1]) is self, "Lease session registration changed")

    def _remember(self):
        with self.authority.lock:
            self.authority.session_states[self] = self._state()

    def check(self):
        with self.lock, self.authority.connection() as c:
            self._current(c)
        return self.wall

    def renew(self):
        with self.lock:
            began = time.monotonic()
            with self.authority.connection(write=True, until=self.mono) as c:
                value = self._current(c)
                now = time.time();wall = min(now + self.seconds, self.deadline)
                require(now < wall, "Absolute lease deadline ended")
                changed = c.execute("UPDATE leases SET lease_wall=?,sequence=sequence+1 WHERE run_id=? AND header=? AND nonce=? AND lease_wall=? AND sequence=? AND intent IS NULL AND state='ACTIVE'",
                    (wall, self.header[0], _wire(self.header), self.nonce, value["lease_wall"], value["sequence"]))
                require(changed.rowcount == 1, "Lease renewal competed")
                # Waiting and the current DB transaction consume the OLD lease.
                self._current_before_commit(value)
            # Do not publish an interval unless its real commit returned within
            # the old monotonic/wall bound. Commit may have blocked in fsync.
            self._current_before_commit(value)
            next_mono = began + min(self.seconds, wall-time.time())
            self.wall, self.mono = wall, next_mono
            self._remember()
            return wall

    def _current_before_commit(self, prior):
        self._issued()
        require(self.failure is None and time.monotonic() < self.mono
                and time.time() < min(self.wall, prior["lease_wall"], self.deadline),
                "Lease renewal ended before publication")

    def prepare(self, commit_id):
        require(type(commit_id) is str and len(commit_id) == 64, "Exact settlement identity required")
        with self.lock, self.authority.connection(write=True, until=self.mono) as c:
            value = self._current(c)
            require(value["pending"] is None or value["pending"] == value["acked"],
                    "Prior business commit requires receipt recovery")
            require(c.execute("SELECT 1 FROM commits WHERE commit_id=?", (commit_id,)).fetchone() is None,
                    "Settlement identity already used")
            c.execute("INSERT INTO commits VALUES(?,?,?,?,'PREPARED')",
                      (commit_id, self.header[0], _wire(self.header), self.nonce))
            c.execute("UPDATE leases SET pending_commit=? WHERE run_id=?", (commit_id, self.header[0]))
            self._current_before_commit(value)
        return dict(protocol=VERSION, control_id=self.authority.binding["control_id"],
                    nonce=self.nonce, commit_id=commit_id, header=list(self.header))

    def commit(self, receipt, delegate, *, stop, clock, durable_check):
        """Only original DBAPI delegate inside the final control write lock.

        durable_check verifies the exact, still-uncommitted main receipt. A
        successful delegate is never retried, even if control acknowledgement
        fails. This serializes takeover; it is not an fsync latency guarantee.
        """
        require(type(receipt) is dict and receipt == dict(protocol=VERSION,
                control_id=self.authority.binding["control_id"], nonce=self.nonce,
                commit_id=receipt.get("commit_id"), header=list(self.header)),
                "Settlement receipt identity changed")
        committed = False
        invoked = False
        try:
            with self.lock, self.authority.connection(write=True, until=self.mono) as c:
                value = self._current(c)
                commit = c.execute("SELECT run_id,header,nonce,state FROM commits WHERE commit_id=?", (receipt["commit_id"],)).fetchone()
                require(commit == (self.header[0], _wire(self.header), self.nonce, "PREPARED")
                        and value["pending"] == receipt["commit_id"] and value["acked"] != receipt["commit_id"]
                        and not stop.is_set(),
                        "Settlement intent or stop changed")
                durable_check(receipt)
                clock()
                require(not stop.is_set(), "Settlement stopped before commit")
                self._current(c)  # Pure time checks follow all stop/callback work.
                invoked = True
                delegate()
                committed = True
                c.execute("UPDATE leases SET acked_commit=? WHERE run_id=?", (receipt["commit_id"], self.header[0]))
                c.execute("UPDATE commits SET state='ACKED' WHERE commit_id=?", (receipt["commit_id"],))
        except BaseException as error:
            if committed:
                self.failure = error
                self._remember()
                raise CommittedAckPending("Business committed; control receipt acknowledgement pending") from error
            if invoked:
                self.failure = error
                self._remember()
                raise CommitOutcomeUnknown("Business commit outcome unknown; inspect durable receipt") from error
            raise

    def recover(self, committed_row, receipt, *, durable_check):
        """Caller holds main writer; inspect receipts only, never replay effects."""
        require(_header(committed_row) == self.header, "Recovery main owner changed")
        self._issued()
        with self.lock, self.authority.connection(write=True) as c:
            value = self.authority.row(c, self.header[0])
            self.authority._match(committed_row, value)
            require(value["pending"] == receipt["commit_id"], "Unknown pending settlement")
            durable_check(receipt)
            c.execute("UPDATE leases SET acked_commit=? WHERE run_id=?", (receipt["commit_id"], self.header[0]))
            c.execute("UPDATE commits SET state='ACKED' WHERE commit_id=?", (receipt["commit_id"],))


def _seal_session_entries():
    """Keep issuance outside mutable sessions, before any role dispatch.

    This is an internal Python-role boundary, not a main receipt certificate.
    Main claim/commit provenance still has to be supplied by the Store protocol.
    """
    exact_type, get = type, object.__getattribute__
    class_get, frame = type.__getattribute__, sys._getframe
    error = DomainError
    authority_type, session_type = Authority, Session
    authorities, sessions = {}, {}
    init = Authority.__init__
    activate = Authority.activate
    state = Session._state
    renew, commit = Session.renew, Session.commit
    renew_code, commit_code = renew.__code__, commit.__code__
    namespace = globals()
    helpers = tuple((name, namespace[name], namespace[name].__code__)
                    for name in ("require", "finite", "_path", "_identity", "_header", "_wire", "_schema"))
    constants = tuple((name, namespace[name]) for name in ("VERSION", "CONTEXT", "HEADER", "_DDL"))
    functions = []
    for kind in (authority_type, session_type):
        for value in class_get(kind, "__dict__").values():
            if exact_type(value) is classmethod:
                value = value.__func__
            if exact_type(value) is FunctionType:
                functions.append(value)
                wrapped = value.__dict__.get("__wrapped__")
                if exact_type(wrapped) is FunctionType:
                    functions.append(wrapped)
    codes = tuple((f, f.__code__, f.__defaults__, f.__kwdefaults__,
                   tuple(cell.cell_contents for cell in f.__closure__ or ())) for f in functions)
    authority_roles = None
    session_roles = None

    def fail(message):
        raise error("VERSION_CONFLICT", message)

    def roles():
        for kind, expected in ((authority_type, authority_roles), (session_type, session_roles)):
            actual = class_get(kind, "__dict__")
            if len(actual) != len(expected) or any(actual.get(k) is not v for k, v in expected):
                fail("Lease class entry roles changed")
        for name, function, code in helpers:
            if namespace.get(name) is not function or function.__code__ is not code:
                fail("Lease helper entry code changed")
        if any(namespace.get(name) is not value for name, value in constants):
            fail("Lease protocol constants changed")
        for function, code, defaults, kwdefaults, closure in codes:
            if (function.__code__ is not code or function.__defaults__ is not defaults
                    or function.__kwdefaults__ is not kwdefaults):
                fail("Lease implementation code changed")
            try:
                contents = tuple(cell.cell_contents for cell in function.__closure__ or ())
            except ValueError:
                fail("Lease implementation closure changed")
            if len(contents) != len(closure) or any(a is not b for a, b in zip(contents, closure)):
                fail("Lease implementation closure changed")

    def authority_snapshot(value):
        if exact_type(value) is not authority_type:
            fail("Exact issued lease authority required")
        data = get(value, "__dict__")
        if exact_type(data) is not dict or any(exact_type(k) is not str for k in data):
            fail("Lease authority fields changed")
        return tuple(data.items()), tuple(data["binding"].items())

    def auth_guard(value):
        roles()
        if exact_type(value) is not authority_type:
            fail("Lease session authority changed")
        saved = authorities.get(value)
        if saved is None:
            fail("Unissued lease authority")
        data = get(value, "__dict__")
        if (exact_type(data) is not dict or any(exact_type(k) is not str for k in data)
                or tuple(data) != tuple(k for k, _ in saved[0])):
            fail("Lease authority fields changed")
        if any(data[k] is not v for k, v in saved[0]):
            fail("Lease authority fields changed")
        binding = data["binding"]
        if (exact_type(binding) is not dict or any(exact_type(k) is not str for k in binding)
                or tuple(binding) != tuple(k for k, _ in saved[1])
                or any(binding[k] is not v for k, v in saved[1])):
            fail("Lease authority binding changed")

    def guard(value):
        roles()
        if exact_type(value) is not session_type:
            fail("Exact issued lease session required")
        saved = sessions.get(value)
        if saved is None:
            fail("Lease session issuance changed")
        data = get(value, "__dict__")
        if (exact_type(data) is not dict or any(exact_type(k) is not str for k in data)
                or tuple(data) != saved[0]
                or any(data[k] is not v for k, v in saved[1])):
            fail("Lease session fields or issuance changed")
        auth_guard(saved[2][0])
        return saved

    def initialized(self, *args, **kwargs):
        sealed = "sim2act:lease-entry.v1"
        if sealed is None:
            raise error("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        sealed()
        if exact_type(self) is not authority_type:
            fail("Exact lease authority required")
        init(self, *args, **kwargs)
        authorities[self] = authority_snapshot(self)

    def activated(self, *args, **kwargs):
        sealed = "sim2act:lease-entry.v1"
        if sealed is None:
            raise error("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        sealed()
        auth_guard(self)
        value = activate(self, *args, **kwargs)
        if value in sessions:
            guard(value)
        else:
            data = get(value, "__dict__")
            sessions[value] = (tuple(data), tuple(data.items()), state(value))
        return value

    def checked(self):
        sealed = "sim2act:lease-entry.v1"
        if sealed is None:
            raise error("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        sealed()
        guard(self)

    def remembered(self):
        sealed = "sim2act:lease-entry.v1"
        if sealed is None:
            raise error("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        sealed()
        roles()
        if exact_type(self) is not session_type or self not in sessions:
            fail("Unissued lease session update")
        saved = sessions[self]
        auth_guard(saved[2][0])
        caller = frame(1)
        if caller.f_globals is not namespace or caller.f_locals.get("self") is not self:
            fail("Lease session update has no committed issuer")
        current = state(self)
        if any(current[i] is not saved[2][i] for i in (0, 1, 2, 3, 4, 7)):
            fail("Immutable lease session fields changed")
        if caller.f_code is renew_code:
            if (current[5] is not caller.f_locals.get("wall")
                    or current[6] is not caller.f_locals.get("next_mono")
                    or current[8] is not saved[2][8]):
                fail("Lease session has no committed renewal")
        elif caller.f_code is commit_code:
            if (current[5] is not saved[2][5] or current[6] is not saved[2][6]
                    or current[8] is not caller.f_locals.get("error")):
                fail("Lease failure publication changed")
        else:
            fail("Lease session update has no committed issuer")
        data = get(self, "__dict__")
        sessions[self] = (tuple(data), tuple(data.items()), current)
        # This map is descriptive compatibility metadata, not the issuer.
        self.authority.session_states[self] = current

    def entry(function):
        code = function.__code__
        defaults, kwdefaults = function.__defaults__, function.__kwdefaults__
        def run(self, *args, **kwargs):
            sealed = "sim2act:lease-entry.v1"
            if sealed is None:
                raise error("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
            sealed()
            guard(self)
            if (function.__code__ is not code or function.__defaults__ is not defaults
                    or function.__kwdefaults__ is not kwdefaults):
                fail("Lease session function changed")
            return function(self, *args, **kwargs)
        return run

    Authority.__init__ = initialized
    Authority.activate = activated
    Session._issued = checked
    Session._remember = remembered
    for name in ("check", "renew", "prepare", "commit", "recover", "_current", "_current_before_commit"):
        setattr(Session, name, entry(getattr(Session, name)))
    authority_roles = tuple(class_get(authority_type, "__dict__").items())
    session_roles = tuple(class_get(session_type, "__dict__").items())


def _seal_control_entries():
    from types import CodeType
    from . import _cold_source_packet as packet
    available = packet.available() and hasattr(packet.native, "lease_entry")
    native_entry = packet.native.lease_entry if available else None
    def seal(code):
        return code.replace(co_consts=tuple(native_entry if type(value) is str and value == "sim2act:lease-entry.v1"
            else seal(value) if type(value) is CodeType else value for value in code.co_consts))
    functions = [_seal_session_entries]
    for cls in (Authority, Session):
        for value in vars(cls).values():
            if type(value) is classmethod:
                value = value.__func__
            if type(value) is FunctionType:
                functions.append(value)
                wrapped = vars(value).get("__wrapped__")
                if type(wrapped) is FunctionType:
                    functions.append(wrapped)
    for function in functions:
        function.__code__ = seal(function.__code__)
    return packet, available


_CODE_PACKET, _CODE_AVAILABLE = _seal_control_entries()
_seal_session_entries()
del _seal_session_entries


def seal_functions(functions):
    """Import-time constants only; subsequent code changes fail the native pin."""
    from types import CodeType
    selected = _CODE_PACKET.native.lease_entry if _CODE_AVAILABLE else None
    actor = (_CODE_PACKET.native.lease_actor_entry
             if _CODE_AVAILABLE and hasattr(_CODE_PACKET.native, "lease_actor_entry") else None)
    def seal(code):
        return code.replace(co_consts=tuple(selected if type(value) is str and value == "sim2act:lease-entry.v1"
            else actor if type(value) is str and value == "sim2act:lease-actor-entry.v1"
            else seal(value) if type(value) is CodeType else value for value in code.co_consts))
    for function in functions:
        function.__code__ = seal(function.__code__)


_CONTROL_CODE_REGISTERED = False


def _register_control_code(runtime_module=None):
    global _CONTROL_CODE_REGISTERED
    if not _CODE_AVAILABLE:
        return
    if _CONTROL_CODE_REGISTERED:
        return
    if runtime_module is None:
        from . import _lease_control_runtime as runtime_module
    if _CONTROL_CODE_REGISTERED:
        return
    if not hasattr(runtime_module, "Runtime"):
        return  # The adapter is importing this module; it finishes registration.
    concrete_path = type(Path("."))
    # CPython 3.12 static builtins can keep tp_dict in interpreter state.
    # They are immutable; register the actual mutable heap-class roles only,
    # as the existing PB schema registration does.
    path_classes = tuple(cls for cls in dict.fromkeys((*Path.__mro__, *concrete_path.__mro__))
                         if type.__getattribute__(cls, "__flags__") & (1 << 9))
    _CODE_PACKET.register(10, globals(),
        ("require", "finite", "_path", "_identity", "_header", "_wire", "_schema",
         "_seal_control_entries", "seal_functions", "_register_control_code"),
        classes=(Authority, Session, runtime_module.Runtime, DomainError, CommittedAckPending, CommitOutcomeUnknown, *path_classes),
        constants=("VERSION", "CONTEXT", "HEADER", "_DDL", "_CODE_PACKET", "_CODE_AVAILABLE",
            "Authority", "Session", "DomainError", "CommittedAckPending", "CommitOutcomeUnknown",
            "json", "math", "os", "secrets", "sqlite3", "stat", "sys", "threading", "time", "Path", "FunctionType",
            "type", "dict", "tuple", "list", "str", "int", "float", "bool", "len", "all", "any", "set", "zip", "vars", "getattr", "hasattr", "setattr", "classmethod", "staticmethod", "object"),
        helpers=((vars(json), ("dumps", "loads")),
            (vars(runtime_module), ("require", "runtime", "marked", "_state", "_main_path", "enable", "_seal_and_register"))),
        constant_helpers=((vars(time), ("time", "monotonic")),
            (vars(sqlite3), ("connect", "Connection")),
            (vars(os), ("open", "close", "stat", "fstat", "path")),
            (vars(os.path), ("abspath",)),
            (vars(threading), ("RLock",)),
            (vars(sys), ("_getframe",)),
            (vars(_CODE_PACKET.native), ("lease_entry", "lease_actor_entry", "register_code")),
            (vars(runtime_module), ("ANCHOR", "RECEIPTS", "RECEIPT_DDL", "control", "DomainError",
                "Runtime", "_RUNTIMES", "_RUNTIME_LOCK", "_RUNTIME_STATES", "json", "secrets", "sqlite3", "threading", "weakref", "Path",
                "type", "dict", "tuple", "list", "str", "int", "float", "bool", "len", "all", "any", "set", "vars", "getattr", "hasattr", "object", "id"))))
    _CONTROL_CODE_REGISTERED = True


_register_control_code()
