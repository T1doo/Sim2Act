"""Actual product page, loopback HTTP and durable worker conditional branches."""

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
from test_csv_composition import setup
from test_csv_dag import NoModel

from sim2act.api import create_app
from sim2act.worker import Worker


@pytest.mark.parametrize("enabled", [False, True])
def test_actual_product_editable_composition(env, tmp_path, enabled):
    _, _, plan, _ = setup(env)
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
    (tmp_path / "info.json").write_text(json.dumps(dict(base=f"http://127.0.0.1:{port}",
        project=env[5], app=plan["app_id"], enabled=enabled)))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        assert shutil.which("node")
        result = subprocess.run(["node", "tests/csv_composition.cjs", str(tmp_path)],
            capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["jobs"]) == 1
        assert len(proof["checks"]) >= 12
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]}
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
