"""Modified saved recipe, unseen target and independent simulated owner."""

import copy
import hashlib
import json

from fastapi.testclient import TestClient
from test_natural_spec_apps import COLD, SOURCE, enqueue, material, ready, setup, transport
from test_natural_spec_owner_acceptance import decision, preview, state
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD
from test_spec_app_operations import snapshot

from sim2act import natural_logic_patches as logic
from sim2act import pb_natural_uses as use
from sim2act.api import create_app
from sim2act.db import Store, fingerprint


def version(data, app, release, inst):
    client = data[2]
    r = client.post(
        f"/api/projects/{data[4]}/apps/{app['id']}/delivery-graph/derive",
        json=dict(request_key="use-graph", expected_candidate_fingerprint=app["fingerprint"]),
    )
    assert r.status_code == 201, r.text
    route = f"/api/internal/instances/{inst['id']}/logic-patches"
    consume = "prior_items" not in app["candidate"]["spec_recipe"]["steps"][2]["inputs"]
    r = client.post(
        route + "/previews",
        json=dict(
            request_key="use-logic",
            expected_revision=inst["revision"],
            expected_release_fingerprint=release["fingerprint"],
            expected_graph_fingerprint=r.json()["graph_fingerprint"],
            consume_prior_feedback=consume,
        ),
    )
    assert r.status_code == 201, r.text
    checked = r.json()
    r = client.post(
        route + "/checks",
        json=dict(
            request_key="use-logic",
            expected_preview_fingerprint=checked["preview_fingerprint"],
            consent=logic.CHECK_CONSENT,
        ),
    )
    assert r.status_code == 202, r.text
    drive_to_success(
        data,
        r.json()["run_id"],
        transport([], SOURCE if use.saved_family(app["candidate"]) == use.PA else COLD),
    )
    r = client.get(route + "/checks/use-logic")
    assert r.status_code == 200, r.text
    r = client.post(
        route + "/version-approvals",
        json=dict(
            request_key="use-logic",
            expected_check_fingerprint=r.json()["check_fingerprint"],
            consent=logic.VERSION_CONSENT,
        ),
    )
    assert r.status_code == 201, r.text
    a = r.json()
    r = client.post(
        "/api/internal/approvals/" + a["id"] + "/commit", json=dict(fingerprint=a["fingerprint"])
    )
    assert r.status_code == 200, r.text
    new = r.json()
    r = client.post(
        "/api/internal/releases/" + new["id"] + "/instances",
        json=dict(
            expected_release_fingerprint=new["fingerprint"], request_key="third-use-instance"
        ),
    )
    assert r.status_code == 201, r.text
    return new, r.json(), checked


def pa_saved(env):
    data = setup(env)
    _, aid, release, inst, _ = ready(data, "parallel")
    app = data[2].get("/api/apps/" + aid).json()
    old = enqueue(data, release, inst)
    drive_to_success(data, old, transport([]))
    path = f"/api/internal/instances/{inst['id']}/runs/{old}/spec-owner-review"
    reviewed, _ = preview(data, path)
    r = data[2].post(path + "-requests", json=decision(reviewed))
    assert r.status_code == 201, r.text
    rid, goal = material(data[2], data[4], COLD, "Second old-version material")
    body = dict(
        expected_revision=inst["revision"],
        expected_release_fingerprint=release["fingerprint"],
        expected_app_fingerprint=app["fingerprint"],
        expected_recipe_fingerprint=fingerprint(app["candidate"]["spec_recipe"]),
        resource_id=rid,
        card_id=goal["id"],
        expected_goal_version=goal["version"],
        expected_goal_fingerprint=goal["fingerprint"],
        expected_source_hash=hashlib.sha256(COLD.encode()).hexdigest(),
        request_key="old-second",
    )
    route = f"/api/internal/instances/{inst['id']}"
    r = data[2].post(route + "/pa-use-reviews", json=body)
    assert r.status_code == 200, r.text
    r = data[2].post(
        route + "/pa-use-runs",
        json=dict(
            review=body,
            expected_review_fingerprint=r.json()["review_fingerprint"],
            consent=use.PA_CONSENT,
        ),
    )
    assert r.status_code == 202, r.text
    drive_to_success(data, r.json()["run_id"], transport([], COLD))
    inst = data[2].get(route).json()
    return data, app, release, inst


