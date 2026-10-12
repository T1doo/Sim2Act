"""Actual HTTP assets/API across two different Node processes and fresh Store/API."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from test_persistent_app_runs import NoModel
from test_registered_text_extraction import prepared, snapshot

from sim2act.api import create_app
from sim2act.db import Store, grants, task_extractions
from sim2act.db import registered_extraction_requests as journal
from sim2act.errors import DomainError
from sim2act.worker import Worker

SCENARIOS = [
    "lost-commit",
    "lost-prepare",
    "before-extract",
    "rolled-back",
    "late-prepare-ABA",
    "late-keyed-ABA",
    "late-discovery-ABA",
    "revoke-source",
    "revoke-target",
    "cross-owner",
    "cross-project",
    "explicit-new-committed",
    "explicit-new-closed",
    "before-prepare",
    "poison-journal-key",
    "poison-journal-body",
    "poison-project-source",
]


def page(client, store, settings, info, tmp_path):
    path = tmp_path / (info["phase"] + "-info.json")
    info["output"] = str(tmp_path / (info["phase"] + "-page.json"))
    path.write_text(json.dumps(info))
    process = subprocess.Popen(
        ["node", "tests/registered_text_recovery_ui.cjs", str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
    )
    worked = 0
    private_proofs = []
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "worker":
                cold_worker = Store(settings.database_url, test_only=True)
                try:
                    assert Worker(cold_worker, settings, NoModel()).once()
                    worked += 1
                finally:
                    cold_worker.engine.dispose()
                answer = {"id": request["id"], "status": 200, "text": "{}"}
            else:
                # The cold revoke discovery/stop path must evaluate no private Run/body cells.
                barrier = None
                if (
                    info["phase"] == "cold"
                    and info["scenario"] == "revoke-source"
                    and (
                        request["path"].endswith("/registered-text-requests")
                        or request["path"].endswith("/extraction-request-close")
                    )
                ):
                    from sql_private_barrier import PrivateReadBarrier

                    with store.tx() as c:
                        key = c.execute(select(journal.c.request_key)).scalar_one()
                    barrier = PrivateReadBarrier(store, {info["run"]})
                    barrier.rules["registered_extraction_requests"] = (
                        journal,
                        "request_key",
                        {key},
                        {"request"},
                    )
                    with barrier:
                        response = client.request(
                            request["method"],
                            request["path"],
                            json=request.get("body"),
                            headers=request.get("headers"),
                        )
                    assert not barrier.blocked and not barrier.evaluated
                    private_proofs.append(
                        {
                            "path": request["path"],
                            "sql": barrier.statements,
                            "blocked": barrier.blocked,
                            "evaluated": barrier.evaluated,
                        }
                    )
                else:
                    response = client.request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers"),
                    )
                answer = {
                    "id": request["id"],
                    "status": response.status_code,
                    "text": response.text,
                    "content_type": response.headers.get("content-type"),
                    "cache_control": response.headers.get("cache-control"),
                }
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        process.stdin.close()
        error = process.stderr.read()
        code = process.wait(timeout=20)
        output = os.environ.get("SIM2ACT_COLD_EVIDENCE_DIR")
        if output:
            target = Path(output)
            target.mkdir(parents=True, exist_ok=True)
            stem = info["scenario"] + "-" + info["phase"]
            (target / (stem + ".log")).write_text(error)
            (target / (stem + "-private.json")).write_text(json.dumps(private_proofs, indent=2))
            if Path(info["output"]).exists():
                (target / (stem + ".json")).write_bytes(Path(info["output"]).read_bytes())
        assert code == 0, error
        proof = json.loads(Path(info["output"]).read_text())
        assert proof["status"] == "PASS"
        assert all(row["visible"] and row["enabled"] for row in proof["actions"])
        assert len(proof["static_resource_loads"]) == 19
        web = Path(__file__).parents[1] / "src/sim2act/web"
        for name, digest in proof["loaded_source_sha256"].items():
            assert hashlib.sha256((web / name).read_bytes()).hexdigest() == digest
        mime = {"/": "text/html; charset=utf-8", "/app.css": "text/css; charset=utf-8"}
        assert all(
            row["content_type"] == mime.get(row["path"], "text/javascript; charset=utf-8")
            for row in proof["static_resource_loads"]
        )
        return proof, worked
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_text_request_cold_actual_http_new_process(env, tmp_path, scenario):
    data, source, _, instance, run, target, resource, url = prepared(env)
    store, settings, client, *_ = data
    initial = snapshot(store)
    info = {
        "project": data[4],
        "original_project": data[4],
        "source": source,
        "instance": instance["id"],
        "run": run["id"],
        "target": target,
        "resource": resource,
        "scenario": scenario,
        "phase": "first",
        "owner": "A",
    }

    def reject_commit(conn, cursor, sql, args, context, many):
        if sql.startswith("UPDATE registered_extraction_requests"):
            raise DomainError("VERSION_CONFLICT", "Controlled journal write rollback")

    if scenario == "rolled-back":
        event.listen(store.engine, "before_cursor_execute", reject_commit)
    try:
        first, count = page(client, store, settings, info, tmp_path)
        assert count == 0
    finally:
        if scenario == "rolled-back":
            event.remove(store.engine, "before_cursor_execute", reject_commit)
    first_key = next(
        r["body"]["request_key"]
        for r in first["requests"]
        if r["method"] == "POST" and r["path"].endswith("/extraction-requests")
    )
    with store.tx() as c:
        rows = list(c.execute(select(journal)).mappings())
    if scenario == "before-prepare":
        assert rows == []
    else:
        assert len(rows) == 1 and rows[0]["request_key"] == first_key
    if scenario in {"revoke-source", "revoke-target"}:
        draft = client.get(
            "/api/apps/" + (source if scenario == "revoke-source" else target)
        ).json()
        with store.tx() as c:
            grant = (
                c.execute(
                    select(grants).where(
                        grants.c.principal_id == draft["runtime_id"], grants.c.revoked.is_(False)
                    )
                )
                .mappings()
                .one()
            )
        response = client.post(
            "/api/grants/" + grant["id"] + "/revoke",
            json={"command": "revoke", "version": grant["revision"]},
        )
        assert response.status_code == 200, response.text
    if scenario in {"cross-owner", "cross-project"}:
        owner = "B" if scenario == "cross-owner" else "A"
        other = client.post(
            "/api/projects",
            headers={"Authorization": "Bearer synthetic-test-" + owner},
            json={"name": "other scope"},
        ).json()["id"]
        info["owner"] = owner
        info["project"] = other
    before_cold = snapshot(store)
    client.close()
    # Original frontend process is already exited; this API/Store has no previous object memory.
    cold = Store(settings.database_url, test_only=True)
    try:
        with TestClient(create_app(cold, settings)) as cold_client:
            info["phase"] = "cold"
            second, worked = page(cold_client, cold, settings, info, tmp_path)
    finally:
        cold.engine.dispose()
    assert first["process_id"] != second["process_id"]
    posts = [
        r for r in second["requests"] if r["method"] == "POST" and r["path"].endswith("/extract")
    ]
    new_scenarios = {"before-prepare", "explicit-new-closed", "explicit-new-committed"}
    assert len(posts) == (1 if scenario in new_scenarios else 0)
    if posts:
        assert posts[0]["body"]["request_key"] != first_key
    with store.tx() as c:
        effects = list(c.execute(select(task_extractions)).mappings())
        history = list(c.execute(select(journal).order_by(journal.c.sequence)).mappings())
    pending_only = {"lost-prepare", "before-extract", "rolled-back", "late-prepare-ABA"}
    if scenario in pending_only:
        assert effects == [] and history[0]["state"] == "PREPARED"
    elif scenario == "revoke-source":
        assert effects == [] and history[0]["state"] == "CLOSED"
    elif scenario == "explicit-new-committed":
        assert len(effects) == 2 and len(history) == 2
    else:
        assert len(effects) == 1
    should_work = scenario not in pending_only | {
        "revoke-source",
        "revoke-target",
        "cross-owner",
        "cross-project",
    }
    assert worked == (1 if should_work else 0)
    after = snapshot(store)
    assert after["principals"] == before_cold["principals"]
    assert after["grants"] == before_cold["grants"]
    # Every original row remains byte-equivalent, including owner declarations/old typed records.
    for table, rows in initial.items():
        for row in rows:
            if table == "grants" and scenario in {"revoke-source", "revoke-target"}:
                continue  # The test explicitly revokes this grant; history/data remain unchanged.
            assert row in after[table], table
    if scenario == "explicit-new-closed":
        assert history[0]["state"] == "CLOSED" and history[1]["previous_key"] == first_key
        assert data[2].is_closed
        with TestClient(create_app(store, settings)) as check_client:
            check_client.headers["Authorization"] = "Bearer synthetic-test-A"
            original = next(
                r["body"]
                for r in first["requests"]
                if r["method"] == "POST" and r["path"].endswith("/extraction-requests")
            )
            original.pop("expected_latest_key")
            original.pop("expected_latest_candidate_fingerprint")
            assert check_client.post(url + "/extract", json=original).status_code == 409
