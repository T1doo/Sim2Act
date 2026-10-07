"""Actual HTTP/jsdom evidence; native browser NOT_RUN, offline Intern transport only."""
import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import select
from test_conditional_apps import authority, independent_report
from test_conditional_run_bindings import env as bounded_env
from test_conditional_run_bindings import envelope, factory
from test_conditional_run_bindings import report as source_report

from sim2act.api import create_app
from sim2act.conditional_runs import candidate_for
from sim2act.db import protocol_jobs, runs
from sim2act.worker import Worker


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def test_report_manifest_real_http_dom(env, tmp_path):
    assert shutil.which("node"), "developer Node dependency required"
    store, settings, _, owner, _, pid, source, fresh = env
    wires = []
    other = store.project(owner, "Other own project")
    before = authority(env)
    app = create_app(store, settings)

    @app.post("/test-only-manifest-worker/{phase}")
    def worker(phase: str):
        with store.tx() as c:
            job = c.execute(select(protocol_jobs).join(runs, runs.c.id == protocol_jobs.c.run_id)
                            .where(runs.c.status == "QUEUED", runs.c.project_id == pid)).mappings().one()
        if phase == "source":
            values = [envelope(resource=source), envelope(source_report())]
        elif phase == "extract":
            values = [envelope(candidate_for(job["accepted_snapshot"]["contract"], source))]
        elif phase == "allow":
            report = independent_report(("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"])
        elif phase == "block":
            report = independent_report(("TRUE", "TRUE", "TRUE"), "BLOCK", ["obtain_receipt", "obtain_prior_approval"])
        elif phase == "unknown":
            report = independent_report(("UNKNOWN", "UNKNOWN", "UNKNOWN"), "UNKNOWN", ["clarify_facts"])
        else:
            raise AssertionError("closed fixture")
        if phase in {"allow", "block", "unknown"}:
            values = [envelope(report)]
        assert Worker(store, settings, protocol_runner_factory=factory(env, tmp_path, values, wires)).once()
        assert not values
        return {"test_only": True}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps({"base": f"http://127.0.0.1:{port}", "project": pid, "other": other, "source": source, "fresh": fresh}))
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
        assert result["status"] == "PASS" and len(result["checks"]) == 46
        assert len(wires) == 7
        assert authority(env) == before
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
