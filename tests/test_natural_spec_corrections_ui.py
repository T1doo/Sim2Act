import json
import os
import subprocess

import pytest
from test_natural_spec_apps import transport
from test_natural_spec_corrections import rejected
from test_pb_natural_specs import drive_to_success
from test_spec_app_operations import snapshot

from sim2act.db import fingerprint


@pytest.mark.parametrize("family,scenario", [("pa", "normal"), ("pb", "run-lost")])
def test_visible_rejection_correction_and_independent_owner(env, tmp_path, family, scenario):
    data, inst, rid, _, goal, content, _, _, _ = rejected(env, family)
    before = snapshot(data[0])
    app = data[2].get("/api/apps/" + inst["source_app_id"]).json()
    info = dict(
        project=data[4],
        name=app["name"],
        run=rid,
        goal_text=goal["content"]["goal"],
        scenario=scenario,
        output=str(tmp_path / "result.json"),
    )
    path = tmp_path / "info.json"
    path.write_text(json.dumps(info))
    stderr = tmp_path / "node.stderr"
    worked = []
    worker_proofs = []
    http_log = tmp_path / "http.ndjson"
    with stderr.open("w") as err:
        process = subprocess.Popen(
            ["node", "tests/natural_spec_corrections_ui.cjs", str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=err,
            text=True,
            env={**os.environ, "NODE_PATH": "/workspace/node-tools/node_modules"},
        )
        try:
            for line in process.stdout:
                request = json.loads(line)
                if request.get("done"):
                    break
                if request.get("command") == "worker":
                    sent = []
                    claims = drive_to_success(data, request["rid"], transport(sent, content))
                    worked.append(request["rid"])
                    worker_proofs.append(dict(run_id=request["rid"], claims=claims, wire=sent))
                    (tmp_path / "worker-proof.json").write_text(json.dumps(worker_proofs, indent=2))
                    answer = dict(id=request["id"], status=200, text="{}")
                else:
                    response = data[2].request(
                        request["method"],
                        request["path"],
                        json=request.get("body"),
                        headers=request.get("headers"),
                    )
                    answer = dict(
                        id=request["id"],
                        status=response.status_code,
                        text=response.text,
                        content_type=response.headers.get("content-type"),
                    )
                    if not request["path"].endswith((".js", ".css")) and request["path"] != "/":
                        with http_log.open("a") as log:
                            log.write(json.dumps(dict(request=request, response=answer)) + "\n")
                process.stdin.write(json.dumps(answer) + "\n")
                process.stdin.flush()
            process.stdin.close()
            code = process.wait(timeout=20)
            assert code == 0, stderr.read_text()
            proof = json.loads((tmp_path / "result.json").read_text())
            assert proof["status"] == "PASS"
            assert len(worked) == 1 and len(proof["checks"]) > 20
            child = worked[0]
            assert [view["run"]["status"] for view in proof["run_views"]] == ["QUEUED", "SUCCEEDED"]
            assert all(view["run"]["id"] == child for view in proof["run_views"])
            after = snapshot(data[0])
            for table in ["runs", "internal_app_runs", "internal_instance_data",
                          "natural_owner_records", "natural_owner_seals"]:
                assert all(row in after[table] for row in before[table]), table
            assert len(after["internal_instance_data"]) == len(before["internal_instance_data"]) + 1
            route = f"/api/internal/instances/{inst['id']}/runs/{child}/spec-owner-review"
            state = data[2].get(route).json()
            assert state["owner_acceptance"] == "ACCEPTED"
            # The original one-layer contract still rejects this child as a
            # correction parent, before any new Run or model call is created.
            body = dict(request_key="no-recursive-correction", expected_owner_sequence=state["sequence"],
                        declaration_id=state["latest"]["id"],
                        declaration_fingerprint=state["latest"]["fingerprint"],
                        expected_context_fingerprint=fingerprint(state["current"]))
            recursive = data[2].post(route.replace("/spec-owner-review", "/correction-reviews"), json=body)
            assert recursive.status_code == 409, recursive.text
            assert "Corrections-of-corrections" in recursive.text
            assert snapshot(data[0]) == after
            (tmp_path / "history-proof.json").write_text(json.dumps(dict(
                parent_run_id=rid, child_run_id=child, preserved_tables=["runs", "internal_app_runs",
                    "internal_instance_data", "natural_owner_records", "natural_owner_seals"],
                before=before, after=after, recursive_status=recursive.status_code,
                recursive_response=recursive.json(), real_model_requests=0), indent=2))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
