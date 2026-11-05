"""Versioned output budget integration; synthetic provider, original API and ledger."""
import pytest
from pydantic import ValidationError
from test_pa_generation_provider import configured,prepared,provider,accepted
from test_goal_text_applications import confirm,release_instance
from sim2act import generation_approvals as approval
from sim2act.contracts import Limits
from sim2act.worker import Worker


def test_explicit_v2_scope_uses_4096_only_for_candidate_and_keeps_runtime_caps(env,monkeypatch):
    data,clock=configured(env,monkeypatch)
    old,body=prepared(data)
    client=data[2];pid=data[4]
    body={**body,'request_key':'scope4096','generation_request_key':'generation4096','output_profile':'pa-candidate-output4096.v1'}
    response=client.post(f'/api/projects/{pid}/application-provider-scopes',json=body)
    assert response.status_code==201,response.text
    scope=response.json()
    assert scope['scope']['version']=='pa-intern-generation-approval.v2'
    assert scope['scope']['candidate_output_tokens']==4096
    assert scope['scope']['limits']==old['scope']['limits']
    response=client.post(f"/api/application-provider-scopes/{scope['approval_id']}/approve",json=dict(expected_scope_fingerprint=scope['scope_fingerprint'],consent=approval.CONSENT,budget_note='Synthetic explicitly selected output4096; no external requests',request_key='approve4096'))
    assert response.status_code==200,response.text
    grant=response.json();rid=accepted(data,grant['activation'],key='generation4096')
    transport,sent=provider(data,clock,output_cap=4096)
    assert Worker(data[0],data[1],goal_planner_transport=transport).once()
    run=client.get('/api/runs/'+rid).json()
    assert run['status']=='PARTIAL',run
    assert [p['max_tokens'] for p in sent]==[1024,4096]
    assert run['contract']['snapshot']['limits']['max_output_tokens']==1024
    with data[0].tx() as c:
        charges,_,_=approval.audit(data[0],c,data[3],scope['approval_id'])
        assert [v.max_tokens for v in charges]==[1024,4096]
        assert all(isinstance(v,approval.Charge4096) for v in charges)
        assert sum(v.envelope for v in charges)<=64000
    app,_=confirm(data,rid,run)
    release,instance=release_instance(data,app)
    assert instance['release_id']==release['id']


def test_ordinary_limits_cannot_borrow_generation_output4096():
    with pytest.raises(ValidationError):
        Limits(max_requests=3,max_tools=1,max_repairs=1,max_total_tokens=64000,max_output_tokens=4096,run_seconds=300)
