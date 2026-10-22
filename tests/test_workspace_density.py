"""Scope navigation must stay read-only when forms become native disclosures."""
import json
import shutil
import subprocess

import pytest


def test_density_scope_focus_and_existing_controls():
    if not shutil.which("node") or subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"], capture_output=True, timeout=10
    ).returncode:
        pytest.skip("Developer Node/jsdom required")
    result = subprocess.run(
        ["node", "tests/workspace_density.cjs"], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS" and report["network"] == report["submits"] == 0
