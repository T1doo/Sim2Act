import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_project_account_close import one

ROOT = Path(__file__).parent


@pytest.mark.parametrize("scenario", ["normal", "lost", "active"])
def test_ordinary_page_unstarted_close_cold_recovery_explicit_next(env, tmp_path, scenario):
    data, aid, _, inst, _, base, _, _ = one(env, key="fixture-baseline")
    info = dict(
        project=data[4],
        selected=dict(app_id=aid, instance_id=inst["id"]),
        scenario=scenario,
        output=str(tmp_path / "result.json"),
    )
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    stderr = tmp_path / "node.stderr"
    with stderr.open("w") as err:
        process = subprocess.Popen(
            ["node", str(ROOT / "project_account_close.cjs"), str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=err,
            text=True,
            env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
        )
        try:
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                response = data[2].request(
                    request["method"],
                    request["path"],
                    json=request.get("body"),
                    headers=request.get("headers"),
                )
                process.stdin.write(
                    json.dumps(
                        dict(
                            id=request["id"],
                            status=response.status_code,
                            text=response.text,
                            content_type=response.headers.get("content-type"),
                        )
                    )
                    + "\n"
                )
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
            assert code == 0, stderr.read_text()
            result = json.loads((tmp_path / "result.json").read_text())
            assert result["status"] == "PASS", result.get("error")
            for asset in result["static_resource_loads"]:
                name = "index.html" if asset["path"] == "/" else asset["path"][1:]
                assert (
                    asset["sha256"]
                    == hashlib.sha256(
                        (Path(__file__).parents[1] / "src/sim2act/web" / name).read_bytes()
                    ).hexdigest()
                )
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
