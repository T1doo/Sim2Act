"""Proof that a fresh project within the sealed fixture DB cannot evade its pool."""

import shutil
import subprocess
import sys

import pytest
from protocol_terminal_setup import prepare


@pytest.fixture(scope="module")
def sealed_protocol_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("sealed-protocol-sequential")
    subprocess.run([sys.executable, "scripts/protocol-ui/fixture.py", "--root", str(root),
                    "--port", "12345", "--action", "seed"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    prepare(root)
    return root


@pytest.mark.parametrize("scope", ["original", "other"])
@pytest.mark.parametrize("optimized", [False, True])
def test_actual_global_seal_refuses_both_projects_under_optimized_python(tmp_path, sealed_protocol_fixture, scope, optimized):
    root = sealed_protocol_fixture
    command = [sys.executable] + (["-O"] if optimized else [])
    result = subprocess.run(command + ["tests/global_experiment_gate_probe.py", str(root), scope],
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "global-gate-receipt.json").exists()
    shutil.copyfile(root / "global-gate-receipt.json", tmp_path / "global-gate-receipt.json")
    shutil.copyfile(root / "old-terminal-receipt.json", tmp_path / "old-terminal-receipt.json")
