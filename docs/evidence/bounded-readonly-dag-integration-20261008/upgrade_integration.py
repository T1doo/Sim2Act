"""Owned latest-dev actual-source upgrade followed by a new four-node run."""

import json

from conftest import env as env
from test_csv_composition import composition, start
from test_csv_dag_upgrade import raw_history_hashes
from test_csv_dag_upgrade import (
    test_actual_old_source_upgrade_retains_history_and_requires_new_exact_confirmation as original_upgrade,
)

BASE = "a02371d44208dc2bc4b561a540dd4afa665e57d8"
MODULE = "d315701b8995a37d8faaff00bdbb806c732a5c4936b8f106e6b4e81941f9caf9"


def test_latest_dev_actual_source_upgrade_then_exact_four_node_composition(env, tmp_path):
    original_upgrade(env, tmp_path, "SIM2ACT_UPGRADE_INTEGRATION_ARCHIVE", BASE, MODULE)
    original = json.loads((tmp_path / "old-source-proof.json").read_text())
    before = json.loads((tmp_path / "upgrade-proof.json").read_text())
    tables = before["preserved_historical_tables"]
    raw_before = raw_history_hashes(env[0], tables)
    aid, base = original["app_id"], original["base"]
    app = env[2].get(f"/api/apps/{aid}").json()
    anchor = env[2].get(f"/api/projects/{env[5]}/apps/{aid}/delivery-graph").json()
    body = dict(expected_candidate_fingerprint=app["fingerprint"],
                expected_graph_fingerprint=anchor["graph_fingerprint"], column="amount",
                request_key="after-upgrade-four", composition=composition())
    reply = env[2].post(base, json=body)
    assert reply.status_code == 201, reply.text
    plan = reply.json()
    rejected = env[2].post(base + "/after-upgrade-four/runs", json=original["old_confirmation"])
    assert rejected.status_code == 409
    worker, job, confirmation = start(env, base, plan, key="new-four-after-upgrade")
    worker.process(job)
    result = env[2].get(f"/api/csv-dag/runs/{job['id']}")
    assert result.status_code == 200, result.text
    proof = result.json()
    assert proof["status"] == "SUCCEEDED" and len(proof["steps"]) == 4
    assert proof["result"]["output_by_step"]["a_report"]["sum"] == "30"
    assert proof["result"]["output_by_step"]["b_report"]["sum"] == "15"
    assert proof["model_requests"] == proof["business_writes"] == 0
    raw_after = raw_history_hashes(env[0], tables)
    assert all(set(raw_before[name]) <= set(raw_after[name]) for name in tables)
    (tmp_path / "composition-upgrade-proof.json").write_text(json.dumps(dict(
        baseline_source=BASE, old_module_sha256=MODULE, original_upgrade=before,
        confirmation=confirmation, plan=plan, four_node_run=proof,
        historical_rows_and_json_bytes_retained=True), ensure_ascii=False, indent=2))
