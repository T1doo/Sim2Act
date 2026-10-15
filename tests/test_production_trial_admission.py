"""Fixed offline sender only: no credentials, real HTTP or LIVE authority."""

import hashlib
import time
from dataclasses import replace

import pytest
from sqlalchemy import select, update
from test_natural_live_admission import frozen, records, started
from test_natural_spec_apps import setup

from sim2act import natural_live_admission as gate
from sim2act import production_trial_admission as production
from sim2act.db import fingerprint, runs
from sim2act.errors import DomainError
from sim2act.natural_trial_api import AdmissionRequest


@pytest.fixture
def trial(env):
    data = setup(env)
    contract, approval = frozen(data)
    contract = contract.model_copy(update={"quota_subject": production.canonical_quota_subject("offline-account")})
    approval = approval.model_copy(update={"expected_contract_fingerprint": fingerprint(contract.model_dump())})
    gate.approve(data[0], data[3], contract, approval)
    job = started(data, contract)
    account = production.AccountEvidence(principal_id=data[3], project_id=data[4],
        trial_key=contract.trial_key, contract_fingerprint=fingerprint(contract.model_dump()),
        account_id="offline-account", quota_subject=contract.quota_subject,
        evidence_sha256="a" * 64, checked_at=time.time() - 1,
        expires_at=contract.expires_at, legal_free_entitlement=True,
        enforced_non_chargeable=True)
    registry = production.OfflineRegistry((account,), production.OfflineSender())
    wire = b'{"offline":true}'
    request = dict(request_key="offline-first-send", stage="generate", run_id=job["id"],
        expected_version=job["version"], fence=job["fence"], wire_bytes=len(wire),
        wire_sha256=hashlib.sha256(wire).hexdigest())
    yield data, contract, approval, job, registry, wire, request
    data[2].close()


def dispatch(t, **kwargs):
    data, contract, approval, job, registry, wire, request = t
    return production.dispatch_offline(data[0], data[3], contract, approval.request_key,
        request, wire, registry=kwargs.pop("registry", registry),
        worker_id=kwargs.pop("worker_id", job["worker_id"]), **kwargs)


def test_offline_known_result_duplicate_cold_read_never_resends(trial):
    data, contract, approval, *_ = trial
    first = dispatch(trial)
    assert first["scope_kind"] == "SYNTHETIC_ONLY" and first["live_allowed"] is False
    assert first["network_requests"] == 0 and first["reserved_requests"] == 1
    assert first["total_tokens"] == 2 and first["ledger"]["slots"][0]["accepted"]
    before = records(data[0])
    assert dispatch(trial, registry=None)["duplicate"] is True
    assert production.recover(data[0], data[3], contract, approval.request_key)["total_tokens"] == 2
    assert records(data[0]) == before


@pytest.mark.parametrize("change", [
    {"principal_id": "user_" + "0" * 32}, {"project_id": "proj_" + "0" * 32},
    {"trial_key": "another-trial"}, {"contract_fingerprint": "0" * 64},
    {"quota_subject": "attacker-quota"}, {"expires_at": 1.0},
    {"checked_at": 1e20}, {"revoked": True}, {"legal_free_entitlement": False},
    {"enforced_non_chargeable": False},
])
def test_untrusted_or_stale_account_has_zero_run_and_budget_mutations(trial, change):
    data, _, _, _, registry, *_ = trial
    bad = registry.accounts[0].model_copy(update=change)
    before = records(data[0])
    with data[0].tx() as c:
        before_runs = [dict(x) for x in c.execute(select(runs)).mappings()]
    with pytest.raises(DomainError) as error:
        dispatch(trial, registry=replace(registry, accounts=(bad,)))
    assert error.value.code == "LIVE_BLOCKED"
    assert records(data[0]) == before
    with data[0].tx() as c:
        assert [dict(x) for x in c.execute(select(runs)).mappings()] == before_runs


def test_arbitrary_callback_or_production_store_never_invoked(trial):
    class Trap:
        def __getattribute__(self, key):
            raise AssertionError("No arbitrary callback or attribute access")
    for registry in (None, Trap(), production.OfflineRegistry((), Trap())):
        before = records(trial[0][0])
        with pytest.raises(DomainError):
            dispatch(trial, registry=registry)
        assert records(trial[0][0]) == before
    trial[0][0].test_only = False
    try:
        with pytest.raises(DomainError):
            dispatch(trial)
    finally:
        trial[0][0].test_only = True


@pytest.mark.parametrize("change", [{"worker_id": "wrong-owner"},
    {"version": 999}, {"fence": 999}, {"cancel_intent": True},
    {"lease_until": 1.0}, {"status": "PAUSED"}])
def test_current_owner_fence_version_cancel_lease_rechecked(trial, change):
    data, _, _, job, *_ = trial
    with data[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == job["id"]).values(**change))
    before = records(data[0])
    with pytest.raises(DomainError):
        dispatch(trial)
    assert records(data[0]) == before


def test_unknown_remains_deducted_and_never_resends_after_cancel(trial):
    registry = replace(trial[4], sender=production.OfflineSender(outcome_unknown=True))
    result = dispatch(trial, registry=registry)
    assert result["usage_status"] == "UNKNOWN" and result["total_tokens"] is None
    assert result["reserved_requests"] == 1 and result["ledger"]["halted"]
    with trial[0][0].tx() as c:
        c.execute(update(runs).where(runs.c.id == trial[3]["id"]).values(cancel_intent=True))
    before = records(trial[0][0])
    recovered = dispatch(trial, registry=None)
    assert recovered["duplicate"] and recovered["usage_status"] == "UNKNOWN"
    assert recovered["reserved_requests"] == 1 and records(trial[0][0]) == before


