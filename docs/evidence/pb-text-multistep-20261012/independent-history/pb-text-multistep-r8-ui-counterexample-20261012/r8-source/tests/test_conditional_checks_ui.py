"""Actual loopback HTTP/DOM; hand-entered reports, no model or oracle-built answers."""

import json
import shutil
import socket
import subprocess
import threading
import time

import pytest
import uvicorn
from sqlalchemy import update
from test_conditional_checks import POLICY, all_rows, request

from sim2act.api import create_app
from sim2act.db import grants, resources


def test_conditional_rule_display_and_source_boundary(env):
    body = request(env)
    client, pid = env[2], env[5]
    before = all_rows(env[0])
    path = f"/api/projects/{pid}/conditional-checks/sources/{body['resource_id']}"
    source = client.get(path)
    assert source.status_code == 200 and len(source.json()["rules"]) == 3
    assert source.json()["rules"][1]["line"] == 4
    result = client.post(f"/api/projects/{pid}/conditional-checks", json=body).json()
    assert [r["satisfaction"] for r in result["rule_results"]] == [
        "SATISFIED",
        "UNSATISFIED",
        "SATISFIED",
    ]
    assert result["decision"] == "BLOCK" and result["check_status"] == "PASS"
    assert "尚未取得" in result["rule_results"][1]["reason"]
    assert all_rows(env[0]) == before
    other = env[0].project(env[3], "Different source scope")
    assert client.get(path.replace(pid, other)).status_code == 403
    with env[0].tx() as c:
        c.execute(
            update(resources)
            .where(resources.c.id == body["resource_id"])
            .values(content=POLICY.read_text() + "changed")
        )
    assert client.get(path).json()["error"]["code"] == "VERIFICATION_FAILED"


def test_conditional_checks_actual_http_dom(env, tmp_path):
    if (
        not shutil.which("node")
        or subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
        ).returncode
    ):
        pytest.skip("Developer Node/jsdom required")
    store, settings, client, owner, _, pid, _ = env
    body = request(env)
    unsupported = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "Unsupported note", "format": "txt", "content": "No registered rules here."},
    ).json()["id"]
    other = store.project(owner, "Other conditional project")
    baseline = all_rows(store)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(
        json.dumps(
            {
                "base": f"http://127.0.0.1:{port}",
                "project": pid,
                "other": other,
                "resource": body["resource_id"],
                "unsupported": unsupported,
            }
        )
    )
    app = create_app(store, settings)

    @app.post("/test-only-source-change")
    def change():
        import hashlib

        value = POLICY.read_text() + "\nChanged rule version."
        with store.tx() as c:
            c.execute(
                update(resources)
                .where(resources.c.id == body["resource_id"])
                .values(content=value, hash=hashlib.sha256(value.encode()).hexdigest())
            )
        return {"test_only": True}

    @app.post("/test-only-source-restore")
    def restore():
        with store.tx() as c:
            c.execute(
                update(resources)
                .where(resources.c.id == body["resource_id"])
                .values(content=POLICY.read_text(), hash=body["expected_source_hash"])
            )
        return {"test_only": True}

    @app.post("/test-only-source-revoke")
    def revoke():
        with store.tx() as c:
            c.execute(
                update(grants)
                .where(grants.c.resource_id == body["resource_id"])
                .values(revoked=True)
            )
        return {"test_only": True}

    @app.get("/test-only-unchanged")
    def unchanged():
        return {"unchanged": all_rows(store) == baseline}

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        end = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < end
            time.sleep(0.01)
        out = subprocess.run(
            ["node", "tests/conditional_checks_ui.cjs", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        (tmp_path / "driver.log").write_text(out.stdout + out.stderr)
        assert out.returncode == 0, out.stdout + out.stderr
        assert json.loads((tmp_path / "results.json").read_text())["status"] == "PASS"
    finally:
        server.should_exit = True
        thread.join(8)
        assert not thread.is_alive()
