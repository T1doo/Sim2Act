"""Product page over real loopback HTTP, real DAG worker and cold result proof."""

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
from sqlalchemy import select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import release
from test_csv_logic_reuse import retire_old

from sim2act.api import create_app
from sim2act.db import app_drafts, grants
from sim2act.worker import Worker


@pytest.mark.parametrize(
    "lost,with_report",
    [
        ("post", False),
        ("post", True),
        ("read", True),
        ("late", True),
        ("identity-late", True),
        ("invalid-binding", True),
        ("unknown403", True),
        ("mint-post", True),
        ("invalid-key", True),
        ("invalid-budget", True),
    ],
)
def test_actual_data_free_logic_page_cold_result_and_safe_recovery(env, tmp_path, lost, with_report):
    aid, rid, _, _, rel = release(env, with_report=with_report)
    aid = rel["snapshot"]["draft"]["id"]
    app = create_app(env[0], env[1])
    worker = Worker(env[0], env[1], NoModel())

    @app.post("/__fixture__/work")
    def work(body: dict, authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A"
        job = env[0].claim(worker.id, env[1].lease_seconds)
        assert job["id"] == body["run_id"]
        worker.process(job)
        return {"run_id": job["id"]}

    @app.post("/__fixture__/target-grant")
    def grant(body: dict, authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A"
        with env[0].tx() as c:
            c.execute(
                update(grants)
                .where(
                    grants.c.principal_id == c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id == body["app_id"])).scalar_one(),
                    grants.c.resource_id == body["resource_id"],
                )
                .values(revoked=body["revoked"])
            )
        return {"changed": True}

    @app.post("/__fixture__/retire-old")
    def retire(authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A"
        retire_old(env, rid)
        return {"retired": True}
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            dict(
                base=f"http://127.0.0.1:{port}",
                project=env[5],
                app=aid,
                resource=rid,
                release=rel["id"],
                lost=lost,
                nodes=3 if with_report else 2,
            )
        )
    )
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        assert shutil.which("node")
        child = subprocess.run(
            ["node", "tests/csv_logic_reuse.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        (tmp_path / "driver.log").write_text(child.stdout + child.stderr)
        assert child.returncode == 0, child.stdout + child.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and proof["pages"] == 2 and len(proof["checks"]) >= 20
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert all(
            p["loaded_source_sha256"]
            == {
                n: hashlib.sha256((web / n).read_bytes()).hexdigest()
                for n in p["loaded_source_sha256"]
            }
            for p in proof["assets"]
        )
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
