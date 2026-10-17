"""Actual complete-MD controls + ASGI/SQLite/original Worker, synthetic NoModel only."""

import hashlib
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest
from sqlalchemy import select
from test_csv_full_report import source
from test_csv_goal_revisions import raw_trace as raw_trace
from test_internal_lifecycle import limits
from test_natural_receipt_candidate import table_snapshot
from test_ordinary_csv_report import NoModel

from sim2act.db import Store, attempts, internal_run_bindings, reservations
from sim2act.worker import Worker


@pytest.mark.parametrize("case", ["deliver", "lost", "navigation"])
def test_visible_complete_md_internal_delivery_and_original_run(env, tmp_path, case):
    rid, original, _, _ = source(env)
    client = env[2]
    materials = []
    for name, content in (
        ("instance-fresh.csv", "amount,quantity\n30,6\n50,9\n"),
        ("other-instance-fresh.csv", "quantity\n100\n200\n"),
    ):
        response = client.post(
            f"/api/projects/{env[5]}/resources",
            json=dict(name=name, format="csv", content=content),
        )
        assert response.status_code == 201, response.text
        materials.append(response.json()["id"])
    other = client.post("/api/projects", json=dict(name="other owner project"))
    assert other.status_code == 201, other.text
    info = dict(
        case=case,
        run=rid,
        project=env[5],
        other=other.json()["id"],
        material=materials[0],
        next_material=materials[1],
        output=str(tmp_path / "page-result.json"),
    )
    (tmp_path / "info.json").write_text(json.dumps(info))
    before = table_snapshot(env[0])
    process = watchdog = None
    worker_runs = []
    try:
        with (tmp_path / "node.stderr").open("w") as errors:
            process = subprocess.Popen(
                ["node", "tests/csv_full_report_instance_pages.cjs", str(tmp_path / "info.json")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                text=True,
                env={
                    **os.environ,
                    "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules"),
                },
            )
            # Multi-stage real API/UI fixture bound, not a changed server deadline.
            watchdog = threading.Timer(240, process.kill)
            watchdog.start()
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    assert case == "deliver"
                    assert Worker(env[0], env[1], NoModel()).once()
                    result = client.get(f"/api/runs/{request['run']}")
                    assert result.status_code == 200, result.text
                    actual = result.json()
                    assert actual["status"] == "SUCCEEDED", actual
                    worker_runs.append(actual)
                    answer = dict(status=200, text="{}")
                elif request.get("command") == "second-instance":
                    # Only the alternative navigation instance is API setup;
                    # the positive Release/commit/create/select chain is UI.
                    assert case == "navigation"
                    root = client.get(f"/api/internal/releases/{request['release']}")
                    assert root.status_code == 200, root.text
                    response = client.post(
                        f"/api/internal/releases/{request['release']}/instances",
                        json=dict(
                            expected_release_fingerprint=root.json()["fingerprint"],
                            request_key="navigation-other-instance",
                        ),
                    )
                    assert response.status_code == 201, response.text
                    answer = dict(status=response.status_code, text=response.text)
                else:
                    response = client.request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers"),
                    )
                    answer = dict(
                        status=response.status_code,
                        text=response.text,
                        content_type=response.headers.get("content-type"),
                    )
                process.stdin.write(json.dumps(dict(id=request["id"], **answer)) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=15)
        assert code == 0, (tmp_path / "node.stderr").read_text()
        page = json.loads((tmp_path / "page-result.json").read_text())
        assert page["status"] == "PASS", page
        for asset in page["assets"]:
            path = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["sha256"]
        assert len(worker_runs) == (1 if case == "deliver" else 0)
        assert not [r for r in page["requests"] if r["status"] >= 400]
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        assert client.get(f"/api/runs/{rid}").json() == original
        after = table_snapshot(env[0])
        for table in ("principals", "app_drafts"):
            assert before[table] == after[table], table
        if case == "deliver":
            originals = {row["id"]: row for row in before["grants"]}
            current = {row["id"]: row for row in after["grants"]}
            assert all(current[key] == value for key, value in originals.items())
            added = [row for key, row in current.items() if key not in originals]
            artifact = worker_runs[0]["result"]["receipts"][-1]["data"]["resource_id"]
            assert len(added) == 2
            assert {row["principal_id"] for row in added} == {env[3], worker_runs[0]["runtime_id"]}
            assert all(
                row["resource_id"] == artifact
                and row["tool_ref"] == "resource.read"
                and row["project_id"] == env[5]
                and not row["revoked"]
                for row in added
            )
        else:
            assert before["grants"] == after["grants"]
        with env[0].tx() as c:
            assert not c.execute(select(attempts)).first()
            assert not c.execute(select(reservations)).first()
            assert not c.execute(select(internal_run_bindings)).first()
        assert len(after["csv_report_workflows"]) == 1
        assert len(after["csv_report_workflow_uses"]) == (2 if case == "navigation" else 1)
        assert len(after["internal_app_runs"]) == (2 if case == "navigation" else 1)
        assert len(after["operations"]) == len(before["operations"]) + (
            3 if case == "deliver" else 0
        )
        if case == "deliver":
            delivery = page["delivery"]
            reopened = Store(env[1].database_url, test_only=True)
            try:
                from sim2act.csv_full_report_instances import delivery as inspect_delivery

                saved = inspect_delivery(reopened, env[3], delivery["aid"], limits(env))
            finally:
                reopened.engine.dispose()
            instance = next(i for i in saved["instances"] if i["id"] == delivery["instance"])
            assert instance["revision"] == 2 and instance["data_version"] == 1
            assert instance["release_id"] == delivery["second_release"]
            assert len(instance["data"]) == len(instance["runs"]) == 1
            record = instance["data"][0]["data"]["result"]
            assert record["ordinary_run_id"] == delivery["run"] and record["sum"] == "15"
            assert client.get(f"/api/runs/{delivery['run']}").json() == worker_runs[0]
            (tmp_path / "reopened-store-delivery.json").write_text(
                json.dumps(saved, ensure_ascii=False, indent=2)
            )
        else:
            uses = [
                r["response"]
                for r in page["requests"]
                if r["method"] == "POST" and r["path"].endswith("/csv-full-report-uses")
            ]
            for receipt in uses:
                actual = client.get(f"/api/runs/{receipt['run_id']}")
                assert actual.status_code == 200, actual.text
                assert actual.json()["status"] == "WAITING_APPROVAL"
            assert not (tmp_path / "page-result.download.md").exists()
    finally:
        if watchdog is not None:
            watchdog.cancel()
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        (tmp_path / "page-worker-proof.json").write_text(
            json.dumps(
                dict(original=original, worker_runs=worker_runs, real_model_requests=0),
                ensure_ascii=False,
                indent=2,
            )
        )
