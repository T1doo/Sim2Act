"""Visible project cancellation gestures against actual HTTP and in-flight Worker."""

import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import httpx
import pytest
from sqlalchemy import update
from test_natural_spec_apps import transport
from test_project_account_close import one
from test_project_check_cancel import original_objects

from sim2act.db import grants
from sim2act.worker import Worker


@pytest.mark.parametrize(
    "scenario",
    ["inflight", "lost", "unknown", "revoke", "fallback_fail", "fallback_badseal", "late", "history_version"],
)
def test_project_page_exact_cancel_unknown_cold_and_permission_recovery(env, tmp_path, scenario):
    data, aid, _, inst, _, base, _, _ = one(env, key="fixture-baseline")
    saved = original_objects(data[0], "none")
    info = dict(
        project=data[4],
        selected=dict(app_id=aid, instance_id=inst["id"]),
        scenario=scenario,
        output=str(tmp_path / "result.json"),
    )
    if scenario == "late":
        made = data[2].post("/api/projects", json={"name": "Independent late receipt project"})
        assert made.status_code == 201, made.text
        peer_pid = made.json()["id"]
        peer_data, peer_aid, _, peer_inst, _, _, _, _ = one(
            (*env[:5], peer_pid, env[6]), key="peer-fixture-baseline"
        )
        info["peer"] = dict(project=peer_pid, app_id=peer_aid, instance_id=peer_inst["id"])
        peer_data[2].close()
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    sent = []
    ready = Event()
    release = Event()
    future = None

    def held(raw, payload):
        ready.set()
        assert release.wait(90), "owned in-flight Worker was not released"

    worker = Worker(data[0], data[1], goal_planner_transport=transport(sent, mutate=held))
    stderr = tmp_path / "node.stderr"
    with ThreadPoolExecutor(max_workers=1) as pool, stderr.open("w") as err:
        process = subprocess.Popen(
            ["node", str(Path(__file__).with_name("project_check_cancel.cjs")), str(path)],
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
                if request.get("action"):
                    action = request["action"]
                    if action == "pause_without_refresh":
                        response = data[2].post(
                            f"/api/internal/instances/{request['instance']}/runs/{request['run']}/commands",
                            json={"command": "pause", "version": request["version"]},
                        )
                        assert response.status_code == 200, response.text
                        (tmp_path / (action + "-public-receipt.json")).write_text(response.text)
                    elif action == "revoke":
                        with data[0].tx() as c:
                            c.execute(
                                update(grants)
                                .where(grants.c.resource_id == data[5])
                                .values(revoked=True)
                            )
                    elif action == "worker_start":
                        future = pool.submit(worker.once)
                        assert ready.wait(60), "actual Worker never entered model transport"
                    elif action == "worker_unknown":

                        def unknown(req):
                            sent.append(req.content)
                            raise httpx.ReadTimeout("synthetic page unknown model result")

                        worker.goal_planner_transport = httpx.MockTransport(unknown)
                        assert worker.once()
                    elif action == "worker_release":
                        release.set()
                        if future is not None:
                            assert future.result(timeout=90)
                            future = None
                    else:
                        raise AssertionError(action)
                    value = dict(
                        id=request["id"], status=200, text="{}", content_type="application/json"
                    )
                else:
                    response = data[2].request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers"),
                    )
                    value = dict(
                        id=request["id"],
                        status=response.status_code,
                        text=response.text,
                        content_type=response.headers.get("content-type"),
                    )
                process.stdin.write(json.dumps(value) + "\n")
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
            assert len(sent) == (1 if scenario in {"inflight", "lost", "unknown"} else 0)
            # Original rows are identical; the one new isolated CHECK is preserved and pinned.
            after = original_objects(data[0], "none")
            assert all(row in after[table] for table, rows in saved.items() for row in rows)
            assert not worker.once()
        finally:
            release.set()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
