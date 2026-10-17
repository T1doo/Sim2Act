"""Visible compatible adoption, cold own-Release downloads and real revocation."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import select
from test_csv_dag import NoModel
from test_csv_dag_instances import create, release
from test_csv_dag_version_switch import next_release
from test_literal_directory import rows

from sim2act.db import (
    Store,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    runs,
)
from sim2act.worker import Worker


def test_visible_compatible_adoption_cold_old_new_downloads_and_revoke(env, tmp_path):
    store, settings, client, owner, _, project, _ = env
    assert store.sqlite and store.test_only and settings.mode == "mock"
    with store.tx() as c:
        prior_runs = set(c.execute(select(runs.c.id)).scalars())
    aid, resource, plan, _, old = release(env, with_report=True)
    target = next_release(env, aid, plan, key="cross-release-target")
    instance = create(env, old)
    with store.tx() as c:
        sources = c.execute(select(runs).where(runs.c.id.not_in(prior_runs))).mappings().all()
    assert len(sources) == 2 and all(r["status"] == "SUCCEEDED" for r in sources)
    assert {old["snapshot"]["execution_source"]["run_id"], target["snapshot"]["execution_source"]["run_id"]} == {r["id"] for r in sources}
    (tmp_path / "fixture-proof.json").write_text(json.dumps({
        "old_release": old, "target_release": target, "instance": instance,
        "source_worker_run_ids": [r["id"] for r in sources],
        "source_creation": "Original release/next_release helpers: actual source-plan/run/release APIs and NoModel Workers. No direct DB mutation to adopt a version.",
    }, indent=2) + "\n")
    info = dict(project=project, app=aid, resource=resource, instance=instance["id"],
                old=old, target=target, download=True, output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    baseline = rows(store)
    authority = {k: baseline[k] for k in ("principals", "grants")}
    worked = checkpoints = revocations = 0
    mutations = []
    process = None
    stderr = tmp_path / "node.stderr"
    try:
        with stderr.open("w") as errors:
            process = subprocess.Popen(["node", "tests/csv_dag_cross_release_download.cjs", str(path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True,
                env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")})
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "worker":
                    cold = Store(settings.database_url, test_only=True)
                    try:
                        assert Worker(cold, settings, NoModel()).once()
                    finally:
                        cold.engine.dispose()
                    worked += 1
                    baseline = rows(store)
                    assert all(baseline[k] == v for k, v in authority.items())
                    answer = dict(status=200, text="{}")
                elif command == "checkpoint":
                    current = rows(store)
                    changed = {k for k in current if current[k] != baseline[k]}
                    expected = {"internal_approvals"} if request["stage"] == "prepare" else {"internal_approvals", "internal_instances"}
                    assert changed == expected
                    assert all(current[k] == v for k, v in authority.items())
                    mutations.append(dict(stage=request["stage"], changed_tables=sorted(changed)))
                    baseline = current
                    answer = dict(status=200, text="{}")
                elif command == "readonly":
                    assert rows(store) == baseline
                    checkpoints += 1
                    answer = dict(status=200, text="{}")
                elif command == "revoke":
                    assert revocations == 0
                    with store.tx() as c:
                        grant = c.execute(select(grants).where(grants.c.principal_id == owner,
                            grants.c.resource_id == resource, grants.c.tool_ref == "resource.read")).mappings().one()
                    response = client.post(f"/api/grants/{grant['id']}/revoke", json={"command": "revoke", "version": grant["revision"]})
                    assert response.status_code == 200
                    current = rows(store)
                    assert all(current[k] == v for k, v in baseline.items() if k != "grants")
                    baseline = current
                    revocations += 1
                    answer = dict(status=200, text="{}")
                else:
                    response = client.request(request["method"], request["path"], json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=response.status_code, text=response.text, content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, stderr.read_text()
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "PASS" and worked == 2 and revocations == 1 and checkpoints >= 5
        assert rows(store) == baseline
        with store.tx() as c:
            saved = c.execute(select(internal_instances).where(internal_instances.c.id == instance["id"])).mappings().one()
            data = c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id == instance["id"])
                .order_by(internal_instance_data.c.version)).mappings().all()
            typed = c.execute(select(internal_app_runs).where(internal_app_runs.c.instance_id == instance["id"])).mappings().all()
        assert saved["release_id"] == target["id"] and saved["revision"] == saved["data_version"] == 2
        assert [r["release_id"] for r in data] == [old["id"], target["id"]]
        assert [r["data"]["result"]["sum"] for r in data] == ["30", "15"]
        assert len(typed) == 2 and all(r["status"] == "SUCCEEDED" for r in typed)
        for asset in result["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "backend": "SQLite synthetic", "tables": len(baseline), "read_checkpoints": checkpoints,
            "all_get_rows_unchanged": True, "source_worker_runs": len(sources), "directory_cold_worker_runs": worked,
            "ui_switch_checkpoints": mutations, "controlled_revocations": revocations,
            "principal_grant_unchanged_during_adoption_and_execution": True,
            "final_instance": dict(saved), "final_records": [dict(r) for r in data],
            "generation_model_calls": 0, "runtime_model_calls": 0,
            "pg": "NOT_RUN", "native_browser": "NOT_RUN", "real_models_semantics": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
