"""Original-contract boundary: a text VIEW change is still PROJECT scoped.

These are synthetic original offline fixtures, not a Report production result
or completion of the proposed presentation binding feature.
"""

import copy

from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import path, snapshot
from test_report_manifest_apps import promoted


def test_existing_report_view_change_cannot_claim_target_only_completion(env, tmp_path):
    bounded = bounded_env.__wrapped__(env)
    app, parent, _, _, wires = promoted(bounded, tmp_path)
    url = path(env, app["id"])
    made = env[2].post(url + "/derive", json={
        "expected_candidate_fingerprint": app["fingerprint"],
        "request_key": "report-text-boundary",
    })
    assert made.status_code == 201, made.text
    baseline = made.json()
    before = snapshot(env)
    node = next(n for n in baseline["graph"]["nodes"] if n["kind"] == "VIEW")
    assert node["definition"] == {"component_ref": "text", "output_field": "decision"}
    original = copy.deepcopy(baseline)
    body = {
        "expected_graph_fingerprint": baseline["graph_fingerprint"],
        "request_key": "decision-to-explanation-scope",
        "changes": [{
            "node_id": node["id"],
            "expected_revision": node["revision"],
            "expected_content_fingerprint": node["content_fingerprint"],
        }],
    }
    reply = env[2].post(url + "/plans", json=body)
    assert reply.status_code == 201, reply.text
    result = reply.json()
    assert result["receipt"]["revalidation_scope"] == "PROJECT"
    assert result["receipt"]["patch_executed"] is False
    assert result["receipt"]["publishable"] is False
    assert result["scope_expansion"]["status"] == "BLOCKED_PARTIAL"
    assert parent["id"] in {item["app_id"] for item in result["scope_expansion"]["omissions"]}
    assert result["scope_jobs"] and all(job["status"] == "PENDING" for job in result["scope_jobs"])
    assert baseline == original
    after = snapshot(env)
    assert all(before[key] == after[key] for key in before if not key.startswith("delivery_graph_"))
    assert env[2].get("/api/apps/" + app["id"]).json()["candidate"] == app["candidate"]
    accepted = snapshot(env)
    replay = env[2].post(url + "/plans", json=body)
    assert replay.status_code == 201 and replay.json()["cached"] is True
    assert snapshot(env) == accepted
    assert len(wires) == 3  # Original source/extraction MockTransport only; no real provider.
