"""Opt-in native CI evidence, emitted before cancellation can hide pytest failures."""

import argparse
import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def redact(text):
    text = re.sub(r"(?i)postgres(?:ql)?(?:\+\w+)?://[^\s\"'<>]+", "<redacted-database-url>", text)
    text = re.sub(r"(?i)\bBearer\s+[^\s\"'<>]+", "Bearer <redacted>", text)
    # Tracebacks include both evaluated values and their source-code escaping.
    # Hide the rest of a credential-bearing line rather than guessing the quote
    # layer; fully quoted multiline values must also be consumed as one value.
    return re.sub(
        r"(?i)(\b(?:[\w]*password|[\w]*authorization|[\w]*api[_-]?key|[\w]*token|[\w]*secret)\b[\"']?[ \t]*[:=][ \t]*)"
        r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\r\n]*)[^\r\n]*",
        r"\1<redacted>",
        text,
    )


class Recorder:
    def __init__(self, path):
        self.path = path
        self.start = time.monotonic()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event, *, visible=False, **values):
        record = dict(
            event=event,
            utc=datetime.now(UTC).isoformat(),
            elapsed_seconds=time.monotonic() - self.start,
            pid=os.getpid(),
            **values,
        )
        line = json.dumps(record, ensure_ascii=True)
        # Close each append before proceeding. Evidence survives Python interruption;
        # failure and start records are also flushed directly into durable Actions logs.
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        if visible:
            # pytest's progress dots may have left stdout mid-line.
            print("\nSIM2ACT_CI_DIAGNOSTIC " + line, flush=True)

    def pytest_sessionstart(self, session):
        self.emit("session_start", visible=True)

    def pytest_collection_finish(self, session):
        nodes = [redact(item.nodeid) for item in session.items]
        self.emit("collection", nodes=nodes)
        self.emit(
            "collection_summary",
            visible=True,
            count=len(nodes),
            nodes_sha256=hashlib.sha256(json.dumps(nodes).encode()).hexdigest(),
        )

    def pytest_runtest_logstart(self, nodeid, location):
        self.emit("node_start", visible=True, nodeid=redact(nodeid))

    def pytest_runtest_logreport(self, report):
        detail = {}
        if report.failed:
            text = redact(report.longreprtext)
            if len(text) > 16000:
                text = text[:8000] + "\n<diagnostic middle omitted>\n" + text[-8000:]
            detail["failure"] = text
        self.emit(
            "node_report",
            visible=report.failed,
            nodeid=redact(report.nodeid),
            phase=report.when,
            outcome=report.outcome,
            duration=report.duration,
            **detail,
        )

    def pytest_collectreport(self, report):
        if report.failed:
            self.emit(
                "collection_failed",
                visible=True,
                nodeid=redact(report.nodeid),
                failure=redact(report.longreprtext)[:16000],
            )

    def pytest_runtest_logfinish(self, nodeid, location):
        self.emit("node_finish", nodeid=redact(nodeid))

    def pytest_keyboard_interrupt(self, excinfo):
        self.emit("interrupted", visible=True, reason="KeyboardInterrupt")

    def pytest_sessionfinish(self, session, exitstatus):
        self.emit("session_finish", visible=True, exitstatus=int(exitstatus))


def pytest_addoption(parser):
    parser.addoption("--ci-diagnostics", type=Path, help="Explicit native CI JSONL path")


def pytest_configure(config):
    path = config.getoption("--ci-diagnostics")
    if path is not None:
        config.pluginmanager.register(Recorder(path), "sim2act-native-diagnostics")


def summarize(path):
    records = []
    incomplete_tail = False
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                if index != len(lines) - 1:
                    raise
                incomplete_tail = True
    collected = [r for r in records if r["event"] == "collection"]
    started = {r["nodeid"] for r in records if r["event"] == "node_start"}
    finished = {r["nodeid"] for r in records if r["event"] == "node_finish"}
    failures = [
        r
        for r in records
        if r["event"] == "collection_failed"
        or (r["event"] == "node_report" and r["outcome"] == "failed")
    ]
    ends = [r for r in records if r["event"] == "session_finish"]
    nodes = set().union(*(set(r["nodes"]) for r in collected)) if collected else set()
    return dict(
        evidence_present=bool(records),
        collected=len(nodes),
        started=len(started),
        finished=len(finished),
        active_nodes=sorted(started - finished),
        not_started_count=len(nodes - started),
        failures=failures,
        exitstatuses=[r["exitstatus"] for r in ends],
        incomplete_tail=incomplete_tail,
        suite_complete=bool(ends)
        and len(finished) == len(nodes)
        and all(r["exitstatus"] in (0, 1) for r in ends)
        and not incomplete_tail,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--junit", required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.report)
    for failure in result["failures"]:
        print("SIM2ACT_CI_FAILURE " + json.dumps(failure), flush=True)
    summary = {k: v for k, v in result.items() if k != "failures"}
    summary["failure_reports"] = len(result["failures"])
    if args.junit.exists():
        root = ET.parse(args.junit).getroot()
        summary["junit"] = [suite.attrib for suite in root.iter("testsuite")]
    else:
        summary["junit"] = "NOT_RUN: no engineering JUnit"
    text = "Engineering diagnostics: " + json.dumps(summary)
    print(text, flush=True)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with Path(step_summary).open("a", encoding="utf-8") as stream:
            stream.write(
                "\n" + text + "\nWin11 product acceptance: NOT_RUN. Real model requests: 0.\n"
            )


if __name__ == "__main__":
    main()
