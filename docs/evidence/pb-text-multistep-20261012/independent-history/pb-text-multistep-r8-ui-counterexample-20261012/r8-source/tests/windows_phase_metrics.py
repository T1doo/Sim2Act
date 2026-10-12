"""Opt-in pytest-process metrics; no SQL text, values, URLs, or fixture IDs exported.

Load explicitly: PYTHONPATH=tests:src pytest -p windows_phase_metrics
                --windows-metrics-output=/tmp/windows-metrics.json
No database is created by loading this plugin. It does not profile subprocesses.
"""

import functools
import json
import platform
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.dialects.sqlite.base import SQLiteDialect
from sqlalchemy.engine import Engine

FIXTURES = frozenset({"env", "runtime_role", "browser_seed", "registered_browser_fixture"})
SCOPES = frozenset({"function", "class", "module", "package", "session"})


class Metrics:
    def __init__(self, clock=time.perf_counter):
        self.clock = clock
        self.started = clock()
        self.local = threading.local()
        self.lock = threading.Lock()
        self.groups = {}
        self.pending = {}
        self.restores = []
        self.listeners = []

    def label(self):
        return getattr(self.local, "fixture", "outside_fixture")

    def record(self, family, labels, started, failed=False):
        elapsed = max(0.0, self.clock() - started)
        key = (family, *labels)
        with self.lock:
            row = self.groups.setdefault(
                key, {"count": 0, "errors": 0, "seconds": 0.0, "max_seconds": 0.0}
            )
            row["count"] += 1
            row["errors"] += int(failed)
            row["seconds"] += elapsed
            row["max_seconds"] = max(row["max_seconds"], elapsed)

    def wrap(self, cls, name, family, phase):
        original = getattr(cls, name)

        @functools.wraps(original)
        def measured(*args, **kwargs):
            started = self.clock()
            previous = getattr(self.local, phase, 0)
            self.local.__dict__[phase] = previous + 1
            failed = False
            try:
                return original(*args, **kwargs)
            except BaseException:
                failed = True
                raise
            finally:
                self.local.__dict__[phase] = previous
                self.record(family, (self.label(),), started, failed)

        setattr(cls, name, measured)
        self.restores.append((cls, name, original, measured))

    def before(self, connection, _cursor, statement, _parameters, context, _executemany):
        # Inspect only operation prefix; neither statement nor parameters are retained.
        if getattr(self.local, "has_table", 0):
            operation = "existence"
        elif context.isddl:
            operation = "ddl"
        else:
            prefix = statement.lstrip()[:16].split(None, 1)[0].upper() if statement.strip() else ""
            operation = (
                prefix.lower() if prefix in {"SELECT", "INSERT", "UPDATE", "DELETE"} else "other"
            )
        dialect = connection.dialect.name
        dialect = dialect if dialect in {"sqlite", "postgresql"} else "other"
        phase = "initialization" if getattr(self.local, "initialization", 0) else "other"
        with self.lock:
            self.pending[id(context)] = (self.clock(), (phase, dialect, operation))

    def finish(self, context, failed):
        if context is None:
            return
        with self.lock:
            saved = self.pending.pop(id(context), None)
        if saved is not None:
            self.record("sql", saved[1], saved[0], failed)

    def after(self, _connection, _cursor, _statement, _parameters, context, _executemany):
        self.finish(context, False)

    def error(self, exception_context):
        # Original exceptions and parameter values are never inspected or replaced.
        self.finish(exception_context.execution_context, True)

    def install(self, store_class):
        self.wrap(store_class, "initialize", "initialize", "initialization")
        self.wrap(PGDialect, "has_table", "has_table", "has_table")
        self.wrap(SQLiteDialect, "has_table", "has_table", "has_table")
        callbacks: list[tuple[str, Callable[..., Any]]] = [
            ("before_cursor_execute", self.before),
            ("after_cursor_execute", self.after),
            ("handle_error", self.error),
        ]
        for name, callback in callbacks:
            event.listen(Engine, name, callback)
            self.listeners.append((name, callback))

    def uninstall(self):
        for name, callback in reversed(self.listeners):
            event.remove(Engine, name, callback)
        self.listeners.clear()
        for cls, name, original, measured in reversed(self.restores):
            # Never overwrite a subsequent patch made by a test or another plugin.
            if getattr(cls, name) is measured:
                setattr(cls, name, original)
        self.restores.clear()

    def report(self, collected, exitstatus):
        with self.lock:
            groups = [
                {"family": key[0], "labels": list(key[1:]), **value}
                for key, value in sorted(self.groups.items())
            ]
            pending = len(self.pending)
        return {
            "schema": "sim2act.windows-phase-metrics.v1",
            "scope": "pytest_process_only",
            "platform": {"Windows": "windows", "Linux": "linux"}.get(platform.system(), "other"),
            "collected_cases": collected,
            "pytest_exitstatus": int(exitstatus),
            "elapsed_seconds": max(0.0, self.clock() - self.started),
            "pending_sql": pending,
            "measurement_status": "COMPLETE" if pending == 0 else "INCOMPLETE",
            "groups": groups,
            "limitations": [
                "nested_or_concurrent_totals_overlap",
                "subprocesses_not_observed",
                "cursor_time_excludes_fetch_and_commit",
                "no_windows_budget_verdict",
            ],
        }


def pytest_addoption(parser):
    parser.addoption(
        "--windows-metrics-output",
        default=None,
        help="Opt-in aggregate diagnostic JSON; no SQL/parameter/config content",
    )


def pytest_configure(config):
    if config.getoption("--windows-metrics-output") is None:
        return
    from sim2act.db import Store

    collector = Metrics()
    try:
        collector.install(Store)
    except BaseException:
        collector.uninstall()
        raise
    config._sim2act_phase_metrics = collector


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    collector = getattr(request.config, "_sim2act_phase_metrics", None)
    if collector is None:
        yield
        return
    name = fixturedef.argname if fixturedef.argname in FIXTURES else "other"
    scope = fixturedef.scope if fixturedef.scope in SCOPES else "other"
    previous = getattr(collector.local, "fixture", "outside_fixture")
    collector.local.fixture = name
    started = collector.clock()
    try:
        outcome = yield
    finally:
        collector.local.fixture = previous
    collector.record("fixture_setup", (name, scope), started, outcome.excinfo is not None)


def pytest_sessionfinish(session, exitstatus):
    collector = getattr(session.config, "_sim2act_phase_metrics", None)
    if collector is None:
        return
    report = collector.report(len(session.items), exitstatus)
    collector.uninstall()
    try:
        Path(session.config.getoption("--windows-metrics-output")).write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        terminal = session.config.pluginmanager.getplugin("terminalreporter")
        if terminal is not None:
            terminal.write_line(
                "Phase metrics unavailable (" + type(exc).__name__ + "); test outcome unchanged."
            )


def pytest_unconfigure(config):
    collector = getattr(config, "_sim2act_phase_metrics", None)
    if collector is not None:
        collector.uninstall()
