"""Fault protocol for exact-task reread; actual HTTP proof stays in process tests."""

import json
import os
import subprocess
from pathlib import Path


def test_conflict_reread_protocol(tmp_path):
    output = tmp_path / "protocol.json"
    process = subprocess.run(
        ["node", "tests/conflict_reread_protocol.cjs", str(output)],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
        capture_output=True, text=True, timeout=60,
    )
    (tmp_path / "stdout.log").write_text(process.stdout)
    (tmp_path / "stderr.log").write_text(process.stderr)
    assert process.returncode == 0, process.stderr
    proof = json.loads(output.read_text())
    assert proof["status"] == "PASS" and len(proof["checks"]) >= 27
