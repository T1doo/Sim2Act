import copy
import json
from dataclasses import replace

import httpx
import pytest
import test_goal_text_applications as helper
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from sim2act.api import create_app
from sim2act.db import (
    app_drafts,
    attempts,
    fingerprint,
    goal_application_candidates,
    grants,
    internal_app_runs,
    internal_instance_data,
    operations,
    principals,
    runs,
)
from sim2act.worker import Worker


def count(c, table):
    return c.execute(select(func.count()).select_from(table)).scalar_one()


@pytest.mark.parametrize("tamper", [False, True])
def test_frozen_aggregate_reservation_cannot_be_lowered(env, tamper):
    data = helper.setup(env)
    settings = replace(data[1], max_total_tokens=45000)
    client = TestClient(create_app(data[0], settings))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    data = (data[0], settings, client, *data[3:])

    def mutate(raw, index, payload):
        if tamper and index == 2:
            with data[0].tx() as c:
                row = c.execute(select(runs).where(runs.c.status == "RUNNING")).mappings().one()
                ctx = copy.deepcopy(row["context"])
                ctx["reserved_tokens"] = 0
                c.execute(update(runs).where(runs.c.id == row["id"]).values(context=ctx))

    rid, result, sent = helper.generate(data, repair=True, mutation=mutate)
    with data[0].tx() as c:
        actual = c.execute(
            select(func.sum(attempts.c.reserved_tokens)).where(attempts.c.run_id == rid)
        ).scalar_one()
    print(
        json.dumps(
            {
                "tamper": tamper,
                "status": result["status"],
                "sent": len(sent),
                "actual_reserved": actual,
                "frozen_limit": 45000,
            }
        )
    )
    assert actual <= 45000, "Actual durable reservations exceed frozen aggregate budget"
    if tamper:
        assert result["status"] != "PARTIAL", "Tampered aggregate counter was accepted"


@pytest.mark.parametrize(
    "field,value", [("status", "CANCELLED"), ("cancel_intent", True), ("result", None)]
)
def test_app_origin_requires_intact_completed_generation(env, field, value):
    data = helper.setup(env)
    rid, result, _ = helper.generate(data)
    aid, _ = helper.confirm(data, rid, result)
    with data[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(**{field: value}))
    reply = data[2].get(f"/api/apps/{aid}")
    print(json.dumps({"field": field, "http_status": reply.status_code}))
    assert reply.status_code in {400, 403, 409}, (
        "Invalidated generation still authorizes the application"
    )


@pytest.mark.parametrize("command", ["cancel", "pause", "revoke", "goal-change"])
def test_change_during_candidate_response_prevents_confirmation(env, command):
    data = helper.setup(env)

    def mutate(raw, index, payload):
        if index != 2:
            return
        with data[0].tx() as c:
            row = c.execute(select(runs).where(runs.c.status == "RUNNING")).mappings().one()
        if command in {"pause", "cancel"}:
            reply = data[2].post(
                f"/api/runs/{row['id']}/commands",
                json={"command": command, "version": row["version"]},
            )
            assert reply.status_code == 200, reply.text
        elif command == "revoke":
            with data[0].tx() as c:
                c.execute(
                    update(grants)
                    .where(grants.c.principal_id == data[3], grants.c.resource_id == data[5])
                    .values(revoked=True)
                )
        else:
            card = data[-1]
            reply = data[2].put(
                f"/api/goal-cards/{card['id']}",
                json={**card["content"], "title": "New title", "expected_version": card["version"]},
            )
            assert reply.status_code == 200, reply.text

    if command == "revoke":
        # Ordinary GET intentionally refuses content after revocation.
        try:
            helper.generate(data, mutation=mutate)
        except AssertionError:
            with data[0].tx() as c:
                row = c.execute(select(runs)).mappings().one()
                assert row["status"] != "PARTIAL" and row["result"] is None
            return
        pytest.fail("Revoked output was readable")
    _, result, sent = helper.generate(data, mutation=mutate)
    assert result["status"] != "PARTIAL" and result["result"] is None
    assert len(sent) == 2
    with data[0].tx() as c:
        assert count(c, app_drafts) == 0


