"""Actual API/normal Worker/httpx offline provider and real tool receipts."""

import copy
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from sim2act.api import create_app
from sim2act.db import (
    attempts,
    events,
    fingerprint,
    grants,
    operations,
    principals,
    run_contracts,
    runs,
)
from sim2act.errors import DomainError
from sim2act.model import MockModel
from sim2act.worker import Worker


def setup(env, provider="intern-s2"):
    store, settings, _, user, other, pid, _ = env
    settings = replace(settings, goal_planner_provider=provider)
    client = TestClient(create_app(store, settings))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    rid = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "novel.csv", "format": "csv", "content": "label,novel_count\na,7\nb,12\n"},
    ).json()["id"]
    content = {
        "title": "本次自然语言目标",
        "goal": "请计算 novel_count 的总量，说明尚待人工确认的含义",
        "known": ["合成材料"],
        "assumptions": ["列含义未签收"],
        "unresolved": ["单位未知"],
        "constraints": ["只读，不外发"],
        "acceptance_checks": ["可回读工具结果"],
        "resource_refs": [rid],
    }
    card = client.post(f"/api/projects/{pid}/goal-cards", json=content).json()
    card = client.get(f"/api/goal-cards/{card['id']}").json()
    return store, settings, client, pid, rid, card


def submit(value, key="nl", **extra):
    _, _, client, pid, _, card = value
    return client.post(
        f"/api/projects/{pid}/goal-cards/{card['id']}/planned-runs",
        json={
            "expected_version": card["version"],
            "expected_fingerprint": card["fingerprint"],
            "request_key": key,
            **extra,
        },
    )


def plan(value, tool="data.aggregate_csv"):
    return {
        "version": "natural-goal-plan.v1",
        "source_goal_fingerprint": value[-1]["fingerprint"],
        "interpretation": {
            "objective": "计算授权新列",
            "assumptions": ["单位未知"],
            "unresolved": ["人工确认含义"],
        },
        "steps": [
            {
                "id": "first",
                "tool_ref": tool,
                "resource_id": value[-2],
                "depends_on": [],
                **({"column": "novel_count"} if tool == "data.aggregate_csv" else {}),
            }
        ],
    }


def response(body, **changes):
    result = {
        "model": "Intern-S2",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        "choices": [
            {"finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(body)}}
        ],
    }
    result.update(changes)
    return result


def authority(store):
    with store.tx() as c:
        return {
            t.name: [dict(r) for r in c.execute(select(t).order_by(t.c.id)).mappings()]
            for t in (principals, grants)
        }


def rows(store, table):
    with store.tx() as c:
        return [dict(r) for r in c.execute(select(table)).mappings()]


@pytest.mark.parametrize("tool", ["resource.read", "data.aggregate_csv"])
def test_actual_provider_selects_distinct_plan_then_real_read_only_task(env, monkeypatch, tool):
    value = setup(env)
    store, settings, client, _, rid, card = value
    before = authority(store)
    expected = plan(value, tool)
    wires = []

    def handler(request):
        body = json.loads(request.content)
        wires.append(body)
        assert body["tools"] == [] and body["model"] == "intern-s2" and not body["stream"]
        projected = json.loads(body["messages"][1]["content"])
        assert projected["saved_goal"]["snapshot"]["content"] == card["content"]
        assert projected["materials"][0]["columns"] == ["label", "novel_count"]
        return httpx.Response(200, json=response(expected))

    monkeypatch.setattr(
        MockModel, "request", lambda *args: pytest.fail("No MockModel planning fallback")
    )
    accepted = submit(value)
    assert accepted.status_code == 202
    run_id = accepted.json()["run_id"]
    assert Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler)).once()
    result = client.get(f"/api/runs/{run_id}").json()
    assert result["status"] == "PARTIAL" and result["result"]["goal_acceptance"] == "NOT_RUN"
    assert (
        result["result"]["owner_acceptance"] == "PENDING"
        and not result["result"]["candidate_generated"]
    )
    assert result["result"]["planning"]["plan"] == expected
    receipt = result["result"]["receipts"][0]
    assert receipt["status"] == "VERIFIED"
    assert (
        receipt["data"]["sum"] == "19"
        if tool == "data.aggregate_csv"
        else receipt["data"]["resource_id"] == rid
    )
    assert len(wires) == len(rows(store, attempts)) == len(rows(store, operations)) == 1
    assert authority(store) == before
    assert submit(value).json()["run_id"] == run_id and len(rows(store, runs)) == 1
    client.close()


