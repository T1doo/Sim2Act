"""Actual product assets over owned loopback HTTP; synthetic worker, no native browser."""

import json
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from fastapi import Header
from test_csv_dag import NoModel
from test_csv_dag_instances import create, enqueue, release, work
from test_csv_dag_version_switch import next_release

from sim2act.api import create_app
from sim2act.worker import Worker


@pytest.mark.parametrize("with_report", [False, True])
@pytest.mark.parametrize("lost", ["post", "read"])
def test_real_page_upgrade_rollback_cold_new_input_and_read_only_recovery(env, tmp_path, with_report, lost):
    aid, rid, plan, _, old = release(env, with_report=with_report)
    target = next_release(env, aid, plan)
    instance = create(env, old)
    first, _ = enqueue(env, instance, old, "amount")
    work(env, first)
    app = create_app(env[0], env[1])
    worker = Worker(env[0], env[1], NoModel())

    @app.post("/__fixture__/work")
    def worker_once(body: dict, authorization: str = Header()):
        assert authorization == "Bearer synthetic-test-A"
        job = env[0].claim(worker.id, env[1].lease_seconds)
        assert job["id"] == body["run_id"]
        worker.process(job)
        return {"run_id": job["id"]}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps(dict(base=f"http://127.0.0.1:{port}",
        project=env[5], app=aid, resource=rid, instance=instance["id"], old=old["id"],
        target=target["id"], lost=lost, nodes=3 if with_report else 2)))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        child = subprocess.run(["node", "tests/csv_dag_version_switch.cjs", str(tmp_path)],
            capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(child.stdout + child.stderr)
        assert child.returncode == 0, child.stdout + child.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS" and len(result["checks"]) >= 20
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
