"""Bounded synthetic ASGI/SQLite/original Worker; real models are forbidden."""

import json

from sqlalchemy import select
from test_csv_full_report import saved
from test_csv_goal_revisions import raw_trace as raw_trace
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_report import NoModel

from sim2act.db import internal_app_runs, internal_run_bindings
from sim2act.worker import Worker


def delivered(env, key="release-one"):
    source, original, options, save, recipe, material, use = saved(env)
    client = env[2]
    root = f"/api/apps/{recipe['id']}/csv-full-report-delivery"
    body = dict(
        expected_definition_fingerprint=recipe["fingerprint"],
        request_key=key,
        consent="FREEZE_COMPLETE_MD_RECIPE_AND_CHECK",
    )
    before = table_snapshot(env[0])
    approval = client.post(root + "/release-approvals", json=body)
    assert approval.status_code == 201, approval.text
    approval = approval.json()
    release = client.post(
        f"/api/internal/approvals/{approval['id']}/commit",
        json=dict(fingerprint=approval["fingerprint"]),
    )
    assert release.status_code == 200, release.text
    release = release.json()
    instance = client.post(
        f"/api/internal/releases/{release['id']}/instances",
        json=dict(expected_release_fingerprint=release["fingerprint"], request_key="instance-one"),
    )
    assert instance.status_code == 201, instance.text
    after = table_snapshot(env[0])
    for table in ("grants", "principals", "runs", "operations", "local_effects", "app_drafts"):
        assert before[table] == after[table], table
    return source, original, recipe, material, release, instance.json(), root, body, approval


def complete(env, iid, release, material, key, revision=1):
    client = env[2]
    body = dict(
        expected_revision=revision,
        expected_release_fingerprint=release["fingerprint"],
        resource_id=material,
        column="quantity",
        request_key=key,
        consent="PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY",
    )
    made = client.post(f"/api/internal/instances/{iid}/csv-full-report-uses", json=body)
    assert made.status_code == 202, made.text
    receipt = made.json()
    rid = receipt["run_id"]
    frozen = client.get(f"/api/runs/{rid}")
    assert frozen.status_code == 200, frozen.text
    frozen = frozen.json()
    assert frozen["status"] == "WAITING_APPROVAL"
    assert not Worker(env[0], env[1], NoModel()).once()
    before = table_snapshot(env[0])
    repeated = client.post(f"/api/internal/instances/{iid}/csv-full-report-uses", json=body)
    assert repeated.status_code == 202 and repeated.json()["run_id"] == rid
    assert before == table_snapshot(env[0])
    confirmed = client.post(
        f"/api/runs/{rid}/confirm-csv-report",
        json=dict(
            version=frozen["version"],
            contract_fingerprint=frozen["contract"]["fingerprint"],
            request_key="confirm-" + key,
        ),
    )
    assert confirmed.status_code == 200, confirmed.text
    assert Worker(env[0], env[1], NoModel()).once()
    result = client.get(f"/api/runs/{rid}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["status"] == "SUCCEEDED", result
    return body, receipt, result


def test_complete_md_internal_release_instance_and_two_fresh_ordinary_runs(env, tmp_path):
    source, original, recipe, material, release, instance, root, release_body, approval = delivered(
        env
    )
    iid = instance["id"]
    body, first, result = complete(env, iid, release, material, "first-fresh")
    summary = env[2].get(root)
    assert summary.status_code == 200, summary.text
    value = summary.json()
    assert len(value["releases"]) == len(value["instances"]) == 1
    actual = value["instances"][0]
    assert actual["data_version"] == 1 and len(actual["runs"]) == len(actual["data"]) == 1
    report = actual["data"][0]["data"]["result"]
    spec = result["contract"]["snapshot"]["ordinary_csv_report"]
    assert report["sum"] == "15" and report["ordinary_run_id"] == first["run_id"]
    md = env[2].get(f"/api/resources/{report['report_resource_id']}")
    assert md.status_code == 200, md.text
    assert md.json()["content"] == spec["report_text"] and md.json()["hash"] == spec["report_hash"]
    second_release_body = {**release_body, "request_key": "second-internal-release"}
    approved = env[2].post(root + "/release-approvals", json=second_release_body)
    assert approved.status_code == 201, approved.text
    approved = approved.json()
    other = env[2].post(
        f"/api/internal/approvals/{approved['id']}/commit",
        json=dict(fingerprint=approved["fingerprint"]),
    )
    assert other.status_code == 200, other.text
    other = other.json()
    fresh = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/resources",
            json=dict(name="second.csv", format="csv", content="quantity\n100\n200\n"),
        )
        .json()["id"]
    )
    adopt_body = dict(
        target_release_id=other["id"],
        expected_target_fingerprint=other["fingerprint"],
        expected_revision=1,
        request_key="adopt-other-exact",
    )
    prepared = env[2].post(
        f"/api/internal/instances/{iid}/csv-full-report-switch-approvals", json=adopt_body
    )
    assert prepared.status_code == 201, prepared.text
    prepared = prepared.json()
    accepted = env[2].post(
        f"/api/internal/instances/{iid}/csv-full-report-switch-requests/adopt-other-exact/commit",
        json=dict(fingerprint=prepared["fingerprint"]),
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["committed"]["revision"] == 2
    before = table_snapshot(env[0])
    recovered = env[2].get(
        f"/api/internal/instances/{iid}/csv-full-report-switch-requests/adopt-other-exact"
    )
    assert (
        recovered.status_code == 200
        and recovered.json()["committed"] == accepted.json()["committed"]
    )
    assert table_snapshot(env[0]) == before
    assert env[2].get(f"/api/runs/{first['run_id']}").json() == result
    _, second, second_result = complete(env, iid, other, fresh, "second-fresh", revision=2)
    assert second["run_id"] != first["run_id"] != source
    final = env[2].get(root)
    assert final.status_code == 200, final.text
    final = final.json()
    assert final["instances"][0]["data_version"] == 2
    assert final["instances"][0]["data"][0] == actual["data"][0]
    assert final["instances"][0]["data"][1]["data"]["result"]["sum"] == "300"
    assert env[2].get(f"/api/runs/{source}").json() == original
    assert env[2].get(f"/api/runs/{first['run_id']}").json() == result
    assert (
        env[2].get(f"{root}/release-requests/{release_body['request_key']}").json()["release"]["id"]
        == release["id"]
    )
    assert env[2].get(f"{root}/instance-requests/{release['id']}/instance-one").json()["id"] == iid
    with env[0].engine.connect() as c:
        assert c.execute(select(internal_run_bindings)).first() is None
        assert len(c.execute(select(internal_app_runs)).all()) == 2
    (tmp_path / "complete-delivery.json").write_text(
        json.dumps(
            dict(
                release=release,
                approval=approval,
                instance=instance,
                first=result,
                second=second_result,
                delivery=final,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
