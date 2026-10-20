"""Engineering-only G0 protections. Importing this module never imports Sim2Act.

The separate launcher requires a fresh, explicit once-only grant. Unit tests use
local stand-ins, never the production-shaped fixture or its Mock prefix.
"""

from __future__ import annotations

import codecs
import contextlib
import hashlib
import io
import json
import locale
import math
import os
import socket
import sqlite3
import threading
import time
from pathlib import Path

MIB = 1024 * 1024
LIMITS = dict(
    exchanges=6,
    methods=8,
    prefix_seconds=480,
    g0_seconds=120,
    work_seconds=600,
    term_seconds=5,
    kill_seconds=5,
    directory_bytes=64 * MIB,
    disk_sample_seconds=0.1,
)
FILES = {
    "mock-exchanges.jsonl": 2 * MIB,
    "failure-observations.jsonl": MIB // 2,
    "source-manifest.json": 15 * MIB // 2,
    "prefix-proof.json": 2 * MIB,
    "diagnostic.json": MIB // 4,
    "control.jsonl": MIB // 16,
    "output.log": 2 * MIB,
    "receipt.json": MIB,
}
DB_FILES = ("fixture.db", "fixture.db-journal", "fixture.db-wal", "fixture.db-shm")
SELECTOR_TIMEOUT_CAP_SECONDS = 0.05
# Output writers retain their byte caps. SQLite files instead use the explicit
# parent-side sampled budget: this is not an aggregate filesystem hard quota.


class DiskMonitor:
    """Sample all run files, including unknown/native temporary filenames."""

    def __init__(self, root, clock=time.monotonic):
        self.root, self.clock = Path(root).resolve(strict=True), clock
        self.samples = self.peak_logical = self.peak_allocated = 0
        self.last = None
        self.first_sample_at = None
        self.min_interval = self.max_interval = None

    def sample(self, pid=None):
        logical = allocated = 0
        seen = set()
        for folder, dirs, names in os.walk(self.root, followlinks=False, onerror=self.scan_error):
            for name in (*dirs, *names):
                path = Path(folder) / name
                try:
                    info = path.lstat()
                except FileNotFoundError:  # SQLite can remove a journal between samples.
                    continue
                if path.is_symlink():
                    raise Boundary("disk monitor found unexpected symlink")
                key = (info.st_dev, info.st_ino)
                if key in seen:
                    continue
                seen.add(key)
                logical += info.st_size
                allocated += info.st_blocks * 512
        # Native SQLite can unlink temporary files while keeping an fd open.
        # Count writable regular fds too, without double-counting visible inodes.
        if pid is not None:
            import stat

            fdroot = Path(f"/proc/{pid}/fd")
            try:
                descriptors = list(fdroot.iterdir())
            except FileNotFoundError:
                descriptors = []
            for path in descriptors:
                try:
                    info = path.stat()
                    flags = next(
                        line.split()[1]
                        for line in Path(f"/proc/{pid}/fdinfo/{path.name}").read_text().splitlines()
                        if line.startswith("flags:")
                    )
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(info.st_mode) or not int(flags, 8) & os.O_ACCMODE:
                    continue
                key = (info.st_dev, info.st_ino)
                if key not in seen:
                    seen.add(key)
                    logical += info.st_size
                    allocated += info.st_blocks * 512
        self.samples += 1
        self.peak_logical = max(self.peak_logical, logical)
        self.peak_allocated = max(self.peak_allocated, allocated)
        at = self.clock()
        if self.last is None:
            self.first_sample_at = at
        else:
            interval = at - self.last["at"]
            self.min_interval = interval if self.min_interval is None else min(self.min_interval, interval)
            self.max_interval = interval if self.max_interval is None else max(self.max_interval, interval)
        self.last = dict(at=at, logical_bytes=logical, allocated_bytes=allocated)
        if max(logical, allocated) > LIMITS["directory_bytes"]:
            raise Boundary("sampled 64MiB disk budget exceeded; not a hard quota")
        return self.last

    @staticmethod
    def scan_error(error):
        raise Boundary("disk budget scan failed") from error

    def report(self):
        intervals = max(0, self.samples - 1)
        span = self.last["at"] - self.first_sample_at if intervals else 0
        return dict(
            mode="SAMPLED_BUDGET_NOT_HARD_QUOTA",
            configured_interval_seconds=LIMITS["disk_sample_seconds"],
            configured_interval_is_scheduled=False,
            scheduling_policy="EVERY_SUPERVISOR_ITERATION_AND_FINALIZATION",
            selector_timeout_cap_seconds=SELECTOR_TIMEOUT_CAP_SECONDS,
            sample_completion_intervals=dict(
                count=intervals,
                minimum=self.min_interval,
                maximum=self.max_interval,
                mean=span / intervals if intervals else None,
            ),
            observed_completion_rate_hz=intervals / span if span > 0 else None,
            samples=self.samples,
            peak_logical_bytes=self.peak_logical,
            peak_allocated_bytes=self.peak_allocated,
            last=self.last,
        )


