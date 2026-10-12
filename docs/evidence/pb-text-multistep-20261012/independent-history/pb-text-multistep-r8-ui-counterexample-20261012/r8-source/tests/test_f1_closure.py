import copy
import hashlib
import json

import pytest
from sqlalchemy import func, select, update
from test_contract_semantics import action_fixture, manifest_fixture

from sim2act.contracts import Limits
from sim2act.db import attempts, grants, operations, resources, run_contracts, runs
from sim2act.errors import DomainError
from sim2act.preflight import preflight
from sim2act.worker import Worker


def counts(store):
    with store.engine.connect() as c:
        return tuple(
            c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [runs, run_contracts, resources, operations, grants]
        )


def test_AT04_cross_project_denial_has_no_database_side_effects(env):
    store, s, client, a, b, pid, res = env
    other = client.post("/api/projects", json={"name": "second project"}).json()["id"]
    before = counts(store)
    assert (
        client.post(
            f"/api/projects/{other}/runs",
            json={"goal": "cross project", "resource_refs": [res], "request_key": "denied"},
        ).status_code
        == 403
    )
    assert counts(store) == before
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert (
        client.post(
            f"/api/projects/{pid}/resources",
            json={"name": "denied", "format": "txt", "content": "no write"},
        ).status_code
        == 403
    )
    assert counts(store) == before


def test_AT08_real_revoke_checks_owner_version_and_effect(env):
    store, s, client, a, b, pid, res = env
    items = client.get(f"/api/projects/{pid}/grants").json()
    g = next(
        x
        for x in items
        if x["resource_id"] == res and x["principal_id"] == a and x["tool_ref"] == "resource.read"
    )
    before = counts(store)
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert (
        client.post(
            f"/api/grants/{g['id']}/revoke", json={"command": "revoke", "version": g["revision"]}
        ).status_code
        == 403
    )
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    assert (
        client.post(
            f"/api/grants/{g['id']}/revoke",
            json={"command": "revoke", "version": g["revision"] + 1},
        ).status_code
        == 409
    )
    assert client.get(f"/api/resources/{res}").status_code == 200
    assert (
        client.post(
            f"/api/grants/{g['id']}/revoke", json={"command": "revoke", "version": g["revision"]}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/grants/{g['id']}/revoke", json={"command": "revoke", "version": g["revision"]}
        ).status_code
        == 409
    )
    assert client.get(f"/api/resources/{res}").status_code == 403
    assert (
        client.post(
            f"/api/projects/{pid}/runs",
            json={"goal": "after revoke", "resource_refs": [res], "request_key": "revoked"},
        ).status_code
        == 403
    )
    assert counts(store) == before


def test_AT05_acceptance_freezes_goal_input_policy_atomically(env):
    store, s, client, a, b, pid, res = env
    body = {"goal": "frozen goal", "resource_refs": [res], "request_key": "frozen"}
    rid = client.post(f"/api/projects/{pid}/runs", json=body).json()["run_id"]
    r = client.get(f"/api/runs/{rid}").json()["contract"]
    assert r["snapshot"]["goal"]["goal"] == "frozen goal"
    assert r["snapshot"]["goal"]["acceptance_version"] == "F1-tool-chain.v1"
    assert r["snapshot"]["resources"][0]["revision"] == 1
    assert (
        r["snapshot"]["resources"][0]["content_hash"]
        == hashlib.sha256(b"item,amount\na,1.25\nb,2.75\n").hexdigest()
    )
    before = counts(store)
    assert client.post(f"/api/projects/{pid}/runs", json=body).json()["run_id"] == rid
    assert counts(store) == before
    policy = {
        "limits": r["snapshot"]["limits"] | {"max_requests": 1},
        "mode": "mock",
        "request_model": "intern-s2",
    }
    with pytest.raises(DomainError):
        store.submit(a, pid, body["goal"], [res], body["request_key"], policy=policy)
    assert counts(store) == before


