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
from builtins import type, dict, tuple, list, str, int, float, bool, len, all, any, set, vars, getattr, hasattr, object, id, min, max

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
    store._authoritative_lease_runtime = selected
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

    def bind_claim(self, claimed, *, owner_stop=None):
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
            self.store.event(c, actual["id"], "LOCAL_LEASE_CONTROL_CLAIM",
                             dict(header=list(expected), marker=marker))
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
            self.authority.activate(committed, self.seconds, owner_stop=owner_stop)
        return committed

    def _bind_boundary(self, boundary, c, row):
        entry = "sim2act:lease-entry.v1"
        entry()
        state = _state(self)
        require(state["store"].owns_connection(c) and c.in_transaction(), "Original lease writer required")
        session = Runtime.session(self, row)
        if session.owner_stop is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Authoritative lease execution is not enabled")
        require(type(session.owner_stop) is threading.Event, "Original worker stop event required")
        until = min(session.deadline, row["created_at"] + state["run_seconds"])
        mono = session.absolute_mono
        snapshot = c.info.get("local_model_snapshot")
        if snapshot is not None and snapshot.settlement_interval is not None:
            mono = min(mono, snapshot.settlement_interval[0])
            until = min(until, snapshot.settlement_interval[1])
        binding = (self, session, control._wire(control._header(row)), session.nonce, session.owner_stop,
            mono, until, None, None, row["id"], None)
        install = "sim2act:commit-control-bind.v1"
        require(install is not None, "Native commit fence unavailable")
        install(boundary, binding, c)

    def _seed_boundary(self, boundary, c, *, effect=None):
        entry = "sim2act:lease-entry.v1"
        entry()
        _state(self)
        read = "sim2act:commit-control-read.v1"
        update_binding = "sim2act:commit-control-bind.v1"
        binding = read(boundary)
        require(binding is not None and binding[0] is self and self.store.owns_connection(c)
                and c.connection.driver_connection.in_transaction, "Original prepared main writer required")
        if binding[7] is not None:
            Runtime._validate_boundary(self, boundary, c)
            return
        from .db import runs
        post = dict(c.execute(select(runs).where(runs.c.id == binding[9])).mappings().one())
        header = control._header(post)
        before = tuple(json.loads(binding[2]))
        require(header[:-1] == before[:-1] and (header[-1] == before[-1]
                or header[-1] == before[-1] + 1 and post["status"] != "RUNNING")
                and post["context"][control.CONTEXT]["nonce"] == binding[3],
                "Final Run owner/version changed")
        receipt = binding[1].prepare(secrets.token_hex(32))
        wire = control._wire(receipt)
        # This protocol metadata write is explicit and precedes full post-G1.
        c.execute(text("INSERT INTO " + RECEIPTS + " VALUES(:key,:control,:run,:nonce,:header,:receipt)"),
            dict(key=receipt["commit_id"], control=receipt["control_id"], run=post["id"],
                 nonce=receipt["nonce"], header=control._wire(tuple(receipt["header"])), receipt=wire))
        post_wire = control._wire(post)
        # Own the complete final proof inputs as bytes; no mutable graph or
        # validation result is retained in the control scope.
        effect = None if effect is None else control._wire(effect)
        binding = (*binding[:7], wire, post_wire, binding[9], (receipt["commit_id"], effect))
        update_binding(boundary, binding, c)

    def _validate_boundary(self, boundary, c):
        entry = "sim2act:lease-entry.v1"
        entry()
        _state(self)
        read = "sim2act:commit-control-read.v1"
        binding = read(boundary)
        require(binding is not None and binding[0] is self and binding[7] is not None
                and self.store.owns_connection(c), "Final prepared scope changed")
        receipt = json.loads(binding[7])
        require(Runtime._receipt(self, c, receipt["commit_id"]) == receipt,
                "Actual uncommitted main receipt changed")
        from .db import runs
        post = dict(c.execute(select(runs).where(runs.c.id == binding[9])).mappings().one())
        require(control._wire(post) == binding[8], "Final main Run postimage changed")

    def _abort_boundary(self, boundary, c):
        entry = "sim2act:lease-entry.v1"
        entry()
        _state(self)
        read = "sim2act:commit-control-read.v1"
        binding = read(boundary)
        require(binding[0] is self and self.store.owns_connection(c)
                and not c.connection.driver_connection.in_transaction,
                "Main rollback must precede aborting control intent")
        if binding[7] is None:
            return
        receipt = json.loads(binding[7])
        with self.authority.connection(write=True) as ctrl:
            value = self.authority.row(ctrl, binding[9])
            require(value["header"] == binding[2] and value["nonce"] == binding[3]
                    and value["pending"] == receipt["commit_id"]
                    and value["acked"] != receipt["commit_id"], "Abort generation changed")
            changed = ctrl.execute("UPDATE commits SET state='ABORTED' WHERE commit_id=? AND state='PREPARED'",
                                  (receipt["commit_id"],))
            require(changed.rowcount == 1, "Abort intent changed")
            ctrl.execute("UPDATE leases SET pending_commit=acked_commit WHERE run_id=?", (binding[9],))

    def publish_command(self, principal, run_id, command, version, *, iid=None):
        """Durable stop intent before waiting for the business writer.

        The control writer serializes this fresh committed-owner read with the
        final business commit. It never waits for a main writer in this order.
        """
        entry = "sim2act:lease-entry.v1"
        entry()
        _state(self)
        if command not in {"pause", "cancel"}:
            return
        with self.authority.connection(write=True) as c:
            actual = Runtime.committed_run(self, run_id)
            require(actual["principal_id"] == principal, "Command owner changed")
            require(actual["version"] == version, "Command version changed")
            if not marked(actual):
                return
            with Runtime._main(self) as main:
                owner = main.execute("SELECT p.owner_id FROM runs r JOIN projects p ON p.id=r.project_id WHERE r.id=? AND r.principal_id=?",
                                     (run_id, principal)).fetchone()
                require(owner == (principal,), "Command project owner changed")
                if iid is not None:
                    association = main.execute("""SELECT a.instance_id,json_extract(b.snapshot,'$.instance_id')
                        FROM internal_run_bindings b JOIN internal_app_runs a ON a.id=b.app_run_id
                        JOIN internal_instances i ON i.id=a.instance_id JOIN runs r ON r.id=b.run_id
                        WHERE b.run_id=? AND a.principal_id=? AND i.principal_id=? AND i.project_id=r.project_id
                          AND i.runtime_id=r.runtime_id AND i.id=?""", (run_id, principal, principal, iid)).fetchone()
                    require(association == (iid, iid), "Command instance scope changed")
            value = self.authority.row(c, run_id)
            self.authority._match(actual, value)
            if actual["status"] != "RUNNING":
                return  # Original command handler validates its state/replay.
            require(value["state"] == "ACTIVE" and value["intent"] in {None, command},
                    "Command control generation changed")
            c.execute("UPDATE leases SET intent=? WHERE run_id=?", (command, run_id))

    def retire_owner(self, c, row):
        """Actual main writer excludes late commits; never reissue old clocks.

        Closing control before main reconciliation is fail-closed on a crash:
        a later writer can repeat reconciliation, but no old worker can commit.
        """
        entry = "sim2act:lease-entry.v1"
        entry()
        _state(self)
        require(self.store.owns_connection(c) and c.connection.driver_connection.in_transaction,
                "Original main writer required for owner retirement")
        with self.authority.connection(write=True) as ctrl:
            value = self.authority.row(ctrl, row["id"])
            before = tuple(json.loads(value["header"]))
            current = control._header(row)
            require(current[:-1] == before[:-1] and (current[-1] == before[-1]
                    or current[-1] == before[-1]+1 and value["intent"] in {"pause", "cancel"})
                    and self.authority.marker(row)["nonce"] == value["nonce"],
                    "Retirement owner/version changed")
            if value["state"] == "ACTIVE" and value["intent"] is None and control.time.time() < min(
                    value["lease_wall"], value["deadline"]):
                return False
            if value["pending"] is not None and value["pending"] != value["acked"]:
                key = value["pending"]
                receipt = Runtime._receipt(self, c, key)
                if receipt is None:
                    changed = ctrl.execute("UPDATE commits SET state='ABORTED' WHERE commit_id=? AND state='PREPARED'", (key,))
                    require(changed.rowcount == 1, "Unknown missing main commit receipt")
                    ctrl.execute("UPDATE leases SET pending_commit=acked_commit WHERE run_id=?", (row["id"],))
                else:
                    require(receipt["nonce"] == value["nonce"] and control._wire(tuple(receipt["header"])) == value["header"],
                            "Retirement main receipt changed")
                    changed = ctrl.execute("UPDATE commits SET state='ACKED' WHERE commit_id=? AND state='PREPARED'", (key,))
                    require(changed.rowcount == 1, "Unknown durable commit outcome")
                    ctrl.execute("UPDATE leases SET acked_commit=? WHERE run_id=?", (key, row["id"]))
            ctrl.execute("UPDATE leases SET state='CLOSED' WHERE run_id=?", (row["id"],))
            return dict(intent=value["intent"], deadline=value["deadline"])

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
        require(type(row) is dict and marked(row), "Explicit authoritative lease Run required")
        # Session issuance/header/marker are checked before its one fresh
        # authority read. _current revalidates every live fact, stop and both
        # clocks; no verdict survives this call. Runtime.session's additional
        # early authority read is needed by its other callers, not here.
        return control.Authority.session(self.authority, row).check()

    def heartbeat(self, worker_id, run_id, fence, version, seconds, *, deadline=None):
        """Fresh committed main owner/authorization; renewal writes control only.

        The main Run lease is historical graph input. Never update it while a
        business WAL reader/writer owns that graph or use an uncommitted main
        heartbeat as evidence of renewal.
        """
        entry = "sim2act:lease-entry.v1"
        if entry is None:
            raise DomainError("UNSUPPORTED_CAPABILITY", "Qualified native lease control is unavailable")
        entry()
        state = _state(self)
        require(type(worker_id) is str and worker_id and type(run_id) is str
                and type(fence) is int and fence >= 1 and type(version) is int and version >= 1
                and control.finite(seconds) and seconds == state["seconds"]
                and (deadline is None or control.finite(deadline)),
                "Exact original heartbeat identity and configuration required")
        node_mono = (None if deadline is None else control.time.monotonic()
                     + max(0, deadline-control.time.time()))
        from .db import Store, runs
        from .goal_applications import source_scope_gate
        with state["engine"].connect() as c:
            c.exec_driver_sql("BEGIN DEFERRED")
            changes = c.connection.driver_connection.total_changes
            source_scope_gate(state["store"], c, run_id)
            actual = dict(c.execute(select(runs).where(runs.c.id == run_id)).mappings().one())
            require(actual["worker_id"] == worker_id and actual["fence"] == fence
                    and actual["version"] == version and actual["status"] == "RUNNING"
                    and not actual["cancel_intent"] and marked(actual),
                    "Authoritative heartbeat Run owner/version/state changed")
            frozen = Store._frozen_contract_after_scope(state["store"], c, actual)
            for resource in actual["resource_refs"]:
                Store.authorize(state["store"], c, actual["principal_id"], actual["runtime_id"],
                    actual["project_id"], resource, "resource.read")
            session = Runtime.session(self, actual)
            require(session.deadline <= min(actual["created_at"] + state["run_seconds"],
                    actual["created_at"] + frozen.limits.run_seconds),
                    "Original absolute heartbeat deadline changed")
            require(deadline is None or control.time.time() < min(deadline, session.deadline),
                    "Original heartbeat node deadline ended")
            require(c.connection.driver_connection.total_changes == changes,
                    "Authoritative heartbeat attempted a main write")
            renewed = session.renew()
            require(deadline is None or control.time.time() < min(deadline, session.deadline),
                    "Original heartbeat node deadline ended before publication")
        # No stale state is published if the committed main owner changed
        # while the control-only renewal was being committed.
        current = Runtime.committed_run(self, run_id)
        require(control._header(current) == control._header(actual)
                and current["status"] == "RUNNING" and not current["cancel_intent"]
                and current["context"][control.CONTEXT] == actual["context"][control.CONTEXT],
                "Authoritative heartbeat main owner changed before publication")
        # Renewal is liveness only, never a Grant or reusable validation PASS.
        # Re-read current authorization after the control commit. The original
        # business graph and final writer still perform their own full checks.
        with state["engine"].connect() as c:
            c.exec_driver_sql("BEGIN DEFERRED")
            changes = c.connection.driver_connection.total_changes
            source_scope_gate(state["store"], c, run_id)
            late = dict(c.execute(select(runs).where(runs.c.id == run_id)).mappings().one())
            require(control._header(late) == control._header(actual)
                    and late["status"] == "RUNNING" and not late["cancel_intent"]
                    and late["context"][control.CONTEXT] == actual["context"][control.CONTEXT],
                    "Authoritative heartbeat owner changed during final validation")
            late_frozen = Store._frozen_contract_after_scope(state["store"], c, late)
            require(session.deadline <= min(late["created_at"] + state["run_seconds"],
                    late["created_at"] + late_frozen.limits.run_seconds),
                    "Original absolute heartbeat deadline changed")
            for resource in late["resource_refs"]:
                Store.authorize(state["store"], c, late["principal_id"], late["runtime_id"],
                    late["project_id"], resource, "resource.read")
            require(c.connection.driver_connection.total_changes == changes,
                    "Final heartbeat validation attempted a main write")
        session.check()
        require(deadline is None or (control.time.monotonic() < node_mono
                    and control.time.time() < min(deadline, session.deadline)),
                "Original heartbeat node deadline ended before final publication")
        return renewed

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
