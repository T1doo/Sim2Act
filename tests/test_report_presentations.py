"""Synthetic archived-result overlays; no actual Report semantic acceptance."""

import copy

import pytest
from sqlalchemy import select, update
from test_conditional_apps import independent_report
from test_conditional_run_bindings import env as bounded_env
from test_conditional_run_bindings import envelope, facts, get, work
from test_delivery_graph_apps import path, snapshot
from test_report_manifest_apps import preview_path, promoted

from sim2act.db import app_drafts, fingerprint, grants, resources
from sim2act.db import delivery_graph_requests as requests


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def prepared(env, tmp_path, *, peer=False):
    app, _, _, _, wires = promoted(env, tmp_path)
    output = independent_report(("TRUE", "FALSE", "FALSE"), "ALLOW", ["submit_claim_and_receipt"])
    output["explanation"] = '<script>window.reportExecuted=true</script> 合成解释'
    accepted = env[2].post(preview_path(env, app["id"]), json={
        "expected_candidate_fingerprint": app["fingerprint"], "input": facts(500),
        "request_key": "archived-result",
    })
    assert accepted.status_code == 202, accepted.text
    work(env, tmp_path, [envelope(output)], wires)
    run = get(env, accepted.json()["run_id"])
    if peer:
        from test_internal_lifecycle import setup_draft
        with env[0].tx() as c:
            csv_id = c.execute(select(resources.c.id).where(resources.c.project_id == env[5], resources.c.format == "csv")).scalar_one()
        peer_id, peer_fp = setup_draft((*env[:6], csv_id))
        response = env[2].post(path(env, peer_id) + "/derive", json={
            "expected_candidate_fingerprint": peer_fp, "request_key": "peer-anchor"})
        assert response.status_code == 201, response.text
    url = path(env, app["id"])
    response = env[2].post(url + "/derive", json={
        "expected_candidate_fingerprint": app["fingerprint"], "request_key": "presentation-anchor",
    })
    assert response.status_code == 201, response.text
    graph = response.json()
    slot = next(n for n in graph["graph"]["nodes"] if n["kind"] == "VIEW")
    plan = env[2].post(url + "/plans", json={
        "expected_graph_fingerprint": graph["graph_fingerprint"], "request_key": "presentation-plan",
        "changes": [{"node_id": slot["id"], "expected_revision": slot["revision"],
                     "expected_content_fingerprint": slot["content_fingerprint"]}],
    })
    assert plan.status_code == 201, plan.text
    body = dict(expected_candidate_fingerprint=app["fingerprint"],
                expected_graph_fingerprint=graph["graph_fingerprint"], plan_key="presentation-plan",
                expected_plan_fingerprint=plan.json()["native_outer_fingerprint"],
                run_id=run["run_id"], expected_run_version=run["version"],
                expected_run_fence=run["fence"], expected_result_fingerprint=run["result_fingerprint"],
                view={"component_ref": "text", "output_field": "explanation"}, request_key="text-version")
    return app, graph, url + "/report-presentations", body, output, wires


def test_new_immutable_presentation_and_actual_archived_readback_preserve_canonical(env, tmp_path):
    app, graph, url, body, output, wires = prepared(env, tmp_path)
    before = snapshot(env)
    reply = env[2].post(url, json=body)
    assert reply.status_code == 201, reply.text
    patch = reply.json()
    slot = next(n for n in graph["graph"]["nodes"] if n["kind"] == "VIEW")
    assert patch["definition"]["slot_id"] == slot["id"]
    assert patch["definition"]["slot_key"] == slot["key"]
    assert patch["preserved_objects"] == graph["graph"]["nodes"]
    assert patch["preserved_edges"] == graph["graph"]["edges"]
    assert patch["impact_plan"]["receipt"]["revalidation_scope"] == "PROJECT"
    assert patch["project_revalidation_status"] == "BLOCKED_PARTIAL"
    assert patch["canonical_patch_executed"] is False
    check_body = dict(expected_patch_fingerprint=patch["patch_fingerprint"], request_key="text-check")
    checked = env[2].post(url + "/text-version/checks", json=check_body)
    assert checked.status_code == 201, checked.text
    result = checked.json()
    assert result["baseline_text"] == "ALLOW" and result["text"] == output["explanation"]
    assert result["display_readback_status"] == "PASS"
    assert result["actual_material_verification"] == "PENDING"
    assert result["overall_run_acceptance"] == "NOT_ACCEPTED"
    assert result["formal_publication_enabled"] is False
    after = snapshot(env)
    assert all(before[key] == after[key] for key in before if key != "delivery_graph_requests")
    # Canonical source, all graph definitions/IDs/revisions, output/schema and histories remain intact.
    assert env[2].get("/api/apps/" + app["id"]).json()["candidate"] == app["candidate"]
    assert env[2].post(url, json=body).json()["cached"] is True
    assert env[2].post(url + "/text-version/checks", json=check_body).json()["cached"] is True
    assert snapshot(env) == after
    reopened = env[2].get(url)
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["items"][0]["checks"][0]["check_fingerprint"] == result["check_fingerprint"]
    assert len(wires) == 4  # Original synthetic source/extraction/report transport only.


