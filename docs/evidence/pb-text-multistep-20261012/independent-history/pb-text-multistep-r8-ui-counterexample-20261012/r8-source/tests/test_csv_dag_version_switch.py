"""Same-app durable workflow upgrades and rollback retain real checked history."""

import copy

import pytest
from sqlalchemy import select, update
from test_csv_dag import NoModel
from test_csv_dag_instances import create, enqueue, release, work
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits

from sim2act import csv_dag as dag
from sim2act import lifecycle
from sim2act.column_patches import read_pair
from sim2act.db import (
    Store,
    fingerprint,
    grants,
    internal_approvals,
    internal_instance_data,
    internal_instances,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


def next_release(env, aid, plan, *, key="second", with_report=None):
    with env[0].tx() as c:
        body, _ = read_pair(c, env[3], aid, "csv_dag_plan", plan["request_key"], dag.PlanInput)
    body = body.model_dump(exclude_none=True)
    body["request_key"] = key
    body["column"] = "quantity"
    body["composition"]["nodes"][1]["column"] = "quantity"
    if with_report is True and len(body["composition"]["nodes"]) == 2:
        body["composition"]["nodes"].append(dict(step_id="formatted", action="intern.csv_report.v1",
            depends_on=["total"], inputs={k: dict(source="step", ref="total", field=k)
                for k in ("resource_id", "column", "count", "sum", "source_hash")}))
    base = f"/api/projects/{env[5]}/apps/{aid}/csv-dag"
    response = env[2].post(base, json=body)
    assert response.status_code == 201, response.text
    p = response.json()
    response = env[2].post(base + f"/{key}/runs", json=dict(expected_plan_fingerprint=p["plan_fingerprint"],
        consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key=key))
    assert response.status_code == 202, response.text
    accepted = response.json()
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job["id"] == accepted["run_id"]
    worker.process(job)
    assert dag.inspect_job(env[0], env[3], job["id"], limits(env))["status"] == "SUCCEEDED"
    a = env[2].post(f"/api/csv-dag/runs/{job['id']}/release-approvals",
        json=dict(expected_plan_fingerprint=p["plan_fingerprint"], request_key=key)).json()
    response = env[2].post(f"/api/internal/approvals/{a['id']}/commit", json=dict(fingerprint=a["fingerprint"]))
    assert response.status_code == 200, response.text
    return response.json()


def prepare(env, instance, target):
    return env[2].post(f"/api/internal/instances/{instance['id']}/switch-approvals",
        json=dict(target_release_id=target["id"], expected_target_fingerprint=target["fingerprint"],
                  expected_revision=instance["revision"]))


def switch(env, instance, target):
    response = prepare(env, instance, target)
    assert response.status_code == 201, response.text
    a = response.json()
    base = f"/api/internal/instances/{instance['id']}/switch-approvals/{a['id']}"
    read = env[2].get(base)
    assert read.status_code == 200, read.text
    assert read.json()["data_preserved"] and not read.json()["new_grants"]
    response = env[2].post(base + "/commit", json=dict(fingerprint=a["fingerprint"]))
    assert response.status_code == 200, response.text
    result = env[2].get(f"/api/internal/instances/{instance['id']}")
    assert result.status_code == 200, result.text
    return result.json(), a


@pytest.mark.parametrize("with_report", [False, True])
def test_upgrade_rollback_new_columns_and_cold_history(env, with_report):
    aid, _, plan, _, old = release(env, with_report=with_report)
    target = next_release(env, aid, plan)
    i = create(env, old)
    first, _ = enqueue(env, i, old, "amount", "old-run")
    work(env, first)
    original = lifecycle.inspect_instance(env[0], env[3], i["id"], limits(env))["data"]
    before = snapshot(env)
    i, _ = switch(env, i, target)
    assert i["revision"] == 2 and i["data_version"] == 1 and i["data"] == original
    second, _ = enqueue(env, i, target, "quantity", "new-run")
    work(env, second)
    i, _ = switch(env, i, old)
    assert i["revision"] == 3 and i["data_version"] == 2
    third, _ = enqueue(env, i, old, "amount", "rollback-run")
    work(env, third)
    frozen = fingerprint(snapshot(env))
    cold = Store(env[1].database_url, test_only=True)
    try:
        data = lifecycle.inspect_instance(cold, env[3], i["id"], limits(env))
        assert data["data_version"] == 3
        assert [r["data"]["result"]["sum"] for r in data["data"]] == ["30", "15", "30"]
        assert [r["release_id"] for r in data["data"]] == [old["id"], target["id"], old["id"]]
        response = env[2].get(f"/api/internal/instances/{i['id']}")
        assert response.status_code == 200, response.text
        assert len(response.json()["runs"]) == 3
        for accepted in [first, second, third]:
            response = env[2].get(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}")
            assert response.status_code == 200, response.text
            assert response.json()["proof"]["model_requests"] == 0
        # Historical reads must not turn into permission for runtime writes.
        with cold.tx() as c:
            job = dag.row(c, env[3], first["run_id"])
            with pytest.raises(DomainError) as rejected:
                dag.binding(cold, c, job, limits(env))
            assert rejected.value.code == "VERSION_CONFLICT"
    finally:
        cold.engine.dispose()
    assert fingerprint(snapshot(env)) == frozen
    after = snapshot(env)
    assert before["principals"] == after["principals"] and before["grants"] == after["grants"]


def test_active_run_blocks_switch_until_explicit_cancel(env):
    aid, _, plan, _, old = release(env)
    target = next_release(env, aid, plan)
    i = create(env, old)
    accepted, _ = enqueue(env, i, old)
    frozen = fingerprint(snapshot(env))
    response = prepare(env, i, target)
    assert response.status_code == 409, response.text
    assert fingerprint(snapshot(env)) == frozen
    response = env[2].post(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}/commands",
        json=dict(command="cancel", version=accepted["version"]))
    assert response.status_code == 200, response.text
    i, _ = switch(env, i, target)
    assert i["data_version"] == 0 and i["runs"][0]["status"] == "CANCELLED"


