"""Actual served ordinary correction page/API/Worker; simulated users, no live model."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_ordinary_corrections import CorrectionModel, original_rows
from test_ordinary_goal_md import ScriptedMd, card

from sim2act.db import grants, run_contracts, runs
from sim2act.model import MockModel
from sim2act.worker import Worker


@pytest.mark.parametrize(
    "case",
    [
        "correction-md",
        "correction-v1",
        "correction-unknown",
        "correction-retry",
        "correction-navigation",
        "correction-revoked",
    ],
)
def test_visible_explicit_ordinary_correction(env, tmp_path, case):
    store, settings, client, owner, other, pid, _ = env
    assert store.sqlite and settings.mode == "mock" and not settings.live_enabled
    goal, source = card(env)
    detail = client.get(f"/api/goal-cards/{goal['id']}").json()
    md = case != "correction-v1"
    alternate = store.project(owner, "Other owned correction project")
    info = dict(
        case=case,
        require_md=md,
        project=pid,
        other=alternate,
        card=goal["id"],
        card_title=detail["content"]["title"],
        expected_unresolved=detail["content"]["unresolved"][0],
        expected_check=detail["content"]["acceptance_checks"][0],
        output=str(tmp_path / "result.json"),
    )
    (tmp_path / "info.json").write_text(json.dumps(info))
    parent_model = ScriptedMd(source) if md else MockModel()
    models, parent_before, workers, process = [], None, 0, None
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
                    if not workers:
                        model = parent_model
                    else:
                        with store.tx() as c:
                            snapshot = c.execute(
                                select(run_contracts.c.snapshot)
                                .join(runs, runs.c.id == run_contracts.c.run_id)
                                .where(runs.c.status == "QUEUED")
                            ).scalar_one()
                        parent = snapshot["ordinary_correction"]["feedback"]["parent_run_id"]
                        parent_before = original_rows(store, parent)
                        model = CorrectionModel(
                            source, snapshot["ordinary_correction"]["feedback"], md
                        )
                    models.append(model)
                    assert Worker(store, settings, model).once()
                    workers += 1
                    answer = dict(status=200, text="{}")
                elif request.get("command") == "revoke":
                    with store.tx() as c:
                        grant = dict(
                            c.execute(
                                select(grants).where(
                                    grants.c.principal_id == owner,
                                    grants.c.resource_id == source,
                                    grants.c.tool_ref == "resource.read",
                                )
                            )
                            .mappings()
                            .one()
                        )
                    reply = client.post(
                        f"/api/grants/{grant['id']}/revoke",
                        json={"command": "revoke", "version": grant["revision"]},
                    )
                    answer = dict(status=reply.status_code, text=reply.text)
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
        assert workers == (1 if case == "correction-revoked" else 2)
        if parent_before:
            after = original_rows(store, result["parent"])
            assert {k: v for k, v in parent_before.items() if k != "resources"} == {
                k: v for k, v in after.items() if k != "resources"
            }
            assert all(after["resources"][k] == v for k, v in parent_before["resources"].items())
            (tmp_path / "parent-before.json").write_text(
                json.dumps(parent_before, ensure_ascii=False, indent=2)
            )
            (tmp_path / "parent-after.json").write_text(
                json.dumps(after, ensure_ascii=False, indent=2)
            )
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "model-boundary.json").write_text(
            json.dumps(
                dict(
                    actual_worker_objects=workers,
                    separate_process_restart="NOT_RUN",
                    real_model_requests=0,
                    real_human_signoff="NOT_RUN",
                    semantic_acceptance="NOT_RUN",
                    child_synthetic_requests=[m.calls for m in models[1:]],
                    pg="NOT_RUN",
                    native_browser="NOT_RUN",
                    windows="NOT_RUN",
                ),
                indent=2,
            )
        )