@pytest.mark.parametrize("damage", ["component", "unknown_output", "html", "expression", "version_bool", "result", "plan", "run", "candidate"])
def test_closed_definition_and_exact_versions_reject_without_any_write(env, tmp_path, damage):
    _, _, url, body, _, _ = prepared(env, tmp_path)
    bad = copy.deepcopy(body)
    if damage == "component":
        bad["view"]["component_ref"] = "chart"
    elif damage == "unknown_output":
        bad["view"]["output_field"] = "undeclared"
    elif damage in {"html", "expression"}:
        bad["view"][damage] = "<script>alert(1)</script>"
    elif damage == "version_bool":
        bad["expected_run_version"] = True
    elif damage in {"result", "plan", "candidate"}:
        field = {"result": "expected_result_fingerprint", "plan": "expected_plan_fingerprint", "candidate": "expected_candidate_fingerprint"}[damage]
        bad[field] = "0" * 64
    else:
        bad["run_id"] = "run_" + "0" * 32
    before = snapshot(env)
    reply = env[2].post(url, json=bad)
    assert reply.status_code in {400, 403, 409, 422}, reply.text
    assert snapshot(env) == before


@pytest.mark.parametrize("damage", ["source", "revoke", "seal", "candidate", "check_version", "same_key"])
def test_saved_overlay_invalidates_and_cannot_forge_readback(env, tmp_path, damage):
    app, _, url, body, _, _ = prepared(env, tmp_path)
    reply = env[2].post(url, json=body)
    assert reply.status_code == 201, reply.text
    patch = reply.json()
    confirm = dict(expected_patch_fingerprint=patch["patch_fingerprint"], request_key="check")
    if damage == "check_version":
        confirm["expected_patch_fingerprint"] = "0" * 64
    elif damage == "same_key":
        changed = copy.deepcopy(body)
        changed["expected_run_version"] += 1
        before = snapshot(env)
        assert env[2].post(url, json=changed).status_code == 409
        assert snapshot(env) == before
        return
    else:
        with env[0].tx() as c:
            if damage == "source":
                rid = app["candidate"]["report_proof"]["target_resource_id"]
                c.execute(update(resources).where(resources.c.id == rid).values(content="changed", hash="0" * 64))
            elif damage == "revoke":
                c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
            elif damage == "candidate":
                changed = copy.deepcopy(app["candidate"])
                changed["manifest"]["views"][0]["output_field"] = "explanation"
                c.execute(update(app_drafts).where(app_drafts.c.id == app["id"]).values(candidate=changed, fingerprint=fingerprint(changed)))
            else:
                row = c.execute(select(requests).where(requests.c.app_id == app["id"], requests.c.kind == "report_presentation")).mappings().one()
                changed = copy.deepcopy(row["snapshot"])
                changed["response"]["definition"]["view"]["output_field"] = "decision"
                c.execute(update(requests).where(requests.c.app_id == app["id"], requests.c.kind == "report_presentation").values(snapshot=changed, fingerprint=fingerprint(changed)))
    before = snapshot(env)
    response = env[2].post(url + "/text-version/checks", json=confirm)
    assert response.status_code in {400, 403, 409}, response.text
    assert response.json()["error"]["code"] in {"VERIFICATION_FAILED", "PERMISSION_DENIED", "GRANT_REVOKED", "VERSION_CONFLICT"}
    assert snapshot(env) == before
    if damage != "check_version":
        assert env[2].get(url).status_code in {400, 403, 409}


def test_manual_view_lock_blocks_saved_overlay_without_writes(env, tmp_path):
    from test_internal_lifecycle import limits

    from sim2act.delivery_graph_apps import set_lock

    app, graph, url, body, _, _ = prepared(env, tmp_path)
    patch = env[2].post(url, json=body).json()
    slot = next(n for n in graph["graph"]["nodes"] if n["kind"] == "VIEW")
    set_lock(env[0], env[3], env[5], app["id"], dict(
        expected_graph_fingerprint=graph["graph_fingerprint"], request_key="manual-view-lock",
        change=dict(node_id=slot["id"], expected_revision=slot["revision"],
                    expected_content_fingerprint=slot["content_fingerprint"]), locked=True), limits(env))
    before = snapshot(env)
    assert env[2].post(url + "/text-version/checks", json=dict(
        expected_patch_fingerprint=patch["patch_fingerprint"], request_key="locked-check")).status_code == 409
    assert env[2].get(url).status_code == 409
    assert snapshot(env) == before