def test_new_run_after_preparation_invalidates_commit(env):
    aid, _, plan, _, old = release(env)
    target = next_release(env, aid, plan)
    i = create(env, old)
    a = prepare(env, i, target).json()
    enqueue(env, i, old)
    frozen = fingerprint(snapshot(env))
    response = env[2].post(f"/api/internal/instances/{i['id']}/switch-approvals/{a['id']}/commit",
        json=dict(fingerprint=a["fingerprint"]))
    assert response.status_code == 409, response.text
    assert fingerprint(snapshot(env)) == frozen


def test_different_execution_family_rejected(env):
    aid, _, plan, _, old = release(env)
    target = next_release(env, aid, plan, with_report=True)
    i = create(env, old)
    frozen = fingerprint(snapshot(env))
    response = prepare(env, i, target)
    assert response.status_code == 409, response.text
    assert fingerprint(snapshot(env)) == frozen


@pytest.mark.parametrize("attack", ["history", "history-null", "history-bool", "approval", "result", "grant", "other-owner"])
def test_changed_history_or_authority_rejects_read_and_switch(env, attack):
    aid, _, plan, _, old = release(env)
    target = next_release(env, aid, plan)
    i = create(env, old)
    accepted, _ = enqueue(env, i, old)
    work(env, accepted)
    i, approval = switch(env, i, target)
    with env[0].tx() as c:
        if attack == "history":
            history = copy.deepcopy(i["history"])
            history[0]["release_id"] = target["id"]
            c.execute(update(internal_instances).where(internal_instances.c.id == i["id"]).values(history=history))
        elif attack in {"history-null", "history-bool"}:
            history = copy.deepcopy(i["history"])
            if attack == "history-null":
                history[1] = None
            else:
                history[0]["revision"] = True
            c.execute(update(internal_instances).where(internal_instances.c.id == i["id"]).values(history=history))
        elif attack == "approval":
            c.execute(update(internal_approvals).where(internal_approvals.c.id == approval["id"]).values(consumed=False))
        elif attack == "result":
            row = c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])).mappings().one()
            data = copy.deepcopy(row["data"])
            data["result"]["sum"] = "999"
            c.execute(update(internal_instance_data).where(internal_instance_data.c.instance_id == i["id"])
                .values(data=data, fingerprint=fingerprint(data)))
        elif attack == "grant":
            c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
    if attack == "other-owner":
        env[2].headers.update({"Authorization": "Bearer synthetic-test-B"})
    frozen = fingerprint(snapshot(env))
    assert env[2].get(f"/api/internal/instances/{i['id']}").status_code in {403, 409}
    assert prepare(env, i, old).status_code in {403, 409}
    assert fingerprint(snapshot(env)) == frozen
