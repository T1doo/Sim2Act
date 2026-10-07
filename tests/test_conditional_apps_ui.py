"""jsdom is a DOM harness over real HTTP, not a native-browser acceptance."""

import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import select, update
from test_conditional_apps import authority, independent_report
from test_conditional_run_bindings import env as bounded_env
from test_conditional_run_bindings import envelope, factory, report

from sim2act.api import create_app
from sim2act.conditional_runs import candidate_for
from sim2act.db import grants, projects, protocol_jobs, runs
from sim2act.worker import Worker


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def test_named_report_draft_real_http_dom(env, tmp_path):
    if (
        not shutil.which("node")
        or subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
        ).returncode
    ):
        pytest.skip("Explicit developer Node/jsdom dependency required")
    store, settings, _, owner, _, pid, source, fresh = env
    other = store.project(owner, "Other own project")
    before = authority(env)
    app = create_app(store, settings)
    wires = []

    @app.post("/test-only-report-worker/{phase}")
    def worker(phase: str):
        with store.tx() as c:
            job = (
                c.execute(
                    select(protocol_jobs)
                    .join(runs, runs.c.id == protocol_jobs.c.run_id)
                    .where(runs.c.project_id == pid, runs.c.status == "QUEUED")
                )
                .mappings()
                .one()
            )
        snapshot = job["accepted_snapshot"]
        if phase == "source":
            values = [envelope(resource=source), envelope(report())]
        elif phase == "extract":
            values = [envelope(candidate_for(snapshot["contract"], source))]
        elif phase == "allow":
            values = [
                envelope(
                    independent_report(
                        ("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"]
                    )
                )
            ]
        elif phase == "block":
            values = [
                envelope(
                    independent_report(
                        ("TRUE", "TRUE", "TRUE"),
                        "BLOCK",
                        ["obtain_receipt", "obtain_prior_approval"],
                    )
                )
            ]
        elif phase == "unknown":
            values = [
                envelope(
                    independent_report(("TRUE", "TRUE", "FALSE"), "UNKNOWN", ["clarify_facts"])
                )
            ]
        else:
            raise AssertionError("closed fixture worker phases")
        assert Worker(
            store, settings, protocol_runner_factory=factory(env, tmp_path, values, wires)
        ).once()
        assert not values
        return {"test_only": True}

    @app.post("/test-only-report-revoke-target")
    def revoke_target():
        with store.tx() as c:
            runtime = c.execute(
                select(projects.c.runtime_id).where(projects.c.id == pid)
            ).scalar_one()
            c.execute(
                update(grants)
                .where(
                    grants.c.resource_id == fresh,
                    grants.c.principal_id == runtime,
                    grants.c.tool_ref == "resource.read",
                )
                .values(revoked=True)
            )
        return {"test_only": True}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            {
                "base": f"http://127.0.0.1:{port}",
                "project": pid,
                "other": other,
                "source": source,
                "fresh": fresh,
            }
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
        out = subprocess.run(
            ["node", "tests/conditional_apps_ui.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        (tmp_path / "driver.log").write_text(out.stdout + out.stderr)
        assert out.returncode == 0, out.stdout + out.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS" and len(result["checks"]) >= 12
        assert len(wires) == 6
        after = authority(env)
        with store.tx() as c:
            runtime = c.execute(
                select(projects.c.runtime_id).where(projects.c.id == pid)
            ).scalar_one()
        expected_grants = [
            {**g, "revoked": True}
            if g["resource_id"] == fresh
            and g["principal_id"] == runtime
            and g["tool_ref"] == "resource.read"
            else g
            for g in before[1]
        ]
        assert after == (before[0], expected_grants)
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
