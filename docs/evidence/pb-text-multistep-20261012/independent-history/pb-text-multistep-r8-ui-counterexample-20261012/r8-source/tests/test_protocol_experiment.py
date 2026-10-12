"""Persistent offline experiment timing hooks use actual slot/Attempt transactions."""

import copy

import pytest
from sqlalchemy import select, update
from test_protocol_jobs import LIMITS, factory_for, source_payload, wire
from test_protocol_jobs import env as _jobs_env

from sim2act.db import Store, events, protocol_jobs, runs
from sim2act.db import protocol_request_slots as slots
from sim2act.errors import DomainError
from sim2act.protocol_experiment import (
    BINDING,
    SEND,
    SETTLED,
    advance,
    bind_run,
    initialize_experiment,
    inspect_experiment,
    preflight,
    reserve_in_tx,
    settle_in_tx,
)
from sim2act.protocol_jobs import enqueue

env = _jobs_env


@pytest.fixture
def wired(env, monkeypatch):
    """Exercise same-tx hooks before root integration; avoid duplicating integrated hooks."""
    import sim2act.protocol_pool as pool

    store, user, pid, a, b, worker, tmp = env
    ticks = [1000.0]
    worker.protocol_clock = lambda: ticks[0]
    reserve, settle = pool.reserve_slot, pool.finish_slot

    def reserve_hook(store, c, run, fence, aid, *args, **kwargs):
        result = reserve(store, c, run, fence, aid, *args, **kwargs)
        if not c.execute(
            select(events.c.id).where(events.c.run_id == aid, events.c.kind == SEND)
        ).first():
            reserve_in_tx(store, c, run, fence, aid, clock=lambda: ticks[0])
        return result

    def settle_hook(store, c, run, fence, aid, *args, **kwargs):
        result = settle(store, c, run, fence, aid, *args, **kwargs)
        if not c.execute(
            select(events.c.id).where(events.c.run_id == aid, events.c.kind == SETTLED)
        ).first():
            settle_in_tx(store, c, run, fence, aid, clock=lambda: ticks[0])
        return result

    monkeypatch.setattr(pool, "reserve_slot", reserve_hook)
    monkeypatch.setattr(pool, "finish_slot", settle_hook)
    experiment = initialize_experiment(store, user, pid, "test-experiment", request_limit=14)
    accepted = enqueue(store, user, pid, "source", source_payload(a), "source", LIMITS)
    bind_run(store, user, experiment["experiment_id"], accepted["run_id"], clock=lambda: ticks[0])
    run = store.claim(worker.id, worker.s.lease_seconds)
    with store.tx() as c:
        snapshot = c.execute(
            select(protocol_jobs.c.accepted_snapshot).where(protocol_jobs.c.run_id == run["id"])
        ).scalar_one()
    factory_for(env, [], "source_a")
    runner = worker.protocol_runner_factory(worker, run, snapshot)
    return env, ticks, experiment["experiment_id"], run, runner


def reserve(wired):
    env, ticks, eid, run, runner = wired
    store, user, pid, a, b, worker, tmp = env
    with store.tx() as c:
        context = copy.deepcopy(
            c.execute(select(runs.c.context).where(runs.c.id == run["id"])).scalar_one()
        )
    return worker.reserve(run["id"], run["fence"], context, request_tools=[])


def settle(wired, aid, raw=None):
    env, ticks, eid, run, runner = wired
    runner._record(aid, wire({"public": "synthetic"}) if raw is None else raw, 0, "RECEIVED")


def test_default_zero_and_explicit_identity_cannot_refill_or_change_owner(env):
    store, user, pid, a, b, worker, tmp = env
    policy = initialize_experiment(store, user, pid, "disabled")
    assert policy["request_limit"] == 0 and policy["live_enabled"] is False
    assert initialize_experiment(store, user, pid, "disabled") == policy
    with pytest.raises(DomainError):
        initialize_experiment(store, user, pid, "disabled", request_limit=14)
    other = store.user("other", "other-token")
    with pytest.raises(DomainError):
        inspect_experiment(store, other, policy["experiment_id"])


