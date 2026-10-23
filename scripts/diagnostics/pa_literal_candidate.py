"""Bounded, standalone literal-list generation; never production P-A authority.

prepare creates only owned synthetic facts. run supervises one claimed worker.
No LIVE invocation is implied by installing/preparing this opt-in diagnostic.
"""

import argparse
import hashlib
import json
import math
import os
import select as io_select
import signal
import sqlite3
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
from sqlalchemy import event, insert, select

from sim2act import goal_applications as generation
from sim2act import pa_candidate_preview as candidate
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store, meta, new_id, principals, resources
from sim2act.errors import DomainError
from sim2act.goals import create_card
from sim2act.model import (
    InternModel,
    normalize_usage,
    parse_response,
    require_returned_model,
    returned_model_identity,
)
from sim2act.model_budget import _save

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/evidence/pa-literal-candidate-contract-20261023"
ENDPOINT = "https://chat.intern-ai.org.cn/api/v1/chat/completions"
CAP = Limits(max_requests=2, max_tools=1, max_repairs=0, max_output_tokens=1024,
             max_total_tokens=64000, run_seconds=300)
ROWS = dict(principals=2, projects=1, resources=1, grants=2, quotas=1,
            goal_cards=1, goal_card_versions=1)
SOURCES = ["scripts/diagnostics/pa_literal_candidate.py", *[
    "src/sim2act/" + name + ".py" for name in (
        "pa_candidate_preview", "goal_applications", "model", "model_budget", "contracts",
        "config", "db", "goals", "tools", "apps", "text_apps", "agent_apps")]]
ASSETS = ["contract.json", "material.txt", "goal.json", "oracle-not-for-provider.json"]


def require(ok, code="PA_BOUNDARY_REJECTED"):
    if not ok:
        raise DomainError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def files(source):
    return {name: digest((source / name).read_bytes()) if (source / name).exists() else None
            for name in ("fixture.sqlite", "fixture.sqlite-wal", "fixture.sqlite-shm",
                         "fixture.sqlite-journal")}


def vector(c):
    return {name: dict(rows=len(rows), sha256=digest(json.dumps(rows).encode()))
            for name, table in sorted(meta.tables.items())
            for rows in [sorted(json.dumps(dict(row), sort_keys=True, separators=(",", ":"))
                                for row in c.execute(select(table)).mappings())]}


def no_secret(body, value, token):
    require(token.encode() not in body, "CREDENTIAL_REFLECTION")
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is str:
            require(token not in item, "CREDENTIAL_REFLECTION")
        elif type(item) is dict:
            pending.extend(item.keys())
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)


def prepare(case):
    """No network/credential lookup. New isolated SQLite and one full saved Goal."""
    case.mkdir(parents=True, exist_ok=False)
    source, control = case / "source", case / "control"
    source.mkdir()
    control.mkdir()
    contract = json.loads((DESIGN / "contract.json").read_text())
    material = (DESIGN / "material.txt").read_bytes()
    require(digest(material) == contract["material_sha256"] and len(material) == 83)
    store = Store("sqlite:///" + str(source / "fixture.sqlite"), test_only=True)
    try:
        store.initialize(quota_subject="synthetic-pa-not-provider-quota")
        user = new_id("user")
        with store.tx() as c:
            c.execute(insert(principals).values(id=user, name="synthetic P-A owner"))
        pid = store.project(user, "synthetic literal candidate")
        rid = new_id("res")
        with store.tx() as c:
            runtime = store.own_project(c, user, pid)["runtime_id"]
            c.execute(insert(resources).values(id=rid, project_id=pid, name="notes.txt",
                format="txt", content=material.decode(), hash=digest(material)))
            store.add_grants(c, user, runtime, pid, rid, ["resource.read"])
        goal = json.loads((DESIGN / "goal.json").read_text())
        require(goal["resource_refs"] == ["FROZEN_RESOURCE_ID"])
        goal["resource_refs"] = [rid]
        card = create_card(store, user, pid, goal)
        request = dict(expected_version=card["version"], expected_fingerprint=card["fingerprint"],
                       request_key="pa-literal-candidate-single-window")
        with store.engine.connect() as c:
            context = candidate.prepare(store, c, user, card["id"], request, CAP)
            tables = vector(c)
            require(all(item["rows"] == ROWS.get(name, 0) for name, item in tables.items()))
            c.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        store.engine.dispose()
    require(all(value is None for name, value in files(source).items() if name != "fixture.sqlite"))
    body = generation.body(context["messages"], generation.READ_TOOLS, 1024)
    require(len(body) <= 32768 and len(body) + 1024 <= 64000, "BUDGET_EXHAUSTED")
    witness = dict(version="PA_LITERAL_PREPARED_V1", context=context, tables=tables,
        inventory=files(source), first_body_sha256=digest(body), first_body_bytes=len(body),
        sources={f: digest((ROOT / f).read_bytes()) for f in SOURCES},
        assets={f: digest((DESIGN / f).read_bytes()) for f in ASSETS},
        output_fit="UNPROVEN_NO_PROVIDER_TOKENIZER_OR_REAL_COMPLETE_CANDIDATE")
    _save(control / "prepared.json", witness)
    return witness


