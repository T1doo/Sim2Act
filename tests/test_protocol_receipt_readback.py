"""Accepted review discovery from sealed facts: no new business command/send.

ASGI + new Store connections and controller VM, not native DOM or OS restart.
"""

import copy
import gzip
import hashlib
import json
import subprocess
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from protocol_pg_sealed import capture, digest, read_sealed
from sqlalchemy import delete, event, insert, select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, events, grants, projects, protocol_jobs, protocol_reviews, runs
from sim2act.model import InternModel
from sim2act.model_budget import BudgetedProvider
from sim2act.worker import Worker

REPO = Path(__file__).parents[1]
COLD = REPO / "docs/evidence/protocol-cold-review-http-20261022"
HEADERS = {"Authorization": "Bearer secret test token"}


def state(store):
    with store.engine.connect() as c:
        return digest(capture(c))


@pytest.fixture
def sealed(tmp_path, monkeypatch):
    fixture, path = read_sealed(tmp_path)
    manifest = json.loads((COLD / "MANIFEST.json").read_text())
    archive = (COLD / "runtime/after.sqlite.gz").read_bytes()
    witness = manifest["runtime/after.sqlite.gz"]
    assert (
        len(archive) == witness["bytes"]
        and hashlib.sha256(archive).hexdigest() == witness["sha256"]
    )
    path.write_bytes(gzip.decompress(archive))
    url = "sqlite:///" + str(path)
    store = Store(url, test_only=True)
    settings = Settings(database_url=url, data_dir=tmp_path, **fixture["api_settings"])
    monkeypatch.setattr(time, "time", lambda: fixture["business_at"])
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("new business work")
        raise AssertionError("Receipt discovery cannot write commands, send, claim or accept")

    for owner, name in [
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (BudgetedProvider, "call"),
        (BudgetedProvider, "preflight"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "__init__"),
        (Worker, "reserve"),
        (Store, "claim"),
        (Store, "event"),
    ]:
        monkeypatch.setattr(owner, name, forbidden)
    sidecars = {n: (tmp_path / n).read_bytes() for n in fixture["sidecars"]}
    try:
        yield store, settings, fixture
    finally:
        assert calls == [] and all(
            (tmp_path / n).read_bytes() == raw for n, raw in sidecars.items()
        )
        store.engine.dispose()


def read(client, fixture, rid=None, pid=None, headers=HEADERS):
    return client.get(
        f"/api/projects/{pid or fixture['project']}/protocol/runs/{rid or fixture['run']}/review-receipt",
        headers=headers,
    )


def assert_readonly(store, operation):
    before, verbs = state(store), []

    def trace(_c, _cur, sql, _params, _context, _many):
        verbs.append(sql.lstrip().split(None, 1)[0].upper())

    event.listen(store.engine, "before_cursor_execute", trace)
    try:
        result = operation()
    finally:
        event.remove(store.engine, "before_cursor_execute", trace)
    assert state(store) == before
    assert set(verbs) <= {"SELECT", "BEGIN"}
    return result


@pytest.mark.parametrize("phase", ["source", "cold"])
def test_accepted_review_readback_new_store_exact_original_no_writes(sealed, tmp_path, phase):
    store, settings, fixture = sealed
    rid = fixture["source_run"] if phase == "source" else fixture["run"]
    with store.engine.connect() as c:
        row = (
            c.execute(select(protocol_reviews).where(protocol_reviews.c.run_id == rid))
            .mappings()
            .one()
        )
        expected = copy.deepcopy(row["payload"]["request"])
    with TestClient(create_app(store, settings)) as client:
        response = assert_readonly(store, lambda: read(client, fixture, rid))
    assert response.status_code == 200
    value = response.json()
    assert set(value) == {"namespace", "run_id", "phase", "state", "request", "receipt"}
    assert value["request"] == expected and value["state"] == "FOUND" and value["phase"] == phase
    assert (
        value["receipt"]["fingerprint"] == row["fingerprint"]
        and value["receipt"]["id"] == row["id"]
    )
    assert set(value["receipt"]) == {
        "id",
        "run_id",
        "contract_id",
        "namespace",
        "decision",
        "reason",
        "fingerprint",
        "publishable",
        "model_requests",
    }
    assert value["receipt"]["publishable"] is False and value["receipt"]["model_requests"] == 0
    # New Store/API instance, no runner; not an OS process restart.
    fresh = Store(settings.database_url, test_only=True)
    try:
        with TestClient(create_app(fresh, settings)) as client:
            again = assert_readonly(fresh, lambda: read(client, fixture, rid))
        assert again.content == response.content
    finally:
        fresh.engine.dispose()
    (tmp_path / "readback.json").write_text(json.dumps(value, indent=2))


