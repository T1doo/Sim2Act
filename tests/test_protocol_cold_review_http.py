"""Genuine sealed Cold: authenticated HTTP, stored proof and connection rebuild.

No initialization, Worker, model, new acceptance, native browser or G0 window.
API instances are threads in this pytest process, not OS process restarts.
"""

import copy
import gzip
import hashlib
import json
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    attempts,
    events,
    fingerprint,
    grants,
    meta,
    operations,
    protocol_jobs,
    protocol_reviews,
    runs,
)
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider
from sim2act.worker import Worker

REPO = Path(__file__).parents[1]
EVIDENCE = REPO / "docs/evidence/protocol-cold-review-http-20261022"
FIXTURE = json.loads((EVIDENCE / "fixture.json").read_text())
HEADERS = {"Authorization": "Bearer secret test token"}  # Original sealed synthetic owner.


def snapshot(store):
    with store.engine.connect() as c:
        return {
            table.name: sorted(
                fingerprint(dict(row)) for row in c.execute(select(table)).mappings()
            )
            for table in meta.sorted_tables
        }


def sidecars(root):
    return {name: (root / name).read_bytes() for name in FIXTURE["sidecars"]}


def cold_row(store):
    with store.engine.connect() as c:
        return dict(c.execute(select(runs).where(runs.c.id == FIXTURE["run"])).mappings().one())


def command():
    return dict(
        contract_id=FIXTURE["contract_id"],
        expected_version=2,
        expected_fence=1,
        expected_result_fingerprint=FIXTURE["expected_result_fingerprint"],
        request_key="sealed-cold-negative-or-probe",
    )


