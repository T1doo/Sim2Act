"""Accounting primitives only; no provider, transport, LIVE approval or fee proof."""

import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from sqlalchemy import select, update

from sim2act import natural_trial_budget as budget
from sim2act.contracts import Strict
from sim2act.db import Store, delivery_graph_requests, fingerprint, projects, runs
from sim2act.errors import DomainError


class SyntheticContract(Strict):
    trial_key: str
    project_id: str
    principal_id: str
    runtime_id: str
    quota_subject: str
    expires_at: float
    caps: dict


def admitted(*args):
    return SimpleNamespace(scope="SYNTHETIC_ONLY", live_allowed=False,
        contract_fingerprint=fingerprint(args[3].model_dump()), stage=args[5],
        run_id=args[6], run_version=args[7], fence=args[8], expires_at=args[3].expires_at,
        runtime_id=args[3].runtime_id,
        stage_authority_fingerprint=None if args[5] == "generate" else "1" * 64)


@pytest.fixture
def trial(env):
    store, settings, client, user, other, pid, resource = env
    with store.tx() as c:
        runtime = c.execute(select(projects.c.runtime_id).where(projects.c.id == pid)).scalar_one()
    contract = SyntheticContract(trial_key="trial", project_id=pid, principal_id=user,
        runtime_id=runtime, quota_subject="synthetic-account-" + pid,
        expires_at=time.time() + 1200,
        caps=dict(generate_requests=3, source_requests=2, cold_requests=2, max_requests=7,
                  max_output_tokens=1024, max_wire_bytes=32768, max_response_ascii_bytes=32768,
                  per_run_reserved=64000, total_reserved=192000, total_output_tokens=7168,
                  run_seconds=300, lease_seconds=30, requests_per_minute=1, paid_cap=0))
    rid = store.submit(user, pid, "synthetic accounting only", [], "generate")
    run = store.claim("synthetic-worker", 30)
    assert run["id"] == rid
    request = budget.Reservation(request_key="r1", stage="generate", run_id=rid,
        expected_version=run["version"], fence=run["fence"], wire_sha256="a" * 64, wire_bytes=100)
    return store, user, other, contract, budget.scope_for(contract, "approval"), request


def reserve(t, request=None, *, store=None, admission=admitted):
    s, user, _, contract, scope, original = t
    return budget.reserve(store or s, user, scope, contract, request or original, admission=admission)


def settle(t, *, admission=admitted, **changes):
    s, user, _, contract, scope, request = t
    response = budget.Settlement(request_key=request.request_key, response_sha256="b" * 64,
        response_ascii_bytes=100, prompt_tokens=5, completion_tokens=3, total_tokens=8)
    return budget.settle(s, user, scope, contract, response.model_copy(update=changes), admission=admission)


def rejected(code, action):
    with pytest.raises(DomainError) as caught:
        action()
    assert caught.value.code == code


def test_duplicate_cold_restart_original_key_is_read_only_and_nonrefundable(trial):
    first = reserve(trial)
    assert first["usage_status"] == "UNKNOWN" and first["total_tokens"] is None
    assert first["reserved_envelope"] == 1124 and first["reserved_requests"] == 1
    second_store = Store(str(trial[0].engine.url), test_only=True)
    try:
        duplicate = reserve(trial, store=second_store)
        assert duplicate["duplicate"] and not duplicate["dispatch_authorized"]
        result = settle(trial)
        assert result["total_tokens"] == 8 and result["status"] == "ACCOUNTED"
        assert budget.read(second_store, trial[1], trial[4])["ledger"] == result["ledger"]
        assert settle(trial)["duplicate"]
        rejected("VERSION_CONFLICT", lambda: reserve(trial,
            trial[-1].model_copy(update={"wire_sha256": "c" * 64})))
        rejected("VERSION_CONFLICT", lambda: settle(trial, total_tokens=9))
    finally:
        second_store.engine.dispose()


def test_two_stores_concurrent_same_key_one_slot(trial):
    second = Store(str(trial[0].engine.url), test_only=True)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(reserve, trial, store=s) for s in (trial[0], second)]
            results = [f.result() for f in futures]
        assert sorted(x["duplicate"] for x in results) == [False, True]
        assert all(x["reserved_requests"] == 1 for x in results)
    finally:
        second.engine.dispose()


