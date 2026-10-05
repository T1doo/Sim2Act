"""General user-authored drafts; no model, execution or release implied."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from sim2act.api import create_app
from sim2act.db import (
    app_drafts,
    app_previews,
    attempts,
    goal_card_versions,
    goal_cards,
    grants,
    operations,
    runs,
)


def body(rid=None):
    return {
        "title": "会议说明草案", "goal": "整理授权文本成清晰说明",
        "known": ["读者是项目成员"], "assumptions": ["不需要外部资料"],
        "unresolved": ["需确认交付长度"], "constraints": ["保留原始事实，不外发"],
        "acceptance_checks": ["每项结论能引用授权材料"], "resource_refs": [rid] if rid else [],
    }


def create(env, content=None):
    *_, client, user, other, pid, rid = env
    response = client.post(f"/api/projects/{pid}/goal-cards", json=content or body(rid))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def count(store, table):
    with store.engine.connect() as c:
        return c.execute(select(func.count()).select_from(table)).scalar_one()


def test_general_goal_versions_preserve_requirements_and_cold_readback_without_execution(env):
    store, settings, client, _, _, pid, rid = env
    tracked = [runs, operations, attempts, app_drafts, app_previews, grants]
    before = {t.name: count(store, t) for t in tracked}
    original = body(rid)
    cid = create(env, original)
    first = client.get(f"/api/goal-cards/{cid}").json()
    assert first["content"] == original and first["state"] == "DRAFT"
    assert not first["executable"] and not first["publishable"]
    assert first["history"][0]["snapshot"]["resource_snapshots"][0]["resource_id"] == rid
    changed = {**original, "constraints": ["新增条件：最多一页"]}
    response = client.put(f"/api/goal-cards/{cid}", json={**changed, "expected_version": 1})
    assert response.status_code == 200 and response.json()["version"] == 2
    stale = client.put(f"/api/goal-cards/{cid}", json={**original, "expected_version": 1})
    assert stale.status_code == 409
    with TestClient(create_app(store, settings)) as cold:
        cold.headers.update({"Authorization": "Bearer synthetic-test-A"})
        result = cold.get(f"/api/goal-cards/{cid}").json()
    assert [v["version"] for v in result["history"]] == [2, 1]
    assert result["history"][1]["snapshot"]["content"] == original
    assert result["content"] == changed and result["fingerprint"] != first["fingerprint"]
    assert count(store, goal_card_versions) == 2
    assert before == {t.name: count(store, t) for t in tracked}
    assert client.get(f"/api/projects/{pid}/goal-cards").json()["items"][0]["id"] == cid


def test_empty_resource_draft_does_not_claim_execution_or_new_permissions(env):
    cid = create(env, body())
    response = env[2].get(f"/api/goal-cards/{cid}").json()
    assert response["history"][0]["snapshot"]["resource_snapshots"] == []
    assert response["content"]["unresolved"] and response["state"] == "DRAFT"


def test_other_user_and_cross_project_references_cannot_read_or_write_cards(env):
    store, _, client, _, _, pid, rid = env
    cid = create(env)
    second = client.post('/api/projects', json={"name": "other project"}).json()["id"]
    assert client.post(f"/api/projects/{second}/goal-cards", json=body(rid)).status_code == 403
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert client.get(f"/api/projects/{pid}/goal-cards").status_code == 403
    assert client.get(f"/api/goal-cards/{cid}").status_code == 403
    assert client.put(f"/api/goal-cards/{cid}", json={**body(), "expected_version": 1}).status_code == 403
    assert client.post(f"/api/projects/{pid}/goal-cards", json=body()).status_code == 403
    assert count(store, goal_cards) == count(store, goal_card_versions) == 1


@pytest.mark.parametrize('scope', ['user', 'runtime'])
def test_withdrawn_material_grant_blocks_historical_read_and_revision(env, scope):
    store, _, client, user, _, _, rid = env
    cid = create(env)
    with store.tx() as c:
        query = select(grants).where(grants.c.resource_id == rid, grants.c.tool_ref == 'resource.read')
        rows = c.execute(query).mappings().all()
        g = next(x for x in rows if (x['principal_id'] == user) == (scope == 'user'))
        c.execute(update(grants).where(grants.c.id == g['id']).values(revoked=True))
    read = client.get(f"/api/goal-cards/{cid}")
    assert read.status_code == 403 and '会议说明' not in read.text
    assert client.put(f"/api/goal-cards/{cid}", json={**body(), "expected_version": 1}).status_code == 403
    assert count(store, goal_card_versions) == 1


@pytest.mark.parametrize('changed', ['content', 'snapshot'])
def test_material_or_snapshot_tampering_refuses_history(env, changed):
    from sim2act.db import resources
    store, _, client, _, _, _, rid = env
    cid = create(env)
    with store.tx() as c:
        if changed == 'content':
            c.execute(update(resources).where(resources.c.id == rid).values(content='tampered'))
        else:
            c.execute(update(goal_card_versions).where(goal_card_versions.c.card_id == cid).values(snapshot={"tampered": True}))
    response = client.get(f"/api/goal-cards/{cid}")
    assert response.status_code == (400 if changed == "content" else 409)
    assert response.json()['error']['code'] in ('VERSION_CONFLICT', 'VERIFICATION_FAILED')


@pytest.mark.parametrize('field,value', [
    ('executor', 'shell'), ('known', ['x' * 1001]), ('constraints', ['x'] * 17),
    ('goal', ''), ('resource_refs', ['bad-path']),
])
def test_closed_input_rejection_has_no_card_write(env, field, value):
    store, _, client, _, _, pid, _ = env
    response = client.post(f"/api/projects/{pid}/goal-cards", json={**body(), field: value})
    assert response.status_code == (400 if field == "resource_refs" else 422)
    assert count(store, goal_cards) == count(store, goal_card_versions) == 0


def test_duplicate_material_references_are_rejected(env):
    store, _, client, _, _, pid, rid = env
    response = client.post(f"/api/projects/{pid}/goal-cards", json={**body(), 'resource_refs': [rid, rid]})
    assert response.status_code == 400 and response.json()["error"]["code"] == "INVALID_INPUT" and count(store, goal_cards) == 0


def test_two_stale_writers_produce_only_one_new_version(env):
    store, settings, _, _, _, _, _ = env
    cid = create(env, body())
    app = create_app(store, settings)
    def revise(index):
        with TestClient(app) as client:
            client.headers.update({'Authorization': 'Bearer synthetic-test-A'})
            return client.put(f'/api/goal-cards/{cid}', json={**body(), 'goal': f'revision {index}', 'expected_version': 1}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(revise, [1, 2]))
    assert sorted(results) == [200, 409]
    assert count(store, goal_card_versions) == 2