class ReadFacts:
    def __init__(self, case, witness, sql):
        self.source, self.witness, self.active = case / "source", witness, 0
        require(set(witness["sources"]) == set(SOURCES) and set(witness["assets"]) == set(ASSETS))
        self.store = Store("sqlite:///file:" + str(self.source / "fixture.sqlite")
                           + "?mode=ro&uri=true", test_only=True)

        def connected(dbapi, _record):
            dbapi.execute("PRAGMA query_only=ON")

            def authorize(action, arg1, arg2, _db, _trigger):
                if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
                              sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_PRAGMA and arg2 is None and arg1 in (
                        "query_only", "read_uncommitted"):
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY

            dbapi.set_authorizer(authorize)

        def statement(_c, _cursor, text, _params, _ctx, _many):
            kind = text.strip().split()[0].upper()
            require(kind == "SELECT" or text.strip().upper() == "PRAGMA QUERY_ONLY")
            sql.append(dict(kind=kind, sha256=digest(text.encode())))

        event.listen(self.store.engine, "connect", connected)
        event.listen(self.store.engine, "before_cursor_execute", statement)

    def check_files(self):
        require(files(self.source) == self.witness["inventory"], "FIXTURE_CHANGED")
        require(all(digest((ROOT / f).read_bytes()) == sha
                    for f, sha in self.witness["sources"].items()), "SOFTWARE_CHANGED")
        require(all(digest((DESIGN / f).read_bytes()) == sha
                    for f, sha in self.witness["assets"].items()), "CONTRACT_CHANGED")

    @contextmanager
    def connection(self):
        self.check_files()
        try:
            with self.store.engine.connect() as c:
                self.active += 1
                require(c.exec_driver_sql("PRAGMA query_only").scalar_one() == 1)
                yield c
        finally:
            self.active = 0
        require(c.closed, "CONNECTION_STILL_OPEN")
        self.check_files()

    def current(self):
        context = self.witness["context"]
        with self.connection() as c:
            candidate._current(self.store, c, context["user"], context)
        require(self.active == 0, "CONNECTION_STILL_OPEN")


