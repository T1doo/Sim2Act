"""Actual HTTP/jsdom evidence; native browser NOT_RUN, offline Intern transport only."""
import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from test_conditional_apps import authority, independent_report, saved
from test_conditional_run_bindings import env as bounded_env
from test_conditional_run_bindings import envelope, factory
from sim2act.api import create_app
from sim2act.worker import Worker


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def test_report_manifest_real_http_dom(env, tmp_path):
    assert shutil.which("node"), "developer Node dependency required"
    store, settings, _, owner, _, pid, _, _ = env
    before = authority(env)
    named, _, wires = saved(env, tmp_path)
    other = store.project(owner, "Other own project")
    app = create_app(store, settings)

    @app.post("/test-only-manifest-worker/{phase}")
    def worker(phase: str):
        if phase == "allow":
            report = independent_report(("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"])
        elif phase == "block":
            report = independent_report(("TRUE", "TRUE", "TRUE"), "BLOCK", ["obtain_receipt", "obtain_prior_approval"])
        else:
            raise AssertionError("closed fixture")
        values = [envelope(report)]
        assert Worker(store, settings, protocol_runner_factory=factory(env, tmp_path, values, wires)).once()
        assert not values
        return {"test_only": True}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps({"base": f"http://127.0.0.1:{port}", "project": pid, "other": other, "named": named["id"]}))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        output = subprocess.run(["node", "tests/report_manifest_ui.cjs", str(tmp_path)], capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(output.stdout + output.stderr)
        assert output.returncode == 0, output.stdout + output.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS" and len(result["checks"]) >= 15
        assert len(wires) == 5
        assert authority(env) == before
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
