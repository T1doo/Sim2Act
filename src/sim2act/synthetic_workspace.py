"""Installed, explicitly synthetic blank workspace; no production configuration.

Reuses the existing first-use/local-candidate loopback, test-only Store and
ordinary Worker pattern. Never initializes a pre-existing directory/database.
"""

import hashlib
import json
import os
import re
import socket
import threading
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


def settings_for(root):
    # Deliberately no Settings.from_env, dotenv, provider or credential discovery.
    return Settings("sqlite:///" + str(root / DATABASE), root, mode="mock")


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
    store = Store(settings_for(root).database_url, test_only=True)
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


def serve(path, *, new=False, port=0):
    require(type(port) is int and 0 <= port <= 65535, "INVALID_PORT")
    # Reserve the actual socket before touching a data directory; no port scan.
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", port))
            listener.listen(128)
        except OSError as error:
            raise WorkspaceError("PORT_UNAVAILABLE") from error
        root, store, marker = open_workspace(path, new=new)
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
                    worker.once()
                    if server.started and not announced:
                        print(json.dumps(dict(event="SYNTHETIC_WORKSPACE_READY", url=address,
                            data_dir=str(root), public_token=TOKEN, worker_id=worker.id,
                            principal_id=marker["principal_id"], mode="SYNTHETIC_TEST_ONLY")), flush=True)
                        announced = True
                    stopped.wait(1)  # Original worker.main service cadence.
            except Exception:
                errors.append("SYNTHETIC_WORKER_STOPPED")
                stopped.set()
                server.should_exit = True

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        try:
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