@pytest.mark.parametrize(
    "fault", ["missing_row", "missing_seal", "seal", "payload", "content", "ambiguous", "revoked"]
)
def test_incomplete_tampered_or_revoked_acceptance_is_not_missing(sealed, fault):
    store, settings, fixture = sealed
    rid = fixture["run"]
    with store.tx() as c:
        where = (events.c.run_id == rid) & (events.c.kind == "PROTOCOL_REVIEW")
        if fault == "missing_row":
            c.execute(delete(protocol_reviews).where(protocol_reviews.c.run_id == rid))
        elif fault == "missing_seal":
            c.execute(delete(events).where(where))
        elif fault == "seal":
            c.execute(update(events).where(where).values(data={"review_id": "not-original"}))
        elif fault == "payload":
            c.execute(
                update(protocol_reviews).where(protocol_reviews.c.run_id == rid).values(payload={})
            )
        elif fault == "content":
            c.execute(
                update(protocol_jobs)
                .where(protocol_jobs.c.run_id == rid)
                .values(result_snapshot={})
            )
        elif fault == "ambiguous":
            row = dict(
                c.execute(select(protocol_reviews).where(protocol_reviews.c.run_id == rid))
                .mappings()
                .one()
            )
            row.update(id="review_" + "f" * 32, request_key="different-key")
            c.execute(insert(protocol_reviews).values(**row))
        else:
            c.execute(update(grants).values(revoked=True))
    with TestClient(create_app(store, settings)) as client:
        response = assert_readonly(store, lambda: read(client, fixture))
    assert response.status_code in {403, 409, 422}
    assert "request_key" not in response.text


def test_no_record_is_explicit_not_proof_of_no_submission(sealed):
    store, settings, fixture = sealed
    with store.tx() as c:
        c.execute(delete(protocol_reviews).where(protocol_reviews.c.run_id == fixture["run"]))
        c.execute(
            delete(events).where(
                events.c.run_id == fixture["run"], events.c.kind == "PROTOCOL_REVIEW"
            )
        )
        c.execute(
            update(runs)
            .where(runs.c.id == fixture["run"])
            .values(status="WAITING_APPROVAL", version=2)
        )
    with TestClient(create_app(store, settings)) as client:
        response = assert_readonly(store, lambda: read(client, fixture))
    assert response.status_code == 200
    assert response.json()["state"] == "NOT_FOUND"
    assert response.json()["request"] is response.json()["receipt"] is None


def test_identity_project_and_phase_isolation(sealed):
    store, settings, fixture = sealed
    # Another project of this same authenticated owner passes own_project, but
    # cannot be used as a locator path for the original Run.
    with store.tx() as c:
        row = dict(
            c.execute(select(projects).where(projects.c.id == fixture["project"])).mappings().one()
        )
        row["id"] = "proj_other_owned"
        c.execute(insert(projects).values(**row))
    with TestClient(create_app(store, settings)) as client:
        for kwargs in [
            dict(headers={}),
            dict(headers={"Authorization": "Bearer invalid"}),
            dict(pid="proj_wrong"),
            dict(pid="proj_other_owned"),
            dict(rid=fixture["extraction_run"]),
        ]:
            response = assert_readonly(store, lambda kwargs=kwargs: read(client, fixture, **kwargs))
            assert response.status_code in {401, 403, 409, 422}
            assert "request_key" not in response.text


def test_cold_page_controller_recovers_only_by_get(sealed, tmp_path):
    store, settings, fixture = sealed
    data = []
    with TestClient(create_app(store, settings)) as client:
        for rid in [fixture["source_run"], fixture["run"]]:
            value = assert_readonly(store, lambda rid=rid: read(client, fixture, rid)).json()
            run = client.get(
                f"/api/projects/{fixture['project']}/protocol/runs/{rid}", headers=HEADERS
            ).json()
            data.append(dict(locator=value, run=run))
    (tmp_path / "cases.json").write_text(json.dumps(data))
    result = subprocess.run(
        ["node", "tests/protocol_receipt_readback.cjs", str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    (tmp_path / "controller.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