def claim_once(case, prepared, wall):
    # One fixture-wide claim, regardless of output directory. Never resumed/released.
    claim = case / "control/execution-claim.json"
    with claim.open("x") as stream:
        json.dump(dict(status="CONSUMED_NO_RETRY", prepared_sha256=digest(prepared),
                       started_at=wall, deadline=wall + 300), stream)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(claim.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class ParentChannel:
    """An inherited pipe capability from the currently supervising owned parent.

    Operator replacement of program/files is outside this standalone diagnostic's
    authority. An env flag or direct CLI action cannot substitute for the pipe.
    """
    def __init__(self, fd, case, output):
        require(type(fd) is int and fd >= 0, "SUPERVISOR_REQUIRED")
        require(stat.S_ISFIFO(os.fstat(fd).st_mode), "SUPERVISOR_REQUIRED")
        data = bytearray()
        deadline = time.monotonic() + 1
        while len(data) <= 4096:
            left = deadline - time.monotonic()
            require(left > 0 and io_select.select([fd], [], [], left)[0], "SUPERVISOR_REQUIRED")
            value = os.read(fd, 1)
            require(value, "SUPERVISOR_REQUIRED")
            if value == b"\n":
                break
            data.extend(value)
        require(len(data) <= 4096, "SUPERVISOR_REQUIRED")
        value = json.loads(data)
        require(set(value) == {"parent_pid", "case", "output", "script_sha256", "nonce",
                               "started_wall", "started_monotonic"}
                and value["parent_pid"] == os.getppid() > 1
                and value["case"] == str(case) and value["output"] == str(output)
                and value["script_sha256"] == digest(Path(__file__).read_bytes())
                and type(value["nonce"]) is str and len(value["nonce"]) == 64,
                "SUPERVISOR_REQUIRED")
        require(all(type(value[k]) in (int, float) and math.isfinite(value[k])
                    for k in ("started_wall", "started_monotonic")), "SUPERVISOR_REQUIRED")
        self.fd, self.parent_pid = fd, value["parent_pid"]
        self.started_wall, self.started_monotonic = value["started_wall"], value["started_monotonic"]
        self.current()

    def current(self):
        require(os.getppid() == self.parent_pid, "SUPERVISOR_LOST")
        # Parent holds the write end throughout supervision. EOF means it closed/died.
        require(not io_select.select([self.fd], [], [], 0)[0], "SUPERVISOR_LOST")
        require(0 <= time.monotonic() - self.started_monotonic < 300
                and time.time() < self.started_wall + 300, "DIAGNOSTIC_DEADLINE")


def run_worker(case, output, *, environ=None, _transport=None, _wall=time.time,
               _monotonic=time.monotonic, _sleep=time.sleep, _parent_channel=None):
    """Cooperative worker; the CLI adds an independent OS-process 300+10 supervisor.

    Underscored injectable IO/clocks are for Mock tests only, never CLI options.
    """
    require(_transport is None or isinstance(_transport, httpx.MockTransport))
    if _transport is None:
        require(type(_parent_channel) is ParentChannel, "SUPERVISOR_REQUIRED")
        _parent_channel.current()
    require(not output.is_relative_to(case) and not case.is_relative_to(output),
            "OUTPUT_MUST_BE_SEPARATE")
    env = os.environ if environ is None else environ
    start, wall = _monotonic(), _wall()
    if _transport is None:
        # Imports and worker startup consume the parent's original 300s window.
        start, wall = _parent_channel.started_monotonic, _parent_channel.started_wall
    prepared = (case / "control/prepared.json").read_bytes()
    claim_once(case, prepared, wall)
    output.mkdir(parents=True, exist_ok=False)
    path = output / "result.json"
    report = dict(classification="RESTRICTED_LITERAL_LIST_CANDIDATE_DIAGNOSTIC",
        fee_basis="USER_CONFIRMED_NO_COST_NOT_OFFICIAL_VERIFICATION",
        production_authority=False, provenance="NOT_ATTESTED", publishable=False,
        started_at=wall, deadline=wall + 300, status="PREPARED", slots=[], retries=0,
        reserved_envelope=0, known_tokens=0, usage_status="NOT_STARTED", tool_reads=0,
        sql=[], output_fit="UNPROVEN", semantic_status="UNKNOWN", goal_acceptance="NOT_RUN")
    _save(path, report)
    facts = None
    try:
        require(env.get("SIM2ACT_MODEL", "intern-s2") == "intern-s2", "CONFIGURATION_MISMATCH")
        token = env.get("SIM2ACT_INTERN_TOKEN", "") or env.get("INTERN_API_TOKEN", "")
        require(type(token) is str and bool(token), "CREDENTIAL_NOT_CONFIGURED")
        w = json.loads(prepared)
        require(w["version"] == "PA_LITERAL_PREPARED_V1")
        # Never persist a supplied prepared context containing reflected credentials.
        no_secret(prepared, w, token)
        facts = ReadFacts(case, w, report["sql"])
        context = w["context"]
        require(context["limits"] == CAP.model_dump())
        facts.current()
        with facts.connection() as c:
            require(vector(c) == w["tables"] and all(
                x["rows"] == ROWS.get(n, 0) for n, x in w["tables"].items()), "FIXTURE_CHANGED")
        first = generation.body(context["messages"], generation.READ_TOOLS, 1024)
        require(len(first) == w["first_body_bytes"] and digest(first) == w["first_body_sha256"])
        settings = Settings("unused-no-business-db", output, mode="live", live_enabled=True,
            token=token, model="intern-s2", max_requests=2, max_repairs=0, max_tools=1,
            max_output_tokens=1024, max_total_tokens=64000, run_seconds=300)
        model = InternModel(settings, _transport)

        def remaining():
            if _transport is None:
                _parent_channel.current()
            left = min(300 - (_monotonic() - start), wall + 300 - _wall())
            require(left > 0, "DIAGNOSTIC_DEADLINE")
            return left

        def call(body):
            remaining()
            facts.current()
            no_secret(body, json.loads(body), token)
            reserve = len(body) + 1024
            require(len(report["slots"]) < 2 and len(body) <= 32768
                    and report["reserved_envelope"] + reserve <= 64000
                    and report["known_tokens"] + reserve <= 64000, "BUDGET_EXHAUSTED")
            slot = dict(status="STARTED_OUTCOME_UNKNOWN", reserved=reserve, body_bytes=len(body),
                request_sha256=digest(body), request=json.loads(body), guard_entries=0,
                reserved_at=_wall(), reserved_elapsed=_monotonic() - start)
            report["slots"].append(slot)
            report["reserved_envelope"] += reserve
            _save(path, report)  # Never refund; crashes consume claim and reservation.
            call_deadline = _wall() + min(120, remaining())

            def guard(request):
                remaining()
                facts.current()  # Original authorization; connection closed before HTTP.
                slot["guard_entries"] += 1
                require(slot["guard_entries"] == 1 and request.method == "POST"
                        and str(request.url) == ENDPOINT == InternModel.ENDPOINT
                        and request.content == body
                        and request.headers.get("authorization") == "Bearer " + token)
                require(facts.active == 0, "CONNECTION_STILL_OPEN")
                require(_wall() < call_deadline, "DIAGNOSTIC_DEADLINE")
                slot.update(send_boundary_at=_wall(), send_boundary_elapsed=_monotonic() - start,
                            request_deadline=call_deadline, read_connections_open=0)
                _save(path, report)
                return {"deadline": call_deadline}

            received = model.request_serialized_captured(body, guard)
            slot["http_status"] = 200
            no_secret(received.body, received.parsed, token)
            raw = received.parsed
            require(type(raw) is dict, "MODEL_OUTPUT_INVALID")
            usage = normalize_usage(raw)
            slot["usage"] = usage
            report["usage_status"] = usage["status"]
            if usage["status"] == "known":
                report["known_tokens"] += usage["tokens"]["total_tokens"]
            identity = returned_model_identity("intern-s2", raw.get("model"))
            require_returned_model(identity)
            require(usage["status"] == "known", "USAGE_UNKNOWN")
            require(usage["tokens"]["completion_tokens"] <= 1024
                    and usage["tokens"]["total_tokens"] <= reserve
                    and report["known_tokens"] <= 64000, "BUDGET_EXHAUSTED")
            parse_response(raw)
            require(_wall() < call_deadline, "DIAGNOSTIC_DEADLINE")
            slot.update(response_sha256=digest(received.body), response_bytes=len(received.body),
                identity=identity, finished_at=_wall(), finished_elapsed=_monotonic() - start,
                status="RECEIVED_DATA_CHECKED")
            remaining()
            facts.current()
            _save(path, report)
            return raw

        raw = call(first)
        with facts.connection() as c:
            feedback = candidate.read_feedback(facts.store, c, context["user"], context, raw)
        report["tool_reads"] = 1
        no_secret(b"", feedback, token)
        report["feedback"] = feedback
        _save(path, report)
        # Actual completed-response monotonic timestamp, not reservation time.
        previous = report["slots"][0]["finished_elapsed"]
        while _monotonic() - start - previous < 60:
            remaining()
            _sleep(min(1, 60 - (_monotonic() - start - previous)))
        remaining()
        require(_monotonic() - start - previous >= 60, "RATE_LIMITED")
        raw = call(generation.body(feedback["messages"], [], 1024))
        oracle = json.loads((DESIGN / "oracle-not-for-provider.json").read_text())
        with facts.connection() as c:
            result = candidate.preview(facts.store, c, context["user"], context, raw,
                sample_inputs=[item["input"] for item in oracle["cases"]])
        no_secret(b"", result, token)
        for sample, expected in zip(result["samples"], oracle["cases"], strict=True):
            citations = sample["result"]["citations"]
            require([x["start_line"] for x in citations] == expected["line_numbers"]
                    and [x["quote"] for x in citations] == expected["quotes"]
                    and all(x["start_line"] == x["end_line"] for x in citations),
                    "LITERAL_ORACLE_REJECTED")
        facts.current()
        with facts.connection() as c:
            require(vector(c) == w["tables"], "FIXTURE_CHANGED")
        remaining()
        report.update(status="PASS_RESTRICTED_LITERAL_CANDIDATE_PREVIEW", preview=result)
    except DomainError as error:
        report.update(status="STOPPED_NO_RETRY", error_code=error.code)
        if report["slots"]:
            slot = report["slots"][-1]
            code = getattr(error, "_received_status_code", None)
            if type(code) is int:
                slot["http_status"] = code
            body = getattr(error, "_received_body", None)
            if type(body) is bytes:
                # Error/partial/truncated body never persisted or hashed.
                slot["error_body_bytes"] = len(body)
    except Exception as error:
        report.update(status="UNKNOWN_INTERNAL_FAILURE", error_type=type(error).__name__)
    finally:
        cleaning = _monotonic()
        if any("usage" not in slot or slot["usage"]["status"] != "known" for slot in report["slots"]):
            report["usage_status"] = "unknown"
        report["known_tokens_basis"] = "SUM_COMPLETE_REPORTS_NOT_UNKNOWN_AS_ZERO"
        if facts is not None:
            try:
                facts.store.engine.dispose()
                report.update(read_engine_disposed=True, read_connections_open=facts.active,
                    source_unchanged=files(facts.source) == facts.witness["inventory"])
            except Exception as error:
                report["cleanup_error_type"] = type(error).__name__
        report["cleanup_seconds"] = _monotonic() - cleaning
        report["elapsed_seconds"] = _monotonic() - start
        report["within_work_window"] = report["elapsed_seconds"] <= 300
        report["cleanup_within_10_seconds"] = report["cleanup_seconds"] <= 10
        if report["status"] == "PASS_RESTRICTED_LITERAL_CANDIDATE_PREVIEW" and not (
                report.get("read_engine_disposed") and report.get("read_connections_open") == 0
                and report.get("source_unchanged") and report["within_work_window"]
                and report["cleanup_within_10_seconds"]):
            report["status"] = "UNKNOWN_CLEANUP_OR_DEADLINE"
        _save(path, report)
    return report


class SupervisorStop(BaseException):
    pass


def supervise(argv, output, *, _work=300, _grace=10, _case=None, _poll_sleep=time.sleep):
    """Fixed CLI defaults; only the newly created child is signalled, no process search."""
    start, wall_start = time.monotonic(), time.time()
    child = None
    read_fd = write_fd = None
    interrupted = cleanup_error = None
    terminated = killed = False
    previous = signal.getsignal(signal.SIGTERM)
    previous_int = signal.getsignal(signal.SIGINT)

    def stop(_signum, _frame):
        raise SupervisorStop()

    signal.signal(signal.SIGTERM, stop)
    try:
        options = {}
        if _case is not None:
            read_fd, write_fd = os.pipe()
            options["pass_fds"] = (read_fd,)
            argv = [*argv, "--parent-channel", str(read_fd)]
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, **options)
        if read_fd is not None:
            os.close(read_fd)
            read_fd = None
            message = dict(parent_pid=os.getpid(), case=str(_case), output=str(output),
                script_sha256=digest(Path(__file__).read_bytes()), nonce=os.urandom(32).hex(),
                started_wall=wall_start, started_monotonic=start)
            os.write(write_fd, json.dumps(message).encode() + b"\n")
        while child.poll() is None and time.monotonic() - start < _work:
            _poll_sleep(.02)
    except BaseException as error:
        interrupted = type(error).__name__
    finally:
        # Further TERM cannot interrupt the bounded cleanup of this one owned child.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            if child is not None and child.poll() is None:
                terminated = True
                child.terminate()
                grace = max(0, min(_grace, start + _work + _grace - time.monotonic()))
                try:
                    child.wait(timeout=max(0, grace - .1))
                except subprocess.TimeoutExpired:
                    killed = True
                    child.kill()
                    child.wait(timeout=max(0, min(.1, start + _work + _grace - time.monotonic())))
        except BaseException as error:
            cleanup_error = type(error).__name__
        finally:
            for fd in (read_fd, write_fd):
                if fd is not None:
                    os.close(fd)
            signal.signal(signal.SIGTERM, previous)
            signal.signal(signal.SIGINT, previous_int)
    record = dict(work_seconds=_work, cleanup_seconds=_grace, started_at=wall_start,
        child_pid=child.pid if child is not None else None,
        child_exit=child.returncode if child is not None else None,
        child_stopped=child is not None and child.returncode is not None,
        terminated=terminated, forced_kill=killed, interrupted=interrupted,
        cleanup_error=cleanup_error, elapsed_seconds=time.monotonic() - start)
    record["within_total_window"] = record["elapsed_seconds"] <= _work + _grace
    output.mkdir(parents=True, exist_ok=True)
    _save(output / "supervisor.json", record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "_worker"))
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute-user-confirmed-pa", action="store_true")
    parser.add_argument("--parent-channel", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    case = args.case.resolve()
    if args.action == "prepare":
        w = prepare(case)
        print(json.dumps(dict(status="PREPARED_NO_HTTP", first_body_bytes=w["first_body_bytes"],
                              output_fit=w["output_fit"])))
        return 0
    if not args.execute_user_confirmed_pa or args.output is None:
        parser.error("new bounded execution decision and a new output directory required")
    output = args.output.resolve()
    require(not output.is_relative_to(case) and not case.is_relative_to(output),
            "OUTPUT_MUST_BE_SEPARATE")
    if args.action == "run":
        require(not output.exists(), "OUTPUT_ALREADY_EXISTS")
        # Preserve the active venv interpreter spelling; resolving its symlink can
        # select the base interpreter and silently lose installed dependencies.
        record = supervise([os.path.abspath(sys.executable), str(Path(__file__).resolve()),
            "_worker", "--case", str(case), "--output", str(output),
            "--execute-user-confirmed-pa"], output, _case=case)
        result = json.loads((output / "result.json").read_text()) if (
            output / "result.json").exists() else {}
        ok = (record["child_stopped"] and record["child_exit"] == 0
              and not record["terminated"] and not record["interrupted"]
              and not record["cleanup_error"] and record["within_total_window"]
              and result.get("status") == "PASS_RESTRICTED_LITERAL_CANDIDATE_PREVIEW")
        print(json.dumps(dict(status=result.get("status", "UNKNOWN_NO_RESULT") if ok
                              else "UNKNOWN_OR_FAILED_SUPERVISED_EXECUTION",
                              supervised_success=ok)))
        return 0 if ok else 1

    channel = ParentChannel(args.parent_channel, case, output)

    def stop(_signum, _frame):
        raise DomainError("SUPERVISOR_WORK_WINDOW_STOPPED")

    signal.signal(signal.SIGTERM, stop)
    report = run_worker(case, output, _parent_channel=channel)
    return 0 if report["status"] == "PASS_RESTRICTED_LITERAL_CANDIDATE_PREVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