@pytest.mark.parametrize("change", ["resource", "goal", "contract", "legacy"])
def test_AT03_changed_frozen_contract_cannot_dispatch(env, change):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "frozen", [res], "frozen")
    with store.tx() as c:
        if change == "resource":
            c.execute(
                update(resources)
                .where(resources.c.id == res)
                .values(content="altered", hash=hashlib.sha256(b"altered").hexdigest())
            )
        elif change == "goal":
            c.execute(update(runs).where(runs.c.id == rid).values(goal="different"))
        elif change == "legacy":
            c.execute(run_contracts.delete().where(run_contracts.c.run_id == rid))
        else:
            snapshot = dict(
                c.execute(
                    select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid)
                ).scalar_one()
            )
            snapshot["limits"] = snapshot["limits"] | {"max_requests": 1}
            c.execute(
                update(run_contracts).where(run_contracts.c.run_id == rid).values(snapshot=snapshot)
            )

    class Never:
        def request(self, *args):
            raise AssertionError("No request allowed on changed contract")

    assert Worker(store, s, Never()).once()
    with store.engine.connect() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == "FAILED"
        assert not c.execute(select(operations.c.id).where(operations.c.run_id == rid)).first()


def test_AT07_frozen_request_budget_survives_larger_worker_config(env):
    store, s, client, a, b, pid, res = env
    policy = {
        "limits": Limits(
            max_requests=1,
            max_tools=1,
            max_repairs=0,
            max_total_tokens=64000,
            max_output_tokens=1024,
            run_seconds=300,
        ).model_dump(),
        "mode": "mock",
        "request_model": "intern-s2",
    }
    rid = store.submit(a, pid, "bounded", [], "bounded", policy=policy)
    Worker(store, s).once()
    r = store.inspect(a, rid)
    assert r["status"] == "FAILED" and r["error"]["code"] == "BUDGET_EXHAUSTED"
    with store.engine.connect() as c:
        assert (
            c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar_one()["requests"] == 1
        )
    assert len(r["known_effects"]) == 1


def preflight_fixture(res):
    action = action_fixture(res)
    manifest = manifest_fixture()
    manifest["input_schema"] = copy.deepcopy(action["input_schema"])
    manifest["output_schema"]["required"] = ["text"]
    manifest["action_bindings"][0]["action_id"] = action["action_id"]
    manifest["workflow"][0]["inputs"] = {
        k: {"source": "input", "field": k} for k in ["amount", "kind"]
    }
    manifest["outputs"] = {"text": {"source": "step", "ref": "read", "field": "text"}}
    manifest["permission_requirements"] = copy.deepcopy(action["permission_requirements"])
    manifest["dependency_lock"] = copy.deepcopy(action["dependencies"]) + [
        {"kind": "prompt", "ref": "intern.system.v1", "version": "1"},
        {"kind": "resource", "ref": res, "version": "1"},
        {"kind": "check", "ref": "receipt.readback.v1", "version": "1"},
    ]
    return manifest, action


def test_AT03_preflight_resolves_connections_permissions_without_execution(env):
    store, s, client, a, b, pid, res = env
    m, action = preflight_fixture(res)
    before = counts(store)
    response = client.post(
        f"/api/projects/{pid}/contracts/preflight", json={"manifest": m, "actions": [action]}
    )
    assert response.status_code == 200 and response.json()["not_an_executable_plan"]
    assert response.json()["topological_order"] == ["read"] and not response.json()["publishable"]
    assert counts(store) == before
    gid = next(
        x
        for x in client.get(f"/api/projects/{pid}/grants").json()
        if x["resource_id"] == res and x["principal_id"] == a and x["tool_ref"] == "resource.read"
    )
    client.post(
        f"/api/grants/{gid['id']}/revoke", json={"command": "revoke", "version": gid["revision"]}
    )
    assert (
        client.post(
            f"/api/projects/{pid}/contracts/preflight", json={"manifest": m, "actions": [action]}
        ).status_code
        == 403
    )
    assert counts(store) == before


