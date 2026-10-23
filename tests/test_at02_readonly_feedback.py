"""Actual SQLite authorization/read gateway and adapter, with finite Mock HTTP only."""

import importlib.util
import json
import sqlite3
import stat
import time
from pathlib import Path

import httpx
import pytest
from sqlalchemy import update

from sim2act.db import Store, grants

FILE = Path(__file__).resolve().parents[1] / "scripts/diagnostics/at02_readonly_feedback.py"
spec = importlib.util.spec_from_file_location("at02_feedback", FILE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
TOKEN = "synthetic-at02-credential-not-real"


class Clock:
    def __init__(self):
        self.start, self.offset = time.time(), 0.0

    def now(self):
        return self.start + self.offset

    def sleep(self, seconds):
        self.offset += seconds


def reply(w, *, final=False):
    message = dict(role="assistant", content="")
    reason = "tool_calls"
    if final:
        message["content"] = "S2A-RO-2947"
        reason = "stop"
    else:
        message["tool_calls"] = [dict(id="read_synthetic_1", type="function", function=dict(
            name="resource.read", arguments=json.dumps({"resource_id": w["resource_id"]})))]
    return dict(model="Intern-S2", choices=[dict(finish_reason=reason, message=message)],
                usage=dict(prompt_tokens=100, completion_tokens=20, total_tokens=120))


def execute(tmp_path, change=None, *, setup=None, receive=None):
    case, output = tmp_path / "case", tmp_path / "output"
    w = runner.prepare(case)
    if setup:
        setup(case, w)
    seen = []

    def handler(request):
        body = json.loads(request.content)
        assert body["max_tokens"] == 512 and body["model"] == "intern-s2"
        assert len(request.content) <= 1988
        seen.append(body)
        if receive:
            return receive(request, w)
        raw = reply(w, final=len(seen) == 2)
        if change:
            change(raw, len(seen), case, w)
        return httpx.Response(200, json=raw)

    clock = Clock()
    report = runner.run(case, output, environ={"INTERN_API_TOKEN": TOKEN},
        _transport=httpx.MockTransport(handler), _wall=clock.now,
        _monotonic=clock.now, _sleep=clock.sleep)
    assert TOKEN not in (output / "result.json").read_text()
    return report, seen, case, w


def test_two_requests_original_gateway_feedback_no_writes_and_no_reuse(tmp_path):
    report, seen, case, _ = execute(tmp_path)
    assert report["status"] == "PASS_BOUNDED_READONLY_FEEDBACK"
    assert len(seen) == 2 and report["tool_reads"] == 1 and report["known_tokens"] == 240
    assert report["source_inventory_unchanged"] is True
    assert all(q["kind"] in ("SELECT", "PRAGMA") for q in report["sql"])
    assert report["reserved_envelope"] <= 5000 and report["retries"] == 0
    assert "S2A-RO-2947" not in json.dumps(seen[0])
    feedback = seen[1]["messages"][-1]
    assert feedback["role"] == "tool" and feedback["tool_call_id"] == "read_synthetic_1"
    assert json.loads(feedback["content"]) == report["tool_feedback"]["result"]
    assert seen[1]["messages"][-2] == report["slots"][0]["assistant"]
    assert seen[1]["tools"] == []
    with pytest.raises(FileExistsError):
        runner.run(case, tmp_path / "different-output", environ={"INTERN_API_TOKEN": TOKEN})


@pytest.mark.parametrize("failure", ["direct", "wrong_resource", "many", "wrong_model", "usage", "length"])
def test_first_failure_never_reads_or_sends_second(tmp_path, failure):
    def change(raw, number, _case, _w):
        assert number == 1
        message = raw["choices"][0]["message"]
        if failure == "direct":
            message.pop("tool_calls")
            message["content"] = "S2A-RO-2947"
            raw["choices"][0]["finish_reason"] = "stop"
        elif failure == "wrong_resource":
            message["tool_calls"][0]["function"]["arguments"] = json.dumps({"resource_id": "res_" + "e" * 32})
        elif failure == "many":
            second = json.loads(json.dumps(message["tool_calls"][0]))
            second["id"] = "another"
            message["tool_calls"].append(second)
        elif failure == "wrong_model":
            raw["model"] = "unapproved"
        elif failure == "usage":
            raw.pop("usage")
        elif failure == "length":
            raw["choices"][0]["finish_reason"] = "length"

    report, seen, _, _ = execute(tmp_path, change)
    assert len(seen) == 1 and report["status"] == "STOPPED_NO_RETRY"
    assert report["tool_reads"] == 0
    assert len(report["slots"]) == 1 and report["reserved_envelope"] > 0


def test_second_body_over_budget_is_not_truncated_or_sent(tmp_path):
    def change(raw, _number, _case, _w):
        raw["choices"][0]["message"]["content"] = "x" * 1900

    report, seen, _, _ = execute(tmp_path, change)
    assert len(seen) == 1 and report["tool_reads"] == 1
    assert report["error_code"] == "BUDGET_EXHAUSTED"


def test_fixture_change_after_response_stops_before_tool(tmp_path):
    def change(_raw, _number, case, _w):
        (case / "source/material.txt").write_text("changed\n")

    report, seen, _, _ = execute(tmp_path, change)
    assert len(seen) == 1 and report["tool_reads"] == 0
    assert report["error_code"] == "FIXTURE_CHANGED"
    assert report["source_inventory_unchanged"] is False


def test_revoked_original_gateway_grant_rejects_before_first_send(tmp_path):
    def revoke(case, w):
        store = Store("sqlite:///" + str(case / "source/fixture.sqlite"), test_only=True)
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.principal_id == w["runtime"]).values(revoked=True))
        store.engine.dispose()
        # Test-only refreeze makes the original authority predicate, rather than drift, reject.
        w["inventory"] = runner.inventory(case / "source")
        runner._save(case / "control/prepared.json", w)

    report, seen, _, _ = execute(tmp_path, setup=revoke)
    assert seen == [] and report["tool_reads"] == 0
    assert report["error_code"] == "GRANT_REVOKED"


