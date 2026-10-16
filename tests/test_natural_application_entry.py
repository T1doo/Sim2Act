"""Unified saved natural-app entry over actual HTTP and mock-only Worker."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_natural_spec_apps import transport
from test_pa_natural_uses import prepared_pa
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD, prepared_use
from test_spec_app_operations import snapshot

from sim2act.api import create_app
from sim2act.db import Store


@pytest.mark.parametrize("family,scenario", [("pa", "normal"), ("pb", "normal"), ("pa", "lost")])
def test_saved_natural_app_visible_use_entry(env, tmp_path, family, scenario):
    if family == "pa":
        data, app, release, inst, _, resource, goal, _, route = prepared_pa(env, history=False)
    else:
        data, app, release, inst, resource, goal, _, route = prepared_use(env, run_base=True)
    assert data[0].test_only and data[1].mode == "mock"
    original = data[2].get(route)
    assert original.status_code == 200, original.text
    original = original.json()
    old_versions = sorted(row["version"] for row in original["data"])
    assert old_versions == [1]
    initial = snapshot(data[0])
    readonly_baseline = initial
    catalog = data[2].get("/api/apps?metadata_only=true")
    assert catalog.status_code == 200, catalog.text
    family_summary = next(row for row in catalog.json()["items"] if row["id"] == app["id"])
    assert family_summary["use_family"] == "NATURAL_" + family.upper()
    assert family_summary["definition_version"] == "pa-natural-spec-app.v1"
    assert "candidate" not in family_summary and "fingerprint" not in family_summary
    foreign_catalog = data[2].get("/api/apps?metadata_only=true", headers={"Authorization": "Bearer synthetic-test-B"})
    assert foreign_catalog.status_code == 200, foreign_catalog.text
    assert all(row["id"] != app["id"] for row in foreign_catalog.json()["items"])
    foreign_app = data[2].get("/api/apps/" + app["id"], headers={"Authorization": "Bearer synthetic-test-B"})
    assert foreign_app.status_code == 403, foreign_app.text
    assert snapshot(data[0]) == initial
    route_proof = dict(
        catalog=dict(status=catalog.status_code, body=catalog.json()),
        other_identity_catalog=dict(status=foreign_catalog.status_code, body=foreign_catalog.json()),
        other_identity_app=dict(status=foreign_app.status_code, body=foreign_app.json()),
        discovery_readonly=True,
    )
    info = dict(
        family=family,
        scenario=scenario,
        project=data[4],
        app=app["id"],
        name=app["name"],
        release=release["id"],
        instance=inst["id"],
        resource=resource,
        goal=goal["id"],
        content=THIRD,
        old_versions=old_versions,
        original_runs=[row["id"] for row in original["runs"]],
        expected_version=original["data_version"] + 1,
        revoke_after=family == "pa" and scenario == "normal",
        output=str(tmp_path / "result.json"),
    )
    info_path = tmp_path / "info.json"
    info_path.write_text(json.dumps(info), encoding="utf-8")
    sent = []
    cold = cold_client = None
    revoked_grant = None
    stderr = tmp_path / "node.stderr"
    node_modules = Path.cwd() / "scripts/engineering-ci/node_modules"
    with stderr.open("w", encoding="utf-8") as err:
        process = subprocess.Popen(
            ["node", str(Path(__file__).with_name("natural_application_entry.cjs")), str(info_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=err,
            text=True,
            env={**os.environ, "NODE_PATH": str(node_modules)},
        )
        try:
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                command = request.get("command")
                if command == "worker":
                    assert request["run_id"] not in info["original_runs"]
                    cold = Store(data[1].database_url, test_only=True)
                    cold_client = TestClient(create_app(cold, data[1]))
                    cold_client.headers["Authorization"] = "Bearer synthetic-test-A"
                    drive_to_success(
                        (cold, data[1], cold_client, *data[3:]),
                        request["run_id"],
                        transport(sent, THIRD),
                    )
                    readonly_baseline = snapshot(cold)
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "readonly-checkpoint":
                    assert snapshot(cold or data[0]) == readonly_baseline
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "freeze-readonly-baseline":
                    readonly_baseline = snapshot(cold or data[0])
                    answer = dict(id=request["id"], status=200, text="{}")
                elif command == "revoke-original":
                    assert info["revoke_after"] and revoked_grant is None
                    active_client = cold_client or data[2]
                    listed = active_client.get(f"/api/projects/{data[4]}/grants")
                    assert listed.status_code == 200, listed.text
                    original_resource = app["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
                    matches = [row for row in listed.json() if row["principal_id"] == app["runtime_id"]
                               and row["resource_id"] == original_resource and row["tool_ref"] == "resource.read"
                               and not row["revoked"]]
                    assert len(matches) == 1, matches
                    revoked_grant = matches[0]
                    revoked = active_client.post(f"/api/grants/{revoked_grant['id']}/revoke",
                        json={"command": "revoke", "version": revoked_grant["revision"]})
                    assert revoked.status_code == 200, revoked.text
                    route_proof["explicit_grant_revocation"] = dict(
                        list_status=listed.status_code, selected_grant=revoked_grant,
                        revoke_status=revoked.status_code, revoke_body=revoked.json(),
                    )
                    readonly_baseline = snapshot(cold or data[0])
                    answer = dict(id=request["id"], status=200, text=json.dumps(route_proof["explicit_grant_revocation"]))
                else:
                    assert command is None, request
                    reply = (cold_client or data[2]).request(
                        request["method"], request["path"],
                        json=request.get("body"), headers=request.get("headers"),
                    )
                    answer = dict(
                        id=request["id"], status=reply.status_code,
                        text=reply.text, content_type=reply.headers.get("content-type"),
                    )
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            assert process.wait(timeout=20) == 0, stderr.read_text(encoding="utf-8")
            proof = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
            assert proof["status"] == "PASS", proof
            assert len(proof["checks"]) >= 25 and len(sent) == 1
            assert proof["run_id"] not in info["original_runs"]
            web = Path.cwd() / "src/sim2act/web"
            assert proof["static_resource_loads"]
            for row in proof["static_resource_loads"]:
                name = "index.html" if row["path"] == "/" else row["path"][1:]
                assert row["sha256"] == hashlib.sha256((web / name).read_bytes()).hexdigest()
            final = snapshot(cold or data[0])
            for table in ["app_drafts", "internal_releases", "goal_cards", "goal_card_versions", "principals"]:
                assert final[table] == initial[table], table
            for row in initial["grants"]:
                expected = {**row, "revoked": True, "revision": row["revision"] + 1} if revoked_grant and row["id"] == revoked_grant["id"] else row
                assert expected in final["grants"]
            previous = [row for row in initial["internal_instance_data"] if row["instance_id"] == inst["id"]]
            current = [row for row in final["internal_instance_data"] if row["instance_id"] == inst["id"]]
            assert all(row in current for row in previous)
            assert sorted(row["version"] for row in current) == old_versions + [info["expected_version"]]
            (tmp_path / "runtime-wire.json").write_text(json.dumps(sent, ensure_ascii=False, indent=2), encoding="utf-8")
            (tmp_path / "persistence-proof.json").write_text(json.dumps(dict(
                family=family, old_versions=old_versions,
                new_versions=sorted(row["version"] for row in current),
                previous_rows_retained=True, frozen_apps_releases_goals_principals_unchanged=True,
                existing_grants_retained_except_explicit_revocation=True,
                actual_run=proof["run_id"], actual_worker_wire_count=len(sent), real_model_requests=0,
            ), indent=2), encoding="utf-8")
            (tmp_path / "route-contract-proof.json").write_text(json.dumps(route_proof, ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if cold_client:
                cold_client.close()
            if cold:
                cold.engine.dispose()


def test_natural_entry_navigation_synthesized_api(tmp_path):
    """Production scripts, synthetic GET API and renderer stubs; no Worker/HTTP."""
    output = tmp_path / "navigation.json"
    outcome = subprocess.run(
        ["node", "tests/natural_application_navigation.cjs", str(output)],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "NODE_PATH": str(Path.cwd() / "scripts/engineering-ci/node_modules")},
    )
    (tmp_path / "driver.log").write_text(outcome.stdout + outcome.stderr)
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr
    proof = json.loads(output.read_text())
    assert proof["status"] == "PASS" and len(proof["checks"]) == 36, proof
    assert proof["followup_instance_workspace_aba"]["isolated"]
    assert proof["owner_clear_stale_status"]["cleared"]
    web = Path.cwd() / "src/sim2act/web"
    assert proof["assets"] == {
        name: hashlib.sha256((web / name).read_bytes()).hexdigest()
        for name in proof["assets"]
    }
