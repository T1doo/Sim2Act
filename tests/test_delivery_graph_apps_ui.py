"""DeliveryGraph actual loopback HTTP/DOM; no native or provider requests."""
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
from test_app_previews import draft
from test_conditional_run_bindings import env as bounded_env
from test_report_manifest_apps import promoted

from sim2act.api import create_app
from sim2act.db import attempts, grants, principals


@pytest.mark.parametrize("family", ["CSV", "REPORT"])
def test_delivery_graph_actual_http_dom(env, tmp_path, family):
    if family == "REPORT":
        env = bounded_env.__wrapped__(env)
        saved, _, _, _, wires = promoted(env, tmp_path)
        aid = saved["id"]
        assert len(wires) == 3
    else:
        aid = draft(env)
    store, settings, client, owner, _, project, *_ = env
    assert shutil.which("node"), "Developer Node required"
    other = store.project(owner, "Other owned graph project")
    inspected = client.get(f"/api/apps/{aid}").json()
    resource = inspected["candidate"]["actions"][0]["permission_requirements"][0]["resource_ref"]
    with store.tx() as c:
        revoke = dict(c.execute(select(grants).where(grants.c.principal_id == owner,
                                                      grants.c.resource_id == resource)).mappings().first())
        before = {name: [dict(r) for r in c.execute(select(table)).mappings()]
                  for name, table in [("grants", grants), ("principals", principals), ("attempts", attempts)]}
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps({"base": f"http://127.0.0.1:{port}", "project": project, "other": other, "app": aid, "revoke": {"id": revoke["id"], "version": revoke["revision"]}}))
    server = uvicorn.Server(uvicorn.Config(create_app(store, settings), host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        result = subprocess.run(["node", "tests/delivery_graph_ui.cjs", str(tmp_path)], capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        receipt = json.loads((tmp_path / "results.json").read_text())
        assert receipt["status"] == "PASS" and receipt["live_requests"] == 0
        assert len(receipt["checks"]) == 28
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert receipt["loaded_source_sha256"] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
                                                    for name in receipt["loaded_source_sha256"]}
        with store.tx() as c:
            after = {name: [dict(r) for r in c.execute(select(table)).mappings()]
                     for name, table in [("grants", grants), ("principals", principals), ("attempts", attempts)]}
        expected = json.loads(json.dumps(before))
        for row in expected["grants"]:
            if row["id"] == revoke["id"]:
                row["revoked"] = True
                row["revision"] += 1
        assert after == expected
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
