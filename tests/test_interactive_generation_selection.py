"""Exact approved-run selection; synthetic provider only, no external calls."""
from dataclasses import replace
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from test_pa_generation_provider import configured,provider,accepted
from sim2act.api import create_app
from sim2act.db import runs
from sim2act import generation_approvals as approval
from sim2act.worker import Worker


def test_interactive_scope_requires_enable_and_exact_approval(env,monkeypatch):
    data,clock=configured(env,monkeypatch)
    store,settings,client,user,pid,_,card=data
    body=dict(card_id=card['id'],expected_version=card['version'],expected_fingerprint=card['fingerprint'],generation_request_key='interactive-run',request_key='interactive-scope',output_profile='pa-candidate-output4096.v1',execution_selection='approved-run')
    denied=client.post(f'/api/projects/{pid}/application-provider-scopes',json=body)
    assert denied.status_code==400 and denied.json()['error']['code']=='RESOURCE_UNAVAILABLE'
    settings=replace(settings,application_generation_run_selection=True)
    client=TestClient(create_app(store,settings));client.headers.update({'Authorization':'Bearer synthetic-test-A'})
    data=(store,settings,client,user,pid,data[5],card)
    prepared=client.post(f'/api/projects/{pid}/application-provider-scopes',json=body)
    assert prepared.status_code==201,prepared.text
    value=prepared.json();scope=approval.ScopeInteractive.model_validate(value['scope'])
    recovery=f'/api/projects/{pid}/application-provider-scopes'
    recovered=client.get(recovery,params={'request_key':body['request_key']})
    assert recovered.status_code==200 and recovered.json()==value
    assert client.get(recovery,params={'request_key':'unknown'}).status_code!=200
    recovery=f'/api/projects/{pid}/application-provider-scopes'
    recovered=client.get(recovery,params={'request_key':body['request_key']})
    assert recovered.status_code==200 and recovered.json()==value
    assert client.get(recovery,params={'request_key':'unknown'}).status_code!=200
    assert scope.version=='pa-intern-generation-approval.v3'
    fake=dict(approval_id=value['approval_id'],scope_fingerprint=value['scope_fingerprint'],approval_fingerprint='0'*64)
    response=client.post(f"/api/projects/{pid}/goal-cards/{card['id']}/application-runs",json=dict(expected_version=card['version'],expected_fingerprint=card['fingerprint'],request_key='interactive-run',activation=fake))
    assert response.status_code in (400,403,404,409)
    with store.tx() as c:assert c.execute(select(func.count()).select_from(runs)).scalar()==0
    grant=client.post(f"/api/application-provider-scopes/{scope.metadata.approval_id}/approve",json=dict(expected_scope_fingerprint=value['scope_fingerprint'],consent=approval.CONSENT,budget_note='Synthetic exact-scope test, zero real calls',request_key='interactive-approve'))
    assert grant.status_code==200,grant.text
    original_grant=grant.json()
    recovered=client.get(recovery,params={'request_key':body['request_key'],'approval_request_key':'interactive-approve'})
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['activation']==original_grant['activation']
    assert recovered.json()['deadline']==original_grant['deadline']
    assert client.get(recovery,params={'request_key':body['request_key'],'approval_request_key':'wrong'}).status_code!=200
    original_grant=grant.json()
    recovered=client.get(recovery,params={'request_key':body['request_key'],'approval_request_key':'interactive-approve'})
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['activation']==original_grant['activation']
    assert recovered.json()['deadline']==original_grant['deadline']
    assert client.get(recovery,params={'request_key':body['request_key'],'approval_request_key':'wrong'}).status_code!=200
    assert approval.selection_matches(scope,settings,scope.metadata.approval_id)
    assert not approval.selection_matches(scope,settings,'gaapproval_'+'0'*32)
    assert not approval.selection_matches(scope,replace(settings,application_generation_run_selection=False),scope.metadata.approval_id)
    # Legacy scopes never gain execution just because interactive selection is enabled.
    old=scope.model_dump();old.pop('execution_selection');old['version']='pa-intern-generation-approval.v2';old['request'].pop('execution_selection')
    old_scope=approval.Scope4096.model_validate(old)
    assert not approval.selection_matches(old_scope,settings,scope.metadata.approval_id)
    rid=accepted(data,grant.json()['activation'],key='interactive-run')
    transport,sent=provider(data,clock,output_cap=4096)
    assert Worker(store,settings,goal_planner_transport=transport).once()
    assert client.get('/api/runs/'+rid).json()['status']=='PARTIAL'
    assert len(sent)==2
    client.close()
