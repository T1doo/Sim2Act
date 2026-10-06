"""The executable demo traverses real HTTP/worker/review and never opens a socket."""

import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/protocol-store-dryrun.py"
spec = importlib.util.spec_from_file_location("protocol_store_dryrun", SCRIPT)
assert spec and spec.loader
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.fixture
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline demonstration attempted a real socket connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_two_forms_share_actual_database_pool_and_independent_reviews(no_network):
    report = demo.demonstrate()
    assert report["mock_calls"] == report["attempt_count"] == report["pool"]["slots_count"] == 8
    assert report["pool"]["request_limit"] == 14 and report["pool"]["known_tokens"] == 160
    assert len(report["offline_handoffs"]) == 6
    assert len(report["handoff_checks_before_reserve"]) == 8
    assert all(h["live_ready"] is False for h in report["offline_handoffs"])
    assert report["slot_attempt_bijection"] and report["distinct_job_approvals"] == 6
    assert report["phase_counts"] == {"source": 2, "extract": 2, "cold": 2}
    assert report["slot_phase_counts"] == {"source": 4, "extract": 2, "cold": 2}
    assert report["operation_count"] == 6 and report["operation_statuses"] == ["VERIFIED"]
    assert all(f["source_review"] == f["cold_review"] == "PASS" for f in report["forms"])
    assert all(
        f["source_technical_semantic"] == f["cold_technical_semantic"] == "UNKNOWN"
        for f in report["forms"]
    )
    assert report["real_model_semantics"] == "NOT_RUN" and report["owner_acceptance"] == "PENDING"
    assert report["external_requests"] == report["live_budget"] == 0
    assert report["request_bounds"]["max_chars"] <= 8000
    assert report["request_bounds"]["max_bytes"] <= 10000
    # The runtime API never accepts the mock candidate or a semantic verdict.
    for submission in report["submissions"]:
        assert (
            not {"candidate", "gold", "decision", "expected_output"} & submission["payload"].keys()
        )
    for family in ("a", "b"):
        source = next(w["body"] for w in report["wire"] if w["stage"] == "source_" + family)
        assert "resource.read" in json.dumps(source)
        assert all("gold_sha256" not in json.dumps(w["body"]) for w in report["wire"])


@pytest.mark.parametrize(
    "family, calls, counts",
    [
        ("a", 2, {"source": 1, "extract": 0, "cold": 0}),
        ("b", 6, {"source": 2, "extract": 1, "cold": 1}),
    ],
)
def test_failed_registered_source_review_stops_before_candidate_sending(
    no_network, family, calls, counts
):
    report = demo.demonstrate(fail_source=family)
    assert report["forms"][-1]["source_review"] == "FAIL"
    assert report["forms"][-1]["stopped_before"] == "extract"
    assert report["mock_calls"] == calls and report["phase_counts"] == counts
    assert not any(w["stage"] in {"extract_" + family, "cold_" + family} for w in report["wire"])
    assert report["pool"]["reserved_requests"] == calls and not report["pool"]["halted"]
    assert report["pool"]["known_tokens"] == calls * 20  # Known semantic FAIL is not UNKNOWN cost.


def test_cli_produces_reviewable_report_in_owned_output_directory(tmp_path):
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path), "--fail-source", "a"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    report = json.loads((tmp_path / "protocol-store-dryrun.json").read_text())
    assert report["mock_calls"] == 2 and report["forms"][0]["source_review"] == "FAIL"
    assert "network=0" in run.stdout and "owner=PENDING" in run.stdout


@pytest.mark.parametrize("wrapped", [False, True])
def test_isolation_audit_detects_nested_json_answer_and_escaped_material(wrapped):
    answer = {"private_fixture_answer": [1, 2]}
    material = "SOURCE text\nwith newline"
    content = {"nested": {"answer": answer, "content": material}}
    wire = {"messages": [{"role": "user", "content": json.dumps(content) if wrapped else content}]}
    with pytest.raises(AssertionError, match="Source answer|unrelated material"):
        demo.assert_isolated_wire(wire, [material], answer)
    with pytest.raises(AssertionError, match="Source answer"):
        demo.assert_isolated_wire(wire, answer=answer)


def test_missing_persisted_controller_handoff_blocks_first_send(no_network, monkeypatch):
    monkeypatch.setattr(demo, "prepare_handoff", lambda *args: {})
    actual_calls = []
    original = demo.ProtocolAttemptRunner.call

    def actual_call(self, messages, tools):
        actual_calls.append(True)
        return original(self, messages, tools)

    monkeypatch.setattr(demo.ProtocolAttemptRunner, "call", actual_call)
    with pytest.raises(AssertionError):
        demo.demonstrate()
    assert actual_calls == []  # require_handoff rejects before reserve/provider path.
