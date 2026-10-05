"""Frozen human goal -> explicit MOCK capability -> restricted read-only preview."""

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    app_drafts,
    app_previews,
    attempts,
    fingerprint,
    goal_candidate_requests,
    grants,
    operations,
    principals,
    resources,
    runs,
)


def counts(store):
    with store.engine.connect() as c:
        return {t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
                for t in [app_drafts, app_previews, goal_candidate_requests, grants,
                          principals, runs, attempts, operations]}


def setup_card(env, refs=None):
    _, _, client, _, _, pid, rid = env
    content = {
        "title": "固定能力演示", "goal": "汇总授权CSV；这不是任意目标生成",
        "known": ["金额单位元"], "assumptions": ["人工确认列含义"],
        "unresolved": ["目标语义未验收"], "constraints": ["不外发", "保留所有原始条件"],
        "acceptance_checks": ["列合计与授权材料一致"], "resource_refs": refs or [rid],
    }
    response = client.post(f"/api/projects/{pid}/goal-cards", json=content)
    assert response.status_code == 201
    return response.json()["id"], content


def create_candidate(env, cid, **overrides):
    body = {"expected_version": 1, "resource_id": env[-1], "capability": "csv.sum", "request_key": "same-intent"}
    return env[2].post(f"/api/goal-cards/{cid}/candidates", json={**body, **overrides})


def test_catalog_is_read_only_and_full_frozen_goal_drives_exact_preview(env):
    store, settings, client, _, _, pid, rid = env
    cid, original = setup_card(env)
    before = counts(store)
    options = client.get(f"/api/goal-cards/{cid}/candidate-options").json()
    assert options["goal_version"] == 1 and options["items"] == []
    assert options["materials"] == [{"id": rid, "name": "data.csv", "format": "csv"}]
    assert [(c["id"], c["tool_ref"], c["version"], c["effect"], c["model_requests"])
            for c in options["capabilities"]] == [("csv.sum", "data.aggregate_csv", "1", "read", 0)]
    assert before == counts(store)
    created = create_candidate(env, cid)
    assert created.status_code == 201, created.text
    result = created.json()
    assert result["generator"] == "MOCK_DETERMINISTIC_CSV_SUM.v1"
    assert result["goal_acceptance"] == "NOT_RUN" and result["model_requests"] == 0
    assert result["state"] == "PREVIEW_ONLY" and not result["publishable"]
    aid = result["id"]
    draft = client.get(f"/api/apps/{aid}").json()
    assert draft["validation"] == {"state":"PREFLIGHTED_DRAFT", "execution_performed":False, "publishable":False, "topological_order":["aggregate"]}
    assert draft["candidate"]["goal"] == original
    assert draft["candidate"]["generation"]["goal_snapshot"]["content"] == original
    assert draft["candidate"]["manifest"]["goal_ref"] == cid
    assert draft["candidate"]["manifest"]["workflow"][0]["binding_id"] == "csv_sum"
    after = counts(store)
    assert after["app_drafts"] == before["app_drafts"] + 1
    assert after["principals"] == before["principals"] + 1
    assert after["grants"] == before["grants"] + 2
    with store.engine.connect() as c:
        scopes = c.execute(select(grants.c.resource_id, grants.c.tool_ref)
                           .where(grants.c.principal_id == draft["runtime_id"])).all()
    assert set(scopes) == {(rid, "resource.read"), (rid, "data.aggregate_csv")}
    preview = client.post(f"/api/apps/{aid}/previews", json={"input": {"column": "amount"}, "request_key": "run-1"}).json()
    assert preview["status"] == "SUCCEEDED" and preview["output"]["sum"] == "4.00"
    assert preview["output"]["count"] == 2 and preview["business_writes"] == preview["model_requests"] == 0
    for table in ["runs", "attempts", "operations"]:
        assert counts(store)[table] == before[table]
    with TestClient(create_app(store, settings)) as cold:
        cold.headers.update({"Authorization": "Bearer synthetic-test-A"})
        assert cold.get(f"/api/apps/{aid}").json()["history"][0]["id"] == preview["id"]
        assert cold.get(f"/api/goal-cards/{cid}/candidate-options").json()["items"][0]["id"] == aid


