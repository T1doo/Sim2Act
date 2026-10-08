"""Existing product JS through actual loopback HTTP; controlled isolated resources."""

import hashlib
import json
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import uvicorn
from sqlalchemy import select
from test_column_patches import assert_domain_unchanged, setup
from test_delivery_graph_apps import snapshot

from sim2act.api import create_app
from sim2act.db import grants


def test_column_patch_actual_http_dom_recovery_exact_version_and_revocation(env, tmp_path):
    aid, rid, _, _, _ = setup(env)
    store, settings, client, owner, _, project, *_ = env
    assert shutil.which("node"), "Developer Node required"
    other = store.project(owner, "Other owned patch project")
    with store.tx() as c:
        revoke = dict(c.execute(select(grants).where(grants.c.principal_id == owner,
                                                    grants.c.resource_id == rid)).mappings().first())
    before = snapshot(env)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "info.json").write_text(json.dumps(dict(
        base=f"http://127.0.0.1:{port}", project=project, other=other, app=aid,
        revoke={"id": revoke["id"], "version": revoke["revision"]})))
    server = uvicorn.Server(uvicorn.Config(create_app(store, settings), host="127.0.0.1",
                                         port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(.01)
        result = subprocess.run(["node", "tests/column_patch_ui.cjs", str(tmp_path)],
                                capture_output=True, text=True, timeout=90)
        (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        receipt = json.loads((tmp_path / "results.json").read_text())
        assert receipt["status"] == "PASS" and len(receipt["checks"]) == 20
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert receipt["loaded_source_sha256"] == {
            name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in receipt["loaded_source_sha256"]}
        after = snapshot(env)
        # Actual owner revoke is the only domain change; patch/check ledgers append.
        expected = json.loads(json.dumps(before))
        for row in expected["grants"]:
            if row["id"] == revoke["id"]:
                row["revoked"] = True
                row["revision"] += 1
        assert_domain_unchanged(expected, after)
    finally:
        server.should_exit = True
        thread.join(10)
        assert not thread.is_alive()
