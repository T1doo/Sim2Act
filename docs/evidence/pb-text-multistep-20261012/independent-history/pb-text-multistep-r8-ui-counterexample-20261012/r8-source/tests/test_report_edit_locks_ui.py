"""Actual protected Report edit workflow via product page and loopback HTTP."""

import hashlib
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import select
from test_delivery_graph_apps import snapshot
from test_report_presentations import env as env
from test_report_presentations import prepared

from sim2act.api import create_app
from sim2act.db import app_drafts


@pytest.mark.parametrize("scenario", ["normal", "aba", "unknown-plan"])
def test_report_edit_lock_actual_http_page(env, tmp_path, scenario):
    app, _, _, _, output, wires = prepared(env, tmp_path, peer=scenario == "unknown-plan")
    peer = None
    if scenario == "unknown-plan":
        with env[0].tx() as c:
            peer = dict(
                next(
                    row
                    for row in c.execute(
                        select(app_drafts).where(app_drafts.c.project_id == env[5])
                    ).mappings()
                    if row["id"] != app["id"]
                    and row["candidate"].get("manifest", {}).get("workflow", [{}])[0].get("step_id")
                    == "aggregate"
                )
            )
    assert shutil.which("node")
    other = env[0].project(env[3], "Other Report project")
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
                explanation=output["explanation"],
                scenario=scenario,
                peer=None if peer is None else dict(id=peer["id"], fingerprint=peer["fingerprint"]),
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
            ["node", "tests/report_edit_locks_ui.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        proof = json.loads((tmp_path / "results.json").read_text())
        assert (
            proof["status"] == "PASS"
            and len(proof["checks"])
            == {
                "normal": 17,
                "aba": 19,
                "unknown-plan": 10,
            }[scenario]
        )
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert proof["loaded_source_sha256"] == {
            name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]
        }
        assert (
            len(wires) == 4
        )  # Existing synthetic fixture only; the new page never requests a model.
        after = snapshot(env)
        for table in before:
            if not table.startswith("delivery_graph_"):
                assert before[table] == after[table], table
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
