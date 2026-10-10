"""Exercise the real pytest lifecycle, including failure before interruption."""

import hashlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
summarize = runpy.run_path(str(ROOT / "scripts/native_pytest_diagnostics.py"))["summarize"]


def test_fixed_remaining_manifest_rejects_missing_duplicate_and_changed_nodes(tmp_path):
    load = runpy.run_path(str(ROOT / "scripts/native_pytest_diagnostics.py"))["remaining11_nodes"]
    expected = load()
    for changed in [expected[:-1], expected[:-1] + [expected[0]], expected[:-1] + ["tests/test_other.py::test_other"]]:
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="manifest mismatch"):
            load(path)
    # Windows checkout line endings do not change the canonical identity.
    path.write_bytes(json.dumps(expected, indent=2).replace("\n", "\r\n").encode())
    assert load(path) == expected


@pytest.mark.parametrize("state", ["complete", "skipped", "interrupted", "partial_tail",
                                   "missing_selection", "missing_full", "wrong_full_hash", "wrong_full_count",
                                   "foreign_start", "foreign_finish", "wrong_header", "extra_session",
                                   "foreign_phase", "swapped_events"])
def test_remaining_scope_requires_all_actual_phases_and_complete_tail(tmp_path, state):
    load = runpy.run_path(str(ROOT / "scripts/native_pytest_diagnostics.py"))["remaining11_nodes"]
    nodes = load()
    full_nodes = nodes + ["tests/test_unselected_fixture.py::test_unselected"]
    records = [dict(event="session_start", requested_scope="DIAGNOSTIC_ONLY_REMAINING11", required_nodes=nodes),
               dict(event="full_collection", nodes=full_nodes),
               dict(event="selection", scope="DIAGNOSTIC_ONLY_REMAINING11", required_nodes=nodes,
                    full_count=len(full_nodes), full_nodes_sha256=hashlib.sha256(json.dumps(full_nodes).encode()).hexdigest(), deselected_count=1),
               dict(event="collection", nodes=nodes)]
    for node in nodes:
        records.append(dict(event="node_start", nodeid=node))
        if state == "interrupted" and node == nodes[-1]:
            break
        for phase in ("setup", "call", "teardown"):
            outcome = "skipped" if state == "skipped" and node == nodes[-1] and phase == "call" else "passed"
            records.append(dict(event="node_report", nodeid=node, phase=phase, outcome=outcome))
        records.append(dict(event="node_finish", nodeid=node))
    records.append(dict(event="session_finish", exitstatus=2 if state == "interrupted" else 0))
    for record in records:
        record["pid"] = 1  # Finite recorder fixture only, not a native execution.
    if state in {"missing_selection", "missing_full"}:
        removed = "selection" if state == "missing_selection" else "full_collection"
        records = [r for r in records if r["event"] != removed]
    elif state == "wrong_full_hash":
        records[2]["full_nodes_sha256"] = "different"
    elif state == "wrong_full_count":
        records[2]["full_count"] += 1
    elif state in {"foreign_start", "foreign_finish"}:
        event = "node_start" if state == "foreign_start" else "node_finish"
        next(r for r in records if r["event"] == event)["nodeid"] = "foreign-node"
    elif state == "wrong_header":
        records[0]["event"] = "different-event"
    elif state == "extra_session":
        records.insert(1, dict(event="session_start", pid=1))
    elif state == "foreign_phase":
        records.insert(-1, dict(event="node_report", nodeid="foreign-node", phase="call", outcome="passed", pid=1))
    elif state == "swapped_events":
        start = next(i for i, r in enumerate(records) if r["event"] == "node_start")
        finish = next(i for i, r in enumerate(records) if r["event"] == "node_finish")
        records[start], records[finish] = records[finish], records[start]
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + ('\n{"event":' if state == "partial_tail" else "\n"))
    result = summarize(path)
    assert result["scope"] == "DIAGNOSTIC_ONLY_REMAINING11"
    assert result["required_targets_complete"] == (state == "complete")
    assert len(result["required_outcomes"]) == 11
    assert result["not_started_count"] == (1 if state == "foreign_start" else 0)


def test_remaining_requested_but_missing_selection_is_not_verified(tmp_path):
    nodes = runpy.run_path(str(ROOT / "scripts/native_pytest_diagnostics.py"))["remaining11_nodes"]()
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps(dict(event="session_start", requested_scope="DIAGNOSTIC_ONLY_REMAINING11", required_nodes=nodes)) + "\n")
    result = summarize(path)
    assert not result["required_targets_complete"] and result["full_collection_count"] is None