def test_confirmation_failed_insert_rolls_back_identity_and_grant(env, monkeypatch):
    import sim2act.goal_applications as ga

    data = helper.setup(env)
    rid, result, _ = helper.generate(data)
    with data[0].tx() as c:
        before = {table.name: count(c, table) for table in [app_drafts, principals, grants]}
    original_insert = ga.insert

    def broken_insert(table):
        if table is ga.goal_application_candidates:
            raise RuntimeError("Independent injection at final source mapping insert")
        return original_insert(table)

    monkeypatch.setattr(ga, "insert", broken_insert)
    with pytest.raises(RuntimeError, match="Independent injection"):
        helper.confirm(data, rid, result)
    with data[0].tx() as c:
        assert {table.name: count(c, table) for table in [app_drafts, principals, grants]} == before


@pytest.mark.parametrize("confirmation", [None, {}, {"candidate_fingerprint": "0" * 64}])
def test_confirmation_authority_cannot_be_removed_after_creation(env, confirmation):
    data = helper.setup(env)
    rid, result, _ = helper.generate(data)
    aid, _ = helper.confirm(data, rid, result)
    with data[0].tx() as c:
        c.execute(
            update(goal_application_candidates)
            .where(goal_application_candidates.c.app_id == aid)
            .values(confirmation=confirmation)
        )
    reply = data[2].get(f"/api/apps/{aid}")
    print(json.dumps({"confirmation": confirmation, "http_status": reply.status_code}))
    assert reply.status_code in {400, 403, 409}, "Saved explicit authorization evidence was ignored"


@pytest.mark.parametrize("shape", [None, 3, []])
def test_corrupt_attempt_parameters_fail_closed_with_typed_error(env, shape):
    data = helper.setup(env)
    rid, result, _ = helper.generate(data)
    aid, _ = helper.confirm(data, rid, result)
    with data[0].tx() as c:
        item = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().first()
        c.execute(update(attempts).where(attempts.c.id == item["id"]).values(parameters=shape))
    reply = TestClient(create_app(data[0], data[1]), raise_server_exceptions=False)
    reply.headers.update({"Authorization": "Bearer synthetic-test-A"})
    response = reply.get(f"/api/apps/{aid}")
    print(json.dumps({"parameter_shape": shape, "http_status": response.status_code}))
    assert response.status_code in {400, 403, 409}, "Storage shape exception escaped as HTTP 500"


@pytest.mark.parametrize("kind", ["receipt", "record", "output", "run_status"])
def test_durable_literal_history_rejects_forged_saved_evidence(env, kind):
    data = helper.setup(env)
    rid, result, _ = helper.generate(data)
    aid, _ = helper.confirm(data, rid, result)
    release, instance = helper.release_instance(data, aid)
    completed = helper.run_input(data, release, instance, {"term": "Beta"}, "history")
    with data[0].tx() as c:
        if kind == "receipt":
            item = (
                c.execute(select(operations).where(operations.c.run_id == completed["id"]))
                .mappings()
                .one()
            )
            value = copy.deepcopy(item["receipt"])
            value["data"]["citations"][0]["quote"] = "forged"
            c.execute(update(operations).where(operations.c.id == item["id"]).values(receipt=value))
        elif kind == "record":
            item = c.execute(select(internal_instance_data)).mappings().one()
            value = copy.deepcopy(item["data"])
            value["result"]["citations"] = []
            c.execute(
                update(internal_instance_data)
                .where(internal_instance_data.c.instance_id == instance["id"])
                .values(data=value, fingerprint=fingerprint(value))
            )
        elif kind == "output":
            item = c.execute(select(internal_app_runs)).mappings().one()
            value = copy.deepcopy(item["output"])
            value["term"] = "Alpha"
            c.execute(
                update(internal_app_runs)
                .where(internal_app_runs.c.id == item["id"])
                .values(output=value)
            )
        else:
            c.execute(update(runs).where(runs.c.id == completed["id"]).values(status="FAILED"))
    response = data[2].get(f"/api/internal/instances/{instance['id']}")
    assert response.status_code in {400, 403, 409}, response.text