@pytest.fixture
def sealed(tmp_path, monkeypatch):
    archive = (REPO / FIXTURE["archive"]).read_bytes()
    assert hashlib.sha256(archive).hexdigest() == FIXTURE["archive_gzip_sha256"]
    raw = gzip.decompress(archive)
    assert hashlib.sha256(raw).hexdigest() == FIXTURE["database_sha256"]
    manifest = json.loads((REPO / FIXTURE["original_manifest"]).read_text())
    assert (
        manifest[FIXTURE["original_database_manifest_key"]]["sha256"] == FIXTURE["database_sha256"]
    )
    database = tmp_path / "cold.sqlite"
    database.write_bytes(raw)
    for name, witness in FIXTURE["sidecars"].items():
        assert manifest[witness["original_manifest_key"]] == {
            "bytes": witness["bytes"],
            "sha256": witness["sha256"],
        }
        source = EVIDENCE / "fixture" / name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == witness["sha256"]
        shutil.copyfile(source, tmp_path / name)
        (tmp_path / name).with_suffix(".lock").write_bytes(b"")
    url = "sqlite:///" + str(database)
    store = Store(url, test_only=True)  # Never initialize/migrate/reset.
    settings = Settings(database_url=url, data_dir=tmp_path, **FIXTURE["api_settings"])
    monkeypatch.setattr(time, "time", lambda: FIXTURE["business_at"])
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("send/preflight/accept/reserve/claim/worker")
        raise AssertionError("Cold review cannot send, reserve, accept or start a Worker")

    for owner, name in (
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (BudgetedProvider, "call"),
        (BudgetedProvider, "preflight"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "reserve"),
        (Worker, "__init__"),
        (Store, "claim"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    try:
        assert cold_row(store)["status"] == "WAITING_APPROVAL"
        yield store, settings, calls
    finally:
        store.engine.dispose()
        assert calls == []


@contextmanager
def owned_api(store, settings, report, label):
    """Confirm every first API thread is gone before starting its successor."""
    initial = set(threading.enumerate())
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(32)
    base = f"http://127.0.0.1:{listener.getsockname()[1]}"
    app = create_app(store, settings)
    counts = dict(get=0, post=0)

    @app.middleware("http")
    async def bounded(request, call_next):
        assert (request.method, request.url.path) in {
            ("GET", f"/api/projects/{FIXTURE['project']}/protocol/runs/{FIXTURE['run']}"),
            ("POST", f"/api/internal/protocol/runs/{FIXTURE['run']}/reviews"),
        }, "Only this sealed Cold inspect/review may reach the API"
        kind = request.method.lower()
        counts[kind] += 1
        assert counts[kind] <= (10 if kind == "get" else 3), "Local Cold HTTP allowance"
        return await call_next(request)

    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=False)
    thread.start()
    try:
        until = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < until
            time.sleep(0.01)
        yield base
    finally:
        until = time.monotonic() + 10
        server.should_exit = True
        thread.join(max(0, until - time.monotonic()))
        for worker in set(threading.enumerate()) - initial:
            if worker.name == "AnyIO worker thread":
                worker.join(max(0, until - time.monotonic()))
        listener.close()
        remaining = [t.name for t in set(threading.enumerate()) - initial if t.is_alive()]
        report.append(
            dict(api=label, stopped=not thread.is_alive(), remaining=remaining, counts=counts)
        )
        assert not thread.is_alive() and not remaining and time.monotonic() <= until


def trace_sql(store, trace, label):
    def capture(_c, _cursor, sql, params, _context, _many):
        item = dict(api=label, sql=sql, parameters=params)
        trace["count"] += 1
        trace["digest"].update(
            (json.dumps(item, sort_keys=True, ensure_ascii=False, default=str) + "\n").encode()
        )
        if len(trace["samples"]) < 128:
            trace["samples"].append(item)

    event.listen(store.engine, "before_cursor_execute", capture)
    return capture


def test_genuine_cold_http_original_key_and_persisted_reopen(sealed, tmp_path):
    store, settings, calls = sealed
    before, original_run, original_sidecars = snapshot(store), cold_row(store), sidecars(tmp_path)
    cleanups, sql = [], dict(count=0, digest=hashlib.sha256(), samples=[])
    capture = trace_sql(store, sql, "first")
    with owned_api(store, settings, cleanups, "first") as base:
        (tmp_path / "http-info.json").write_text(
            json.dumps(
                dict(base=base, project=FIXTURE["project"], run=FIXTURE["run"], phase="cold")
            )
        )
        result = subprocess.run(
            ["node", "tests/protocol_review_ui.cjs", str(tmp_path), "http-cold"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=30,
        )
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
    event.remove(store.engine, "before_cursor_execute", capture)
    payload = json.loads((tmp_path / "http-receipts.json").read_text())
    assert payload["read"]["phase"] == "cold"
    assert payload["bodies"][0] == payload["bodies"][1]
    assert payload["receipts"][0] == payload["receipts"][1]
    result = json.loads((tmp_path / "http-cold-result.json").read_text())
    assert (
        result["source_sha256"]
        == hashlib.sha256((REPO / "src/sim2act/web/protocol.js").read_bytes()).hexdigest()
    )
    after = snapshot(store)
    assert {name for name in before if before[name] != after[name]} == {
        "runs",
        "events",
        "protocol_reviews",
    }
    assert len(after["events"]) == len(before["events"]) + 1
    assert len(after["protocol_reviews"]) == len(before["protocol_reviews"]) + 1
    current = cold_row(store)
    assert {key for key in current if current[key] != original_run[key]} == {"status", "version"}
    assert current["status"] == "SUCCEEDED" and current["version"] == 3 and current["fence"] == 1
    with store.engine.connect() as c:
        row = dict(
            c.execute(select(protocol_reviews).where(protocol_reviews.c.run_id == FIXTURE["run"]))
            .mappings()
            .one()
        )
        assert fingerprint(row["payload"]["request"]) == fingerprint(payload["bodies"][0])
        from sim2act.protocol_reviews import _public

        assert fingerprint(_public(row)) == fingerprint(payload["receipts"][0])
        ledger = dict(
            attempts=[
                dict(r)
                for r in c.execute(
                    select(attempts).where(attempts.c.run_id == FIXTURE["run"])
                ).mappings()
            ],
            operations=[
                dict(r)
                for r in c.execute(
                    select(operations).where(operations.c.run_id == FIXTURE["run"])
                ).mappings()
            ],
            completion_events=[
                dict(r)
                for r in c.execute(
                    select(events).where(events.c.run_id == FIXTURE["run"])
                ).mappings()
            ],
            review=row,
        )
    store.engine.dispose()  # First API/AnyIO stopped before a new connection/API.
    reopened = Store(settings.database_url, test_only=True)
    capture = trace_sql(reopened, sql, "reopened")
    try:
        with (
            owned_api(reopened, settings, cleanups, "reopened") as base,
            httpx.Client(base_url=base, headers=HEADERS, timeout=5) as client,
        ):
            path = f"/api/projects/{FIXTURE['project']}/protocol/runs/{FIXTURE['run']}"
            fresh = client.get(path)
            assert fresh.status_code == 200 and fingerprint(fresh.json()) == fingerprint(
                payload["read"]
            )
            repeated = client.post(
                f"/api/internal/protocol/runs/{FIXTURE['run']}/reviews", json=payload["bodies"][0]
            )
            assert repeated.status_code == 201 and fingerprint(repeated.json()) == fingerprint(
                payload["receipts"][0]
            )
            final = client.get(path)
            assert final.status_code == 200 and fingerprint(final.json()) == fingerprint(
                fresh.json()
            )
        assert snapshot(reopened) == after and sidecars(tmp_path) == original_sidecars and not calls
        (tmp_path / "result.json").write_text(
            json.dumps(
                dict(
                    status="PASS",
                    phase="cold",
                    classification="SYNTHETIC_SQLITE_AUTHENTICATED_LOOPBACK_HTTP",
                    run=FIXTURE["run"],
                    source=FIXTURE["source_run"],
                    extraction=FIXTURE["extraction_run"],
                    before=dict(status="WAITING_APPROVAL", version=2, fence=1),
                    after=dict(
                        status="SUCCEEDED",
                        version=3,
                        fence=1,
                        semantic_status="PASS",
                        semantic_review="APPROVED",
                        owner_semantic_acceptance="PENDING",
                        formal_publication_enabled=False,
                    ),
                    new_mock=0,
                    new_model=0,
                    new_worker=0,
                    new_source=0,
                    new_extract=0,
                    changed_tables=["runs", "events", "protocol_reviews"],
                    accounting_unchanged=True,
                    original_result_unchanged=True,
                    sidecars_unchanged=True,
                    original_deadlines_unchanged=True,
                    original_key_replay_after_reopen=True,
                    strict_receipt_projection=True,
                    cleanups=cleanups,
                    restart_scope="same pytest process, sequential API threads/new Store/connection; not OS process restart",
                    clock="explicit sealed completion timestamp+1; not real-clock/G0",
                ),
                indent=2,
            )
        )
        (tmp_path / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2))
        (tmp_path / "sql.json").write_text(
            json.dumps(
                dict(
                    observed_statement_count=sql["count"],
                    all_observed_sql_sha256=sql["digest"].hexdigest(),
                    retained_samples=sql["samples"],
                    scope="all observed SQL counted/digested; first 128 samples retained, not a full SQL replay log",
                ),
                ensure_ascii=False,
                default=str,
            )
        )
        (tmp_path / "table-comparison.json").write_text(
            json.dumps(dict(before=before, after=after), indent=2)
        )
        with (
            reopened.engine.connect() as connection,
            sqlite3.connect(tmp_path / "after.sqlite") as target,
        ):
            connection.connection.driver_connection.backup(target)
        (tmp_path / "after.sqlite.gz").write_bytes(
            gzip.compress((tmp_path / "after.sqlite").read_bytes(), mtime=0)
        )
    finally:
        event.remove(reopened.engine, "before_cursor_execute", capture)
        reopened.engine.dispose()
        (tmp_path / "cleanup.json").write_text(json.dumps(cleanups, indent=2))


@pytest.mark.parametrize(
    "change",
    [
        "contract",
        "fence",
        "fingerprint",
        "revoke_new",
        "cold_attempt",
        "cold_operation",
        "upstream_review",
        "upstream_plan",
    ],
)
def test_cold_http_rejects_stale_or_broken_dependencies_without_writes(sealed, tmp_path, change):
    store, settings, calls = sealed
    body = command()
    with store.tx() as c:
        if change == "contract":
            body["contract_id"] = "protocol.synthetic.a-source.v1"
        elif change == "fence":
            body["expected_fence"] += 1
        elif change == "fingerprint":
            body["expected_result_fingerprint"] = "0" * 64
        elif change == "revoke_new":
            changed = c.execute(
                update(grants)
                .where(grants.c.resource_id == FIXTURE["new_resource"])
                .values(revoked=True)
            )
            assert changed.rowcount > 0
        elif change == "cold_attempt":
            c.execute(
                update(attempts)
                .where(attempts.c.run_id == FIXTURE["run"])
                .values(response_model="wrong-model")
            )
        elif change == "cold_operation":
            c.execute(
                update(operations)
                .where(operations.c.run_id == FIXTURE["run"])
                .values(call_id="wrong-plan-step")
            )
        elif change == "upstream_review":
            row = (
                c.execute(
                    select(protocol_reviews).where(
                        protocol_reviews.c.run_id == FIXTURE["source_run"]
                    )
                )
                .mappings()
                .one()
            )
            value = copy.deepcopy(row["payload"])
            value["decision"] = "FAIL"
            c.execute(
                update(protocol_reviews)
                .where(protocol_reviews.c.id == row["id"])
                .values(payload=value)
            )
        else:
            row = (
                c.execute(
                    select(protocol_jobs).where(protocol_jobs.c.run_id == FIXTURE["extraction_run"])
                )
                .mappings()
                .one()
            )
            value = copy.deepcopy(row["result_snapshot"])
            value["compiled_plan"]["plan_fingerprint"] = "0" * 64
            c.execute(
                update(protocol_jobs)
                .where(protocol_jobs.c.run_id == row["run_id"])
                .values(result_snapshot=value)
            )
    # Baseline is AFTER intentional corruption/revocation, not before it.
    before, original_sidecars = snapshot(store), sidecars(tmp_path)
    with TestClient(create_app(store, settings)) as client:
        response = client.post(
            f"/api/internal/protocol/runs/{FIXTURE['run']}/reviews", headers=HEADERS, json=body
        )
        assert 400 <= response.status_code < 500
        read = client.get(
            f"/api/projects/{FIXTURE['project']}/protocol/runs/{FIXTURE['run']}", headers=HEADERS
        )
        if change in {"contract", "fence", "fingerprint"}:
            assert read.status_code == 200
        else:
            assert 400 <= read.status_code < 500
        assert snapshot(store) == before and sidecars(tmp_path) == original_sidecars and not calls
        with store.engine.connect() as c:
            assert (
                c.execute(
                    select(protocol_reviews).where(protocol_reviews.c.run_id == FIXTURE["run"])
                ).first()
                is None
            )
    (tmp_path / "rejection.json").write_text(
        json.dumps(
            dict(
                change=change,
                post_status=response.status_code,
                error=response.json(),
                get_status=read.status_code,
                no_extra_writes=True,
                sidecars_unchanged=True,
                new_mock=0,
            ),
            indent=2,
        )
    )


def test_cold_http_authentication_and_wrong_project_are_closed(sealed):
    store, settings, calls = sealed
    before = snapshot(store)
    with TestClient(create_app(store, settings)) as client:
        path = f"/api/projects/{FIXTURE['project']}/protocol/runs/{FIXTURE['run']}"
        assert client.get(path).status_code == 403
        assert (
            client.post(
                f"/api/internal/protocol/runs/{FIXTURE['run']}/reviews", json=command()
            ).status_code
            == 403
        )
        response = client.get(
            f"/api/projects/proj_{'0' * 32}/protocol/runs/{FIXTURE['run']}", headers=HEADERS
        )
        assert response.status_code == 403
    assert snapshot(store) == before and not calls


def test_cold_review_insert_failure_rolls_back_status_version_and_receipt(sealed, tmp_path):
    store, settings, calls = sealed
    before, original_sidecars = snapshot(store), sidecars(tmp_path)
    fired = []

    def fail(_c, _cursor, statement, _params, _context, _many):
        if statement.startswith("INSERT INTO protocol_reviews"):
            fired.append(True)
            raise RuntimeError("Synthetic Cold review write fault")

    event.listen(store.engine, "before_cursor_execute", fail)
    try:
        with TestClient(create_app(store, settings), raise_server_exceptions=False) as client:
            response = client.post(
                f"/api/internal/protocol/runs/{FIXTURE['run']}/reviews",
                headers=HEADERS,
                json=command(),
            )
            assert response.status_code == 500
    finally:
        event.remove(store.engine, "before_cursor_execute", fail)
    assert (
        fired == [True]
        and snapshot(store) == before
        and sidecars(tmp_path) == original_sidecars
        and not calls
    )
    (tmp_path / "rollback.json").write_text(
        json.dumps(
            dict(
                status="PASS",
                fault="actual review INSERT after Run UPDATE",
                http_status=500,
                full_table_rollback=True,
                original_sidecars_unchanged=True,
            )
        )
    )
