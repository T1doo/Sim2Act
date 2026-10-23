"""Only owned synthetic SQLite, original adapter + MockTransport, no real HTTP."""

import importlib.util
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from sqlalchemy import update
from test_goal_text_applications import fixture_candidate

from sim2act.db import Store, grants

FILE = Path(__file__).resolve().parents[1] / "scripts/diagnostics/pa_literal_candidate.py"
spec = importlib.util.spec_from_file_location("pa_literal_runner", FILE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
TOKEN = "synthetic-pa-credential-not-real"


@pytest.fixture(autouse=True)
def source_import_path_for_child_processes(monkeypatch):
    # pytest's pythonpath configuration is not inherited by new Python processes.
    monkeypatch.setenv("PYTHONPATH", str(FILE.parents[2] / "src"))


class Clock:
    def __init__(self):
        self.start, self.offset = time.time(), 0.0

    def now(self):
        return self.start + self.offset

    def sleep(self, seconds):
        self.offset += seconds


def response(w, final):
    context = w["context"]
    if final:
        value = fixture_candidate(json.loads(context["messages"][1]["content"]))
        value["source_hash"] = context["source"]["hash"]
        message = dict(role="assistant", content=json.dumps(value, separators=(",", ":")))
    else:
        message = dict(role="assistant", content="", tool_calls=[dict(
            id="bound-material-read", type="function", function=dict(name="resource.read",
                arguments=json.dumps({"resource_id": context["source"]["resource_id"]})))])
    return dict(model="Intern-S2", choices=[dict(message=message,
        finish_reason="stop" if final else "tool_calls")], usage=dict(
            prompt_tokens=100, completion_tokens=900, total_tokens=1000))


def execute(tmp_path, *, change=None, setup=None, receive=None):
    case, output = tmp_path / "case", tmp_path / "output"
    w = runner.prepare(case)
    clock, seen = Clock(), []
    if setup:
        setup(case, w, clock)

    def handler(request):
        seen.append(json.loads(request.content))
        assert request.url == runner.ENDPOINT and seen[-1]["max_tokens"] == 1024
        assert request.headers["authorization"] == "Bearer " + TOKEN
        # The on-disk reservation exists before actual adapter IO.
        ledger = json.loads((output / "result.json").read_text())
        slot = ledger["slots"][-1]
        assert slot["request_sha256"] == runner.digest(request.content)
        assert slot["guard_entries"] == 1 and slot["read_connections_open"] == 0
        assert ledger["reserved_envelope"] == sum(s["reserved"] for s in ledger["slots"])
        if receive:
            return receive(request, w, clock)
        raw = response(w, len(seen) == 2)
        if change:
            change(raw, len(seen), case, w, clock)
        return httpx.Response(200, json=raw)

    report = runner.run_worker(case, output, environ={"INTERN_API_TOKEN": TOKEN},
        _transport=httpx.MockTransport(handler), _wall=clock.now,
        _monotonic=clock.now, _sleep=clock.sleep)
    assert TOKEN not in (output / "result.json").read_text()
    return report, seen, case, output, w


def test_two_rounds_strict_preview_full_wire_shared_budget_and_closed_connections(tmp_path):
    report, seen, case, output, w = execute(tmp_path)
    assert report["status"] == "PASS_RESTRICTED_LITERAL_CANDIDATE_PREVIEW"
    assert len(seen) == 2 and report["tool_reads"] == 1 and report["known_tokens"] == 2000
    assert report["source_unchanged"] and report["read_engine_disposed"]
    assert report["read_connections_open"] == 0 and report["retries"] == 0
    assert all(q["kind"] in ("SELECT", "PRAGMA") for q in report["sql"])
    assert report["reserved_envelope"] == sum(x["reserved"] for x in report["slots"]) <= 64000
    assert report["slots"][1]["send_boundary_elapsed"] - report["slots"][0]["finished_elapsed"] >= 60
    assert seen[1]["messages"] == report["feedback"]["messages"]
    assert seen[1]["messages"][-1]["tool_call_id"] == "bound-material-read"
    assert json.loads(seen[1]["messages"][-1]["content"]) == w["context"]["source"]
    assert seen[1]["tools"] == [] and report["preview"]["publishable"] is False
    assert report["preview"]["generation_provenance"] == "NOT_ATTESTED"
    assert report["preview"]["semantic_status"] == "UNKNOWN"
    before = json.loads((output / "result.json").read_text())
    with pytest.raises(FileExistsError):
        runner.run_worker(case, tmp_path / "different-output", environ={"INTERN_API_TOKEN": TOKEN},
                          _transport=httpx.MockTransport(lambda _: pytest.fail("no resend")))
    assert json.loads((output / "result.json").read_text()) == before


@pytest.mark.parametrize("fault", ["direct", "wrong_resource", "wrong_model", "usage", "length",
                                    "output_budget", "reported_budget"])
def test_first_failure_consumes_claim_reservation_and_never_sends_second(tmp_path, fault):
    def change(raw, number, _case, _w, _clock):
        assert number == 1
        if fault == "direct":
            raw["choices"][0].update(message=dict(role="assistant", content="done"), finish_reason="stop")
        elif fault == "wrong_resource":
            raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps(
                {"resource_id": "res_" + "a" * 32})
        elif fault == "wrong_model":
            raw["model"] = "other"
        elif fault == "usage":
            raw.pop("usage")
        elif fault == "length":
            raw["choices"][0]["finish_reason"] = "length"
        elif fault == "output_budget":
            raw["usage"].update(completion_tokens=1025, total_tokens=1125)
        else:
            raw["usage"].update(prompt_tokens=63900, completion_tokens=900, total_tokens=64800)

    report, seen, case, _output, _w = execute(tmp_path, change=change)
    assert len(seen) == 1 and report["status"] == "STOPPED_NO_RETRY" and report["tool_reads"] == 0
    assert report["reserved_envelope"] > 0 and (case / "control/execution-claim.json").exists()
    assert "preview" not in report


@pytest.mark.parametrize("fault", ["length", "missing_field", "wrong_id", "unknown_usage"])
def test_final_failure_never_repairs_completes_or_expands_limit(tmp_path, fault):
    def change(raw, number, _case, _w, _clock):
        if number != 2:
            return
        if fault == "length":
            raw["choices"][0]["finish_reason"] = "length"
        elif fault == "unknown_usage":
            raw.pop("usage")
        else:
            value = json.loads(raw["choices"][0]["message"]["content"])
            if fault == "missing_field":
                value["manifest"].pop("workflow")
            else:
                value["manifest"]["app_id"] = "app_" + "a" * 32
            raw["choices"][0]["message"]["content"] = json.dumps(value)

    report, seen, _case, _output, _w = execute(tmp_path, change=change)
    assert len(seen) == 2 and report["status"] == "STOPPED_NO_RETRY"
    assert report["tool_reads"] == 1 and report["retries"] == 0 and "preview" not in report
    assert all(body["max_tokens"] == 1024 for body in seen)


@pytest.mark.parametrize("escaped", [False, True])
def test_credential_reflection_no_response_hash_or_private_data_saved(tmp_path, escaped):
    def receive(_request, w, _clock):
        raw = response(w, False)
        raw["private_reasoning"] = TOKEN
        body = json.dumps(raw)
        if escaped:
            body = body.replace(TOKEN, "".join("\\u%04x" % ord(x) for x in TOKEN))
        return httpx.Response(200, content=body)

    report, seen, _case, _output, _w = execute(tmp_path, receive=receive)
    assert len(seen) == 1 and report["error_code"] == "CREDENTIAL_REFLECTION"
    assert "response_sha256" not in report["slots"][0] and "feedback" not in report


def test_source_change_stops_at_next_original_boundary(tmp_path):
    def changed(_raw, _number, case, _w, _clock):
        with sqlite3.connect(case / "source/fixture.sqlite") as c:
            c.execute("UPDATE resources SET content='changed'")

    report, seen, _case, _output, _w = execute(tmp_path, change=changed)
    assert len(seen) == 1 and report["error_code"] == "FIXTURE_CHANGED"
    assert report["tool_reads"] == 0 and report["source_unchanged"] is False


def test_fresh_authorization_rejects_even_if_test_refreezes_file_digest(tmp_path):
    def setup(case, w, _clock):
        store = Store("sqlite:///" + str(case / "source/fixture.sqlite"), test_only=True)
        with store.tx() as c:
            c.execute(update(grants).values(revoked=True))
        store.engine.dispose()
        # Test-only adjustment reaches original authorization instead of the earlier drift gate.
        w["inventory"] = runner.files(case / "source")
        runner._save(case / "control/prepared.json", w)

    report, seen, _case, _output, _w = execute(tmp_path, setup=setup)
    assert seen == [] and report["error_code"] == "GRANT_REVOKED"


@pytest.mark.parametrize("fault", ["prompt", "missing_source"])
def test_tampered_prompt_or_missing_frozen_source_rejected_before_send(tmp_path, fault):
    def setup(case, w, _clock):
        if fault == "prompt":
            w["context"]["messages"][1]["content"] = "unapproved"
        else:
            w["sources"].pop("src/sim2act/agent_apps.py")
        runner._save(case / "control/prepared.json", w)

    report, seen, _case, _output, _w = execute(tmp_path, setup=setup)
    assert seen == [] and report["status"] == "STOPPED_NO_RETRY"


def test_actual_wire_tamper_rejected_before_transport(tmp_path, monkeypatch):
    original = runner.InternModel.request_serialized_captured

    def tampered(self, body, guard):
        value = json.loads(body)
        value["max_tokens"] = 1025
        return original(self, json.dumps(value).encode(), guard)

    monkeypatch.setattr(runner.InternModel, "request_serialized_captured", tampered)
    report, seen, _case, _output, _w = execute(tmp_path)
    assert seen == [] and report["status"] == "STOPPED_NO_RETRY"
    assert report["reserved_envelope"] > 0 and len(report["slots"]) == 1


def test_second_wire_over_limit_is_not_truncated_or_sent(tmp_path):
    def change(raw, _number, _case, _w, _clock):
        raw["choices"][0]["message"]["content"] = "x" * 17000

    report, seen, _case, _output, _w = execute(tmp_path, change=change)
    assert len(seen) == 1 and report["tool_reads"] == 1
    assert report["error_code"] == "BUDGET_EXHAUSTED" and len(report["slots"]) == 1


def test_second_deadline_clipped_to_whole_window_and_gap_after_response(tmp_path, monkeypatch):
    clock_ref = []
    original = runner.candidate.read_feedback

    def feedback(*args, **kwargs):
        clock_ref[0].offset += 100
        return original(*args, **kwargs)

    monkeypatch.setattr(runner.candidate, "read_feedback", feedback)

    def change(_raw, number, _case, _w, clock):
        clock_ref[:] = [clock]
        if number == 1:
            clock.offset += 110

    report, seen, _case, _output, _w = execute(tmp_path, change=change)
    assert report["status"] == "PASS_RESTRICTED_LITERAL_CANDIDATE_PREVIEW" and len(seen) == 2
    second = report["slots"][1]
    assert second["request_deadline"] == report["deadline"]
    assert second["request_deadline"] - second["send_boundary_at"] == 90


def test_whole_deadline_stops_before_second_send(tmp_path):
    def change(_raw, _number, _case, _w, clock):
        clock.offset += 301

    report, seen, _case, _output, _w = execute(tmp_path, change=change)
    assert len(seen) == 1 and report["error_code"] == "DIAGNOSTIC_DEADLINE"
    assert report["within_work_window"] is False


def test_upstream_access_refusal_no_retry_or_fallback(tmp_path):
    report, seen, _case, _output, _w = execute(tmp_path,
        receive=lambda *_: httpx.Response(403, content="denied"))
    assert len(seen) == 1 and report["slots"][0]["http_status"] == 403
    assert report["status"] == "STOPPED_NO_RETRY" and "feedback" not in report
    assert report["usage_status"] == "unknown"


def test_database_readonly_authorizer_and_complete_inventory(tmp_path):
    case = tmp_path / "case"
    w = runner.prepare(case)
    facts = runner.ReadFacts(case, w, [])
    try:
        with facts.connection() as c:
            for sql in ("UPDATE resources SET content='bad'", "PRAGMA query_only=OFF",
                        "ATTACH DATABASE ':memory:' AS other"):
                with pytest.raises(runner.DomainError):
                    c.exec_driver_sql(sql)
                with pytest.raises(sqlite3.DatabaseError):
                    c.connection.driver_connection.execute(sql)
        assert facts.active == 0 and runner.files(case / "source") == w["inventory"]
    finally:
        facts.store.engine.dispose()


@pytest.mark.parametrize("mode", ["exit", "cooperative", "ignore"])
def test_supervisor_only_owned_child_normal_termination_or_forced_cleanup(tmp_path, mode):
    # No API, model or database. Real OS child verifies independent supervision.
    if mode == "exit":
        code = "raise SystemExit(0)"
        work = 1
    else:
        code = "import time; time.sleep(10)"
        if mode == "ignore":
            code = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)"
        work = .2
    record = runner.supervise([sys.executable, "-c", code], tmp_path / mode,
                               _work=work, _grace=.5)
    assert record["child_stopped"] and record["within_total_window"]
    assert record["terminated"] == (mode != "exit")
    assert record["forced_kill"] == (mode == "ignore")
    assert (record["child_exit"] == 0) == (mode == "exit")


