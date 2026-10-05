"""Bounded completed synthetic task proofs; no PREVIEW/F1 status promotion."""

import copy
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from test_goal_candidates import setup_card

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    app_drafts,
    app_previews,
    attempts,
    fingerprint,
    grants,
    local_csv_tasks,
    operations,
    resource_retirements,
    resources,
    runs,
    task_extractions,
)
from sim2act.errors import DomainError
from sim2act.local_tasks import POLICY
from sim2act.tools import authorized_read


def setup_completed(env, client=None, column="amount", request_key="task"):
    client = client or env[2]
    pid, source = env[-2:]
    task = client.post(
        f"/api/projects/{pid}/local-csv-tasks",
        json={
            "resource_id": source,
            "column": column,
            "request_key": request_key,
            "synthetic_fixture": True,
            "goal": "fixed_csv_exact_sum.v1",
        },
    )
    assert task.status_code == 201
    task = task.json()
    rid = client.post(
        f"/api/projects/{pid}/resources",
        json={
            "name": "new.csv",
            "format": "csv",
            "content": "amount,quantity\n10,2\n30,3\n",
        },
    ).json()["id"]
    extraction = {
        "expected_proof_fingerprint": task["proof_fingerprint"],
        "resource_id": rid,
        "name": "from completed synthetic task",
        "request_key": "extract",
    }
    retirement = {
        "expected_proof_fingerprint": task["proof_fingerprint"],
        "expected_source_hash": task["proof"]["source_hash"] if task["proof"] else "0" * 64,
        "retain_minimal_proof": True,
        "policy": POLICY,
    }
    return task, rid, extraction, retirement


def extract(client, task, body):
    response = client.post(f"/api/local-csv-tasks/{task['id']}/extract", json=body)
    assert response.status_code == 201, response.json()
    return response.json()["id"]


def retire(client, task, body):
    return client.post(f"/api/local-csv-tasks/{task['id']}/retire-source", json=body)


def preview(client, aid, column="amount", key="new"):
    return client.post(
        f"/api/apps/{aid}/previews", json={"input": {"column": column}, "request_key": key}
    )


def counts(store):
    with store.engine.connect() as c:
        return {
            t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [
                app_drafts,
                app_previews,
                local_csv_tasks,
                task_extractions,
                resource_retirements,
                grants,
                runs,
                attempts,
                operations,
            ]
        }


def test_completed_task_retired_source_cold_client_new_input_and_failure(env):
    store, s, client, user, _, pid, source = env
    task, rid, body, retirement = setup_completed(env)
    assert task["status"] == "SUCCEEDED" and task["namespace"] == "LOCAL_DECLARATIVE_TASK"
    assert task["output"]["sum"] == "4.00"
    assert task["proof"]["check"]["status"] == "PASS"
    aid = extract(client, task, body)
    grants_before = []
    with store.tx() as c:
        grants_before = [dict(x) for x in c.execute(select(grants)).mappings()]
    assert retire(client, task, retirement).status_code == 200
    with store.tx() as c:
        old = c.execute(select(resources).where(resources.c.id == source)).mappings().one()
        receipt = (
            c.execute(select(local_csv_tasks).where(local_csv_tasks.c.id == task["id"]))
            .mappings()
            .one()
        )
        assert old["content"] == "" and old["format"] == "retired"
        assert receipt["input"] is None and receipt["output"] is None
        assert receipt["proof"] == task["proof"]
        assert [dict(x) for x in c.execute(select(grants)).mappings()] == grants_before
        with pytest.raises(DomainError, match="来源已显式退休"):
            authorized_read(
                store,
                c,
                user,
                store.own_project(c, user, pid)["runtime_id"],
                pid,
                "resource.read",
                {"resource_id": source},
            )
    assert client.get(f"/api/resources/{source}").status_code == 400
    # New Store/connection/client: no original session, old cells or sum to replay.
    cold_store = Store(s.database_url, test_only=True)
    if not store.sqlite:
        cold_store.engine = cold_store.engine.execution_options(
            **store.engine.get_execution_options()
        )
    with TestClient(create_app(cold_store, s)) as cold:
        cold.headers["Authorization"] = "Bearer synthetic-test-A"
        draft = cold.get(f"/api/apps/{aid}")
        assert draft.status_code == 200
        assert "4.00" not in str(draft.json()["candidate"]["task_proof"])
        result = preview(cold, aid).json()
        assert result["status"] == "SUCCEEDED" and result["output"]["sum"] == "40"
        assert result["output"]["resource_id"] == rid
        bad = preview(cold, aid, "missing", "bad").json()
        assert bad["status"] == "FAILED" and bad["error"]["code"] == "INVALID_INPUT"
        assert len(cold.get(f"/api/apps/{aid}").json()["history"]) == 2
        assert cold.get(f"/api/local-csv-tasks/{task['id']}").json()["proof"] == task["proof"]
    cold_store.engine.dispose()
    with store.tx() as c:
        for t in [runs, attempts, operations]:
            assert c.execute(select(func.count()).select_from(t)).scalar_one() == 0


