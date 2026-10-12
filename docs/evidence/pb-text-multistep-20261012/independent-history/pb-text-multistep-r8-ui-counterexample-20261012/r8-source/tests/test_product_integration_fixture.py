import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "scripts" / "agent-ui"))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import runs


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_existing_agent_seed_and_fifo_normal_worker(tmp_path):
    original = load("original_agent_fixture", "scripts/agent-ui/fixture.py")
    glue = load("integration_fixture", "scripts/agent-ui/integration_fixture.py")
    original.seed(tmp_path, 8123)
    info = json.loads((tmp_path / "info.json").read_text())["integration"]
    store, settings = glue.context(tmp_path)
    try:
        with TestClient(create_app(store, settings)) as c:
            c.headers.update({"Authorization": "Bearer synthetic-agent-ui-A"})
            instance = c.get("/api/internal/instances/" + info["instance"]).json()
            accepted = []
            for column in ["amount", "tax"]:
                response = c.post(
                    "/api/internal/instances/" + info["instance"] + "/runs",
                    json={
                        "expected_revision": instance["revision"],
                        "expected_release_fingerprint": instance["release_fingerprint"],
                        "input": {"column": column},
                        "request_key": "glue-" + column,
                    },
                )
                assert response.status_code == 202
                accepted.append(response.json()["run_id"])
            with pytest.raises(AssertionError, match="Target must be actual oldest"):
                glue.integration_worker(tmp_path, accepted[1])
            with store.tx() as conn:
                assert all(
                    conn.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
                    == "QUEUED"
                    for rid in accepted
                )
            for rid in accepted:
                assert glue.integration_worker(tmp_path, rid)["status"] == "PASS"
            actual = c.get("/api/internal/instances/" + info["instance"]).json()
            assert actual["data_version"] == 2 and len(actual["data"]) == 2
            (tmp_path / "glue-proof.json").write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "new_identity": False,
                        "fifo_wrong_target_refused_without_mutation": True,
                        "actual_results": [
                            (r["version"], r["data"]["result"]["sum"]) for r in actual["data"]
                        ],
                        "real_model_requests": 0,
                    },
                    indent=2,
                )
            )
    finally:
        store.engine.dispose()
