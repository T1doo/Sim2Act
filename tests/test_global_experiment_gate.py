"""Proof that a fresh project within the sealed fixture DB cannot evade its pool."""

import hashlib
import shutil
import subprocess
import sys

import pytest
from protocol_terminal_setup import prepare


def fixture_files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


@pytest.fixture(scope="module")
def sealed_protocol_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("sealed-protocol-sequential")
    subprocess.run([sys.executable, "scripts/protocol-ui/fixture.py", "--root", str(root),
                    "--port", "12345", "--action", "seed"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    prepare(root)
    baseline = fixture_files(root)
    yield root, baseline
    assert fixture_files(root) == baseline, "sealed template must preserve every experiment marker and file"


@pytest.mark.parametrize("scope", ["original", "other"])
@pytest.mark.parametrize("optimized", [False, True])
def test_actual_global_seal_refuses_both_projects_under_optimized_python(tmp_path, sealed_protocol_fixture, scope, optimized):
    template, baseline = sealed_protocol_fixture
    shutil.copytree(template, tmp_path, dirs_exist_ok=True)
    root = tmp_path
    assert fixture_files(root) == baseline, "each case starts with independent exact old terminal state"
    command = [sys.executable] + (["-O"] if optimized else [])
    result = subprocess.run(command + ["tests/global_experiment_gate_probe.py", str(root), scope],
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "global-gate-receipt.json").exists()
    assert fixture_files(template) == baseline, "probe cannot mutate shared sealed template"
