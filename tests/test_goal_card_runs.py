"""Saved human conditions reach the real ordinary worker; Mock is contract evidence."""

import copy
import json

import pytest
from sqlalchemy import select, update

from sim2act.db import fingerprint, goal_card_versions, grants, principals, resources, runs
from sim2act.model import MockModel
from sim2act.worker import Worker


def card(env):
    _, _, client, _, _, pid, rid = env
    content = {"title": "按完整条件执行", "goal": "只读取材料，保留来源与未决事项",
               "known": ["这是假数据"], "assumptions": ["列含义尚待人工确认"],
               "unresolved": ["不能签收语义"], "constraints": ["不写业务数据", "不扩大授权"],
               "acceptance_checks": ["工具读取有真实回执", "不把旧成功当本次结果"],
               "resource_refs": [rid]}
    response = client.post(f"/api/projects/{pid}/goal-cards", json=content)
    assert response.status_code == 201
    return response.json(), content


def start(env, source, **changes):
    *_, pid, _rid = env
    body = {"expected_version": source["version"], "expected_fingerprint": source["fingerprint"],
            "request_key": "goal-real-task"}
    body.update(changes)
    return env[2].post(f"/api/projects/{pid}/goal-cards/{source['id']}/runs", json=body)


def authority(store):
    with store.engine.connect() as c:
        return fingerprint({t.name: sorted([dict(r) for r in c.execute(select(t)).mappings()],
                                            key=fingerprint) for t in (principals, grants)})


def test_complete_saved_conditions_reach_normal_worker_and_new_receipts(env, monkeypatch):
    store, settings, client, *_ = env
    source, content = card(env)
    before = authority(store)
    accepted = start(env, source)
    assert accepted.status_code == 202 and accepted.json()["candidate_generated"] is False
    rid = accepted.json()["run_id"]
    observed = []
    original = MockModel.request

    def observe(model, messages, tools):
        observed.append(copy.deepcopy((messages, tools)))
        return original(model, messages, tools)

    monkeypatch.setattr(MockModel, "request", observe)
    store.test_only = False  # This feature needs no protocol factory/test-only production gate.
    assert Worker(store, settings).once()
    result = client.get(f"/api/runs/{rid}").json()
    assert result["status"] == "PARTIAL" and result["result"]["goal_acceptance"] == "NOT_RUN"
    assert result["result"]["mode"] == "MOCK" and len(result["result"]["receipts"]) == 1
    binding = result["contract"]["snapshot"]["source_goal_card"]
    assert json.loads(observed[0][0][1]["content"])["saved_goal"] == binding
    assert binding["snapshot"]["content"] == content
    assert result["contract"]["snapshot"]["goal"]["constraints"] == content["constraints"]
    assert {t["function"]["name"] for t in observed[0][1]} == {"resource.read", "data.aggregate_csv"}
    assert len(observed) == 2 and authority(store) == before
    assert start(env, source).json()["run_id"] == rid


def test_lost_acceptance_after_goal_revision_keeps_original_snapshot(env):
    source, content = card(env)
    rid = start(env, source).json()["run_id"]
    revised = {**content, "goal": "修订后的另一个目标", "constraints": ["新条件"], "expected_version": 1}
    assert env[2].put(f"/api/goal-cards/{source['id']}", json=revised).status_code == 200
    assert start(env, source).json()["run_id"] == rid
    assert start(env, source, request_key="stale-new").status_code == 409
    assert Worker(env[0], env[1]).once()
    view = env[2].get(f"/api/runs/{rid}").json()
    assert view["contract"]["snapshot"]["source_goal_card"]["snapshot"]["content"] == content


@pytest.mark.parametrize("change", [{"expected_version": True}, {"expected_version": 1.0},
                                  {"snapshot": {}}, {"candidate": {}}, {"policy": {}}])
def test_closed_client_cannot_supply_execution_or_source(env, change):
    source, _ = card(env)
    assert start(env, source, **change).status_code == 422
    with env[0].engine.connect() as c:
        assert not c.execute(select(runs)).first()


def test_same_key_changed_version_or_fingerprint_and_other_project(env):
    source, _ = card(env)
    rid = start(env, source).json()["run_id"]
    assert start(env, source, expected_version=2).status_code == 409
    assert start(env, source, expected_fingerprint="0" * 64).status_code == 409
    other, _ = card(env)
    assert start(env, other).status_code == 409
    pid = env[2].post("/api/projects", json={"name": "另一个项目"}).json()["id"]
    body = {"expected_version": 1, "expected_fingerprint": source["fingerprint"], "request_key": "cross"}
    assert env[2].post(f"/api/projects/{pid}/goal-cards/{source['id']}/runs", json=body).status_code == 403
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert start(env, source).status_code == 403
    with env[0].engine.connect() as c:
        assert [r[0] for r in c.execute(select(runs.c.id))] == [rid]


@pytest.mark.parametrize("damage", ["history", "resource", "grant"])
def test_source_damage_before_worker_zero_model_requests(env, monkeypatch, damage):
    store, settings, client, *_rest, resource_id = env
    source, _ = card(env)
    rid = start(env, source).json()["run_id"]
    with store.tx() as c:
        if damage == "history":
            saved = c.execute(select(goal_card_versions).where(goal_card_versions.c.card_id == source["id"])).mappings().one()
            value = copy.deepcopy(saved["snapshot"])
            value["content"]["constraints"] = []
            c.execute(update(goal_card_versions).where(goal_card_versions.c.card_id == source["id"]).values(snapshot=value))
        elif damage == "resource":
            c.execute(update(resources).where(resources.c.id == resource_id).values(content="tampered"))
        else:
            c.execute(update(grants).where(grants.c.resource_id == resource_id).values(revoked=True))
    calls = []
    monkeypatch.setattr(MockModel, "request", lambda *a: calls.append(a))
    assert Worker(store, settings).once()
    assert calls == []
    with store.engine.connect() as c:
        saved = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert saved["status"] in {"FAILED", "WAITING_RESOURCE"} and saved["result"] is None
    assert client.get(f"/api/runs/{rid}").status_code in {403, 409}


def test_unadvertised_write_tool_rejected_without_authority_change(env, monkeypatch):
    source, _ = card(env)
    rid = start(env, source).json()["run_id"]
    before = authority(env[0])
    monkeypatch.setattr(MockModel, "request", lambda *_: {
        "model": "MOCK-intern-contract", "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": "", "tool_calls": [{"id": "write", "type": "function",
            "function": {"name": "artifact.save_text", "arguments": '{"text":"forbidden"}'}}]}}]})
    assert Worker(env[0], env[1]).once()
    view = env[2].get(f"/api/runs/{rid}").json()
    assert view["status"] == "FAILED" and view["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    assert authority(env[0]) == before and view["known_effects"] == []
