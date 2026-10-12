"""Actual TestClient IPC page gestures, synthetic scoped provider, cold NoModel."""

import copy
import hashlib
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_pa_generation_provider import approved, configured, provider
from test_pa_material_bindings import NEW_CONTENT

from sim2act.api import create_app
from sim2act.db import Store, attempts
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["valid", "binding-lost", "binding-late", "scope-late"])
def test_scoped_model_generation_and_new_material_page(env, monkeypatch, tmp_path, scenario):
    data, clock = configured(env, monkeypatch)
    store, settings, client, _, pid, _, card = data
    resource = client.post(f"/api/projects/{pid}/resources", json=dict(name="fresh.md", format="md", content=NEW_CONTENT)).json()["id"]
    goal = copy.deepcopy(card["content"])
    goal.update(title="Explicit UI new-material goal", goal="逐字引用新材料全部匹配行", resource_refs=[resource])
    target = client.post(f"/api/projects/{pid}/goal-cards", json=goal).json()["id"]
    scope, _, _ = approved(data)  # Freeze all authorized material only after fixture setup.
    info = tmp_path / "info.json"
    info.write_text(json.dumps(dict(project=pid, card=card["id"], target_card=target, target_resource=resource,
        approval_id=scope["approval_id"], scenario=scenario, output=str(tmp_path / "results.json"))))
    transport, sent = provider(data, clock)
    process = subprocess.Popen(["node", "tests/pa_provider_ui.cjs", str(info)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"})
    cold = None
    cold_client = None
    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command"):
                if request["command"] == "provider-worker":
                    assert Worker(store, settings, goal_planner_transport=transport).once()
                else:
                    assert request["command"] == "cold-worker"
                    if cold is None:
                        cold = Store(settings.database_url, test_only=True)
                        cold_settings = replace(settings, goal_planner_provider="disabled",
                            application_generation_activation_enabled=False, application_generation_live_id="", live_enabled=False, token="")
                        cold_client = TestClient(create_app(cold, cold_settings))
                        cold_client.headers.update({"Authorization": "Bearer synthetic-test-A"})
                    assert Worker(cold, cold_settings).once()
                answer = dict(id=request["id"], status=200, text="{}")
            else:
                r = (cold_client or client).request(request["method"], request["path"], json=request.get("body"), headers=request.get("headers"))
                answer = dict(id=request["id"], status=r.status_code, text=r.text, content_type=r.headers.get("content-type"))
            process.stdin.write(json.dumps(answer) + "\n")
            process.stdin.flush()
        errors = process.stderr.read()
        code = process.wait(timeout=20)
        (tmp_path / "driver.log").write_text(errors)
        assert code == 0, errors
        proof = json.loads((tmp_path / "results.json").read_text())
        assert proof["status"] == "PASS" and len(proof["checks"]) >= 15
        web = Path(__file__).parents[1] / "src/sim2act/web"
        assert len(proof["loaded_source_sha256"]) == 20
        assert proof["loaded_source_sha256"] == {name: hashlib.sha256((web / name).read_bytes()).hexdigest()
            for name in proof["loaded_source_sha256"]}
        with store.tx() as c:
            assert len(c.execute(select(attempts.c.id)).all()) == len(sent) == 2
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if cold_client:
            cold_client.close()
        if cold:
            cold.engine.dispose()
        client.close()
