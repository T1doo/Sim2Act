"""Bounded standalone AT02 gateway diagnostic; no Run or production source authority.

prepare creates ONLY owned synthetic test data. run claims that fixture once,
opens its source read-only, and uses the original gateway and Intern adapter.
"""

import argparse
import hashlib
import json
import os
import signal
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
from sqlalchemy import event, insert, select

from sim2act.config import Settings
from sim2act.db import Store, meta, new_id, principals, resources
from sim2act.errors import DomainError
from sim2act.model import (
    InternModel,
    normalize_usage,
    parse_response,
    require_returned_model,
    returned_model_identity,
)
from sim2act.model_budget import _save
from sim2act.tools import authorized_read, definitions, validate_call

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/evidence/at02-readonly-feedback-design-20261023"
SOURCE_FILES = ["src/sim2act/model.py", "src/sim2act/tools.py", "src/sim2act/db.py",
                "src/sim2act/config.py", "src/sim2act/contracts.py",
                "src/sim2act/production_evidence.py",
                "scripts/diagnostics/at02_readonly_feedback.py"]
EXPECTED_ROWS = {"principals": 2, "projects": 1, "resources": 1, "grants": 2, "quotas": 1}
ENDPOINT = "https://chat.intern-ai.org.cn/api/v1/chat/completions"


def require(ok, code="DIAGNOSTIC_BOUNDARY_REJECTED"):
    if not ok:
        raise DomainError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(source):
    return {name: digest((source / name).read_bytes()) if (source / name).exists() else None
            for name in ("fixture.sqlite", "fixture.sqlite-wal", "fixture.sqlite-shm",
                         "fixture.sqlite-journal", "material.txt")}


def vector(c):
    result = {}
    for name, table in sorted(meta.tables.items()):
        rows = sorted(json.dumps(dict(row), sort_keys=True, separators=(",", ":"))
                      for row in c.execute(select(table)).mappings())
        result[name] = dict(rows=len(rows), sha256=digest(json.dumps(rows).encode()))
    return result


def prepare(case):
    case.mkdir(parents=True, exist_ok=False)
    source = case / "source"
    source.mkdir()
    (case / "control").mkdir()
    material = (DESIGN / "material.txt").read_bytes()
    design = json.loads((DESIGN / "contract.json").read_text())
    require(digest(material) == design["material"]["sha256"])
    (source / "material.txt").write_bytes(material)
    store = Store("sqlite:///" + str(source / "fixture.sqlite"), test_only=True)
    try:
        store.initialize(quota_subject="synthetic-at02-not-provider-quota")
        user = new_id("user")
        with store.tx() as c:
            c.execute(insert(principals).values(id=user, name="synthetic read diagnostic"))
        project = store.project(user, "synthetic read-only diagnostic")
        rid = new_id("res")
        with store.tx() as c:
            runtime = store.own_project(c, user, project)["runtime_id"]
            c.execute(insert(resources).values(id=rid, project_id=project, name="synthetic.txt",
                format="txt", content=material.decode(), hash=digest(material)))
            store.add_grants(c, user, runtime, project, rid, ["resource.read"])
        with store.engine.connect() as c:
            tables = vector(c)
            require(all(item["rows"] == EXPECTED_ROWS.get(name, 0)
                        for name, item in tables.items()))
            c.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        store.engine.dispose()
    require(all(not (source / name).exists() for name in
                ("fixture.sqlite-wal", "fixture.sqlite-shm", "fixture.sqlite-journal")))
    schema = [tool for tool in definitions() if tool["function"]["name"] == "resource.read"]
    require(schema == json.loads((DESIGN / "tool-schema.json").read_text()))
    messages = json.loads(json.dumps(design["first_messages_template"]))
    messages[1]["content"] = messages[1]["content"].replace("{FROZEN_RESOURCE_ID}", rid)
    first = wire(messages, schema)
    require(len(first) <= 1988)
    witness = dict(version="AT02_READONLY_PREPARED_V1", user=user, runtime=runtime,
        project=project, resource_id=rid, inventory=inventory(source), tables=tables,
        schema=schema, first_messages=messages, first_body_sha256=digest(first),
        first_body_bytes=len(first), source_sha256={f: digest((ROOT / f).read_bytes())
            for f in SOURCE_FILES}, design_sha256=digest((DESIGN / "contract.json").read_bytes()))
    _save(case / "control/prepared.json", witness)
    return witness