def test_fresh_revocation_before_send_refuses_without_reservation(trial):
    data, contract, approval, *_ = trial
    gate.revoke(data[0], data[3], contract, gate.RevokeInput(
        expected_contract_fingerprint=fingerprint(contract.model_dump()), request_key="revoke-now",
        consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL"))
    before = records(data[0])
    with pytest.raises(DomainError):
        dispatch(trial)
    assert records(data[0]) == before


def test_http_production_default_deny_and_no_authority_override(trial):
    data, contract, approval, job, *_ = trial
    path = f"/api/projects/{data[4]}/natural-trials/{contract.trial_key}"
    payload = dict(contract=contract.model_dump(), approval_key=approval.request_key,
        stage="generate", run_id=job["id"], expected_version=job["version"], fence=job["fence"])
    before = records(data[0])
    for suffix in ("/admission", "/production-admission"):
        response = data[2].post(path + suffix, json=payload)
        assert response.status_code == 400 and response.json()["error"]["code"] == "LIVE_BLOCKED"
        for key in ("free", "quota_subject", "account_id", "fee_authority", "sender"):
            assert data[2].post(path + suffix, json=payload | {key: True}).status_code == 422
        data[2].headers["Authorization"] = "Bearer synthetic-test-B"
        assert data[2].post(path + suffix, json=payload).status_code == 403
        data[2].headers["Authorization"] = "Bearer synthetic-test-A"
    assert records(data[0]) == before
    assert AdmissionRequest.model_validate(payload).contract == contract


def test_one_account_cannot_split_quota_across_trials(trial):
    registry = trial[4]
    conflicting = registry.accounts[0].model_copy(update={"trial_key": "second-trial",
        "quota_subject": "another-rate-limit-bucket"})
    with pytest.raises(DomainError):
        dispatch(trial, registry=replace(registry, accounts=registry.accounts + (conflicting,)))


def test_stale_signed_account_record_not_valid_until_arbitrary_expiry(trial):
    registry = trial[4]
    stale = registry.accounts[0].model_copy(update={"checked_at": time.time() - 31})
    with pytest.raises(DomainError):
        dispatch(trial, registry=replace(registry, accounts=(stale,)))


def test_settlement_rechecks_worker_owner_in_same_admission(trial, monkeypatch):
    from sim2act import natural_trial_budget as budget
    original = budget.settle
    def changed(store, user, scope, contract, settlement, **kw):
        with store.tx() as c:
            c.execute(update(runs).where(runs.c.id == trial[3]["id"]).values(worker_id="new-worker"))
        return original(store, user, scope, contract, settlement, **kw)
    monkeypatch.setattr(budget, "settle", changed)
    result = dispatch(trial)
    assert result["reserved_requests"] == 1 and result["ledger"]["halted"]
    assert result["ledger"]["slots"][0]["accepted"] is False


def test_same_account_cannot_change_bucket_by_replacing_registry(trial):
    data, contract, _, _, registry, *_ = trial
    changed = contract.model_copy(update={"quota_subject": "different-bucket"})
    account = registry.accounts[0].model_copy(update={"quota_subject": changed.quota_subject,
        "contract_fingerprint": fingerprint(changed.model_dump())})
    with pytest.raises(DomainError):
        production._resolve(data[0], data[3], changed, replace(registry, accounts=(account,)))


def test_qualification_rejects_same_key_damaged_anchor_bytes():
    import json
    from pathlib import Path
    anchor = Path(production.__file__).with_name("text_software_anchors.json")
    original = anchor.read_bytes()
    changed = json.loads(original)
    first = next(iter(changed))
    changed[first]["files"][next(iter(changed[first]["files"]))] = "0" * 64
    try:
        anchor.write_text(json.dumps(changed))
        with pytest.raises(DomainError):
            production._qualified()
    finally:
        anchor.write_bytes(original)


def test_unknown_late_usage_recovers_accounting_without_acceptance_or_refund(trial):
    from sim2act import natural_trial_budget as budget
    registry = replace(trial[4], sender=production.OfflineSender(outcome_unknown=True))
    first = dispatch(trial, registry=registry)
    slot = first["ledger"]["slots"][0]
    fixed = dict(slot["settlement"], prompt_tokens=1, completion_tokens=1, total_tokens=2)
    scope = budget.scope_for(trial[1], trial[2].request_key)
    late = budget.settle(trial[0][0], trial[0][3], scope, trial[1], fixed)
    assert late["reserved_requests"] == 1 and late["ledger"]["halted"]
    assert late["ledger"]["slots"][0]["accepted"] is False
    assert len(late["ledger"]["slots"][0]["settlement_history"]) == 2
    assert dispatch(trial, registry=None)["duplicate"] is True


def test_duplicate_key_cannot_change_original_wire_or_create_another_slot(trial):
    dispatch(trial)
    before = records(trial[0][0])
    altered = list(trial)
    altered[5] = b'{"different":true}'
    altered[6] = dict(trial[6], wire_bytes=len(altered[5]),
        wire_sha256=hashlib.sha256(altered[5]).hexdigest())
    with pytest.raises(DomainError):
        dispatch(altered)
    assert records(trial[0][0]) == before
