"""Ordinary complete CSV contract -> explicit sum-only application; synthetic only."""

import json

from sqlalchemy import select
from test_internal_lifecycle import create, release
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_report import NoModel, prepare
from test_persistent_app_runs import enqueue

from sim2act.db import internal_run_bindings, runs
from sim2act.worker import Worker


def setup(env):
    store, settings, client, _, _, project, source = env
    accepted = prepare(client, project, source)
    assert accepted.status_code == 202, accepted.text
    rid = accepted.json()["run_id"]
    frozen = client.get(f"/api/runs/{rid}").json()
    confirmed = client.post(f"/api/runs/{rid}/confirm-csv-report", json=dict(
        version=frozen["version"], contract_fingerprint=frozen["contract"]["fingerprint"],
        request_key="confirm-original-report",
    ))
    assert confirmed.status_code == 200, confirmed.text
    assert Worker(store, settings, NoModel()).once()
    original = client.get(f"/api/runs/{rid}").json()
    assert original["status"] == "SUCCEEDED"
    target_resource = client.post(f"/api/projects/{project}/resources", json=dict(
        name="unseen.csv", format="csv", content="amount,quantity,bad\n30,6,x\n50,9,y\n",
    )).json()["id"]
    target = client.post(f"/api/projects/{project}/apps/csv-preview", json=dict(
        name="already authorized target", resource_id=target_resource, goal="new CSV",
    )).json()["id"]
    return rid, original, target, target_resource


def options_body(env, rid, target, key="sum-only"):
    response = env[2].get(f"/api/runs/{rid}/csv-sum-candidate-options")
    assert response.status_code == 200, response.text
    options = response.json()
    target = next(t for t in options["targets"] if t["id"] == target)
    return options, dict(
        expected_proof_fingerprint=options["source_proof_fingerprint"],
        target_app_id=target["id"], expected_target_draft_fingerprint=target["fingerprint"],
        name="Explicit sum only", request_key=key,
        consent="EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT",
    )


def test_ordinary_success_to_sum_only_new_input_version_instance_and_fresh_run(env, tmp_path):
    rid, original, target, material = setup(env)
    before = table_snapshot(env[0])
    options, body = options_body(env, rid, target)
    assert table_snapshot(env[0]) == before
    response = env[2].post(f"/api/runs/{rid}/csv-sum-candidates", json=body)
    assert response.status_code == 201, response.text
    made = response.json()
    assert made["state"] == "CANDIDATE_ONLY" and made["full_md_report_included"] is False
    assert made["source_task_accepted"] is True and made["candidate_task_acceptance"] == "NOT_RUN"
    after = table_snapshot(env[0])
    assert all(before[k] == after[k] for k in before if k not in {"app_drafts", "task_extractions"})
    assert len(after["app_drafts"]) == len(before["app_drafts"]) + 1
    assert len(after["task_extractions"]) == len(before["task_extractions"]) + 1
    draft = env[2].get(f"/api/apps/{made['id']}")
    assert draft.status_code == 200, draft.text
    draft = draft.json()
    assert draft["candidate"]["manifest"]["source_run_ref"] == rid
    assert draft["candidate"]["manifest"]["goal_ref"] == original["contract"]["snapshot"]["goal"]["goal_id"]
    assert draft["candidate"]["actions"][0]["effect"] == "read"
    assert "artifact.save_text" not in str(draft["candidate"]["manifest"]["permission_requirements"])
    preview = env[2].post(f"/api/apps/{made['id']}/previews", json=dict(
        input={"column": "quantity"}, request_key="unseen-independent-check",
    )).json()
    assert preview["status"] == "SUCCEEDED" and preview["output"]["sum"] == "15"
    assert preview["output"]["resource_id"] == material
    rel, _, _ = release(env, made["id"], made["candidate_fingerprint"])
    instance = create(env, rel)
    queued = enqueue(env, instance, rel, column="quantity")
    assert Worker(env[0], env[1], NoModel()).once()
    result = env[2].get(f"/api/runs/{queued['run_id']}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "15"
    assert result["result_version"] == 1 and result["id"] != rid
    assert env[2].get(f"/api/runs/{rid}").json() == original
    with env[0].tx() as c:
        assert not c.execute(select(internal_run_bindings).where(internal_run_bindings.c.run_id == rid)).first()
        assert len(c.execute(select(runs)).all()) == 2
    (tmp_path / "sum-only-delivery.json").write_text(json.dumps(dict(
        source=original, options=options, request=body, candidate=draft,
        preview=preview, release=rel, instance=instance, accepted=queued, result=result,
        real_model_requests=0,
    ), ensure_ascii=False, indent=2))
