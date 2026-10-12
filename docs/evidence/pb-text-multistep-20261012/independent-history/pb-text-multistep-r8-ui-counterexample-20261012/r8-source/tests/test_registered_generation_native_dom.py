"""Direct real HTTP UI events in jsdom; native module verified separately."""

import importlib.util
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

from sim2act.api import create_app


@pytest.mark.parametrize("inject_poll_race", [False, True], ids=["normal", "poll-refresh-order"])
def test_registered_generation_direct_actual_http_dom(tmp_path, inject_poll_race):
    if not shutil.which("node"):
        pytest.skip("Developer Node required for optional HTTP DOM module check")
    probe = subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
    )
    if probe.returncode:
        pytest.skip("Developer jsdom must be resolvable through NODE_PATH or Node module path")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "registered_ui_fixture", repo / "scripts/agent-ui/fixture.py"
    )
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.seed(tmp_path, port)
    info = json.loads((tmp_path / "info.json").read_text())
    store, settings = fixture.context(tmp_path)
    before = fixture.generation_counts(store)
    server = uvicorn.Server(
        uvicorn.Config(create_app(store, settings), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < deadline
            time.sleep(0.02)
        result = subprocess.run(
            [
                "node",
                "tests/registered_generation_native_dom.cjs",
                str(tmp_path),
                os.sys.executable,
                *(["--inject-poll-race"] if inject_poll_race else []),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            cwd=repo,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        data = json.loads(result.stdout.strip())
        assert data["browser"] == "NOT_RUN" and data["visual"] == "NOT_RUN"
        assert data["result"]["status"] == "PASS"
        race = data["result"]["pollRace"]
        assert race["enabled"] is inject_poll_race
        if inject_poll_race:
            assert race["observedNull"] is True and race["recovered"] is True
            null_event = next(e for e in race["events"] if e["name"] == "manual read returned")
            recovered = race["events"][-1]
            assert null_event["iid"] is None and null_event["rid"] is None
            assert recovered["iid"] == data["result"]["metadata"]["generated"]["instance"]
            assert recovered["rid"] == data["result"]["metadata"]["generated"]["id"]
            assert recovered["status"] == "SUCCEEDED"
        assert (
            data["result"]["metadata"]["source"]["id"]
            != data["result"]["metadata"]["generated"]["id"]
        )
        after = fixture.generation_counts(store)
        assert after["principal_fingerprint"] == before["principal_fingerprint"]
        expected = [dict(g) for g in before["grant_rows"]]
        for grant in expected:
            if (grant["principal_id"], grant["resource_id"]) in {
                (info["registered_source_runtime"], info["registered_source_resource"]),
                (info["registered_target_runtime"], info["registered_target_resource"]),
            } and grant["tool_ref"] in {"resource.read", "data.aggregate_csv"}:
                grant.update(revoked=True, revision=grant["revision"] + 1)
        assert after["grant_rows"] == expected
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
        store.engine.dispose()
