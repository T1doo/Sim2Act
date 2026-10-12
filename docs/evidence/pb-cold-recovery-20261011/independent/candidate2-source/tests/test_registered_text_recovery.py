"""Protected original-key journal, actual SQLite/API, cold Store and commit races."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, update
from test_registered_text_extraction import prepared, request, snapshot

from sim2act.api import create_app
from sim2act.db import Store, grants, runs, task_extractions
from sim2act.db import registered_extraction_requests as journal
from sim2act.errors import DomainError


def ready(env):
    values = prepared(env)
    data, _, _, _, _, target, _, url = values
    _, body = request(data, url, target)
    return values, body


def close_body(client, url):
    row = client.get(url + "/extraction-requests").json()["latest"]
    return {
        "request_key": row["request_key"],
        "expected_latest_key": row["request_key"],
        "expected_request_fingerprint": row["request_fingerprint"],
    }


def prepare_body(body, prior=None):
    return {
        **body,
        "expected_latest_key": prior["request_key"] if prior else None,
        "expected_latest_candidate_fingerprint": prior["candidate_fingerprint"]
        if prior and prior["state"] == "COMMITTED"
        else None,
    }


def test_prepared_original_request_is_discovered_by_cold_authenticated_get(env):
    values, body = ready(env)
    data, _, _, instance, run, _, _, url = values
    before = snapshot(data[0])
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            index = client.get(url + "/extraction-requests")
            assert index.status_code == 200, index.text
            latest = index.json()["latest"]
            assert latest["request_key"] == body["request_key"]
            assert latest["instance_id"] == instance["id"]
            assert latest["source_run_id"] == run["id"]
            assert latest["state"] == "PREPARED"
            assert "request" not in latest and body["name"] not in index.text
            protected = client.get(
                url + "/extraction-requests", params={"request_key": body["request_key"]}
            )
            assert protected.status_code == 200
            assert protected.json()["request"] == {
                "instance_id": instance["id"],
                "source_run_id": run["id"],
                **body,
            }
            assert protected.headers["cache-control"] == "no-store"
            assert index.headers["cache-control"] == "no-store"
            assert (
                client.get(
                    url + "/extraction-receipts", params={"request_key": body["request_key"]}
                ).status_code
                == 400
            )
    finally:
        cold.engine.dispose()
    assert snapshot(data[0]) == before


def test_committed_lost_response_cold_reads_preserve_single_effect_and_original_rows(env):
    values, body = ready(env)
    data, _, _, instance, run, _, _, url = values
    baseline = snapshot(data[0])
    result = data[2].post(url + "/extract", json=body)
    assert result.status_code == 201, result.text
    before = snapshot(data[0])
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            project = client.get(f"/api/projects/{data[4]}/registered-text-requests")
            assert project.status_code == 200 and project.headers["cache-control"] == "no-store"
            assert len(project.json()["items"]) == 1
            meta = project.json()["items"][0]
            assert meta["state"] == "COMMITTED" and "request" not in meta
            keyed = client.get(
                url + "/extraction-requests", params={"request_key": meta["request_key"]}
            )
            assert keyed.status_code == 200
            for _ in range(2):
                saved = client.get(
                    url + "/extraction-receipts", params={"request_key": meta["request_key"]}
                )
                assert saved.status_code == 200 and saved.json()["id"] == result.json()["id"]
                assert saved.json()["request_fingerprint"] == meta["request_fingerprint"]
            assert client.get("/api/apps/" + meta["app_id"]).status_code == 200
    finally:
        cold.engine.dispose()
    assert snapshot(data[0]) == before
    for table, rows in baseline.items():
        if table not in {"app_drafts", "task_extractions", "registered_extraction_requests"}:
            assert before[table] == rows, table
    assert [h["state"] for h in before["registered_extraction_requests"][0]["history"]] == [
        "PREPARED",
        "COMMITTED",
    ]


def test_bare_new_text_post_and_wrong_same_key_cannot_bypass_journal(env):
    values, body = ready(env)
    data, *_, url = values
    before = snapshot(data[0])
    for changed in (
        {**body, "request_key": "unprepared-new-key"},
        {**body, "name": "changed intent"},
    ):
        assert data[2].post(url + "/extract", json=changed).status_code == 409
    assert (
        data[2]
        .post(url + "/extraction-requests", json=prepare_body({**body, "name": "different"}))
        .status_code
        == 409
    )
    assert snapshot(data[0]) == before


def test_closed_high_watermark_rejects_late_post_prepare_and_allows_explicit_new_key(env):
    values, body = ready(env)
    data, *_, url = values
    closed = data[2].post(url + "/extraction-request-close", json=close_body(data[2], url))
    assert closed.status_code == 200 and closed.json()["state"] == "CLOSED"
    before = snapshot(data[0])
    assert data[2].post(url + "/extract", json=body).status_code == 409
    assert data[2].post(url + "/extraction-requests", json=prepare_body(body)).status_code == 409
    new = {**body, "request_key": "explicit-new-key", "name": "New explicit request"}
    assert data[2].post(url + "/extraction-requests", json=prepare_body(new)).status_code == 409
    assert snapshot(data[0]) == before
    created = data[2].post(url + "/extraction-requests", json=prepare_body(new, closed.json()))
    assert created.status_code == 201 and created.json()["sequence"] == 2
    assert data[2].post(url + "/extract", json=body).status_code == 409
    assert data[2].post(url + "/extract", json=new).status_code == 201
    with data[0].tx() as c:
        records = list(c.execute(select(task_extractions)).mappings())
        assert len(records) == 1 and records[0]["request_key"] == new["request_key"]


def test_committed_cannot_close_and_new_request_revalidates_previous_candidate(env):
    values, body = ready(env)
    data, *_, url = values
    result = data[2].post(url + "/extract", json=body).json()
    before = snapshot(data[0])
    meta = data[2].post(url + "/extraction-request-close", json=close_body(data[2], url)).json()
    assert meta["state"] == "COMMITTED" and snapshot(data[0]) == before
    new = {**body, "request_key": "next-explicit-key"}
    assert data[2].post(url + "/extraction-requests", json=prepare_body(new)).status_code == 409
    assert (
        data[2]
        .post(
            url + "/extraction-requests",
            json={**prepare_body(new, meta), "expected_latest_candidate_fingerprint": "0" * 64},
        )
        .status_code
        == 409
    )
    assert snapshot(data[0]) == before
    accepted = data[2].post(url + "/extraction-requests", json=prepare_body(new, meta))
    assert accepted.status_code == 201
    second = data[2].post(url + "/extract", json=new)
    assert second.status_code == 201 and second.json()["id"] != result["id"]
    assert (
        data[2]
        .get(url + "/extraction-receipts", params={"request_key": body["request_key"]})
        .json()["id"]
        == result["id"]
    )


def test_concurrent_new_prepare_cas_has_one_winner(env):
    values, body = ready(env)
    data, *_, url = values
    prior = data[2].post(url + "/extraction-request-close", json=close_body(data[2], url)).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(
                lambda key: data[2].post(
                    url + "/extraction-requests",
                    json=prepare_body({**body, "request_key": key}, prior),
                ),
                ["new-A", "new-B"],
            )
        )
    assert sorted(r.status_code for r in replies) == [201, 409]
    latest = data[2].get(url + "/extraction-requests").json()["latest"]
    assert latest["sequence"] == 2 and latest["previous_key"] == body["request_key"]


def test_concurrent_close_and_extract_have_one_atomic_outcome(env):
    values, body = ready(env)
    data, *_, url = values
    closing = close_body(data[2], url)
    with ThreadPoolExecutor(max_workers=2) as pool:
        extraction = pool.submit(data[2].post, url + "/extract", json=body)
        closure = pool.submit(data[2].post, url + "/extraction-request-close", json=closing)
        made, closed = extraction.result(), closure.result()
    assert closed.status_code == 200
    with data[0].tx() as c:
        row = c.execute(select(journal)).mappings().one()
        effects = list(c.execute(select(task_extractions)).mappings())
    if made.status_code == 201:
        assert closed.json()["state"] == row["state"] == "COMMITTED" and len(effects) == 1
    else:
        assert (
            made.status_code == 409
            and closed.json()["state"] == row["state"] == "CLOSED"
            and effects == []
        )


def test_commit_journal_update_failure_rolls_back_app_and_receipt(env):
    values, body = ready(env)
    data, *_, url = values
    before = snapshot(data[0])

    def fail(conn, cursor, sql, args, context, many):
        if sql.startswith("UPDATE registered_extraction_requests"):
            raise DomainError("VERSION_CONFLICT", "Controlled third-write journal failure")

    event.listen(data[0].engine, "before_cursor_execute", fail)
    try:
        assert data[2].post(url + "/extract", json=body).status_code == 409
    finally:
        event.remove(data[0].engine, "before_cursor_execute", fail)
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("scope", ["foreign-owner", "foreign-project", "wrong-instance"])
def test_request_routes_reject_before_foreign_private_run_or_request_cells(env, tmp_path, scope):
    from sql_private_barrier import PrivateReadBarrier

    values, body = ready(env)
    data, _, _, instance, run, _, resource, url = values
    foreign = (
        data[2]
        .post(
            "/api/projects",
            headers={"Authorization": "Bearer synthetic-test-B"},
            json={"name": "foreign"},
        )
        .json()["id"]
    )
    if scope == "foreign-owner":
        data[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif scope == "foreign-project":
        with data[0].tx() as c:
            c.execute(update(runs).where(runs.c.id == run["id"]).values(project_id=foreign))
    else:
        url = url.replace(instance["id"], "instance_" + "0" * 32)
    before = snapshot(data[0])
    barrier = PrivateReadBarrier(data[0], {run["id"]}, {data[5], resource})
    barrier.rules["registered_extraction_requests"] = (
        journal,
        "request_key",
        {body["request_key"]},
        {"request"},
    )
    with barrier:
        for method, path, payload in [
            ("GET", url + "/extraction-requests", None),
            ("GET", url + "/extraction-requests?request_key=" + body["request_key"], None),
            ("POST", url + "/extraction-requests", prepare_body(body)),
            (
                "POST",
                url + "/extraction-request-close",
                {
                    "request_key": body["request_key"],
                    "expected_latest_key": body["request_key"],
                    "expected_request_fingerprint": before["registered_extraction_requests"][0][
                        "request_fingerprint"
                    ],
                },
            ),
        ]:
            response = data[2].request(method, path, json=payload)
            assert response.status_code == 403, response.text
        if scope == "foreign-owner":
            assert (
                data[2].get(f"/api/projects/{data[4]}/registered-text-requests").status_code == 403
            )
    assert not barrier.blocked and not barrier.evaluated
    assert snapshot(data[0]) == before
    (tmp_path / "private-gate-proof.json").write_text(
        json.dumps(
            {
                "scope": scope,
                "sql": barrier.statements,
                "blocked": barrier.blocked,
                "evaluated": barrier.evaluated,
            },
            indent=2,
        )
    )


@pytest.mark.parametrize("domain", ["source", "target"])
def test_revoked_recovery_reads_no_journal_body_but_metadata_close_remains_available(
    env, tmp_path, domain
):
    from sql_private_barrier import PrivateReadBarrier

    values, body = ready(env)
    data, source, _, _, run, target, resource, url = values
    closing = close_body(data[2], url)
    runtime = (
        data[2].get("/api/apps/" + (source if domain == "source" else target)).json()["runtime_id"]
    )
    with data[0].tx() as c:
        grant = (
            c.execute(
                select(grants).where(grants.c.principal_id == runtime, grants.c.revoked.is_(False))
            )
            .mappings()
            .one()
        )
    assert (
        data[2]
        .post(
            "/api/grants/" + grant["id"] + "/revoke",
            json={"command": "revoke", "version": grant["revision"]},
        )
        .status_code
        == 200
    )
    before = snapshot(data[0])
    barrier = PrivateReadBarrier(data[0], set())
    barrier.rules["registered_extraction_requests"] = (
        journal,
        "request_key",
        {body["request_key"]},
        {"request"},
    )
    with barrier:
        denied = data[2].get(
            url + "/extraction-requests", params={"request_key": body["request_key"]}
        )
        assert denied.status_code == 403, denied.text
    assert not barrier.blocked and not any(
        r["table"] == "registered_extraction_requests" for r in barrier.evaluated
    )
    assert snapshot(data[0]) == before
    closing_barrier = PrivateReadBarrier(data[0], {run["id"]}, {data[5], resource})
    closing_barrier.rules["registered_extraction_requests"] = (
        journal,
        "request_key",
        {body["request_key"]},
        {"request"},
    )
    with closing_barrier:
        index = data[2].get(f"/api/projects/{data[4]}/registered-text-requests")
        assert index.status_code == 200 and body["name"] not in index.text
        closed = data[2].post(url + "/extraction-request-close", json=closing)
        assert closed.status_code == 200 and closed.json()["state"] == "CLOSED"
    assert not closing_barrier.blocked and not closing_barrier.evaluated
    (tmp_path / "revoked-close-proof.json").write_text(
        json.dumps(
            {
                "domain": domain,
                "read_sql": barrier.statements,
                "close_sql": closing_barrier.statements,
                "close_private_evaluations": closing_barrier.evaluated,
            },
            indent=2,
        )
    )


@pytest.mark.parametrize("field", ["request", "state", "history"])
def test_corrupt_request_journal_cannot_install_or_start_new_request(env, field):
    values, body = ready(env)
    data, *_, url = values
    with data[0].tx() as c:
        row = c.execute(select(journal)).mappings().one()
        changed = copy.deepcopy(row[field])
        if field == "request":
            changed["name"] = "polluted secret request"
        elif field == "state":
            changed = "CLOSED"
        else:
            changed.append({"state": "COMMITTED", "at": 1})
        c.execute(update(journal).values(**{field: changed}))
    before = snapshot(data[0])
    for method, path, payload in [
        ("GET", url + "/extraction-requests?request_key=" + body["request_key"], None),
        ("POST", url + "/extract", body),
        ("POST", url + "/extraction-requests", prepare_body({**body, "request_key": "new"})),
    ]:
        reply = data[2].request(method, path, json=payload)
        assert reply.status_code == 409, reply.text
    assert snapshot(data[0]) == before


def test_legacy_committed_original_key_stays_read_only_without_journal_backfill(env):
    from sqlalchemy import delete

    values, body = ready(env)
    data, *_, url = values
    made = data[2].post(url + "/extract", json=body)
    assert made.status_code == 201
    # Controlled legacy persisted shape only; this does not execute an old source upgrade.
    with data[0].tx() as c:
        c.execute(delete(journal))
    before = snapshot(data[0])
    saved = data[2].get(url + "/extraction-receipts", params={"request_key": body["request_key"]})
    assert saved.status_code == 200 and saved.json()["id"] == made.json()["id"]
    assert data[2].post(url + "/extraction-requests", json=prepare_body(body)).status_code == 409
    assert data[2].post(url + "/extract", json=body).status_code == 409
    assert data[2].get(url + "/extraction-requests").json()["latest"] is None
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("field", ["instance_id", "source_app_id"])
def test_project_index_checks_actual_binding_before_returning_opaque_recovery_item(
    env, tmp_path, field
):
    from sql_private_barrier import PrivateReadBarrier

    from sim2act.db import (
        internal_app_runs,
        internal_instances,
        internal_releases,
        internal_run_bindings,
    )

    values, body = ready(env)
    data, _, release, instance, run, target, resource, url = values
    with data[0].tx() as c:
        c.execute(
            update(journal).values(
                **{field: target if field == "source_app_id" else "instance_" + "0" * 32}
            )
        )
    before = snapshot(data[0])
    barrier = PrivateReadBarrier(data[0], {run["id"]}, {data[5], resource})
    barrier.rules["registered_extraction_requests"] = (
        journal,
        "request_key",
        {body["request_key"]},
        {"request"},
    )
    barrier.rules["internal_run_bindings"] = (
        internal_run_bindings,
        "run_id",
        {run["id"]},
        {"snapshot"},
    )
    barrier.rules["internal_releases"] = (internal_releases, "id", {release["id"]}, {"snapshot"})
    barrier.rules["internal_instances"] = (
        internal_instances,
        "id",
        {instance["id"]},
        {"data", "history"},
    )
    barrier.rules["internal_app_runs"] = (
        internal_app_runs,
        "id",
        {run["app_run_id"]},
        {"input", "output", "error"},
    )
    with barrier:
        response = data[2].get(f"/api/projects/{data[4]}/registered-text-requests")
        assert response.status_code == 409, response.text
    assert not barrier.blocked and not barrier.evaluated
    assert snapshot(data[0]) == before
    (tmp_path / "metadata-binding-proof.json").write_text(
        json.dumps(
            {
                "field": field,
                "sql": barrier.statements,
                "evaluated": barrier.evaluated,
                "blocked": barrier.blocked,
            },
            indent=2,
        )
    )


def test_install_receipt_requires_latest_while_old_committed_history_remains_readable(env):
    values, body = ready(env)
    data, *_, url = values
    made = data[2].post(url + "/extract", json=body).json()
    meta = data[2].get(url + "/extraction-requests").json()["latest"]
    saved = data[2].get(
        url + "/extraction-receipts",
        params={"request_key": body["request_key"], "require_latest": True},
    )
    assert saved.status_code == 200 and saved.json()["latest_verified"] is True
    assert saved.json()["journal_sequence"] == meta["sequence"]
    newer = {**body, "request_key": "newer-explicit-request"}
    assert (
        data[2].post(url + "/extraction-requests", json=prepare_body(newer, meta)).status_code
        == 201
    )
    before = snapshot(data[0])
    assert (
        data[2]
        .get(
            url + "/extraction-receipts",
            params={"request_key": body["request_key"], "require_latest": True},
        )
        .status_code
        == 409
    )
    old = data[2].get(url + "/extraction-receipts", params={"request_key": body["request_key"]})
    assert old.status_code == 200 and old.json()["id"] == made["id"]
    assert snapshot(data[0]) == before