@pytest.mark.parametrize(
    "change",
    [
        "revision",
        "missing_input",
        "type",
        "missing_lock",
        "missing_permission",
        "budget",
        "optional_source",
        "output",
    ],
)
def test_AT03_preflight_rejects_unsafe_connections_and_budget(env, change):
    m, action = preflight_fixture(env[-1])
    bad = copy.deepcopy(m)
    if change == "revision":
        bad["action_bindings"][0]["revision"] = 2
    elif change == "missing_input":
        bad["workflow"][0]["inputs"].pop("kind")
    elif change == "type":
        bad["input_schema"]["properties"]["amount"] = {"type": "integer"}
    elif change == "missing_lock":
        bad["dependency_lock"] = []
    elif change == "missing_permission":
        bad["permission_requirements"] = []
    elif change == "budget":
        bad["runtime_limits"]["max_requests"] = 3
    elif change == "optional_source":
        bad["input_schema"]["required"] = ["kind"]
    else:
        bad["outputs"]["text"]["field"] = "missing"
    with pytest.raises(DomainError):
        preflight(json.dumps(bad), [action], Limits(**m["runtime_limits"]))


def unknown_local_effect(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "SYNTHETIC local effect recovery", [], "unknown-effect")
    Worker(store, s).once()
    with store.tx() as c:
        op = dict(c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one())
        c.execute(
            update(operations)
            .where(operations.c.id == op["id"])
            .values(status="OUTCOME_UNKNOWN", receipt=None)
        )
        c.execute(
            update(runs).where(runs.c.id == rid).values(status="WAITING_RESOURCE", lease_until=0)
        )
    version = client.get(f"/api/runs/{rid}").json()["version"]
    return (
        rid,
        op,
        {
            "operation_id": op["id"],
            "version": version,
            "expected_fingerprint": op["fingerprint"],
            "evidence": "SYNTHETIC lost receipt; inspect trusted local ledger",
        },
    )


def test_AT06_unknown_effect_blocks_cancel_completion_and_resume(env):
    store, s, client, a, b, pid, res = env
    rid, op, body = unknown_local_effect(env)
    before = counts(store)
    assert (
        client.post(
            f"/api/runs/{rid}/commands", json={"command": "resume", "version": body["version"]}
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/runs/{rid}/commands", json={"command": "cancel", "version": body["version"]}
        ).json()["status"]
        == "RECONCILING"
    )
    body["version"] += 1
    response = client.post(f"/api/runs/{rid}/reconcile-operation", json=body)
    assert (
        response.status_code == 200
        and response.json()["status"] == "CANCELLED"
        and response.json()["operation_status"] == "VERIFIED"
    )
    assert (
        response.json()["tools_dispatched"] == 0
        and response.json()["known_effects"][0]["id"] == op["id"]
    )
    assert counts(store) == before
    assert client.post(f"/api/runs/{rid}/reconcile-operation", json=body).status_code == 409


def test_AT06_recovered_local_effect_pauses_and_never_duplicates_artifact(env):
    store, s, client, a, b, pid, res = env
    rid, op, body = unknown_local_effect(env)
    before = counts(store)
    response = client.post(f"/api/runs/{rid}/reconcile-operation", json=body)
    assert response.json()["status"] == "PAUSED"
    assert counts(store) == before
    assert Worker(store, s).once() is False
    with store.engine.connect() as c:
        original_attempts = c.execute(
            select(func.count()).select_from(attempts).where(attempts.c.run_id == rid)
        ).scalar_one()
    v = response.json()["version"]
    client.post(f"/api/runs/{rid}/commands", json={"command": "resume", "version": v})
    Worker(store, s).once()
    assert store.inspect(a, rid)["status"] == "PARTIAL" and counts(store) == before
    with store.engine.connect() as c:
        assert (
            c.execute(
                select(func.count()).select_from(attempts).where(attempts.c.run_id == rid)
            ).scalar_one()
            == original_attempts
        )