def test_unsupervised_real_entry_and_direct_worker_cli_rejected_before_claim_or_credential(tmp_path):
    class NoCredentialAccess(dict):
        def get(self, *_):
            pytest.fail("must reject before reading credentials")

    case, output = tmp_path / "case", tmp_path / "output"
    with pytest.raises(runner.DomainError) as error:
        runner.run_worker(case, output, environ=NoCredentialAccess())
    assert error.value.code == "SUPERVISOR_REQUIRED" and not case.exists() and not output.exists()
    child = subprocess.run([sys.executable, str(FILE), "_worker", "--case", str(case),
        "--output", str(output), "--execute-user-confirmed-pa"],
        capture_output=True, timeout=10, env={**os.environ, "INTERN_API_TOKEN": TOKEN})
    assert child.returncode != 0 and b"SUPERVISOR_REQUIRED" in child.stderr
    assert TOKEN.encode() not in child.stderr and not case.exists() and not output.exists()


def test_supervised_inherited_pipe_capability_and_parent_binding(tmp_path):
    case, output = tmp_path / "case", tmp_path / "output"
    code = (
        "import importlib.util,sys; from pathlib import Path; "
        f"s=importlib.util.spec_from_file_location('runner',{str(FILE)!r}); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        f"c=m.ParentChannel(int(sys.argv[-1]),Path({str(case)!r}),Path({str(output)!r})); "
        "c.current()")
    record = runner.supervise([sys.executable, "-c", code], output, _case=case, _work=5, _grace=1)
    assert record["child_exit"] == 0 and record["child_stopped"] and not record["interrupted"]
    assert not record["terminated"] and not record["cleanup_error"]