@pytest.mark.parametrize("mode", ["interrupt", "collection_error", "failure"])
def test_actual_pytest_failure_evidence_survives_incomplete_suite(tmp_path, mode):
    root = Path(__file__).resolve().parents[1]
    trace = tmp_path / "events.jsonl"
    xml = tmp_path / "junit.xml"
    secrets = [
        "fake-db-secret",
        "fake-bearer-secret",
        "fake-basic-secret",
        "fake-spaced-password",
        "fake-escaped-secret",
        "fake-unquoted-secret",
    ]
    if mode != "collection_error":
        code = r"""
def test_failure():
    assert False, "diagnostic assertion; postgresql+psycopg://fixture:fake-db-secret@localhost/db; Bearer fake-bearer-secret; authorization='Basic fake-basic-secret'; password='first fake-spaced-password'; secret='first\\' fake-escaped-secret'; authorization=Basic fake-unquoted-secret"

def test_pass():
    assert True

def test_interrupted():
    raise KeyboardInterrupt

def test_never_started():
    assert False, "unexecuted fixture"
"""
        if mode == "failure":
            code = code.split("def test_interrupted():")[0]
    else:
        code = 'raise RuntimeError("collection diagnostic assertion")\n'
    (tmp_path / "test_fixture.py").write_text(code)
    env = {**os.environ, "PYTHONPATH": str(root), "PYTHONUTF8": "1"}
    # The isolated fixture must not overwrite the outer CI suite's JUnit output.
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("GITHUB_STEP_SUMMARY", None)
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "scripts.native_pytest_diagnostics",
            "--ci-diagnostics",
            str(trace),
            "--junitxml",
            str(xml),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert child.returncode == (1 if mode == "failure" else 2)
    result = summarize(trace)
    assert result["evidence_present"] and result["suite_complete"] == (mode == "failure")
    assert result["exitstatuses"] == [child.returncode]
    assert len(result["failures"]) == 1
    assert "diagnostic assertion" in result["failures"][0]["failure"]
    diagnostics = "\n".join(
        line for line in child.stdout.splitlines() if line.startswith("SIM2ACT_CI_DIAGNOSTIC ")
    )
    assert "diagnostic assertion" in diagnostics
    for secret in secrets:
        assert secret not in diagnostics + trace.read_text()
    if mode == "interrupt":
        assert result["collected"] == 4 and result["started"] == 3 and result["finished"] == 2
        assert result["not_started_count"] == 1
        assert result["active_nodes"] == ["test_fixture.py::test_interrupted"]
        assert result["failures"][0]["nodeid"] == "test_fixture.py::test_failure"
        assert result["failures"][0]["phase"] == "call"
        assert "test_fixture.py::test_interrupted" in diagnostics
    elif mode == "collection_error":
        assert result["failures"][0]["event"] == "collection_failed"
    else:
        baseline = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert baseline.returncode == child.returncode == 1
        assert result["collected"] == result["finished"] == 2
        assert "1 failed, 1 passed" in baseline.stdout and "1 failed, 1 passed" in child.stdout
    report = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/native_pytest_diagnostics.py"),
            "--report",
            str(trace),
            "--junit",
            str(xml),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert report.returncode == 0
    assert "SIM2ACT_CI_FAILURE" in report.stdout
    assert "diagnostic assertion" in report.stdout
    assert (
        '"suite_complete": true' if mode == "failure" else '"suite_complete": false'
    ) in report.stdout
    for secret in secrets:
        assert secret not in report.stdout
    (tmp_path / "child.log").write_text(child.stdout + child.stderr)
    (tmp_path / "report.log").write_text(report.stdout + report.stderr)


def test_partial_last_append_is_incomplete_evidence(tmp_path):
    path = tmp_path / "partial.jsonl"
    path.write_text(json.dumps(dict(event="node_start", nodeid="actual_started")) + '\n{"event":')
    result = summarize(path)
    assert result["active_nodes"] == ["actual_started"]
    assert result["incomplete_tail"] and not result["suite_complete"]
    path.write_text('{"event":\n' + json.dumps(dict(event="session_finish", exitstatus=0)))
    with pytest.raises(json.JSONDecodeError):
        summarize(path)