class Boundary(BaseException):
    """An engineering boundary failure, never a business DomainError."""


class G0Stop(BaseException):
    def __init__(self, owner, classification, original=None):
        self.owner, self.classification, self.original = owner, classification, original


class Budget:
    def __init__(self, started, clock=time.monotonic):
        self.started, self.clock, self.g0_at = started, clock, None

    def enter_g0(self, at):
        now = self.clock()
        if (
            self.g0_at is not None
            or not math.isfinite(at)
            or not self.started <= at <= now
            or at >= self.started + 480
        ):
            raise Boundary("invalid or late first G0 event")
        self.g0_at = at

    @property
    def deadline(self):
        return min(
            self.started + 600, self.started + 480 if self.g0_at is None else self.g0_at + 120
        )

    def check(self):
        if self.clock() >= self.deadline:
            raise Boundary("wall budget exhausted")


class MockBudget:
    def __init__(self, healthy=lambda: True):
        self.exchanges = self.methods = 0
        self.closed = False
        self.stage = "generate"
        self.source_sync = 0
        self.healthy = healthy

    def enter(self, *, asynchronous, exact_transport):
        expected = ("generate",) * 3 + ("source",) * 2 + ("cold",)
        if not self.healthy() or self.closed or not exact_transport or self.methods >= 8:
            raise Boundary("Mock method outside exact finite prefix")
        if asynchronous:
            if self.exchanges >= 6 or self.stage != expected[self.exchanges]:
                raise Boundary("Mock exchange outside exact stage/order")
            self.exchanges += 1
        else:
            if self.stage != "source" or self.source_sync >= 2:
                raise Boundary("unexpected local Source delegate")
            self.source_sync += 1
        self.methods += 1

    def close(self):
        if not self.healthy() or (self.exchanges, self.methods, self.source_sync) != (6, 8, 2):
            raise Boundary("G0 reached without exact six/eight prefix")
        self.closed = True


