"""Actual product DOM/HTTP and owned worker controls, no model or business write."""

import hashlib
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import Header
from sqlalchemy import select
from test_csv_dag import CSV, NoModel

from sim2act import csv_dag as dag
from sim2act.api import create_app
from sim2act.db import grants, runs
from sim2act.worker import Worker


def test_fixed_dag_actual_http_dom_exact_confirmation_recovery_and_revocation(env, tmp_path):
    store, settings, client, owner, _, pid, _ = env
    rid = client.post(f"/api/projects/{pid}/resources", json=dict(name="page-dag.csv", format="csv", content=CSV.read_text())).json()["id"]
    aid = client.post(f"/api/projects/{pid}/apps/csv-preview", json=dict(name="page DAG", goal="engineering only", resource_id=rid)).json()["id"]
    app_info = client.get(f"/api/apps/{aid}").json()
    client.post(f"/api/projects/{pid}/apps/{aid}/delivery-graph/derive", json=dict(expected_candidate_fingerprint=app_info["fingerprint"], request_key="page-source"))
    other = store.project(owner, "owned navigation project")
    with store.tx() as c:
        revoke = dict(c.execute(select(grants).where(grants.c.resource_id == rid, grants.c.principal_id == owner)).mappings().first())
    app = create_app(store, settings)
    worker = Worker(store, settings, NoModel())
    jobs = {}

    # Owned test-only HTTP hook; not mounted by product create_app.
    @app.post("/__fixture__/work")
    def work(body: dict, authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A"
        with store.tx() as c:
            state = c.execute(select(runs.c.status).where(runs.c.id == body["run_id"])).scalar()
        if state == "QUEUED":
            claimed = store.claim(worker.id, settings.lease_seconds)
            assert claimed["id"] == body["run_id"]
            jobs[body["run_id"]] = claimed
        job = jobs[body["run_id"]]
        if body["one_step"]:
            dag.advance(worker, job)
        else:
            worker.process(job)
        return {"run_id": job["id"]}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps(dict(base=f"http://127.0.0.1:{port}", project=pid,
        other=other, app=aid, revoke=dict(id=revoke["id"], version=revoke["revision"]))))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < end
            time.sleep(.01)
        assert shutil.which("node")
        result = subprocess.run(["node", "tests/csv_dag_ui.cjs", str(tmp_path)], capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 20
        root = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in proof["loaded_source_sha256"]}
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
