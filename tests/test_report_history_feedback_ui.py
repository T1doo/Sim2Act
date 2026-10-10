"""Actual HTTP200 damaged-proof feedback; exact UNKNOWN recovery and navigation guards."""

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
from fastapi.responses import Response
from sqlalchemy import select
from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import setup_draft
from test_report_presentations import prepared

from sim2act.db import resources


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


@pytest.mark.parametrize(
    "phase,stage,away",
    [
        (phase, stage, None)
        for phase in ("checks", "definition")
        for stage in ("manifest", "envelope", "item")
    ]
    + [("checks", "envelope", "other_app"), ("definition", "item", "identity")],
)
def test_damaged_history_current_feedback_and_exact_recovery(env, tmp_path, phase, stage, away):
    app, _, _, _, output, _ = prepared(env, tmp_path)
    with env[0].tx() as c:
        csv_id = c.execute(
            select(resources.c.id).where(
                resources.c.project_id == env[5], resources.c.format == "csv"
            )
        ).scalar_one()
    peer, _ = setup_draft((*env[:6], csv_id))
    env[0].project(env[4], "Other isolated identity project")
    before = snapshot(env)
    baseline = os.environ.get("SIM2ACT_PRESENTATION_JS_BASELINE")
    if baseline:
        code = Path(baseline).read_text()
        route = next(
            r for r in env[2].app.routes if getattr(r, "path", None) == "/report-manifest.js"
        )
        route.dependant.call = lambda: Response(code, media_type="application/javascript")

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            dict(
                base=f"http://127.0.0.1:{port}",
                app=app["id"],
                peer=peer,
                project=env[5],
                explanation=output["explanation"],
                phase=phase,
                stage=stage,
                away=away,
            )
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
        completed = subprocess.run(
            ["node", "tests/report_history_feedback_ui.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        (tmp_path / "driver.log").write_text(completed.stdout + completed.stderr)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        result = json.loads((tmp_path / "results.json").read_text())
        assert result["status"] == "PASS"
        assert len(result["hashes"]) == 7
        for name, digest in result["hashes"].items():
            assert (
                hashlib.sha256((Path("src/sim2act/web") / name).read_bytes()).hexdigest() == digest
            )
        after = snapshot(env)
        assert all(
            before[name] == after[name] for name in before if not name.startswith("delivery_graph_")
        )
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
