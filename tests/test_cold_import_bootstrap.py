"""Startup must work without API or test-suite preload masking schema cycles."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "sim2act.pb_natural_uses",
        "sim2act.pa_spec_apps",
        "sim2act._cold_policy_segment",
    ],
)
def test_fresh_interpreter_schema_bootstrap(module):
    source = Path(__file__).resolve().parents[1] / "src"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            'import sys, importlib; sys.path.insert(0, sys.argv[1]); importlib.import_module(sys.argv[2]); print("IMPORT_OK")',
            str(source),
            module,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "IMPORT_OK"
