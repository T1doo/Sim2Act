import hashlib
import json
import time
from pathlib import Path

import pytest
from sqlalchemy import select, update

from sim2act.contracts import resource_id, strict_json, validate_action
from sim2act.db import Store, grants, operations, resources, runs
from sim2act.errors import DomainError
from sim2act.tools import dispatch
from sim2act.worker import Worker


def enqueue(env, key="request-1"):
    store, s, client, a, b, pid, res = env
    response = client.post(
        f"/api/projects/{pid}/runs",
        json={"goal": "读取数据并给出有依据的结果", "resource_refs": [res], "request_key": key},
    )
    assert response.status_code == 202
    return response.json()["run_id"]


def test_sources_and_frozen_cases():
    root = Path(__file__).parents[1]
    for record in json.loads((root / "docs/sources/V5/manifest.json").read_text()):
        blob = (root / "docs/sources/V5" / record["name"]).read_bytes()
        assert len(blob) == record["bytes"]
        assert len(blob.splitlines()) == record["lines"]
        assert hashlib.sha256(blob).hexdigest() == record["sha256"]
    assert len(list((root / "tests/cases").glob("AT-*.json"))) == 28


@pytest.mark.parametrize(
    "raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '{"x":', "[" * 30 + "0" + "]" * 30]
)
def test_AT03_strict_json(raw):
    with pytest.raises(DomainError):
        strict_json(raw)


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "C:\\Users\\private.txt",
        "\\\\server\\share",
        "file.txt:stream",
        "/etc/passwd",
        "res_../../.env",
    ],
)
def test_AT03_logical_ids_only(path):
    with pytest.raises(DomainError):
        resource_id(path)


def test_AT03_manifest_and_http_duplicates(env):
    from sim2act.db import new_id

    base = {
        "schema_version": "1.0-draft",
        "action_id": new_id("action"),
        "revision": 1,
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "executor": {"kind": "bounded_agent", "ref": "intern.agent", "version": "1"},
        "allowed_tool_refs": ["resource.read"],
        "dependencies": [],
        "permission_requirements": [],
        "effect": "read",
        "preconditions": [],
        "postcheck_refs": ["receipt.readback.v1"],
        "limits": {
            "max_requests": 4,
            "max_tools": 4,
            "max_repairs": 1,
            "max_total_tokens": 64000,
            "max_output_tokens": 1024,
            "run_seconds": 300,
        },
        "idempotency": "read_only",
        "reconcile_ref": "operation.lookup.v1",
        "error_contract": ["INVALID_INPUT"],
    }
    assert validate_action(json.dumps(base)).executor.ref == "intern.agent"
    for mutation in [
        {"effect": "external_write"},
        {"script": "print(1)"},
        {"executor": {"kind": "registered_tool", "ref": "os.system", "version": "1"}},
        {"input_schema": {"type": "object", "$ref": "https://bad"}},
    ]:
        with pytest.raises(DomainError):
            validate_action(json.dumps(base | mutation))
    client = env[2]
    assert (
        client.post(
            "/api/projects",
            content='{"name":"one","name":"two"}',
            headers={"Content-Type": "application/json"},
        ).status_code
        == 400
    )


def test_AT04_cross_principal_project_and_run(env):
    store, s, client, a, b, pid, res = env
    rid = enqueue(env)
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    for route in [
        f"/api/resources/{res}",
        f"/api/runs/{rid}",
        f"/api/projects/{pid}/resources",
        f"/api/projects/{pid}/runs",
        f"/api/projects/{pid}/grants",
    ]:
        response = client.get(route)
        assert response.status_code == 403
        assert "1.25" not in response.text
    other = client.post("/api/projects", json={"name": "other"}).json()["id"]
    assert (
        client.post(
            f"/api/projects/{other}/runs",
            json={"goal": "guess", "resource_refs": [res], "request_key": "x"},
        ).status_code
        == 403
    )
    client.headers.pop("Authorization")
    assert client.get("/api/projects").status_code == 403


def test_AT05_persist_accept_reopen_and_worker(env):
    store, s, client, a, b, pid, res = env
    rid = enqueue(env)
    assert client.get(f"/api/runs/{rid}").json()["status"] == "QUEUED"
    if store.sqlite:
        reopened = Store(s.database_url, test_only=True)
        assert reopened.inspect(a, rid)["status"] == "QUEUED"
        reopened.engine.dispose()
    assert Worker(store, s).once()
    result = client.get(f"/api/runs/{rid}").json()
    assert result["status"] == "PARTIAL"  # F1 cannot declare full goal acceptance.
    assert result["result"]["mode"] == "MOCK"
    assert result["result"]["goal_acceptance"] == "NOT_RUN"
    assert (
        result["result"]["receipts"][0]["data"]["hash"]
        == hashlib.sha256(b"item,amount\na,1.25\nb,2.75\n").hexdigest()
    )


