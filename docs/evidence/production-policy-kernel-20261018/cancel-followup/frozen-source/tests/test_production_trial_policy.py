"""Uninstalled policy state transitions; SQLite synthetic context, zero model IO."""

import hashlib
import json
import time

import pytest
from sqlalchemy import select, update
from test_natural_live_admission import frozen, started
from test_natural_spec_apps import setup
from test_spec_app_operations import snapshot

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as budget
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as production
from sim2act import production_trial_policy as policy
from sim2act.db import fingerprint, grants, new_id, runs
from sim2act.errors import DomainError


@pytest.fixture
def kernel(env, tmp_path):
    data = setup(env)
    contract, approval = frozen(data)
    account = "synthetic-policy-account"
    contract = contract.model_copy(update=dict(quota_subject=production.canonical_quota_subject(account)))
    approval = approval.model_copy(update=dict(expected_contract_fingerprint=fingerprint(contract.model_dump())))
    gate.approve(data[0], data[3], contract, approval)  # LIVE_BLOCKED consent, never a LIVE permit.
    job = started(data, contract)
    scope = evidence.requirements_for(data[3], contract, approval.request_key)
    source = policy.SourceVerificationResult(requirements_fingerprint=fingerprint(scope.model_dump()),
        account_id=account, quota_subject=scope.quota_subject, provider=scope.provider,
        model=scope.model, endpoint=scope.endpoint, evidence_fingerprint="a" * 64,
        decision="ALLOW", legal_free_entitlement=True, enforced_non_chargeable=True, revoked=False,
        observed_at=time.time() - 600, expires_at=contract.expires_at)
    with data[0].tx() as c:
        worker = c.execute(select(runs.c.worker_id).where(runs.c.id == job["id"])).scalar_one()
        context = policy.check_run(data[0], c, data[3], contract, approval.request_key,
            "generate", job["id"], job["version"], job["fence"], worker)
    wire = b'{"synthetic_policy_only":true}'
    identity = policy.identity_for(context, source, new_id("attempt"), wire)
    ledger = policy.Ledger(scope=scope, account_id=account)
    cursor = policy.AccountQuotaCursor(account_id=account, quota_subject=scope.quota_subject)
    proof = []

    def invoke(operation, *, state=ledger, quota=cursor, item=identity, body=wire,
               result=source, original=contract, **kwargs):
        before = snapshot(data[0])
        try:
            with data[0].tx() as c:
                return operation(data[0], c, data[3], original, approval.request_key,
                    state, quota, item, body, result, **kwargs)
        finally:
            after = snapshot(data[0])
            assert before == after
            proof.append(dict(operation=operation.__name__, strict_all_rows_equal=True,
                tables={table: dict(rows=len(rows), before_sha256=fingerprint(rows),
                    after_sha256=fingerprint(after[table])) for table, rows in before.items()}))

    yield data, contract, approval, job, scope, source, identity, ledger, cursor, wire, invoke
    (tmp_path / "policy-readonly-windows.json").write_text(json.dumps(dict(
        scope="SYNTHETIC_INPUTS_UNINSTALLED_POLICY_ONLY", windows=proof,
        model_calls=0, worker_once_calls=0, production_permits=0,
        note="Pure immutable outputs, not installed durable state or DB-global quota"), indent=2))
    data[2].close()


def received(**changes):
    return policy.Outcome(outcome="RECEIVED", response_sha256="b" * 64,
        response_ascii_bytes=40, prompt_tokens=5, completion_tokens=3, total_tokens=8,
        **changes)


