"""Actual old executable source → current integration, no migration of old proofs."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import JSON, Text, cast, select
from test_csv_dag import NoModel
from test_delivery_graph_apps import snapshot

from sim2act import csv_dag
from sim2act.db import fingerprint, meta
from sim2act.worker import Worker


def raw_history_hashes(store, names):
    """Hash literal stored JSON text, preserving representation as well as values."""
    result = {}
    with store.tx() as c:
        for name in names:
            table = meta.tables[name]
            fields = [*table.primary_key.columns,
                      *[cast(column, Text).label(column.name) for column in table.columns
                        if isinstance(column.type, JSON)]]
            result[name] = sorted(fingerprint(list(row)) for row in c.execute(select(*fields)))
    return result


@pytest.mark.parametrize("archive_env,archive_sha,module_hash", [
    ("SIM2ACT_UPGRADE_OLD_ARCHIVE", "5a5543c902fbb78dd91c28c98386af51fb24dd67", "91efd66bd69498c0aa62eefa285112095383d4f950d6cab0c2fa017de0a02aa5"),
    ("SIM2ACT_UPGRADE_CORE_ARCHIVE", "1b65e94ebd81c1e31091b3078b8223328b726294", "240c76f358870a9d933f94d129eeda362553092035044d6f306ee4dd7a58b3c0"),
])
def test_actual_old_source_upgrade_retains_history_and_requires_new_exact_confirmation(env, tmp_path, archive_env, archive_sha, module_hash):
    archive_path = os.environ.get(archive_env)
    if not archive_path:
        pytest.skip("Actual old-source upgrade requires an explicitly prepared owned source archive")
    archive = Path(archive_path)
    old_source = archive / "src/sim2act/csv_dag.py"
    assert old_source.exists() and old_source.read_bytes() != Path(csv_dag.__file__).read_bytes()
    assert hashlib.sha256(old_source.read_bytes()).hexdigest() == module_hash
    output = tmp_path / "old-source-proof.json"
    body = dict(database_url=env[1].database_url,
                schema=env[0].engine.get_execution_options().get("schema_translate_map", {}).get(None),
                data_root=str(tmp_path), owner=env[3], other=env[4], project=env[5],
                resource=env[6], output=str(output))
    driver = Path(__file__).with_name("fixtures") / "csv_dag_upgrade.py"
    child = subprocess.run([sys.executable, str(driver)], cwd=archive,
                           env={**os.environ, "PYTHONPATH": str(archive / "src") + os.pathsep + str(archive / "tests"), "LIVE": "0"},
                           input=json.dumps(body), text=True, capture_output=True, timeout=60)
    assert child.returncode == 0, child.stdout + child.stderr
    old = json.loads(output.read_text())
    assert Path(old["old_module_path"]).resolve() == old_source.resolve()
    assert old["old_module_sha256"] == hashlib.sha256(old_source.read_bytes()).hexdigest()
    assert old["old_result"]["result"]["output"]["sum"] == "15"
    assert old["old_preview"]["output"]["sum"] == "30"
    before = snapshot(env)
    assert fingerprint(before) == fingerprint(old["old_snapshot"])
    immutable = ["runs", "operations", "operation_intents", "events", "delivery_graph_requests", "delivery_graph_anchors", "delivery_graph_source_versions", "app_drafts", "app_previews", "resources"]
    raw_before = raw_history_hashes(env[0], immutable)
    client, pid, aid = env[2], env[5], old["app_id"]
    rejected = []
    for path in [old["base"] + "/old-plan", f"/api/csv-dag/runs/{old['old_run']}",
                 old["base"], f"/api/projects/{pid}/apps/{old['other_app_id']}/delivery-graph",
                 f"/api/projects/{pid}/apps/{aid}/delivery-graph/column-patches"]:
        reply = client.get(path)
        assert reply.status_code == 409, reply.text
        rejected.append(dict(path=path, status=reply.status_code, error=reply.json()))
    replay = client.post(old["base"] + "/old-plan/runs", json=old["old_confirmation"])
    assert replay.status_code == 409
    metadata = client.get(f"/api/csv-dag/runs/{old['old_run']}/status")
    assert metadata.status_code == 200 and metadata.json()["proof_status"] == "NOT_VALIDATED"
    assert metadata.json()["result"] is None and metadata.json()["steps"] == []
    assert fingerprint(snapshot(env)) == fingerprint(before)  # All failed reads/replays write nothing.
    app = client.get(f"/api/apps/{aid}").json()
    graph = client.post(f"/api/projects/{pid}/apps/{aid}/delivery-graph/derive", json=dict(
        expected_candidate_fingerprint=app["fingerprint"], request_key="new-source-anchor"))
    assert graph.status_code == 201, graph.text
    history = client.get(old["base"])
    assert history.status_code == 200 and history.json()["invalidated"] == [dict(request_key="old-plan", state="INVALIDATED")]
    plan = client.post(old["base"], json=dict(expected_candidate_fingerprint=app["fingerprint"],
        expected_graph_fingerprint=graph.json()["graph_fingerprint"], column="quantity", request_key="new-source-plan"))
    assert plan.status_code == 201 and plan.json()["plan_fingerprint"] != old["old_plan"]["plan_fingerprint"]
    before_wrong = snapshot(env)
    wrong = client.post(old["base"] + "/new-source-plan/runs", json=old["old_confirmation"])
    assert wrong.status_code == 409 and fingerprint(snapshot(env)) == fingerprint(before_wrong)
    accepted = client.post(old["base"] + "/new-source-plan/runs", json=dict(
        expected_plan_fingerprint=plan.json()["plan_fingerprint"], consent="CONFIRM_EXACT_OFFLINE_CSV_DAG", request_key="new-source-run"))
    assert accepted.status_code == 202, accepted.text
    worker = Worker(env[0], env[1], NoModel())
    job = env[0].claim(worker.id, env[1].lease_seconds)
    assert job["id"] == accepted.json()["run_id"] != old["old_run"]
    worker.process(job)
    current = client.get(f"/api/csv-dag/runs/{job['id']}")
    assert current.status_code == 200 and current.json()["status"] == "SUCCEEDED"
    assert current.json()["result"]["output"]["sum"] == "15"
    after = snapshot(env)
    for name in immutable:
        assert set(map(fingerprint, before[name])) <= set(map(fingerprint, after[name])), name
    raw_after = raw_history_hashes(env[0], immutable)
    assert all(set(raw_before[name]) <= set(raw_after[name]) for name in immutable)
    (tmp_path / "upgrade-proof.json").write_text(json.dumps(dict(
        archive_sha=archive_sha, old_module_sha256=old["old_module_sha256"],
        rejected=rejected, old_control=metadata.json(), history_after_new_anchor=history.json(),
        current=current.json(), preserved_historical_tables=immutable,
        old_snapshot_fingerprint=fingerprint(before), old_raw_json_hashes=raw_before,
        old_json_storage_bytes_preserved=True, no_migration=True), ensure_ascii=False, indent=2))
