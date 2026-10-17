"""Unified existing DAG instance controls, real HTTP/Worker and finite branch boundary."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from test_controlled_branches import proof as branch_proof
from test_controlled_branches import setup as branch_setup
from test_controlled_branches import start as branch_start
from test_csv_dag import NoModel
from test_csv_dag_instances import create, release
from test_csv_two_sum_instances import DECIMAL, STEPS, check_output
from test_csv_two_sum_instances import release as dual_release
from test_literal_directory import rows
from test_project_column_versions import created as fixed_created

from sim2act.db import Store, grants, internal_app_runs, internal_instance_data, runs
from sim2act.worker import Worker


@pytest.mark.parametrize("scenario", ["use", "report", "guards", "dual", "fixed",
                                      "download-use", "download-report", "download-dual", "download-fixed"])
def test_saved_csv_dag_directory_actual_http(env, tmp_path, scenario):
    family = scenario.removeprefix("download-")
    downloading = scenario.startswith("download-")
    store, settings, client, owner, _, project, _ = env
    assert store.sqlite and store.test_only and settings.mode == "mock"
    with store.tx() as c:
        original_runs = set(c.execute(select(runs.c.id)).scalars())
    fixture_group = None
    if family == "dual":
        aid, resource, _, source, rel = dual_release(env, DECIMAL)
        first = create(env, rel)
    elif family == "fixed":
        values, _, _, _, _, _, fixture_group = fixed_created(env)
        aid, resource = values[3], values[5]  # The other group member, not its anchor application.
        entry = next(e for e in fixture_group["entries"] if e["app_id"] == aid)
        rel = client.get(f"/api/internal/releases/{entry['release_id']}").json()
        first = client.get(f"/api/internal/instances/{entry['instance_id']}").json()
        source = client.get(f"/api/csv-dag/runs/{rel['snapshot']['execution_source']['run_id']}").json()
    else:
        aid, resource, _, source, rel = release(env, with_report=family == "report")
        first = create(env, rel)
    second = create(env, rel, "second-directory-instance")
    selection_listing = None
    if family in {"dual", "fixed"}:
        listing = client.get(f"/api/internal/apps/{aid}/dag-instances")
        assert listing.status_code == 200, listing.text
        selection_listing = listing.json()
        assert len(selection_listing["items"]) == 2
        choices = {i["id"]: i for i in (first, second)}
        assert set(choices) == {i["id"] for i in selection_listing["items"]}
        saved, unselected = (choices[i["id"]] for i in reversed(selection_listing["items"]))
    else:
        saved, unselected = first, second
    with store.tx() as c:
        fixture_runs = c.execute(select(runs).where(runs.c.id.not_in(original_runs))).mappings().all()
    assert len(fixture_runs) == (4 if family == "fixed" else 1)
    assert all(r["status"] == "SUCCEEDED" for r in fixture_runs)
    (tmp_path / "fixture-proof.json").write_text(json.dumps({
        "source_worker_run_ids": [r["id"] for r in fixture_runs],
        "selected_source_run": source, "release": rel, "selected_instance": saved,
        "unselected_instance": unselected, "authoritative_selection_listing": selection_listing,
        "project_version_group": fixture_group,
    }, indent=2) + "\n")
    inspected = client.get(f"/api/apps/{aid}").json()
    approval = client.post(f"/api/internal/apps/{aid}/release-approvals", json={
        "expected_draft_fingerprint": inspected["fingerprint"], "sample_input": {"column": "amount"},
    })
    assert approval.status_code == 201, approval.text
    a = approval.json()
    committed = client.post(f"/api/internal/approvals/{a['id']}/commit", json={"fingerprint": a["fingerprint"]})
    assert committed.status_code == 200, committed.text
    plain = create(env, committed.json(), "plain-directory-instance")
    other = store.project(owner, "Other owned project")
    baseline = rows(store)
    authority = {name: baseline[name] for name in ("principals", "grants")}
    normal_list = client.get(f"/api/internal/apps/{aid}/instances")
    dag_list = client.get(f"/api/internal/apps/{aid}/dag-instances")
    assert normal_list.status_code == dag_list.status_code == 200
    assert [v["id"] for v in normal_list.json()["items"]] == [plain["id"]]
    assert {v["id"] for v in dag_list.json()["items"]} == {saved["id"], unselected["id"]}
    assert rows(store) == baseline
    info = dict(project=project, other=other, app=aid, instance=saved["id"],
                second_instance=unselected["id"], plain_instance=plain["id"], release=rel["id"],
                resource=resource, execution=rel["snapshot"]["execution_source"],
                source_run=source["id"], nodes=2 if family in {"use", "guards"} else 3,
                scenario=family, download=downloading, output=str(tmp_path / "result.json"))
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    worked, checkpoints, revocations = 0, 0, 0
    stderr = tmp_path / "node.stderr"
    process = None
    try:
        with stderr.open("w") as errors:
            process = subprocess.Popen(["node", "tests/csv_dag_directory.cjs", str(path)],
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
                    assert all(baseline[name] == expected for name, expected in authority.items())
                    answer = dict(status=200, text="{}")
                elif command == "readonly":
                    assert rows(store) == baseline
                    checkpoints += 1
                    answer = dict(status=200, text="{}")
                elif command == "revoke":
                    assert (family == "guards" or downloading and family == "dual") and revocations == 0
                    with store.tx() as c:
                        grant = c.execute(select(grants).where(grants.c.principal_id == owner,
                            grants.c.resource_id == resource, grants.c.tool_ref == "resource.read")).mappings().one()
                    response = client.post(f"/api/grants/{grant['id']}/revoke", json={
                        "command": "revoke", "version": grant["revision"],
                    })
                    assert response.status_code == 200
                    current = rows(store)
                    assert all(current[name] == value for name, value in baseline.items() if name != "grants")
                    baseline = current
                    revocations += 1
                    answer = dict(status=response.status_code, text=response.text)
                else:
                    response = client.request(request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"))
                    answer = dict(status=response.status_code, text=response.text,
                                  content_type=response.headers.get("content-type"))
                process.stdin.write(json.dumps({"id": request["id"], **answer}) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
        assert code == 0, stderr.read_text()
        proof = json.loads((tmp_path / "result.json").read_text())
        assert proof["status"] == "PASS" and worked == (0 if scenario == "guards" else 2)
        assert checkpoints >= 2 and revocations == int(family == "guards" or downloading and family == "dual") and rows(store) == baseline
        with store.tx() as c:
            typed = c.execute(select(internal_app_runs).where(
                internal_app_runs.c.instance_id == saved["id"])).mappings().all()
            records = c.execute(select(internal_instance_data).where(
                internal_instance_data.c.instance_id == saved["id"])
                .order_by(internal_instance_data.c.version)).mappings().all()
        assert len(typed) == len(records) == worked
        if worked:
            assert [r["version"] for r in records] == [1, 2]
            if family == "dual":
                for record, columns in zip(records, [dict(zip(STEPS, ["quantity", "amount"], strict=True)),
                                                     dict(zip(STEPS, ["amount", "quantity"], strict=True))], strict=True):
                    check_output(record["data"]["result"], DECIMAL, resource, columns)
            else:
                assert [r["data"]["result"]["sum"] for r in records] == (["30", "15"] if family == "fixed" else ["15", "30"])
                assert [r["data"]["result"]["column"] for r in records] == (["amount", "quantity"] if family == "fixed" else ["quantity", "amount"])
        if family in {"dual", "fixed"} and not (downloading and family == "dual"):
            detail = client.get(f"/api/internal/instances/{saved['id']}").json()
            assert len(detail["runs"]) == 2 and detail["release_id"] == rel["id"]
            for record in detail["data"]:
                run = next(r for r in detail["runs"] if r["app_run_id"] == record["run_id"])
                assert run["instance_id"] == saved["id"] and run["release_id"] == record["release_id"] == rel["id"]
                assert run["run_id"] == run["proof"]["id"] and run["result_version"] == record["version"]
                assert run["output"] == record["data"]["result"]
                assert run["execution_version"] == rel["snapshot"]["execution_source"]["version"]
                assert run["proof"]["result"]["instance_result"]["record_fingerprint"] == record["fingerprint"]
            untouched = client.get(f"/api/internal/instances/{unselected['id']}").json()
            assert untouched["data_version"] == 0 and untouched["runs"] == untouched["data"] == []
            assert rows(store) == baseline
            (tmp_path / "final-instance-proof.json").write_text(json.dumps({
                "selected": detail, "unselected": untouched,
            }, indent=2) + "\n")
        for asset in proof["assets"]:
            file = Path("src/sim2act/web") / (asset["path"].lstrip("/") or "index.html")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == asset["sha256"]
        (tmp_path / "database-proof.json").write_text(json.dumps({
            "download_feature": downloading, "backend": "SQLite synthetic", "tables": len(baseline), "read_checkpoints": checkpoints,
            "all_get_rows_unchanged": True, "fixture_source_worker_runs": len(fixture_runs),
            "cold_worker_runs_from_directory": worked, "source_run_id": source["id"],
            "new_result_versions": [r["version"] for r in records],
            "authority_unchanged_except_explicit_revoke": True, "controlled_revocations": revocations,
            "generation_model_calls": 0, "runtime_model_calls": 0,
            "directory_end_to_end_variants": [rel["snapshot"]["execution_source"]["version"]],
            "pg": "NOT_RUN", "native_browser": "NOT_RUN", "real_semantics": "NOT_RUN",
        }, indent=2) + "\n")
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def test_existing_finite_csv_branches_are_not_saved_dag_instances(env, tmp_path):
    resource, base, plan, _ = branch_setup(env)
    baseline = rows(env[0])
    authority = {name: baseline[name] for name in ("principals", "grants")}
    results = []
    for enabled in (False, True):
        worker, job, _ = branch_start(env, base, plan, {"include_report": enabled}, str(enabled))
        worker.process(job)
        before = rows(env[0])
        value = branch_proof(env, job)
        assert value["status"] == ("SUCCEEDED" if enabled else "PARTIAL")
        assert [step["status"] for step in value["steps"]] == ["VERIFIED", "VERIFIED", "VERIFIED" if enabled else "SKIPPED"]
        assert value["result"]["output_status"] == ("PRODUCED" if enabled else "SKIPPED")
        assert (value["result"]["output"] is None) is (not enabled)
        rejected = env[2].post(f"/api/csv-dag/runs/{job['id']}/release-approvals", json={
            "expected_plan_fingerprint": plan["plan_fingerprint"], "request_key": "branch-" + str(enabled),
        })
        assert rejected.status_code == 409, rejected.text
        assert rows(env[0]) == before
        assert all(before[name] == original for name, original in authority.items())
        results.append(dict(enabled=enabled, actual_run=value, release_status=rejected.status_code,
                            release_response=rejected.json()))
    listing = env[2].get(f"/api/internal/apps/{plan['app_id']}/dag-instances")
    assert listing.status_code == 200 and listing.json()["items"] == []
    (tmp_path / "branch-proof.json").write_text(json.dumps({
        "backend": "SQLite synthetic", "resource": resource, "finite_branch_cases": results,
        "dag_instances": listing.json(), "model_requests": 0,
        "scope": "Existing typed boolean branch semantics only; conditional plans remain ineligible for internal instances. Not exceptional recovery.",
        "pg": "NOT_RUN", "native_browser": "NOT_RUN",
    }, indent=2) + "\n")
