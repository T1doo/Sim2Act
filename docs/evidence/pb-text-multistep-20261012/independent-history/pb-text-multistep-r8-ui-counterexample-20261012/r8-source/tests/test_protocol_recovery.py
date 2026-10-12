"""State recovery uses actual protocol ledgers and never invokes a provider."""

import copy
import time
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import func, select, update
from test_protocol_http import NoProvider, body, envelope, factory
from test_protocol_reviews import prepared

from sim2act.db import attempts, events, protocol_jobs, protocol_request_slots, runs
from sim2act.errors import DomainError
from sim2act.protocol_pool import initialize_pools
from sim2act.protocol_recovery import recover
from sim2act.tools import definitions
from sim2act.worker import Worker


@pytest.fixture
def env(env):
    initialize_pools(env[0], offline_limit=14)
    material = (
        Path(__file__).parents[1]
        / "docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt"
    )
    response = env[2].post(
        f"/api/projects/{env[5]}/resources",
        json={"name": "recovery policy", "format": "txt", "content": material.read_text()},
    )
    assert response.status_code == 201, response.text
    return (*env[:6], response.json()["id"])


def created(env):
    response = env[2].post(f"/api/projects/{env[5]}/protocol/source", json=body(env))
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def row(env, rid):
    with env[0].tx() as c:
        return dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())


def request(current, key="recover"):
    return {
        "expected_version": current["version"],
        "expected_fence": current["fence"],
        "request_key": key,
    }


def expire(env, rid):
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(lease_until=time.time() - 1))


def test_complete_source_recovery_only_preserves_waiting_review(env, tmp_path):
    rid, _, _, seen = prepared(env, tmp_path)
    before = row(env, rid)
    with env[0].tx() as c:
        original = copy.deepcopy(
            c.execute(
                select(protocol_jobs.c.result_snapshot).where(protocol_jobs.c.run_id == rid)
            ).scalar_one()
        )
    result = recover(env[0], env[3], rid, request(before))
    assert result["status"] == "WAITING_APPROVAL"
    assert result["recovery"] == "AWAITING_REVIEW"
    assert result["provider_requests"] == 0 and result["automatic_resend"] is False
    assert result["version"] == before["version"] and result["fence"] == before["fence"]
    cached = recover(env[0], env[3], rid, request(before))
    assert cached == {**result, "cached": True}
    assert len(seen) == 2 and env[0].claim("recovered", 30) is None
    with env[0].tx() as c:
        assert (
            c.execute(
                select(protocol_jobs.c.result_snapshot).where(protocol_jobs.c.run_id == rid)
            ).scalar_one()
            == original
        )
        assert c.execute(select(func.count()).select_from(protocol_request_slots)).scalar_one() == 2


def test_expired_unsent_claim_is_paused_not_auto_queued(env):
    rid = created(env)
    worker = Worker(env[0], env[1], NoProvider())
    owned = env[0].claim(worker.id, 30)
    assert owned["id"] == rid
    expire(env, rid)
    assert env[0].claim("next-worker", 30) is None
    current = row(env, rid)
    assert current["status"] == "PAUSED"
    assert current["fence"] == owned["fence"] + 1
    assert current["version"] == owned["version"] + 1
    result = recover(env[0], env[3], rid, request(current))
    assert result["recovery"] == "UNSENT_PAUSED" and result["provider_requests"] == 0
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 0
        assert c.execute(select(func.count()).select_from(protocol_request_slots)).scalar_one() == 0
        with pytest.raises(DomainError) as caught:
            env[0].guard(c, rid, owned["fence"])
        assert caught.value.code == "VERSION_CONFLICT"