def test_runtime_link_rejected_even_with_supplied_grants(tmp_path):
    def wrong(case, w):
        w["runtime"] = w["user"]  # Both have grants; project relation must still be exact.
        runner._save(case / "control/prepared.json", w)

    report, seen, _, _ = execute(tmp_path, setup=wrong)
    assert seen == [] and report["error_code"] == "RUNTIME_MISMATCH"


def test_escaped_credential_reflection_no_hash_or_persist(tmp_path):
    def receive(_request, w):
        raw = reply(w)
        raw["private_reasoning"] = TOKEN
        body = json.dumps(raw).replace(TOKEN, "".join("\\u%04x" % ord(c) for c in TOKEN))
        return httpx.Response(200, content=body)

    report, seen, _, _ = execute(tmp_path, receive=receive)
    assert len(seen) == 1 and report["error_code"] == "CREDENTIAL_REFLECTION"
    assert "response_sha256" not in report["slots"][0]


def test_upstream_refusal_never_retries(tmp_path):
    report, seen, _, _ = execute(tmp_path, receive=lambda _request, _w: httpx.Response(403))
    assert len(seen) == 1 and report["slots"][0]["http_status"] == 403
    assert report["status"] == "STOPPED_NO_RETRY" and report["tool_reads"] == 0


def test_sql_write_rejected_before_execution_and_source_unchanged(tmp_path):
    case = tmp_path / "case"
    w = runner.prepare(case)
    source = runner.ReadSource(case, w, [])
    try:
        with source.connection() as c:
            with pytest.raises(runner.DomainError):
                c.exec_driver_sql("UPDATE resources SET content='bad'")
            with pytest.raises(runner.DomainError):
                c.exec_driver_sql("ATTACH DATABASE ':memory:' AS other")
            raw = c.connection.driver_connection
            for sql in ("UPDATE resources SET content='bad'", "PRAGMA query_only=OFF",
                        "ATTACH DATABASE ':memory:' AS other"):
                with pytest.raises(sqlite3.DatabaseError):
                    raw.execute(sql)
        assert runner.inventory(case / "source") == w["inventory"]
    finally:
        source.store.engine.dispose()


def test_prepared_prompt_tampering_cannot_send_other_input(tmp_path):
    def tamper(case, w):
        w["first_messages"][1]["content"] = "Unapproved substituted input"
        runner._save(case / "control/prepared.json", w)

    report, seen, _, _ = execute(tmp_path, setup=tamper)
    assert seen == [] and report["status"] == "STOPPED_NO_RETRY"


def test_omitted_source_witness_rejected_before_connection(tmp_path):
    def tamper(case, w):
        w["source_sha256"].pop("src/sim2act/production_evidence.py")
        runner._save(case / "control/prepared.json", w)

    report, seen, _, _ = execute(tmp_path, setup=tamper)
    assert seen == [] and report["status"] == "STOPPED_NO_RETRY"


def test_global_deadline_stops_after_first_no_second_send(tmp_path, monkeypatch):
    monkeypatch.setattr(Clock, "sleep", lambda self, seconds: setattr(self, "offset", self.offset + 601))
    report, seen, _, _ = execute(tmp_path)
    assert len(seen) == 1 and report["error_code"] == "DIAGNOSTIC_DEADLINE"
    assert report["within_600_seconds"] is False


def test_wrong_second_answer_keeps_two_actual_calls_and_one_read(tmp_path):
    def wrong(raw, number, _case, _w):
        if number == 2:
            raw["choices"][0]["message"]["content"] = "wrong"

    report, seen, _, _ = execute(tmp_path, wrong)
    assert len(seen) == 2 and report["tool_reads"] == 1
    assert report["error_code"] == "REVISION_REJECTED" and report["retries"] == 0


@pytest.mark.parametrize("prompt,completion", [(100, 513), (9000, 20)])
def test_usage_over_output_or_reservation_stops_and_keeps_actual(tmp_path, prompt, completion):
    def over(raw, _number, _case, _w):
        raw["usage"] = dict(prompt_tokens=prompt, completion_tokens=completion,
                            total_tokens=prompt + completion)

    report, seen, _, _ = execute(tmp_path, over)
    assert len(seen) == 1 and report["tool_reads"] == 0
    assert report["error_code"] == "BUDGET_EXHAUSTED"
    assert report["known_tokens"] == prompt + completion


def test_claim_directory_fsync_failure_consumes_claim_without_sending(tmp_path, monkeypatch):
    case = tmp_path / "case"
    runner.prepare(case)
    original = runner.os.fsync

    def fail_directory(fd):
        if stat.S_ISDIR(runner.os.fstat(fd).st_mode):
            raise OSError("synthetic directory sync failure")
        return original(fd)

    monkeypatch.setattr(runner.os, "fsync", fail_directory)
    with pytest.raises(OSError):
        runner.run(case, tmp_path / "output", environ={"INTERN_API_TOKEN": TOKEN},
                   _transport=httpx.MockTransport(lambda _: pytest.fail("No send")))
    assert (case / "control/execution-claim.json").exists()
    assert not (tmp_path / "output").exists()
    with pytest.raises(FileExistsError):
        runner.run(case, tmp_path / "other", environ={"INTERN_API_TOKEN": TOKEN})
