"""Pure guard units: no Sim2Act, fixture imports, transport or business G0."""

import contextlib
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from g0_bounded import SCOPE, cleanup, proc_identity, signal_owned, validate_grant
from g0_guard import (
    FILES,
    LIMITS,
    Boundary,
    BoundedWriter,
    Budget,
    DiskMonitor,
    G0Stop,
    MockBudget,
    StopBoundary,
    guarded_connection_class,
)


class FakeDomainError(Exception):
    code = "ORIGINAL"
    message = "exact original refusal"


class ProtectionUnits(unittest.TestCase):
    def tearDown(self):
        self.assertFalse(any(k == "sim2act" or k.startswith("sim2act.") for k in sys.modules))

    def test_limits_reserve_all_files_under_directory_cap(self):
        self.assertLess(4 * 12 * 1024**2 + sum(FILES.values()), LIMITS["directory_bytes"])

    def test_mock_order_counts_and_permanent_close(self):
        b = MockBudget()
        for _ in range(3):
            b.enter(asynchronous=True, exact_transport=True)
        b.stage = "source"
        for _ in range(2):
            b.enter(asynchronous=True, exact_transport=True)
            b.enter(asynchronous=False, exact_transport=True)
        b.stage = "cold"
        b.enter(asynchronous=True, exact_transport=True)
        b.close()
        self.assertEqual((b.exchanges, b.methods), (6, 8))
        for asynchronous in (True, False):
            with self.assertRaises(Boundary):
                b.enter(asynchronous=asynchronous, exact_transport=True)
        self.assertEqual((b.exchanges, b.methods), (6, 8))

    def test_mock_unrelated_transport_and_wrong_stage_deny_before_consume(self):
        b = MockBudget()
        for asynchronous, exact in ((True, False), (False, True)):
            with self.assertRaises(Boundary):
                b.enter(asynchronous=asynchronous, exact_transport=exact)
        b.stage = "cold"
        with self.assertRaises(Boundary):
            b.enter(asynchronous=True, exact_transport=True)
        self.assertEqual((b.methods, b.exchanges), (0, 0))

    def test_clock_no_reset_on_phase_or_late_entry(self):
        now = [0.0]
        b = Budget(0, lambda: now[0])
        self.assertEqual(b.deadline, 480)
        now[0] = 400
        b.enter_g0(400)
        self.assertEqual(b.deadline, 520)
        with self.assertRaises(Boundary):
            b.enter_g0(401)
        now[0] = 520
        with self.assertRaises(Boundary):
            b.check()
        late = Budget(0, lambda: 500)
        with self.assertRaises(Boundary):
            late.enter_g0(480)

    def test_writer_reserves_bytes_before_write_and_never_truncates(self):
        stream = io.BytesIO()
        writer = BoundedWriter(stream, 4)
        writer.write(b"123")
        with self.assertRaises(Boundary):
            writer.write(b"45")
        self.assertEqual(stream.getvalue(), b"123")
        self.assertEqual(writer.used, 3)

    def test_short_writes_complete_or_fail_with_consumed_budget(self):
        class Short(io.BytesIO):
            def write(self, raw):
                return super().write(raw[:1])

        stream = Short()
        writer = BoundedWriter(stream, 4)
        writer.write(b"1234")
        self.assertEqual(stream.getvalue(), b"1234")

        class Broken(io.BytesIO):
            def write(self, raw):
                return 0

        writer = BoundedWriter(Broken(), 4)
        with self.assertRaises(Boundary):
            writer.write(b"1234")
        self.assertEqual(writer.used, 4)

    def test_cached_sql_and_direct_dbapi_writes_denied_rollback_allowed(self):
        c = sqlite3.connect(":memory:", factory=guarded_connection_class())
        try:
            c.execute("create table t (x integer)")
            c.execute("insert into t values (1)")
            c.execute("update t set x=2")  # prime the identical cached SQL
            c.commit()
            c.execute("begin immediate")
            c.arm_g0()
            for sql in (
                "update t set x=2",
                "with a as (select 1) update t set x=3",
                "insert into t values(4)",
                "delete from t",
                "drop table t",
                "pragma user_version=99",
                "attach ':memory:' as other",
            ):
                with self.assertRaises(sqlite3.DatabaseError, msg=sql):
                    c.execute(sql)
            self.assertEqual(c.execute("select x from t").fetchall(), [(2,)])
            self.assertEqual(c.g0_denied_actions, 7)
            c.rollback()
            for action in (
                lambda: c.set_authorizer(None),
                lambda: c.blobopen("t", "x", 1),
                lambda: c.backup(c),
                lambda: c.enable_load_extension(True),
                lambda: c.create_function("evil", 0, lambda: 1),
            ):
                with self.assertRaises(Boundary):
                    action()
        finally:
            c.close()

    def target(self):
        mocks = MockBudget()
        mocks.exchanges, mocks.methods, mocks.source_sync = 6, 8, 2
        events = []
        b = StopBoundary(FakeDomainError, mocks, lambda event: events.append(event))
        worker = object()
        b.bind(worker, "run")

        class Raw:
            def arm_g0(self):
                events.append("armed")

        c = types.SimpleNamespace(connection=types.SimpleNamespace(driver_connection=Raw()))
        args = (
            worker,
            c,
            {"id": "run", "version": 3},
            {"call_run": {"id": "run"}, "aid": "first-attempt", "meta": {"run_version": 3}},
            None,
        )
        return b, args, events

    def test_success_stops_only_after_complete_original_context_exit(self):
        b, args, events = self.target()

        @contextlib.contextmanager
        def original(*args):
            events.append("binding")
            yield object()
            events.extend(
                ["second-proof-checked", "full-hash-close", "original-final-stop-deadline"]
            )

        with self.assertRaises(G0Stop) as stopped:
            with b.wrap(original, *args):
                events.extend(["first-commit", "parse-usage-receipts", "second-commit"])
            events.append("W5")
        self.assertEqual(stopped.exception.classification, "G0_COMPLETED_NO_W5")
        self.assertNotIn("W5", events)
        self.assertEqual(events[-1], "original-final-stop-deadline")

    def test_enter_refusal_unwinds_before_same_exception_is_preserved(self):
        b, args, events = self.target()
        error = FakeDomainError()
        error._cold_admission_diagnostic = {
            "finite": [{"name": "run_check.deadline", "value": 30}],
            "end": 31,
            "stop": False,
        }

        @contextlib.contextmanager
        def original(*args):
            try:
                raise error
                yield
            finally:
                events.append("original-invalidated")

        with self.assertRaises(G0Stop) as stopped:
            with b.wrap(original, *args):
                self.fail("must not enter body")
        self.assertIs(stopped.exception.original, error)
        self.assertIs(stopped.exception.__cause__, error)
        self.assertEqual(events[-1], "original-invalidated")
        self.assertIs(
            b.diagnostic(stopped.exception)["original_diagnostic"], error._cold_admission_diagnostic
        )

    def test_non_domain_error_is_not_relabelled_and_foreign_signal_denied(self):
        b, args, events = self.target()

        @contextlib.contextmanager
        def original(*args):
            yield object()
            raise ValueError("resource or unexpected exception")

        with self.assertRaises(ValueError):
            with b.wrap(original, *args):
                pass
        with self.assertRaises(Boundary):
            b.diagnostic(G0Stop(b, "G0_COMPLETED_NO_W5"))

    def test_guard_denial_cannot_be_relabelled_as_original_business_refusal(self):
        b, args, events = self.target()
        args[1].connection.driver_connection.g0_denied_actions = 1
        error = FakeDomainError()

        @contextlib.contextmanager
        def original(*args):
            raise error
            yield

        with self.assertRaises(Boundary) as stopped:
            with b.wrap(original, *args):
                pass
        self.assertIs(stopped.exception.__cause__, error)
        self.assertIsNone(b.signal)

    def test_bounded_exception_graph_retains_cause_context_and_exact_diag(self):
        from g0_guard import exception_chain

        cause, context = ValueError("cause"), RuntimeError("context")
        error = FakeDomainError()
        error.__cause__, error.__context__ = cause, context
        error._cold_admission_diagnostic = {"end": 31, "stop": False}
        graph = exception_chain(error)
        self.assertEqual(len(graph["chain"]), 3)
        self.assertEqual(graph["chain"][0]["cause"], 1)
        self.assertEqual(graph["chain"][0]["context"], 2)
        self.assertIs(graph["chain"][0]["original_diagnostic"], error._cold_admission_diagnostic)

    def test_grant_exact_match_expiry_and_scope(self):
        description = dict(
            scope=SCOPE,
            head="f" * 40,
            limits=LIMITS,
            native_library="/tmp/unit.so",
            source_manifest_sha256="a" * 64,
            sqlite_version="unit",
            source_manifest={},
        )
        grant = {k: v for k, v in description.items() if k != "source_manifest"}
        grant.update(expires_at=200, grant_id="unit-only-grant")
        validate_grant(grant, description, 100)
        for key, value in (("scope", "full-PB"), ("expires_at", 99), ("head", "0" * 40)):
            with self.assertRaises(Boundary):
                validate_grant({**grant, key: value}, description, 100)

    def test_owned_dummy_process_cleanup_no_business_imports(self):
        p = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)"], start_new_session=True
        )
        try:
            identity = proc_identity(p.pid)
            with self.assertRaises(Boundary):
                signal_owned(p.pid, {**identity, "started": identity["started"] + 1}, 15)
            import time

            self.assertTrue(cleanup(p, identity, time.monotonic()))
        finally:
            if p.poll() is None:
                p.kill()
                p.wait(timeout=2)

    def test_cleanup_checks_group_after_leader_has_exited(self):
        import g0_bounded as launcher

        leader = types.SimpleNamespace(pid=12345, poll=lambda: 0)
        identity = dict(pid=12345, pgid=12345, sid=12345, started=10, uid=os.getuid())
        # No real descendant is created. A remaining member requires a signal
        # even though the leader has already exited, and the grace is not reset.
        with (
            patch.object(launcher, "group_members", side_effect=[[identity], []]),
            patch.object(launcher, "signal_owned", return_value=True) as send,
        ):
            self.assertTrue(launcher.cleanup(leader, identity, 0, clock=lambda: 1))
            send.assert_called_once()

    def test_direct_child_cli_cannot_allocate_outputs_or_import_product(self):
        with tempfile.TemporaryDirectory(prefix="g0-cli-pure-unit-") as root:
            absent = Path(root) / "must-not-exist"
            interpreters = {sys.executable, os.environ.get("G0_NATIVE_UNIT_PYTHON", sys.executable)}
            for interpreter in interpreters:
                result = subprocess.run(
                    [
                        interpreter,
                        "-B",
                        str(Path(__file__).with_name("g0_bounded.py")),
                        "--child",
                        str(absent),
                        "1",
                    ],
                    capture_output=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 2, result.stderr.decode())
                self.assertIn(b"BLOCKED", result.stdout)
                self.assertFalse(absent.exists())

    def test_network_and_model_denied_before_original_handler(self):
        import socket

        import pytest
        from g0_guard import install_network_denials

        class Sync:
            def handle_request(self, *args):
                self.fail("original handler reached")

        class Async:
            async def handle_async_request(self, *args):
                raise AssertionError("original async reached")

        class Model:
            pass

        fake_http = types.SimpleNamespace(HTTPTransport=Sync, AsyncHTTPTransport=Async)
        fake_model = types.SimpleNamespace(MockModel=Model)
        with pytest.MonkeyPatch.context() as p:
            install_network_denials(p, fake_http, fake_model)
            for call in (
                lambda: socket.getaddrinfo("example.invalid", 443),
                lambda: Sync().handle_request(None),
                lambda: Model(),
            ):
                with self.assertRaises(Boundary):
                    call()

    def test_native_vfs_local_sql_only(self):
        library = os.environ.get("G0_UNIT_NATIVE_LIBRARY")
        if not library:
            self.skipTest("explicit separately compiled native unit dependency required")
        code = """
import pathlib, sqlite3, sys, tempfile
from g0_guard import install_vfs
with tempfile.TemporaryDirectory(prefix="g0-vfs-pure-unit-") as root:
    db=pathlib.Path(root)/"fixture.db"
    native, api=install_vfs(sys.argv[1],db)
    c=sqlite3.connect(db)
    c.execute("create table t (x)")
    c.execute("insert into t values(1)")
    c.commit()
    assert c.execute("select x from t").fetchone()==(1,)
    c.execute("pragma journal_mode=wal")
    d=sqlite3.connect(db)
    d.execute("insert into t values(2)")
    d.commit()
    assert c.execute("select count(*) from t").fetchone()==(2,)
    d.close(); c.close()
    assert native.g0_fault()==0, native.g0_fault()
    assert native.g0_open_handles()==0, native.g0_open_handles()
    try:
        sqlite3.connect(pathlib.Path(root)/"outside.db")
    except sqlite3.DatabaseError:
        pass
    else:
        raise AssertionError("unlisted native path accepted")
    assert not (pathlib.Path(root)/"outside.db").exists()
    assert native.g0_fault()!=0
    assert not any(k=="sim2act" or k.startswith("sim2act.") for k in sys.modules)
"""
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(Path(__file__).parent),
        }
        # This is a stand-alone native-protection unit runtime, never a fallback
        # launcher for the application's frozen interpreter/dependencies.
        interpreter = os.environ.get("G0_NATIVE_UNIT_PYTHON", sys.executable)
        result = subprocess.run(
            [interpreter, "-B", "-c", code, library], env=env, capture_output=True, timeout=15
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_sampled_disk_counts_unknown_sparse_and_unlinked_writable_files(self):
        with tempfile.TemporaryDirectory(prefix="g0-disk-pure-unit-") as root:
            monitor = DiskMonitor(root)
            unknown = Path(root) / "native-random.tmp"
            unknown.write_bytes(b"1234")
            sample = monitor.sample(os.getpid())
            self.assertGreaterEqual(sample["logical_bytes"], 4)
            with unknown.open("r+b"):
                unknown.unlink()
                sample = monitor.sample(os.getpid())
                self.assertGreaterEqual(sample["logical_bytes"], 4)
            huge = Path(root) / "unknown-native-file"
            with huge.open("wb") as stream:
                stream.truncate(LIMITS["directory_bytes"] + 1)
            with self.assertRaisesRegex(Boundary, "not a hard quota"):
                monitor.sample()
            self.assertGreater(monitor.report()["peak_logical_bytes"], LIMITS["directory_bytes"])

    def test_disk_monitor_rejects_symlink_and_scan_error(self):
        with tempfile.TemporaryDirectory(prefix="g0-disk-pure-unit-") as root:
            monitor = DiskMonitor(root)
            (Path(root) / "link").symlink_to("/tmp")
            with self.assertRaises(Boundary):
                monitor.sample()
            with self.assertRaises(Boundary):
                monitor.scan_error(PermissionError("unit"))

    def native_unit(self, code):
        library = os.environ.get("G0_UNIT_NATIVE_LIBRARY")
        if not library:
            self.skipTest("explicit separately compiled native unit dependency required")
        interpreter = os.environ.get("G0_NATIVE_UNIT_PYTHON", sys.executable)
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(Path(__file__).parent),
        }
        with tempfile.TemporaryDirectory(prefix="g0-native-pure-unit-") as root:
            result = subprocess.run(
                [interpreter, "-B", "-c", code, library, root],
                env=env,
                capture_output=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_native_size_cap_and_sticky_open_failure(self):
        self.native_unit("""
import pathlib,sqlite3,sys
from g0_guard import install_vfs,MIB,DB_FILES
root=pathlib.Path(sys.argv[2]); db=root/"fixture.db"
native,api=install_vfs(sys.argv[1],db)
c=sqlite3.connect(db);c.execute("create table t(x blob)");c.commit()
try:
    c.execute("insert into t values(zeroblob(?))",(13*MIB,));c.commit()
except sqlite3.DatabaseError:
    pass
else:
    raise AssertionError("native cap failed")
assert native.g0_fault()==2,native.g0_fault()
try:
    sqlite3.connect(db)
except sqlite3.DatabaseError:
    pass
else:
    raise AssertionError("sticky fault accepted a new native open")
c.close()
assert all(p.name in DB_FILES and p.stat().st_size<=12*MIB for p in root.iterdir())
""")

    def test_native_rejects_linked_database_before_touching_target(self):
        self.native_unit("""
import pathlib,sqlite3,sys
from g0_guard import install_vfs
root=pathlib.Path(sys.argv[2]);db=root/"fixture.db";target=root/"original"
target.write_bytes(b"preserve")
db.symlink_to(target)
native,api=install_vfs(sys.argv[1],db)
try:
    sqlite3.connect(db)
except sqlite3.DatabaseError:
    pass
else:
    raise AssertionError("symlink accepted")
assert target.read_bytes()==b"preserve"
assert native.g0_fault()!=0
""")

    def test_child_io_closes_uri_alias_attach_and_unbounded_python_write(self):
        self.native_unit("""
import pathlib,sqlite3,_sqlite3,sys,io,socket
from g0_guard import install_vfs,install_child_io,Files,Boundary
root=pathlib.Path(sys.argv[2]);db=root/"fixture.db"
raw_alias=_sqlite3.connect
files=Files(root)
native,api=install_vfs(sys.argv[1],db)
class Patch:
    def setattr(self,owner,name,value):
        setattr(owner,name,value)
install_child_io(Patch(),files,db)
c=sqlite3.connect(str(db));c.execute("create table t(x)");c.commit()
alias=_sqlite3.connect(str(db));alias.close()
for callback in (lambda:sqlite3.connect("file:"+str(db)+"?vfs=unix",uri=True),
                 lambda:raw_alias(str(db)),
                 lambda:io.FileIO(root/"extra","w"),
                 lambda:socket.getaddrinfo("example.invalid",443)):
    try:
        callback()
    except Boundary:
        pass
    else:
        raise AssertionError("entry boundary accepted")
try:
    c.execute("attach 'file:"+str(root/"other")+"?vfs=unix' as other")
except sqlite3.DatabaseError:
    pass
else:
    raise AssertionError("ATTACH bypass accepted")
c.close();files.close()
import gc
gc.collect()
assert native.g0_open_handles()==0
assert not any(k=="sim2act" or k.startswith("sim2act.") for k in sys.modules)
""")


if __name__ == "__main__":
    unittest.main()
