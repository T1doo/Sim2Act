"""Real full DOM/app.js, synthesized API; offline UI contract evidence only."""
import hashlib
import json
import subprocess
from pathlib import Path


def test_saved_goal_execution_ui(tmp_path):
    result = subprocess.run(
        ["node", "tests/goal_card_run_ui.cjs", str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads((tmp_path / "results.json").read_text())
    assert receipt["status"] == "PASS" and len(receipt["checks"]) == 24
    source = Path(__file__).parents[1] / "src/sim2act/web/app.js"
    assert receipt["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_saved_goal_execution_actual_http_ui(env, tmp_path):
    import socket
    import threading
    import time

    import uvicorn
    from sqlalchemy import select
    from test_goal_cards import body

    from sim2act.api import create_app
    from sim2act.db import grants, principals, runs
    from sim2act.worker import Worker

    store, settings, client, _, _, project, resource = env
    card = client.post(f"/api/projects/{project}/goal-cards", json=body(resource)).json()["id"]
    with store.tx() as connection:
        before = {table.name: [dict(row) for row in connection.execute(
            select(table).order_by(table.c.id)
        ).mappings()] for table in (grants, principals)}
    app = create_app(store, settings)

    @app.post("/test-only-goal-worker")
    def work():
        assert store.test_only and settings.mode == "mock"
        if not Worker(store, settings).once():
            raise AssertionError("Expected owned queued task")
        return {"test_only": True}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps({
        "base": f"http://127.0.0.1:{port}", "project": project, "card": card,
    }))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        result = subprocess.run(
            ["node", "tests/goal_card_run_ui.cjs", str(tmp_path), "HTTP"],
            capture_output=True, text=True, timeout=30,
        )
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        receipt = json.loads((tmp_path / "results.json").read_text())
        assert receipt["status"] == "PASS" and len(receipt["checks"]) == 7
        source = Path(__file__).parents[1] / "src/sim2act/web/app.js"
        assert receipt["loaded_source_sha256"]["app.js"] == hashlib.sha256(source.read_bytes()).hexdigest()
        with store.tx() as connection:
            assert len(connection.execute(select(runs)).all()) == 1
            for table in (grants, principals):
                assert [dict(row) for row in connection.execute(
                    select(table).order_by(table.c.id)
                ).mappings()] == before[table.name]
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
