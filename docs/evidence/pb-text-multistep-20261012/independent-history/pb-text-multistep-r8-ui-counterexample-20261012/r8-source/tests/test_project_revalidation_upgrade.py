"""Previous executable source persists real project plan; new checks require fresh anchors."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_csv_dag_upgrade import raw_history_hashes
from test_delivery_graph_apps import snapshot

from sim2act.db import meta
from sim2act.project_revalidation import CONSENT


def test_actual_previous_source_project_plan_upgrade(env, tmp_path):
    archive = os.environ.get("SIM2ACT_PROJECT_CHECK_OLD_ARCHIVE")
    if not archive:
        pytest.skip("Actual project check source upgrade requires explicit owned previous archive")
    source = Path(archive) / "src/sim2act/api.py"
    expected = os.environ["SIM2ACT_PROJECT_CHECK_OLD_API_SHA256"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    output = tmp_path / "old-source-proof.json"
    body = dict(
        database_url=env[1].database_url,
        schema=env[0].engine.get_execution_options().get("schema_translate_map", {}).get(None),
        data_root=str(tmp_path),
        owner=env[3],
        other=env[4],
        project=env[5],
        resource=env[6],
        output=str(output),
    )
    child = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("fixtures") / "project_revalidation_upgrade.py"),
        ],
        cwd=archive,
        input=json.dumps(body),
        capture_output=True,
        text=True,
        timeout=90,
        env={
            **os.environ,
            "PYTHONPATH": str(Path(archive) / "src") + os.pathsep + str(Path(archive) / "tests"),
            "LIVE": "0",
            "SIM2ACT_LIVE_ENABLED": "false",
        },
    )
    (tmp_path / "child.log").write_text(child.stdout + child.stderr)
    assert child.returncode == 0, child.stdout + child.stderr
    old = json.loads(output.read_text())
    assert old["old_api"] == str(source.resolve()) and old["old_api_hash"] == expected
    assert old["old_negative_status"] == 404 and old["mock_calls"] == 4
    assert snapshot(env) == old["snapshot"]
    before = snapshot(env)
    raw = raw_history_hashes(env[0], list(meta.tables))
    rejected = env[2].get(old["base"] + "/options", params={"plan_key": "presentation-plan"})
    assert rejected.status_code == 409, rejected.text
    assert snapshot(env) == before and raw_history_hashes(env[0], list(meta.tables)) == raw
    root = old["base"].removesuffix("scope-checks")
    membership = env[2].get(f"/api/projects/{env[5]}/apps/{old['app']['id']}/delivery-graph/plans")
    assert membership.status_code == 409, membership.text
    # Explicitly refresh both trusted canonical peers, never the unsupported named source.
    peers = [
        row
        for row in before["app_drafts"]
        if row["project_id"] == env[5] and row["candidate"].get("manifest")
    ]
    for peer in peers:
        made = env[2].post(
            f"/api/projects/{env[5]}/apps/{peer['id']}/delivery-graph/derive",
            json={
                "expected_candidate_fingerprint": peer["fingerprint"],
                "request_key": "explicit-new-source",
            },
        )
        assert made.status_code == 201, made.text
    anchor = env[2].get(root.rstrip("/")).json()
    node = next(n for n in anchor["graph"]["nodes"] if n["kind"] == "VIEW")
    plan = env[2].post(
        root + "plans",
        json={
            "expected_graph_fingerprint": anchor["graph_fingerprint"],
            "request_key": "new-project-plan",
            "changes": [
                {
                    "node_id": node["id"],
                    "expected_revision": node["revision"],
                    "expected_content_fingerprint": node["content_fingerprint"],
                }
            ],
        },
    )
    assert plan.status_code == 201, plan.text
    choices = env[2].get(old["base"] + "/options", params={"plan_key": "new-project-plan"})
    assert choices.status_code == 200, choices.text
    options = choices.json()
    selected = []
    for item in options["applications"]:
        value = dict(
            app_id=item["app_id"],
            kind=item["kind"],
            expected_graph_fingerprint=item["binding"]["graph_fingerprint"],
        )
        if item["kind"] == "CSV":
            value["input"] = {"column": "amount"}
        else:
            run = item["runs"][0]
            value.update(
                run_id=run["run_id"],
                expected_run_version=run["version"],
                expected_run_fence=run["fence"],
                expected_result_fingerprint=run["result_fingerprint"],
            )
        selected.append(value)
    checked = env[2].post(
        old["base"],
        json={
            "plan_key": "new-project-plan",
            "expected_plan_fingerprint": options["plan_fingerprint"],
            "expected_options_fingerprint": options["options_fingerprint"],
            "selections": selected,
            "request_key": "new-project-check",
            "consent": CONSENT,
        },
    )
    assert checked.status_code == 201 and checked.json()["executed_checks_status"] == "PASS", (
        checked.text
    )
    after = snapshot(env)
    for table in before:
        if table not in {
            "delivery_graph_requests",
            "delivery_graph_states",
            "delivery_graph_anchors",
            "delivery_graph_source_versions",
            "delivery_graph_scope_jobs",
        }:
            assert before[table] == after[table], table
    for table in (
        "delivery_graph_requests",
        "delivery_graph_anchors",
        "delivery_graph_source_versions",
        "delivery_graph_scope_jobs",
    ):
        assert all(row in after[table] for row in before[table]), table
    (tmp_path / "upgrade-proof.json").write_text(
        json.dumps(
            dict(
                old_api_hash=expected,
                old_api_negative=404,
                old_plan_source_rejected=409,
                explicit_refresh=True,
                old_literal_json_before_refresh_preserved=True,
                old_plan_jobs_retained=True,
                new_check=checked.json(),
                overall_acceptance="NOT_ACCEPTED",
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
