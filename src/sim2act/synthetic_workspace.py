"""Installed, explicitly synthetic blank workspace; no production configuration.

Reuses the existing first-use/local-candidate loopback, test-only Store and
ordinary Worker pattern. Never initializes a pre-existing directory/database.
"""

import hashlib
import json
import os
import re
import signal
import socket
import stat
import sys
import tempfile
import threading
import traceback
from contextlib import contextmanager
from pathlib import Path

import uvicorn
from sqlalchemy import UniqueConstraint, inspect
from sqlalchemy.dialects import sqlite
from starlette.responses import HTMLResponse

from .api import create_app
from .config import Settings
from .db import Store, meta
from .errors import DomainError
from .worker import Worker

VERSION = "sim2act-blank-synthetic-workspace.v1"
TOKEN = "public-synthetic-blank-workspace"
DATABASE = "synthetic-workspace.db"
MARKER = "synthetic-workspace.json"
DESKTOP_ORIGIN = "desktop-origin.json"
DESKTOP_ORIGIN_VERSION = "sim2act-desktop-origin.v1"
BANNER = ('<section id="synthetic-workspace-banner" role="status">'
          '<strong>合成工程 · 仅供非敏感练习材料</strong> '
          '从空白项目开始，数据保留在本机。仅确定性工具；自然模型生成、LIVE和正式发布关闭。 '
          '公开测试登录：<code>' + TOKEN + '</code></section>')


class WorkspaceError(RuntimeError):
    pass


class NeverModel:
    def request(self, *_args, **_kwargs):
        raise DomainError("UNSUPPORTED_CAPABILITY", "This synthetic workspace has no model provider")

    complete = request


def require(value, code):
    if not value:
        raise WorkspaceError(code)


def schema_structure(inspector=None):
    """Pin this finite SQLite schema, including the constraints used for CAS."""
    dialect = sqlite.dialect()
    if inspector is None:
        return {table.name: {
            "columns": [{"name": c.name, "type": str(c.type.compile(dialect=dialect)),
                         "nullable": c.nullable} for c in table.columns],
            "primary_key": [c.name for c in table.primary_key.columns],
            "unique": sorted([c.name for c in constraint.columns]
                             for constraint in table.constraints
                             if isinstance(constraint, UniqueConstraint)),
        } for table in meta.sorted_tables}
    return {name: {
        "columns": [{"name": c["name"], "type": str(c["type"].compile(dialect=dialect)),
                     "nullable": c["nullable"]} for c in inspector.get_columns(name)],
        "primary_key": inspector.get_pk_constraint(name)["constrained_columns"],
        "unique": sorted(c["column_names"] for c in inspector.get_unique_constraints(name)),
    } for name in inspector.get_table_names()}


def schema_fingerprint():
    return hashlib.sha256(json.dumps(schema_structure(), sort_keys=True).encode()).hexdigest()


def checked_path(path):
    root = Path(os.path.abspath(path))
    require("?" not in str(root), "AMBIGUOUS_DIRECTORY")
    require(not any(part.is_symlink() for part in [root, *root.parents]), "LINKED_DIRECTORY")
    return root


def _origin_path(root):
    path = root / DESKTOP_ORIGIN
    require(not any(part.is_symlink() or part.is_junction()
                    for part in [path, *path.parents]), "LINKED_DESKTOP_ORIGIN")
    return path