def test_persistent_global_spacing_known_calls_and_restart(wired):
    env, ticks, eid, run, runner = wired
    store, user, *_ = env
    aid = reserve(wired)
    settle(wired, aid)
    with pytest.raises(DomainError) as raised:
        reserve(wired)
    assert raised.value.code == "RATE_LIMITED"
    ticks[0] += 6
    second = reserve(wired)
    settle(wired, second)
    reopened = Store(str(store.engine.url), test_only=True)
    reopened.engine = store.engine  # Preserve isolated PG schema routing; no initialize/reset.
    assert inspect_experiment(reopened, user, eid)["requests"] == 2
    assert inspect_experiment(reopened, user, eid)["settled"] == 2
    ticks[0] += 6
    third = reserve(wired)
    settle(wired, third)
    ticks[0] += 6
    with pytest.raises(DomainError):
        reserve(wired)
    assert inspect_experiment(store, user, eid)["requests"] == 3


@pytest.mark.parametrize("time", [999.0, 1301.0])
def test_clock_rollback_or_stage_timeout_stops_persistently_before_send(wired, time):
    env, ticks, eid, run, runner = wired
    ticks[0] = time
    with pytest.raises(DomainError):
        preflight(env[0], env[1], run["id"], clock=lambda: ticks[0])
    assert inspect_experiment(env[0], env[1], eid)["status"] == "STOPPED"
    assert inspect_experiment(env[0], env[1], eid)["requests"] == 0
    ticks[0] = 1010
    with pytest.raises(DomainError):
        reserve(wired)


def test_started_crash_survives_new_store_and_stops_globally(wired):
    env, ticks, eid, run, runner = wired
    aid = reserve(wired)  # Committed STARTED, no transport call or fabricated outcome.
    ticks[0] += 7
    with pytest.raises(DomainError) as raised:
        preflight(env[0], env[1], run["id"], clock=lambda: ticks[0])
    assert raised.value.code == "OUTCOME_UNKNOWN"
    summary = inspect_experiment(env[0], env[1], eid)
    assert summary["status"] == "STOPPED" and summary["requests"] == 1
    with env[0].tx() as c:
        assert (
            c.execute(select(slots.c.status).where(slots.c.attempt_id == aid)).scalar_one()
            == "STARTED"
        )
    with pytest.raises(DomainError):
        reserve(wired)


def test_known_failure_stops_without_falsifying_usage_unknown(wired):
    env, ticks, eid, run, runner = wired
    aid = reserve(wired)
    runner._record(aid, wire({"public": "known failure"}), 0, "FAILED")
    summary = inspect_experiment(env[0], env[1], eid)
    assert summary["status"] == "STOPPED" and summary["settled"] == 1
    with env[0].tx() as c:
        assert (
            c.execute(select(slots.c.usage).where(slots.c.attempt_id == aid)).scalar_one()["status"]
            == "known"
        )


def test_unreviewed_source_cannot_advance_or_bind_extract(wired):
    env, ticks, eid, run, runner = wired
    with pytest.raises(DomainError):
        advance(env[0], env[1], eid, run["id"], clock=lambda: ticks[0])
    assert inspect_experiment(env[0], env[1], eid)["accepted_stages"] == 0


def test_tampered_one_binding_seal_rejected(wired):
    env, ticks, eid, run, runner = wired
    with env[0].tx() as c:
        c.execute(
            update(events)
            .where(events.c.run_id == run["id"], events.c.kind == BINDING)
            .values(data={"value": {}, "fingerprint": "0" * 64})
        )
    with pytest.raises(DomainError):
        reserve(wired)


