"""Owned HTTP/body/action teardown oracles using actual app.js and timer."""
import json
import subprocess

import pytest


@pytest.mark.parametrize("case", ["pending-poll", "network-error", "action-error", "controlled-lost"])
def test_natural_ui_owned_page_drain(tmp_path, case):
    completed = subprocess.run(
        ["node", "tests/natural_ui_drain.cjs", str(tmp_path), case],
        capture_output=True, text=True, timeout=30,
    )
    (tmp_path / "driver.log").write_text(completed.stdout + completed.stderr)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["status"] == "PASS" and result["case"] == case