@pytest.mark.parametrize(
    "provider,mode", [("disabled", "mock"), ("intern-s2", "mock"), ("intern-s2", "live")]
)
def test_production_selection_does_not_grant_live_or_mock_fallback(
    env, monkeypatch, provider, mode
):
    value = setup(env, provider)
    store, settings, client, *_ = value
    settings = replace(settings, mode=mode, live_enabled=True, token="synthetic-never-send")
    client.close()
    client = TestClient(create_app(store, settings))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    value = (store, settings, client, *value[3:])
    from sim2act.model import InternModel

    monkeypatch.setattr(
        InternModel, "request_serialized", lambda *a, **k: pytest.fail("Zero network required")
    )
    monkeypatch.setattr(MockModel, "request", lambda *a, **k: pytest.fail("No fallback required"))
    run_id = submit(value).json()["run_id"]
    assert Worker(store, settings).once()
    view = client.get(f"/api/runs/{run_id}").json()
    assert view["status"] == "WAITING_RESOURCE"
    assert rows(store, attempts) == rows(store, operations) == []
    client.close()


@pytest.mark.parametrize(
    "damage",
    [
        "unknown_field",
        "write",
        "outside",
        "column",
        "dependency",
        "duplicate_id",
        "wrong_goal",
        "bool_version",
        "duplicate_json",
        "wrong_model",
        "unknown_usage",
        "truncated",
        "refusal",
    ],
)
def test_invalid_provider_result_dispatches_nothing_and_does_not_retry(env, damage):
    value = setup(env)
    store, settings, client, *_ = value
    before = authority(store)
    proposed = plan(value)
    raw = response(proposed)
    if damage == "unknown_field":
        proposed["publish"] = True
    if damage == "write":
        proposed["steps"][0]["tool_ref"] = "artifact.save_text"
    if damage == "outside":
        proposed["steps"][0]["resource_id"] = "res_" + "0" * 32
    if damage == "column":
        proposed["steps"][0]["column"] = "absent"
    if damage == "dependency":
        proposed["steps"][0]["depends_on"] = ["first"]
    if damage == "duplicate_id":
        proposed["steps"].append(copy.deepcopy(proposed["steps"][0]))
    if damage == "wrong_goal":
        proposed["source_goal_fingerprint"] = "0" * 64
    if damage == "bool_version":
        proposed["version"] = True
    raw["choices"][0]["message"]["content"] = json.dumps(proposed)
    if damage == "duplicate_json":
        raw["choices"][0]["message"]["content"] = json.dumps(proposed).replace(
            '"steps":', '"steps": [], "steps":'
        )
    if damage == "wrong_model":
        raw["model"] = "other"
    if damage == "unknown_usage":
        raw.pop("usage")
    if damage == "truncated":
        raw["choices"][0]["finish_reason"] = "length"
    if damage == "refusal":
        raw["choices"][0]["message"]["refusal"] = "unsupported"
    wires = []
    transport = httpx.MockTransport(
        lambda request: (wires.append(request.content), httpx.Response(200, json=raw))[1]
    )
    run_id = submit(value).json()["run_id"]
    assert Worker(store, settings, goal_planner_transport=transport).once()
    assert len(wires) == len(rows(store, attempts)) == 1 and rows(store, operations) == []
    assert client.get(f"/api/runs/{run_id}").json()["status"] in {"FAILED", "WAITING_RESOURCE"}
    with store.tx() as c:
        current = c.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
        ctx = dict(current["context"])
        ctx["requests"] = 0
        c.execute(update(runs).where(runs.c.id == run_id).values(status="QUEUED", context=ctx))
    assert Worker(store, settings, goal_planner_transport=transport).once()
    assert len(wires) == 1 and len(rows(store, attempts)) == 1 and authority(store) == before
    client.close()


def test_transport_injection_and_closed_input(env):
    value = setup(env)
    store, settings, client, *_ = value
    assert submit(value, plan=plan(value)).status_code == 422 and rows(store, runs) == []
    with pytest.raises(DomainError):
        Worker(store, settings, goal_planner_transport=httpx.HTTPTransport())
    store.test_only = False
    with pytest.raises(DomainError):
        Worker(store, settings, goal_planner_transport=httpx.MockTransport(lambda r: None))
    client.close()