@pytest.mark.parametrize("state", ["FAILED", "PARTIAL", "UNKNOWN", "RUNNING"])
def test_noncompleted_task_never_extracts(env, state):
    store, _, client, *_ = env
    task, _, body, retirement = setup_completed(env)
    with store.tx() as c:
        c.execute(
            update(local_csv_tasks).where(local_csv_tasks.c.id == task["id"]).values(status=state)
        )
    before = counts(store)
    assert client.post(f"/api/local-csv-tasks/{task['id']}/extract", json=body).status_code == 400
    assert retire(client, task, retirement).status_code == 400
    assert counts(store) == before


def test_actual_bad_task_records_failure_not_success(env):
    store, _, client, *_ = env
    task, _, body, _ = setup_completed(env, column="missing")
    assert task["status"] == "FAILED" and task["proof"] is None and task["output"] is None
    body["expected_proof_fingerprint"] = "0" * 64
    assert client.post(f"/api/local-csv-tasks/{task['id']}/extract", json=body).status_code == 400
    with store.tx() as c:
        row = c.execute(select(local_csv_tasks)).mappings().one()
        assert row["status"] == "FAILED" and row["error"]["code"] == "INVALID_INPUT"


@pytest.mark.parametrize(
    "scope", ["source_user", "source_project", "target_user", "target_project", "target_app"]
)
@pytest.mark.parametrize("expiry", [False, True])
def test_current_source_and_target_intersection_revocation_and_expiry(env, scope, expiry):
    store, _, client, user, _, pid, source = env
    task, rid, body, retirement = setup_completed(env)
    aid = extract(client, task, body)
    assert retire(client, task, retirement).status_code == 200
    with store.tx() as c:
        project = store.own_project(c, user, pid)
        runtime = c.execute(
            select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)
        ).scalar_one()
        identity = (
            user
            if scope.endswith("user")
            else runtime
            if scope.endswith("app")
            else project["runtime_id"]
        )
        resource = source if scope.startswith("source") else rid
        c.execute(
            update(grants)
            .where(grants.c.principal_id == identity, grants.c.resource_id == resource)
            .values(**({"expires_at": 0} if expiry else {"revoked": True}))
        )
    before = counts(store)
    assert client.get(f"/api/apps/{aid}").status_code == 403
    assert preview(client, aid).status_code == 403
    assert counts(store) == before


@pytest.mark.parametrize(
    "component",
    [
        "candidate_proof",
        "candidate_remove",
        "task_proof",
        "task_version",
        "retirement_policy",
        "retirement_hash",
        "resurrect_content",
    ],
)
def test_proof_version_and_retirement_tamper_fail_closed(env, component):
    store, _, client, *_ = env
    task, _, body, retirement = setup_completed(env)
    aid = extract(client, task, body)
    assert retire(client, task, retirement).status_code == 200
    with store.tx() as c:
        if component.startswith("candidate"):
            candidate = copy.deepcopy(
                c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
            )
            if component == "candidate_remove":
                del candidate["task_proof"]
                candidate["manifest"].update(origin="goal", source_run_ref=None)
            else:
                candidate["task_proof"]["proof"]["source_hash"] = "0" * 64
                candidate["task_proof"]["proof_fingerprint"] = fingerprint(
                    candidate["task_proof"]["proof"]
                )
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == aid)
                .values(candidate=candidate, fingerprint=fingerprint(candidate))
            )
        elif component.startswith("task"):
            proof = copy.deepcopy(task["proof"])
            proof["source_hash" if component == "task_proof" else "version"] = (
                "0" * 64 if component == "task_proof" else 2
            )
            c.execute(
                update(local_csv_tasks)
                .where(local_csv_tasks.c.id == task["id"])
                .values(proof=proof, proof_fingerprint=fingerprint(proof))
            )
        elif component.startswith("retirement"):
            c.execute(
                update(resource_retirements).values(
                    **(
                        {"policy": "unknown"}
                        if component.endswith("policy")
                        else {"source_hash": "0" * 64}
                    )
                )
            )
        else:
            c.execute(
                update(resources).where(resources.c.id == env[-1]).values(content="amount\n999\n")
            )
    before = counts(store)
    assert client.get(f"/api/apps/{aid}").status_code == 409
    assert preview(client, aid).status_code == 409
    assert counts(store) == before


