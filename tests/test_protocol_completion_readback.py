"""Sealed completed facts only: authenticated ASGI GET, no sends or writers."""

import copy
import gzip
import hashlib
import json
import socket
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, insert, select, update

from sim2act import protocol_extract_completion as extract
from sim2act import protocol_jobs
from sim2act import protocol_source_completion as source
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    attempts,
    events,
    fingerprint,
    grants,
    meta,
    protocol_request_slots,
    resources,
    runs,
)
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider
from sim2act.worker import Worker

REPO = Path(__file__).parents[1]
HEADERS = {"Authorization": "Bearer secret test token"}


def snapshot(store):
    with store.engine.connect() as c:
        return {
            t.name: sorted(fingerprint(dict(r)) for r in c.execute(select(t)).mappings())
            for t in meta.sorted_tables
        }


def prepare(root, phase, monkeypatch, *, before=False, reviewed=False):
    root.mkdir(exist_ok=True)
    archive = REPO / f"docs/evidence/protocol-{phase}-process-recovery-20261022"
    original = json.loads((archive / "original.json").read_text())
    original["phase"] = phase
    manifest = json.loads((archive / "MANIFEST.json").read_text())
    name = "before.sqlite.gz" if before else "after.sqlite.gz"
    packed = (archive / name).read_bytes()
    expected = manifest[name]
    assert hashlib.sha256(packed).hexdigest() == (
        expected if isinstance(expected, str) else expected["sha256"]
    )
    db = root / "sealed.sqlite"
    db.write_bytes(gzip.decompress(packed))
    if reviewed:
        evidence = REPO / "docs/evidence/protocol-completion-readback-20261022"
        origin = json.loads((evidence / "source-reviewed-origin.json").read_text())
        packed = (evidence / "source-reviewed.sqlite.gz").read_bytes()
        assert hashlib.sha256(packed).hexdigest() == origin["gzip_sha256"]
        raw_db = gzip.decompress(packed)
        assert hashlib.sha256(raw_db).hexdigest() == origin["raw_sha256"]
        db.write_bytes(raw_db)
    raw = (archive / "original-received-sidecar.json").read_bytes()
    expected = manifest["original-received-sidecar.json"]
    assert hashlib.sha256(raw).hexdigest() == (
        expected if isinstance(expected, str) else expected["sha256"]
    )
    sidecar = root / (original["run"] + ".json")
    sidecar.write_bytes(raw)
    sidecar.with_suffix(".lock").write_bytes(b"")
    store = Store("sqlite:///" + str(db), test_only=True)
    settings = Settings(
        **dict(original["settings"], database_url=str(store.engine.url), data_dir=root)
    )
    monkeypatch.setattr(time, "time", lambda: original["resume_at"])
    return store, settings, original, sidecar


