"""Shared budget tests use durable slots and actual offline InternModel requests."""

import copy

import pytest
from sqlalchemy import select, update
from test_protocol_jobs import (
    env as _jobs_env,
)
from test_protocol_jobs import (
    factory_for,
    source_payload,
    wire,
)

from sim2act.contracts import Limits
from sim2act.db import Store, attempts, protocol_jobs, runs
from sim2act.db import protocol_request_pools as pools
from sim2act.db import protocol_request_slots as slots
from sim2act.errors import DomainError
from sim2act.protocol_jobs import enqueue
from sim2act.protocol_pool import (
    LIVE_POOL,
    OFFLINE_POOL,
    audit_pool,
    initialize_pools,
    inspect_pool,
    require_pool,
)

env = _jobs_env

LIMITS = Limits(
    max_requests=3,
    max_tools=4,
    max_repairs=0,
    max_total_tokens=64000,
    max_output_tokens=1024,
    run_seconds=300,
)


def claimed_source(env, key="source"):
    store, user, pid, a, b, worker, tmp = env
    accepted = enqueue(store, user, pid, "source", source_payload(a), key, LIMITS)
    claimed = store.claim(worker.id, worker.s.lease_seconds)
    with store.tx() as c:
        snapshot = c.execute(
            select(protocol_jobs.c.accepted_snapshot).where(protocol_jobs.c.run_id == claimed["id"])
        ).scalar_one()
    return accepted, claimed, snapshot


def test_explicit_default_pool_zero_live_and_offline_and_no_reset(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "empty.sqlite"), test_only=True)
    store.initialize()
    initialize_pools(store)
    assert inspect_pool(store, OFFLINE_POOL)["request_limit"] == 0
    assert inspect_pool(store, LIVE_POOL)["request_limit"] == 0
    with pytest.raises(DomainError) as raised:
        initialize_pools(store, offline_limit=14)
    assert raised.value.code == "VERSION_CONFLICT"


