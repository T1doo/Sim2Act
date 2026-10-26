"""Cold trial recovery must not depend on a private Goal catalog read."""

import json
import subprocess
from pathlib import Path


def test_cold_trial_original_key_survives_catalog_failure(tmp_path):
    result = subprocess.run(
        ["node", "tests/trial_cold_key_directory_failure.cjs"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    (tmp_path / "driver.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(result.stdout)
    assert value["status"] == "PASS"
    assert value["http"] == value["model"] == value["worker"] == 0
    assert all(request["method"] == "GET" for request in value["requests"])