def test_two_stores_different_keys_unknown_first_blocks_second(trial):
    second = Store(str(trial[0].engine.url), test_only=True)
    def attempt(s, key):
        try:
            return reserve(trial, trial[-1].model_copy(update={"request_key": key}), store=s)
        except DomainError as exc:
            return exc.code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, s, k) for s, k in ((trial[0], "a"), (second, "b"))]
            actual = [f.result() for f in futures]
        assert sum(isinstance(x, dict) for x in actual) == 1 and "OUTCOME_UNKNOWN" in actual
        assert budget.read(trial[0], trial[1], trial[4])["reserved_requests"] == 1
    finally:
        second.engine.dispose()


@pytest.mark.parametrize("change,code", [({"fence": 2}, "VERSION_CONFLICT"),
    ({"expected_version": 2}, "VERSION_CONFLICT")])
def test_actual_run_version_fence_refusal_has_no_partial_ledger(trial, change, code):
    rejected(code, lambda: reserve(trial, trial[-1].model_copy(update=change)))
    with trial[0].tx() as c:
        assert not c.execute(select(delivery_graph_requests)).first()


@pytest.mark.parametrize("mode", ["denied", "expired", "cancel"])
def test_initial_denial_expiry_cancel_no_partial(trial, mode):
    store, user, _, contract, scope, request = trial
    if mode == "expired":
        contract = contract.model_copy(update={"expires_at": time.time() - 1})
        scope = budget.scope_for(contract, "approval")
    if mode == "cancel":
        store.command(user, request.run_id, "cancel", request.expected_version)
    def denied(*args):
        raise DomainError("PERMISSION_DENIED")
    with pytest.raises(DomainError):
        budget.reserve(store, user, scope, contract, request,
                       admission=denied if mode == "denied" else admitted)
    with store.tx() as c:
        assert not c.execute(select(delivery_graph_requests)).first()


@pytest.mark.parametrize("mode", ["cancel", "revoked", "version", "fence", "unknown", "overflow"])
def test_late_or_unknown_usage_retained_halted_no_refund(trial, mode):
    reserve(trial)
    store, user, _, _, scope, request = trial
    if mode == "cancel":
        store.command(user, request.run_id, "cancel", request.expected_version)
    elif mode in {"version", "fence"}:
        with store.tx() as c:
            c.execute(update(runs).where(runs.c.id == request.run_id)
                      .values(**{mode: 2}))
    def denied(*args):
        raise DomainError("PERMISSION_DENIED")
    changes = dict(prompt_tokens=None, completion_tokens=None, total_tokens=None) if mode == "unknown" else {}
    if mode == "overflow":
        changes = dict(response_ascii_bytes=32769, prompt_tokens=1000, completion_tokens=1025, total_tokens=2025)
    result = settle(trial, admission=denied if mode == "revoked" else admitted, **changes)
    assert result["status"] == ("RECONCILING" if mode == "unknown" else "HALTED")
    assert result["reserved_envelope"] == 1124
    assert result["reserved_requests"] == 1 and not result["ledger"]["slots"][0]["accepted"]
    assert result["total_tokens"] == (None if mode == "unknown" else 2025 if mode == "overflow" else 8)
    assert budget.read(store, user, scope)["ledger"] == result["ledger"]
    with pytest.raises(DomainError):
        reserve(trial, request.model_copy(update={"request_key": "new"}))


def test_quota_across_trials_real_rate_no_wait_or_partial(trial):
    reserve(trial)
    settle(trial)
    s, user, _, contract, _, req = trial
    contract = contract.model_copy(update={"trial_key": "explicit-new"})
    rejected("RATE_LIMITED", lambda: budget.reserve(s, user, budget.scope_for(contract, "new"),
        contract, req, admission=admitted))
    with s.tx() as c:
        assert not c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.request_key == "explicit-new")).first()


def test_corrupt_pair_and_nonowner_fail_closed(trial):
    reserve(trial)
    s, user, other, _, scope, _ = trial
    rejected("PERMISSION_DENIED", lambda: budget.read(s, other, scope))
    with s.tx() as c:
        c.execute(update(delivery_graph_requests).where(delivery_graph_requests.c.kind == budget.KIND)
                  .values(fingerprint="0" * 64))
    rejected("VERSION_CONFLICT", lambda: budget.read(s, user, scope))


def test_fixed_caps_cannot_expand(trial):
    contract = trial[3]
    for field in contract.caps:
        caps = {**contract.caps, field: contract.caps[field] + 1}
        rejected("BUDGET_EXHAUSTED", lambda caps=caps: budget.scope_for(
            contract.model_copy(update={"caps": caps}), "approval"))


