"""Actual HTTP project-wide deterministic checks and page receipt recovery."""

import hashlib
import json
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from test_delivery_graph_apps import snapshot
from test_project_revalidation import env as env
from test_project_revalidation import setup

from sim2act.api import create_app


@pytest.mark.parametrize("scenario", ["normal", "late-acceptance"])
def test_actual_project_revalidation_http_page(env, tmp_path, scenario):
    app, _, _, _, wires = setup(env, tmp_path)
    other = env[0].project(env[3], "Other project")
    before = snapshot(env)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            dict(
                base=f"http://127.0.0.1:{port}",
                project=env[5],
                other=other,
                app=app["id"],
                scenario=scenario,
            )
        )
    )
    server = uvicorn.Server(
        uvicorn.Config(create_app(env[0], env[1]), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        result = subprocess.run(
            ["node", "tests/project_revalidation_ui.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=140,
        )
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 14
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {
            name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]
        }
        after = snapshot(env)
        for table in before:
            if table != "delivery_graph_requests":
                assert before[table] == after[table], table
        assert len(wires) == 4
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