def test_cross_owner_and_project_no_authority_transfer(env):
    _, _, client, _, _, pid, _ = env
    task, _, body, retirement = setup_completed(env)
    aid = extract(client, task, body)
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    before = counts(env[0])
    assert client.get(f"/api/apps/{aid}").status_code == 403
    assert preview(client, aid).status_code == 403
    assert retire(client, task, retirement).status_code == 403
    assert client.post(f"/api/local-csv-tasks/{task['id']}/extract", json=body).status_code == 403
    assert counts(env[0]) == before
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    other_pid = client.post("/api/projects", json={"name": "other project"}).json()["id"]
    rid = client.post(
        f"/api/projects/{other_pid}/resources",
        json={"name": "other.csv", "format": "csv", "content": "amount\n99\n"},
    ).json()["id"]
    assert (
        client.post(
            f"/api/local-csv-tasks/{task['id']}/extract", json={**body, "resource_id": rid}
        ).status_code
        == 403
    )
    assert pid != other_pid


@pytest.mark.parametrize("change", ["consent", "policy", "version", "hash"])
def test_retirement_explicit_consent_version_and_policy(env, change):
    _, _, client, *_ = env
    task, _, _, retirement = setup_completed(env)
    field, value, expected = {
        "consent": ("retain_minimal_proof", False, 422),
        "policy": ("policy", "unknown", 422),
        "version": ("expected_proof_fingerprint", "0" * 64, 409),
        "hash": ("expected_source_hash", "0" * 64, 409),
    }[change]
    before = counts(env[0])
    assert retire(client, task, {**retirement, field: value}).status_code == expected
    assert counts(env[0]) == before
    assert client.get(f"/api/resources/{env[-1]}").json()["content"]


@pytest.mark.parametrize("consumer", ["preview", "goal", "f1"])
def test_retirement_refuses_existing_consumers(env, consumer):
    _, _, client, _, _, pid, rid = env
    task, _, _, retirement = setup_completed(env)
    if consumer == "preview":
        assert (
            client.post(
                f"/api/projects/{pid}/apps/csv-preview",
                json={"name": "old app", "resource_id": rid, "goal": "old"},
            ).status_code
            == 201
        )
    elif consumer == "goal":
        setup_card(env)
    else:
        assert (
            client.post(
                f"/api/projects/{pid}/runs",
                json={"goal": "old task", "resource_refs": [rid], "request_key": "oldrun"},
            ).status_code
            == 202
        )
    before = counts(env[0])
    assert retire(client, task, retirement).status_code == 409
    assert counts(env[0]) == before
    assert client.get(f"/api/resources/{rid}").json()["content"]


def test_task_extract_retirement_idempotency_and_live_refusal(env):
    store, s, client, _, _, pid, source = env
    task, _, body, retirement = setup_completed(env)
    aid = extract(client, task, body)
    before = counts(store)
    assert extract(client, task, body) == aid and counts(store) == before
    changed = client.post(
        f"/api/local-csv-tasks/{task['id']}/extract", json={**body, "name": "changed"}
    )
    assert changed.status_code == 409
    assert retire(client, task, retirement).status_code == 200
    before = counts(store)
    assert retire(client, task, retirement).status_code == 200 and counts(store) == before
    assert (
        client.post(
            f"/api/local-csv-tasks/{task['id']}/extract", json={**body, "request_key": "late"}
        ).status_code
        == 400
    )
    with TestClient(create_app(store, replace(s, mode="live"))) as live:
        live.headers["Authorization"] = "Bearer synthetic-test-A"
        assert (
            live.post(
                f"/api/projects/{pid}/local-csv-tasks",
                json={
                    "resource_id": source,
                    "column": "amount",
                    "request_key": "new",
                    "synthetic_fixture": True,
                    "goal": "fixed_csv_exact_sum.v1",
                },
            ).status_code
            == 400
        )
    assert counts(store) == before


