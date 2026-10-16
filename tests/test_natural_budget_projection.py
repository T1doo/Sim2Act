"""Existing finite trial gate and read-only accounting; no sender or qualification bypass.

Concurrency/cross-Run tests explicitly use the existing synthetic ledger stub,
controlled fixture clock and real SQLite Stores. They are not natural execution.
"""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Event

import pytest
from test_natural_live_admission import frozen, records, started
from test_natural_spec_apps import recipe, setup
from test_natural_trial_budget import admitted
from test_natural_trial_budget import trial as trial

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as budget
from sim2act.db import Store, fingerprint
from sim2act.errors import DomainError


def settlement(request, **changes):
    return budget.Settlement(request_key=request.request_key, response_sha256="b" * 64,
        response_ascii_bytes=10, prompt_tokens=5, completion_tokens=3, total_tokens=8, **changes)


def save(tmp_path, name, **proof):
    (tmp_path / (name + ".json")).write_text(json.dumps(proof, indent=2) + "\n")


@pytest.mark.parametrize("outcome", ["pending", "unknown", "rejected", "overflow"])
def test_actual_read_projection_preserves_every_held_slot(trial, tmp_path, outcome):
    store, user, _, contract, scope, request = trial
    initial = budget.reserve(store, user, scope, contract, request, admission=admitted)
    result = initial
    if outcome != "pending":
        raw = settlement(request).model_dump()
        if outcome == "unknown":
            raw.update(completion_tokens=None, total_tokens=None)
        if outcome == "overflow":
            raw.update(prompt_tokens=1000, completion_tokens=1025, total_tokens=2025)

        def denied(*args):
            raise DomainError("PERMISSION_DENIED", "Synthetic failed response cannot be accepted")

        result = budget.settle(store, user, scope, contract, raw,
                               admission=denied if outcome == "rejected" else admitted)
    projected = result["budget_projection"]
    assert projected["held_requests"] == 1 and projected["held_token_envelope"] == 1124
    assert projected["unreserved_request_capacity"] == 6
    assert projected["money"] == dict(paid_cap=0, actual_paid=None, currency=None,
        status="UNKNOWN", fee_verification="NOT_LIVE_VERIFIED", live_allowed=False)
    unknown = outcome in {"pending", "unknown"}
    assert projected["unresolved_usage_requests"] == int(unknown)
    assert result["total_tokens"] == (None if unknown else 8 if outcome == "rejected" else 2025)
    assert projected["known_unaccepted_tokens"] == (0 if unknown else result["total_tokens"])
    before = records(store)
    cold = Store(str(store.engine.url), test_only=True)
    try:
        recovered = budget.read(cold, user, scope)
        assert recovered["budget_projection"] == projected and records(store) == before
        duplicate = budget.reserve(cold, user, scope, contract, request, admission=lambda *a: pytest.fail("History cannot re-admit"))
        assert duplicate["duplicate"] and not duplicate["dispatch_authorized"]
        assert duplicate["budget_projection"] == projected and records(store) == before
    finally:
        cold.engine.dispose()
    save(tmp_path, "PROJECTION", kind="SYNTHETIC_LEDGER_PRIMITIVE", outcome=outcome,
         initial=initial, result=result, cold_rows_unchanged=True, transport_calls=0)


def advance(clock, store, job, target):
    while clock[0] < target:
        clock[0] = min(target, clock[0] + 10)
        store.heartbeat(job["worker_id"], job["id"], job["fence"], 30,
                        _deadline=job["created_at"] + 300, _running_only=True)


@pytest.mark.parametrize("boundary", ["requests", "tokens"])
def test_two_sqlite_stores_compete_for_last_finite_capacity(trial, monkeypatch, tmp_path, boundary):
    store, user, _, contract, scope, original = trial
    clock = [time.time()]
    monkeypatch.setattr(time, "time", lambda: clock[0])  # Synthetic fixture clock only.
    with store.tx() as c:
        job = dict(store.guard(c, original.run_id, original.fence))
    for index in range(2 if boundary == "requests" else 1):
        if index:
            advance(clock, store, job, clock[0] + 61)
        request = original.model_copy(update=dict(request_key="existing-" + str(index),
            wire_bytes=100 if boundary == "requests" else 32768))
        budget.reserve(store, user, scope, contract, request, admission=admitted)
        budget.settle(store, user, scope, contract, settlement(request), admission=admitted)
    advance(clock, store, job, clock[0] + 61)
    before = budget.read(store, user, scope)
    second = Store(str(store.engine.url), test_only=True)
    go, ready = Event(), [Event(), Event()]

    def contender(connection_store, number):
        ready[number].set()
        assert go.wait(5)
        request = original.model_copy(update=dict(request_key="contender-" + str(number),
            wire_bytes=100 if boundary == "requests" else 20000))
        try:
            with connection_store.tx() as c:
                budget._reserve(connection_store, c, user, scope, contract, request, admission=admitted)
                # Fixed synthetic usage in the same controller transaction, no IO.
                return budget._settle(connection_store, c, user, scope, contract,
                                      settlement(request), admission=admitted)
        except DomainError as error:
            return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(contender, s, i) for i, s in enumerate((store, second))]
            assert all(event.wait(5) for event in ready)
            go.set()
            results = [future.result(timeout=15) for future in futures]
        assert sum(isinstance(value, dict) for value in results) == 1
        assert "BUDGET_EXHAUSTED" in results
        after = budget.read(store, user, scope)
        assert after["reserved_requests"] == before["reserved_requests"] + 1
        assert after["budget_projection"]["held_token_envelope"] <= 64000
        assert after["budget_projection"]["money"]["actual_paid"] is None
        save(tmp_path, "CAPACITY_RACE", kind="SYNTHETIC_LEDGER_PRIMITIVE_CONTROLLED_CLOCK",
             boundary=boundary, before=before, after=after, contenders=results, transport_calls=0)
    finally:
        go.set()
        second.engine.dispose()


