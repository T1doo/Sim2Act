"""Real separate SQLite commits, not default-path or large-Cold acceptance."""

import json
import sqlite3
import sys
import threading
import time
from contextlib import contextmanager

import pytest

from sim2act._lease_control import Authority, CommittedAckPending, CommitOutcomeUnknown, CONTEXT, Session
from sim2act.errors import DomainError


def owner(tmp_path, seconds=30):
    authority = Authority.provision(tmp_path / "leases.db", "a" * 64)
    row = dict(id="run_synthetic", principal_id="user_synthetic", project_id="proj_synthetic",
               runtime_id="runtime_synthetic", worker_id="worker_synthetic", fence=1,
               version=1, status="RUNNING", cancel_intent=False, context={})
    row["context"][CONTEXT] = authority.prepare_claim(row, seconds, time.time() + 60)
    session = authority.activate(row, seconds)
    return authority, row, session


def test_real_control_renewal_does_not_invalidate_business_wal_upgrade(tmp_path):
    authority, row, session = owner(tmp_path)
    main = sqlite3.connect(tmp_path / "business.db", isolation_level=None)
    try:
        assert main.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        main.execute("CREATE TABLE result(value INTEGER)")
        main.execute("INSERT INTO result VALUES(1)")
        main.execute("BEGIN DEFERRED")
        assert main.execute("SELECT value FROM result").fetchone() == (1,)
        before = main.total_changes
        old = session.wall
        assert session.renew() > old
        assert main.total_changes == before
        main.execute("UPDATE result SET value=2")
        main.commit()
        assert main.execute("SELECT value FROM result").fetchone() == (2,)
        assert authority.check(row)["sequence"] == 1
    finally:
        main.close()


@pytest.mark.parametrize("command", ["pause", "cancel"])
def test_committed_control_intent_rejects_old_renewal_and_commit(tmp_path, command):
    authority, row, session = owner(tmp_path)
    receipt = session.prepare("b" * 64)
    authority.command(row, command)
    with pytest.raises(DomainError, match="control intent"):
        session.renew()
    invoked = []
    with pytest.raises(DomainError, match="control intent"):
        session.commit(receipt, lambda: invoked.append(True), stop=threading.Event(),
                       clock=lambda: None, durable_check=lambda _: None)
    assert invoked == [] and authority.check(row, live=False)["intent"] == command


def test_real_expiry_cannot_renew_or_reissue_process_clock(tmp_path):
    authority, row, session = owner(tmp_path, .12)
    threading.Event().wait(.15)
    with pytest.raises(DomainError, match="expired"):
        session.renew()
    fresh = Authority(authority.path, authority.binding)
    with pytest.raises(DomainError, match="cannot reissue"):
        fresh.activate(row, .12)


def test_real_absolute_monotonic_cutoff_never_moves_with_renewal(tmp_path):
    authority = Authority.provision(tmp_path / "absolute-leases.db", "d" * 64)
    row = dict(id="run_absolute", principal_id="user_synthetic", project_id="proj_synthetic",
        runtime_id="runtime_synthetic", worker_id="worker_synthetic", fence=1,
        version=1, status="RUNNING", cancel_intent=False, context={})
    row["context"][CONTEXT] = authority.prepare_claim(row, 1, time.time() + .4)
    session = authority.activate(row, 1)
    absolute = session.absolute_mono
    threading.Event().wait(.08)
    session.renew()
    assert session.absolute_mono is absolute and session.mono <= absolute
    threading.Event().wait(max(0, absolute-time.monotonic()) + .02)
    with pytest.raises(DomainError, match="expired|ended"):
        session.renew()
    assert authority.check(row, live=False)["sequence"] == 1


def test_direct_or_mutated_session_is_not_an_issued_owner(tmp_path):
    authority, row, session = owner(tmp_path)
    forged = Session(authority, session.header, session.nonce, 30, session.deadline,
                     session.wall, time.monotonic())
    with pytest.raises(DomainError, match="issuance"):
        forged.check()
    session.wall += 60
    with pytest.raises(DomainError, match="issuance"):
        session.check()


def test_missing_control_file_never_recreates_or_uses_legacy(tmp_path):
    authority, row, session = owner(tmp_path)
    renamed = authority.path.with_suffix(".preserved")
    authority.path.rename(renamed)
    with pytest.raises(DomainError, match="storage unavailable"):
        session.check()
    assert not authority.path.exists() and renamed.exists()


