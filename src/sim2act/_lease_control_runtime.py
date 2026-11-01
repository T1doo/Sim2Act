"""Explicit local protocol adapter; legacy databases keep their original lease.

This adapter is not a permission provider. It binds control generations and
claim/commit receipts to the actual original main SQLite database.
"""

import hashlib
import json
import secrets
import sqlite3
import threading
import weakref
from pathlib import Path
from builtins import type, dict, tuple, list, str, int, float, bool, len, all, any, set, vars, getattr, hasattr, object, id

from sqlalchemy import select, text, update

from . import _lease_control as control
from .errors import DomainError

ANCHOR = "LOCAL_LEASE_CONTROL_V1"
RECEIPTS = "local_lease_control_receipts"
RECEIPT_DDL = "CREATE TABLE local_lease_control_receipts(commit_id TEXT PRIMARY KEY,control_id TEXT NOT NULL,run_id TEXT NOT NULL,nonce TEXT NOT NULL,header TEXT NOT NULL,receipt TEXT NOT NULL)"
_RUNTIMES = weakref.WeakKeyDictionary()
_RUNTIME_LOCK = threading.RLock()


def require(ok, message):
    if not ok:
        raise DomainError("VERSION_CONFLICT", message)


def runtime(store):
    entry = "sim2act:lease-entry.v1"
    if entry is None:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
    entry()
    with _RUNTIME_LOCK:
        return _RUNTIMES.get(store)


def marked(row):
    context = row.get("context")
    return type(context) is dict and control.CONTEXT in context


def _state(value):
    current = "sim2act:lease-runtime-current.v1"
    require(current is not None, "Qualified runtime provenance unavailable")
    return dict(current(value))


def _main_path(store):
    from .db import Store
    require(type(store) is Store and store.test_only and store.sqlite
            and store.engine.url.drivername == "sqlite"
            and store.engine.url.database not in (None, "", ":memory:")
            and not store.engine.url.database.startswith("file:"),
            "Lease control requires an explicit test-only file SQLite workspace")
    path = control._path(Path(store.engine.url.database))
    control._identity(path)
    return path


def enable(store, settings, *, create=False):
    """Explicit provisioning/open only; no automatic existing-data migration."""
    entry = "sim2act:lease-entry.v1"
    if entry is None:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
    entry()
    from .config import Settings
    from .db import events, runs
    actor = "sim2act:lease-actor-entry.v1"
    if actor is None:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified lease actor is unavailable")
    actor()
    require(type(settings) is Settings and control.finite(settings.lease_seconds)
            and control.finite(settings.run_seconds) and 0 < settings.lease_seconds <= 30
            and 0 < settings.run_seconds <= 300,
            "Original finite worker configuration required")
    require(runtime(store) is None, "Lease protocol already opened")
    path = _main_path(store)
    store._enable_local_model_snapshots()
    identity = control._identity(path)
    seconds, run_seconds = settings.lease_seconds, settings.run_seconds
    uri, engine = path.as_uri(), store.engine
    control_path = path.with_name(path.name + ".leases-v1.sqlite")
    if create:
        with store.tx() as c:
            require(c.execute(select(events.c.id).where(events.c.kind == ANCHOR,
                    events.c.run_id.is_(None))).first() is None, "Existing lease generation cannot be replaced")
            require(c.execute(select(runs.c.id).where(runs.c.status.in_(
                ["RUNNING", "PAUSE_REQUESTED", "CANCEL_REQUESTED", "RECONCILING"]))).first() is None,
                "Active legacy owners must finish before protocol provisioning")
            main_id = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
            authority = control.Authority.provision(control_path, main_id)
            c.exec_driver_sql(RECEIPT_DDL)
            record = dict(binding=authority.binding, main_device=identity[0], main_inode=identity[1])
            store.event(c, None, ANCHOR, record)
        # If the main commit failed, the orphan control file is preserved and
        # cannot authorize anything. Never recreate/overwrite either file.
    with store.engine.connect() as c:
        records = c.execute(select(events.c.data).where(events.c.kind == ANCHOR,
                             events.c.run_id.is_(None))).scalars().all()
        require(len(records) == 1 and type(records[0]) is dict, "Missing or duplicate main lease binding")
        record = records[0]
        require(set(record) == {"binding", "main_device", "main_inode"}
                and (record["main_device"], record["main_inode"]) == identity,
                "Main workspace identity changed")
        actual = c.exec_driver_sql("SELECT sql FROM sqlite_schema WHERE name=?", (RECEIPTS,)).scalar_one()
        require(actual == RECEIPT_DDL, "Unknown main lease receipt schema")
        require(c.exec_driver_sql("SELECT 1 FROM sqlite_schema WHERE type='trigger' AND tbl_name=?", (RECEIPTS,)).first() is None,
                "Main lease receipt triggers are unsupported")
    authority = control.Authority(control_path, record["binding"])
    selected = Runtime(store, authority, path, identity, seconds, run_seconds, uri, engine)
    install = "sim2act:lease-runtime-install.v1"
    require(install is not None, "Qualified runtime issuer unavailable")
    install(selected)
    with _RUNTIME_LOCK:
        _RUNTIMES[store] = selected
    return selected


