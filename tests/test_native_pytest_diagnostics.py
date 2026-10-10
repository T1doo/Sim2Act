"""Exercise the real pytest lifecycle, including failure before interruption."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
summarize = runpy.run_path(str(ROOT / "scripts/native_pytest_diagnostics.py"))["summarize"]


@pytest.mark.parametrize("mode", ["interrupt", "collection_error", "failure"])
def test_actual_pytest_failure_evidence_survives_incomplete_suite(tmp_path, mode):
    root = Path(__file__).resolve().parents[1]
    trace = tmp_path / "events.jsonl"
    xml = tmp_path / "junit.xml"
    if mode != "collection_error":
        code = """
def test_failure():
    assert False, "diagnostic assertion; postgresql+psycopg://fixture:fake-db-secret@localhost/db; Bearer fake-bearer-secret"

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
    assert "fake-db-secret" not in diagnostics + trace.read_text()
    assert "fake-bearer-secret" not in diagnostics + trace.read_text()
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
    assert "fake-db-secret" not in report.stdout and "fake-bearer-secret" not in report.stdout
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
