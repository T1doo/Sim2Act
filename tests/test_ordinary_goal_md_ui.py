"""Served full-page/ASGI/registered tool MD delivery; only simulated user declarations."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from test_ordinary_goal_md import REPORT, ScriptedMd, card

from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["md-deliver", "md-navigation", "md-missing", "md-partial-file"])
def test_saved_goal_md_actual_page(env, tmp_path, case):
    store, settings, client, owner, other, pid, _ = env
    assert store.sqlite and settings.mode == "mock" and not settings.live_enabled
    goal, source = card(env)
    detail = client.get(f"/api/goal-cards/{goal['id']}").json()
    alternate = store.project(owner, "Other owned project")
    info = dict(
        case=case,
        require_md=True,
        project=pid,
        other=alternate,
        card=goal["id"],
        card_title=detail["content"]["title"],
        expected_unresolved=detail["content"]["unresolved"][0],
        expected_check=detail["content"]["acceptance_checks"][0],
        report=REPORT,
        output=str(tmp_path / "result.json"),
    )
    (tmp_path / "info.json").write_text(json.dumps(info))
    model = ScriptedMd(
        source,
        "missing"
        if case == "md-missing"
        else "sequential"
        if case == "md-partial-file"
        else "normal",
    )
    workers = 0
    process = None
    try:
        with (tmp_path / "node.stderr").open("w") as error:
            process = subprocess.Popen(
                ["node", "tests/ordinary_owner_ui.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=error,
                text=True,
                env={
                    **os.environ,
                    "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules"),
                },
            )
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    assert Worker(store, settings, model).once()
                    workers += 1
                    answer = dict(status=200, text="{}")
                else:
                    reply = client.request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers"),
                    )
                    answer = dict(
                        status=reply.status_code,
                        text=reply.text,
                        content_type=reply.headers.get("content-type"),
                    )
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS"
        for asset in result["assets"]:
            path = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
        assert workers == 1 and model.calls == (2 if case == "md-missing" else 3)
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "model-boundary.json").write_text(
            json.dumps(
                dict(
                    actual_worker_instances=workers,
                    separate_worker_process_restart="NOT_RUN",
                    synthetic_model_requests=model.calls,
                    real_model_requests=0,
                    real_human_signoff="NOT_RUN",
                    semantic_acceptance="NOT_RUN",
                    pg="NOT_RUN",
                    native_browser="NOT_RUN",
                ),
                indent=2,
            )
        )
