"""Offline adapter proofs and opt-in actual PG application-role concurrency.

The real PG test never calls the legacy env/runtime_role provisioning fixtures.
No explicit current connection means SKIP, never a SQLite PG substitute.
"""

import copy
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from protocol_pg_sealed import (
    FIXTURE_PATH,
    capture,
    digest,
    qualify,
    read_sealed,
    restore,
    runtime_spec,
)
from sqlalchemy import create_engine, event, insert, null, text
from sqlalchemy.dialects import postgresql

from sim2act.db import Store, fingerprint, meta, protocol_jobs
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider
from sim2act.protocol_jobs import inspect as inspect_job
from sim2act.protocol_reviews import review
from sim2act.worker import Worker


def original(tmp_path):
    fixture, path = read_sealed(tmp_path)
    source = create_engine("sqlite:///" + str(path))
    try:
        with source.connect() as c:
            return fixture, capture(c)
    finally:
        source.dispose()


@pytest.mark.parametrize("fault", [False, True])
def test_complete_sealed_mapping_and_atomic_import_offline(tmp_path, fault):
    _, records = original(tmp_path)
    target = create_engine("sqlite:///" + str(tmp_path / "target.sqlite"))
    meta.create_all(target)  # Offline SQLite adapter only; never the actual PG branch.
    statements = []

    def witness(_c, _cur, statement, _params, _context, _many):
        statements.append(statement.lstrip().split(None, 1)[0])
        if fault and statement.startswith("INSERT INTO protocol_jobs"):
            raise RuntimeError("offline import interruption")

    event.listen(target, "before_cursor_execute", witness)
    try:
        if fault:
            with (
                pytest.raises(RuntimeError, match="offline import interruption"),
                target.begin() as c,
            ):
                restore(c, records)
            with target.connect() as c:
                assert all(not rows for rows in capture(c).values())
        else:
            with target.begin() as c:
                restore(c, records)
            with target.connect() as c:
                assert digest(capture(c)) == digest(records)
            before = list(statements)
            with pytest.raises(ValueError, match="not empty"), target.begin() as c:
                restore(c, records)
            assert statements[len(before) :] and "INSERT" not in statements[len(before) :]
        assert set(statements) <= {"SELECT", "INSERT"}
        (tmp_path / "adapter-result.json").write_text(
            json.dumps(
                dict(
                    status="PASS",
                    scope="offline SQLite adapter only, not PG",
                    tables=len(records),
                    rows=sum(len(rows) for rows in records.values()),
                    fault_rollback=fault,
                    sql_verbs=sorted(set(statements)),
                    original_typed_digests=digest(records),
                ),
                indent=2,
            )
        )
    finally:
        target.dispose()


def test_sql_null_json_null_strict_types_and_pg_dialect(tmp_path):
    _, records = original(tmp_path)
    engine = create_engine("sqlite:///" + str(tmp_path / "nulls.sqlite"))
    meta.create_all(engine)
    # Two actual storage null kinds, and bool/int/float/list values in JSON.
    a, b = (
        copy.deepcopy(records["protocol_jobs"][0]["values"]),
        copy.deepcopy(records["protocol_jobs"][0]["values"]),
    )
    a.update(run_id="null-sql", result_snapshot=null())
    b.update(
        run_id="null-json",
        result_snapshot=None,
        accepted_snapshot={"b": True, "i": 1, "f": 1.0, "l": [None, False, 0]},
    )
    try:
        with engine.begin() as c:
            c.execute(insert(protocol_jobs).values(**a))
            c.execute(insert(protocol_jobs).values(**b))
        with engine.connect() as c:
            data = capture(c)
        rows = {row["values"]["run_id"]: row for row in data["protocol_jobs"]}
        assert rows["null-sql"]["values"]["result_snapshot"] is None
        assert "result_snapshot" in rows["null-sql"]["json_sql_null"]
        assert rows["null-json"]["values"]["result_snapshot"] is None
        assert "result_snapshot" not in rows["null-json"]["json_sql_null"]
        left, right = copy.deepcopy(rows["null-sql"]), copy.deepcopy(rows["null-json"])
        right["values"] = copy.deepcopy(left["values"])
        assert digest(dict(a=[left])) != digest(dict(a=[right]))
        typed = rows["null-json"]["values"]["accepted_snapshot"]
        assert type(typed["b"]) is bool and type(typed["i"]) is int and type(typed["f"]) is float
        assert (
            type(typed["l"]) is list and type(typed["l"][1]) is bool and type(typed["l"][2]) is int
        )
        # Compile every original fixed-schema insert for the actual PG dialect.
        count = 0
        for table in meta.sorted_tables:
            for row in records[table.name]:
                statement = insert(table).values(**row["values"])
                assert str(statement.compile(dialect=postgresql.dialect())).startswith(
                    "INSERT INTO"
                )
                count += 1
        assert count > 0
    finally:
        engine.dispose()
    destination = create_engine("sqlite:///" + str(tmp_path / "null-copy.sqlite"))
    meta.create_all(destination)
    try:
        with destination.begin() as c:
            restore(c, data)
        with destination.connect() as c:
            assert digest(capture(c)) == digest(data)
    finally:
        destination.dispose()


