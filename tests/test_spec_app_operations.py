"""Actual read-only recovery/artifact operations for the saved spec app."""

import copy
import hashlib
import json

import pytest
from sqlalchemy import select, update
from test_natural_spec_apps import enqueue, ready, setup, transport

from sim2act.db import (
    attempts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_run_bindings,
    meta,
    resources,
    runs,
)
from sim2act.worker import Worker


def snapshot(store):
    with store.tx() as c:
        return {table.name: sorted((dict(row) for row in c.execute(select(table)).mappings()),
                                   key=lambda row: json.dumps(row, sort_keys=True, default=str))
                for table in meta.sorted_tables}


def test_original_key_reads_queued_and_completed_without_reexecution(env, tmp_path):
    data = setup(env)
    _, app, release, instance, _ = ready(data)
    job = enqueue(data, release, instance, key="original-key")
    path = f"/api/internal/instances/{instance['id']}/spec-run-requests/original-key"
    before = snapshot(data[0])
    queued = data[2].get(path)
    assert queued.status_code == 200, queued.text
    queued = queued.json()
    assert queued["namespace"] == "spec-run-request.v1"
    assert queued["run_id"] == job and queued["app_id"] == app
    assert queued["instance_id"] == instance["id"] and queued["principal_id"] == data[3]
    assert queued["project_id"] == data[4] and queued["release_id"] == release["id"]
    assert queued["request"] == dict(expected_revision=1,
        expected_release_fingerprint=release["fingerprint"], input={}, request_key="original-key")
    assert queued["request_fingerprint"] == fingerprint(dict(instance_id=instance["id"],
        expected_revision=1, expected_release_fp=release["fingerprint"], input={}))
    assert queued["status"] == "QUEUED"
    assert snapshot(data[0]) == before
    sent = []
    assert Worker(data[0], data[1], goal_planner_transport=transport(sent)).once()
    before = snapshot(data[0])
    result = data[2].get(path)
    assert result.status_code == 200, result.text
    assert result.json() == {**queued, "status": "SUCCEEDED"}
    assert snapshot(data[0]) == before and len(sent) == 1
    (tmp_path / "original-key-receipts.json").write_text(json.dumps([queued, result.json()], indent=2))


@pytest.mark.parametrize("fault", ["other_user", "missing_key", "binding", "accepted", "revoked"])
def test_original_key_rejects_wrong_scope_or_changed_receipt(env, tmp_path, fault):
    from sql_private_barrier import PrivateReadBarrier

    from sim2act.db import events

    data = setup(env)
    origin, _, release, instance, _ = ready(data)
    job = enqueue(data, release, instance, key="original-key")
    path = f"/api/internal/instances/{instance['id']}/spec-run-requests/original-key"
    if fault == "other_user":
        data[2].headers["Authorization"] = "Bearer synthetic-test-B"
    elif fault == "missing_key":
        path = path.replace("original-key", "never-accepted")
    else:
        with data[0].tx() as c:
            if fault == "revoked":
                c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
            elif fault == "accepted":
                row = c.execute(select(events).where(events.c.run_id == job,
                    events.c.kind == "ACCEPTED")).mappings().one()
                c.execute(update(events).where(events.c.id == row["id"])
                          .values(data={**row["data"], "instance_id": "foreign-instance"}))
            else:
                row = c.execute(select(internal_run_bindings).where(
                    internal_run_bindings.c.run_id == job)).mappings().one()
                changed = copy.deepcopy(row["snapshot"])
                changed["request_fingerprint"] = "0" * 64
                c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id == job)
                          .values(snapshot=changed))
    before = snapshot(data[0])
    if fault in {"revoked", "other_user"}:
        with PrivateReadBarrier(data[0], {origin, job}, {data[5]}) as barrier:
            response = data[2].get(path)
            assert response.status_code == 403, response.text
            assert not barrier.blocked and not barrier.evaluated
            (tmp_path / "read-barrier.json").write_text(json.dumps(barrier.statements, indent=2))
    else:
        response = data[2].get(path)
        assert response.status_code == (400 if fault == "missing_key" else 409), response.text
        assert response.json()["error"]["code"] == ("OUTCOME_UNKNOWN" if fault == "missing_key" else "VERSION_CONFLICT")
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("fault", [None, "artifact", "artifact_grant", "source_grant"])
def test_saved_artifact_exact_scoped_bytes_and_read_only(env, tmp_path, fault):
    data = setup(env)
    _, app, release, instance, _ = ready(data)
    job = enqueue(data, release, instance)
    sent = []
    assert Worker(data[0], data[1], goal_planner_transport=transport(sent)).once()
    with data[0].tx() as c:
        a = c.execute(select(internal_app_runs).where(
            internal_app_runs.c.instance_id == instance["id"])).mappings().one()
        output = a["output"]
        if fault == "artifact":
            c.execute(update(resources).where(resources.c.id == output["resource_id"])
                      .values(content="{}"))
        elif fault:
            rid = output["resource_id"] if fault == "artifact_grant" else data[5]
            c.execute(update(grants).where(grants.c.resource_id == rid).values(revoked=True))
    before = snapshot(data[0])
    response = data[2].get(f"/api/internal/app-run-jobs/{job}/spec-artifact")
    if fault:
        assert response.status_code == (400 if fault == "artifact" else 403), response.text
        assert response.json()["error"]["code"] == ("VERIFICATION_FAILED" if fault == "artifact" else "GRANT_REVOKED")
    else:
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["app_id"] == app and result["run_id"] == job
        assert result["instance_id"] == instance["id"] and result["release_id"] == release["id"]
        assert result["app_run_id"] == a["id"] and result["result_version"] == 1
        assert result["output_fingerprint"] == fingerprint(output)
        assert result["resource"]["hash"] == hashlib.sha256(result["resource"]["content"].encode()).hexdigest()
        assert json.loads(result["resource"]["content"]) == output["checklist"]
        assert "desk lamp" in result["markdown_view"]
        assert result["semantic_status"] == "UNKNOWN" and result["owner_acceptance"] == "PENDING"
        assert result["project_writes"] == result["new_model_requests"] == 0
        (tmp_path / "saved-artifact.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    assert snapshot(data[0]) == before and len(sent) == 1
    with data[0].tx() as c:
        assert c.execute(select(attempts.c.id).where(attempts.c.run_id == job)).all()
        assert c.execute(select(runs.c.status).where(runs.c.id == job)).scalar_one() == "SUCCEEDED"