def test_same_trial_projection_never_resets_between_three_runs(trial, monkeypatch, tmp_path):
    store, user, _, contract, scope, original = trial
    clock = [time.time()]
    monkeypatch.setattr(time, "time", lambda: clock[0])  # No real waiting or provider.
    requests = []
    for index, stage in enumerate(("generate", "source", "cold")):
        if index:
            clock[0] += 61
            rid = store.submit(user, scope.project_id, "synthetic ledger role", [], stage)
            job = store.claim("synthetic-" + stage, 30)
            assert job["id"] == rid
            request = original.model_copy(update=dict(run_id=rid, stage=stage,
                request_key=stage, expected_version=job["version"], fence=job["fence"]))
        else:
            request = original
        requests.append(request)
        budget.reserve(store, user, scope, contract, request, admission=admitted)
        result = budget.settle(store, user, scope, contract, settlement(request), admission=admitted)
        store.command(user, request.run_id, "cancel", request.expected_version)
    projected = result["budget_projection"]
    assert len({request.run_id for request in requests}) == 3
    assert projected["held_requests"] == 3 and projected["held_token_envelope"] == 3372
    assert projected["unreserved_request_capacity"] == 4 and result["total_tokens"] == 24
    assert {s["run_id"] for s in projected["stages"].values()} == {r.run_id for r in requests}
    save(tmp_path, "CROSS_RUN", kind="SYNTHETIC_LEDGER_PRIMITIVE_CONTROLLED_CLOCK",
         contract=contract.model_dump(), result=result, transport_calls=0)


def exact_contract(data, family):
    contract, approval = frozen(data)
    if family == "P-B":
        contract = gate.PBTrialContract(**contract.model_dump(), path="P-B",
            extraction_request_key="exact-pb-extraction", extraction_recipe=recipe("parallel"))
        approval = approval.model_copy(update={"expected_contract_fingerprint": fingerprint(contract.model_dump())})
    return contract, approval


@pytest.mark.parametrize("family", ["P-A", "P-B"])
def test_real_natural_budget_http_projection_and_duplicate_are_read_only(env, tmp_path, family):
    data = setup(env)
    store, _, client, user, *_ = data
    try:
        contract, approval = exact_contract(data, family)
        gate.approve(store, user, contract, approval)
        job = started(data, contract)
        fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)
        request = budget.Reservation(request_key="synthetic-accounting-intent", stage="generate",
            run_id=job["id"], expected_version=job["version"], fence=job["fence"],
            wire_sha256="a" * 64, wire_bytes=100)
        scope = budget.scope_for(contract, approval.request_key)
        first = budget.reserve(store, user, scope, contract, request,
                               admission=partial(gate.admit, fee_authority=fee))
        before = records(store)
        path = f"/api/projects/{contract.project_id}/natural-trials/{contract.trial_key}/approvals/{approval.request_key}/budget"
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert response.json()["budget_projection"] == first["budget_projection"]
        duplicate = budget.reserve(store, user, scope, contract, request,
                                   admission=lambda *args: pytest.fail("History cannot mint a send permit"))
        assert duplicate["duplicate"] and not duplicate["dispatch_authorized"]
        assert response.json()["total_tokens"] is None and records(store) == before
        save(tmp_path, "REAL_CONTRACT_HTTP", family=family, contract=contract.model_dump(),
             first=first, method="GET", path=path, status=response.status_code,
             response=response.json(), duplicate=duplicate, accounting_rows_unchanged=True,
             transport_calls=0, qualification="NOT_BYPASSED; no production dispatch attempted")
    finally:
        client.close()


@pytest.mark.parametrize("family", ["P-A", "P-B"])
@pytest.mark.parametrize("failure", ["missing", "goal_drift", "expired", "revoked"])
def test_real_natural_contract_refusal_has_no_new_reservation(env, monkeypatch, tmp_path, family, failure):
    data = setup(env)
    store, _, client, user, *_ = data
    try:
        contract, approval = exact_contract(data, family)
        if failure != "missing":
            gate.approve(store, user, contract, approval)
        job = started(data, contract)
        if failure == "goal_drift":
            changed = copy.deepcopy(contract.model_dump())
            changed["bindings"][0]["goal_version"] += 1
            contract = gate.parse_contract(changed)
        elif failure == "expired":
            expired_at = contract.expires_at
            monkeypatch.setattr(time, "time", lambda: expired_at)
        elif failure == "revoked":
            gate.revoke(store, user, contract, gate.RevokeInput(
                expected_contract_fingerprint=fingerprint(contract.model_dump()), request_key="stop",
                consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL"))
        before = records(store)
        fee = gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()), contract.quota_subject)
        request = budget.Reservation(request_key="must-refuse", stage="generate", run_id=job["id"],
            expected_version=job["version"], fence=job["fence"], wire_sha256="a" * 64, wire_bytes=100)
        with pytest.raises(DomainError) as error:
            budget.reserve(store, user, budget.scope_for(contract, approval.request_key), contract,
                           request, admission=partial(gate.admit, fee_authority=fee))
        assert records(store) == before
        save(tmp_path, "REAL_CONTRACT_REFUSAL", kind="REAL_NATURAL_ADMISSION_WITH_SYNTHETIC_FEE_ONLY",
             family=family, failure=failure, error=error.value.public(),
             contract=contract.model_dump(), accounting_rows_unchanged=True, transport_calls=0)
    finally:
        client.close()
