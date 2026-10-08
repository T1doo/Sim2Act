"""Passive request/SQL/function timings for two original owned PG DOM cases."""

import contextvars
import functools
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

ROOT = Path(os.environ["SIM2ACT_DIAG_ROOT"])
REQUEST = contextvars.ContextVar("diagnostic_request", default=None)
NODE = "session"
LOCK = threading.Lock()
GROUPS = {}
RESTORES = []
PENDING = {}
SERIAL = 0
STATEMENTS = {}


def write(kind, **value):
    with LOCK:
        with (ROOT / "python-timeline.jsonl").open("a") as output:
            output.write(
                json.dumps(
                    {
                        "utc_ns": time.time_ns(),
                        "monotonic": time.perf_counter(),
                        "event": kind,
                        "node": NODE,
                        **value,
                    }
                )
                + "\n"
            )


def group(kind, identity, seconds):
    key = (NODE, kind, REQUEST.get(), identity)
    with LOCK:
        row = GROUPS.setdefault(key, {"count": 0, "seconds": 0.0, "max_seconds": 0.0})
        row["count"] += 1
        row["seconds"] += seconds
        row["max_seconds"] = max(row["max_seconds"], seconds)


class RequestProbe:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        global SERIAL
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        with LOCK:
            SERIAL += 1
            index = SERIAL
        label = f"{index}:{scope['method']}:{scope['path']}"
        token = REQUEST.set(label)
        started = time.perf_counter()
        write("request_start", request=label)
        status = None

        async def sent(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            return await self.app(scope, receive, sent)
        finally:
            write(
                "request_end", request=label, status=status, seconds=time.perf_counter() - started
            )
            REQUEST.reset(token)


def backend(connection):
    return getattr(
        getattr(connection.connection.driver_connection, "info", None), "backend_pid", None
    )


def before(connection, _cursor, statement, parameters, context, _many):
    normalized = re.sub(r"test_[a-f0-9]+", "OWNED_SCHEMA", statement)
    key = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    with LOCK:
        STATEMENTS[key] = normalized
    locking = "grants" in statement and "FOR UPDATE" in statement
    row = {
        "started": time.perf_counter(),
        "request": REQUEST.get(),
        "signature": key,
        "operation": statement.lstrip().split(None, 1)[0],
        "backend": backend(connection),
        "locking": locking,
    }
    if locking:
        row["parameters"] = (
            list(parameters) if isinstance(parameters, (list, tuple)) else list(parameters.values())
        )
        # All values here are owned synthetic grant coordinates, not credentials.
        write("grant_lock_start", **{k: v for k, v in row.items() if k != "started"})
    with LOCK:
        PENDING[id(context)] = row


def finished(context, error=None):
    with LOCK:
        row = PENDING.pop(id(context), None)
    if row is None:
        return
    elapsed = time.perf_counter() - row.pop("started")
    group("sql", row["signature"], elapsed)
    if row["locking"] or error is not None or elapsed > 0.5:
        write("sql_end", **row, seconds=elapsed, sqlstate=getattr(error, "sqlstate", None))


def after(_connection, _cursor, _statement, _parameters, context, _many):
    finished(context)


def failed(error_context):
    finished(error_context.execution_context, error_context.original_exception)


def wrap(module, name):
    original = getattr(module, name)

    @functools.wraps(original)
    def measured(*args, **kwargs):
        before = time.perf_counter()
        if name == "initialize":
            write("initialize_start")
        try:
            return original(*args, **kwargs)
        finally:
            group("function", module.__name__ + "." + name, time.perf_counter() - before)
            if name == "initialize":
                write("initialize_end", seconds=time.perf_counter() - before)

    setattr(module, name, measured)
    RESTORES.append((module, name, original))


def pytest_configure(config):
    from sim2act import api
    from sim2act.db import Store

    original = api.create_app

    @functools.wraps(original)
    def app(*args, **kwargs):
        result = original(*args, **kwargs)
        result.add_middleware(RequestProbe)
        return result

    api.create_app = app
    RESTORES.append((api, "create_app", original))
    for name in ["initialize", "authorize"]:
        wrap(Store, name)
    from sim2act import conditional_apps, delivery_graph_apps, report_manifest_apps

    for module, names in [
        (conditional_apps, ["_load_validated_origin", "load"]),
        (
            report_manifest_apps,
            [
                "_read_canonical",
                "_fresh_origin",
                "_validate_canonical",
                "load",
                "promote",
                "preview",
                "records",
                "inspect",
            ],
        ),
        (
            delivery_graph_apps,
            [
                "load_family",
                "build",
                "current",
                "derive",
                "inspect",
                "expansion",
                "plan",
                "history",
            ],
        ),
    ]:
        for name in names:
            if hasattr(module, name):
                wrap(module, name)
    event.listen(Engine, "before_cursor_execute", before)
    event.listen(Engine, "after_cursor_execute", after)
    event.listen(Engine, "handle_error", failed)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    global NODE
    NODE = item.nodeid
    write("node_start")
    yield
    write("node_end")


def pytest_sessionfinish(session, exitstatus):
    rows = [
        {"node": key[0], "kind": key[1], "request": key[2], "identity": key[3], **value}
        for key, value in GROUPS.items()
    ]
    (ROOT / "hotspot-groups.json").write_text(
        json.dumps(
            {
                "groups": rows,
                "statements": STATEMENTS,
                "pending_sql": len(PENDING),
                "exitstatus": int(exitstatus),
                "limits": "nested function/SQL/request spans overlap; preload/observer overhead unpaired",
            },
            indent=2,
        )
        + "\n"
    )


def pytest_unconfigure(config):
    for module, name, original in reversed(RESTORES):
        setattr(module, name, original)
    for name, callback in [
        ("before_cursor_execute", before),
        ("after_cursor_execute", after),
        ("handle_error", failed),
    ]:
        event.remove(Engine, name, callback)
