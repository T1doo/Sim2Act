"""Explicit ordinary correction; synthetic reasons, users and models only."""

import json

from test_ordinary_goal_md import execute
from test_ordinary_owner_review import decision, prepare, review


def rejected(env):
    goal, source, receipt, model, result = execute(env)
    rid = receipt["run_id"]
    prepare(env, rid)
    body = decision(env, rid, accept=False)
    body["choices"][0]["reason"] = "SIMULATED: retain Beta exception, do not grant access <script>unsafe()</script>"
    response = review(env, rid, "post", body)
    assert response.status_code == 201, response.text
    return goal, source, rid, result, response.json()["record"]


def preview(env, rid):
    response = env[2].get(f"/api/runs/{rid}/correction-preview")
    assert response.status_code == 200, response.text
    return response.json()


def correction_body(value, key="explicit-correction"):
    return dict(expected_preview_fingerprint=value["preview_fingerprint"],
        declaration_id=value["feedback"]["declaration_id"],
        declaration_fingerprint=value["feedback"]["declaration_fingerprint"],
        expected_sequence=value["feedback"]["declaration_sequence"],
        request_key=key, consent="RUN_NEW_CORRECTION_KEEP_GOAL_CRITERIA_AND_HISTORY")


def test_rejected_ordinary_result_previews_exact_new_request_without_mutation(env, tmp_path):
    goal, source, rid, result, declaration = rejected(env)
    value = preview(env, rid)
    assert value["parent_run_id"] == rid
    assert value["feedback"]["declaration_id"] == declaration["id"]
    assert value["feedback"]["issues"][0]["reason"].startswith("SIMULATED: retain Beta")
    assert value["source_goal"]["version"] == goal["version"]
    assert value["source_goal"]["snapshot"]["content"]["resource_refs"] == [source]
    assert env[2].get(f"/api/runs/{rid}").json() == result
    (tmp_path / "preview.json").write_text(json.dumps(value, ensure_ascii=False, indent=2))