@pytest.mark.parametrize("damage", ["policy", "plan", "attempt", "usage", "receipt", "counter"])
def test_persistent_plan_or_receipt_tamper_cannot_resume_or_refall_back(env, damage):
    value = setup(env)
    store, settings, client, *_ = value
    run_id = submit(value).json()["run_id"]
    calls = []
    transport = httpx.MockTransport(
        lambda request: (
            calls.append(request.content),
            httpx.Response(200, json=response(plan(value))),
        )[1]
    )
    assert Worker(store, settings, goal_planner_transport=transport).once()
    with store.tx() as c:
        current = c.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
        ctx = copy.deepcopy(current["context"])
        if damage == "plan":
            ctx["natural_plan"]["plan"]["interpretation"]["objective"] = "forged"
            ctx["natural_plan"]["fingerprint"] = fingerprint(ctx["natural_plan"]["plan"])
        if damage == "counter":
            ctx["tools"] = 0
        if damage == "policy":
            frozen = copy.deepcopy(
                c.execute(
                    select(run_contracts.c.snapshot).where(run_contracts.c.run_id == run_id)
                ).scalar_one()
            )
            frozen.pop("natural_planning")
            c.execute(
                update(run_contracts)
                .where(run_contracts.c.run_id == run_id)
                .values(snapshot=frozen, fingerprint=fingerprint(frozen))
            )
        if damage == "attempt":
            result = copy.deepcopy(
                c.execute(
                    select(attempts.c.response).where(attempts.c.run_id == run_id)
                ).scalar_one()
            )
            proposed = json.loads(result["content"])
            proposed["interpretation"]["objective"] = "伪造目标"
            result["content"] = json.dumps(proposed)
            c.execute(update(attempts).where(attempts.c.run_id == run_id).values(response=result))
        if damage == "usage":
            c.execute(
                update(attempts)
                .where(attempts.c.run_id == run_id)
                .values(usage={"status": "unknown", "tokens": None})
            )
        if damage == "receipt":
            op = c.execute(select(operations).where(operations.c.run_id == run_id)).mappings().one()
            receipt = copy.deepcopy(op["receipt"])
            receipt["data"]["sum"] = "999"
            c.execute(update(operations).where(operations.c.id == op["id"]).values(receipt=receipt))
        c.execute(update(runs).where(runs.c.id == run_id).values(status="QUEUED", context=ctx))
    assert Worker(store, settings, goal_planner_transport=transport).once()
    assert len(calls) == len(rows(store, attempts)) == len(rows(store, operations)) == 1
    assert rows(store, runs)[0]["status"] != "PARTIAL"
    client.close()


def test_two_step_plan_resumes_actual_receipts_without_new_provider(env):
    value = setup(env)
    store, settings, client, *_ = value
    proposed = plan(value, "resource.read")
    second = plan(value)["steps"][0]
    second.update(id="second", depends_on=["first"])
    proposed["steps"].append(second)
    wires = []
    run_id = submit(value).json()["run_id"]
    transport = httpx.MockTransport(
        lambda request: (
            wires.append(request.content),
            httpx.Response(200, json=response(proposed)),
        )[1]
    )
    assert Worker(store, settings, goal_planner_transport=transport).once()
    initial = client.get(f"/api/runs/{run_id}").json()
    assert initial["status"] == "PARTIAL" and len(initial["result"]["receipts"]) == 2
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == run_id).values(status="QUEUED", result=None))
    assert Worker(store, settings).once()
    assert client.get(f"/api/runs/{run_id}").json()["result"] == initial["result"]
    assert len(wires) == len(rows(store, attempts)) == 1 and len(rows(store, operations)) == 2
    client.close()


@pytest.mark.parametrize(
    "damage",
    ["wire_size", "tool_limit", "reported_output", "timeout", "revoke", "policy_bool", "result"],
)
def test_boundary_limits_and_current_authorization(env, damage):
    value = setup(env)
    store, settings, client, *_ = value
    if damage == "wire_size":
        content = copy.deepcopy(value[-1]["content"])
        content["known"] = ["x" * 1000 for _ in range(16)]
        cid = client.post(f"/api/projects/{value[3]}/goal-cards", json=content).json()["id"]
        value = (*value[:-1], client.get(f"/api/goal-cards/{cid}").json())
    run_id = submit(value).json()["run_id"]
    raw = response(plan(value))
    if damage == "reported_output":
        raw["usage"] = {"prompt_tokens": 1, "completion_tokens": 1025, "total_tokens": 1026}
    if damage == "tool_limit":
        step = copy.deepcopy(plan(value)["steps"][0])
        step.update(id="second", depends_on=["first"])
        raw = response({**plan(value), "steps": [plan(value)["steps"][0], step]})
        settings = replace(settings, max_tools=1)
        # Worker may tighten limits; planning validates this before dispatch.
    if damage in {"revoke", "policy_bool"}:
        with store.tx() as c:
            if damage == "revoke":
                c.execute(
                    update(grants).where(grants.c.resource_id == value[-2]).values(revoked=True)
                )
            else:
                frozen = copy.deepcopy(
                    c.execute(
                        select(run_contracts.c.snapshot).where(run_contracts.c.run_id == run_id)
                    ).scalar_one()
                )
                frozen["natural_planning"]["request_limit"] = True
                c.execute(
                    update(run_contracts)
                    .where(run_contracts.c.run_id == run_id)
                    .values(snapshot=frozen, fingerprint=fingerprint(frozen))
                )
    wires = []

    def handler(request):
        wires.append(request.content)
        if damage == "timeout":
            raise httpx.ReadTimeout("synthetic outcome unknown")
        return httpx.Response(200, json=raw)

    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    if damage == "result":
        with store.tx() as c:
            result = copy.deepcopy(
                c.execute(select(runs.c.result).where(runs.c.id == run_id)).scalar_one()
            )
            result["goal_acceptance"] = "PASS"
            c.execute(update(runs).where(runs.c.id == run_id).values(result=result))
        assert client.get(f"/api/runs/{run_id}").status_code == 409
    else:
        assert rows(store, operations) == []
        assert len(wires) == (0 if damage in {"wire_size", "revoke", "policy_bool"} else 1)
    client.close()