class BoundedWriter:
    """Reserve bytes before each write; partial failures stay consumed."""

    def __init__(self, stream, limit):
        self.stream, self.limit, self.used = stream, limit, 0
        self.lock = threading.Lock()

    def write(self, raw):
        if type(raw) is not bytes:
            raise Boundary("byte writer requires bytes")
        with self.lock:
            if len(raw) > self.limit - self.used:
                raise Boundary("output budget exhausted")
            self.used += len(raw)
            view = memoryview(raw)
            while view:
                written = self.stream.write(view)
                if type(written) is not int or not 0 < written <= len(view):
                    raise Boundary("incomplete output write")
                view = view[written:]
            self.stream.flush()
        return len(raw)

    def json(self, value):
        return self.write((json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode())


class Files:
    """Bounded Python outputs; native SQLite disk use is sampled separately."""

    def __init__(self, root, names=None):
        self.root = Path(root).resolve(strict=True)
        self.writers = {}
        self.real_open = io.open
        for name, cap in FILES.items():
            if names is not None and name not in names:
                continue
            fd = os.open(
                self.root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
            self.writers[name] = BoundedWriter(os.fdopen(fd, "wb", buffering=0), cap)

    def writer(self, name):
        return self.writers[name]

    def close(self):
        for writer in self.writers.values():
            writer.stream.close()

    def fixture_open(
        self,
        file,
        mode="r",
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        closefd=True,
        opener=None,
    ):
        writing = any(c in mode for c in "wax+")
        if not writing:
            return self.real_open(file, mode, buffering, encoding, errors, newline, closefd, opener)
        path = Path(file).absolute()
        if (
            path.parent != self.root
            or path.name not in {"mock-exchanges.jsonl", "failure-observations.jsonl"}
            or mode != "a"
        ):
            raise Boundary("unexpected fixture file write")
        # Path.open forwards these defaults positionally, with None encoding
        # resolved by io.text_encoding to "locale" or "utf-8". Accept only
        # equivalent UTF-8/strict/default-newline writes to the bounded stream.
        encoding = io.text_encoding(encoding)
        if encoding == "locale":
            encoding = locale.getencoding()
        if (
            buffering != -1
            or codecs.lookup(encoding).name != "utf-8"
            or errors not in (None, "strict")
            or newline is not None
            or closefd is not True
            or opener is not None
        ):
            raise Boundary("unexpected fixture writer options")
        writer = self.writer(path.name)

        class Append:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def write(self, text):
                if not isinstance(text, str):
                    raise TypeError("text writer requires str")
                writer.write(text.encode("utf-8"))
                return len(text)

        return Append()


def sqlite_authorizer(action, arg1, arg2, database, trigger):
    """Installed anew at G0 enter, expires cached SQL; no I/O/exception here."""
    if action in (sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and arg2 in {
        "json_extract",
        "json_quote",
        "json_type",
        "json_valid",
        "length",
        "count",
        "coalesce",
        "min",
        "max",
        "sum",
        "lower",
        "upper",
        "substr",
        "abs",
        "ifnull",
    }:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_TRANSACTION and arg1 == "ROLLBACK":
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def guarded_connection_class():
    class Connection(sqlite3.Connection):
        g0_read_only = False

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            def baseline(action, arg1, arg2, database, trigger):
                if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
                    return sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_FUNCTION and arg2 == "load_extension":
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            super().set_authorizer(baseline)

        def arm_g0(self):
            if self.g0_read_only:
                raise Boundary("connection already armed")
            # Setting, rather than switching a callback flag, expires cached SQL.
            self.g0_denied_actions = 0

            def read_only(action, arg1, arg2, database, trigger):
                result = sqlite_authorizer(action, arg1, arg2, database, trigger)
                if result != sqlite3.SQLITE_OK:
                    self.g0_denied_actions = min(64, self.g0_denied_actions + 1)
                return result

            super().set_authorizer(read_only)
            self.g0_read_only = True

        def set_authorizer(self, callback):
            if self.g0_read_only:
                raise Boundary("cannot disarm G0 connection before rollback/disposal")
            return super().set_authorizer(callback)

        def blobopen(self, *args, **kwargs):
            raise Boundary("Blob API outside frozen SQL-only fixture")

        def backup(self, *args, **kwargs):
            raise Boundary("backup outside finite prefix")

        def deserialize(self, *args, **kwargs):
            raise Boundary("database replacement outside finite prefix")

        def enable_load_extension(self, *args, **kwargs):
            raise Boundary("SQLite extension loading prohibited")

        def load_extension(self, *args, **kwargs):
            raise Boundary("SQLite extension loading prohibited")

        def create_function(self, name, narg, func, *, deterministic=False):
            # SQLAlchemy's SQLite dialect registers these two pure functions.
            if self.g0_read_only or name not in {"regexp", "floor"}:
                raise Boundary("unexpected SQLite UDF")
            return super().create_function(name, narg, func, deterministic=deterministic)

        def create_aggregate(self, *args, **kwargs):
            raise Boundary("SQLite aggregate registration prohibited")

        def create_window_function(self, *args, **kwargs):
            raise Boundary("SQLite window registration prohibited")

    return Connection


class StopBoundary:
    def __init__(self, domain_error, mocks, notify, clock=time.monotonic):
        self.domain_error, self.mocks, self.notify, self.clock = domain_error, mocks, notify, clock
        self.target = None
        self.entered = False
        self.instance = None
        self.result = None
        self.signal = None
        self.raw = None

    def bind(self, worker, run_id):
        if self.target is not None:
            raise Boundary("G0 target already bound")
        self.target = (worker, run_id)

    @contextlib.contextmanager
    def wrap(self, original, worker, c, current, inputs, platform):
        if self.target is None or worker is not self.target[0]:
            with original(worker, c, current, inputs, platform) as value:
                yield value
            return
        if (
            self.entered
            or current["id"] != self.target[1]
            or inputs["call_run"]["id"] != current["id"]
        ):
            raise Boundary("unexpected Cold context identity")
        if inputs["meta"]["run_version"] != current["version"] or not inputs["aid"]:
            raise Boundary("unexpected Cold version/attempt")
        raw = c.connection.driver_connection
        self.raw = raw
        self.mocks.close()
        self.entered = True
        self.notify(
            {
                "event": "g0_enter",
                "at": self.clock(),
                "attempt": inputs["aid"],
                "run": current["id"],
            }
        )
        raw.arm_g0()
        started = self.clock()
        try:
            with original(worker, c, current, inputs, platform) as value:
                if value is None:
                    raise Boundary("target Cold not eligible")
                yield value
        except self.domain_error as error:
            if getattr(raw, "g0_denied_actions", 0) or not self.mocks.healthy():
                raise Boundary(
                    "G0 protection failed; original exception retained as cause"
                ) from error
            self.signal = G0Stop(self, "G0_ORIGINAL_REJECTION_NO_W5", error)
            self.result = {
                "classification": self.signal.classification,
                "g0_wall_seconds": self.clock() - started,
            }
            raise self.signal from error
        else:
            if getattr(raw, "g0_denied_actions", 0) or not self.mocks.healthy():
                raise Boundary("G0 protection failed before successful stop")
            self.signal = G0Stop(self, "G0_COMPLETED_NO_W5")
            self.result = {
                "classification": self.signal.classification,
                "g0_wall_seconds": self.clock() - started,
            }
            raise self.signal

    def observe_init(self, original):
        boundary = self

        def wrapped(instance, *args, **kwargs):
            original(instance, *args, **kwargs)
            if boundary.entered:
                if boundary.instance is not None:
                    raise Boundary("second diagnostic instance")
                boundary.instance = instance

        return wrapped

    def diagnostic(self, signal):
        if signal is not self.signal or signal.owner is not self:
            raise Boundary("foreign stop signal")
        result = dict(self.result)
        if signal.original is not None:
            error = signal.original
            result["original_error"] = exception_chain(error)
            original = getattr(error, "_cold_admission_diagnostic", None)
            result["original_diagnostic"] = original if original is not None else "NOT_REACHED"
        if self.instance is not None:
            result["partial"] = {
                "stages": self.instance.stages,
                "run_context": self.instance.run_context,
                "incomplete": self.instance.incomplete,
            }
        else:
            result["partial"] = "NOT_REACHED"
        result["g0_authorizer_denials"] = getattr(self.raw, "g0_denied_actions", "UNKNOWN")
        result["w5_entries"] = "STATIC_STOP_BEFORE_NEXT_STATEMENT_NOT_AN_OBSERVED_COUNTER"
        return result


def exception_chain(error):
    chain, objects, indices, truncated = [], [error], {id(error): 0}, False
    for error in objects:
        frames, tb = [], error.__traceback__
        while tb is not None and len(frames) < 64:
            frames.append(
                dict(
                    file=tb.tb_frame.f_code.co_filename,
                    function=tb.tb_frame.f_code.co_name,
                    line=tb.tb_lineno,
                )
            )
            tb = tb.tb_next
        record = dict(
            type=type(error).__name__,
            code=getattr(error, "code", None),
            message=str(error)[:1024],
            traceback=frames,
            frames_truncated=tb is not None,
            cause=None,
            context=None,
            suppress_context=error.__suppress_context__,
            original_diagnostic=getattr(error, "_cold_admission_diagnostic", None),
        )
        for name, next_error in (("cause", error.__cause__), ("context", error.__context__)):
            if next_error is None:
                continue
            if id(next_error) not in indices:
                if len(objects) >= 8:
                    truncated = True
                    record[name] = "TRUNCATED"
                    continue
                indices[id(next_error)] = len(objects)
                objects.append(next_error)
            record[name] = indices[id(next_error)]
        chain.append(record)
    return dict(chain=chain, chain_truncated=truncated)


def install_network_denials(patch, httpx, model):
    def deny(*args, **kwargs):
        raise Boundary("real network/model boundary")

    for owner, names in (
        (socket.socket, ("connect", "connect_ex", "bind", "listen", "sendto", "sendmsg")),
        (
            socket,
            (
                "create_connection",
                "getaddrinfo",
                "gethostbyname",
                "gethostbyname_ex",
                "gethostbyaddr",
            ),
        ),
        (httpx.HTTPTransport, ("handle_request",)),
        (httpx.AsyncHTTPTransport, ("handle_async_request",)),
    ):
        for name in names:
            if hasattr(owner, name):
                patch.setattr(owner, name, deny)
    patch.setattr(model.MockModel, "__init__", deny)


def install_mock_counter(patch, httpx, budget, fixture, normal_source):
    sync = httpx.MockTransport.handle_request
    asynchronous = httpx.MockTransport.handle_async_request

    def handle(self, request):
        budget.enter(asynchronous=False, exact_transport=self is normal_source)
        return sync(self, request)

    async def handle_async(self, request):
        budget.enter(asynchronous=True, exact_transport=self is fixture["transport"])
        if len(request.content) > 32768:
            raise Boundary("request wire limit")
        result = await asynchronous(self, request)
        if len(result.content) > 32768:
            raise Boundary("response wire limit")
        return result

    patch.setattr(httpx.MockTransport, "handle_request", handle)
    patch.setattr(httpx.MockTransport, "handle_async_request", handle_async)


def hashes(paths):
    return {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}


def same_sqlite_api():
    import _sqlite3
    import ctypes

    # Some standalone Pythons statically embed SQLite and hide its API. Loading
    # libsqlite3.so instead would protect a different engine: always refuse.
    api = ctypes.CDLL(getattr(_sqlite3, "__file__", None))
    try:
        for name in ("sqlite3_vfs_find", "sqlite3_vfs_register", "sqlite3_libversion_number"):
            getattr(api, name)
    except AttributeError:
        raise Boundary("loaded SQLite has no public VFS API; native disk closure BLOCKED") from None
    api.sqlite3_libversion_number.restype = ctypes.c_int
    version = tuple(map(int, sqlite3.sqlite_version.split(".")))
    if api.sqlite3_libversion_number() != version[0] * 1000000 + version[1] * 1000 + version[2]:
        raise Boundary("same loaded SQLite ABI/version required")
    return api


def install_vfs(library, database):
    import ctypes

    api = same_sqlite_api()
    api.sqlite3_vfs_find.argtypes = [ctypes.c_char_p]
    api.sqlite3_vfs_find.restype = ctypes.c_void_p
    guard = ctypes.CDLL(str(Path(library).resolve(strict=True)))
    guard.g0_install.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int64]
    guard.g0_install.restype = ctypes.c_int
    original = api.sqlite3_vfs_find(None)
    if guard.g0_install(
        original,
        ctypes.cast(api.sqlite3_vfs_register, ctypes.c_void_p),
        os.fsencode(database),
        12 * MIB,
    ):
        raise Boundary("unsupported SQLite/native VFS ABI")
    guard.g0_fault.restype = guard.g0_open_handles.restype = ctypes.c_int
    return guard, api  # Keep both libraries alive until child process exit.


def install_child_io(patch, files, database):
    import _sqlite3
    import builtins
    import sys

    real_connect = sqlite3.connect
    connection = guarded_connection_class()
    database = str(Path(database).resolve())

    def connect(selected, *args, **kwargs):
        if str(selected) != database or "factory" in kwargs or kwargs.get("uri") or len(args) > 3:
            raise Boundary("SQLite path/URI/factory outside sole new database")
        return real_connect(selected, *args, **kwargs, factory=connection)

    patch.setattr(sqlite3, "connect", connect)
    patch.setattr(sqlite3.dbapi2, "connect", connect)
    patch.setattr(_sqlite3, "connect", connect)
    patch.setattr(builtins, "open", files.fixture_open)
    patch.setattr(io, "open", files.fixture_open)

    def audit(event, args):
        if event == "open":
            path, mode, flags = args
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                raise Boundary("unaccounted Python file write")
            if isinstance(path, (str, bytes, os.PathLike)):
                selected = Path(os.fsdecode(path)).absolute()
                if any(part in {".aws", ".ssh", ".env", ".credentials"} for part in selected.parts):
                    raise Boundary("credential file read prohibited")
        if event == "sqlite3.connect" and str(args[0]) != database:
            raise Boundary("non-fixture SQLite connect")
        if event == "sqlite3.connect/handle" and not isinstance(args[0], connection):
            # CPython emits this before __init__ is complete; close() is not
            # legal yet. The uncaught BaseException ends the dedicated child;
            # no success classification is possible with native handles alive.
            raise Boundary("unprotected DBAPI connection alias")
        if event in {
            "socket.connect",
            "socket.bind",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "socket.gethostbyaddr",
            "subprocess.Popen",
            "os.fork",
            "os.forkpty",
            "os.system",
            "os.posix_spawn",
            "os.exec",
            "ctypes.dlopen",
            "ctypes.dlsym",
        } or event in {
            "os.remove",
            "os.rename",
            "os.mkdir",
            "os.link",
            "os.symlink",
            "os.truncate",
            "os.chmod",
            "os.chown",
            "os.chdir",
            "shutil.copyfile",
        }:
            raise Boundary("child network/process/filesystem mutation prohibited: " + event)

    sys.addaudithook(audit)  # Deliberately lasts until this dedicated child exits.
    return connection