@pytest.mark.parametrize("wrong_source", [False, True])
def test_two_forms_real_worker_review_sequence_global_clock_and_shared_pool(wired, wrong_source):
    import json
    from pathlib import Path

    from sim2act.protocol_jobs import inspect, process_job
    from sim2act.protocol_readiness import candidate_for
    from sim2act.protocol_reviews import contract_snapshot, evaluation_contract, review

    env, ticks, eid, first, first_adapter = wired
    store, user, pid, a, b, worker, tmp = env
    material_root = (
        Path(__file__).parents[1] / "docs/evidence/model-protocol-preparation-20261006/materials"
    )
    refs = {"a-source": [a], "a-cold": [b]}
    for package in ("b-source", "b-cold"):
        refs[package] = [
            store.resource(
                user, pid, package + name, "txt", (material_root / package / name).read_text()
            )
            for name in ("request.txt", "rules.txt")
        ]
    seen = []

    def execute(run, stage, replies):
        requests = factory_for(env, replies, stage)
        factory = worker.protocol_runner_factory

        def timed_factory(worker, run, snapshot):
            if run["id"] == first["id"]:
                import httpx

                adapter = first_adapter  # Reuse existing unsent ledger, never reset it.
                pending = list(replies)

                def original(request):
                    requests.append(json.loads(request.content))
                    return httpx.Response(200, json=pending.pop(0))
            else:
                adapter = factory(worker, run, snapshot)
                original = adapter.provider.model.transport.handler
            transport = adapter.provider.model.transport

            def response(request):
                result = original(request)
                ticks[0] += 7  # Explicit synthetic server clock, shared across all six jobs.
                return result

            transport.handler = response
            original_call = adapter.call

            def scheduled_call(messages, tools):
                ticks[0] += 7  # Conservative six seconds AFTER prior settlement.
                return original_call(messages, tools)

            adapter.call = scheduled_call
            return adapter

        worker.protocol_runner_factory = timed_factory
        process_job(worker, run)
        seen.extend(requests)
        return inspect(store, user, run["id"])

    def accepted(rid, result, contract_id):
        decision = review(
            store,
            user,
            rid,
            {
                "contract_id": contract_id,
                "expected_result_fingerprint": result["result_fingerprint"],
                "expected_fence": result["fence"],
                "expected_version": result["version"],
                "request_key": "accept-" + rid,
            },
        )
        assert decision["decision"] == "PASS"
        advance(store, user, eid, rid, clock=lambda: ticks[0])
        return inspect(store, user, rid)

    def queued(phase, payload, key):
        rid = enqueue(store, user, pid, phase, payload, key, LIMITS)["run_id"]
        bind_run(store, user, eid, rid, clock=lambda: ticks[0])
        claimed = store.claim(worker.id, worker.s.lease_seconds)
        assert claimed["id"] == rid
        return claimed

    for family in ("a", "b"):
        source_id = f"protocol.synthetic.{family}-source.v1"
        cold_id = f"protocol.synthetic.{family}-cold.v1"
        contract = evaluation_contract(source_id)[0]
        source = (
            first
            if family == "a"
            else queued(
                "source",
                {
                    "contract_id": source_id,
                    "goal": contract["public_goal"],
                    "inputs": contract["expected_inputs"],
                    "resource_ids": refs[family + "-source"],
                },
                "source-b",
            )
        )
        read = wire(rid=refs[family + "-source"][0])
        read["choices"][0]["message"]["tool_calls"] = [
            {
                "id": "read-" + str(i),
                "type": "function",
                "function": {
                    "name": "resource.read",
                    "arguments": json.dumps({"resource_id": rid}),
                },
            }
            for i, rid in enumerate(refs[family + "-source"])
        ]
        result = execute(
            source,
            "source_" + family,
            [read, wire({"wrong": True} if wrong_source else contract["expected_output"])],
        )
        assert result["status"] == "WAITING_APPROVAL", result
        if wrong_source:
            verdict = review(
                store,
                user,
                source["id"],
                {
                    "contract_id": source_id,
                    "expected_result_fingerprint": result["result_fingerprint"],
                    "expected_fence": result["fence"],
                    "expected_version": result["version"],
                    "request_key": "fail-review",
                },
            )
            assert verdict["decision"] == "FAIL"
            with pytest.raises(DomainError):
                advance(store, user, eid, source["id"], clock=lambda: ticks[0])
            assert inspect_experiment(store, user, eid)["status"] == "STOPPED"
            assert inspect_experiment(store, user, eid)["requests"] == 2
            return
        source_result = accepted(source["id"], result, source_id)
        extraction = queued(
            "extract",
            {
                "source_run_id": source["id"],
                "expected_source_fingerprint": source_result["result_fingerprint"],
            },
            "extract-" + family,
        )
        extracted = execute(
            extraction,
            "extract_" + family,
            [wire(candidate_for(contract_snapshot(source_id), refs[family + "-source"]))],
        )
        assert extracted["status"] == "SUCCEEDED"
        advance(store, user, eid, extraction["id"], clock=lambda: ticks[0])
        plan = extracted["result"]["compiled_plan"]
        cold_contract = evaluation_contract(cold_id)[0]
        cold = queued(
            "cold",
            {
                "extraction_run_id": extraction["id"],
                "expected_plan_fingerprint": plan["plan_fingerprint"],
                "inputs": cold_contract["expected_inputs"],
                "resource_bindings": {
                    f"material_{i}": rid for i, rid in enumerate(refs[family + "-cold"])
                },
                "contract_id": cold_id,
            },
            "cold-" + family,
        )
        pending = execute(cold, "cold_" + family, [wire(cold_contract["expected_output"])])
        assert pending["status"] == "WAITING_APPROVAL"
        accepted(cold["id"], pending, cold_id)
    summary = inspect_experiment(store, user, eid)
    assert summary["status"] == "COMPLETED" and summary["accepted_stages"] == 6
    assert summary["requests"] == summary["settled"] == len(seen) == 8