class Runtime:
    def __init__(self, store, authority, path, identity, seconds, run_seconds, uri, engine):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        require(type(self) is Runtime, "Exact lease runtime required")
        self.store, self.authority = store, authority
        self.path, self.identity = path, identity
        self.seconds, self.run_seconds = seconds, run_seconds
        self.uri, self.engine = uri, engine

    def _main(self):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        state = _state(self)
        require(control._identity(state["path"]) == state["identity"], "Main workspace file identity changed")
        return sqlite3.connect(state["uri"] + "?mode=ro", uri=True,
                               isolation_level=None, timeout=.2)

    def committed_run(self, run_id):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        _state(self)
        # No main writer or FIFO gate: metadata from one real committed WAL read.
        c = Runtime._main(self)
        try:
            c.row_factory = sqlite3.Row
            c.execute("BEGIN DEFERRED")
            row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            require(row is not None, "Missing committed lease Run")
            value = dict(row)
            for key in ("context", "resource_refs", "result", "error"):
                if value.get(key) is not None:
                    value[key] = json.loads(value[key])
            require(type(value["cancel_intent"]) is int and value["cancel_intent"] in (0, 1),
                    "Invalid committed control intent flag")
            value["cancel_intent"] = bool(value["cancel_intent"])
            return value
        finally:
            c.close()

    def bind_claim(self, claimed):
        """Called before a newly claimed owner is returned to its Worker.

        Pending control -> durable main marker -> active control. Each crash
        leaves a finite, non-executable pending record until explicit recovery.
        """
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        _state(self)
        from .db import runs
        from time import monotonic, time
        cutoff = (monotonic() + min(self.seconds, claimed["lease_until"]-time()), claimed["lease_until"])
        absolute = []
        def clock():
            require(monotonic() < cutoff[0] and time() < min(cutoff[1], *absolute),
                    "Original owner expired during claim handoff")
        expected = control._header(claimed)
        with self.store.tx(_commit_clock_check=clock) as c:
            actual = self.store.guard(c, claimed["id"], claimed["fence"])
            require(control._header(actual) == expected and not marked(actual)
                    and actual["status"] == "RUNNING" and not actual["cancel_intent"],
                    "Claim changed before authority handoff")
            frozen = self.store.frozen_contract(c, actual)
            deadline = min(actual["created_at"] + self.run_seconds,
                           actual["created_at"] + frozen.limits.run_seconds)
            absolute.append(deadline)
            marker = self.authority.prepare_claim(actual, self.seconds, deadline)
            context = dict(actual["context"]);context[control.CONTEXT] = marker
            changed = c.execute(update(runs).where(runs.c.id == actual["id"],
                runs.c.worker_id == actual["worker_id"], runs.c.fence == actual["fence"],
                runs.c.version == actual["version"], runs.c.status == "RUNNING",
                runs.c.cancel_intent.is_(False), runs.c.lease_until == actual["lease_until"])
                .values(context=context))
            require(changed.rowcount == 1, "Claim handoff competed")
        # Hold the actual main writer across the fresh read and activation.
        # No main DML occurs in this segment; a competing version/intent cannot
        # slip between receipt inspection and issuing the process-local clock.
        def no_activation_write():
            require(raw.total_changes == changes, "Main activation barrier wrote protected data")
        with self.store.tx(_commit_check=no_activation_write, _commit_clock_check=clock) as c:
            raw = c.connection.driver_connection
            changes = raw.total_changes
            committed = dict(c.execute(select(runs).where(runs.c.id == claimed["id"])).mappings().one())
            no_activation_write()
            require(control._header(committed) == expected
                    and committed["status"] == "RUNNING" and not committed["cancel_intent"]
                    and committed["context"][control.CONTEXT] == marker,
                    "Main claim receipt changed before activation")
            self.authority.activate(committed, self.seconds)
        return committed

    def session(self, row):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        _state(self)
        require(marked(row), "Explicit authoritative lease Run required")
        self.authority.check(row)
        return self.authority.session(row)

    def lease(self, row):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        _state(self)
        return Runtime.session(self, row).check()

    def _receipt(self, c, commit_id):
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        _state(self)
        row = c.execute(text("SELECT control_id,run_id,nonce,header,receipt FROM " + RECEIPTS +
                             " WHERE commit_id=:key"), dict(key=commit_id)).mappings().one_or_none()
        if row is None:
            return None
        value = json.loads(row["receipt"])
        require(type(value) is dict and value == dict(protocol=control.VERSION,
                control_id=row["control_id"], nonce=row["nonce"], commit_id=commit_id,
                header=json.loads(row["header"])) and value["header"][0] == row["run_id"]
                and value["control_id"] == self.authority.binding["control_id"],
                "Malformed durable main lease receipt")
        return value

    def recover_committed(self, c, commit_id):
        """Fresh-process positive acknowledgement from actual main data only.

        Never issues an old mono clock, invokes a supplied callback/delegate,
        claims a Run, or replays an effect. Negative/ambiguous recovery refuses.
        """
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        _state(self)
        require(self.store.owns_connection(c) and c.in_transaction()
                and c.connection.driver_connection.in_transaction,
                "Original main recovery transaction required")
        # The caller may have inserted a receipt and then roll back. Only an
        # independent WAL reader proves that this receipt really committed.
        with self.engine.connect() as durable:
            receipt = Runtime._receipt(self, durable, commit_id)
        require(receipt is not None, "No durable main receipt; commit outcome remains unknown")
        with self.authority.connection(write=True) as selected:
            value = self.authority.row(selected, receipt["header"][0])
            require(value["header"] == control._wire(tuple(receipt["header"]))
                    and value["nonce"] == receipt["nonce"] and value["pending"] == commit_id,
                    "Durable receipt belongs to another lease generation")
            actual = selected.execute("SELECT run_id,header,nonce,state FROM commits WHERE commit_id=?",
                                      (commit_id,)).fetchone()
            require(actual is not None and actual[:3] == (receipt["header"][0],
                    control._wire(tuple(receipt["header"])), receipt["nonce"])
                    and actual[3] in {"PREPARED", "ACKED"}, "Unknown control commit intent")
            selected.execute("UPDATE commits SET state='ACKED' WHERE commit_id=?", (commit_id,))
            selected.execute("UPDATE leases SET acked_commit=? WHERE run_id=?",
                             (commit_id, receipt["header"][0]))
        return receipt


def _seal_and_register():
    import sys
    from types import FunctionType
    functions = [require, runtime, marked, _state, _main_path, enable]
    functions.extend(value for value in vars(Runtime).values() if type(value) is FunctionType)
    control.seal_functions(functions)
    control._register_control_code(sys.modules[__name__])
    if control._CODE_AVAILABLE:
        control._CODE_PACKET.native.register_lease_runtime(Runtime, enable)


_seal_and_register()