def _origin_bytes(record):
    return (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _read_desktop_origin(root):
    """Startup metadata only, never an authorization or a substitute for READY."""
    path = _origin_path(root)
    if not path.exists():
        return None
    require(path.is_file(), "INVALID_DESKTOP_ORIGIN")
    try:
        before = path.stat()
        require(before.st_size <= 4096, "INVALID_DESKTOP_ORIGIN")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            actual = os.fstat(stream.fileno())
            require(stat.S_ISREG(actual.st_mode)
                    and (before.st_dev, before.st_ino) == (actual.st_dev, actual.st_ino),
                    "DESKTOP_ORIGIN_CHANGED")
            raw = stream.read(4097)
        require(len(raw) <= 4096, "INVALID_DESKTOP_ORIGIN")
        record = json.loads(raw)
        require(type(record) is dict and set(record) == {
            "version", "host", "port", "principal_id", "workspace_fingerprint"},
            "INVALID_DESKTOP_ORIGIN")
        require(record["version"] == DESKTOP_ORIGIN_VERSION and record["host"] == "127.0.0.1"
                and type(record["port"]) is int and 1 <= record["port"] <= 65535
                and type(record["principal_id"]) is str
                and re.fullmatch(r"user_[a-f0-9]{32}", record["principal_id"])
                and type(record["workspace_fingerprint"]) is str
                and re.fullmatch(r"[a-f0-9]{64}", record["workspace_fingerprint"])
                and raw == _origin_bytes(record), "INVALID_DESKTOP_ORIGIN")
        after = _origin_path(root).stat()
        require((after.st_dev, after.st_ino, after.st_size) ==
                (actual.st_dev, actual.st_ino, len(raw)), "DESKTOP_ORIGIN_CHANGED")
        return record, raw, (actual.st_dev, actual.st_ino)
    except (OSError, ValueError, TypeError) as error:
        raise WorkspaceError("INVALID_DESKTOP_ORIGIN") from error


def _bind_desktop_origin(root, marker, port, prior):
    record = dict(version=DESKTOP_ORIGIN_VERSION, host="127.0.0.1", port=port,
                  principal_id=marker["principal_id"],
                  workspace_fingerprint=hashlib.sha256(_origin_bytes(marker)).hexdigest())
    if prior is not None:
        require(prior[0] == record and _read_desktop_origin(root) == prior,
                "DESKTOP_ORIGIN_CHANGED")
        return prior
    # Publish complete bytes without replacing a winner of a concurrent startup.
    # The listener remains bound throughout. No Worker or UI exists yet.
    pending = None
    try:
        fd, pending = tempfile.mkstemp(prefix=".desktop-origin-pending-", dir=root)
        with os.fdopen(fd, "wb") as stream:
            original = os.fstat(stream.fileno())
            identity = original.st_dev, original.st_ino
            stream.write(_origin_bytes(record))
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "nt":
            # Windows rename refuses an existing destination. Use its atomic
            # no-replace move instead of requiring hard-link support there.
            os.rename(pending, _origin_path(root))
        else:
            os.link(pending, _origin_path(root), follow_symlinks=False)
            directory = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except FileExistsError as error:
        raise WorkspaceError("DESKTOP_ORIGIN_CHANGED") from error
    except OSError as error:
        raise WorkspaceError("DESKTOP_ORIGIN_UNAVAILABLE") from error
    finally:
        if pending is not None:
            Path(pending).unlink(missing_ok=True)
    saved = _read_desktop_origin(root)
    require(saved is not None and saved[0] == record and saved[2] == identity,
            "DESKTOP_ORIGIN_CHANGED")
    return saved


def settings_for(root):
    # Deliberately no Settings.from_env, dotenv, provider or credential discovery.
    # The original CHECK/version API can hold this engineering database while
    # the service heartbeat competes for its writer lock. Use Store.tx's same
    # bounded 30-second ceiling on every SQLite connection in this entry only.
    return Settings("sqlite:///" + str(root / DATABASE) + "?timeout=30", root, mode="mock")


def open_workspace(path, *, new=False):
    root = checked_path(path)
    if new:
        require(not root.exists(), "NEW_DIRECTORY_REQUIRED")
        root.mkdir(mode=0o700)
    else:
        require(root.is_dir(), "WORKSPACE_MISSING")
        for name in [MARKER, DATABASE]:
            file = root / name
            require(file.is_file() and not file.is_symlink(), "UNKNOWN_WORKSPACE")
        require((root / MARKER).stat().st_size <= 4096, "UNKNOWN_WORKSPACE")
        marker = json.loads((root / MARKER).read_text(encoding="utf-8"))
        require(isinstance(marker, dict) and set(marker) == {
            "version", "mode", "principal_id", "schema_fingerprint"}, "UNKNOWN_WORKSPACE")
        require(marker["version"] == VERSION and marker["mode"] == "SYNTHETIC_TEST_ONLY"
                and isinstance(marker["principal_id"], str)
                and re.fullmatch(r"user_[a-f0-9]{32}", marker["principal_id"]), "UNKNOWN_WORKSPACE")
        require(marker["schema_fingerprint"] == schema_fingerprint(), "SCHEMA_CHANGED")
    for suffix in ["", "-journal", "-wal", "-shm"]:
        file = root / (DATABASE + suffix)
        require(not file.is_symlink() and (not file.exists() or file.is_file()), "LINKED_DATABASE")
    store = Store(settings_for(root).database_url, test_only=True, workspace_serialized=True)
    try:
        require(store.engine.url.database == str(root / DATABASE), "AMBIGUOUS_DIRECTORY")
        if new:
            store.initialize()
            principal = store.user("Public synthetic workspace", TOKEN)
            marker = dict(version=VERSION, mode="SYNTHETIC_TEST_ONLY", principal_id=principal,
                          schema_fingerprint=schema_fingerprint())
            # The directory is new and exclusively created by this call.
            with (root / MARKER).open("x", encoding="utf-8") as stream:
                json.dump(marker, stream, indent=2)
                stream.write("\n")
        else:
            inspector = inspect(store.engine)
            require(schema_structure(inspector) == schema_structure(), "SCHEMA_CHANGED")
            require(store.authenticate(TOKEN) == marker["principal_id"], "IDENTITY_CHANGED")
        return root, store, marker
    except Exception:
        store.engine.dispose()
        raise


def workspace_app(store, settings):
    app = create_app(store, settings)

    @app.get("/")
    def synthetic_page():
        page = Path(__file__).with_name("web").joinpath("index.html").read_text(encoding="utf-8")
        return HTMLResponse(page.replace("<body>", "<body>" + BANNER, 1))

    # Only this explicit entry's root page changes; original security middleware
    # still checks Origin and supplies CSP, nosniff and no-store to every route.
    app.router.routes.insert(0, app.router.routes.pop())

    return app



@contextmanager
def _console_break_as_interrupt():
    # Windows starts a new process group with Ctrl+C disabled. The portable
    # launcher sends only that owned group Ctrl+Break. Uvicorn handles it, then
    # re-raises the previous handler; translate that into KeyboardInterrupt so
    # the original worker/store finally block runs instead of default process exit.
    managed = (os.name == "nt" and hasattr(signal, "SIGBREAK")
               and threading.current_thread() is threading.main_thread())
    previous = signal.signal(signal.SIGBREAK, signal.default_int_handler) if managed else None
    try:
        yield
    finally:
        if managed:
            signal.signal(signal.SIGBREAK, previous)

def _read_owned_control(stream, worker_id, request_stop):
    """Private desktop pipe only; EOF also stops startup before READY.

    This has no HTTP/credential/Run admission surface. Both accepted STOP and
    EOF enter the original server shutdown/finally path and emit its receipt.
    """
    while True:
        line = stream.readline(512)
        if line == "":
            request_stop()
            return
        if len(line) > 256 or not line.endswith("\n"):
            request_stop()
            return
        try:
            message = json.loads(line)
        except (ValueError, TypeError):
            continue
        if (type(message) is dict and set(message) == {"command", "worker_id"}
                and message["command"] == "stop" and message["worker_id"] == worker_id):
            request_stop()
            return


def serve(path, *, new=False, port=0, control_stdin=False):
    require(type(port) is int and 0 <= port <= 65535, "INVALID_PORT")
    require(type(control_stdin) is bool, "INVALID_CONTROL_MODE")
    require(not control_stdin or (sys.stdin is not None and not sys.stdin.isatty()), "OWNED_STDIN_PIPE_REQUIRED")
    origin_root = checked_path(path)
    prior_origin = _read_desktop_origin(origin_root) if control_stdin else None
    if prior_origin is not None:
        require(port in (0, prior_origin[0]["port"]), "DESKTOP_ORIGIN_PORT_MISMATCH")
        port = prior_origin[0]["port"]
    # Reserve the actual socket before mutating a data directory; no port scan,
    # reuse option, fallback address, or request to a process occupying the port.
    with socket.socket() as listener:
        try:
            if control_stdin and os.name == "nt":
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(("127.0.0.1", port))
            listener.listen(128)
        except OSError as error:
            raise WorkspaceError("PORT_UNAVAILABLE") from error
        root, store, marker = open_workspace(path, new=new)
        try:
            desktop_origin = (_bind_desktop_origin(root, marker, listener.getsockname()[1], prior_origin)
                              if control_stdin else None)
        except Exception:
            store.engine.dispose()
            raise
        settings = settings_for(root)
        worker = Worker(store, settings, NeverModel())
        server = uvicorn.Server(uvicorn.Config(workspace_app(store, settings), host="127.0.0.1",
            log_level="error", access_log=False, timeout_graceful_shutdown=5))
        stopped = threading.Event()
        errors = []
        address = "http://127.0.0.1:" + str(listener.getsockname()[1])

        def work():
            announced = False
            try:
                while not stopped.is_set():
                    if desktop_origin is not None:
                        require(_read_desktop_origin(root) == desktop_origin, "DESKTOP_ORIGIN_CHANGED")
                    # FIFO admission is per Store.tx, not the entire Run.
                    # Commands/reads can enter between atomic steps and while
                    # the Worker computes outside a database transaction.
                    worker.once()
                    if server.started and not announced:
                        if desktop_origin is not None:
                            require(_read_desktop_origin(root) == desktop_origin, "DESKTOP_ORIGIN_CHANGED")
                        print(json.dumps(dict(event="SYNTHETIC_WORKSPACE_READY", url=address,
                            data_dir=str(root), public_token=TOKEN, worker_id=worker.id,
                            principal_id=marker["principal_id"], mode="SYNTHETIC_TEST_ONLY", control_stdin=control_stdin)), flush=True)
                        announced = True
                    stopped.wait(1)  # Original worker.main service cadence.
            except Exception as error:
                errors.append("SYNTHETIC_WORKER_STOPPED")
                code = getattr(getattr(error, "orig", None), "sqlite_errorcode", None)
                print(json.dumps(dict(event="SYNTHETIC_WORKER_ERROR", worker_id=worker.id,
                    error_type=type(error).__name__, sqlite_errorcode=code if type(code) is int else None,
                    frames=[dict(module=Path(f.filename).name, function=f.name, line=f.lineno)
                            for f in traceback.extract_tb(error.__traceback__)[:32]])), flush=True)
                stopped.set()
                server.should_exit = True

        if control_stdin:
            print(json.dumps(dict(event="SYNTHETIC_WORKSPACE_STARTING", worker_id=worker.id,
                mode="SYNTHETIC_TEST_ONLY", control_stdin=True)), flush=True)
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        if control_stdin:
            def control():
                try:
                    _read_owned_control(sys.stdin, worker.id,
                        lambda: setattr(server, "should_exit", True))
                except (OSError, ValueError):
                    server.should_exit = True
            threading.Thread(target=control, name="owned-desktop-control", daemon=True).start()
        try:
            with _console_break_as_interrupt():
                server.run(sockets=[listener])
        except KeyboardInterrupt:
            pass  # Uvicorn may re-raise its handled, owned Ctrl+C.
        finally:
            stopped.set()
            worker.stop.set()
            thread.join(10)
            clean = not thread.is_alive() and not errors
            if not thread.is_alive():
                store.engine.dispose()
            print(json.dumps(dict(event="SYNTHETIC_WORKSPACE_STOPPED", worker_id=worker.id,
                worker_stopped=not thread.is_alive(), clean=clean, data_preserved=(root / DATABASE).is_file())), flush=True)
        require(clean, "SYNTHETIC_WORKER_STOPPED")