def test_supervisor_keyboard_interrupt_still_stops_and_reaps_owned_child(tmp_path):
    def interrupted(_seconds):
        raise KeyboardInterrupt()

    record = runner.supervise([sys.executable, "-c", "import time; time.sleep(10)"],
                               tmp_path / "output", _work=1, _grace=.5, _poll_sleep=interrupted)
    assert record["interrupted"] == "KeyboardInterrupt"
    assert record["child_stopped"] and record["terminated"] and not record["cleanup_error"]


def test_case_output_overlap_rejected_before_supervisor_can_write(tmp_path):
    case = tmp_path / "case"
    child = subprocess.run([sys.executable, str(FILE), "run", "--case", str(case),
        "--output", str(case / "source"), "--execute-user-confirmed-pa"],
        capture_output=True, timeout=10)
    assert child.returncode != 0 and b"OUTPUT_MUST_BE_SEPARATE" in child.stderr
    assert not case.exists()


def test_concurrent_claim_has_only_one_winner(tmp_path):
    case = tmp_path / "case"
    (case / "control").mkdir(parents=True)

    def claim(_index):
        try:
            runner.claim_once(case, b"synthetic", time.time())
            return "consumed"
        except FileExistsError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, [0, 1]))
    assert sorted(results) == ["consumed", "rejected"]


