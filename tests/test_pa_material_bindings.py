"""P-A provider graph typed binding, actual new-material cold NoModel computation."""

import copy
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from test_goal_text_applications import confirm, release_instance, run_input
from test_pa_generation_provider import accepted, approved, configured, provider

from sim2act import pa_material_bindings as binding
from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    fingerprint,
    goal_application_candidates,
    grants,
    internal_instance_data,
    principals,
    task_extractions,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker

NEW_CONTENT = "Gamma fresh material\nDelta independent target\nGamma not an old report\n"


def source_and_target(env, monkeypatch):
    data, clock = configured(env, monkeypatch)
    scope, grant, _ = approved(data)
    rid = accepted(data, grant["activation"])
    transport, sent = provider(data, clock)
    assert Worker(data[0], data[1], goal_planner_transport=transport).once()
    result = data[2].get(f"/api/runs/{rid}").json()
    original, _ = confirm(data, rid, result)
    response = data[2].post(f"/api/projects/{data[4]}/resources", json=dict(name="fresh.md", format="md", content=NEW_CONTENT))
    assert response.status_code == 201, response.text
    resource = response.json()["id"]
    goal = copy.deepcopy(data[6]["content"])
    goal.update(title="Explicit own new-material goal", goal="引用本份新材料的完整匹配行；语义待人核验", resource_refs=[resource])
    response = data[2].post(f"/api/projects/{data[4]}/goal-cards", json=goal)
    assert response.status_code == 201, response.text
    card = response.json()
    path = f"/api/projects/{data[4]}/pa-model-candidates/{rid}"
    response = data[2].get(path + "/material-binding-options", params=dict(card_id=card["id"]))
    assert response.status_code == 200, response.text
    options = response.json()
    body = dict(card_id=card["id"], expected_goal_version=options["target_goal"]["version"],
        expected_goal_fingerprint=options["target_goal"]["fingerprint"], expected_source_hash=options["source_hash"],
        expected_model_candidate_fingerprint=options["model_candidate_fingerprint"],
        expected_graph_fingerprint=options["graph_fingerprint"], name="P-A new material literal report",
        consent=binding.CONSENT, request_key="explicit-new-material")
    return data, scope, sent, rid, original, resource, options, path, body


def rows(store):
    with store.tx() as c:
        return {t.name: [dict(r) for r in c.execute(select(t)).mappings()]
            for t in (principals, grants, app_drafts, task_extractions, goal_application_candidates, attempts)}


def test_model_graph_preserved_and_new_material_cold_no_model_result(env, monkeypatch):
    data, scope, sent, rid, original, resource, options, path, body = source_and_target(env, monkeypatch)
    before = rows(data[0])
    response = data[2].post(path + "/material-bindings", json=body)
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved["namespace"] == binding.VERSION and saved["id"] != original
    assert saved["model_requests"] == 0 and saved["owner_acceptance"] == "PENDING" and saved["formal_publication_enabled"] is False
    recovered = data[2].get(path + "/material-binding-requests/" + body["request_key"])
    assert recovered.status_code == 200 and recovered.json()["id"] == saved["id"]
    with data[0].tx() as c:
        original_draft = c.execute(select(app_drafts).where(app_drafts.c.id == original)).mappings().one()
        target_draft = c.execute(select(app_drafts).where(app_drafts.c.id == saved["id"])).mappings().one()
        raw = {k: original_draft["candidate"][k] for k in ("manifest", "actions", "source_hash", "goal")}
        new = binding.executable(target_draft["candidate"])
        assert fingerprint(binding.slots(raw)) == fingerprint(binding.slots(new)) == options["graph_fingerprint"]
        assert new["manifest"]["workflow"] == raw["manifest"]["workflow"]
        assert new["manifest"]["origin"] == "goal" and new["manifest"]["source_run_ref"] is None
        assert new["manifest"]["workflow"][0]["step_id"] == "provider_chosen_literal_report"
        assert new["goal"] == options["target_goal"]["snapshot"]["content"]
        assert new["goal"] != raw["goal"] and new["source_hash"] != raw["source_hash"]
        fresh_grants = c.execute(select(grants).where(grants.c.principal_id == saved["runtime_id"])).mappings().all()
        assert len(fresh_grants) == 1 and fresh_grants[0]["resource_id"] == resource and fresh_grants[0]["tool_ref"] == "resource.read"
    after = rows(data[0])
    assert before["attempts"] == after["attempts"] and before["goal_application_candidates"] == after["goal_application_candidates"]
    cold = Store(data[1].database_url, test_only=True)
    settings = replace(data[1], goal_planner_provider="disabled", application_generation_activation_enabled=False,
        application_generation_live_id="", live_enabled=False, token="")
    client = TestClient(create_app(cold, settings))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    cold_data = (cold, settings, client, *data[3:])
    release, instance = release_instance(cold_data, saved["id"])
    result = run_input(cold_data, release, instance, {"term": "Gamma"}, "new-material-cold-input")
    assert result["status"] == "SUCCEEDED"
    assert result["result"]["resource_id"] == resource and result["result"]["source_hash"] == body["expected_source_hash"]
    assert result["result"]["citations"] == [
        dict(start_line=1, end_line=1, quote="Gamma fresh material"),
        dict(start_line=3, end_line=3, quote="Gamma not an old report")]
    empty = run_input(cold_data, release, instance, {"term": "Beta"}, "old-source-term-new-material")
    assert empty["status"] == "SUCCEEDED" and empty["result"]["citations"] == []
    assert len(sent) == 2, "new material binding and cold results consume no model slot"
    assert rows(cold)["attempts"] == before["attempts"]
    client.close()
    cold.engine.dispose()