def test_idempotent_accept_and_conflict(env):
    rid = enqueue(env)
    assert enqueue(env) == rid
    _, _, client, _, _, pid, res = env
    assert (
        client.post(
            f"/api/projects/{pid}/runs",
            json={"goal": "changed", "resource_refs": [res], "request_key": "request-1"},
        ).status_code
        == 409
    )


def test_AT06_transaction_crash_recovery_and_fence(env):
    store, s, client, a, b, pid, res = env
    rid = enqueue(env)
    old = store.claim("old-worker", 30)
    call = {
        "id": "local-write",
        "function": {"name": "artifact.save_text"},
        "args": {"text": "verified content"},
    }
    with pytest.raises(RuntimeError):
        dispatch(store, rid, old["fence"], call, crash_before_commit=True)
    with store.engine.connect() as c:
        assert not c.execute(select(operations).where(operations.c.run_id == rid)).first()
    receipt = dispatch(store, rid, old["fence"], call)
    assert dispatch(store, rid, old["fence"], call) == receipt
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(lease_until=time.time() - 1))
    recovered = store.claim("new-worker", 30)
    assert recovered["fence"] > old["fence"]
    with pytest.raises(DomainError, match="Stale"):
        dispatch(store, rid, old["fence"], {**call, "id": "stale-new-effect"})
    assert dispatch(store, rid, recovered["fence"], call) == receipt
    with store.engine.connect() as c:
        assert (
            len(c.execute(select(resources).where(resources.c.content == "verified content")).all())
            == 1
        )


@pytest.mark.parametrize("expired", [False, True])
def test_AT08_revoke_expire_dispatch_and_cached_visibility(env, expired):
    store, s, client, a, b, pid, res = env
    rid = enqueue(env)
    worker = store.claim("worker", 30)
    with store.tx() as c:
        c.execute(
            update(grants).where(grants.c.resource_id == res).values(expires_at=time.time() - 1)
            if expired
            else update(grants).where(grants.c.resource_id == res).values(revoked=True, revision=2)
        )
    with pytest.raises(DomainError) as e:
        dispatch(
            store,
            rid,
            worker["fence"],
            {"id": "read", "function": {"name": "resource.read"}, "args": {"resource_id": res}},
        )
    assert e.value.code == "GRANT_REVOKED"
    assert client.get(f"/api/resources/{res}").status_code == 403
    assert client.get(f"/api/runs/{rid}").status_code == 403
    assert client.get(f"/api/projects/{pid}/resources").json() == []


def test_command_version_and_no_new_dispatch(env):
    store, s, client, a, b, pid, res = env
    rid = enqueue(env)
    old = store.claim("worker", 30)
    version = client.get(f"/api/runs/{rid}").json()["version"]
    assert (
        client.post(
            f"/api/runs/{rid}/commands", json={"command": "pause", "version": version}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/runs/{rid}/commands", json={"command": "cancel", "version": version}
        ).status_code
        == 409
    )
    with pytest.raises(DomainError):
        dispatch(
            store,
            rid,
            old["fence"],
            {"id": "read", "function": {"name": "resource.read"}, "args": {"resource_id": res}},
        )


def test_aggregate_independent_decimal_oracle(env):
    store, s, client, a, b, pid, res = env
    rid = enqueue(env)
    run = store.claim("worker", 30)
    receipt = dispatch(
        store,
        rid,
        run["fence"],
        {
            "id": "sum",
            "function": {"name": "data.aggregate_csv"},
            "args": {"resource_id": res, "column": "amount"},
        },
    )
    assert receipt["data"]["sum"] == "4.00"  # independent fixture oracle: 1.25 + 2.75
    assert receipt["data"]["count"] == 2


def test_revoked_material_read_cannot_be_bypassed_by_aggregate_grant(env):
    store, s, client, a, b, pid, res = env
    rid = enqueue(env)
    run = store.claim("worker", 30)
    with store.tx() as c:
        c.execute(
            update(grants)
            .where(grants.c.resource_id == res, grants.c.tool_ref == "resource.read")
            .values(revoked=True)
        )
    with pytest.raises(DomainError) as e:
        dispatch(
            store,
            rid,
            run["fence"],
            {
                "id": "sum",
                "function": {"name": "data.aggregate_csv"},
                "args": {"resource_id": res, "column": "amount"},
            },
        )
    assert e.value.code == "GRANT_REVOKED"


def test_revoked_output_artifact_blocks_history_readback(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "synthetic local artifact", [], "output-revoke")
    Worker(store, s).once()
    result = client.get(f"/api/runs/{rid}").json()
    artifact = result["result"]["receipts"][0]["artifact_refs"][0]
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == artifact).values(revoked=True))
    assert client.get(f"/api/resources/{artifact}").status_code == 403
    assert client.get(f"/api/runs/{rid}").status_code == 403