@pytest.mark.parametrize("confirmation", [None, []])
def test_confirmation_read_recovery_uses_typed_authority(env, confirmation):
    data = helper.setup(env)
    rid, result, _ = helper.generate(data)
    aid, _ = helper.confirm(data, rid, result)
    with data[0].tx() as c:
        c.execute(
            update(goal_application_candidates)
            .where(goal_application_candidates.c.app_id == aid)
            .values(confirmation=confirmation)
        )
    client = TestClient(create_app(data[0], data[1]), raise_server_exceptions=False)
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    response = client.get(f"/api/runs/{rid}/confirmed-application-candidate?request_key=confirm-1")
    print(
        json.dumps(
            {"confirmation_recovery_shape": confirmation, "http_status": response.status_code}
        )
    )
    assert response.status_code in {400, 403, 409}, response.text


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED"])
def test_job_read_cannot_skip_literal_history_verification(env, status):
    data = helper.setup(env)
    rid, result, _ = helper.generate(data)
    aid, _ = helper.confirm(data, rid, result)
    release, instance = helper.release_instance(data, aid)
    completed = helper.run_input(data, release, instance, {"term": "Beta"}, "job-history")
    with data[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == completed["id"]).values(status=status))
    response = data[2].get(f"/api/internal/instances/{instance['id']}/runs/{completed['id']}")
    print(
        json.dumps(
            {
                "job_status": status,
                "http_status": response.status_code,
                "result_present": bool(response.json().get("result")),
            }
        )
    )
    assert response.status_code in {400, 403, 409}, (
        "Job history downgrade skips exact successful-result proof"
    )


def test_unknown_provider_response_never_resends_or_imports_candidate(env):
    data = helper.setup(env)

    def timeout(raw, index, payload):
        if index == 2:
            raise httpx.ReadTimeout("Independent synthetic lost provider response")

    rid, result, sent = helper.generate(data, mutation=timeout)
    assert result["status"] == "WAITING_RESOURCE" and result["result"] is None
    assert len(sent) == 2
    with data[0].tx() as c:
        prior = (
            c.execute(
                select(attempts).where(attempts.c.run_id == rid).order_by(attempts.c.created_at)
            )
            .mappings()
            .all()
        )
    assert "generation_rejected_raw" not in prior[-1]["parameters"], (
        "Unknown response must not invent raw evidence"
    )
    response = data[2].post(
        f"/api/runs/{rid}/commands", json={"command": "resume", "version": result["version"]}
    )
    assert response.status_code == 200, response.text
    resent = []

    def forbid(request):
        resent.append(request)
        pytest.fail("Unknown generation request was actually resent")

    assert Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(forbid)).once()
    assert not resent
    with data[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    imported = data[2].post(
        f"/api/runs/{rid}/reconcile",
        json={
            "attempt_id": prior[-1]["id"],
            "version": row["version"],
            "decision": "record_response",
            "expected_fingerprint": prior[-1]["parameters"]["request_fingerprint"],
            "evidence": "Independent synthetic imported response",
            "acknowledge_unknown_cost": True,
            "response": helper.wire({"role": "assistant", "content": "{}"}),
        },
    )
    assert (
        imported.status_code == 400 and imported.json()["error"]["code"] == "UNSUPPORTED_CAPABILITY"
    ), imported.text


def test_late_actual_response_preserved_without_old_fence_mutation(env):
    data = helper.setup(env)
    saved = {}

    def switch(raw, index, payload):
        if index != 2:
            return
        with data[0].tx() as c:
            row = c.execute(select(runs).where(runs.c.status == "RUNNING")).mappings().one()
            state = {
                "fence": row["fence"] + 1,
                "worker_id": "independent-new-owner",
                "status": "PAUSED",
            }
            c.execute(update(runs).where(runs.c.id == row["id"]).values(**state))
            saved.update(state)

    rid, result, sent = helper.generate(data, mutation=switch)
    assert len(sent) == 2 and result["status"] == "PAUSED" and result["result"] is None
    with data[0].tx() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        last = (
            c.execute(
                select(attempts)
                .where(attempts.c.run_id == rid)
                .order_by(attempts.c.created_at.desc())
            )
            .mappings()
            .first()
        )
    assert all(row[k] == v for k, v in saved.items())
    assert (
        last["status"] == "FAILED"
        and last["response"]["role"] == "assistant"
        and last["response"]["content"]
    )
    raw = json.loads(last["parameters"]["generation_rejected_raw"])
    assert (
        raw["choices"][0]["message"] == last["response"]
        and raw["choices"][0]["finish_reason"] == "stop"
    )