def test_request_repetition_and_changed_version_binding_do_not_duplicate_authority(env):
    store, _, client, _, _, _, _ = env
    cid, original = setup_card(env)
    first = create_candidate(env, cid).json()
    before = counts(store)
    assert create_candidate(env, cid).json() == first
    assert counts(store) == before
    assert client.put(f"/api/goal-cards/{cid}", json={**original, "constraints": ["新条件"], "expected_version": 1}).status_code == 200
    assert create_candidate(env, cid).json() == first
    assert create_candidate(env, cid, expected_version=2).status_code == 409
    assert create_candidate(env, cid, request_key="stale-new").status_code == 409
    old = client.get(f"/api/apps/{first['id']}").json()
    assert old["candidate"]["goal"]["constraints"] == original["constraints"]
    assert old["candidate"]["generation"]["goal_version"] == 1
    assert counts(store) == before


@pytest.mark.parametrize("field,value,status", [
    ("capability", "shell", 422), ("executor", "python", 422),
    ("model", "live", 422), ("actions", [{"code": "run arbitrary code"}], 422),
    ("expected_version", 0, 422), ("expected_version", 2, 409),
    ("request_key", "", 422), ("resource_id", "../file", 400),
])
def test_closed_inputs_and_stale_versions_fail_without_side_effect(env, field, value, status):
    cid, _ = setup_card(env)
    before = counts(env[0])
    assert create_candidate(env, cid, **{field: value}).status_code == status
    assert counts(env[0]) == before


def test_unbound_cross_project_and_other_user_sources_are_rejected(env):
    store, _, client, _, _, _, _ = env
    cid, _ = setup_card(env)
    second = client.post('/api/projects', json={"name": "another project"}).json()["id"]
    other_rid = client.post(f'/api/projects/{second}/resources', json={"name":"foreign.csv", "format":"csv", "content":"n\n1\n"}).json()["id"]
    before = counts(store)
    assert create_candidate(env, cid, resource_id=other_rid).status_code == 403
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert create_candidate(env, cid).status_code == 403
    assert client.get(f"/api/goal-cards/{cid}/candidate-options").status_code == 403
    assert counts(store) == before


def test_non_csv_source_is_explicitly_unsupported_without_grant_or_draft(env):
    store, _, client, _, _, pid, _ = env
    rid = client.post(f'/api/projects/{pid}/resources', json={"name":"note.md", "format":"md", "content":"# goal"}).json()["id"]
    cid, _ = setup_card(env, [rid])
    before = counts(store)
    assert client.get(f"/api/goal-cards/{cid}/candidate-options").json()["materials"] == []
    response = create_candidate(env, cid, resource_id=rid)
    assert response.status_code == 400 and response.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert counts(store) == before


@pytest.mark.parametrize("scope", ["user", "project", "app", "unselected_origin"])
def test_withdrawn_grants_block_candidate_history_and_preview(env, scope):
    store, _, client, user, _, pid, rid = env
    note = client.post(f'/api/projects/{pid}/resources', json={"name":"conditions.txt", "format":"txt", "content":"synthetic requirement"}).json()["id"]
    cid, _ = setup_card(env, [rid, note])
    aid = create_candidate(env, cid).json()["id"]
    runtime = client.get(f"/api/apps/{aid}").json()["runtime_id"]
    with store.tx() as c:
        rows = c.execute(select(grants).where(grants.c.resource_id == (note if scope == "unselected_origin" else rid), grants.c.tool_ref == "resource.read")).mappings().all()
        principal = user if scope in ["user", "unselected_origin"] else runtime if scope == "app" else next(g["principal_id"] for g in rows if g["principal_id"].startswith("runtime_"))
        c.execute(update(grants).where(grants.c.resource_id == (note if scope == "unselected_origin" else rid), grants.c.principal_id == principal, grants.c.tool_ref == "resource.read").values(revoked=True))
    before = counts(store)
    assert client.get(f"/api/apps/{aid}").status_code == 403
    assert client.post(f"/api/apps/{aid}/previews", json={"input":{"column":"amount"}, "request_key":"revoked"}).status_code == 403
    assert create_candidate(env, cid).status_code == 403
    assert counts(store) == before