def test_started_claim_recovery_preserves_attempt_and_globally_stops(env):
    rid = created(env)
    worker = Worker(env[0], replace(env[1], max_requests=3), NoProvider())
    owned = env[0].claim(worker.id, 30)
    context = copy.deepcopy(owned["context"])
    context["messages"] = [{"role": "user", "content": "synthetic pending request"}]
    tools = [t for t in definitions() if t["function"]["name"] == "resource.read"]
    aid = worker.reserve(rid, owned["fence"], context, request_tools=tools)
    expire(env, rid)
    assert env[0].claim("after-crash", 30) is None
    current = row(env, rid)
    assert current["status"] == "WAITING_RESOURCE" and current["fence"] > owned["fence"]
    answer = recover(env[0], env[3], rid, request(current))
    assert answer["recovery"] == "STOPPED_UNKNOWN" and answer["global_send_blocked"] is True
    with env[0].tx() as c:
        assert (
            c.execute(select(attempts.c.status).where(attempts.c.id == aid)).scalar_one()
            == "STARTED"
        )
        assert c.execute(
            select(protocol_request_slots.c.status).where(
                protocol_request_slots.c.attempt_id == aid
            )
        ).scalar_one() in {"STARTED", "UNKNOWN"}
    with pytest.raises(DomainError) as caught:
        env[0].command(env[3], rid, "resume", answer["version"])
    assert caught.value.code == "OUTCOME_UNKNOWN"
    other = (
        env[2]
        .post(
            f"/api/projects/{env[5]}/protocol/source", json=body(env, request_key="different-run")
        )
        .json()["run_id"]
    )
    fresh = env[0].claim("other-run", 30)
    assert fresh["id"] == other
    next_worker = Worker(env[0], replace(env[1], max_requests=3), NoProvider())
    next_context = copy.deepcopy(fresh["context"])
    next_context["messages"] = context["messages"]
    with pytest.raises(DomainError) as stopped:
        next_worker.reserve(other, fresh["fence"], next_context, request_tools=tools)
    assert stopped.value.code == "OUTCOME_UNKNOWN"
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 1


@pytest.mark.parametrize(
    "field,value",
    [("expected_version", True), ("expected_fence", False), ("PASS", True), ("response", {})],
)
def test_recovery_rejects_bool_versions_and_caller_evidence(env, field, value):
    rid = created(env)
    payload = {**request(row(env, rid)), field: value}
    result = env[2].post(f"/api/projects/{env[5]}/protocol/runs/{rid}/recover", json=payload)
    assert result.status_code == 422


def test_recovery_rejects_active_worker_and_stale_fence(env):
    rid = created(env)
    current = env[0].claim("active", 30)
    with pytest.raises(DomainError) as active:
        recover(env[0], env[3], rid, request(current))
    assert active.value.code == "VERSION_CONFLICT"
    expire(env, rid)
    with pytest.raises(DomainError) as stale:
        recover(env[0], env[3], rid, {**request(current), "expected_fence": current["fence"] + 1})
    assert stale.value.code == "VERSION_CONFLICT"


def test_recovery_auth_project_revocation_and_idempotency(env, tmp_path):
    rid, _, _, _ = prepared(env, tmp_path)
    current = row(env, rid)
    other = env[2].post("/api/projects", json={"name": "other"}).json()["id"]
    url = f"/api/projects/{env[5]}/protocol/runs/{rid}/recover"
    assert (
        env[2]
        .post(f"/api/projects/{other}/protocol/runs/{rid}/recover", json=request(current))
        .status_code
        == 403
    )
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    assert env[2].post(url, json=request(current)).status_code == 403
    env[2].headers["Authorization"] = "Bearer synthetic-test-A"
    assert env[2].post(url, json=request(current)).status_code == 200
    changed = {**request(current), "expected_fence": current["fence"] + 1}
    assert env[2].post(url, json=changed).status_code == 409
    from sim2act.db import grants

    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.project_id == env[5]).values(revoked=True))
    assert env[2].post(url, json=request(current)).status_code == 403


def test_recovery_event_row_cannot_spoof_status_or_bool_version(env, tmp_path):
    rid, _, _, _ = prepared(env, tmp_path)
    current = row(env, rid)
    recover(env[0], env[3], rid, request(current))
    with env[0].tx() as c:
        item = (
            c.execute(
                select(events).where(
                    events.c.run_id == rid, events.c.kind == "PROTOCOL_RECOVERY_REQUEST"
                )
            )
            .mappings()
            .one()
        )
        value = copy.deepcopy(item["data"])
        value["response"]["status"] = "SUCCEEDED"
        c.execute(update(events).where(events.c.id == item["id"]).values(data=value))
    with pytest.raises(DomainError) as caught:
        recover(env[0], env[3], rid, request(current))
    assert caught.value.code == "VERSION_CONFLICT"