def test_shared_atomic_request_limit_across_runs_and_new_runner_files(env):
    store, user, pid, a, b, worker, tmp = env
    actual = []
    for index in range(14):
        accepted, run, snapshot = claimed_source(env, str(index))
        requests = factory_for(env, [wire({"summary": str(index)})], "source_a")
        runner = worker.protocol_runner_factory(worker, run, snapshot)
        runner.call([{"role": "user", "content": "read-only budget wire probe"}], [])
        actual.extend(requests)
        with store.tx() as c:
            c.execute(
                update(runs).where(runs.c.id == run["id"]).values(status="PAUSED", lease_until=0)
            )
    summary = inspect_pool(store, OFFLINE_POOL)
    assert summary["reserved_requests"] == 14 and summary["known_tokens"] == 280
    assert len(actual) == 14 and summary["has_pending"] is False
    accepted, run, snapshot = claimed_source(env, "fifteenth")
    requests = factory_for(env, [wire({"summary": "forbidden fifteenth"})], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    with pytest.raises(DomainError) as raised:
        runner.call([{"role": "user", "content": "new local ledger cannot refill global cap"}], [])
    assert raised.value.code == "BUDGET_EXHAUSTED" and not requests
    with store.engine.connect() as c:
        assert len(c.execute(select(attempts)).all()) == 14
        assert len(c.execute(select(slots)).all()) == 14
    # A fresh Store/controller cannot erase capacity or replace immutable records.
    initialize_pools(store, offline_limit=14)
    assert inspect_pool(store, OFFLINE_POOL)["reserved_requests"] == 14


def test_known_preflight_policy_rejection_does_not_reserve_or_send(env):
    store, user, pid, a, b, worker, tmp = env
    accepted, run, snapshot = claimed_source(env)
    requests = factory_for(env, [wire({"summary": "must not be sent"})], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    with pytest.raises(DomainError) as raised:
        runner.call([{"role": "user", "content": "x" * 10001}], [])
    assert raised.value.code == "BUDGET_EXHAUSTED" and not requests
    assert inspect_pool(store, OFFLINE_POOL)["reserved_requests"] == 0
    with store.engine.connect() as c:
        assert not c.execute(select(attempts)).first()


def test_slot_and_attempt_reservation_rollback_together(env, monkeypatch):
    store, user, pid, a, b, worker, tmp = env
    accepted, run, snapshot = claimed_source(env)
    original = store.event

    def crash(c, rid, kind, data=None):
        if kind == "MODEL_RESERVED":
            raise RuntimeError("synthetic crash before shared DB commit")
        return original(c, rid, kind, data)

    monkeypatch.setattr(store, "event", crash)
    with pytest.raises(RuntimeError):
        worker.reserve(run["id"], run["fence"], copy.deepcopy(run["context"]), request_tools=[])
    assert inspect_pool(store, OFFLINE_POOL)["reserved_requests"] == 0
    with store.engine.connect() as c:
        assert not c.execute(select(attempts)).first() and not c.execute(select(slots)).first()


def test_unfinished_reserved_request_globally_blocks_restart_without_refund(env):
    store, user, pid, a, b, worker, tmp = env
    accepted, run, snapshot = claimed_source(env)
    aid = worker.reserve(run["id"], run["fence"], copy.deepcopy(run["context"]), request_tools=[])
    with pytest.raises(DomainError) as raised:
        require_pool(store, OFFLINE_POOL)
    assert raised.value.code == "OUTCOME_UNKNOWN"
    summary = inspect_pool(store, OFFLINE_POOL)
    assert (
        summary["halted"] is True
        and summary["has_pending"] is True
        and summary["reserved_requests"] == 1
    )
    initialize_pools(store, offline_limit=14)
    with store.tx() as c:
        assert (
            c.execute(select(attempts.c.status).where(attempts.c.id == aid)).scalar_one()
            == "STARTED"
        )
        assert (
            c.execute(select(slots.c.status).where(slots.c.attempt_id == aid)).scalar_one()
            == "STARTED"
        )
        assert audit_pool(c, OFFLINE_POOL)["reserved_requests"] == 1
    with pytest.raises(DomainError):
        require_pool(store, OFFLINE_POOL)


def test_shared_token_limit_cannot_be_refilled_by_new_run(env):
    store, user, pid, a, b, worker, tmp = env
    accepted, run, snapshot = claimed_source(env)
    ctx = copy.deepcopy(run["context"])
    ctx["messages"] = [{"role": "user", "content": "x" * 62000}]
    # This directly exercises the conservative DB byte reservation, not transport.
    aid = worker.reserve(run["id"], run["fence"], ctx, request_tools=[])
    assert inspect_pool(store, OFFLINE_POOL)["reserved_tokens"] > 63000
    # Settle through the real adapter _record to preserve both ledgers atomically.
    requests = factory_for(env, [], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    runner._record(aid, wire({"summary": "known synthetic record"}), 0, "RECEIVED")
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == run["id"]).values(status="PAUSED", lease_until=0))
    _, other, other_snapshot = claimed_source(env, "other")
    requests = factory_for(env, [wire({"summary": "forbidden"})], "source_a")
    runner = worker.protocol_runner_factory(worker, other, other_snapshot)
    with pytest.raises(DomainError) as raised:
        runner.call([{"role": "user", "content": "minimal"}], [])
    assert raised.value.code == "BUDGET_EXHAUSTED" and not requests


def test_pool_ledger_record_deletion_cannot_reset_count(env):
    from sqlalchemy import delete

    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    worker.reserve(run["id"], run["fence"], copy.deepcopy(run["context"]), request_tools=[])
    with store.tx() as c:
        c.execute(delete(slots))
    with pytest.raises(DomainError):
        require_pool(store, OFFLINE_POOL)
    with store.engine.connect() as c:
        assert (
            c.execute(select(pools.c.halted).where(pools.c.id == OFFLINE_POOL)).scalar_one() is True
        )


def test_unknown_usage_stops_other_runs_but_preserves_actual_known_failure(env):
    # Semantic/policy failures after a known response do not manufacture UNKNOWN.
    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    factory_for(env, [wire({"summary": "known policy-invalid result"})], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    runner.call([{"role": "user", "content": "known response"}], [])
    runner.halt()
    assert inspect_pool(store, OFFLINE_POOL)["halted"] is False
    require_pool(store, OFFLINE_POOL)


def test_controller_genesis_prevents_coherent_zero_to_fourteen_raise(tmp_path):
    from sim2act.db import fingerprint
    from sim2act.protocol_pool import _policy

    store = Store("sqlite:///" + str(tmp_path / "approval.sqlite"), test_only=True)
    store.initialize()
    initialize_pools(store)
    with store.tx() as c:
        c.execute(
            update(pools)
            .where(pools.c.id == OFFLINE_POOL)
            .values(request_limit=14, policy_fingerprint=fingerprint(_policy("offline", 14)))
        )
    with pytest.raises(DomainError) as raised:
        require_pool(store, OFFLINE_POOL)
    assert raised.value.code == "VERSION_CONFLICT"


def test_coordinated_slot_and_counter_deletion_cannot_refill_new_run(env):
    from sqlalchemy import delete

    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    factory_for(env, [wire({"summary": "known"})], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    runner.call([{"role": "user", "content": "first"}], [])
    with store.tx() as c:
        c.execute(delete(slots))
        c.execute(
            update(pools)
            .where(pools.c.id == OFFLINE_POOL)
            .values(reserved_requests=0, reserved_tokens=0, known_tokens=0)
        )
        c.execute(update(runs).where(runs.c.id == run["id"]).values(status="PAUSED", lease_until=0))
    _, new_run, new_snapshot = claimed_source(env, "new")
    requests = factory_for(env, [wire({"summary": "forbidden refill"})], "source_a")
    runner = worker.protocol_runner_factory(worker, new_run, new_snapshot)
    with pytest.raises(DomainError):
        runner.call([{"role": "user", "content": "second"}], [])
    assert not requests
    with store.engine.connect() as c:
        assert len(c.execute(select(attempts)).all()) == 1


@pytest.mark.parametrize("field", ["fence", "phase", "reserved_tokens", "token_limit"])
def test_fixed_slot_and_pool_policy_tamper_rejects_direct_reservation(env, field):
    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    factory_for(env, [wire({"summary": "known"})], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    runner.call([{"role": "user", "content": "first"}], [])
    with store.tx() as c:
        if field == "token_limit":
            c.execute(update(pools).where(pools.c.id == OFFLINE_POOL).values(token_limit=999999))
        else:
            values = {"fence": 999, "phase": "unrelated", "reserved_tokens": 1}
            c.execute(update(slots).values(**{field: values[field]}))
            if field == "reserved_tokens":
                c.execute(update(pools).where(pools.c.id == OFFLINE_POOL).values(reserved_tokens=1))
        c.execute(update(runs).where(runs.c.id == run["id"]).values(status="PAUSED", lease_until=0))
    _, other, other_snapshot = claimed_source(env, "other")
    with pytest.raises(DomainError):
        worker.reserve(
            other["id"], other["fence"], copy.deepcopy(other["context"]), request_tools=[]
        )
    with store.engine.connect() as c:
        assert len(c.execute(select(attempts)).all()) == 1


def test_actual_unknown_usage_globally_blocks_new_run_and_keeps_both_records(env):
    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    raw = wire({"summary": "unknown usage"})
    raw.pop("usage")
    requests = factory_for(env, [raw], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    with pytest.raises(DomainError):
        runner.call([{"role": "user", "content": "first"}], [])
    assert len(requests) == 1
    state = inspect_pool(store, OFFLINE_POOL)
    assert state["halted"] and state["has_unknown"] and state["reserved_requests"] == 1
    with store.tx() as c:
        assert c.execute(select(slots.c.status)).scalar_one() == "UNKNOWN"
        assert c.execute(select(attempts.c.status)).scalar_one() == "FAILED"
        c.execute(
            update(runs)
            .where(runs.c.id == run["id"])
            .values(status="WAITING_RESOURCE", lease_until=0)
        )
    _, other, other_snapshot = claimed_source(env, "other")
    requests = factory_for(env, [wire({"summary": "no extra send"})], "source_a")
    runner = worker.protocol_runner_factory(worker, other, other_snapshot)
    with pytest.raises(DomainError):
        runner.call([{"role": "user", "content": "second"}], [])
    assert not requests
    assert inspect_pool(store, OFFLINE_POOL)["reserved_requests"] == 1


def test_interruption_after_atomic_reservation_preserves_started_and_halts(env, monkeypatch):
    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    requests = factory_for(env, [], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)

    def crash(*args):
        raise KeyboardInterrupt("synthetic crash after DB reservation")

    monkeypatch.setattr(runner.provider, "call", crash)
    with pytest.raises(KeyboardInterrupt):
        runner.call([{"role": "user", "content": "first"}], [])
    assert not requests
    state = inspect_pool(store, OFFLINE_POOL)
    assert state["halted"] and state["has_pending"] and state["reserved_requests"] == 1
    with store.engine.connect() as c:
        assert c.execute(select(attempts.c.status)).scalar_one() == "STARTED"
        assert c.execute(select(slots.c.status)).scalar_one() == "STARTED"


def test_actual_known_token_overrun_preserved_without_clamp_and_halts_budget(env):
    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    raw = wire({"summary": "known excessive usage"})
    raw["usage"] = {"prompt_tokens": 99990, "completion_tokens": 10, "total_tokens": 100000}
    requests = factory_for(env, [raw], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    with pytest.raises(DomainError) as raised:
        runner.call([{"role": "user", "content": "known overrun"}], [])
    assert raised.value.code == "BUDGET_EXHAUSTED" and len(requests) == 1
    summary = inspect_pool(store, OFFLINE_POOL)
    assert summary["known_tokens"] == 100000 and summary["halted"] is True
    assert summary["halt_reason"] == "BUDGET_EXHAUSTED" and summary["has_unknown"] is False
    with store.tx() as c:
        assert c.execute(select(slots.c.usage)).scalar_one()["tokens"]["total_tokens"] == 100000
        assert c.execute(select(attempts.c.usage)).scalar_one()["tokens"]["total_tokens"] == 100000
    with pytest.raises(DomainError) as raised:
        require_pool(store, OFFLINE_POOL)
    assert raised.value.code == "BUDGET_EXHAUSTED"
    # Clearing a mutable flag cannot make immutable known expenditure disappear.
    with store.tx() as c:
        c.execute(
            update(pools).where(pools.c.id == OFFLINE_POOL).values(halted=False, halt_reason=None)
        )
        c.execute(update(runs).where(runs.c.id == run["id"]).values(status="PAUSED", lease_until=0))
    _, other, other_snapshot = claimed_source(env, "other")
    requests = factory_for(env, [wire({"summary": "forbidden additional cost"})], "source_a")
    runner = worker.protocol_runner_factory(worker, other, other_snapshot)
    with pytest.raises(DomainError) as raised:
        runner.call([{"role": "user", "content": "cannot refill actual overrun"}], [])
    assert raised.value.code == "BUDGET_EXHAUSTED" and not requests


def test_sticky_unknown_observation_cannot_be_cleared_after_origin_settles(env):
    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    aid = worker.reserve(run["id"], run["fence"], copy.deepcopy(run["context"]), request_tools=[])
    with pytest.raises(DomainError):
        require_pool(store, OFFLINE_POOL)
    factory_for(env, [], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    runner._record(aid, wire({"summary": "late but same fenced origin response"}), 0, "RECEIVED")
    with store.tx() as c:
        c.execute(
            update(pools).where(pools.c.id == OFFLINE_POOL).values(halted=False, halt_reason=None)
        )
        c.execute(update(runs).where(runs.c.id == run["id"]).values(status="PAUSED", lease_until=0))
    summary = inspect_pool(store, OFFLINE_POOL)
    assert summary["halted"] and not summary["has_pending"] and not summary["has_unknown"]
    _, other, other_snapshot = claimed_source(env, "other")
    requests = factory_for(
        env, [wire({"summary": "cannot resume shared stop by clearing flags"})], "source_a"
    )
    runner = worker.protocol_runner_factory(worker, other, other_snapshot)
    with pytest.raises(DomainError):
        runner.call([{"role": "user", "content": "second"}], [])
    assert not requests and inspect_pool(store, OFFLINE_POOL)["reserved_requests"] == 1


@pytest.mark.parametrize("malformed", [None, {}, {"total_tokens": False}])
def test_malformed_stored_known_usage_is_controlled_and_sticky_halts(env, malformed):
    store, user, pid, a, b, worker, tmp = env
    _, run, snapshot = claimed_source(env)
    requests = factory_for(env, [wire({"summary": "known response"})], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    runner.call([{"role": "user", "content": "first"}], [])
    assert len(requests) == 1
    with store.tx() as c:
        c.execute(update(slots).values(usage={"status": "known", "tokens": malformed}))
    with pytest.raises(DomainError) as raised:
        require_pool(store, OFFLINE_POOL)
    assert raised.value.code == "OUTCOME_UNKNOWN"
    with store.engine.connect() as c:
        assert (
            c.execute(select(pools.c.halted).where(pools.c.id == OFFLINE_POOL)).scalar_one() is True
        )
    with pytest.raises(DomainError):
        runner.call([{"role": "user", "content": "cannot send"}], [])
    assert len(requests) == 1
