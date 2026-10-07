"""One real served session interleaves all three integrated product slices."""

import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import select
from test_internal_lifecycle import limits, release

from sim2act.api import create_app
from sim2act.db import (
    app_drafts,
    attempts,
    grants,
    internal_app_runs,
    internal_instance_data,
    principals,
)
from sim2act.lifecycle import create_instance
from sim2act.worker import Worker


def test_integrated_same_session_source_and_recovery(env, tmp_path):
    if not shutil.which("node"):
        pytest.skip("Developer Node required for integrated HTTP/DOM oracle")
    if subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    ).returncode:
        pytest.skip("Developer jsdom required for integrated HTTP/DOM oracle")
    store, settings, client, owner, other_owner, project, original_resource = env
    resource = client.post(
        f"/api/projects/{project}/resources",
        json={
            "name": "integrated.csv",
            "format": "csv",
            "content": "amount,tax,memo\n5,1,x\n7,2,y\n",
        },
    ).json()["id"]
    appid = client.post(
        f"/api/projects/{project}/apps/csv-preview",
        json={
            "name": "Integrated synthetic sum",
            "resource_id": resource,
            "goal": "Integrated two numerical inputs",
        },
    ).json()["id"]
    with store.tx() as c:
        fp = c.execute(
            select(app_drafts.c.fingerprint).where(app_drafts.c.id == appid)
        ).scalar_one()
    rel, _, _ = release(env, appid, fp)
    instance = create_instance(
        store,
        owner,
        rel["id"],
        rel["fingerprint"],
        limits(env),
        request_key="integration-existing-instance",
    )
    first = client.post(
        f"/api/projects/{project}/runs",
        json={
            "goal": "Integrated persisted ordinary source",
            "resource_refs": [original_resource],
            "request_key": "integration-first",
        },
    ).json()["run_id"]
    assert Worker(store, settings).once()
    assert client.get("/api/runs/" + first).json()["status"] == "PARTIAL"
    other = store.project(owner, "Other owned project")
    foreign = store.project(other_owner, "Other identity project")

    def authority():
        with store.tx() as c:
            return {
                name: [dict(r) for r in c.execute(select(table)).mappings()]
                for name, table in [("grants", grants), ("principals", principals)]
            }

    before = authority()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            {
                "base": f"http://127.0.0.1:{port}",
                "project": project,
                "other": other,
                "foreignProject": foreign,
                "app": appid,
                "instance": instance["id"],
                "first": first,
                "resource": original_resource,
            }
        )
    )
    app = create_app(store, settings)

    @app.post("/test-only-worker")
    def work():
        class NoProvider:
            def complete(self, *_a, **_k):
                raise AssertionError("CSV oracle forbids model")

        assert store.test_only and settings.mode == "mock"
        assert Worker(store, settings, NoProvider()).once()
        return {"synthetic_only": True}

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < end
            time.sleep(0.01)
        result = subprocess.run(
            ["node", "tests/product_integration.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        received = json.loads((tmp_path / "results.json").read_text())
        assert received["status"] == "PASS" and len(received["checks"]) == 16
        assert authority() == before
        with store.tx() as c:
            ar = list(c.execute(select(internal_app_runs)).mappings())
            data = list(c.execute(select(internal_instance_data)).mappings())
            ats = list(c.execute(select(attempts)).mappings())
            assert len(ar) == 3 and len(data) == 2 and len(ats) == 2
            assert all(a["mode"] == "MOCK" and a["status"] == "RECEIVED" for a in ats)
        (tmp_path / "backend-proof.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "application_runs": len(ar),
                    "result_records": len(data),
                    "mock_attempts": len(ats),
                    "authority_rows_identical": True,
                    "real_model_requests": 0,
                },
                indent=2,
            )
        )
    finally:
        server.should_exit = True
        thread.join(8)
        assert not thread.is_alive()