def test_generic_f1_expired_claim_still_recovers_without_protocol_marker(env):
    store, _, _, owner, _, project, resource = env
    made = env[2].post(
        f"/api/projects/{project}/runs",
        json={"goal": "sum", "resource_refs": [resource], "request_key": "f1-expired"},
    )
    assert made.status_code == 202, made.text
    rid = made.json()["run_id"]
    original = store.claim("original-f1", 30)
    assert original["id"] == rid
    expire(env, rid)
    reclaimed = store.claim("next-f1", 30)
    assert reclaimed["id"] == rid and reclaimed["status"] == "RUNNING"
    assert reclaimed["fence"] > original["fence"]
    with pytest.raises(DomainError):
        recover(store, owner, rid, request(reclaimed))


def test_received_response_without_atomic_completion_cannot_continue(env, tmp_path):
    rid = created(env)
    worker = Worker(env[0], replace(env[1], max_requests=3), NoProvider())
    owned = env[0].claim(worker.id, 30)
    with env[0].tx() as c:
        snapshot = c.execute(
            select(protocol_jobs.c.accepted_snapshot).where(protocol_jobs.c.run_id == rid)
        ).scalar_one()
    seen = []
    runner = factory(env, tmp_path, [envelope(resource=env[6])], seen)(worker, owned, snapshot)
    read_tools = [t for t in definitions() if t["function"]["name"] == "resource.read"]
    runner.call([{"role": "user", "content": "read synthetic authorized material"}], read_tools)
    assert len(seen) == 1
    expire(env, rid)
    assert env[0].claim("response-recovery", 30) is None
    current = row(env, rid)
    assert current["status"] == "WAITING_RESOURCE"
    result = recover(env[0], env[3], rid, request(current))
    assert result["recovery"] == "CONTINUATION_NOT_IMPLEMENTED" and result["provider_requests"] == 0
    assert len(seen) == 1
    with env[0].tx() as c:
        assert (
            c.execute(
                select(protocol_jobs.c.result_snapshot).where(protocol_jobs.c.run_id == rid)
            ).scalar_one()
            is None
        )
        assert not c.execute(
            select(events.c.id).where(events.c.run_id == rid, events.c.kind == "PROTOCOL_COMPLETED")
        ).first()
        assert (
            c.execute(select(attempts.c.status).where(attempts.c.run_id == rid)).scalar_one()
            == "RECEIVED"
        )
    with pytest.raises(DomainError) as caught:
        env[0].command(env[3], rid, "resume", current["version"])
    assert caught.value.code == "OUTCOME_UNKNOWN"


def test_completed_pause_version_is_not_rewritten_for_acceptance(env, tmp_path):
    rid, _, _, _ = prepared(env, tmp_path)
    before = row(env, rid)
    env[0].command(env[3], rid, "pause", before["version"])
    paused = row(env, rid)
    with pytest.raises(DomainError):
        recover(env[0], env[3], rid, request(paused))
    after = row(env, rid)
    assert after["version"] == paused["version"] > before["version"]
    assert after["fence"] == paused["fence"] and after["status"] == "PAUSED"


def test_expired_namespace_frozen_marker_cannot_fall_back_to_f1(env):
    rid = created(env)
    old = env[0].claim("original-protocol", 30)
    with env[0].tx() as c:
        c.execute(protocol_jobs.delete().where(protocol_jobs.c.run_id == rid))
        c.execute(
            events.delete().where(events.c.run_id == rid, events.c.kind == "PROTOCOL_ACCEPTED")
        )
        context = dict(old["context"])
        context.pop("kind")
        c.execute(update(runs).where(runs.c.id == rid).values(context=context, lease_until=0))
    from sim2act.protocol_jobs import is_protocol_job

    assert is_protocol_job(env[0], rid) is True
    assert env[0].claim("wrong-f1-path", 30) is None
    current = row(env, rid)
    assert current["status"] == "WAITING_RESOURCE"
    assert current["fence"] > old["fence"]
    with env[0].tx() as c:
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 0
        assert not c.execute(
            select(events.c.id).where(events.c.run_id == rid, events.c.kind == "RECONCILED")
        ).first()
