"""Controlled local-page scheduling; separate from HTTP/Worker and native qualification."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

SCENARIOS = [
    "old-success-after-new-success", "old-failure-after-new-success",
    "initial-failure-after-edit-aba", "initial-catch-edit-aba", "initial-catch-new-read",
    "refresh-catch-new-read", "recover-catch-new-read", "save-readback-catch-new-read",
    "current-initial-failure", "current-refresh-failure", "success-after-edit-aba",
]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_owned_goal_read_summary_qualification(tmp_path, scenario):
    root = Path(__file__).parents[1]
    web = root / "src/sim2act/web"
    source = Path(os.environ.get("SIM2ACT_OWN_GOAL_READ_SOURCE", web / "owner-review.js"))
    output = tmp_path / "result.json"
    process = subprocess.run(["node", str(root / "tests/own_goal_read_errors.cjs"), scenario,
        str(source), str(output), str(web)], text=True, capture_output=True, timeout=20,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
    evidence = os.environ.get("SIM2ACT_OWN_GOAL_READ_EVIDENCE")
    if evidence:
        target = Path(evidence)
        target.mkdir(parents=True, exist_ok=True)
        (target / (scenario + ".log")).write_text(process.stdout + process.stderr)
        (target / (scenario + "-exit.json")).write_text(json.dumps({"exit_code": process.returncode}))
        if output.exists():
            (target / (scenario + ".json")).write_bytes(output.read_bytes())
    assert process.returncode == 0, process.stdout + process.stderr
    proof = json.loads(output.read_text())
    assert proof["status"] == "PASS" and all(proof["checks"].values())
    assert proof["classification"] == "CONTROLLED_LOCAL_SOURCE_JSDOM_REAL_SHA256"
    assert proof["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
