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

REMAINING11_SHA256 = "1f2b967e13bf163e1c19e33d9297f185f54d9c872a64295366142ac77021314e"


def remaining11_nodes(path=None):
    nodes = json.loads((path or Path(__file__).with_name("native-remaining11.json")).read_text(encoding="utf-8"))
    if (
        not isinstance(nodes, list)
        or len(nodes) != 11
        or any(not isinstance(node, str) for node in nodes)
        or len(set(nodes)) != 11
        or hashlib.sha256(json.dumps(nodes).encode()).hexdigest() != REMAINING11_SHA256
    ):
        raise ValueError("Fixed remaining11 manifest mismatch; no alternative selection.")
    return nodes


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
    def __init__(self, path, required_nodes=None):
        self.path = path
        self.required_nodes = required_nodes
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
        detail = {}
        if self.required_nodes is not None:
            detail = dict(requested_scope="DIAGNOSTIC_ONLY_REMAINING11", required_nodes=self.required_nodes)
        self.emit("session_start", visible=True, **detail)

    def pytest_collection_modifyitems(self, session, config, items):
        if self.required_nodes is None:
            return
        import pytest

        full_nodes = [redact(item.nodeid) for item in items]
        by_node = {item.nodeid: item for item in items}
        if len(by_node) != len(items) or any(node not in by_node for node in self.required_nodes):
            raise pytest.UsageError("Required remaining11 nodes missing or duplicate; no partial selection.")
        self.emit("full_collection", nodes=full_nodes)
        self.emit(
            "selection",
            visible=True,
            scope="DIAGNOSTIC_ONLY_REMAINING11",
            full_count=len(full_nodes),
            full_nodes_sha256=hashlib.sha256(json.dumps(full_nodes).encode()).hexdigest(),
            required_nodes=self.required_nodes,
            deselected_count=len(items) - len(self.required_nodes),
        )
        deselected = [item for item in items if item.nodeid not in self.required_nodes]
        items[:] = [by_node[node] for node in self.required_nodes]
        config.hook.pytest_deselected(items=deselected)

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
            visible=report.failed or self.required_nodes is not None,
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
        self.emit("node_finish", visible=self.required_nodes is not None, nodeid=redact(nodeid))

    def pytest_keyboard_interrupt(self, excinfo):
        self.emit("interrupted", visible=True, reason="KeyboardInterrupt")

    def pytest_sessionfinish(self, session, exitstatus):
        self.emit("session_finish", visible=True, exitstatus=int(exitstatus))


def pytest_addoption(parser):
    parser.addoption("--ci-diagnostics", type=Path, help="Explicit native CI JSONL path")
    parser.addoption("--ci-remaining11", action="store_true", help="Fixed diagnostic targets; not full acceptance")


def pytest_configure(config):
    path = config.getoption("--ci-diagnostics")
    required_nodes = None
    if config.getoption("--ci-remaining11"):
        import pytest

        if path is None:
            raise pytest.UsageError("Remaining11 requires explicit diagnostics; no silent reduced coverage.")
        required_nodes = remaining11_nodes()
    if path is not None:
        config.pluginmanager.register(Recorder(path, required_nodes), "sim2act-native-diagnostics")


def read_records(path):
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
    return records, incomplete_tail


def summarize(path):
    records, incomplete_tail = read_records(path)
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
    result = dict(
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
    selected = [r for r in records if r["event"] == "selection"]
    requested = [r for r in records if r.get("requested_scope") == "DIAGNOSTIC_ONLY_REMAINING11"]
    if selected or requested:
        selection = selected[-1] if selected else dict(
            scope="DIAGNOSTIC_ONLY_REMAINING11", required_nodes=requested[-1]["required_nodes"],
            full_count=None, full_nodes_sha256=None, deselected_count=None,
        )
        required = selection["required_nodes"]
        reports = [r for r in records if r["event"] == "node_report"]
        full = [r for r in records if r["event"] == "full_collection"]
        full_nodes = full[0]["nodes"] if len(full) == 1 else []
        pid = requested[0].get("pid") if len(requested) == 1 else None
        # A request header is evidence of intended scope, never a replacement
        # for the actual selection/full-collection records or their session.
        selection_verified = (
            len(requested) == len(selected) == len(full) == len(collected) == len(ends) == 1
            and requested[0] is records[0] and ends[0] is records[-1]
            and isinstance(pid, int) and not isinstance(pid, bool) and pid > 0
            and all(r.get("pid") == pid for r in records)
            and records.index(requested[0]) < records.index(full[0])
            < records.index(selected[0]) < records.index(collected[0])
            and selection["scope"] == "DIAGNOSTIC_ONLY_REMAINING11"
            and requested[0]["required_nodes"] == required == collected[0]["nodes"]
            and isinstance(full_nodes, list) and all(isinstance(node, str) for node in full_nodes)
            and len(set(full_nodes)) == len(full_nodes) >= 11
            and set(required) <= set(full_nodes)
            and selection["full_count"] == len(full_nodes)
            and selection["full_nodes_sha256"] == hashlib.sha256(json.dumps(full_nodes).encode()).hexdigest()
            and selection["deselected_count"] == len(full_nodes) - 11
            and sum(r["event"] == "node_start" for r in records) == 11
            and sum(r["event"] == "node_finish" for r in records) == 11
        )
        outcomes = {
            node: {phase: [r["outcome"] for r in reports if r["nodeid"] == node and r["phase"] == phase]
                   for phase in ("setup", "call", "teardown")}
            for node in required
        }
        result.update(
            scope="DIAGNOSTIC_ONLY_REMAINING11",
            full_collection_count=selection["full_count"],
            full_collection_sha256=selection["full_nodes_sha256"],
            deselected_count=selection["deselected_count"],
            required_outcomes=outcomes,
            selection_verified=selection_verified,
            required_targets_complete=selection_verified and result["suite_complete"] and nodes == set(required)
            and len(required) == 11 and len(set(required)) == 11
            and hashlib.sha256(json.dumps(required).encode()).hexdigest() == REMAINING11_SHA256
            and all(phases == {phase: ["passed"] for phase in ("setup", "call", "teardown")}
                    for phases in outcomes.values())
            and result["exitstatuses"] == [0] and not failures,
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--junit", required=True, type=Path)
    args = parser.parse_args()
    result = summarize(args.report)
    if result.get("scope") == "DIAGNOSTIC_ONLY_REMAINING11":
        records, _ = read_records(args.report)
        full = [r["nodes"] for r in records if r["event"] == "full_collection"]
        if full:
            for offset in range(0, len(full[-1]), 20):
                print("SIM2ACT_CI_FULL_COLLECTION " + json.dumps(dict(offset=offset, nodes=full[-1][offset:offset + 20])), flush=True)
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
    if result.get("scope") == "DIAGNOSTIC_ONLY_REMAINING11" and not result["required_targets_complete"]:
        raise SystemExit("Remaining11 incomplete/failed/skipped; full acceptance remains NOT_ACCEPTED.")


if __name__ == "__main__":
    main()
