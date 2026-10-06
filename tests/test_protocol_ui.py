"""Real local HTTP UI, jsdom and sandboxed installed Linux Chromium separately."""

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import func, select

from sim2act.api import create_app
from sim2act.db import attempts
from sim2act.protocol_pool import initialize_pools


@pytest.mark.parametrize("engine", ["dom", "chromium"])
def test_protocol_user_entry_actual_http(env, tmp_path, engine):
    store, settings, client, user, other_user, project, _ = env
    if not store.sqlite:
        pytest.skip("Owned subprocess fixture currently SQLite only; no PG UI coverage claimed")
    if not shutil.which("node") or engine == "chromium" and not shutil.which("chromium"):
        pytest.skip("Installed developer Node/Chromium required")
    if (
        engine == "dom"
        and subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"], capture_output=True
        ).returncode
    ):
        pytest.skip("Developer jsdom via NODE_PATH required")
    initialize_pools(store, offline_limit=14)
    repo = Path(__file__).resolve().parents[1]
    materials = repo / "docs/evidence/model-protocol-preparation-20261006/materials"
    resources = {}
    for phase in ["source", "cold"]:
        response = client.post(
            f"/api/projects/{project}/resources",
            json={
                "name": phase + "-policy.txt",
                "format": "txt",
                "content": (materials / ("a-" + phase) / "policy.txt").read_text(),
            },
        )
        assert response.status_code == 201
        resources[phase] = response.json()["id"]
    other_project = client.post("/api/projects", json={"name": "Other owned project"}).json()["id"]
    imported = client.post(
        f"/api/projects/{other_project}/resources",
        json={
            "name": "other-policy.txt",
            "format": "txt",
            "content": (materials / "a-source" / "policy.txt").read_text(),
        },
    ).json()["id"]
    contract = next(
        x
        for x in client.get(f"/api/projects/{other_project}/protocol/contracts").json()["items"]
        if x["contract_id"] == "protocol.synthetic.a-source.v1"
    )
    other_run = client.post(
        f"/api/projects/{other_project}/protocol/source",
        json={
            "contract_id": contract["contract_id"],
            "goal": contract["public_goal"],
            "inputs": contract["public_inputs"],
            "resource_ids": [imported],
            "request_key": "other-project-negative",
        },
    ).json()["run_id"]
    other_state = client.get(f"/api/projects/{other_project}/protocol/runs/{other_run}").json()
    paused = client.post(
        f"/api/projects/{other_project}/protocol/runs/{other_run}/recover",
        json={
            "expected_version": other_state["version"],
            "expected_fence": other_state["fence"],
            "request_key": "other-project-unsent-pause",
        },
    )
    assert paused.status_code == 200
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    info = {
        "base": f"http://127.0.0.1:{port}",
        "database": settings.database_url,
        "user": user,
        "other_user": other_user,
        "project": project,
        "other_project": other_project,
        "other_run": other_run,
        **resources,
    }
    (tmp_path / "info.json").write_text(json.dumps(info))
    server = uvicorn.Server(
        uvicorn.Config(create_app(store, settings), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.02)
        result = subprocess.run(
            ["node", "tests/protocol_ui_driver.cjs", str(tmp_path), os.sys.executable, engine],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=100,
        )
        (tmp_path / "driver-stderr.log").write_text(result.stderr)
        if (
            engine == "chromium"
            and result.returncode
            and "FATAL:sandbox/linux/suid/client/setuid_sandbox_host.cc" in result.stderr
            and "is owned by root and has mode 4755" in result.stderr
        ):
            pytest.skip(
                "BLOCKED_SANDBOX: installed Chromium SUID helper requires root ownership/mode4755; security policy unchanged"
            )
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout.strip())
        assert report["status"] == "PASS"
        assert report["engine"] == engine
        assert report["checks"] >= 12
        with store.tx() as c:
            assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 4
        (tmp_path / "report.json").write_text(json.dumps(report, indent=2))
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
