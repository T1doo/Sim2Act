"""Passive full-run HTTP/SQL exception inventory; no assertions or retry changes."""

import contextvars
import functools
import json
import os
import re
import threading
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from sqlalchemy import event
from sqlalchemy.engine import Engine

ROOT = Path(os.environ["SIM2ACT_EXCEPTION_AUDIT_ROOT"])
REQUEST = contextvars.ContextVar("full_pg_request", default=None)
LOCK = threading.Lock()
NODE = "session"
REQUESTS = {}
EXCEPTIONS = []
SQL_ERRORS = []
ORIGINAL = None
PATCHED = None


def normalize(path):
    return re.sub(r"(?:test|proj|app|res|run|grant|user|task|op)_[a-f0-9]{32}", "OWNED_ID", path)


def sql_error(context):
    error = context.original_exception
    connection = context.connection
    backend = None
    if connection is not None:
        # Inspect the existing DBAPI handle; do not reconnect an invalidated
        # connection while observing its original error.
        dbapi = getattr(connection, "_dbapi_connection", None)
        backend = getattr(
            getattr(getattr(dbapi, "driver_connection", None), "info", None), "backend_pid", None
        )
    row = {
        "utc_ns": time.time_ns(),
        "node": NODE,
        "request": REQUEST.get(),
        "backend": backend,
        "sqlstate": getattr(error, "sqlstate", None),
        "exception_type": type(error).__name__,
        "statement": re.sub(r"'(?:''|[^'])*'", "'<literal>'", normalize(context.statement or "")),
    }
    with LOCK:
        SQL_ERRORS.append(row)


def pytest_configure(config):
    global ORIGINAL, PATCHED
    ORIGINAL = FastAPI.__call__

    @functools.wraps(ORIGINAL)
    async def measured(app, scope, receive, send):
        if scope["type"] != "http":
            return await ORIGINAL(app, scope, receive, send)
        node = NODE
        label = f"{scope['method']}:{scope['path']}"
        token = REQUEST.set(label)
        started = time.perf_counter()
        status = None
        exception_type = None

        async def sent(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            return await ORIGINAL(app, scope, receive, sent)
        except BaseException as error:
            exception_type = type(error).__name__
            raise
        finally:
            seconds = time.perf_counter() - started
            with LOCK:
                key = (node, scope["method"], normalize(scope["path"]), status)
                row = REQUESTS.setdefault(key, {"count": 0, "seconds": 0.0})
                row["count"] += 1
                row["seconds"] += seconds
                if exception_type is not None or (status is not None and status >= 500):
                    EXCEPTIONS.append(
                        {
                            "utc_ns": time.time_ns(),
                            "node": node,
                            "request": label,
                            "status": status,
                            "exception_type": exception_type,
                            "seconds": seconds,
                        }
                    )
            REQUEST.reset(token)

    PATCHED = measured
    FastAPI.__call__ = PATCHED
    event.listen(Engine, "handle_error", sql_error)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    global NODE
    NODE = item.nodeid
    yield


def pytest_sessionfinish(session, exitstatus):
    groups = [
        {"node": key[0], "method": key[1], "path": key[2], "status": key[3], **row}
        for key, row in REQUESTS.items()
    ]
    (ROOT / "exception-audit.json").write_text(
        json.dumps(
            {
                "schema": "sim2act.full-pg-exception-audit.v1",
                "http_groups": groups,
                "http_exceptions": EXCEPTIONS,
                "sql_errors": SQL_ERRORS,
                "pytest_exitstatus": int(exitstatus),
                "limits": "Observed pytest-process FastAPI calls and SQLAlchemy errors only; subprocess internals not instrumented. No SQL parameters, headers or exception messages. Re-raises original exceptions. Overlapping request seconds are not wall time.",
            },
            indent=2,
        )
        + "\n"
    )


def pytest_unconfigure(config):
    if FastAPI.__call__ is PATCHED:
        FastAPI.__call__ = ORIGINAL
    event.remove(Engine, "handle_error", sql_error)