@pytest.mark.parametrize(
    "change", ["legacy", "invalid_effect", "other_subject", "fingerprint", "revoked"]
)
def test_AT06_unknown_tool_effect_only_trusted_readback_can_resolve(env, change):
    store, s, client, a, b, pid, res = env
    rid, op, body = unknown_local_effect(env)
    if change == "legacy":
        from sim2act.db import operation_intents

        with store.tx() as c:
            c.execute(
                operation_intents.delete().where(operation_intents.c.operation_id == op["id"])
            )
    elif change == "invalid_effect":
        with store.tx() as c:
            c.execute(
                update(resources)
                .where(resources.c.id == op["receipt"]["data"]["resource_id"])
                .values(content="corrupted")
            )
    elif change == "other_subject":
        client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    elif change == "fingerprint":
        body["expected_fingerprint"] = "0" * 64
    else:
        g = next(
            x
            for x in client.get(f"/api/projects/{pid}/grants").json()
            if x["tool_ref"] == "artifact.save_text" and x["principal_id"] == a
        )
        client.post(
            f"/api/grants/{g['id']}/revoke", json={"command": "revoke", "version": g["revision"]}
        )
    before = counts(store)
    result = client.post(f"/api/runs/{rid}/reconcile-operation", json=body)
    if change == "legacy":
        assert (
            result.json()["operation_status"] == "OUTCOME_UNKNOWN"
            and result.json()["status"] == "WAITING_RESOURCE"
        )
    elif change == "invalid_effect":
        assert (
            result.json()["operation_status"] == "EFFECT_KNOWN_INVALID"
            and result.json()["status"] == "FAILED"
        )
    else:
        assert (
            result.status_code == 403
            if change in {"other_subject", "revoked"}
            else result.status_code == 400
        )
    assert counts(store) == before


def test_AT06_read_only_unknown_effect_can_be_recomputed_without_dispatch(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "synthetic read recovery", [res], "read-recovery")
    Worker(store, s).once()
    with store.tx() as c:
        op = c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one()
        c.execute(
            update(operations)
            .where(operations.c.id == op["id"])
            .values(status="DISPATCHED", receipt=None)
        )
        c.execute(
            update(runs).where(runs.c.id == rid).values(status="WAITING_RESOURCE", lease_until=0)
        )
    before = counts(store)
    v = client.get(f"/api/runs/{rid}").json()["version"]
    result = client.post(
        f"/api/runs/{rid}/reconcile-operation",
        json={
            "operation_id": op["id"],
            "version": v,
            "expected_fingerprint": op["fingerprint"],
            "evidence": "SYNTHETIC read-only recomputation",
        },
    )
    assert result.json()["operation_status"] == "VERIFIED" and result.json()["status"] == "PAUSED"
    assert result.json()["tools_dispatched"] == 0 and counts(store) == before
    with store.engine.connect() as c:
        receipt = c.execute(
            select(operations.c.receipt).where(operations.c.id == op["id"])
        ).scalar_one()
        assert (
            receipt["data"]["hash"] == hashlib.sha256(b"item,amount\na,1.25\nb,2.75\n").hexdigest()
        )
    assert DomainError("OUTCOME_UNKNOWN").public()["effect_known"] is False


def test_AT06_unknown_adapter_has_no_operator_shortcut_or_automatic_retry(env):
    from sqlalchemy import insert

    from sim2act.db import new_id

    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "synthetic unsupported adapter", [], "unsupported-adapter")
    oid = new_id("op")
    fp = "1" * 64
    with store.tx() as c:
        c.execute(
            insert(operations).values(
                id=oid,
                run_id=rid,
                call_id="synthetic-external",
                fingerprint=fp,
                tool_ref="synthetic.external",
                status="OUTCOME_UNKNOWN",
            )
        )
        c.execute(update(runs).where(runs.c.id == rid).values(status="WAITING_RESOURCE"))
    v = client.get(f"/api/runs/{rid}").json()["version"]
    result = client.post(
        f"/api/runs/{rid}/reconcile-operation",
        json={
            "operation_id": oid,
            "version": v,
            "expected_fingerprint": fp,
            "evidence": "SYNTHETIC; no adapter evidence",
        },
    )
    assert result.json()["operation_status"] == "OUTCOME_UNKNOWN"
    assert result.json()["status"] == "WAITING_RESOURCE"
    assert (
        client.post(
            f"/api/runs/{rid}/commands",
            json={"command": "resume", "version": result.json()["version"]},
        ).status_code
        == 400
    )
    assert Worker(store, s).once() is False