def test_application_role_completed_task_retirement_path(env, runtime_role):
    store, s, _, *_ = env
    app_store = Store(runtime_role)
    with TestClient(
        create_app(app_store, Settings(runtime_role, s.data_dir, mode="mock"))
    ) as client:
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        task, rid, body, retirement = setup_completed(env, client)
        aid = extract(client, task, body)
        assert retire(client, task, retirement).status_code == 200
        assert client.get(f"/api/apps/{aid}").status_code == 200
        assert preview(client, aid).json()["output"]["sum"] == "40"
        assert preview(client, aid, "missing", "bad").json()["status"] == "FAILED"
        assert retire(client, task, retirement).status_code == 200
        assert client.get(f"/api/resources/{env[-1]}").status_code == 400
    app_store.engine.dispose()


def test_completed_task_candidates_cannot_recursively_extract_as_preview(env):
    _, _, client, *_ = env
    task, rid, body, retirement = setup_completed(env)
    aid = extract(client, task, body)
    assert retire(client, task, retirement).status_code == 200
    receipt = preview(client, aid).json()
    draft = client.get(f"/api/apps/{aid}").json()
    before = counts(env[0])
    response = client.post(
        f"/api/previews/{receipt['id']}/extract",
        json={
            "expected_source_fingerprint": draft["fingerprint"],
            "resource_id": rid,
            "name": "recursive",
            "request_key": "recursive",
        },
    )
    assert (
        response.status_code == 400 and response.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    )
    assert counts(env[0]) == before


def test_rehashing_extra_source_content_into_proof_is_rejected(env):
    store, _, client, *_ = env
    task, _, body, _ = setup_completed(env)
    with store.tx() as c:
        proof = {**task["proof"], "old_cells": "synthetic original content"}
        c.execute(
            update(local_csv_tasks)
            .where(local_csv_tasks.c.id == task["id"])
            .values(proof=proof, proof_fingerprint=fingerprint(proof))
        )
    before = counts(store)
    assert (
        client.post(
            f"/api/local-csv-tasks/{task['id']}/extract",
            json={**body, "expected_proof_fingerprint": fingerprint(proof)},
        ).status_code
        == 409
    )
    assert counts(store) == before


def test_concurrent_task_extraction_and_retirement_retry_do_not_duplicate(env):
    from concurrent.futures import ThreadPoolExecutor

    store, s, client, _, _, pid, source = env

    def command(path, body):
        with TestClient(create_app(store, s)) as parallel:
            parallel.headers["Authorization"] = "Bearer synthetic-test-A"
            return parallel.post(path, json=body)

    with ThreadPoolExecutor(max_workers=2) as pool:
        body = {
            "resource_id": source,
            "column": "amount",
            "request_key": "concurrent",
            "synthetic_fixture": True,
            "goal": "fixed_csv_exact_sum.v1",
        }
        tasks = list(
            pool.map(lambda _: command(f"/api/projects/{pid}/local-csv-tasks", body), range(2))
        )
    assert all(x.status_code == 201 for x in tasks)
    assert tasks[0].json()["id"] == tasks[1].json()["id"]
    task = tasks[0].json()
    rid = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "new.csv", "format": "csv", "content": "amount\n9\n"},
    ).json()["id"]
    extraction = {
        "expected_proof_fingerprint": task["proof_fingerprint"],
        "resource_id": rid,
        "name": "concurrent",
        "request_key": "concurrent",
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        candidates = list(
            pool.map(
                lambda _: command(f"/api/local-csv-tasks/{task['id']}/extract", extraction),
                range(2),
            )
        )
    assert all(x.status_code == 201 for x in candidates)
    assert candidates[0].json()["id"] == candidates[1].json()["id"]
    retirement = {
        "expected_proof_fingerprint": task["proof_fingerprint"],
        "expected_source_hash": task["proof"]["source_hash"],
        "retain_minimal_proof": True,
        "policy": POLICY,
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        retired = list(
            pool.map(
                lambda _: command(f"/api/local-csv-tasks/{task['id']}/retire-source", retirement),
                range(2),
            )
        )
    assert all(x.status_code == 200 for x in retired)
    assert retired[0].json() == retired[1].json()
    assert preview(client, candidates[0].json()["id"]).json()["output"]["sum"] == "9"
