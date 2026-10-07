"""Exact future native module against existing owned protocol fixture and actual HTTP."""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest


def test_conditional_native_shared_module_existing_fixture(tmp_path):
    if (
        not shutil.which("node")
        or subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).returncode
    ):
        pytest.skip("Developer Node/jsdom required")
    repo = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    child = {**os.environ, "PYTHONPATH": "src"}
    seed = subprocess.run(
        [
            sys.executable,
            "scripts/protocol-ui/fixture.py",
            "--root",
            str(tmp_path),
            "--port",
            str(port),
            "--action",
            "seed",
        ],
        env=child,
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert seed.returncode == 0, seed.stdout + seed.stderr
    with (tmp_path / "api.log").open("wb") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "scripts/protocol-ui/fixture.py",
                "--root",
                str(tmp_path),
                "--action",
                "serve",
            ],
            env=child,
            cwd=repo,
            stdout=log,
            stderr=log,
        )
    try:
        end = time.monotonic() + 10
        while time.monotonic() < end:
            assert server.poll() is None
            try:
                if httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.05)
        else:
            pytest.fail("Owned fixture API not ready")
        out = subprocess.run(
            ["node", "tests/conditional_native_oracle.cjs", str(tmp_path), sys.executable],
            env=child,
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
        )
        (tmp_path / "driver.log").write_text(out.stdout + out.stderr)
        assert out.returncode == 0, out.stdout + out.stderr
        result = json.loads((tmp_path / "conditional-results.json").read_text())
        assert result["status"] == "PASS" and result["real_model_requests"] == 0
        assert len(result["checks"]) == 22
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
