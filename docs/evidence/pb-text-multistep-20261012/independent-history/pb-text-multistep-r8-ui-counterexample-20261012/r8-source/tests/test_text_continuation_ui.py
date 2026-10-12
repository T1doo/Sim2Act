"""Visible shipped page, real local TestClient and Worker, exact approved old DB.

The old source and initial native Goal bodies are denied by evaluating-cell SQL
barriers for the whole cold flow. No native browser or live provider is involved.
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select, update
from test_persistent_app_runs import NoModel
from test_text_continuations import legacy  # noqa: F401
from test_text_logic_reuse import source_barrier

from sim2act.db import Store, goal_card_versions, goal_cards, grants
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["valid", "commit-lost"])
def test_existing_software_continuation_visible_cold_page(legacy, tmp_path, scenario):  # noqa: F811
    store, settings, client, old = legacy
    data = (store, settings, client, old["owner"], old["project"], old["old_private"]["resource"], None)
    private = old["old_private"]
    with store.tx() as c:
        ids = set(c.execute(select(goal_cards.c.id).where(goal_cards.c.project_id == old["project"])).scalars())
    if old.get("goal"):
        ids.remove(old["goal"]["card_id"])
    barrier = source_barrier(data, private["app"], private["release"], private["instance"], private["run"])
    barrier.rules["goal_card_versions"] = (goal_card_versions, "card_id", ids, {"snapshot"})
    info = dict(project=old["project"], instance=old["instance"]["id"], old_source=private["app"],
        old_run=private["run"]["id"], old_resource=private["resource"], source_implementation=old["software_fp"],
        scenario=scenario, fixture_time=old["fixture_time"], output=str(tmp_path / "result.json"))
    (tmp_path / "info.json").write_text(json.dumps(info))
    stderr = tmp_path / "node-stderr.log"
    cold_stores = []
    worked = 0
    with stderr.open("w") as errors, barrier:
        process = subprocess.Popen(["node", "tests/text_continuation_ui.cjs", str(tmp_path / "info.json")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
            env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
        try:
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "revoke-target":
                    with store.tx() as c:
                        c.execute(update(grants).where(grants.c.principal_id == old["app"]["runtime_id"]).values(revoked=True))
                    answer = dict(id=request["id"], status=200, text="{}")
                elif request.get("command") == "worker":
                    cold = Store(settings.database_url, test_only=True)
                    cold_stores.append(cold)
                    barrier.attach(cold)
                    assert Worker(cold, settings, NoModel()).once()
                    worked += 1
                    answer = dict(id=request["id"], status=200, text="{}")
                else:
                    response = client.request(request["method"], request["path"], json=request.get("body"), headers=request.get("headers"))
                    answer = dict(id=request["id"], status=response.status_code, text=response.text, content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
            errors.flush()
            assert code == 0, stderr.read_text()
            proof = json.loads((tmp_path / "result.json").read_text())
            assert proof["status"] == "PASS" and worked == 1 and not barrier.blocked
            assert len(proof["static_resource_loads"]) == 20 * proof["boots"]
            web = Path(__file__).parents[1] / "src/sim2act/web"
            for row in proof["static_resource_loads"]:
                asset = web / (row["path"].lstrip("/") or "index.html")
                assert hashlib.sha256(asset.read_bytes()).hexdigest() == row["sha256"]
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            destination = os.environ.get("SIM2ACT_TEXT_CONTINUATION_EVIDENCE")
            if destination:
                folder = Path(destination)
                folder.mkdir(parents=True, exist_ok=True)
                stem = ("a747" if old.get("goal") else "233") + "-" + scenario
                for file, suffix in [(stderr, ".log"), (tmp_path / "result.json", ".json")]:
                    if file.exists():
                        (folder / (stem + suffix)).write_bytes(file.read_bytes())
                (folder / (stem + "-exit.json")).write_text(json.dumps({"exit_code": process.returncode, "workers": worked, "private_evaluations": barrier.blocked}))
                (folder / (stem + "-sql.json")).write_text(json.dumps({"private_evaluations": barrier.blocked, "evaluated_cells": barrier.evaluated, "statements": barrier.statements}))
    for cold in cold_stores:
        cold.engine.dispose()
