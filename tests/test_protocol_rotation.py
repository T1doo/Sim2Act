"""Owned process failures never acknowledge stale API health or leave a child."""

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path("scripts/protocol-ui").resolve()))
import rotation  # noqa: E402


@pytest.mark.parametrize("mode", ["invalid", "fresh-exit", "stale-health"])
def test_owned_rotation_failure_is_closed_and_collects_children(tmp_path, monkeypatch, mode):
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    old_info = {"port": 12345, "project": "old-project", "source": "old-source", "bearer": "synthetic"}
    fresh_info = {**old_info, "project": "fresh-project", "source": "fresh-source"}
    for root, info in [(tmp_path, old_info), (fresh, fresh_info)]:
        (root / "info.json").write_text(json.dumps(info))
    original = subprocess.Popen
    old = original([sys.executable, "-c", "import time; time.sleep(30)"])
    spawned = []

    def owned_spawn(command, **kwargs):
        if "--action" in command:
            assert old.poll() is not None, "old owned process must be joined before replacement"
            command = [sys.executable, "-c", "raise SystemExit(3)" if mode == "fresh-exit" else "import time; time.sleep(30)"]
        child = original(command, **kwargs)
        spawned.append(child)
        return child

    monkeypatch.setattr(rotation.subprocess, "Popen", owned_spawn)
    monkeypatch.setattr(rotation, "snapshot", lambda root: {"tables": {}, "rootScope": "test-only"})
    monkeypatch.setattr(rotation.httpx, "get", lambda url, **kw: httpx.Response(
        200, json=[{"id": "old-source"}] if url.endswith("/resources") else {"status": "ok"}
    ))
    action = {"action": "unsupported", "extra": "SECRET"} if mode == "invalid" else {"action": "fresh-protocol-fixture.v1"}
    code = "from pathlib import Path;import time;Path(" + repr(str(tmp_path / "fresh-request.json")) + ").write_text(" + repr(json.dumps(action)) + ");time.sleep(30)"
    with pytest.raises((ValueError, RuntimeError, subprocess.TimeoutExpired)):
        rotation.run_node([sys.executable, "-c", code, sys.executable], old, tmp_path,
                          Path.cwd(), os.environ.copy(), timeout=0.4)
    assert not (tmp_path / "fresh-response.json").exists()
    assert old.poll() is not None and all(child.poll() is not None for child in spawned)