@pytest.mark.parametrize("change", ["goal", "source", "graph", "model", "target-revoked", "origin-revoked"])
def test_binding_exact_preview_or_authority_change_has_zero_partial_write(env, monkeypatch, change):
    data, _, _, _, original, resource, _, path, body = source_and_target(env, monkeypatch)
    if change == "goal":
        body["expected_goal_version"] += 1
    elif change in {"source", "graph", "model"}:
        field = {"source": "expected_source_hash", "graph": "expected_graph_fingerprint", "model": "expected_model_candidate_fingerprint"}[change]
        body[field] = "a" * 64
    else:
        with data[0].tx() as c:
            if change == "target-revoked":
                c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True, revision=2))
            else:
                runtime = c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id == original)).scalar_one()
                c.execute(update(grants).where(grants.c.principal_id == runtime).values(revoked=True, revision=2))
    before = rows(data[0])
    response = data[2].post(path + "/material-bindings", json=body)
    assert 400 <= response.status_code < 500, response.text
    assert rows(data[0]) == before


@pytest.mark.parametrize("change", ["graph", "marker", "namespace"])
def test_typed_binding_cannot_lower_or_rewrite_received_model_graph(env, monkeypatch, change):
    data, _, _, _, _, _, _, path, body = source_and_target(env, monkeypatch)
    saved = data[2].post(path + "/material-bindings", json=body).json()
    with data[0].tx() as c:
        candidate = c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == saved["id"])).scalar_one()
        if change == "graph":
            candidate["manifest"]["workflow"][0]["step_id"] = "coherent_replacement"
            for output in candidate["manifest"]["outputs"].values():
                output["ref"] = "coherent_replacement"
        elif change == "namespace":
            candidate.pop("namespace")
            candidate.pop("pa_binding")
        else:
            c.execute(delete(task_extractions).where(task_extractions.c.app_id == saved["id"]))
        c.execute(update(app_drafts).where(app_drafts.c.id == saved["id"]).values(candidate=candidate, fingerprint=fingerprint(candidate)))
    response = data[2].get(f"/api/apps/{saved['id']}")
    assert response.status_code == 409, response.text


def test_binding_seal_write_failure_rolls_back_all_new_objects(env, monkeypatch):
    data, _, _, _, _, _, _, path, body = source_and_target(env, monkeypatch)
    before = rows(data[0])
    original = binding.remember

    def fail(c, user, aid, kind, key, request, result):
        original(c, user, aid, kind, key, request, result)
        if kind == binding.BIND:
            raise DomainError("VERSION_CONFLICT", "Synthetic binding seal fault after write")

    monkeypatch.setattr(binding, "remember", fail)
    response = data[2].post(path + "/material-bindings", json=body)
    assert response.status_code == 409 and rows(data[0]) == before


def test_new_goal_or_permission_change_before_cold_execution_no_success(env, monkeypatch):
    data, _, _, _, _, resource, _, path, body = source_and_target(env, monkeypatch)
    saved = data[2].post(path + "/material-bindings", json=body).json()
    release, instance = release_instance(data, saved["id"])
    from sim2act import app_jobs
    actual_compute = app_jobs.compute

    def revoke_after_compute(plan, *args, **kwargs):
        output = actual_compute(plan, *args, **kwargs)
        with data[0].tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True, revision=2))
        return output

    monkeypatch.setattr(app_jobs, "compute", revoke_after_compute)
    response = data[2].post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance["revision"], expected_release_fingerprint=release["fingerprint"],
        input={"term": "Gamma"}, request_key="revoke-before-typed-commit"))
    assert response.status_code == 202, response.text
    assert Worker(data[0], data[1]).once()
    with data[0].tx() as c:
        assert not c.execute(select(internal_instance_data.c.run_id).where(internal_instance_data.c.instance_id == instance["id"])).first()
