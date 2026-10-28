"""Unregistered production boundary, synthetic data only; no provider requests."""

import inspect
import json
import time

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import update
from test_natural_live_admission import frozen, started
from test_natural_spec_apps import recipe, setup
from test_spec_app_operations import snapshot

from sim2act import natural_live_admission as gate
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as production
from sim2act.config import Settings
from sim2act.db import fingerprint, grants
from sim2act.errors import DomainError


@pytest.fixture(autouse=True)
def no_configured_credentials(monkeypatch):
    monkeypatch.delenv("SIM2ACT_INTERN_TOKEN", raising=False)
    monkeypatch.delenv("INTERN_API_TOKEN", raising=False)


def pair():
    now = time.time()
    requirements = evidence.EvidenceRequirements(principal_id="user_" + "1" * 32,
        project_id="proj_" + "2" * 32, runtime_id="runtime_" + "3" * 32,
        trial_key="synthetic-data-only", approval_key="not-live-authorization",
        contract_fingerprint="a" * 64, software_fingerprint="b" * 64,
        authorization_fingerprint="c" * 64,
        quota_subject=production.canonical_quota_subject("synthetic-account"), expires_at=now + 60)
    candidate = evidence.AccountEvidenceCandidate(
        requirements_fingerprint=fingerprint(requirements.model_dump()),
        source_id="synthetic-untrusted-source", account_id="synthetic-account",
        quota_subject=requirements.quota_subject, entitlement_evidence_sha256="d" * 64,
        enforcement_evidence_sha256="e" * 64, issued_at=now - 2, checked_at=now - 1,
        expires_at=now + 30, outcome="RECEIVED", legal_free_entitlement=True,
        enforced_non_chargeable=True, revoked=False, paid_cap=0)
    return requirements, candidate, now


def test_complete_candidate_is_only_non_executable_unverified_diagnostic(tmp_path):
    requirements, candidate, now = pair()
    original = candidate.model_dump()
    diagnostic = evidence.validate_candidate(requirements, candidate, now=now)
    assert diagnostic.data_consistent is True
    assert diagnostic.source_verification == "SOURCE_UNVERIFIED"
    assert diagnostic.fee_verification == "NOT_VERIFIED"
    assert diagnostic.live_allowed is diagnostic.dispatch_authorized is False
    assert not isinstance(diagnostic, (gate.FeeProof, gate.Permit, production.AccountEvidence))
    assert candidate.model_dump() == original
    assert tuple(inspect.signature(evidence.resolve_account).parameters) == (
        "user", "contract", "approval_key")
    for value in (requirements, candidate, diagnostic):
        with pytest.raises(ValidationError):
            value.paid_cap = 1
    (tmp_path / "diagnostic.json").write_text(json.dumps(diagnostic.model_dump(), indent=2))


def test_candidate_binding_unknown_claims_and_original_time_bounds_fail_closed(tmp_path):
    requirements, candidate, now = pair()
    cases = {
        "wrong-requirements": {"requirements_fingerprint": "0" * 64},
        "wrong-account": {"account_id": "different-account"},
        "split-quota": {"quota_subject": "different-bucket"},
        "entitlement-unknown": {"legal_free_entitlement": None},
        "entitlement-false": {"legal_free_entitlement": False},
        "enforcement-unknown": {"enforced_non_chargeable": None},
        "enforcement-false": {"enforced_non_chargeable": False},
        "revoked": {"revoked": True}, "revocation-unknown": {"revoked": None},
        "unknown-source-outcome": {"outcome": "UNKNOWN"},
        "stale": {"issued_at": now - 32, "checked_at": now - 31},
        "future": {"checked_at": now + 1},
        "issued-after-checked": {"issued_at": now},
        "expired": {"expires_at": now},
        "renewed-beyond-original": {"expires_at": requirements.expires_at + 1},
    }
    proof = []
    for label, change in cases.items():
        with pytest.raises(DomainError) as denied:
            evidence.validate_candidate(requirements, candidate.model_copy(update=change), now=now)
        assert denied.value.code == "LIVE_BLOCKED" and denied.value.retryable is False
        proof.append(dict(case=label, code=denied.value.code, message=denied.value.message))
    # Fingerprint includes every explicit requirement, including the approval key.
    for field, value in {"principal_id": "user_" + "4" * 32,
                         "project_id": "proj_" + "5" * 32,
                         "runtime_id": "runtime_" + "6" * 32,
                         "trial_key": "another-trial", "approval_key": "another-approval",
                         "contract_fingerprint": "f" * 64}.items():
        with pytest.raises(DomainError):
            evidence.validate_candidate(requirements.model_copy(update={field: value}), candidate, now=now)
    (tmp_path / "candidate-refusals.json").write_text(json.dumps(proof, indent=2))