@pytest.mark.parametrize("change", ["missing_table", "missing_column", "bad_null_witness"])
def test_invalid_representation_rejected_before_insert(tmp_path, change):
    _, records = original(tmp_path)
    if change == "missing_table":
        records.pop("protocol_reviews")
    elif change == "missing_column":
        records["protocol_jobs"][0]["values"].pop("result_snapshot")
    else:
        records["protocol_jobs"][0]["json_sql_null"].append("run_id")
    engine = create_engine("sqlite:///" + str(tmp_path / "invalid.sqlite"))
    meta.create_all(engine)
    try:
        with pytest.raises(ValueError), engine.begin() as c:
            restore(c, records)
        with engine.connect() as c:
            assert all(not rows for rows in capture(c).values())
    finally:
        engine.dispose()


def test_explicit_pg_connection_gate_does_not_accept_sqlite_or_remote(monkeypatch):
    for url, schema in [
        ("sqlite:///local.sqlite", "test_" + "a" * 32),
        ("postgresql+psycopg://user:hidden@remote.invalid:5432/db", "test_" + "a" * 32),
        ("postgresql+psycopg://user:hidden@127.0.0.1:5432/db", "public"),
        (
            "postgresql+psycopg://user:hidden@127.0.0.1:5432/db?host=remote.invalid",
            "test_" + "a" * 32,
        ),
        (
            "postgresql+psycopg://user:hidden@127.0.0.1:5432/db?options=-crole=other",
            "test_" + "a" * 32,
        ),
        (
            "postgresql+psycopg://user:hidden@127.0.0.1:5432/db?service=other",
            "test_" + "a" * 32,
        ),
        ("postgresql+psycopg://user@127.0.0.1:5432/db", "test_" + "a" * 32),
    ]:
        with pytest.raises(ValueError) as failed:
            runtime_spec(url, schema)
        assert "hidden" not in str(failed.value)
    from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg
    from sqlalchemy.engine import make_url

    good = "postgresql+psycopg://user:hidden@127.0.0.1:5432/db"
    qualified, _ = runtime_spec(good, "test_" + "a" * 32)
    args = PGDialect_psycopg().create_connect_args(make_url(qualified))[1]
    assert args["host"] == args["hostaddr"] == "127.0.0.1"
    assert args["options"] == "-cstatement_timeout=20000 -clock_timeout=10000"
    with monkeypatch.context() as patch:
        patch.setenv("PGHOSTADDR", "remote.invalid")
        with pytest.raises(ValueError):
            runtime_spec(good, "test_" + "a" * 32)
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as c, pytest.raises(ValueError, match="Actual PostgreSQL"):
            qualify(c, "test_" + "a" * 32)
    finally:
        engine.dispose()


