"""Original engineering controls and local reading navigation, not pixels."""

import json
import shutil
import subprocess

import pytest


def test_original_engineering_controls_and_reading_navigation(tmp_path):
    if not shutil.which("node") or subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
    ).returncode:
        pytest.skip("Developer Node/jsdom required")
    result = subprocess.run(
        ["node", "tests/engineering_workspace.cjs"],
        capture_output=True, text=True, timeout=20,
    )
    (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS" and report["requests"] == report["submits"] == 0
    assert report["recovery_hash_preserved"] and report["original_inputs_and_ack_preserved"]