def test_strict_forged_models_and_callbacks_are_not_executed():
    requirements, candidate, now = pair()

    class Trap:
        def __getattribute__(self, name):
            raise AssertionError("No untrusted attribute access")

        def __repr__(self):
            raise AssertionError("No untrusted repr in errors")

        def __call__(self, *args, **kwargs):
            raise AssertionError("No untrusted callback")

    class SubCandidate(evidence.AccountEvidenceCandidate):
        pass

    for forged in (Trap(), candidate.model_dump(),
                   SubCandidate(**candidate.model_dump()),
                   candidate.model_copy(update={"paid_cap": False}),
                   candidate.model_copy(update={"legal_free_entitlement": 1}),
                   candidate.model_copy(update={"checked_at": float("nan")}),
                   candidate.model_copy(update={"source_id": "https://untrusted.invalid/source"}),
                   candidate.model_copy(update={"account_id": "../local-path"}),
                   candidate.model_copy(update={"model_dump": Trap()}),
                   candidate.model_copy(update={"entitlement_evidence_sha256": Trap()})):
        with pytest.raises(DomainError):
            evidence.validate_candidate(requirements, forged, now=now)
    for key in ("token", "credential", "source", "registry", "sender", "free"):
        with pytest.raises(ValidationError):
            evidence.AccountEvidenceCandidate.model_validate(candidate.model_dump() | {key: True})
    missing = candidate.model_dump()
    del missing["revoked"]
    with pytest.raises(ValidationError):
        evidence.AccountEvidenceCandidate.model_validate(missing)
    for reference in (True, float("inf"), Trap()):
        with pytest.raises(DomainError):
            evidence.validate_candidate(requirements, candidate, now=reference)
    with pytest.raises(DomainError):
        evidence.requirements_for(requirements.principal_id, Trap(), "key")


def test_original_contract_projection_all_versions_and_shadowed_serializers(env, tmp_path):
    data = setup(env)
    contract, approval = frozen(data)
    prepared = time.time()
    versions = [contract, gate.TrialContractV2(**dict(contract.model_dump(),
        namespace="natural-live-trial.v2", expires_at=prepared + 3600,
        prepared_at=prepared, review_expires_at=prepared + 300,
        execution_expires_at=prepared + 3600)),
        gate.PBTrialContract(**contract.model_dump(), path="P-B",
            extraction_request_key="separate-extraction", extraction_recipe=recipe("ordered"))]
    projections = []
    for original in versions:
        projected = evidence.requirements_for(data[3], original, approval.request_key)
        assert projected.contract_fingerprint == fingerprint(original.model_dump())
        assert projected.principal_id == data[3] and projected.project_id == data[4]
        assert projected.approval_key == approval.request_key
        assert projected.expires_at == original.expires_at and projected.paid_cap == 0
        with pytest.raises(DomainError, match=evidence.SOURCE_MISSING):
            evidence.resolve_account(data[3], original, approval.request_key)
        projections.append(projected.model_dump())

    def trap(*args, **kwargs):
        raise AssertionError("No shadowed instance serializer/callback")

    forged = [contract.model_copy(update={"model_dump": trap}),
        contract.model_copy(update={"bindings": [trap]}),
        contract.model_copy(update={"bindings": [
            contract.bindings[0].model_copy(update={"model_dump": trap}), contract.bindings[1]]}),
        contract.model_copy(update={"quota_subject": 1})]
    for original in forged:
        with pytest.raises(DomainError):
            evidence.requirements_for(data[3], original, approval.request_key)
    with pytest.raises(DomainError):
        evidence.requirements_for("user_" + "0" * 32, contract, approval.request_key)
    (tmp_path / "original-contract-projections.json").write_text(json.dumps(projections, indent=2))
    data[2].close()


