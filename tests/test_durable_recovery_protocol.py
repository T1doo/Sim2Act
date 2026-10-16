"""Fault-focused Storage/Web Locks protocol; separate from actual HTTP acceptance."""

import json
import os
import subprocess
from pathlib import Path


def test_durable_spec_recovery_protocol(tmp_path):
    result = tmp_path / "protocol.json"
    process = subprocess.run(
        ["node", "tests/durable_recovery_protocol.cjs", str(result)],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
        capture_output=True, text=True, timeout=40,
    )
    (tmp_path / "protocol.stdout").write_text(process.stdout)
    (tmp_path / "protocol.stderr").write_text(process.stderr)
    assert process.returncode == 0, process.stderr
    proof = json.loads(result.read_text())
    assert proof["status"] == "PASS" and len(proof["checks"]) >= 22
