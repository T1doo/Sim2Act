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
from test_csv_dag import NoModel
from test_csv_dag_instances import setup

from sim2act.api import create_app
from sim2act.worker import Worker


@pytest.mark.parametrize("lost", ["post", "read"])
def test_actual_dag_internal_reuse_and_cold_new_column_page(env, tmp_path, lost):
    aid, rid, plan, _, source = setup(env)
    plan.pop("cached", None)
    app = create_app(env[0], env[1])
    worker = Worker(env[0], env[1], NoModel())

    @app.post("/__fixture__/work")
    def work(body: dict, authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A"
        job = env[0].claim(worker.id, env[1].lease_seconds)
        assert job["id"] == body["run_id"]
        worker.process(job)
        return {"run_id": job["id"]}

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
                source=source["id"],
                plan=plan,
                lost=lost,
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
            ["node", "tests/csv_dag_instances.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        (tmp_path / "driver.log").write_text(child.stdout + child.stderr)
        assert child.returncode == 0, child.stdout + child.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and proof["pages"] == 2 and len(proof["checks"]) >= 14
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