@pytest.fixture(autouse=True)
def no_business_work(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("forbidden business work")
        raise AssertionError("Readback must not enter any writer, provider or worker")

    for owner, name in (
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (BudgetedProvider, "call"),
        (BudgetedProvider, "preflight"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "__init__"),
        (Worker, "reserve"),
        (Store, "claim"),
        (Store, "event"),
        (source, "complete_source"),
        (extract, "complete_extract"),
        (protocol_jobs, "complete_in_tx"),
        (protocol_jobs, "compile_extraction"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    yield
    assert calls == []


@pytest.fixture(params=["source", "extract"])
def sealed(request, tmp_path, monkeypatch):
    value = prepare(tmp_path, request.param, monkeypatch)
    try:
        yield value
    finally:
        value[0].engine.dispose()


def read(client, original, *, pid=None, rid=None, headers=HEADERS):
    return client.get(
        f"/api/projects/{pid or original['project']}/protocol/runs/{rid or original['run']}/completion-receipt",
        headers=headers,
    )


def readonly(value, operation):
    store, _, _, sidecar = value
    before = snapshot(store)
    raw = sidecar.read_bytes() if sidecar.exists() else None
    statements = []

    def trace(_c, _cursor, sql, params, _ctx, _many):
        verb = sql.lstrip().split(None, 1)[0].upper()
        statements.append(dict(sql=sql, parameters=repr(params)))
        assert verb in {"BEGIN", "SELECT"}, "DML/DDL forbidden even on failure"

    event.listen(store.engine, "before_cursor_execute", trace)
    try:
        response = operation()
    finally:
        event.remove(store.engine, "before_cursor_execute", trace)
        assert snapshot(store) == before
        assert (sidecar.read_bytes() if sidecar.exists() else None) == raw
    file = sidecar.parent / "readonly-observation.json"
    history = json.loads(file.read_text()) if file.exists() else []
    history.append(
        dict(
            method=response.request.method,
            path=response.request.url.path,
            before_tables=before,
            after_tables=snapshot(store),
            sidecar_sha256=None if raw is None else hashlib.sha256(raw).hexdigest(),
            tables=len(before),
            status=response.status_code,
            response=response.json(),
            statements=statements,
            business_post=0,
            models=0,
            worker=0,
            all_tables_unchanged=True,
            sidecar_unchanged=True,
        )
    )
    file.write_text(json.dumps(history, indent=2))
    return response


def test_original_receipt_after_execution_deadline_and_new_store(sealed, monkeypatch):
    store, settings, original, _ = sealed
    # Historical execution ended; current read grants are still valid.
    monkeypatch.setattr(time, "time", lambda: original["resume_at"] + 600)
    # Today's execution cap cannot be used to rewrite a historical completion.
    settings = replace(settings, run_seconds=1)
    with store.engine.connect() as c:
        kind = source.COMPLETED if original["phase"] == "source" else extract.COMPLETED
        old = c.execute(
            select(events.c.data).where(events.c.run_id == original["run"], events.c.kind == kind)
        ).scalar_one()
    with TestClient(create_app(store, settings)) as client:
        response = readonly(sealed, lambda original=original: read(client, original))
    assert response.status_code == 200, response.text
    got = response.json()
    assert set(got) == {"namespace", "run_id", "phase", "state", "request", "receipt"}
    assert got["state"] == "FOUND" and got["namespace"] == "protocol-completion-readback.v1"
    assert fingerprint(got["request"]) == fingerprint(old["request"])
    assert (
        fingerprint(got["receipt"]) == fingerprint(old["response"])
        and got["receipt"]["cached"] is False
    )
    fresh = Store(settings.database_url, test_only=True)
    try:
        with TestClient(create_app(fresh, settings)) as client:
            again = readonly(
                (fresh, settings, original, sealed[3]),
                lambda original=original: read(client, original),
            )
        assert again.content == response.content
    finally:
        fresh.engine.dispose()


@pytest.mark.parametrize(
    "fault",
    [
        "missing_run",
        "missing_attempt",
        "duplicate",
        "wrong_family",
        "response_namespace",
        "response_extra",
        "response_bool",
        "request_bool",
        "recovery_float",
        "cross_run",
        "wrong_attempt",
        "slot",
        "content",
        "runtime_revoked",
        "principal_revoked",
        "runtime_expired",
        "principal_expired",
        "late",
        "early",
        "cancel",
        "revoked",
        "expired",
        "sidecar",
        "usage",
        "wire",
    ],
)
def test_failures_are_readonly_conflicts_not_missing(sealed, fault):
    store, settings, original, sidecar = sealed
    rid = original["run"]
    with store.tx() as c:
        kind = source.COMPLETED if original["phase"] == "source" else extract.COMPLETED
        roots = c.execute(select(events).where(events.c.kind == kind)).mappings().all()
        ids = [r["id"] for r in roots]
        old = copy.deepcopy(next(r["data"] for r in roots if r["run_id"] == rid))
        if fault.startswith("missing_"):
            c.execute(
                delete(events).where(
                    events.c.id.in_(
                        [r["id"] for r in roots if (r["run_id"] == rid) == (fault == "missing_run")]
                    )
                )
            )
        elif fault == "duplicate":
            row = dict(roots[0])
            row["id"] = "event_extra_completion_readback"
            c.execute(insert(events).values(**row))
        elif fault == "wrong_family":
            c.execute(
                update(events)
                .where(events.c.id.in_(ids))
                .values(kind=extract.COMPLETED if kind == source.COMPLETED else source.COMPLETED)
            )
        elif fault in {
            "response_namespace",
            "response_extra",
            "response_bool",
            "request_bool",
            "recovery_float",
            "cross_run",
            "late",
            "early",
        }:
            if fault == "response_namespace":
                old["response"]["namespace"] = "protocol-review.v1"
            if fault == "response_extra":
                old["response"]["extra"] = 1
            if fault == "response_bool":
                old["response"]["provider_requests"] = False
            if fault == "request_bool":
                old["request"]["expected_version"] = True
            if fault == "recovery_float":
                old["recovery_fence"] = float(old["recovery_fence"])
            if fault == "cross_run":
                old["response"]["run_id"] = "run_not_original"
            if fault == "late":
                old["completed_at"] += 1000
            if fault == "early":
                old["completed_at"] = 0
            c.execute(update(events).where(events.c.id.in_(ids)).values(data=old))
        elif fault == "cancel":
            c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))
        elif fault == "wrong_attempt":
            aids = list(c.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).scalars())
            mirror = next(r for r in roots if r["run_id"] != rid)
            other = next((a for a in aids if a != mirror["run_id"]), rid)
            c.execute(update(events).where(events.c.id == mirror["id"]).values(run_id=other))
        elif fault == "slot":
            c.execute(
                update(protocol_request_slots)
                .where(protocol_request_slots.c.run_id == rid)
                .values(fence=999)
            )
        elif fault == "content":
            c.execute(
                update(resources)
                .where(resources.c.project_id == original["project"])
                .values(content="changed content")
            )
        elif fault.startswith("runtime_") or fault.startswith("principal_"):
            actor = c.execute(
                select(
                    runs.c.runtime_id if fault.startswith("runtime_") else runs.c.principal_id
                ).where(runs.c.id == rid)
            ).scalar_one()
            c.execute(
                update(grants)
                .where(grants.c.project_id == original["project"], grants.c.principal_id == actor)
                .values(
                    **(
                        {"revoked": True}
                        if fault.endswith("revoked")
                        else {"expires_at": time.time() - 1}
                    )
                )
            )
        elif fault in {"revoked", "expired"}:
            c.execute(
                update(grants)
                .where(grants.c.project_id == original["project"])
                .values(
                    **({"revoked": True} if fault == "revoked" else {"expires_at": time.time() - 1})
                )
            )
        elif fault in {"usage", "wire"}:
            row = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().first()
            if fault == "usage":
                c.execute(update(attempts).where(attempts.c.id == row["id"]).values(usage={}))
            else:
                params = dict(row["parameters"])
                params["protocol_wire"] = {}
                c.execute(
                    update(attempts).where(attempts.c.id == row["id"]).values(parameters=params)
                )
    if fault == "sidecar":
        sidecar.write_text("{}")
    with TestClient(create_app(store, settings)) as client:
        response = readonly(sealed, lambda original=original: read(client, original))
    assert response.status_code in {400, 403, 409}, response.text
    assert response.json()["error"]["code"] in {
        "GRANT_REVOKED",
        "VERIFICATION_FAILED",
        "PERMISSION_DENIED",
        "VERSION_CONFLICT",
    }


