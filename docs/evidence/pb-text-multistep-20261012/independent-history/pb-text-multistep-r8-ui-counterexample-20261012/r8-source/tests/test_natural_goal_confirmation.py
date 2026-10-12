"""Explicit human confirmation separates actual provider planning from real reads."""

import copy

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select, update
from test_natural_goal_planning import authority, plan, response, rows, setup, submit

from sim2act.contracts import NaturalPlanningPolicy
from sim2act.db import events, grants, operations, resources, runs
from sim2act.goal_planner import policy
from sim2act.worker import Worker


def planned(env, key="confirmation"):
    value = setup(env)
    store, settings, client, _, _, _ = value
    wires = []

    def handler(request):
        wires.append(request.content)
        return httpx.Response(200, json=response(plan(value)))

    rid = submit(value, key).json()["run_id"]
    worker = Worker(store, settings, goal_planner_transport=httpx.MockTransport(handler))
    assert worker.once()
    result = client.get(f"/api/runs/{rid}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["status"] == "WAITING_APPROVAL"
    assert result["result"] is None
    assert result["natural_plan"]["validation"] == "VALIDATED"
    assert result["natural_plan"]["confirmation_required"] is True
    assert result["natural_plan"]["confirmed"] is False
    assert not rows(store, operations)
    body = {
        "expected_version": result["version"],
        "expected_plan_fingerprint": result["natural_plan"]["fingerprint"],
        "request_key": "explicit-human-confirm",
    }
    return value, rid, worker, wires, body


def confirm(client, rid, body):
    return client.post(f"/api/runs/{rid}/confirm-natural-plan", json=body)


def test_plan_waits_then_explicit_confirm_executes_without_second_model_call(env):
    value, rid, worker, wires, body = planned(env)
    store, _, client, _, _, _ = value
    before = authority(store)
    assert not worker.once()  # WAITING_APPROVAL is not claimable.
    first = confirm(client, rid, body)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "QUEUED"
    repeated = confirm(client, rid, body)
    assert repeated.json() == first.json()
    assert len([e for e in rows(store, events) if e["kind"] == "NL_PLAN_CONFIRMED"]) == 1
    assert worker.once()
    result = client.get(f"/api/runs/{rid}").json()
    assert result["status"] == "PARTIAL"  # Technical read is not goal semantic acceptance.
    assert result["natural_plan"]["confirmed"] is True
    assert result["result"]["receipts"][0]["data"]["sum"] == "19"
    assert result["result"]["goal_acceptance"] == "NOT_RUN"
    assert len(wires) == len(rows(store, operations)) == 1
    assert confirm(client, rid, body).status_code == 200
    assert authority(store) == before


@pytest.mark.parametrize("mutation", ["version", "plan", "key-extra", "bool-version"])
def test_stale_or_nonclosed_confirmation_has_zero_effects(env, mutation):
    value, rid, _, wires, body = planned(env)
    store, _, client, _, _, _ = value
    before = rows(store, runs), rows(store, events), authority(store)
    wrong = copy.deepcopy(body)
    if mutation == "version":
        wrong["expected_version"] += 1
    elif mutation == "plan":
        wrong["expected_plan_fingerprint"] = "0" * 64
    elif mutation == "key-extra":
        wrong["execute"] = True
    else:
        wrong["expected_version"] = True
    assert confirm(client, rid, wrong).status_code in {409, 422}
    assert (rows(store, runs), rows(store, events), authority(store)) == before
    assert len(wires) == 1 and not rows(store, operations)


def test_revoke_and_foreign_owner_confirmation_zero_effects(env):
    value, rid, _, _, body = planned(env)
    store, _, client, _, resource, _ = value
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert confirm(client, rid, body).status_code == 403
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == resource).values(revoked=True))
    before = rows(store, runs), rows(store, events)
    assert confirm(client, rid, body).status_code in {403, 409}
    assert (rows(store, runs), rows(store, events)) == before
    assert not rows(store, operations)


