"""Explicit synthetic entry only; no token persistence or accidental general LIVE."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import attempts, runs
from sim2act.model import InternModel
from sim2act import production_evidence
from sim2act.synthetic_workspace import NeverModel, WorkspaceError, serve, settings_for
from sim2act.worker import Worker


def test_default_entry_does_not_even_read_configured_token(tmp_path, monkeypatch):
    def forbidden():raise AssertionError('Default entry must not discover provider credentials')
    monkeypatch.setattr(production_evidence,'configured_token',forbidden)
    monkeypatch.setenv('SIM2ACT_MODEL_MODE','live');monkeypatch.setenv('SIM2ACT_LIVE_ENABLED','true')
    settings=settings_for(tmp_path)
    assert settings.mode=='mock' and not settings.live_enabled and settings.token==''
    assert settings.goal_planner_provider=='disabled' and not settings.natural_activation_enabled
    assert not settings.application_generation_activation_enabled


def test_explicit_missing_existing_token_fails_before_workspace_creation(tmp_path, monkeypatch):
    monkeypatch.delenv('INTERN_API_TOKEN',raising=False);monkeypatch.delenv('SIM2ACT_INTERN_TOKEN',raising=False)
    folder=tmp_path/'absent'
    with pytest.raises(WorkspaceError,match='EXACT_READ_EXISTING_TOKEN_MISSING'):
        serve(folder,new=True,exact_read_live=True)
    assert not folder.exists()


def test_explicit_finite_entry_does_not_open_other_model_families(env, tmp_path, monkeypatch):
    monkeypatch.setenv('INTERN_API_TOKEN','SYNTHETIC_NO_NETWORK')
    monkeypatch.delenv('SIM2ACT_INTERN_TOKEN',raising=False)
    settings=settings_for(tmp_path,exact_read_live=True)
    # Same local Store for the test; no production database or new credential.
    from dataclasses import replace
    settings=replace(settings,database_url=env[1].database_url)
    assert settings.max_requests==2 and settings.max_repairs==0 and settings.goal_planner_provider=='disabled'
    assert not settings.natural_activation_enabled and not settings.application_generation_activation_enabled
    calls=[]
    def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('Unexpected model network')
    monkeypatch.setattr(InternModel,'_request_serialized',forbidden)
    with TestClient(create_app(env[0],settings)) as client:
        client.headers['Authorization']='Bearer synthetic-test-A'
        user,project,resource=env[3],env[5],env[6]
        generic=client.post(f'/api/projects/{project}/runs',json={'goal':'ordinary goal is still disabled',
            'resource_refs':[resource],'request_key':'ordinary-no-live'})
        assert generic.status_code==202
        assert Worker(env[0],settings,NeverModel()).once()
        card=client.post(f'/api/projects/{project}/goal-cards',json={'title':'Synthetic scope',
            'goal':'Read the supplied synthetic CSV.','known':[],'assumptions':[],'unresolved':[],
            'constraints':['Read only.'],'acceptance_checks':['Check source.'],'resource_refs':[resource]})
        assert card.status_code==201,card.text
        saved=client.get('/api/goal-cards/'+card.json()['id']).json()
        for suffix in ['planned-runs','application-runs']:
            response=client.post(f"/api/projects/{project}/goal-cards/{saved['id']}/{suffix}",json={
                'expected_version':saved['version'],'expected_fingerprint':saved['fingerprint'],'request_key':'disabled-'+suffix})
            assert response.status_code==202,response.text
            assert Worker(env[0],settings,NeverModel()).once()
        with env[0].engine.connect() as c:
            assert all(r['status']!='SUCCEEDED' for r in c.execute(select(runs)).mappings())
            assert all(a['status']!='RECEIVED' for a in c.execute(select(attempts)).mappings())
    assert calls==[]
