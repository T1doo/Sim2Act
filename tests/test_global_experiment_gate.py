"""Proof that a fresh project within the sealed fixture DB cannot evade its pool."""

import subprocess
import sys

import pytest
from protocol_terminal_setup import prepare


@pytest.mark.parametrize("scope", ["original", "other"])
@pytest.mark.parametrize("optimized", [False, True])
def test_actual_global_seal_refuses_both_projects_under_optimized_python(tmp_path, scope, optimized):
    subprocess.run([sys.executable, "scripts/protocol-ui/fixture.py", "--root", str(tmp_path),
                    "--port", "12345", "--action", "seed"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    prepare(tmp_path)
    command = [sys.executable] + (["-O"] if optimized else [])
    result = subprocess.run(command + ["tests/global_experiment_gate_probe.py", str(tmp_path), scope],
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "global-gate-receipt.json").exists()
