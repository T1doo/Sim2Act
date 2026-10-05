"""Real API and worker processes against an isolated PostgreSQL test schema."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest


@pytest.mark.skipif(
    not os.environ.get("SIM2ACT_TEST_DATABASE_URL"),
    reason="PostgreSQL subprocess check needs explicit test URL",
)
def test_AT05_real_process_stop_accept_restart_reopen(env, tmp_path):
    from sqlalchemy.engine import make_url

    store, s, client, a, b, pid, res = env
    schema = store.engine.get_execution_options()["schema_translate_map"][None]
    url = (
        make_url(s.database_url)
        .update_query_dict({"options": "-csearch_path=" + schema})
        .render_as_string(hide_password=False)
    )
    root = Path(__file__).parents[1]
    data = tmp_path / "中文 空格数据"
    # Supply only synthetic configuration; do not read dotenv or pass a live token.
    child_env = {
        "PATH": str(Path(sys.executable).parent),
        "SIM2ACT_DATABASE_URL": url,
        "SIM2ACT_DATA_DIR": str(data),
        "SIM2ACT_MODEL_MODE": "mock",
        "SIM2ACT_LIVE_ENABLED": "false",
    }
    if os.name == "nt":
        # Windows subprocesses require their system/temp paths; never inherit credentials.
        child_env.update(
            {
                key: os.environ[key]
                for key in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP")
                if key in os.environ
            }
        )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"

    def manage(command):
        p = subprocess.run(
            [sys.executable, "scripts/manage.py", command, "--port", str(port)],
            cwd=root,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert p.returncode == 0, p.stdout + p.stderr
        return p.stdout

    try:
        started = json.loads(manage("start"))
        assert len({p["pid"] for p in started["processes"]}) == 2
        assert httpx.get(base + "/health").json()["worker"] == "UP"
        # Port conflict must not launch a second process pair.
        duplicate = subprocess.run(
            [sys.executable, "scripts/manage.py", "start", "--port", str(port)],
            cwd=root,
            env=child_env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert duplicate.returncode != 0
        import psutil

        wp = next(x for x in started["processes"] if x["kind"] == "worker")
        psutil.Process(wp["pid"]).terminate()
        for _ in range(100):
            try:
                if psutil.Process(wp["pid"]).status() in {psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD}:
                    break
            except psutil.NoSuchProcess:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Worker did not stop")
        with httpx.Client(
            base_url=base, headers={"Authorization": "Bearer synthetic-test-A"}
        ) as browser:
            response = browser.post(
                f"/api/projects/{pid}/runs",
                json={
                    "goal": "process disconnect test",
                    "resource_refs": [res],
                    "request_key": "real-process",
                },
            )
            assert response.status_code == 202
            rid = response.json()["run_id"]
            assert browser.get(f"/api/runs/{rid}").json()["status"] == "QUEUED"
        # Client disconnected. Database owns accepted task; restart both independent processes.
        manage("stop")
        assert data.exists() and not (data / "processes.json").exists()
        manage("start")
        with httpx.Client(
            base_url=base, headers={"Authorization": "Bearer synthetic-test-A"}
        ) as browser:
            for _ in range(50):
                result = browser.get(f"/api/runs/{rid}").json()
                if result["status"] == "PARTIAL":
                    break
                time.sleep(0.1)
            assert result["status"] == "PARTIAL"
            assert result["result"]["mode"] == "MOCK"
            assert result["result"]["receipts"][0]["status"] == "VERIFIED"
        manage("stop")
        offline = json.loads(manage("status"))
        assert offline["health"] == "OFFLINE"
        # Final restart confirms a completed result survives service shutdown.
        manage("start")
        with httpx.Client(
            base_url=base, headers={"Authorization": "Bearer synthetic-test-A"}
        ) as browser:
            assert browser.get(f"/api/runs/{rid}").json()["result"] == result["result"]
    finally:
        manage("stop")
