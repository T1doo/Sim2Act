"""Controlled local production submit function; no HTTP or Worker qualification."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("scenario", ["late-r1-after-r2", "normal-r1"])
def test_text_workflow_pending_request_identity(tmp_path, scenario):
    root = Path(__file__).parents[1]
    source = root / "src/sim2act/web/internal.js"
    output = tmp_path / "result.json"
    process = subprocess.run(
        ["node", str(root / "tests/text_workflow_pending.cjs"), scenario,
         str(source), str(output)],
        text=True, capture_output=True, timeout=20,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
    )
    evidence = os.environ.get("SIM2ACT_PENDING_EVIDENCE_DIR")
    if evidence:
        folder = Path(evidence)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (scenario + ".log")).write_text(process.stdout + process.stderr)
        if output.exists():
            (folder / (scenario + ".json")).write_bytes(output.read_bytes())
    assert process.returncode == 0, process.stdout + process.stderr
    proof = json.loads(output.read_text())
    assert proof["status"] == "PASS" and all(proof["checks"].values())
    assert proof["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert proof["classification"] == "CONTROLLED_LOCAL_PRODUCTION_FUNCTION_JSDOM"
