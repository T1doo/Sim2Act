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
sys.path.insert(0, "/workspace/Sim2Act-native-session-diagnostic/tests")
from protocol_terminal_setup import prepare


@pytest.mark.parametrize("optimized", [False, True])
def test_conditional_bound_native_shared_actual_http(tmp_path, monkeypatch, optimized):
    if optimized:
        monkeypatch.setenv("PYTHONOPTIMIZE", "1")
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
    repo = Path('/workspace/Sim2Act-native-session-diagnostic')
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
    fresh_seed = subprocess.run([
        sys.executable, "scripts/protocol-ui/fixture.py", "--root", str(tmp_path / "fresh"),
        "--port", str(port), "--action", "seed"], env=child, cwd=repo,
        capture_output=True, text=True, timeout=30)
    assert fresh_seed.returncode == 0, fresh_seed.stdout + fresh_seed.stderr
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
        prepare(tmp_path)
        sys.path.insert(0, str(repo / "scripts/protocol-ui"))
        from rotation import run_node

        with (tmp_path / "driver.log").open("wb") as output:
            run_node(["node", "tests/conditional_runs_native.cjs", str(tmp_path), sys.executable],
                     server, tmp_path, repo, child, timeout=60, stdout=output, stderr=output)
        result = json.loads((tmp_path / "bound-native-results.json").read_text())
        assert result["status"] == "PASS" and result["bound"]["real_model_requests"] == 0
        assert len(result["bound"]["checks"]) == 19 and len(result["manual"]["checks"]) == 22
        assert result["transition"]["old_all_tables_retained"] is True
        assert result["transition"]["max_concurrent_protocol_servers"] == 1
        terminal=json.loads((tmp_path/"old-terminal-receipt.json").read_text())
        assert terminal["jobs"]==5 and terminal["actual_mock_attempts"]==4 and terminal["queued"]==0
        assert terminal["real_model_requests"]==0
        transition=result["transition"]
        assert transition["old_before"]["tables"]==transition["old_after"]["tables"]
        old_info=json.loads((tmp_path/"info.json").read_text())
        fresh_info=json.loads((tmp_path/"fresh/info.json").read_text())
        assert old_info["source"] != fresh_info["source"]
        assert old_info["project"] != fresh_info["project"]
        assert transition["fresh_current_source"]["resource"]==fresh_info["source"]
        assert transition["separate_authority_baselines"] is True
        bound=result["bound"]
        assert bound["semanticStatus"]=="UNKNOWN" and bound["overallAcceptance"]=="NOT_ACCEPTED"
        assert bound["actual_mock_requests"]==4
        assert bound["durable"]["after"]["attempts_count"]-bound["durable"]["before"]["attempts_count"]==4
        assert bound["durable"]["after"]["resource_reads_count"]-bound["durable"]["before"]["resource_reads_count"]==2
        assert bound["durable"]["after"]["grants"]==bound["durable"]["before"]["grants"]
        assert bound["durable"]["after"]["principals"]==bound["durable"]["before"]["principals"]
        safe={"optimized":optimized,"status":"PASS","old_terminal":terminal,"transition":transition,
              "bound":bound,"manual_checks":len(result["manual"]["checks"]),"native":"NOT_RUN","pixels":"NOT_RUN"}
        evidence=Path("/tmp/native-session-failure-independent-review")/("combo-optimized.json" if optimized else "combo-normal.json")
        evidence.write_text(json.dumps(safe,indent=2))
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
