"""Real authenticated HTTP generation from durable CSV runs; provider forbidden."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from test_internal_api import enqueue, instance, path, release
from test_persistent_app_runs import NoModel

from sim2act.api import create_app
from sim2act.db import Store, app_drafts, grants, principals, runs
from sim2act.worker import Worker


def source_and_target(env):
    client = env[2]
    rel, _, _ = release(env)
    inst = instance(env, rel)
    queued = enqueue(env, inst, rel)
    assert queued.status_code == 202
    job = queued.json()
    assert Worker(env[0], env[1], NoModel()).once()
    assert client.get(path(inst, job)).json()["status"] == "SUCCEEDED"
    resource = client.post(
        f"/api/projects/{env[5]}/resources",
        json={"name": "new.csv", "format": "csv", "content": "amount,other\n10,7\n20,8\n"},
    ).json()["id"]
    target = client.post(
        f"/api/projects/{env[5]}/apps/csv-preview",
        json={"name": "existing target", "resource_id": resource, "goal": "target scope"},
    ).json()["id"]
    url = path(inst, job)
    options = client.get(url + "/extraction-options")
    assert options.status_code == 200, options.text
    data = options.json()
    item = next(t for t in data["targets"] if t["id"] == target)
    body = {
        "expected_proof_fingerprint": data["proof_fingerprint"],
        "target_app_id": target,
        "expected_target_draft_fingerprint": item["fingerprint"],
        "name": "Saved successful task",
        "request_key": "generation-request",
    }
    return url, body, data


def counts(env):
    with env[0].tx() as c:
        return {
            "principals": c.execute(select(func.count()).select_from(principals)).scalar_one(),
            "runs": c.execute(select(func.count()).select_from(runs)).scalar_one(),
            "grants": [dict(g) for g in c.execute(select(grants).order_by(grants.c.id)).mappings()],
        }


def test_http_server_generated_candidate_cold_new_input_no_permissions(env):
    url, body, _ = source_and_target(env)
    before = counts(env)
    made = env[2].post(url + "/extract", json=body)
    assert made.status_code == 201, made.text
    result = made.json()
    assert result["model_requests"] == 0 and result["publishable"] is False
    assert result["formal_publication_enabled"] is False
    repeated = env[2].post(url + "/extract", json=body)
    assert repeated.status_code == 201 and repeated.json()["id"] == result["id"]
    assert counts(env) == before
    cold = Store(env[1].database_url, test_only=True)
    if not cold.sqlite:
        cold.engine = cold.engine.execution_options(**env[0].engine.get_execution_options())
    with TestClient(create_app(cold, env[1])) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        draft = client.get("/api/apps/" + result["id"])
        assert draft.status_code == 200, draft.text
        candidate = draft.json()["candidate"]
        assert candidate["manifest"]["source_run_ref"] == url.rsplit("/", 1)[1]
        assert candidate["task_proof"]["proof"]["kind"] == "completed_registered_csv_apprun.v1"
        cold_env = (cold, env[1], client, *env[3:])
        rel, _, _ = release(cold_env, result["id"], result["candidate_fingerprint"])
        inst = instance(cold_env, rel, "cold-generated-instance")
        queued = enqueue(cold_env, inst, rel, "cold-generated-run", "other")
        assert queued.status_code == 202, queued.text
        assert Worker(cold, env[1], NoModel()).once()
        actual = client.get(path(inst, queued.json())).json()
        assert actual["status"] == "SUCCEEDED" and actual["result"]["sum"] == "15"
        assert actual["result_version"] == 1
        assert actual["result"]["sum"] != "4.00"
    cold.engine.dispose()
    assert counts(env)["grants"] == before["grants"]


@pytest.mark.parametrize(
    "field",
    [
        "candidate",
        "manifest",
        "actions",
        "runtime",
        "resource_id",
        "column",
        "goal",
        "limits",
        "executor",
        "offline_replay",
        "protocol",
        "provider",
        "gold",
    ],
)
def test_http_caller_executable_or_privilege_fields_refused(env, field):
    url, body, _ = source_and_target(env)
    before = counts(env)
    with env[0].tx() as c:
        drafts_before = c.execute(select(func.count()).select_from(app_drafts)).scalar_one()
    response = env[2].post(url + "/extract", json={**body, field: {}})
    assert response.status_code == 422, response.text
    assert counts(env) == before
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(app_drafts)).scalar_one() == drafts_before


def test_http_identity_instance_scope_and_changed_idempotent_input(env):
    url, body, _ = source_and_target(env)
    assert env[2].post(url + "/extract", json=body).status_code == 201
    assert env[2].post(url + "/extract", json={**body, "name": "changed"}).status_code == 409
    wrong_scope = url.replace(url.split("/")[4], "instance_" + "0" * 32)
    assert env[2].get(wrong_scope + "/extraction-options").status_code == 403
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].get(url + "/extraction-options").status_code == 403
    assert env[2].post(url + "/extract", json=body).status_code == 403


def test_http_stale_target_and_source_revocation_reject_cached_generation(env):
    url, body, _ = source_and_target(env)
    assert (
        env[2]
        .post(url + "/extract", json={**body, "expected_target_draft_fingerprint": "0" * 64})
        .status_code
        == 409
    )
    made = env[2].post(url + "/extract", json=body)
    assert made.status_code == 201, made.text
    before = counts(env)
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
    assert env[2].get(url + "/extraction-options").status_code == 403
    assert env[2].post(url + "/extract", json=body).status_code == 403
    assert counts(env)["principals"] == before["principals"]


def test_real_http_dom_generation_entry_and_lost_receipt(env):
    import json
    import shutil
    import socket
    import subprocess
    import threading
    import time

    import uvicorn

    if not shutil.which("node"):
        pytest.skip("Optional HTTP-backed DOM check requires Node; not a native browser check")
    dependency = subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )
    if dependency.returncode:
        pytest.skip(
            "Optional HTTP-backed DOM check requires developer jsdom via module path or NODE_PATH"
        )
    url, body, _ = source_and_target(env)
    instance_id, run_id = url.split("/")[4], url.split("/")[6]
    source_app = env[2].get("/api/internal/instances/" + instance_id).json()["source_app_id"]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(env[0], env[1]), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 10
        while not server.started:
            assert thread.is_alive() and time.time() < deadline
            time.sleep(0.02)
        before = counts(env)
        result = subprocess.run(
            [
                "node",
                "tests/registered_run_generation_dom.cjs",
                json.dumps(
                    {
                        "base": f"http://127.0.0.1:{port}",
                        "pid": env[5],
                        "sourceApp": source_app,
                        "iid": instance_id,
                        "rid": run_id,
                        "target": body["target_app_id"],
                    }
                ),
            ],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        checked = json.loads(result.stdout.strip())
        assert len(checked["checks"]) == 16 and checked["browser"] == "NOT_RUN"
        after = counts(env)
        assert after["principals"] == before["principals"] and after["runs"] == before["runs"]
        expected_grants = [dict(g) for g in before["grants"]]
        revoked = next(g for g in expected_grants if g["id"] == checked["revokedGrantId"])
        revoked.update(revoked=True, revision=revoked["revision"] + 1)
        assert after["grants"] == expected_grants
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
