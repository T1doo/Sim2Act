"""Actual served page: deterministic foreground/background read interleaving."""

import hashlib
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from test_natural_goal_planning import authority, plan, response, setup, submit

from sim2act.api import create_app
from sim2act.worker import Worker


def test_background_read_cannot_interrupt_explicit_plan_read(env, tmp_path):
    if (
        not shutil.which("node")
        or subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
        ).returncode
    ):
        pytest.skip("Developer Node and jsdom required for actual DOM oracle")
    value = setup(env)
    store, settings, client, project, _, _ = value
    rid = submit(value, key="foreground-polling").json()["run_id"]
    calls = []

    def provider(request):
        calls.append(str(request.url))
        assert request.url.host == "chat.intern-ai.org.cn"
        return httpx.Response(200, json=response(plan(value)))

    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(provider)).once()
    assert client.get(f"/api/runs/{rid}").json()["status"] == "WAITING_APPROVAL"
    before = authority(store)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            {
                "base": f"http://127.0.0.1:{port}",
                "project": project,
                "run_id": rid,
            }
        )
    )
    server = uvicorn.Server(
        uvicorn.Config(create_app(store, settings), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        result = subprocess.run(
            ["node", "tests/run_detail_polling.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and proof["posts"] == 0
        assert (
            proof["loaded_source_sha256"]["app.js"]
            == hashlib.sha256(
                (Path(__file__).parents[1] / "src/sim2act/web/app.js").read_bytes()
            ).hexdigest()
        )
        assert authority(store) == before and len(calls) == 1
        assert client.get(f"/api/runs/{rid}").json()["status"] == "WAITING_APPROVAL"
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
