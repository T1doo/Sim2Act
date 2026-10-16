"""Real synthetic HTTP/Worker + JSDOM Blob bytes; not PG/native file download."""

import hashlib
import json
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


@pytest.mark.parametrize("case", ["versions-and-rejections", "navigation", "revocation"])
def test_csv_run_download_actual_http_and_dom(env, tmp_path, case):
    if not shutil.which("node") or subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
    ).returncode:
        pytest.fail("This engineering acceptance requires installed Node/jsdom")
    store, settings, client, owner, other_owner, project, _ = env
    assert store.sqlite and settings.mode == "mock"  # Explicit synthetic scope, never PG evidence.
    material = client.post(f"/api/projects/{project}/resources", json={
        "name": "synthetic-private.csv", "format": "csv",
        "content": "amount,tax,memo\n9007199254740993.123456789,0.1,PRIVATE_SYNTHETIC_ROW\n0.000000001,0.2,x\n",
    }).json()["id"]
    aid = client.post(f"/api/projects/{project}/apps/csv-preview", json={
        "name": "Download synthetic sum", "resource_id": material, "goal": "Exact sum",
    }).json()["id"]
    fp = client.get(f"/api/apps/{aid}").json()["fingerprint"]
    saved, _, _ = release(env, aid, fp)
    current, other_instance = instance(env, saved), instance(env, saved, "other")
    run_ids, outputs = [], []
    for column in ("amount", "tax", "memo"):
        response = enqueue(env, current, saved, key=column, column=column)
        assert response.status_code == 202, response.text
        rid = response.json()["run_id"]
        assert Worker(store, settings, NoModel()).once()
        result = client.get(f"/api/internal/instances/{current['id']}/runs/{rid}")
        assert result.status_code == 200, result.text
        run_ids.append(rid)
        outputs.append(result.json())
    assert [r["status"] for r in outputs] == ["SUCCEEDED", "SUCCEEDED", "FAILED"]
    assert [r["result_version"] for r in outputs] == [1, 2, None]
    assert outputs[0]["result"]["sum"] == "9007199254740993.123456790"
    assert outputs[1]["result"]["sum"] == "0.3"
    other_project = store.project(owner, "Other owned project")
    store.project(other_owner, "Other identity project")
    before = snapshot(store)
    revocations = []
    with store.tx() as connection:
        grant = dict(connection.execute(select(grants).where(
            grants.c.project_id == project, grants.c.principal_id == owner,
            grants.c.resource_id == material, grants.c.tool_ref == "resource.read",
        )).mappings().one())
    app = create_app(store, settings)

    @app.post("/test-only-revoke")
    def revoke(authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A" and not revocations
        response = client.post(f"/api/grants/{grant['id']}/revoke", json={
            "command": "revoke", "version": grant["revision"],
        })
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
    info = dict(base=f"http://127.0.0.1:{port}", case=case, project=project, other=other_project,
                app=aid, instance=current["id"], other_instance=other_instance["id"], runs=run_ids,
                outputs=outputs, web_hashes={name: hashlib.sha256((web / name).read_bytes()).hexdigest()
                    for name in ("app.js", "internal.js", "protocol.js", "use.js")})
    (tmp_path / "info.json").write_text(json.dumps(info))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        child = subprocess.run(["node", "tests/csv_run_download.cjs", str(tmp_path)],
                               capture_output=True, text=True, timeout=75)
        (tmp_path / "driver.log").write_text(child.stdout + child.stderr)
        assert child.returncode == 0, child.stdout + child.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and proof["browser_download"] == "NOT_RUN"
        after = snapshot(store)
        assert after == (revocations[0] if case == "revocation" else before)
        assert len(revocations) == int(case == "revocation")
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "backend": "SQLite synthetic only", "tables": len(before),
            "before_sha256": digest(before), "after_sha256": digest(after),
            "download_get_rows_unchanged": True,
            "controlled_revoke_only": case == "revocation",
            "after_revoke_sha256": digest(revocations[0]) if revocations else None,
            "row_counts": {name: len(rows) for name, rows in after.items()},
            "model_requests": 0, "pg": "NOT_RUN", "native_browser": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