def test_actual_production_routes_missing_source_authorize_first_and_never_write(env, monkeypatch, tmp_path):
    data = setup(env)
    store, settings, client, user, pid = data[:5]
    assert store.sqlite and store.test_only and settings.mode == "mock" and not settings.live_enabled
    forbidden, downstream, source_calls, http = [], [], [], []

    def no_io(*args, **kwargs):
        forbidden.append("unexpected-provider-or-credential-access")
        raise AssertionError("No real provider or credential access")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_io)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_io)
    monkeypatch.setattr(Settings, "from_env", no_io)
    original_resolver, original_qualified = evidence.resolve_account, production._qualified

    def observed_source(*args):
        source_calls.append(evidence.requirements_for(*args).model_dump())
        return original_resolver(*args)

    def observed_qualified():
        downstream.append("software-qualification-reached")
        return original_qualified()

    monkeypatch.setattr(evidence, "resolve_account", observed_source)
    monkeypatch.setattr(production, "_qualified", observed_qualified)
    contract, approval = frozen(data)
    receipt = gate.approve(store, user, contract, approval)
    assert receipt["live_allowed"] is False
    job = started(data, contract)  # Fixture claim only, never Worker.once or a model.
    path = f"/api/projects/{pid}/natural-trials/{contract.trial_key}"
    payload = dict(contract=contract.model_dump(), approval_key=approval.request_key,
        stage="generate", run_id=job["id"], expected_version=job["version"], fence=job["fence"])
    phases = []

    def post(url, body):
        response = client.post(url, json=body)
        http.append(dict(method="POST", path=url, request=body,
                         status=response.status_code, response=response.json()))
        return response

    def unchanged(label, before):
        after = snapshot(store)
        assert before == after  # Exact rows in all 55 actual fixture tables.
        phases.append(dict(phase=label, strict_all_rows_equal=True, tables={
            table: dict(rows=len(rows), before_sha256=fingerprint(rows),
                        after_sha256=fingerprint(after[table])) for table, rows in before.items()}))

    before = snapshot(store)
    for suffix in ("/admission", "/production-admission"):
        for _ in range(2):  # Repeated original request never reserves or resends.
            response = post(path + suffix, payload)
            assert response.status_code == 400
            assert response.json()["error"]["code"] == "LIVE_BLOCKED"
            assert response.json()["error"]["message"].startswith(evidence.SOURCE_MISSING)
            assert response.json()["error"]["safe_retry"] is False
        for key in ("source", "evidence", "registry", "sender", "fee_authority", "free", "usage"):
            assert post(path + suffix, payload | {key: True}).status_code == 422
    calls = len(source_calls)
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert post(path + "/production-admission", payload).status_code == 403
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    assert post(path.replace(pid, "proj_" + "0" * 32) + "/production-admission", payload).status_code == 403
    assert len(source_calls) == calls == 4
    unchanged("owner-duplicates-extra-fields-and-foreign-scope", before)
    # Explicit fixture revocation is separate from the no-write request window.
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == contract.bindings[0].resource_id)
                  .values(revoked=True))
    before = snapshot(store)
    assert post(path + "/production-admission", payload).status_code == 403
    assert len(source_calls) == calls
    unchanged("current-read-revoked-before-source", before)
    assert not forbidden and not downstream
    proof = dict(scope="SYNTHETIC_SQLITE_ONLY", actual_http=http, source_calls=source_calls,
        table_windows=phases, provider_or_credential_calls=forbidden,
        literal_software_qualification="NOT_REACHED", downstream_calls=downstream,
        worker_once_calls=0, model_calls=0, live_permits=0,
        missing_source="LIVE_BLOCKED", actual_fee_authority="ABSENT")
    (tmp_path / "actual-production-boundary-proof.json").write_text(json.dumps(proof, indent=2))
    client.close()
