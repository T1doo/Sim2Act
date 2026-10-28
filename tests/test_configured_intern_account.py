"""Configured server account source; no network or real credentials."""
import time
from dataclasses import replace
from pathlib import Path

import pytest
from test_natural_live_admission import frozen
from test_natural_spec_apps import setup

from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_policy as policy
from sim2act import spec_production as controller
from sim2act.config import Settings
from sim2act.errors import DomainError


def test_configured_source_binds_original_trial_and_stops_on_missing_or_split_account(env, monkeypatch):
    data = setup(env)
    contract, approval = frozen(data)
    contract = contract.model_copy(update={'quota_subject': admission.canonical_quota_subject(evidence.ACCOUNT_ID)})
    monkeypatch.setenv('INTERN_API_TOKEN', 'synthetic-only-not-a-credential')
    monkeypatch.delenv('SIM2ACT_INTERN_TOKEN', raising=False)
    source = evidence.resolve_account(data[3], contract, approval.request_key)
    checked = policy.check_source(evidence.requirements_for(data[3], contract, approval.request_key), source, now=time.time())
    assert checked.account_id == evidence.ACCOUNT_ID and checked.decision == 'ALLOW'
    assert checked.endpoint == evidence.FREE_SERVICE_POLICY['endpoint']
    assert checked.expires_at == contract.expires_at
    assert 'synthetic-only' not in checked.model_dump_json()
    with pytest.raises(DomainError, match='quota subject'):
        evidence.resolve_account(data[3], contract.model_copy(update={'quota_subject': 'different-account'}), approval.request_key)
    with pytest.raises(DomainError, match='expired'):
        evidence.resolve_account(data[3], contract.model_copy(update={'expires_at': time.time()-1}), approval.request_key)
    monkeypatch.delenv('INTERN_API_TOKEN')
    with pytest.raises(DomainError, match='credential missing'):
        evidence.resolve_account(data[3], contract, approval.request_key)
    data[2].close()


def test_production_environment_uses_same_server_credential_and_one_account(monkeypatch):
    from sim2act.db import Store
    monkeypatch.setenv('INTERN_API_TOKEN', 'synthetic-only')
    monkeypatch.setenv('SIM2ACT_INTERN_TOKEN', '')
    store = Store('postgresql+psycopg://unused@127.0.0.1:1/unused')
    settings = Settings(str(store.engine.url), Path('.'), mode='live', live_enabled=True,
        token='synthetic-only', quota_subject=admission.canonical_quota_subject(evidence.ACCOUNT_ID),
        goal_planner_provider='intern-s2', application_generation_activation_enabled=True)
    try:
        controller.environment(store, settings, None)
        for change in ({'token':'different'}, {'quota_subject':'other'}, {'mode':'mock'}, {'live_enabled':False}):
            with pytest.raises(DomainError, match='disabled'):
                controller.environment(store, replace(settings, **change), None)
        monkeypatch.setenv('SIM2ACT_INTERN_TOKEN','dedicated-synthetic-only')
        with pytest.raises(DomainError):
            controller.environment(store, settings, None)
        controller.environment(store, replace(settings, token='dedicated-synthetic-only'), None)
    finally:
        store.engine.dispose()
