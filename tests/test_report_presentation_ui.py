"""Actual loopback HTTP and product JS DOM; synthetic Report, native NOT_RUN."""

import hashlib
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from test_conditional_run_bindings import env as bounded_env
from test_report_presentations import prepared


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def test_archived_report_presentation_actual_http_dom(env, tmp_path):
    app, _, _, _, output, _ = prepared(env, tmp_path)
    other = env[0].project(env[3], "Other owned DOM project")
    baseline = os.environ.get("SIM2ACT_PRESENTATION_JS_BASELINE")
    if baseline:
        # Trusted local counterexample fixture only; no product input/route added.
        from fastapi.responses import Response
        code = Path(baseline).read_text()
        route = next(r for r in env[2].app.routes if getattr(r, "path", None) == "/report-manifest.js")
        route.dependant.call = lambda: Response(code, media_type="application/javascript")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps({
        "base": f"http://127.0.0.1:{port}", "app": app["id"],
        "project": env[5], "other": other, "explanation": output["explanation"],
    }))
    server = uvicorn.Server(uvicorn.Config(env[2].app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        output = subprocess.run(["node", "tests/report_presentation_ui.cjs", str(tmp_path)],
                                capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(output.stdout + output.stderr)
        assert output.returncode == 0, output.stdout + output.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS" and len(result["checks"]) == 30
        for name, digest in result["hashes"].items():
            assert hashlib.sha256((Path("src/sim2act/web") / name).read_bytes()).hexdigest() == digest
        assert len(result["hashes"]) == 7
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