def test_absent_completion_marks_do_not_need_sidecar_or_reconstruct_key(sealed):
    store, settings, original, sidecar = sealed
    with store.tx() as c:
        c.execute(delete(events).where(events.c.kind.in_([source.COMPLETED, extract.COMPLETED])))
    sidecar.unlink()
    with TestClient(create_app(store, settings)) as client:
        response = readonly(sealed, lambda original=original: read(client, original))
    assert response.status_code == 200 and response.json()["state"] == "NOT_FOUND"
    assert response.json()["request"] is response.json()["receipt"] is None


@pytest.mark.parametrize("phase", ["source", "extract"])
def test_ready_or_accepted_is_not_completed(tmp_path, monkeypatch, phase):
    value = prepare(tmp_path, phase, monkeypatch, before=True)
    store, settings, original, _ = value
    try:
        with TestClient(create_app(store, settings)) as client:
            response = readonly(value, lambda original=original: read(client, original))
        assert response.status_code == 200 and response.json()["state"] == "NOT_FOUND"
    finally:
        store.engine.dispose()


def test_auth_project_and_mode_gate(sealed):
    store, settings, original, _ = sealed
    with TestClient(create_app(store, settings)) as client:
        for kwargs in ({"headers": {}}, {"pid": "proj_not_owned"}, {"rid": "run_unknown"}):
            response = readonly(sealed, lambda kwargs=kwargs: read(client, original, **kwargs))
            assert response.status_code in {401, 403}
    with TestClient(create_app(store, replace(settings, mode="live"))) as client:
        assert readonly(sealed, lambda original=original: read(client, original)).status_code == 403