def third(data, app, old, inst, new, ni, checked, tmp_path, family):
    resource, goal = material(data[2], data[4], THIRD, "Third unseen modified-version Goal")
    route = f"/api/internal/instances/{ni['id']}/{family.route}"
    body = dict(
        expected_revision=ni["revision"],
        expected_release_fingerprint=new["fingerprint"],
        expected_app_fingerprint=app["fingerprint"],
        expected_recipe_fingerprint=checked["new_recipe_fingerprint"],
        resource_id=resource,
        card_id=goal["id"],
        expected_goal_version=goal["version"],
        expected_goal_fingerprint=goal["fingerprint"],
        expected_source_hash=hashlib.sha256(THIRD.encode()).hexdigest(),
        request_key="third-modified-logic",
    )
    before = snapshot(data[0])
    r = data[2].post(route + "-reviews", json=body)
    assert r.status_code == 200, r.text
    assert snapshot(data[0]) == before
    review = r.json()
    assert (
        review["effective_candidate"]["spec_recipe"]
        == checked["effective_candidate"]["spec_recipe"]
    )
    assert (
        review["effective_candidate"]["spec_recipe"]
        != new["snapshot"]["draft"]["candidate"]["spec_recipe"]
    )
    assert (
        review["effective_candidate"]["logic_revision"]
        == checked["effective_candidate"]["logic_revision"]
    )
    assert review["saved_logic_source"]["origin"] == new["snapshot"]["natural_logic_source"]
    assert not any(
        k in review["effective_candidate"]
        for k in ("goal_application", "spec_binding", "spec_task")
    )
    bad = copy.deepcopy(body)
    bad["expected_recipe_fingerprint"] = fingerprint(app["candidate"]["spec_recipe"])
    r = data[2].post(route + "-reviews", json=bad)
    assert r.status_code == 409, r.text
    assert snapshot(data[0]) == before
    commit = dict(
        review=body,
        expected_review_fingerprint=review["review_fingerprint"],
        consent=family.consent,
    )
    r = data[2].post(route + "-runs", json=commit)
    assert r.status_code == 202, r.text
    run = r.json()["run_id"]
    cold = Store(data[1].database_url, test_only=True)
    try:
        client = TestClient(create_app(cold, data[1]))
        client.headers["Authorization"] = "Bearer synthetic-test-A"
        current = (cold, data[1], client, *data[3:])
        r = client.get(route + "-requests/" + body["request_key"])
        assert r.status_code == 200, r.text
        assert r.json()["reviewed"] == review
        sent = []
        drive_to_success(current, run, transport(sent, THIRD))
        r = client.get("/api/internal/app-run-jobs/" + run + "/spec-artifact")
        assert r.status_code == 200, r.text
        result = json.loads(r.json()["resource"]["content"])
        assert result["source_content"] == THIRD and result["source"]["resource_id"] == resource
        assert (
            result["human_unresolved"] == goal["content"]["unresolved"]
            and result["owner_acceptance"] == "PENDING"
        )
        assert len(sent) == 2 and SOURCE not in json.dumps(sent) and COLD not in json.dumps(sent)
        inputs = json.loads(sent[1]["messages"][1]["content"])["current_inputs"]
        assert ("prior_items" in inputs) == (
            "prior_items" in checked["effective_candidate"]["spec_recipe"]["steps"][2]["inputs"]
        )
        after = snapshot(cold)
        for table in (
            "app_drafts",
            "internal_releases",
            "goal_cards",
            "goal_card_versions",
            "natural_owner_records",
            "natural_owner_seals",
        ):
            assert before[table] == after[table], table
        assert all(
            row in after["internal_instance_data"] for row in before["internal_instance_data"]
        )
        path = f"/api/internal/instances/{ni['id']}/runs/{run}/spec-owner-review"
        s = state(current, path)
        assert s["latest"] is None and s["current"]["source_goal"]["card_id"] == goal["id"]
        reviewed, _ = preview(current, path)
        r = client.post(path + "-requests", json=decision(reviewed))
        assert r.status_code == 201, r.text
        assert (
            state(current, path, "decision")["owner_acceptance"] == "ACCEPTED"
            and result["owner_acceptance"] == "PENDING"
        )
        (tmp_path / "third-proof.json").write_text(
            json.dumps(
                dict(
                    review=review,
                    result=result,
                    wire=sent,
                    simulated_owner=r.json(),
                    real_model_requests=0,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        client.close()
    finally:
        cold.engine.dispose()


def test_pa_modified_release_third_material_cold_worker_and_fresh_owner(env, tmp_path):
    data, app, old, inst = pa_saved(env)
    new, ni, checked = version(data, app, old, inst)
    third(data, app, old, inst, new, ni, checked, tmp_path, use.PA)


def test_pb_modified_release_third_material_cold_worker_and_fresh_owner(env, tmp_path):
    from test_pb_natural_specs import prepare, preview_commit

    prepared = prepare(env, style="sequential", edit=False)
    data, _, _, _, _, path, _, _ = prepared
    _, commit = preview_commit(prepared)
    r = data[2].post(path + "/extractions", json=commit)
    assert r.status_code == 201, r.text
    app = data[2].get("/api/apps/" + r.json()["id"]).json()
    old, inst = instance(data, app["id"])
    run = enqueue(data, old, inst)
    drive_to_success(data, run, transport([], COLD))
    inst = data[2].get("/api/internal/instances/" + inst["id"]).json()
    new, ni, checked = version(data, app, old, inst)
    third(data, app, old, inst, new, ni, checked, tmp_path, use.PB)