def wire(messages, tools):
    return httpx.Request("POST", ENDPOINT, json=dict(model="intern-s2", messages=messages,
                        tools=tools, stream=False, max_tokens=512)).content


class ReadSource:
    def __init__(self, case, witness, sql):
        self.source, self.witness, self.sql = case / "source", witness, sql
        require(set(witness["source_sha256"]) == set(SOURCE_FILES))
        # uri=true is required by SQLAlchemy to pass mode=ro to sqlite itself.
        url = "sqlite:///file:" + str(self.source / "fixture.sqlite") + "?mode=ro&uri=true"
        self.store = Store(url, test_only=True)

        def connect(dbapi, _record):
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

        event.listen(self.store.engine, "connect", connect)
        event.listen(self.store.engine, "before_cursor_execute", statement)

    def check_files(self):
        require(inventory(self.source) == self.witness["inventory"], "FIXTURE_CHANGED")
        require(all(digest((ROOT / f).read_bytes()) == sha
                    for f, sha in self.witness["source_sha256"].items()), "SOFTWARE_CHANGED")
        require(digest((DESIGN / "contract.json").read_bytes()) == self.witness["design_sha256"])

    @contextmanager
    def connection(self):
        self.check_files()
        w = self.witness
        with self.store.engine.connect() as c:
            require(c.exec_driver_sql("PRAGMA query_only").scalar_one() == 1)
            p = self.store.own_project(c, w["user"], w["project"])
            require(p["runtime_id"] == w["runtime"], "RUNTIME_MISMATCH")
            self.store.authorize(c, w["user"], w["runtime"], w["project"],
                                 w["resource_id"], "resource.read")
            yield c
        self.check_files()

    def check(self):
        with self.connection():
            pass

    def read(self):
        w = self.witness
        with self.connection() as c:
            value = authorized_read(self.store, c, w["user"], w["runtime"], w["project"],
                                    "resource.read", {"resource_id": w["resource_id"]})
        require(value == dict(resource_id=w["resource_id"], content=(
            self.source / "material.txt").read_text(), hash=w["inventory"]["material.txt"], format="txt"))
        return value


def no_secret(raw_bytes, raw, token):
    require(token.encode() not in raw_bytes, "CREDENTIAL_REFLECTION")
    pending = [raw]
    while pending:
        value = pending.pop()
        if type(value) is str:
            require(token not in value, "CREDENTIAL_REFLECTION")
        elif type(value) is dict:
            pending.extend(value.keys())
            pending.extend(value.values())
        elif type(value) is list:
            pending.extend(value)


