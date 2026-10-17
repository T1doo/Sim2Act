"""A completed ordinary Run cannot be attached retroactively to a saved recipe."""

import json

from test_csv_full_report import saved
from test_csv_goal_revisions import raw_trace as raw_trace
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_report import NoModel

from sim2act.db import fingerprint
from sim2act.worker import Worker


def test_precreated_successful_ordinary_run_cannot_become_a_new_workflow_use(env, tmp_path):
    store, settings, client, user, _, project, _ = env
    source_run, original, options, save_body, recipe, material, use = saved(env)
    key = "collision-completed-report"
    use = {**use, "request_key": key}
    ordinary_key = "full-report-" + fingerprint([user, recipe["id"], key])[:64]
    evidence = {
        "draft_scope": "one completed precreated ordinary Run; no real model",
        "recipe": recipe,
        "workflow_use_request": use,
        "ordinary_request_key": ordinary_key,
    }
    try:
        made = client.post(
            f"/api/projects/{project}/csv-report-runs",
            json={"resource_id": material, "column": use["column"], "request_key": ordinary_key},
        )
        evidence["precreated_prepare"] = {"status": made.status_code, "body": made.json()}
        assert made.status_code == 202, made.text
        rid = made.json()["run_id"]
        frozen = client.get(f"/api/runs/{rid}").json()
        assert frozen["status"] == "WAITING_APPROVAL"
        confirmed = client.post(
            f"/api/runs/{rid}/confirm-csv-report",
            json={
                "version": frozen["version"],
                "contract_fingerprint": frozen["contract"]["fingerprint"],
                "request_key": "confirm-precreated-report",
            },
        )
        assert confirmed.status_code == 200, confirmed.text
        assert Worker(store, settings, NoModel()).once()
        completed = client.get(f"/api/runs/{rid}").json()
        assert completed["status"] == "SUCCEEDED"
        assert completed["result"]["goal_acceptance"] == "PASS_CSV_REPORT_CONTRACT"
        assert not any(e["kind"] == "CSV_FULL_REPORT_USE" for e in completed["events"])
        before = table_snapshot(store)
        response = client.post(f"/api/apps/{recipe['id']}/csv-full-report-uses", json=use)
        after = table_snapshot(store)
        evidence.update(
            preexisting_run_id=rid,
            preexisting_complete_run=completed,
            workflow_use_response={"status": response.status_code, "body": response.json()},
            database_before_fingerprint=fingerprint(before),
            database_after_fingerprint=fingerprint(after),
            changed_tables=[name for name in before if before[name] != after[name]],
        )
        assert response.status_code == 409, response.text
        assert before == after, (
            "Rejected collision must not change Run context/events/uses or any rows"
        )
        assert client.get(f"/api/runs/{rid}").json() == completed
    finally:
        (tmp_path / "precreated-run-collision.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, default=str)
        )
