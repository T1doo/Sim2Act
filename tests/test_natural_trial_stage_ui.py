"""Actual page/root API with typed stage wire simulation. No fake backend acceptance."""

import json
import os
import re
import subprocess

import pytest
from sqlalchemy import select, update
from test_natural_spec_apps import recipe
from test_natural_trial_preparation import prepared_data  # noqa: F401

from sim2act import natural_live_admission as gate
from sim2act.db import delivery_graph_requests, fingerprint, grants
from sim2act.natural_trial_api import StageApprovalRequest, StageReviewRequest, original_contract


@pytest.mark.parametrize("scenario", ["happy", "lost", "bad", "stale", "revoke", "late", "storage"])
def test_delivered_stage_controls_use_original_intent_without_model_authority(
    prepared_data,  # noqa: F811
    tmp_path,
    scenario,
):
    data, choices = prepared_data
    store, _, client, user, pid = data[:5]
    ids = {k: "run_" + v * 32 for k, v in [("source", "1"), ("cold", "2"), ("generate", "3")]}
    shape = recipe("ordered")
    stored = {}
    authority_revision = [1]
    info = tmp_path / "info.json"
    cold_card = client.get("/api/goal-cards/" + choices["bindings"][1]["card_id"]).json()
    cold_resource = client.get("/api/resources/" + cold_card["content"]["resource_refs"][0]).json()
    info.write_text(
        json.dumps(
            dict(
                project=pid,
                source=choices["bindings"][0]["card_id"],
                cold=choices["bindings"][1]["card_id"],
                sourceRun=ids["source"],
                coldRun=ids["cold"],
                sourceText=gate.MaterialGoal.model_fields
                and data[2].get("/api/resources/" + data[5]).json()["content"],
                coldText=cold_resource["content"],
                scenario=scenario,
                output=str(tmp_path / "result.json"),
            )
        )
    )
    process = subprocess.Popen(
        ["node", "tests/natural_trial_stage_ui.cjs", str(info)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "NODE_PATH": "/workspace/scratch/sim2act-ui-deps-20261029/node_modules"},
    )
    records = []
    last_contract = None

    def response(request):
        nonlocal last_contract
        path = request.get("path", "")
        body = request.get("body")
        stage_route = (
            path.endswith("/stage-review") or path.endswith("/stage-approval") or "/stages/" in path
        )
        if stage_route:
            key = re.search("/natural-trials/([^/]+)", path)[1]
            # Actual original server authentication/root-resource checks before wire data.
            auth = client.get(
                f"/api/projects/{pid}/natural-trials/{key}/approvals/"
                + last_contract.stage_keys.generate
                + "_approval"
            )
            if auth.status_code != 200:
                return auth.status_code, auth.text
            c = original_contract(store, user, pid, key)
            last_contract = c
            if path.endswith("/stage-review"):
                parsed = StageReviewRequest.model_validate(body)
                stage = parsed.stage
                assert parsed.contract == c and parsed.run_id == ids[stage]
                a = gate.StageAuthorityV2(
                    contract_fingerprint=fingerprint(c.model_dump()),
                    stage=stage,
                    run_id=ids[stage],
                    accepted_fingerprint="a" * 64,
                    app_run_id="iapprun_" + "4" * 32,
                    instance_id="iinstance_" + "5" * 32,
                    instance_revision=authority_revision[0],
                    runtime_id=c.runtime_id,
                    app_id="app_" + "6" * 32,
                    candidate_fingerprint="b" * 64,
                    recipe_fingerprint=fingerprint(shape),
                    release_id="irelease_" + "7" * 32,
                    release_fingerprint="c" * 64,
                    generation_run_id=ids["generate"],
                    generation_candidate_fingerprint="d" * 64,
                    target_goal_fingerprint=c.bindings[stage == "cold"].goal_fingerprint,
                    authorization_fingerprint=c.authorization_fingerprint,
                    predecessor_run_id=ids["generate" if stage == "source" else "source"],
                    predecessor_created_at=c.prepared_at + 1,
                    stage_approval_expires_at=min(c.prepared_at + 1 + 900, c.execution_expires_at),
                )
                return 200, json.dumps(
                    dict(
                        authority=a.model_dump(),
                        authority_fingerprint=fingerprint(a.model_dump()),
                        live_allowed=False,
                        actual_model_requests=0,
                        fee_status="NOT_VERIFIED",
                    )
                )
            if path.endswith("/stage-approval"):
                parsed = StageApprovalRequest.model_validate(body)
                a = parsed.approval.authority
                assert parsed.contract == c and a.instance_revision == authority_revision[0]
                # Simulation map only: NO gate.approve_stage / PHASE inserts or fake Grant.
                stored[(a.stage, parsed.approval.request_key)] = parsed.approval.model_dump()
                return 200, json.dumps(
                    dict(
                        status="EXACT_STAGE_BOUND_LIVE_BLOCKED",
                        authority=a.model_dump(),
                        authority_fingerprint=parsed.approval.expected_authority_fingerprint,
                        live_allowed=False,
                        actual_model_requests=0,
                        formal_publication_enabled=False,
                    )
                )
            stage, key = path.split("/stages/")[1].split("/")
            value = stored[(stage, key)]
            return 200, json.dumps(
                dict(
                    status="HISTORICAL_STAGE_BINDING_LIVE_BLOCKED",
                    request=value,
                    authority_fingerprint=value["expected_authority_fingerprint"],
                    live_allowed=False,
                    dispatch_authorized=False,
                    new_model_requests=0,
                    fee_status="NOT_VERIFIED",
                )
            )
        if path == f"/api/projects/{pid}/runs?metadata_only=true":
            return 200, json.dumps([dict(id=ids[k], status="QUEUED") for k in ("source", "cold")])
        if path == "/api/apps/app_" + "6" * 32:
            return 200, json.dumps(
                dict(
                    id="app_" + "6" * 32,
                    name="受控界面配方",
                    fingerprint="b" * 64,
                    candidate=dict(spec_recipe=shape),
                )
            )
        reply = client.request(request["method"], path, json=body, headers=request.get("headers"))
        if path.endswith("/preparation") and reply.status_code == 200:
            last_contract = gate.parse_contract(reply.json()["contract"])
        return reply.status_code, reply.text

    try:
        for line in process.stdout:
            request = json.loads(line)
            if request.get("done"):
                break
            if request.get("command") == "change-version":
                authority_revision[0] += 1
                status, text = 200, "{}"
            elif request.get("command") == "revoke-read":
                with store.tx() as c:
                    c.execute(
                        update(grants).where(grants.c.resource_id == data[5]).values(revoked=True)
                    )
                status, text = 200, "{}"
            else:
                status, text = response(request)
            records.append(dict(request=request, status=status))
            process.stdin.write(
                json.dumps(
                    dict(
                        id=request["id"], status=status, text=text, content_type="application/json"
                    )
                )
                + "\n"
            )
            process.stdin.flush()
        errors = process.stderr.read()
        code = process.wait(timeout=20)
        (tmp_path / "wire.log").write_text(errors)
        (tmp_path / "requests.json").write_text(json.dumps(records, indent=2))
        assert code == 0, errors
        proof = json.loads((tmp_path / "result.json").read_text())
        assert proof["status"] == "PASS"
        with store.tx() as c:
            assert not c.execute(
                select(delivery_graph_requests.c.app_id).where(
                    delivery_graph_requests.c.kind.in_([gate.PHASE, gate.PHASE + "_seal"])
                )
            ).first()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