def test_reserve_delay_uses_settlement_clock_for_next_send(wired):
    from sim2act.protocol_experiment import validate_dispatch_in_tx

    env, ticks, eid, run, runner = wired
    aid = reserve(wired)
    ticks[0] += 5
    with env[0].tx() as c:
        env[0].lock_project(c, env[1], env[2])
        env[0].guard(c, run["id"], run["fence"])
        assert validate_dispatch_in_tx(env[0], c, run, run["fence"], clock=lambda: ticks[0]) == aid
    settle(wired, aid)
    ticks[0] += 1  # reserve+6, but only settle+1: must still refuse.
    with pytest.raises(DomainError) as raised:
        reserve(wired)
    assert raised.value.code == "RATE_LIMITED"
    ticks[0] += 5
    assert reserve(wired) != aid


def test_actual_dispatch_checks_deadline_after_committed_reservation(wired):
    from sim2act.protocol_experiment import validate_dispatch_in_tx

    env, ticks, eid, run, runner = wired
    aid = reserve(wired)
    ticks[0] = 1301
    with pytest.raises(DomainError) as raised:
        with env[0].tx() as c:
            env[0].lock_project(c, env[1], env[2])
            env[0].guard(c, run["id"], run["fence"])
            validate_dispatch_in_tx(env[0], c, run, run["fence"], clock=lambda: ticks[0])
    assert raised.value.code == "BUDGET_EXHAUSTED"
    with env[0].tx() as c:
        assert (
            c.execute(select(slots.c.status).where(slots.c.attempt_id == aid)).scalar_one()
            == "STARTED"
        )


def test_deleted_send_and_attempt_mirror_cannot_reset_stage_count(wired):
    from sqlalchemy import delete

    env, ticks, eid, run, runner = wired
    aid = reserve(wired)
    settle(wired, aid)
    with env[0].tx() as c:
        c.execute(delete(events).where(events.c.run_id.in_([eid, aid]), events.c.kind == SEND))
    ticks[0] += 7
    with pytest.raises(DomainError):
        reserve(wired)


def test_actual_db_thread_race_reserves_only_one_origin(wired):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait(timeout=10)
        try:
            return reserve(wired)
        except DomainError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: attempt(), range(2)))
    assert sum(v.startswith("attempt_") for v in results) == 1
    assert inspect_experiment(wired[0][0], wired[0][1], wired[2])["requests"] == 1


def test_deleted_forward_binding_typed_rejection_persists_stop_and_no_send(wired):
    from sqlalchemy import delete

    from sim2act.protocol_experiment import BOUND

    env, ticks, eid, run, runner = wired
    with env[0].tx() as c:
        c.execute(delete(events).where(events.c.run_id == eid, events.c.kind == BOUND))
    with pytest.raises(DomainError) as raised:
        preflight(env[0], env[1], run["id"], clock=lambda: ticks[0])
    assert raised.value.code == "VERSION_CONFLICT"
    with env[0].tx() as c:
        assert c.execute(
            select(events.c.id).where(
                events.c.run_id == eid, events.c.kind == "PROTOCOL_EXPERIMENT_STOPPED"
            )
        ).first()
        assert not c.execute(select(slots.c.attempt_id)).first()


def test_origin_forward_traces_prevent_experiment_namespace_fallback(wired):
    from sqlalchemy import delete

    from sim2act.protocol_experiment import GENESIS, is_experiment_run
    from sim2act.protocol_pool import OFFLINE_POOL

    env, ticks, eid, run, runner = wired
    with env[0].tx() as c:
        c.execute(
            delete(events).where((events.c.run_id == OFFLINE_POOL) & (events.c.kind == GENESIS))
        )
        c.execute(delete(events).where((events.c.run_id == run["id"]) & (events.c.kind == BINDING)))
        assert is_experiment_run(c, run["id"]) is True
    with pytest.raises(DomainError):
        initialize_experiment(env[0], env[1], env[2], "cannot-refill-orphan", request_limit=14)
    with pytest.raises(DomainError):
        reserve(wired)  # Actual Worker gate; not a direct verifier stand-in.
    with env[0].tx() as c:
        assert not c.execute(select(slots.c.attempt_id)).first()