def test_expiry_after_reserve_records_actual_late_usage(trial):
    s, user, _, contract, _, req = trial
    contract = contract.model_copy(update={"expires_at": time.time() + 0.2})
    scope = budget.scope_for(contract, "short")
    budget.reserve(s, user, scope, contract, req, admission=admitted)
    time.sleep(0.21)
    result = budget.settle(s, user, scope, contract,
        budget.Settlement(request_key=req.request_key, response_sha256="b" * 64,
            response_ascii_bytes=10, prompt_tokens=2, completion_tokens=3, total_tokens=5),
        admission=admitted)
    assert result["status"] == "HALTED" and result["total_tokens"] == 5
    assert result["reserved_requests"] == 1 and not result["dispatch_authorized"]


@pytest.mark.parametrize("pretend", [None, True, {"approved": True, "free": True}])
def test_untrusted_bool_or_dict_permit_has_no_ledger(trial, pretend):
    rejected("PERMISSION_DENIED", lambda: reserve(trial, admission=lambda *args: pretend))
    with trial[0].tx() as c:
        assert not c.execute(select(delivery_graph_requests)).first()


def test_role_cannot_bind_same_run_and_reserved_cap_is_atomic(trial):
    reserve(trial)
    settle(trial)
    rejected("VERSION_CONFLICT", lambda: reserve(trial,
        trial[-1].model_copy(update={"stage": "source", "request_key": "source"})))
    # Owned synthetic history at the original cap; no timer or lease changes.
    s, user, _, _, scope, req = trial
    with s.tx() as c:
        ledger = budget._ledger(c, scope)
        first = ledger["slots"][0]
        first["reservation"]["wire_bytes"] = 32768
        second = {**first, "reservation": {**first["reservation"],
            "request_key": "second", "wire_bytes": 29183},
            "settlement": {**first["settlement"], "request_key": "second"},
            "settlement_history": [{**first["settlement"], "request_key": "second"}]}
        ledger["slots"].append(second)
        budget._write(c, user, scope.project_id, budget.KIND, scope.trial_key,
                      scope.model_dump(), ledger)
    before = budget.read(s, user, scope)
    rejected("BUDGET_EXHAUSTED", lambda: reserve(trial,
        req.model_copy(update={"request_key": "third", "wire_bytes": 1})))
    assert budget.read(s, user, scope)["ledger"] == before["ledger"]


def test_unknown_original_response_usage_recovery_preserves_history_halt(trial):
    reserve(trial)
    initial = settle(trial, completion_tokens=None, total_tokens=None)
    assert initial["status"] == "RECONCILING" and initial["total_tokens"] is None
    recovered = settle(trial)
    slot = recovered["ledger"]["slots"][0]
    assert recovered["total_tokens"] == 8 and recovered["status"] == "HALTED"
    assert recovered["reserved_requests"] == 1 and recovered["reserved_envelope"] == 1124
    assert not slot["accepted"] and recovered["ledger"]["halted"]
    assert slot["settlement_history"] == [initial["ledger"]["slots"][0]["settlement"], slot["settlement"]]
    assert settle(trial)["duplicate"]
    assert budget.read(trial[0], trial[1], trial[4])["ledger"] == recovered["ledger"]
    rejected("OUTCOME_UNKNOWN", lambda: reserve(trial,
        trial[-1].model_copy(update={"request_key": "no-resend"})))


@pytest.mark.parametrize("changes", [{"response_sha256": "c" * 64},
    {"response_ascii_bytes": 101}, {"prompt_tokens": 6, "total_tokens": 9}])
def test_unknown_usage_recovery_wrong_original_proof_atomic(trial, changes):
    reserve(trial)
    settle(trial, completion_tokens=None, total_tokens=None)
    before = budget.read(trial[0], trial[1], trial[4])
    rejected("VERSION_CONFLICT", lambda: settle(trial, **changes))
    assert budget.read(trial[0], trial[1], trial[4])["ledger"] == before["ledger"]


