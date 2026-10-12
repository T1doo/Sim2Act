"""Explicit synthetic provider + actual SQLite HTTP/Worker + cold text AppRun."""

import copy
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from test_bounded_agent_apps import candidate as agent_fixture

from sim2act.api import create_app
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    fingerprint,
    goal_application_candidates,
    grants,
    run_contracts,
)
from sim2act.worker import Worker

CONTENT = (
    "Alpha obligation retained\nBeta due tomorrow\nAlpha owner undecided\n<em>Beta literal</em>\n"
)


def fixture_candidate(initial):
    """A provider fixture chooses a supported graph; never a production template."""
    source = initial["source"]
    saved = initial["saved_goal"]
    ids = initial["server_ids"]
    value = agent_fixture(source["resource_id"], CONTENT)
    value.pop("source_revision")
    value["goal"] = saved["snapshot"]["content"]
    manifest, action = value["manifest"], value["actions"][0]
    manifest.update(
        app_id=ids["app_id"],
        goal_ref=saved["card_id"],
        runtime_limits=initial["literal_contract"]["limits"],
    )
    manifest["action_bindings"][0]["action_id"] = ids["action_id"]
    manifest["dependency_lock"] = [
        {"kind": "resource", "ref": source["resource_id"], "version": "1"},
        {"kind": "tool", "ref": "text.literal_evidence", "version": "1"},
        {"kind": "check", "ref": "source.literal_evidence.v1", "version": "1"},
    ]
    action.update(
        action_id=ids["action_id"],
        executor={"kind": "registered_tool", "ref": "text.literal_evidence", "version": "1"},
        allowed_tool_refs=[],
        limits=initial["literal_contract"]["limits"],
    )
    return value


def wire(message, finish="stop", **changes):
    return {
        "model": "intern-s2",
        "choices": [{"finish_reason": finish, "message": message}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 900, "total_tokens": 1000},
        **changes,
    }


def setup(env, *, provider="intern-s2"):
    store, settings, _, user, _, pid, _ = env
    selected = replace(settings, goal_planner_provider=provider)
    client = TestClient(create_app(store, selected))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    text = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "checks.md", "format": "md", "content": CONTENT},
    ).json()["id"]
    goal = {
        "title": "Literal references",
        "goal": "给检索词返回完整匹配行和来源；不推断语义",
        "known": ["大小写敏感"],
        "assumptions": ["用户知道检索词"],
        "unresolved": ["义务解释未验"],
        "constraints": ["全部命中完整行", "不得总结"],
        "acceptance_checks": ["独立核对行号与原文"],
        "resource_refs": [text],
    }
    card = client.post(f"/api/projects/{pid}/goal-cards", json=goal).json()
    card = client.get(f"/api/goal-cards/{card['id']}").json()
    return store, selected, client, user, pid, text, card


def generate(data, *, repair=False, mutation=None):
    store, settings, client, _, pid, text, card = data
    sent = []

    def handler(request):
        payload = json.loads(request.content)
        sent.append(payload)
        initial = json.loads(payload["messages"][1]["content"])
        if len(sent) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "model-read-1",
                        "type": "function",
                        "function": {
                            "name": "resource.read",
                            "arguments": json.dumps({"resource_id": text}),
                        },
                    }
                ],
            }
            raw = wire(message, "tool_calls")
        else:
            receipt = json.loads(
                next(m["content"] for m in payload["messages"] if m["role"] == "tool")
            )
            assert receipt["status"] == "VERIFIED" and receipt["data"]["content"] == CONTENT
            value = fixture_candidate(initial)
            if repair and len(sent) == 2:
                value["manifest"]["workflow"][0]["inputs"].pop("term")
            if len(sent) == 3:
                assert "repair" in json.loads(payload["messages"][-1]["content"])
                assert payload["messages"][-2]["content"] != json.dumps(value)
            raw = wire(
                {
                    "role": "assistant",
                    "content": json.dumps(value, ensure_ascii=False, separators=(",", ":")),
                }
            )
        if mutation:
            mutation(raw, len(sent), payload)
        return httpx.Response(200, json=raw)

    body = {
        "expected_version": card["version"],
        "expected_fingerprint": card["fingerprint"],
        "request_key": "text-generation-1",
    }
    accepted = client.post(
        f"/api/projects/{pid}/goal-cards/{card['id']}/application-runs", json=body
    )
    assert accepted.status_code == 202, accepted.text
    rid = accepted.json()["run_id"]
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    result = client.get(f"/api/runs/{rid}")
    assert result.status_code == 200, result.text
    return rid, result.json(), sent