def test_controller_original_completion_still_isolated(tmp_path):
    run = subprocess.run(
        ["node", "tests/protocol_completion_ui.cjs", str(tmp_path), "logic"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=20,
    )
    (tmp_path / "driver.log").write_text(run.stdout + run.stderr)
    assert run.returncode == 0, run.stdout + run.stderr


def test_exact_completed_source_review_and_controller(tmp_path, monkeypatch):
    cases = []
    for label, phase, reviewed in [
        ("source", "source", False),
        ("source-reviewed", "source", True),
        ("extract", "extract", False),
    ]:
        value = prepare(tmp_path / label, phase, monkeypatch, reviewed=reviewed)
        store, settings, original, _ = value
        try:
            with TestClient(create_app(store, settings)) as client:
                locator = readonly(value, lambda original=original: read(client, original))
                current = readonly(
                    value,
                    lambda original=original: client.get(
                        f"/api/projects/{original['project']}/protocol/runs/{original['run']}",
                        headers=HEADERS,
                    ),
                )
            assert locator.status_code == current.status_code == 200
            if reviewed:
                assert (
                    current.json()["status"] == "SUCCEEDED"
                    and current.json()["semantic_status"] == "PASS"
                )
                assert locator.json()["receipt"]["status"] == "WAITING_APPROVAL"
                assert current.json()["version"] == locator.json()["receipt"]["version"] + 1
            cases.append(dict(label=label, locator=locator.json(), run=current.json()))
        finally:
            store.engine.dispose()
    (tmp_path / "cases.json").write_text(json.dumps(cases, indent=2))
    run = subprocess.run(
        ["node", "tests/protocol_completion_readback.cjs", str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=20,
    )
    (tmp_path / "readback-driver.log").write_text(run.stdout + run.stderr)
    assert run.returncode == 0, run.stdout + run.stderr
    unknown = subprocess.run(
        ["node", "tests/protocol_completion_readback.cjs", str(tmp_path), "unknown"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=20,
    )
    (tmp_path / "unknown-driver.log").write_text(unknown.stdout + unknown.stderr)
    assert unknown.returncode == 0, unknown.stdout + unknown.stderr


def test_local_authenticated_tcp_get_and_owned_cleanup(sealed):
    store, settings, original, sidecar = sealed
    owned_before = set(threading.enumerate())
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(create_app(store, settings), log_level="error"))
    worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]})
    until = time.monotonic() + 5
    worker.start()
    try:
        while not server.started and worker.is_alive() and time.monotonic() < until:
            threading.Event().wait(0.01)
        assert server.started
        with httpx.Client(
            base_url=f"http://127.0.0.1:{listener.getsockname()[1]}", timeout=3
        ) as client:
            response = readonly(sealed, lambda: read(client, original))
        assert response.status_code == 200 and response.json()["state"] == "FOUND"
    finally:
        server.should_exit = True
        cleanup_until = time.monotonic() + 3
        worker.join(max(0, cleanup_until - time.monotonic()))
        listener.close()
        owned = [
            t
            for t in threading.enumerate()
            if t not in owned_before and t.name == "AnyIO worker thread"
        ]
        for t in owned:
            t.join(max(0, cleanup_until - time.monotonic()))
        receipt = dict(
            api_stopped=not worker.is_alive(),
            owned_anyio_alive=[t.name for t in owned if t.is_alive()],
            within_deadline=time.monotonic() <= cleanup_until,
            forced_stop=False,
        )
        (sidecar.parent / "tcp-cleanup.json").write_text(json.dumps(receipt, indent=2))
        assert (
            receipt["api_stopped"]
            and not receipt["owned_anyio_alive"]
            and receipt["within_deadline"]
        )
