"""Real acceptance remains unknown after a later transport-boundary rejection."""

import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import func, select
from test_conditional_apps import authority, saved
from test_conditional_run_bindings import env as bounded_env

from sim2act.db import protocol_jobs


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


@pytest.mark.parametrize("fault", ["lost", "malformed"])
def test_actual_prior_unknown_retry_422_keeps_original_intent(env, tmp_path, fault):
    if (
        not shutil.which("node")
        or subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
        ).returncode
    ):
        pytest.skip("Explicit developer jsdom dependency required")
    before = authority(env)
    draft, _, wires = saved(env, tmp_path)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            {
                "base": f"http://127.0.0.1:{port}",
                "project": env[5],
                "app": draft["id"],
                "fault": fault,
            }
        )
    )
    server = uvicorn.Server(
        uvicorn.Config(env[2].app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        out = subprocess.run(
            ["node", "tests/conditional_apps_recovery.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=25,
        )
        (tmp_path / "recovery-driver.log").write_text(out.stdout + out.stderr)
        assert out.returncode == 0, out.stdout + out.stderr
        result = json.loads((tmp_path / "recovery-results.json").read_text())
        assert result["status"] == "PASS" and len(result["checks"]) == 7
        with env[0].tx() as c:
            assert (
                c.execute(
                    select(func.count())
                    .select_from(protocol_jobs)
                    .where(protocol_jobs.c.kind == "cold")
                ).scalar_one()
                == 1
            )
        assert len(wires) == 3 and authority(env) == before
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