def confirm(data, rid, result):
    _, _, client, _, _, _, _ = data
    body = {
        "expected_version": result["version"],
        "candidate_fingerprint": result["result"]["candidate_fingerprint"],
        "request_key": "confirm-1",
        "name": "Literal app",
    }
    response = client.post(f"/api/runs/{rid}/confirm-application-candidate", json=body)
    assert response.status_code == 200, response.text
    return response.json()["id"], body


def release_instance(data, aid):
    _, _, client, _, _, _, _ = data
    draft = client.get(f"/api/apps/{aid}").json()
    prepared = client.post(
        f"/api/internal/apps/{aid}/release-approvals",
        json={
            "expected_draft_fingerprint": draft["fingerprint"],
            "sample_input": {"term": "Alpha"},
        },
    )
    assert prepared.status_code == 201, prepared.text
    a = prepared.json()
    release = client.post(
        f"/api/internal/approvals/{a['id']}/commit", json={"fingerprint": a["fingerprint"]}
    )
    assert release.status_code == 200, release.text
    r = release.json()
    instance = client.post(
        f"/api/internal/releases/{r['id']}/instances",
        json={"expected_release_fingerprint": r["fingerprint"], "request_key": "cold-1"},
    )
    assert instance.status_code == 201, instance.text
    return r, instance.json()


def run_input(data, release, instance, value, key):
    store, settings, client, _, _, _, _ = data
    response = client.post(
        f"/api/internal/instances/{instance['id']}/runs",
        json={
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "input": value,
            "request_key": key,
        },
    )
    assert response.status_code == 202, response.text
    worker = Worker(store, settings)
    assert worker.once()
    r = client.get(f"/api/internal/instances/{instance['id']}/runs/{response.json()['run_id']}")
    assert r.status_code == 200, r.text
    return r.json()