def test_positive_policy_transitions_are_not_permits_or_installed_authority(kernel, tmp_path):
    data, contract, approval, _, scope, source, item, _, _, wire, call = kernel
    reserved = call(policy.reserve)
    marked = call(policy.record_attempt, state=reserved.ledger, quota=reserved.quota)
    settled = call(policy.settle, state=marked.ledger, quota=marked.quota, outcome=received())
    assert settled.ledger.slots[0].accepted and not settled.ledger.halted
    assert len(settled.ledger.slots) == 1
    assert all(v.live_allowed is v.dispatch_authorized is v.real_source_verified is False
        for v in (reserved, marked, settled))
    assert policy.Transition.model_validate_json(settled.model_dump_json()) == settled
    duplicate = call(policy.reserve, state=settled.ledger, quota=settled.quota)
    assert duplicate.duplicate and duplicate.ledger == settled.ledger and duplicate.quota == settled.quota
    with pytest.raises(DomainError) as limited:
        call(policy.reserve, state=settled.ledger, quota=settled.quota,
             item=item.model_copy(update=dict(attempt_id=new_id("attempt"))))
    assert limited.value.code == "RATE_LIMITED"
    original_request = budget.Reservation(request_key=item.attempt_id, stage=item.stage,
        run_id=item.run_id, expected_version=item.version, fence=item.fence,
        wire_sha256=item.wire_sha256, wire_bytes=item.wire_bytes)
    with data[0].tx() as c, pytest.raises(DomainError) as denied:
        budget._active(data[0], c, budget.scope_for(contract, approval.request_key),
            original_request, contract, lambda *args: reserved)
    assert denied.value.code == "PERMISSION_DENIED"
    with pytest.raises(DomainError, match=evidence.SOURCE_MISSING):
        evidence.resolve_account(data[3], contract, approval.request_key)
    # Ten-minute-old source input is not forced to seek a fictitious 30s renewal.
    assert policy.check_source(scope, source, now=time.time()) == source
    (tmp_path / "non-executable-policy-transition.json").write_text(settled.model_dump_json(indent=2))


def test_exact_contract_account_quota_wire_worker_and_internal_result_bindings(kernel, tmp_path):
    _, contract, _, _, _, source, item, _, cursor, _, call = kernel
    cases = {
        "contract": dict(original=contract.model_copy(update=dict(trial_key="different-trial"))),
        "source-contract": dict(result=source.model_copy(update=dict(requirements_fingerprint="f" * 64))),
        "account": dict(result=source.model_copy(update=dict(account_id="different-account"))),
        "quota": dict(quota=cursor.model_copy(update=dict(quota_subject="different-bucket"))),
        "source-quota": dict(result=source.model_copy(update=dict(quota_subject="different-bucket"))),
        "wire": dict(body=b'{"different":true}'),
        "wire-sha": dict(item=item.model_copy(update=dict(wire_sha256="e" * 64))),
        "worker": dict(item=item.model_copy(update=dict(worker_id="another-worker"))),
        "approval": dict(item=item.model_copy(update=dict(approval_fingerprint="d" * 64))),
        "endpoint-cannot-migrate": dict(result=source.model_copy(update=dict(
            endpoint="https://discovery-api.intern-ai.org.cn/v1/chat/completions"))),
    }
    proof = []
    for label, changes in cases.items():
        with pytest.raises(DomainError) as denied:
            call(policy.reserve, **changes)
        proof.append(dict(case=label, code=denied.value.code))
    (tmp_path / "identity-refusals.json").write_text(json.dumps(proof, indent=2))


def test_source_expiry_revocation_unknown_and_missing_entitlement_fail_closed(kernel):
    source, call = kernel[5], kernel[-1]
    for change in ({"expires_at": time.time() - 1}, {"observed_at": time.time() + 60},
                   {"revoked": True}, {"revoked": None}, {"decision": "UNKNOWN"},
                   {"legal_free_entitlement": None}, {"enforced_non_chargeable": False}):
        with pytest.raises(DomainError) as denied:
            call(policy.reserve, result=source.model_copy(update=change))
        assert denied.value.code == "LIVE_BLOCKED"