def test_actual_admission_generate_worker_reservation_combination(env):
    """Root runs this after integrating both modules; no transport invocation."""
    import copy

    import httpx
    from test_natural_spec_apps import setup

    from sim2act import goal_applications
    from sim2act.db import events
    from sim2act.worker import Worker

    import test_natural_live_admission as helper

    from sim2act import natural_live_admission as gate

    data = setup(env)
    try:
        contract, body = helper.frozen(data, ttl=1200.0)
        gate.approve(data[0], data[3], contract, body)
        job = helper.started(data, contract)
        with data[0].tx() as c:
            frozen = data[0].frozen_contract(c, job)
            ctx = copy.deepcopy(job["context"])
            ctx["messages"] = goal_applications.initial_messages(data[0], c, job)
            tools = goal_applications.stage_tools(frozen.application_generation, 0)
        def never_send(request):
            raise AssertionError("Accounting combination must not invoke transport")
        worker = Worker(data[0], data[1], goal_planner_transport=httpx.MockTransport(never_send))
        # Use the actual claimant to retain the original ownership interval.
        worker.id = "synthetic-admission-worker"
        attempt_id = worker.reserve(job["id"], job["fence"], ctx,
            request_tools=tools, verify_goal_source=True, generation_request=True)
        with data[0].tx() as c:
            wire = c.execute(select(events.c.data).where(events.c.run_id == job["id"],
                events.c.kind == "GA_WIRE_RESERVED")).scalar_one()["wire"]
        fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)
        admission = partial(gate.admit, fee_authority=fee)
        scope = budget.scope_for(contract, body.request_key)
        request = budget.Reservation(request_key=attempt_id, stage="generate", run_id=job["id"],
            expected_version=job["version"], fence=job["fence"], wire_sha256=wire["sha256"],
            wire_bytes=wire["bytes"])
        result = budget.reserve(data[0], data[3], scope, contract, request, admission=admission)
        assert result["reserved_requests"] == 1 and result["reserved_envelope"] == wire["bytes"] + 1024
        assert result["total_tokens"] is None and not result["dispatch_authorized"]
        with data[0].tx() as c:
            permit = admission(data[0], c, data[3], contract, body.request_key, "generate",
                               job["id"], job["version"], job["fence"])
            assert permit.expires_at < scope.expires_at
            assert budget.audit(data[0], c, data[3], scope)["ledger"] == result["ledger"]
        data[0].command(data[3], job["id"], "cancel", job["version"])
        late = budget.settle(data[0], data[3], scope, contract,
            budget.Settlement(request_key=attempt_id, response_sha256="b" * 64,
                response_ascii_bytes=10, prompt_tokens=2, completion_tokens=3, total_tokens=5),
            admission=admission)
        assert late["status"] == "HALTED" and late["total_tokens"] == 5
        assert not late["ledger"]["slots"][0]["accepted"]
        assert budget.read(data[0], data[3], scope)["reserved_requests"] == 1
    finally:
        data[2].close()


def test_seven_actual_reservations_stage_binding_nontransfer_no_refund(trial):
    """Uses real 60s spacing and ordinary 30s heartbeats; no clock/lease patch."""
    store, user, _, contract, scope, first = trial
    last = None
    count = 0
    for stage, cap in budget.STAGES.items():
        request = first
        if stage != "generate":
            rid = store.submit(user, scope.project_id, "synthetic accounting only", [], stage)
            job = store.claim("worker-" + stage, 30)
            assert job["id"] == rid
            request = first.model_copy(update={"run_id": rid, "stage": stage,
                "fence": job["fence"], "expected_version": job["version"]})
        stopped = Event()
        failures = []
        with store.tx() as c:
            deadline = c.execute(select(runs.c.created_at).where(
                runs.c.id == request.run_id)).scalar_one() + 300
        def heartbeat(stopped=stopped, stage=stage, request=request,
                      deadline=deadline, failures=failures):
            while not stopped.wait(10):
                try:
                    store.heartbeat("synthetic-worker" if stage == "generate" else "worker-" + stage,
                        request.run_id, request.fence,
                        lease_seconds=30, _deadline=deadline,
                        _running_only=True)
                except BaseException as exc:
                    failures.append(exc)
                    return
        thread = Thread(target=heartbeat)
        thread.start()
        try:
            for _index in range(cap):
                if last is not None:
                    delay = 60.05 - (time.time() - last)
                    if delay > 0:
                        time.sleep(delay)
                assert not failures
                count += 1
                req = request.model_copy(update={"request_key": "slot" + str(count)})
                current = budget.reserve(store, user, scope, contract, req, admission=admitted)
                last = current["ledger"]["last_reserved_at"]
                result = budget.settle(store, user, scope, contract,
                    budget.Settlement(request_key=req.request_key, response_sha256="b" * 64,
                        response_ascii_bytes=10, prompt_tokens=1, completion_tokens=1, total_tokens=2),
                    admission=admitted)
            rejected("BUDGET_EXHAUSTED", lambda req=req, stage=stage: budget.reserve(store, user, scope, contract,
                req.model_copy(update={"request_key": "overflow-" + stage}), admission=admitted))
            store.command(user, request.run_id, "cancel", request.expected_version)
        finally:
            stopped.set()
            thread.join(timeout=5)
        assert not failures
    assert result["reserved_requests"] == 7 and result["reserved_envelope"] == 7868
    assert result["total_tokens"] == 14 and result["usage_status"] == "KNOWN"
    assert budget.read(store, user, scope)["reserved_requests"] == 7
