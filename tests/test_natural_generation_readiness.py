"""Read-only selection projection and original checker delegation; no LIVE calls."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from test_pa_generation_provider import configured
from sim2act.api import create_app
from sim2act.natural_generation_readiness import read
from sim2act.errors import DomainError


def test_no_launcher_selection_is_blocked_and_other_principal_denied(env,monkeypatch):
    data,_=configured(env,monkeypatch)
    store,settings,client,user,pid,_,card=data
    path=f"/api/projects/{pid}/goal-cards/{card['id']}/natural-generation-readiness"
    value=client.get(path).json()
    assert value['availability']=='BLOCKED' and value['reason']=='NO_LAUNCHER_SELECTION'
    assert value['new_runs']==value['new_approvals']==value['actual_model_requests']==0
    selection=dict(user='user_'+'0'*32,project=pid,trial='t',approval='a',account='intern-ai-configured-account')
    other=TestClient(create_app(store,settings,production_selection=selection))
    other.headers.update(client.headers)
    assert other.get(path).status_code==403
    other.close()


def test_projection_requires_original_checker_and_exact_goal(env,monkeypatch):
    data,_=configured(env,monkeypatch)
    store,settings,client,user,pid,_,card=data
    card=client.get('/api/goal-cards/'+card['id']).json()
    card['snapshot']=next(v['snapshot'] for v in card['history'] if v['version']==card['version'])
    selection=dict(user=user,project=pid,trial='t',approval='a',account='intern-ai-configured-account')
    first=SimpleNamespace(card_id=card['id'],goal_version=card['version'],goal_fingerprint=card['fingerprint'],goal_snapshot=SimpleNamespace(model_dump=lambda:card['snapshot']))
    contract=SimpleNamespace(bindings=[first],stage_keys=SimpleNamespace(generate='original-generation-key'),expires_at=1234.,model_dump=lambda:{'trial':'original'})
    # Synthetic projection only: the real launch checker remains a mandatory
    # dependency and is separately tested by the production/launch suites.
    with patch('sim2act.launch_configuration.check_selection') as checked,patch('sim2act.natural_trial_api.original_contract',return_value=contract),patch('sim2act.natural_trial_api.existing_worker_selection',return_value={'worker_selection':selection,'approval_fingerprint':'f'*64}):
        value=read(store,settings,selection,user,pid,card['id'])
        checked.assert_called_once_with(store,settings,selection)
        assert value['generation_request_key']=='original-generation-key'
        assert value['snapshot']==card['snapshot'] and value['expires_at']==1234.
        assert value['new_runs']==0
        with pytest.raises(DomainError):read(store,settings,selection,user,pid,'goal_'+'0'*32)
        checked.side_effect=DomainError('LIVE_BLOCKED')
        with pytest.raises(DomainError):read(store,settings,selection,user,pid,card['id'])
        checked.side_effect=ValueError('QUOTA_SUBJECT_NOT_INITIALIZED')
        with pytest.raises(DomainError) as denied:read(store,settings,selection,user,pid,card['id'])
        assert denied.value.code=='LIVE_BLOCKED'
