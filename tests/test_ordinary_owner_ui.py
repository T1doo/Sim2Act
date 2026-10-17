"""Full served page + actual authenticated ASGI + real Worker, synthetic user actions."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_goal_card_runs import authority, card

from sim2act.db import grants
from sim2act.model import MockModel
from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["accept", "reject", "navigation-unknown", "late-intent", "revocation"])
def test_ordinary_owner_full_page_actual_api(env, tmp_path, case):
    store, settings, client, owner, other, project, material = env
    assert store.sqlite and store.test_only and settings.mode == "mock" and not settings.live_enabled
    source, _ = card(env)
    alternate = store.project(owner, "Other owned project")
    store.project(other, "Other identity project")
    before = authority(store)
    info = dict(case=case, project=project, other=alternate, card=source["id"],
        output=str(tmp_path / "result.json"))
    (tmp_path / "info.json").write_text(json.dumps(info))
    calls = worker_runs = 0
    process = None
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(["node", "tests/ordinary_owner_ui.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    class CountedMock(MockModel):
                        def request(self, messages, tools):
                            nonlocal calls
                            calls += 1
                            assert {t["function"]["name"] for t in tools} == {"resource.read", "data.aggregate_csv"}
                            return super().request(messages, tools)
                    assert Worker(store, settings, CountedMock()).once()
                    worker_runs += 1
                    answer = dict(status=200, text="{}")
                elif request.get("command") == "revoke":
                    with store.tx() as c:
                        grant = dict(c.execute(select(grants).where(grants.c.principal_id == owner,
                            grants.c.resource_id == material, grants.c.tool_ref == "resource.read")).mappings().one())
                    response = client.post(f"/api/grants/{grant['id']}/revoke", json={"command": "revoke", "version": grant["revision"]})
                    answer = dict(status=response.status_code, text=response.text)
                else:
                    response = client.request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=response.status_code, text=response.text,
                        content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps({"id": request["id"], **answer})+"\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS" and worker_runs == 1 and calls == 2
        if case != "revocation":
            assert authority(store) == before
        for asset in result["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "model-boundary.json").write_text(json.dumps(dict(
            worker_runs=worker_runs, synthetic_model_calls=calls, real_model_calls=0,
            real_human_signoff="NOT_RUN", semantic_goal_acceptance="NOT_RUN",
            native_browser="NOT_RUN", pg="NOT_RUN"), indent=2))