def test_goal_feedback_repair_release_cold_worker(env):
    data = setup(env)
    store, settings, client, user, _, text, card = data
    rid, result, sent = generate(data, repair=True)
    assert result["status"] == "PARTIAL", result
    assert len(sent) == 3 and sent[1]["tools"] == sent[2]["tools"] == []
    assert result["result"]["candidate"]["goal"] == card["content"]
    assert result["result"]["goal_acceptance"] == "NOT_RUN"
    with store.tx() as c:
        assert (
            c.execute(select(func.count()).select_from(goal_application_candidates)).scalar() == 0
        )
        original = (
            c.execute(
                select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at)
            )
            .mappings()
            .all()
        )
        assert len(original) == 3 and original[1]["error"] == "INVALID_MANIFEST"
        assert (
            "term"
            not in json.loads(original[1]["response"]["content"])["manifest"]["workflow"][0][
                "inputs"
            ]
        )
        assert all(a["mode"] == "MOCK" for a in original)
    aid, body = confirm(data, rid, result)
    assert (
        client.post(f"/api/runs/{rid}/confirm-application-candidate", json=body).json()["cached"]
        is True
    )
    assert (
        client.post(
            f"/api/runs/{rid}/confirm-application-candidate", json={**body, "name": "changed"}
        ).status_code
        == 409
    )
    preview = client.post(
        f"/api/apps/{aid}/previews", json={"input": {"term": "Alpha"}, "request_key": "preview-1"}
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["output"]["citations"] == [
        {"start_line": 1, "end_line": 1, "quote": "Alpha obligation retained"},
        {"start_line": 3, "end_line": 3, "quote": "Alpha owner undecided"},
    ]
    release, instance = release_instance(data, aid)
    # Reopen a cold store/worker; no Replay or provider injected into actual application run.
    cold = Store(settings.database_url, test_only=True)
    cold_data = (cold, *data[1:])
    result = run_input(cold_data, release, instance, {"term": "Beta"}, "cold-beta")
    assert result["status"] == "SUCCEEDED", result
    assert result["result"]["citations"] == [
        {"start_line": 2, "end_line": 2, "quote": "Beta due tomorrow"},
        {"start_line": 4, "end_line": 4, "quote": "<em>Beta literal</em>"},
    ]
    assert (
        run_input(cold_data, release, instance, {"term": "beta"}, "case-sensitive")["result"][
            "citations"
        ]
        == []
    )
    assert (
        run_input(cold_data, release, instance, {"term": "Alpha"}, "cold-alpha")["result"][
            "citations"
        ]
        != result["result"]["citations"]
    )
    for index, bad in enumerate(
        [
            {},
            {"term": 3},
            {"term": ""},
            {"term": " Alpha"},
            {"term": "a" * 81},
            {"term": "Beta", "resource_id": text},
        ]
    ):
        failed = run_input(cold_data, release, instance, bad, "bad-" + str(index))
        assert failed["status"] == "FAILED" and failed["result"] is None
    rows = client.get(f"/api/internal/instances/{instance['id']}").json()["data"]
    assert len(rows) == 3
    with store.tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar() == 3
        runtime = c.execute(select(app_drafts.c.runtime_id).where(app_drafts.c.id == aid)).scalar()
        actual = c.execute(select(grants).where(grants.c.principal_id == runtime)).mappings().all()
        assert (
            len(actual) == 1
            and actual[0]["resource_id"] == text
            and actual[0]["tool_ref"] == "resource.read"
        )
    cold.engine.dispose()


@pytest.mark.parametrize(
    "fault", ["usage", "identity", "truncated", "wrong-tool", "frozen-goal", "extra-field"]
)
def test_generation_failures_do_not_create_apps_or_retry(env, fault):
    data = setup(env)

    def mutate(raw, index, payload):
        if fault == "usage" and index == 1:
            raw.pop("usage")
        if fault == "identity" and index == 1:
            raw["model"] = "other"
        if fault == "truncated" and index == 1:
            raw["choices"][0]["finish_reason"] = "length"
        if fault == "wrong-tool" and index == 1:
            raw["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "artifact.save_text"
        if fault == "frozen-goal" and index == 2:
            value = json.loads(raw["choices"][0]["message"]["content"])
            value["goal"]["constraints"] = []
            raw["choices"][0]["message"]["content"] = json.dumps(value, separators=(",", ":"))
        if fault == "extra-field" and index >= 2:
            value = json.loads(raw["choices"][0]["message"]["content"])
            value["free_code"] = "bad"
            raw["choices"][0]["message"]["content"] = json.dumps(value, separators=(",", ":"))

    rid, result, sent = generate(data, mutation=mutate)
    assert result["status"] in {"FAILED", "WAITING_RESOURCE"}, result
    assert result["result"] is None
    assert len(sent) == (3 if fault == "extra-field" else 2 if fault == "frozen-goal" else 1)
    with data[0].tx() as c:
        if fault in {"usage", "identity", "truncated"}:
            rejected = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one()
            raw = json.loads(rejected["parameters"]["generation_rejected_raw"])
            assert (
                raw["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "resource.read"
            )
        assert c.execute(select(func.count()).select_from(app_drafts)).scalar() == 0
        assert (
            c.execute(select(func.count()).select_from(goal_application_candidates)).scalar() == 0
        )


def test_default_generation_has_no_model_send(env):
    data = setup(env, provider="disabled")
    rid, result, sent = generate(data)
    assert result["status"] == "WAITING_RESOURCE" and sent == []


@pytest.mark.parametrize("change", ["candidate", "marker", "executor", "attempt", "route"])
def test_independent_origin_blocks_resigned_candidate_and_route_downgrade(env, change):
    data = setup(env)
    rid, result, _ = generate(data)
    aid, _ = confirm(data, rid, result)
    store, _, client, _, _, _, _ = data
    with store.tx() as c:
        if change in {"candidate", "marker", "executor"}:
            row = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one()
            value = copy.deepcopy(row["candidate"])
            if change == "candidate":
                value["goal"]["constraints"] = []
            if change == "marker":
                value.pop("goal_application")
            if change == "executor":
                value["actions"][0]["executor"] = {
                    "kind": "registered_tool",
                    "ref": "data.aggregate_csv",
                    "version": "1",
                }
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == aid)
                .values(candidate=value, fingerprint=fingerprint(value))
            )
        elif change == "attempt":
            row = (
                c.execute(
                    select(attempts)
                    .where(attempts.c.run_id == rid)
                    .order_by(attempts.c.created_at.desc())
                )
                .mappings()
                .first()
            )
            msg = dict(row["response"])
            value = json.loads(msg["content"])
            value["goal"]["unresolved"] = []
            msg["content"] = json.dumps(value)
            c.execute(update(attempts).where(attempts.c.id == row["id"]).values(response=msg))
        else:
            value = c.execute(
                select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid)
            ).scalar()
            value = {k: v for k, v in value.items() if k != "application_generation"}
            c.execute(
                update(run_contracts)
                .where(run_contracts.c.run_id == rid)
                .values(snapshot=value, fingerprint=fingerprint(value))
            )
    assert client.get(f"/api/apps/{aid}").status_code == 409
