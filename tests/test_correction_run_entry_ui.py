"""Receipt navigation only; synthetic navigation/control responses, no Worker or model calls."""

import json
import os
import subprocess


def test_verified_correction_run_entry_and_navigation_isolation(tmp_path):
    proof = tmp_path / "correction-run-entry.json"
    completed = subprocess.run(
        ["node", "tests/correction_run_entry.cjs", str(proof)],
        env={**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", "/workspace/node-tools/node_modules")},
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(proof.read_text())
    assert result["status"] == "PASS"
    assert result["classification"] == "ACTUAL_PAGE_CONTROLLERS_SYNTHESIZED_NAVIGATION_AND_CANCEL"