@pytest.mark.parametrize("mutation", ["plan-context", "plan-event", "resource", "project"])
def test_current_source_and_plan_binding_tamper_rejected(env, mutation):
    value, rid, _, _, body = planned(env)
    store, _, client, _, resource, _ = value
    other_project = client.post("/api/projects", json={"name": "Another owned project"}).json()[
        "id"
    ]
    with store.tx() as c:
        r = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        if mutation == "plan-context":
            ctx = copy.deepcopy(r["context"])
            ctx["natural_plan"]["plan"]["interpretation"]["objective"] = "Changed"
            c.execute(update(runs).where(runs.c.id == rid).values(context=ctx))
        elif mutation == "plan-event":
            e = (
                c.execute(
                    select(events).where(
                        events.c.run_id == rid, events.c.kind == "NL_PLAN_VALIDATED"
                    )
                )
                .mappings()
                .one()
            )
            data = copy.deepcopy(e["data"])
            data["fingerprint"] = "0" * 64
            c.execute(update(events).where(events.c.id == e["id"]).values(data=data))
        elif mutation == "resource":
            c.execute(
                update(resources)
                .where(resources.c.id == resource)
                .values(content="novel_count\n999\n")
            )
        else:
            c.execute(update(runs).where(runs.c.id == rid).values(project_id=other_project))
    assert confirm(client, rid, body).status_code in {403, 409}
    assert not rows(store, operations)


def test_manual_queue_or_resume_cannot_bypass_confirmation_and_cancel_waiting(env):
    value, rid, worker, wires, body = planned(env)
    store, _, client, _, _, _ = value
    # A direct state change cannot manufacture the independent confirmation seal.
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status="QUEUED"))
    assert worker.once()
    assert client.get(f"/api/runs/{rid}").json()["status"] == "WAITING_APPROVAL"
    assert len(wires) == 1 and not rows(store, operations)
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status="PAUSED"))
        version = c.execute(select(runs.c.version).where(runs.c.id == rid)).scalar_one()
    from sim2act.errors import DomainError

    with pytest.raises(DomainError) as rejected:
        store.command(env[3], rid, "resume", version)
    assert rejected.value.code == "PERMISSION_DENIED"
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status="WAITING_APPROVAL"))
    assert store.command(env[3], rid, "cancel", version) == "CANCELLED"
    body["expected_version"] = version + 1
    assert confirm(client, rid, body).status_code == 409
    assert not rows(store, operations)


def test_confirmation_seal_tamper_blocks_worker_before_read(env):
    value, rid, worker, wires, body = planned(env)
    store, _, client, _, _, _ = value
    assert confirm(client, rid, body).status_code == 200
    with store.tx() as c:
        r = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        ctx = copy.deepcopy(r["context"])
        ctx["natural_plan_confirmation"]["plan_fingerprint"] = "0" * 64
        c.execute(update(runs).where(runs.c.id == rid).values(context=ctx))
    assert worker.once()
    assert not rows(store, operations) and len(wires) == 1
    assert client.get(f"/api/runs/{rid}").status_code == 409


@pytest.mark.parametrize("provider", ["disabled", "intern-s2"])
def test_status_is_project_scoped_disabled_and_zero_allowance(env, provider):
    value = setup(env, provider=provider)
    store, settings, client, pid, _, _ = value
    status = client.get(f"/api/projects/{pid}/natural-planning-status").json()
    assert status["provider"] == provider and status["live_request_allowance"] == 0
    assert status["available"] is False
    assert status["reason"] == (
        "PROVIDER_DISABLED" if provider == "disabled" else "LIVE_ALLOWANCE_ZERO"
    )
    rid = submit(value).json()["run_id"]
    assert Worker(store, settings).once()
    assert client.get(f"/api/runs/{rid}").json()["status"] == "WAITING_RESOURCE"
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert client.get(f"/api/projects/{pid}/natural-planning-status").status_code == 403
    assert not rows(store, operations)


def test_old_optional_policy_keeps_original_shape_and_strict_flag():
    old = policy("disabled", require_confirmation=False)
    assert "require_confirmation" not in old
    assert NaturalPlanningPolicy.model_validate(old).model_dump(exclude_none=True) == old
    for bad in [1, False, "true"]:
        with pytest.raises(ValidationError):
            NaturalPlanningPolicy.model_validate({**old, "require_confirmation": bad})


