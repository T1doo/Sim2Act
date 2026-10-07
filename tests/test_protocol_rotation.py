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


@pytest.mark.parametrize("blocked_phase", ["snapshot", "stop"])
def test_owned_node_deadline_remains_active_during_blocked_lifecycle(tmp_path, monkeypatch, blocked_phase):
    """A lifecycle operation cannot keep the actual Node child alive past its deadline."""
    import time

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    info = {"port": 12345, "project": "p", "source": "s", "bearer": "synthetic"}
    for root in (tmp_path, fresh):
        (root / "info.json").write_text(json.dumps(info))
    original = subprocess.Popen
    old = original([sys.executable, "-c", "import time; time.sleep(30)"])
    spawned = []
    observations = []

    def owned_spawn(command, **kwargs):
        child = original(command, **kwargs)
        spawned.append(child)
        return child

    def blocked_snapshot(root):
        time.sleep(0.35)
        observations.append(spawned[0].poll())
        return {"tables": {}}

    monkeypatch.setattr(rotation.subprocess, "Popen", owned_spawn)
    real_stop = rotation.stop

    def blocked_stop(child):
        if child is old:
            time.sleep(0.35)
            observations.append(spawned[0].poll())
        real_stop(child)

    monkeypatch.setattr(rotation, "snapshot", blocked_snapshot if blocked_phase == "snapshot" else lambda root: {"tables": {}})
    if blocked_phase == "stop":
        monkeypatch.setattr(rotation, "stop", blocked_stop)
    request = str(tmp_path / "fresh-request.json")
    code = "from pathlib import Path;import time;Path(" + repr(request) + ").write_text('{\"action\":\"fresh-protocol-fixture.v1\"}');time.sleep(30)"
    with pytest.raises(subprocess.TimeoutExpired):
        rotation.run_node([sys.executable, "-c", code, sys.executable], old, tmp_path,
                          Path.cwd(), os.environ.copy(), timeout=0.2)
    assert observations and all(code is not None for code in observations)
    assert len(spawned) == 1, "no replacement may start after deadline"
    assert old.poll() is not None and spawned[0].poll() is not None
    assert not (tmp_path / "fresh-response.json").exists()


def test_transition_control_files_are_published_atomically():
    """Both real implementations publish only completed same-directory files."""
    source = Path("scripts/browser-ci/protocol-transition.cjs").read_text()
    assert "fs.writeFileSync(requestTmp," in source
    assert "fs.renameSync(requestTmp,request)" in source
    source = Path("scripts/protocol-ui/rotation.py").read_text()
    assert 'response.with_name(response.name + ".tmp")' in source
    assert "response_tmp.write_text(" in source
    assert "response_tmp.replace(response)" in source
