"""Visible normal controls over actual in-process HTTP and cold SQLite Worker."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select, update
from test_text_workflows import NoModel, draft, enqueue, instance, material, once

from sim2act.db import Store, goal_card_versions, goal_cards
from sim2act.db import fingerprint as digest
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["valid", "creation-lost", "run-lost", "false-branch", "late-open-workspace", "late-open-edit"])
def test_actual_four_step_text_page_cold_extraction(env, tmp_path, scenario):
    source, _ = draft(env)
    release, inst = instance(env, source["id"])
    source_run = enqueue(env, release, inst)
    once(env)
    rid, card = material(env, "Cedar new owner\nQuartz tomorrow\nCedar reserved\n", "md")
    # Synthetic fixture title only; real page loads the full native saved version.
    with env[0].tx() as c:
        saved = c.execute(select(goal_card_versions.c.snapshot).where(goal_card_versions.c.card_id == card["id"])).scalar()
        saved["content"]["title"] = "Unseen own target four-step goal"
        c.execute(update(goal_card_versions).where(goal_card_versions.c.card_id == card["id"]).values(snapshot=saved, fingerprint=digest(saved)))
        c.execute(update(goal_cards).where(goal_cards.c.id == card["id"]).values(title=saved["content"]["title"], fingerprint=digest(saved)))
    info = dict(project=env[5], source_run=source_run, resource=rid, scenario=scenario,
        goal_title=saved["content"]["title"], output=str(tmp_path / "page-result.json"))
    info_path = tmp_path / "info.json"
    info_path.write_text(json.dumps(info))
    stderr_path = tmp_path / "node-stderr.log"
    cold_stores = []
    worked = 0
    with stderr_path.open("w") as errors:
        process = subprocess.Popen(["node", "tests/text_workflows_ui.cjs", str(info_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
            env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
        try:
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    cold = Store(env[1].database_url, test_only=True)
                    cold_stores.append(cold)
                    assert Worker(cold, env[1], NoModel()).once()
                    worked += 1
                    answer = dict(id=request["id"], status=200, text="{}")
                else:
                    response = env[2].request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(id=request["id"], status=response.status_code, text=response.text,
                        content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
            errors.flush()
            assert code == 0, stderr_path.read_text()
            proof = json.loads((tmp_path / "page-result.json").read_text())
            assert proof["status"] == "PASS" and worked == (0 if scenario.startswith("late-open-") else 1)
            assert len(proof["static_resource_loads"]) == 20 * proof["boots"]
            for row in proof["static_resource_loads"]:
                path = Path("src/sim2act/web") / (row["path"].lstrip("/") or "index.html")
                assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for cold in cold_stores:
                cold.engine.dispose()
            output = os.environ.get("SIM2ACT_TEXT_WORKFLOW_EVIDENCE_DIR")
            if output:
                folder = Path(output)
                folder.mkdir(parents=True, exist_ok=True)
                (folder / (scenario + "-stderr.log")).write_bytes(stderr_path.read_bytes())
                if (tmp_path / "page-result.json").exists():
                    (folder / (scenario + "-page.json")).write_bytes((tmp_path / "page-result.json").read_bytes())