def test_confirmation_from_another_actual_run_cannot_replay(env):
    value, first, worker, wires, body = planned(env, key="first")
    store, _, client, _, _, _ = value
    assert confirm(client, first, body).status_code == 200
    second = submit(value, key="second").json()["run_id"]
    # FIFO first completes; second plans under its independent actual Attempt.
    assert worker.once()
    assert worker.once()
    assert client.get(f"/api/runs/{second}").json()["status"] == "WAITING_APPROVAL"
    with store.tx() as c:
        first_ctx = c.execute(select(runs.c.context).where(runs.c.id == first)).scalar_one()
        second_ctx = copy.deepcopy(
            c.execute(select(runs.c.context).where(runs.c.id == second)).scalar_one()
        )
        seal = first_ctx["natural_plan_confirmation"]
        second_ctx["natural_plan_confirmation"] = copy.deepcopy(seal)
        c.execute(update(runs).where(runs.c.id == second).values(context=second_ctx))
        store.event(c, second, "NL_PLAN_CONFIRMED", copy.deepcopy(seal))
    assert confirm(client, second, body).status_code == 409
    assert len(wires) == 2 and len(rows(store, operations)) == 1


def test_concurrent_same_key_confirmation_is_single_atomic_transition(env):
    from concurrent.futures import ThreadPoolExecutor

    from sim2act.goal_planner import confirm_natural_plan

    value, rid, _, _, body = planned(env)
    store, _, _, _, _, _ = value
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _: confirm_natural_plan(store, env[3], rid, body), range(2)))
    assert result[0] == result[1]
    assert len([e for e in rows(store, events) if e["kind"] == "NL_PLAN_CONFIRMED"]) == 1
    assert not rows(store, operations)


def test_legacy_absent_flag_executes_original_frozen_policy_without_rewriting(env):
    from sim2act.contracts import Limits

    value = setup(env)
    store, settings, client, pid, _, card = value
    old_policy = policy("intern-s2", require_confirmation=False)
    limits = Limits(**{key: getattr(settings, key) for key in Limits.model_fields}).model_dump()
    rid = store.submit(
        env[3],
        pid,
        "",
        [],
        "legacy-policy",
        policy={
            "limits": {**limits, "max_requests": 1, "max_repairs": 0},
            "mode": "mock",
            "request_model": "intern-s2",
            "natural_planning": old_policy,
        },
        goal_source={
            "card_id": card["id"],
            "version": card["version"],
            "fingerprint": card["fingerprint"],
        },
    )
    accepted = [e for e in rows(store, events) if e["kind"] == "ACCEPTED"]
    worker = Worker(
        store,
        settings,
        goal_planner_transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=response(plan(value)))
        ),
    )
    assert worker.once()
    result = client.get(f"/api/runs/{rid}").json()
    assert result["status"] == "PARTIAL"
    assert result["natural_plan"]["confirmation_required"] is False
    assert [e for e in rows(store, events) if e["kind"] == "ACCEPTED"] == accepted


def test_natural_resume_issues_project_then_run_then_grant_lock_queries(env):
    from sqlalchemy import event

    value, rid, _, _, body = planned(env)
    store, _, client, _, _, _ = value
    assert confirm(client, rid, body).status_code == 200
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status="PAUSED"))
        version = c.execute(select(runs.c.version).where(runs.c.id == rid)).scalar_one()
    locks = []

    def record(conn, statement, multiparams, params, options):
        if getattr(statement, "_for_update_arg", None) is not None:
            tables = statement.get_final_froms()
            if len(tables) == 1 and getattr(tables[0], "name", None) in {
                "projects",
                "runs",
                "grants",
            }:
                locks.append(tables[0].name)

    event.listen(store.engine, "before_execute", record)
    try:
        assert store.command(env[3], rid, "resume", version) == "QUEUED"
    finally:
        event.remove(store.engine, "before_execute", record)
    assert locks[:3] == ["projects", "runs", "grants"]
    assert not rows(store, operations)
