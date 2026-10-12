"""Actual immediately preceding product source, persisted old Report and new lock."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_csv_dag_upgrade import raw_history_hashes
from test_delivery_graph_apps import snapshot

from sim2act import manual_locks
from sim2act.db import fingerprint, meta


def test_actual_old_report_upgrade_preserves_literal_history_requires_new_anchor(env, tmp_path):
    archive_path = os.environ.get("SIM2ACT_REPORT_LOCK_OLD_ARCHIVE")
    if not archive_path:
        pytest.skip("Actual Report edit-lock upgrade requires explicitly prepared owned old source")
    archive = Path(archive_path)
    source = archive / "src/sim2act/manual_locks.py"
    expected = os.environ["SIM2ACT_REPORT_LOCK_OLD_MODULE_SHA256"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    assert source.read_bytes() != Path(manual_locks.__file__).read_bytes()
    proof = tmp_path / "old-report-lock-proof.json"
    body = dict(
        database_url=env[1].database_url,
        schema=env[0].engine.get_execution_options().get("schema_translate_map", {}).get(None),
        data_root=str(tmp_path),
        owner=env[3],
        other=env[4],
        project=env[5],
        resource=env[6],
        output=str(proof),
    )
    child = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("fixtures") / "report_edit_locks_upgrade.py"),
        ],
        cwd=archive,
        input=json.dumps(body),
        capture_output=True,
        text=True,
        timeout=90,
        env={
            **os.environ,
            "PYTHONPATH": str(archive / "src") + os.pathsep + str(archive / "tests"),
            "LIVE": "0",
            "SIM2ACT_LIVE_ENABLED": "false",
        },
    )
    (tmp_path / "child.log").write_text(child.stdout + child.stderr)
    assert child.returncode == 0, child.stdout + child.stderr
    old = json.loads(proof.read_text())
    assert Path(old["old_manual_module"]).resolve() == source.resolve()
    assert old["old_manual_sha256"] == expected and old["mock_calls"] == 4
    assert old["old_negative_status"] == 400
    before = snapshot(env)
    assert before == old["snapshot"]
    raw_before = raw_history_hashes(env[0], list(meta.tables))
    env[0].initialize()  # Explicit owner upgrade; no runtime/API migration.
    assert snapshot(env) == before and raw_history_hashes(env[0], list(meta.tables)) == raw_before
    app = old["app"]
    base = old["url"].removesuffix("report-presentations")
    rejected = env[2].get(old["url"])
    assert rejected.status_code == 409, rejected.text
    stale = env[2].post(base + "manual-locks", json=old["lock_request"])
    assert stale.status_code == 409, stale.text
    assert fingerprint(snapshot(env)) == fingerprint(before)
    anchor = env[2].post(
        base + "derive",
        json=dict(
            expected_candidate_fingerprint=app["fingerprint"], request_key="upgraded-report-anchor"
        ),
    )
    assert anchor.status_code == 201, anchor.text
    request = dict(
        old["lock_request"],
        expected_graph_fingerprint=anchor.json()["graph_fingerprint"],
        expected_graph_revision=anchor.json()["graph_revision"],
        request_key="upgraded-report-view-lock",
    )
    node = next(n for n in anchor.json()["graph"]["nodes"] if n["key"] == "view:text:decision")
    request["change"] = dict(
        node_id=node["id"],
        expected_revision=node["revision"],
        expected_content_fingerprint=node["content_fingerprint"],
    )
    assert node["id"] == old["lock_request"]["change"]["node_id"]
    accepted = env[2].post(base + "manual-locks", json=request)
    assert accepted.status_code == 201 and accepted.json()["lock"]["revision"] == 1, accepted.text
    after = snapshot(env)
    for table in before:
        assert (
            set(map(fingerprint, before[table])) <= set(map(fingerprint, after[table]))
            or table == "delivery_graph_states"
        ), table
    raw_after = raw_history_hashes(env[0], list(meta.tables))
    assert all(
        set(rows) <= set(raw_after[table])
        for table, rows in raw_before.items()
        if table != "delivery_graph_states"
    )
    assert env[2].get(f"/api/apps/{app['id']}").json()["candidate"] == app["candidate"]
    (tmp_path / "upgrade-proof.json").write_text(
        json.dumps(
            dict(
                source_sha="afb2f1f3813fc3a4744923f31bbcb4666b88cccd",
                old_manual_module_sha256=expected,
                old_entry_negative=old["old_negative_error"],
                old_history_rejection=rejected.json(),
                raw_json_preserved_on_explicit_upgrade=True,
                immutable_history_preserved_after_new_anchor=True,
                stable_view_id_retained=True,
                new_exact_lock=accepted.json(),
                status="PASS",
                real_models=0,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