def test_sigterm_supervisor_cleans_its_actual_owned_child(tmp_path):
    marker, output = tmp_path / "child-started", tmp_path / "output"
    owned_code = f"from pathlib import Path; import time; Path({str(marker)!r}).touch(); time.sleep(10)"
    code = (
        "import importlib.util,sys; from pathlib import Path; "
        f"s=importlib.util.spec_from_file_location('runner',{str(FILE)!r}); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        f"m.supervise([sys.executable,'-c',{owned_code!r}],Path({str(output)!r}),_work=5,_grace=.5)")
    parent = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 4
        while not marker.exists() and parent.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        assert marker.exists()
        os.kill(parent.pid, signal.SIGTERM)
        parent.wait(timeout=2)
        record = json.loads((output / "supervisor.json").read_text())
        assert record["interrupted"] == "SupervisorStop"
        assert record["child_stopped"] and record["terminated"] and not record["cleanup_error"]
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=1)


def test_actual_cli_supervised_worker_reaches_missing_credential_gate_with_zero_http(tmp_path):
    case, output = tmp_path / "case", tmp_path / "output"
    runner.prepare(case)
    env = {**os.environ, "SIM2ACT_MODEL": "intern-s2", "SIM2ACT_INTERN_TOKEN": "",
           "INTERN_API_TOKEN": ""}
    result = subprocess.run([sys.executable, str(FILE), "run", "--case", str(case),
        "--output", str(output), "--execute-user-confirmed-pa"],
        capture_output=True, timeout=10, env=env)
    assert result.returncode == 1
    record = json.loads((output / "supervisor.json").read_text())
    report = json.loads((output / "result.json").read_text())
    assert record["child_stopped"] and record["child_exit"] == 1
    assert not record["terminated"] and not record["interrupted"] and not record["cleanup_error"]
    assert report["error_code"] == "CREDENTIAL_NOT_CONFIGURED" and report["slots"] == []
    assert report["started_at"] == record["started_at"]
    assert report["deadline"] == record["started_at"] + 300
    assert (case / "control/execution-claim.json").exists()
