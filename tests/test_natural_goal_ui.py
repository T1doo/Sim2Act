"""Actual loopback HTTP/full DOM; optional protected Playwright uses the same oracle."""
import json
import socket
import subprocess
import threading
import time

import httpx
import pytest
import uvicorn
from sqlalchemy import select, update
from test_natural_goal_planning import authority, plan, response, setup

from sim2act.api import create_app
from sim2act.db import attempts, grants, operations, runs
from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["valid", "disabled", "invalid_schema", "cancel", "revoke"])
def test_natural_goal_actual_http_ui(env, tmp_path, case):
    value = setup(env, provider="disabled" if case == "disabled" else "intern-s2")
    store, settings, client, project, resource, card = value
    other = store.project(env[3], "Other owned UI scope")
    before = authority(store)
    expected = plan(value)
    expected["interpretation"]["objective"] = '<script>window.NL_XSS=1</script> 合成目标'
    if case == "invalid_schema":
        expected["steps"][0]["tool_ref"] = "unknown.execute"
    wires = []

    def handler(request):
        body = json.loads(request.content)
        assert request.url.host == "chat.intern-ai.org.cn"
        assert body["tools"] == [] and body["model"] == "intern-s2"
        projected = json.loads(body["messages"][1]["content"])
        assert projected["saved_goal"]["snapshot"]["content"] == card["content"]
        wires.append(body)
        return httpx.Response(200, json=response(expected))

    app = create_app(store, settings)

    @app.post("/test-only-nl-worker")
    def work():
        if not store.test_only or settings.mode != "mock":
            raise AssertionError("Offline test fixture only")
        if not Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once():
            raise AssertionError("Expected owned queued run")
        return {"test_only": True}

    @app.get("/test-only-nl-state")
    def state():
        with store.tx() as connection:
            return {
                "runs": [dict(row) for row in connection.execute(select(
                    runs.c.id, runs.c.status, runs.c.version
                ).order_by(runs.c.id)).mappings()],
                "attempts": len(connection.execute(select(attempts)).all()),
                "operations": len(connection.execute(select(operations)).all()),
                "wires": len(wires), "test_only": True,
            }

    @app.post("/test-only-nl-revoke")
    def revoke():
        if case != "revoke" or not store.test_only:
            raise AssertionError("Closed revoke-only fixture")
        with store.tx() as connection:
            grant = connection.execute(select(grants).where(
                grants.c.project_id == project,
                grants.c.resource_id == resource,
                grants.c.principal_id == env[3],
                grants.c.tool_ref == "resource.read",
                grants.c.revoked.is_(False),
            )).mappings().one()
            connection.execute(update(grants).where(grants.c.id == grant["id"]).values(
                revoked=True, revision=grant["revision"] + 1,
            ))
        return {"test_only": True, "revoked_id": grant["id"]}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps({
        "base": f"http://127.0.0.1:{port}", "project": project,
        "card": card["id"], "version": card["version"], "fingerprint": card["fingerprint"],
        "case": case, "resource": resource, "other_project": other,
    }))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        completed = subprocess.run(
            ["node", "tests/natural_goal_ui.cjs", str(tmp_path)],
            capture_output=True, text=True, timeout=60,
        )
        (tmp_path / "driver.log").write_text(completed.stdout + completed.stderr)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        receipt = json.loads((tmp_path / "results.json").read_text())
        assert receipt["status"] == "PASS" and receipt["api"] == "ACTUAL_LOOPBACK_HTTP"
        assert receipt["browser"] == "JSDOM_NOT_NATIVE"
        after = authority(store)
        if case == "revoke":
            assert after["principals"] == before["principals"]
            changed = [(a, b) for a, b in zip(before["grants"], after["grants"], strict=True) if a != b]
            assert len(changed) == 1
            original, revoked = changed[0]
            assert revoked == {**original, "revoked": True, "revision": original["revision"] + 1}
            assert all(a == b for a, b in zip(before["grants"], after["grants"], strict=True) if a["id"] != original["id"])
        else:
            assert after == before
        final = state()
        assert len(final["runs"]) == 1
        assert final["wires"] == (0 if case == "disabled" else 1)
        assert final["operations"] == (1 if case == "valid" else 0)
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
        client.close()
