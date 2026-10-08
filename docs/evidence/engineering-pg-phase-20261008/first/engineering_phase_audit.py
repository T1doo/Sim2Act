"""Passive diagnostic collection/report ledger; does not select or change tests."""

import json
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption("--engineering-audit-output", default=None)


def pytest_configure(config):
    config._engineering_reports = []
    config._engineering_nodes = []


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
            "exitstatus": int(exitstatus),
            "scope": "pytest_report_durations_not_subprocess_internal_spans",
        }, indent=2) + "\n", encoding="utf-8")


def pytest_unconfigure(config):
    global _active
    if _active is config:
        _active = None