@pytest.mark.parametrize("failure", ["ack", "delegate"])
def test_business_commit_success_ack_failure_is_not_a_rollback(tmp_path, failure):
    authority, row, session = owner(tmp_path)
    receipt = session.prepare("c" * 64)
    main_path = tmp_path / "business.db"
    main = sqlite3.connect(main_path, isolation_level=None)
    main.execute("CREATE TABLE receipts(commit_id TEXT PRIMARY KEY,receipt TEXT NOT NULL)")
    main.execute("BEGIN IMMEDIATE")
    main.execute("INSERT INTO receipts VALUES(?,?)", (receipt["commit_id"], json.dumps(receipt, sort_keys=True)))
    calls, denied = [], []
    def reject_ack(action, table, column, database, origin):
        if action == sqlite3.SQLITE_UPDATE and table in {"leases", "commits"}:
            denied.append((action, table, column))
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    def commit():
        calls.append(True)
        main.commit()
        if failure == "delegate":
            raise OSError("Synthetic delegate failure after actual main commit")
        # Portable actual ACK failure: Windows correctly refuses renaming a
        # database while this control writer is open. Deny only its later ACK
        # UPDATE, after the genuine business commit has returned successfully.
        frame = sys._getframe(1)
        assert frame.f_locals["self"] is session and frame.f_locals["receipt"] is receipt
        control = frame.f_locals["c"]
        assert isinstance(control, sqlite3.Connection)
        control.set_authorizer(reject_ack)
    def check(value):
        saved = main.execute("SELECT receipt FROM receipts WHERE commit_id=?", (value["commit_id"],)).fetchone()
        assert saved is not None and json.loads(saved[0]) == value
    try:
        with pytest.raises(CommittedAckPending if failure == "ack" else CommitOutcomeUnknown):
            session.commit(receipt, commit, stop=threading.Event(), clock=lambda: None, durable_check=check)
        assert calls == [True] and not main.in_transaction
        assert bool(denied) is (failure == "ack")
        assert authority.check(row, live=False)["acked"] is None
        main.execute("BEGIN IMMEDIATE")
        session.recover(row, receipt, durable_check=check)
        main.commit()
        assert authority.check(row, live=False)["acked"] == receipt["commit_id"]
        assert calls == [True]
        with sqlite3.connect(main_path) as fresh:
            assert fresh.execute("SELECT count(*) FROM receipts").fetchone() == (1,)
    finally:
        main.close()


def test_acknowledged_receipt_cannot_enter_commit_delegate_again(tmp_path):
    authority, row, session = owner(tmp_path)
    receipt = session.prepare("d" * 64)
    calls = []
    session.commit(receipt, lambda: calls.append(True), stop=threading.Event(),
                   clock=lambda: None, durable_check=lambda _: None)
    with pytest.raises(DomainError):
        session.commit(receipt, lambda: calls.append(True), stop=threading.Event(),
                       clock=lambda: None, durable_check=lambda _: None)
    assert calls == [True]


def test_stop_callback_cannot_consume_last_lease_then_allow_commit(tmp_path):
    authority, row, session = owner(tmp_path, .12)
    receipt = session.prepare("e" * 64)
    calls = []
    class SlowStop:
        def is_set(self):
            threading.Event().wait(.08)
            return False
    with pytest.raises(DomainError):
        session.commit(receipt, lambda: calls.append(True), stop=SlowStop(),
                       clock=lambda: None, durable_check=lambda _: None)
    assert calls == []


@pytest.mark.parametrize("field", ["lock", "authority"])
def test_foreign_session_role_is_rejected_before_dispatch(tmp_path, field):
    authority, row, session = owner(tmp_path)
    calls = []
    class Foreign:
        def __enter__(self):calls.append("lock");return self
        def __exit__(self, *_):return False
        def connection(self, **_):calls.append("connection");return self
    setattr(session, field, Foreign())
    with pytest.raises(DomainError):session.check()
    assert calls == []


def test_direct_remember_cannot_authorize_an_extended_session_clock(tmp_path):
    authority, row, session = owner(tmp_path)
    session.mono += 300
    with pytest.raises(DomainError):session._remember()