def test_current_run_worker_version_fence_lease_phase_and_approval_are_rechecked(kernel):
    data, contract, approval, job, _, _, item, _, _, _, call = kernel
    for field, value in {"worker_id": "replaced-worker", "version": job["version"] + 1,
                         "fence": job["fence"] + 1, "lease_until": 1.0}.items():
        with data[0].tx() as c:
            original = c.execute(select(runs.c[field]).where(runs.c.id == job["id"])).scalar_one()
            c.execute(update(runs).where(runs.c.id == job["id"]).values({field: value}))
        try:
            with pytest.raises(DomainError):
                call(policy.reserve)
        finally:
            with data[0].tx() as c:
                c.execute(update(runs).where(runs.c.id == job["id"]).values({field: original}))
    with pytest.raises(DomainError):
        call(policy.reserve, item=item.model_copy(update=dict(stage="source", stage_fingerprint="a" * 64)))
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == contract.bindings[0].resource_id)
                  .values(revoked=True))
    with pytest.raises(DomainError) as denied:
        call(policy.reserve)
    assert denied.value.code == "GRANT_REVOKED"
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == contract.bindings[0].resource_id)
                  .values(revoked=False))
    gate.revoke(data[0], data[3], contract, gate.RevokeInput(
        expected_contract_fingerprint=fingerprint(contract.model_dump()),
        request_key="policy-original-revoke", consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL"))
    with pytest.raises(DomainError):
        call(policy.reserve)
    assert approval.request_key


def test_cancel_after_reservation_cannot_record_attempt_and_keeps_usage(kernel, tmp_path):
    data, _, _, job, _, _, _, _, _, _, call = kernel
    reserved = call(policy.reserve)
    marked = call(policy.record_attempt, state=reserved.ledger, quota=reserved.quota)
    with data[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == job["id"]).values(cancel_intent=True))
    with pytest.raises(DomainError):
        call(policy.record_attempt, state=reserved.ledger, quota=reserved.quota)
    settled = call(policy.settle, state=marked.ledger, quota=marked.quota, outcome=received())
    slot = settled.ledger.slots[0]
    assert settled.ledger.halted and not slot.accepted and slot.attempted
    assert slot.settlement.total_tokens == 8 and len(settled.ledger.slots) == 1
    duplicate = call(policy.reserve, state=settled.ledger, quota=settled.quota)
    assert duplicate.duplicate and duplicate.ledger == settled.ledger
    (tmp_path / "cancel-after-reservation.json").write_text(settled.model_dump_json(indent=2))


def test_unknown_and_missing_usage_hold_slot_and_never_allow_new_attempt(kernel, tmp_path):
    _, _, _, _, _, source, item, _, _, _, call = kernel
    reserved = call(policy.reserve)
    marked = call(policy.record_attempt, state=reserved.ledger, quota=reserved.quota)
    unknown = policy.Outcome(outcome="UNKNOWN", response_sha256="b" * 64,
        response_ascii_bytes=40, prompt_tokens=5)
    settled = call(policy.settle, state=marked.ledger, quota=marked.quota, outcome=unknown)
    restored = policy.Transition.model_validate_json(settled.model_dump_json())
    assert restored.ledger.halted and len(restored.ledger.slots) == 1
    assert restored.ledger.slots[0].settlement.total_tokens is None
    assert restored.ledger.slots[0].settlement.prompt_tokens == 5
    assert restored.quota == reserved.quota
    for operation, changes in ((policy.record_attempt, {}), (policy.reserve, dict(
            item=item.model_copy(update=dict(attempt_id=new_id("attempt")))))):
        with pytest.raises(DomainError) as denied:
            call(operation, state=restored.ledger, quota=restored.quota, **changes)
        assert denied.value.code == "OUTCOME_UNKNOWN"
    duplicate = call(policy.reserve, state=restored.ledger, quota=restored.quota,
                     result=source.model_copy(update=dict(revoked=True)))
    assert duplicate.duplicate and duplicate.ledger == restored.ledger
    (tmp_path / "unknown-nonrefundable-no-resend.json").write_text(restored.model_dump_json(indent=2))


def test_unreachable_restored_state_and_callbacks_are_rejected(kernel):
    _, _, _, _, _, _, item, ledger, cursor, wire, call = kernel
    reserved = call(policy.reserve)
    first = reserved.ledger.slots[0]
    other = first.model_copy(update=dict(identity=item.model_copy(update=dict(attempt_id=new_id("attempt"))),
                                        reserved_at=first.reserved_at + 60))
    invalid = ledger.model_copy(update=dict(slots=(first, other)))
    with pytest.raises(DomainError):
        call(policy.record_attempt, state=invalid,
             quota=reserved.quota.model_copy(update=dict(last_reserved_at=other.reserved_at)))
    accepted = first.model_copy(update=dict(attempted=True, settlement=received(), accepted=True))
    dense = ledger.model_copy(update=dict(slots=(accepted, other.model_copy(update=dict(reserved_at=first.reserved_at)))))
    with pytest.raises(DomainError):
        call(policy.record_attempt, state=dense, quota=reserved.quota)

    class Trap:
        def __getattribute__(self, name):
            raise AssertionError("No callback/attribute on arbitrary policy input")

        def __repr__(self):
            raise AssertionError("No untrusted repr in policy errors")

    for changes in (dict(result=Trap()), dict(item=item.model_copy(update=dict(worker_id=Trap()))),
                    dict(state=ledger.model_copy(update=dict(slots=(Trap(),)))),
                    dict(quota=cursor.model_copy(update=dict(last_reserved_at=float("nan"))))):
        with pytest.raises(DomainError):
            call(policy.reserve, **changes)
    assert item.wire_sha256 == hashlib.sha256(wire).hexdigest()
