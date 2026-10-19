"""Real synthetic HTTP/Worker + JSDOM Blob bytes; not PG/native file download."""

import hashlib
import json
import re
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi import Header
from sqlalchemy import select
from test_internal_api import enqueue, instance, release
from test_persistent_app_runs import NoModel

from sim2act.api import create_app
from sim2act.db import grants, meta
from sim2act.worker import Worker


def snapshot(store):
    with store.tx() as connection:
        return {
            table.name: sorted(
                json.dumps(dict(row), sort_keys=True, default=str)
                for row in connection.execute(select(table)).mappings()
            )
            for table in meta.sorted_tables
        }


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


@pytest.fixture(autouse=True)
def fixture_http_evidence(env, tmp_path):
    raw = []

    def trace(response):
        response.read()
        request = response.request
        raw.append(
            dict(
                method=request.method,
                url=str(request.url),
                request_body=request.content.decode("utf-8") if request.content else None,
                status=response.status_code,
                response_text=response.text,
                response_headers=dict(response.headers),
            )
        )

    env[2].event_hooks["response"].append(trace)
    try:
        yield
    finally:
        env[2].event_hooks["response"].remove(trace)
        (tmp_path / "fixture-http.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


@pytest.mark.parametrize(
    "case", ["versions-and-rejections", "navigation", "revocation", "csv-format", "csv-boundaries"]
)
def test_csv_run_download_actual_http_and_dom(env, tmp_path, case):
    if (
        not shutil.which("node")
        or subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
        ).returncode
    ):
        pytest.fail("This engineering acceptance requires installed Node/jsdom")
    store, settings, client, owner, other_owner, project, _ = env
    assert store.sqlite and settings.mode == "mock"  # Explicit synthetic scope, never PG evidence.
    content = (
        "amount,tax,memo\n9007199254740993.123456789,0.1,PRIVATE_SYNTHETIC_ROW\n0.000000001,0.2,x\n"
    )
    if case.startswith("csv-"):
        content = 'amount,tax,memo,"财务,""净额""",=SUM(A1)\n9007199254740993.123456789,0.1,PRIVATE_SYNTHETIC_ROW,-1,2\n0.000000001,0.2,x,-2,3\n'
    material = client.post(
        f"/api/projects/{project}/resources",
        json={
            "name": "synthetic-private.csv",
            "format": "csv",
            "content": content,
        },
    ).json()["id"]
    aid = client.post(
        f"/api/projects/{project}/apps/csv-preview",
        json={
            "name": "Download synthetic sum",
            "resource_id": material,
            "goal": "Exact sum",
        },
    ).json()["id"]
    fp = client.get(f"/api/apps/{aid}").json()["fingerprint"]
    saved, _, _ = release(env, aid, fp)
    current, other_instance = instance(env, saved), instance(env, saved, "other")
    run_ids, outputs, worker_log = [], [], []
    for column in ("amount", "tax", "memo"):
        response = enqueue(env, current, saved, key=column, column=column)
        assert response.status_code == 202, response.text
        rid = response.json()["run_id"]
        worker = Worker(store, settings, NoModel())
        started = time.time()
        assert worker.once()
        worker_log.append(
            dict(
                worker_id=worker.id,
                run_id=rid,
                started_at=started,
                ended_at=time.time(),
                claimed=True,
            )
        )
        result = client.get(f"/api/internal/instances/{current['id']}/runs/{rid}")
        assert result.status_code == 200, result.text
        run_ids.append(rid)
        outputs.append(result.json())
    assert [r["status"] for r in outputs] == ["SUCCEEDED", "SUCCEEDED", "FAILED"]
    assert [r["result_version"] for r in outputs] == [1, 2, None]
    assert outputs[0]["result"]["sum"] == "9007199254740993.123456790"
    assert outputs[1]["result"]["sum"] == "0.3"
    if case.startswith("csv-"):
        newer, _, _ = release(env, aid, fp)
        approved = client.post(
            f"/api/internal/instances/{current['id']}/switch-approvals",
            json=dict(
                target_release_id=newer["id"],
                expected_target_fingerprint=newer["fingerprint"],
                expected_revision=current["revision"],
            ),
        )
        assert approved.status_code == 201, approved.text
        approval = approved.json()
        switched = client.post(
            f"/api/internal/instances/{current['id']}/switch-approvals/{approval['id']}/commit",
            json=dict(fingerprint=approval["fingerprint"]),
        )
        assert switched.status_code == 200, switched.text
        current = {**current, **switched.json()}
        for column in ['财务,"净额"', "=SUM(A1)"]:
            response = enqueue(env, current, newer, key=column, column=column)
            assert response.status_code == 202, response.text
            rid = response.json()["run_id"]
            worker = Worker(store, settings, NoModel())
            started = time.time()
            assert worker.once()
            worker_log.append(
                dict(
                    worker_id=worker.id,
                    run_id=rid,
                    started_at=started,
                    ended_at=time.time(),
                    claimed=True,
                )
            )
            result = client.get(f"/api/internal/instances/{current['id']}/runs/{rid}")
            assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED", result.text
            run_ids.append(rid)
            outputs.append(result.json())
        assert outputs[0]["release_id"] != outputs[3]["release_id"]
        assert outputs[3]["result"]["sum"] == "-3" and outputs[4]["result"]["sum"] == "5"
    other_project = store.project(owner, "Other owned project")
    store.project(other_owner, "Other identity project")
    before = snapshot(store)
    (tmp_path / "database-before-page.json").write_text(json.dumps(before, indent=2) + "\n")
    (tmp_path / "worker-log.json").write_text(json.dumps(worker_log, indent=2) + "\n")
    revocations = []
    with store.tx() as connection:
        grant = dict(
            connection.execute(
                select(grants).where(
                    grants.c.project_id == project,
                    grants.c.principal_id == owner,
                    grants.c.resource_id == material,
                    grants.c.tool_ref == "resource.read",
                )
            )
            .mappings()
            .one()
        )
    app = create_app(store, settings)

    @app.post("/test-only-revoke")
    def revoke(authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A" and not revocations
        response = client.post(
            f"/api/grants/{grant['id']}/revoke",
            json={
                "command": "revoke",
                "version": grant["revision"],
            },
        )
        assert response.status_code == 200, response.text
        after_revoke = snapshot(store)
        assert all(before[name] == rows for name, rows in after_revoke.items() if name != "grants")
        assert before["grants"] != after_revoke["grants"]
        revocations.append(after_revoke)
        return {"status": "REVOKED"}

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    web = Path("src/sim2act/web")
    asset_names = [
        "index.html",
        "app.css",
        *re.findall(r'<script[^>]+src="/([^"]+)"', (web / "index.html").read_text()),
    ]
    info = dict(
        base=f"http://127.0.0.1:{port}",
        case=case,
        project=project,
        other=other_project,
        app=aid,
        instance=current["id"],
        other_instance=other_instance["id"],
        runs=run_ids,
        outputs=outputs,
        web_hashes={
            name: hashlib.sha256((web / name).read_bytes()).hexdigest() for name in asset_names
        },
        current_release=current["release_id"],
    )
    (tmp_path / "info.json").write_text(json.dumps(info))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        child = subprocess.run(
            ["node", "tests/csv_run_download.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=75,
        )
        (tmp_path / "driver.log").write_text(child.stdout + child.stderr)
        assert child.returncode == 0, child.stdout + child.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and proof["browser_download"] == "NOT_RUN"
        after = snapshot(store)
        (tmp_path / "database-after-page.json").write_text(json.dumps(after, indent=2) + "\n")
        assert after == (revocations[0] if case in {"revocation", "csv-boundaries"} else before)
        assert len(revocations) == int(case in {"revocation", "csv-boundaries"})
        if case.startswith("csv-"):
            import csv
            import io

            for filename in proof.get("csv_files", []):
                raw = (tmp_path / filename).read_bytes()
                assert not raw.startswith(b"\xef\xbb\xbf") and raw.endswith(b"\r\n")
                parsed = list(csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True))
                assert (
                    parsed[0]
                    == [
                        "instance_id",
                        "run_id",
                        "release_id",
                        "result_version",
                        "resource_id",
                        "column",
                        "sum",
                        "count",
                    ]
                    and len(parsed) == 2
                )
                output = next(r for r in outputs if r["id"] == parsed[1][1])
                expected = [
                    current["id"],
                    output["id"],
                    output["release_id"],
                    str(output["result_version"]),
                    output["result"]["resource_id"],
                    output["result"]["column"],
                    output["result"]["sum"],
                    str(output["result"]["count"]),
                ]
                assert parsed[1] == expected
                target = io.StringIO(newline="")
                writer = csv.writer(target, lineterminator="\r\n")
                writer.writerows([parsed[0], expected])
                assert raw == target.getvalue().encode("utf-8")
        (tmp_path / "database-proof.json").write_text(
            json.dumps(
                {
                    "backend": "SQLite synthetic only",
                    "tables": len(before),
                    "before_sha256": digest(before),
                    "after_sha256": digest(after),
                    "download_get_rows_unchanged": True,
                    "controlled_revoke_only": case in {"revocation", "csv-boundaries"},
                    "after_revoke_sha256": digest(revocations[0]) if revocations else None,
                    "row_counts": {name: len(rows) for name, rows in after.items()},
                    "model_requests": 0,
                    "pg": "NOT_RUN",
                    "native_browser": "NOT_RUN",
                },
                indent=2,
            )
            + "\n"
        )
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