def test_existing_pg_app_role_sealed_cold_atomic_and_original_key_wait(tmp_path, monkeypatch):
    supplied = os.environ.get("SIM2ACT_PROTOCOL_PG_RUNTIME_URL")
    schema = os.environ.get("SIM2ACT_PROTOCOL_PG_SCHEMA")
    if not supplied or not schema:
        pytest.skip(
            "Actual PG NOT_RUN: explicit preexisting app URL and pre-migrated empty isolated schema absent; no provisioning"
        )
    url, schema = runtime_spec(supplied, schema)
    fixture, records = original(tmp_path)
    stores = []

    def app_store():
        store = Store(url)
        store.engine = store.engine.execution_options(schema_translate_map={None: schema})
        stores.append(store)
        return store

    probe, first, second = app_store(), app_store(), app_store()
    release, held, second_connected = threading.Event(), threading.Event(), threading.Event()
    pids, receipts = {}, []
    evidence = dict(
        status="UNKNOWN",
        scope="actual PG only if explicitly provisioned before test",
        records_retained=False,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("No model, acceptance, Worker or claim allowed")

    for owner, name in (
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (BudgetedProvider, "call"),
        (BudgetedProvider, "preflight"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "__init__"),
        (Worker, "reserve"),
        (Store, "claim"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    monkeypatch.setattr(time, "time", lambda: fixture["business_at"])
    body = dict(
        contract_id=fixture["contract_id"],
        expected_version=2,
        expected_fence=1,
        expected_result_fingerprint=fixture["expected_result_fingerprint"],
        request_key="sealed-cold-pg-concurrent-original",
    )
    try:
        with probe.engine.begin() as c:
            evidence["qualification"] = qualify(c, schema)
            # No schema/role/DDL/grant action. This consumes the preauthorized empty schema once.
            restore(c, records)
        evidence["records_retained"] = True
        with probe.engine.connect() as c:
            before = digest(capture(c))
        fired = []

        def fault(_c, _cursor, sql, _params, _context, _many):
            if sql.startswith("INSERT INTO") and ".protocol_reviews " in sql:
                fired.append(True)
                raise RuntimeError("owned PG review INSERT fault")

        event.listen(first.engine, "before_cursor_execute", fault)
        try:
            with pytest.raises(RuntimeError, match="owned PG review INSERT fault"):
                review(first, fixture["user"], fixture["run"], body)
        finally:
            event.remove(first.engine, "before_cursor_execute", fault)
        assert fired == [True]
        with probe.engine.connect() as c:
            assert digest(capture(c)) == before

        original_event = first.event

        def pause(c, rid, kind, data):
            if rid == fixture["run"] and kind == "PROTOCOL_REVIEW":
                pids["first"] = c.execute(text("SELECT pg_catalog.pg_backend_pid()")).scalar_one()
                held.set()
                assert release.wait(10), "Bounded test transaction was not released"
            return original_event(c, rid, kind, data)

        monkeypatch.setattr(first, "event", pause)

        def connection_pid(dbapi_connection, _record):
            pids["second"] = dbapi_connection.info.backend_pid
            second_connected.set()

        event.listen(second.engine, "connect", connection_pid)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(review, first, fixture["user"], fixture["run"], body)
            try:
                assert held.wait(5)
                b = pool.submit(review, second, fixture["user"], fixture["run"], body)
                assert second_connected.wait(5)
                until = time.monotonic() + 5
                blocking = []
                while time.monotonic() < until:
                    with probe.engine.connect() as c:
                        blocking = c.execute(
                            text("SELECT pg_catalog.pg_blocking_pids(:pid)"),
                            dict(pid=pids["second"]),
                        ).scalar_one()
                    if pids["first"] in blocking:
                        break
                    time.sleep(0.02)
                assert (
                    pids["first"] != pids["second"] and pids["first"] in blocking and not b.done()
                )
                evidence["actual_wait"] = dict(pids=pids, blocking=blocking)
            finally:
                release.set()
            receipts = [a.result(timeout=15), b.result(timeout=15)]
        assert fingerprint(receipts[0]) == fingerprint(receipts[1])
        fresh = app_store()
        assert fingerprint(review(fresh, fixture["user"], fixture["run"], body)) == fingerprint(
            receipts[0]
        )
        current = inspect_job(fresh, fixture["user"], fixture["run"])
        assert (
            current["phase"] == "cold"
            and current["status"] == "SUCCEEDED"
            and current["version"] == 3
        )
        assert (
            current["fence"] == 1
            and current["semantic_status"] == "PASS"
            and current["semantic_review"] == "APPROVED"
        )
        assert (
            current["owner_semantic_acceptance"] == "PENDING"
            and current["formal_publication_enabled"] is False
        )
        with probe.engine.connect() as c:
            after_records = capture(c)
            after = digest(after_records)
        expected_runs = copy.deepcopy(records["runs"])
        for row in expected_runs:
            if row["values"]["id"] == fixture["run"]:
                row["values"]["status"] = "SUCCEEDED"
                row["values"]["version"] = 3
        assert digest(dict(runs=expected_runs))["runs"] == after["runs"]
        assert all(
            (tmp_path / name).read_bytes() == (FIXTURE_PATH.parent / "fixture" / name).read_bytes()
            for name in fixture["sidecars"]
        )
        assert {name for name in before if before[name] != after[name]} == {
            "runs",
            "events",
            "protocol_reviews",
        }
        assert len(after["protocol_reviews"]) == len(before["protocol_reviews"]) + 1
        assert len(after["events"]) == len(before["events"]) + 1
        evidence.update(
            status="PASS",
            before=before,
            after=after,
            receipts=receipts,
            current=current,
            new_model=0,
            new_source=0,
            new_extract=0,
            ddl_or_grants_issued=False,
            retained_data="Exact synthetic fixture plus its reviewed Cold; no automatic DELETE/DROP",
        )
    finally:
        release.set()
        for store in stores:
            store.engine.dispose()
        (tmp_path / "pg-result.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
