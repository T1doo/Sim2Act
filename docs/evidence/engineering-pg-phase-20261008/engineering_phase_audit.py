"""Passive diagnostic collection/report ledger; does not select or change tests."""

import json
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--engineering-audit-output", default=None)


def pytest_configure(config):
    config._engineering_reports = []
    config._engineering_nodes = []
    config._engineering_env_definitions = {}


def pytest_collection_finish(session):
    session.config._engineering_nodes = [item.nodeid for item in session.items]


def pytest_runtest_logreport(report):
    # The config is not on TestReport; the session-level plugin object records reports.
    if _active is not None:
        _active._engineering_reports.append(
            {"nodeid": report.nodeid, "phase": report.when,
             "outcome": report.outcome, "seconds": report.duration}
        )


_active = None


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    outcome = yield
    if fixturedef.argname == "env":
        definitions = request.config._engineering_env_definitions
        key = fixturedef.baseid
        row = definitions.setdefault(key, {"count": 0, "failed": 0, "dialects": {}})
        row["count"] += 1
        if outcome.excinfo is not None:
            row["failed"] += 1
        else:
            value = outcome.get_result()
            if isinstance(value, tuple) and value and hasattr(value[0], "engine"):
                dialect = value[0].engine.dialect.name
                dialect = dialect if dialect in {"postgresql", "sqlite"} else "other"
                row["dialects"][dialect] = row["dialects"].get(dialect, 0) + 1


def pytest_sessionstart(session):
    global _active
    _active = session.config


def pytest_sessionfinish(session, exitstatus):
    output = session.config.getoption("--engineering-audit-output")
    if output is not None:
        Path(output).write_text(json.dumps({
            "schema": "sim2act.engineering-phase-audit.v1",
            "nodes": session.config._engineering_nodes,
            "reports": session.config._engineering_reports,
            "env_fixture_definitions": session.config._engineering_env_definitions,
            "exitstatus": int(exitstatus),
            "scope": "pytest_report_durations_not_subprocess_internal_spans",
        }, indent=2) + "\n", encoding="utf-8")


def pytest_unconfigure(config):
    global _active
    if _active is config:
        _active = None