@pytest.mark.parametrize("tamper", ["actual_source", "goal_snapshot", "requirements", "executor", "dependency_version"])
def test_tampering_is_refused_even_when_candidate_fingerprint_is_recomputed(env, tamper):
    store, _, client, _, _, _, rid = env
    cid, _ = setup_card(env)
    aid = create_candidate(env, cid).json()["id"]
    with store.tx() as c:
        if tamper == "actual_source":
            c.execute(update(resources).where(resources.c.id == rid).values(content="tampered"))
        else:
            original = c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
            candidate = copy.deepcopy(original)
            if tamper == "goal_snapshot":
                candidate["generation"]["goal_snapshot"]["content"]["constraints"] = []
            elif tamper == "requirements":
                candidate["goal"]["constraints"] = []
            elif tamper == "executor":
                candidate["actions"][0]["executor"] = {"kind":"registered_tool", "ref":"artifact.save_text", "version":"1"}
            else:
                candidate["manifest"]["dependency_lock"][1]["version"] = "99"
            c.execute(update(app_drafts).where(app_drafts.c.id == aid).values(candidate=candidate, fingerprint=fingerprint(candidate)))
    before = counts(store)
    response = client.get(f"/api/apps/{aid}")
    assert response.status_code in [400, 409], response.text
    assert client.post(f"/api/apps/{aid}/previews", json={"input":{"column":"amount"}, "request_key":"tamper"}).status_code in [400, 409]
    assert counts(store) == before


def test_two_identical_concurrent_requests_create_one_app_and_two_scoped_grants(env):
    store, settings, _, _, _, _, rid = env
    cid, _ = setup_card(env)
    before = counts(store)
    app = create_app(store, settings)
    def submit(_):
        with TestClient(app) as client:
            client.headers.update({"Authorization":"Bearer synthetic-test-A"})
            response = client.post(f"/api/goal-cards/{cid}/candidates", json={"expected_version":1,"resource_id":rid,"capability":"csv.sum","request_key":"concurrent"})
            assert response.status_code == 201
            return response.json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(submit, [1, 2]))
    assert first == second
    after = counts(store)
    assert after["app_drafts"] == before["app_drafts"] + 1
    assert after["goal_candidate_requests"] == before["goal_candidate_requests"] + 1
    assert after["principals"] == before["principals"] + 1
    assert after["grants"] == before["grants"] + 2


def test_failed_preview_retains_history_and_can_recover_with_valid_new_input(env):
    cid, _ = setup_card(env)
    aid = create_candidate(env, cid).json()["id"]
    client = env[2]
    failed = client.post(f"/api/apps/{aid}/previews", json={"input":{"column":"not-a-column"}, "request_key":"bad"}).json()
    assert failed["status"] == "FAILED" and failed["output"] is None
    ok = client.post(f"/api/apps/{aid}/previews", json={"input":{"column":"amount"}, "request_key":"good"}).json()
    assert ok["status"] == "SUCCEEDED" and ok["id"] != failed["id"]
    assert [r["status"] for r in client.get(f"/api/apps/{aid}").json()["history"]] == ["SUCCEEDED", "FAILED"]
    assert client.get(f"/api/goal-cards/{cid}").json()["version"] == 1


def test_pg_application_role_can_use_explicitly_migrated_candidate_tables(env, runtime_role):
    """This API path runs under bounded business CRUD, not the fixture schema owner."""
    _, settings, _, _, _, pid, rid = env
    store = Store(runtime_role)
    try:
        with TestClient(create_app(store, Settings(runtime_role, settings.data_dir, mode="mock"))) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            content = {"title":"application role goal", "goal":"sum CSV", "known":[],
                       "assumptions":[], "unresolved":["acceptance not run"],
                       "constraints":["read only"], "acceptance_checks":[], "resource_refs":[rid]}
            cid = client.post(f"/api/projects/{pid}/goal-cards", json=content).json()["id"]
            assert client.get(f"/api/goal-cards/{cid}/candidate-options").status_code == 200
            body = {"expected_version":1, "resource_id":rid, "capability":"csv.sum", "request_key":"role"}
            first = client.post(f"/api/goal-cards/{cid}/candidates", json=body)
            assert first.status_code == 201
            assert client.post(f"/api/goal-cards/{cid}/candidates", json=body).json() == first.json()
            aid = first.json()["id"]
            result = client.post(f"/api/apps/{aid}/previews", json={"input":{"column":"amount"}, "request_key":"role-preview"}).json()
            assert result["status"] == "SUCCEEDED" and result["output"]["sum"] == "4.00"
            assert client.get(f"/api/apps/{aid}").json()["history"][0]["id"] == result["id"]
    finally:
        store.engine.dispose()