def run(case, output, *, environ=None, _transport=None, _wall=time.time,
        _monotonic=time.monotonic, _sleep=time.sleep):
    env = os.environ if environ is None else environ
    start, wall_start = _monotonic(), _wall()
    prepared_bytes = (case / "control/prepared.json").read_bytes()
    # Claim is shared by every possible output directory for this fixture.
    claim = case / "control/execution-claim.json"
    with claim.open("x") as stream:
        stream.write(json.dumps(dict(status="CONSUMED_NO_RETRY", started_at=wall_start,
            deadline=wall_start + 600, prepared_sha256=digest(prepared_bytes),
            runner_sha256=digest(Path(__file__).read_bytes()))) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    # The exclusive directory entry must survive a crash as well as its file data.
    directory = os.open(claim.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    output.mkdir(parents=True, exist_ok=False)
    deadline = wall_start + 600
    report = dict(classification="CURRENT_BASELINE_AT02_READONLY_DIAGNOSTIC",
        fee_basis="USER_CONFIRMED_NO_COST_NOT_OFFICIAL_VERIFICATION",
        production_authority=False, account_source_verified=False,
        started_at=wall_start, deadline=deadline, prepared_sha256=digest(prepared_bytes),
        limits=dict(requests=2, output_tokens_each=512, body_bytes_each=1988,
                    reserved_envelope=5000, work_seconds=600, cleanup_seconds=10),
        slots=[], reserved_envelope=0,
        known_tokens=0, known_tokens_basis="SUM_OF_COMPLETE_REPORTS_NOT_UNKNOWN_AS_ZERO",
        usage_status="NOT_STARTED", tool_reads=0, retries=0, status="PREPARED", sql=[])
    path = output / "result.json"
    _save(path, report)
    source = None
    token = ""
    try:
        require(env.get("SIM2ACT_MODEL", "intern-s2") == "intern-s2", "CONFIGURATION_MISMATCH")
        token = env.get("SIM2ACT_INTERN_TOKEN", "") or env.get("INTERN_API_TOKEN", "")
        require(bool(token), "CREDENTIAL_NOT_CONFIGURED")
        w = json.loads(prepared_bytes)
        require(w["version"] == "AT02_READONLY_PREPARED_V1")
        design = json.loads((DESIGN / "contract.json").read_text())
        validate_call("resource.read", {"resource_id": w["resource_id"]})
        expected_messages = json.loads(json.dumps(design["first_messages_template"]))
        expected_messages[1]["content"] = expected_messages[1]["content"].replace(
            "{FROZEN_RESOURCE_ID}", w["resource_id"])
        require(w["first_messages"] == expected_messages)
        require(w["inventory"]["material.txt"] == design["material"]["sha256"])
        require(set(w["tables"]) == set(meta.tables) and all(
            entry["rows"] == EXPECTED_ROWS.get(name, 0) for name, entry in w["tables"].items()))
        source = ReadSource(case, w, report["sql"])
        with source.connection() as c:
            require(vector(c) == w["tables"], "FIXTURE_CHANGED")
        schema = [t for t in definitions() if t["function"]["name"] == "resource.read"]
        require(schema == w["schema"])
        require(digest(wire(w["first_messages"], schema)) == w["first_body_sha256"])
        settings = Settings("unused-no-business-database", output, mode="live", live_enabled=True,
                            token=token, max_requests=2, max_repairs=0, max_output_tokens=512)
        model = InternModel(settings, _transport)

        def healthy():
            require(_monotonic() - start < 600 and _wall() < deadline, "DIAGNOSTIC_DEADLINE")

        def call(messages, tools):
            healthy()
            source.check()
            body = wire(messages, tools)
            no_secret(body, json.loads(body), token)
            reserve = len(body) + 512
            require(len(report["slots"]) < 2 and len(body) <= 1988
                    and report["reserved_envelope"] + reserve <= 5000
                    and report["known_tokens"] + reserve <= 5000, "BUDGET_EXHAUSTED")
            slot = dict(status="STARTED_OUTCOME_UNKNOWN", reserved=reserve, body_bytes=len(body),
                        request_sha256=digest(body), request=json.loads(body), guard_entries=0)
            report["slots"].append(slot)
            report["reserved_envelope"] += reserve
            _save(path, report)  # Durable before adapter entry; never release on unknown/failure.
            call_deadline = min(_wall() + 120, deadline)

            def guard(request):
                healthy()
                source.check()  # Closes its read connection before returning to HTTP.
                slot["guard_entries"] += 1
                require(slot["guard_entries"] == 1 and request.method == "POST"
                        and str(request.url) == ENDPOINT == InternModel.ENDPOINT
                        and request.content == body
                        and request.headers.get("authorization") == "Bearer " + token)
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
            if usage["tokens"] is not None:
                slot["reported_tokens"] = usage["tokens"]
            if usage["status"] == "known":
                report["known_tokens"] += usage["tokens"]["total_tokens"]
            identity = returned_model_identity("intern-s2", raw.get("model"))
            require_returned_model(identity)
            slot["identity"] = identity  # Only the accepted fixed aliases reach persistence.
            require(usage["status"] == "known", "USAGE_UNKNOWN")
            require(usage["tokens"]["completion_tokens"] <= 512
                    and usage["tokens"]["total_tokens"] <= reserve
                    and report["known_tokens"] <= 5000, "BUDGET_EXHAUSTED")
            safe, calls = parse_response(raw)
            slot.update(response_sha256=digest(received.body), response_bytes=len(received.body),
                        assistant=safe, status="RECEIVED_VALID", finished_at=_wall())
            healthy()
            _save(path, report)
            return safe, calls

        messages = w["first_messages"]
        assistant, calls = call(messages, schema)
        require(len(calls) == 1 and calls[0]["function"]["name"] == "resource.read"
                and calls[0]["args"] == {"resource_id": w["resource_id"]}, "TOOL_SELECTION_REJECTED")
        feedback = source.read()
        report["tool_reads"] = 1
        report["tool_feedback"] = dict(call_id=calls[0]["id"], tool="resource.read", result=feedback,
                                       kind="ACTUAL_AUTHORIZED_READ_NOT_OPERATION_RECEIPT")
        _save(path, report)
        prior_end = report["slots"][0]["finished_at"]
        wait = max(0, 6 - (_wall() - prior_end))
        if wait:
            _sleep(wait)
        healthy()
        require(_wall() - prior_end >= 6, "RATE_LIMITED")
        final, calls = call([*messages, assistant, dict(role="tool", tool_call_id=(
            report["tool_feedback"]["call_id"]), content=json.dumps(feedback, separators=(",", ":")))], [])
        require(not calls and final["content"].strip() == feedback["content"].rstrip("\n"),
                "REVISION_REJECTED")
        source.check()
        with source.connection() as c:
            require(vector(c) == w["tables"], "FIXTURE_CHANGED")
        healthy()
        report["status"] = "PASS_BOUNDED_READONLY_FEEDBACK"
    except DomainError as error:
        report.update(status="STOPPED_NO_RETRY", error_code=error.code)
        if report["slots"]:
            slot = report["slots"][-1]
            status = getattr(error, "_received_status_code", None)
            if type(status) is int:
                slot["http_status"] = status
            captured = getattr(error, "_received_body", None)
            if type(captured) is bytes:
                # Invalid/partial/error bodies never persist or receive a digest.
                slot.update(error_body_bytes=len(captured), error_body_complete=getattr(
                    error, "_received_body_complete", False))
    except Exception as error:
        report.update(status="UNKNOWN_INTERNAL_FAILURE", error_type=type(error).__name__)
    finally:
        cleanup_start = _monotonic()
        if any("usage" not in slot for slot in report["slots"]):
            report["usage_status"] = "unknown"
        if source is not None:
            try:
                source.store.engine.dispose()
                report["read_engine_disposed"] = True
                report["source_inventory_unchanged"] = inventory(source.source) == source.witness["inventory"]
            except Exception as error:
                report["cleanup_error_type"] = type(error).__name__
        report["cleanup_seconds"] = _monotonic() - cleanup_start
        report["cleanup_within_10_seconds"] = report["cleanup_seconds"] <= 10
        report["elapsed_seconds"] = _monotonic() - start
        report["within_600_seconds"] = report["elapsed_seconds"] <= 600
        if report["status"] == "PASS_BOUNDED_READONLY_FEEDBACK" and not (
                report.get("read_engine_disposed") and report.get("source_inventory_unchanged")
                and report["cleanup_within_10_seconds"] and report["within_600_seconds"]):
            report["chain_status"] = report["status"]
            report["status"] = "UNKNOWN_CLEANUP_OR_DEADLINE"
        _save(path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute-user-confirmed-at02", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        w = prepare(args.case.resolve())
        print(json.dumps(dict(status="PREPARED_SYNTHETIC_OFFLINE", first_body_bytes=w["first_body_bytes"])))
        return 0
    if not args.execute_user_confirmed_at02 or args.output is None:
        parser.error("run requires explicit execution selection and a new output directory")

    def work_window_stop(_signum, _frame):
        raise DomainError("SUPERVISOR_WORK_WINDOW_STOPPED")

    signal.signal(signal.SIGTERM, work_window_stop)
    report = run(args.case.resolve(), args.output.resolve())
    print(json.dumps({k: report[k] for k in ("status", "known_tokens", "tool_reads", "elapsed_seconds")}))
    return 0 if report["status"] == "PASS_BOUNDED_READONLY_FEEDBACK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