@pytest.mark.parametrize(
    "damage",
    [
        "attempt_wire",
        "wire_event",
        "coherent_wire",
        "coherent_unknown",
        "coherent_float",
        "request_counter",
        "removed_seal",
        "reserved_tokens",
    ],
)
def test_original_wire_and_strict_budget_survive_coordinated_tamper(env, damage):
    value = setup(env)
    store, settings, client, *_ = value
    calls = []
    transport = httpx.MockTransport(
        lambda request: (
            calls.append(request.content),
            httpx.Response(200, json=response(plan(value))),
        )[1]
    )
    run_id = submit(value).json()["run_id"]
    assert Worker(store, settings, goal_planner_transport=transport).once()
    with store.tx() as c:
        current = c.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
        ctx = copy.deepcopy(current["context"])
        if damage in {"attempt_wire", "coherent_wire"}:
            parameters = copy.deepcopy(
                c.execute(
                    select(attempts.c.parameters).where(attempts.c.run_id == run_id)
                ).scalar_one()
            )
            parameters["planning_wire"]["sha256"] = "0" * 64
            c.execute(
                update(attempts).where(attempts.c.run_id == run_id).values(parameters=parameters)
            )
        if damage in {"wire_event", "coherent_wire"}:
            seal = copy.deepcopy(
                c.execute(
                    select(events.c.data).where(
                        events.c.run_id == run_id, events.c.kind == "NL_PLANNING_WIRE_RESERVED"
                    )
                ).scalar_one()
            )
            seal["wire"]["sha256"] = "0" * 64
            c.execute(
                update(events)
                .where(events.c.run_id == run_id, events.c.kind == "NL_PLANNING_WIRE_RESERVED")
                .values(data=seal)
            )
        if damage in {"coherent_unknown", "coherent_float"}:
            usage = (
                {"status": "unknown", "tokens": None}
                if damage == "coherent_unknown"
                else {
                    "status": "known",
                    "tokens": {"prompt_tokens": 10.0, "completion_tokens": 20, "total_tokens": 30},
                }
            )
            seal = copy.deepcopy(
                c.execute(
                    select(events.c.data).where(
                        events.c.run_id == run_id, events.c.kind == "NL_PLAN_RECEIVED"
                    )
                ).scalar_one()
            )
            seal["usage"] = usage
            c.execute(update(attempts).where(attempts.c.run_id == run_id).values(usage=usage))
            c.execute(
                update(events)
                .where(events.c.run_id == run_id, events.c.kind == "NL_PLAN_RECEIVED")
                .values(data=seal)
            )
        if damage == "request_counter":
            ctx["requests"] = 0
        if damage == "reserved_tokens":
            c.execute(update(attempts).where(attempts.c.run_id == run_id).values(reserved_tokens=1))
        if damage == "removed_seal":
            from sqlalchemy import delete

            ctx.pop("natural_plan")
            ctx["requests"] = 0
            c.execute(
                delete(events).where(
                    events.c.run_id == run_id, events.c.kind == "NL_PLAN_VALIDATED"
                )
            )
        c.execute(update(runs).where(runs.c.id == run_id).values(context=ctx))
    view = client.get(f"/api/runs/{run_id}")
    unknown = damage in {"coherent_unknown", "coherent_float"}
    assert view.status_code == (400 if unknown else 409)
    assert view.json()["error"]["code"] == ("OUTCOME_UNKNOWN" if unknown else "VERSION_CONFLICT")
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == run_id).values(status="QUEUED"))
    assert Worker(store, settings, goal_planner_transport=transport).once()
    assert len(calls) == len(rows(store, attempts)) == len(rows(store, operations)) == 1
    assert rows(store, runs)[0]["status"] != "PARTIAL"
    client.close()