def test_project_membership_change_invalidates_original_plan_and_presentation(env, tmp_path):
    app, _, url, body, _, _ = prepared(env, tmp_path)
    patch = env[2].post(url, json=body).json()
    # A new same-project candidate with no graph is an additional conservative
    # scope omission, not something a target-only presentation check can erase.
    with env[0].tx() as c:
        row = dict(c.execute(select(app_drafts).where(app_drafts.c.id == app["id"])).mappings().one())
        row["id"] = "app_" + "1" * 32
        from sqlalchemy import insert
        c.execute(insert(app_drafts).values(**row))
    before = snapshot(env)
    response = env[2].post(url + "/text-version/checks", json=dict(
        expected_patch_fingerprint=patch["patch_fingerprint"], request_key="membership-check"))
    assert response.status_code == 409, response.text
    assert env[2].get(url).status_code == 409
    assert snapshot(env) == before


@pytest.mark.parametrize("damage", ["peer_revoke", "peer_lock", "peer_graph", "definition_seals", "check_seals", "run_fence", "result"])
def test_peer_bindings_and_coordinated_receipt_damage_fail_closed(env, tmp_path, damage):
    from test_internal_lifecycle import limits

    from sim2act.db import runs
    from sim2act.delivery_graph_apps import DeriveInput, derive, set_lock

    app, _, url, body, _, _ = prepared(env, tmp_path, peer=True)
    patch = env[2].post(url, json=body).json()
    confirm = dict(expected_patch_fingerprint=patch["patch_fingerprint"], request_key="sealed-check")
    assert env[2].post(url + "/text-version/checks", json=confirm).status_code == 201
    with env[0].tx() as c:
        rows = c.execute(select(app_drafts).where(app_drafts.c.project_id == env[5])).mappings().all()
        peer = next(row for row in rows if row["candidate"].get("actions", [{}])[0].get("executor", {}).get("ref") == "data.aggregate_csv")
        if damage == "peer_revoke":
            rid = peer["candidate"]["manifest"]["data_bindings"][0]["resource_ref"]
            c.execute(update(grants).where(grants.c.project_id == env[5], grants.c.resource_id == rid).values(revoked=True))
        elif damage.endswith("seals"):
            kind = "report_presentation" if damage == "definition_seals" else "report_presentation_check"
            for row in c.execute(select(requests).where(requests.c.app_id == app["id"], requests.c.kind.in_([kind, kind + "_seal"]))).mappings().all():
                changed = copy.deepcopy(row["snapshot"])
                if damage == "definition_seals":
                    changed["response"]["definition"]["presentation_revision"] += 1
                else:
                    changed["response"]["text"] = "forged explanation"
                c.execute(update(requests).where(requests.c.app_id == app["id"], requests.c.kind == row["kind"], requests.c.request_key == row["request_key"]).values(snapshot=changed, fingerprint=fingerprint(changed)))
        elif damage == "run_fence":
            c.execute(update(runs).where(runs.c.id == body["run_id"]).values(fence=body["expected_run_fence"] + 1))
        elif damage == "result":
            c.execute(update(runs).where(runs.c.id == body["run_id"]).values(result={"forged": True}))
    if damage in {"peer_lock", "peer_graph"}:
        peer_graph = env[2].get(path(env, peer["id"])).json()
        slot = next(n for n in peer_graph["graph"]["nodes"] if n["kind"] == "VIEW")
        set_lock(env[0], env[3], env[5], peer["id"], dict(
            expected_graph_fingerprint=peer_graph["graph_fingerprint"], request_key="peer-manual-lock",
            change=dict(node_id=slot["id"], expected_revision=slot["revision"],
                        expected_content_fingerprint=slot["content_fingerprint"]), locked=True), limits(env))
        if damage == "peer_graph":
            derive(env[0], env[3], env[5], peer["id"], DeriveInput(
                expected_candidate_fingerprint=peer["fingerprint"], request_key="peer-new-anchor"), limits(env))
    before = snapshot(env)
    restored = env[2].post(url, json=body)
    if damage == "check_seals":
        # An intact definition remains readable; it returns no damaged check.
        assert restored.status_code == 201 and restored.json()["cached"] is True
    else:
        assert restored.status_code in {400, 403, 409}, restored.text
    for response in (env[2].post(url + "/text-version/checks", json=confirm), env[2].get(url)):
        assert response.status_code in {400, 403, 409}, response.text
    assert snapshot(env) == before
