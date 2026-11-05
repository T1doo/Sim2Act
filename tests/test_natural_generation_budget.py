"""New-profile projection and byte-compatible legacy scope, not dispatch IO."""
import json
import pytest
from pydantic import ValidationError
from test_natural_trial_preparation import prepared_data,scope
from sim2act import natural_live_admission as gate
from sim2act.natural_generation_budget import PROFILE,output_limit
from sim2act.db import fingerprint
from sim2act.errors import DomainError
from test_production_trial_policy import kernel


def test_new_profile_changes_only_generation_projection_and_scope_fingerprint(prepared_data):
    _,_,_,receipt=scope(prepared_data)
    original=receipt['contract'];legacy=gate.parse_contract(original)
    assert legacy.model_dump()==original and 'generation_profile' not in legacy.model_dump()
    new=gate.parse_contract({**original,'generation_profile':PROFILE})
    assert fingerprint(new.model_dump())!=fingerprint(original)
    assert new.caps==legacy.caps and new.expires_at==legacy.expires_at
    assert [output_limit(legacy,s) for s in ('generate','source','cold')]==[1024]*3
    assert [output_limit(new,s) for s in ('generate','source','cold')]==[4096,1024,1024]
    assert gate.parse_contract(json.loads(new.model_dump_json())).model_dump()==new.model_dump()
    with pytest.raises(ValidationError):gate.parse_contract({**original,'generation_profile':'unapproved'})
    with pytest.raises(DomainError):output_limit(new,'other')
    from sim2act.production_evidence import requirements_for
    assert requirements_for(new.principal_id,new,'synthetic-approval').generation_profile==PROFILE
    assert 'generation_profile' not in requirements_for(legacy.principal_id,legacy,'synthetic-approval').model_dump()


def test_profile_ledger_uses_conservative_generate_envelope_and_keeps_total_output(kernel):
    import time
    from sim2act import production_trial_policy as policy
    _,_,_,_,scope,_,identity,_,_,_,_=kernel
    extended=scope.model_copy(update={'generation_profile':PROFILE})
    identity=identity.model_copy(update={'requirements_fingerprint':fingerprint(extended.model_dump())})
    assert policy._envelope(extended,identity)==identity.wire_bytes+4096
    assert policy._envelope(scope,identity)==identity.wire_bytes+1024
    assert policy._envelope(extended,identity.model_copy(update={'stage':'source'}))==identity.wire_bytes+1024
    result=policy.Outcome(outcome='RECEIVED',response_sha256='a'*64,response_ascii_bytes=100,prompt_tokens=1,completion_tokens=2048,total_tokens=2049)
    slot=policy.Slot(identity=identity,reserved_at=time.time(),attempted=True,settlement=result,accepted=True)
    ledger=policy.Ledger(scope=extended,account_id=identity.account_id,slots=(slot,))
    assert policy._ledger(ledger)==ledger
    old_identity=identity.model_copy(update={'requirements_fingerprint':fingerprint(scope.model_dump())})
    with pytest.raises(DomainError):policy._ledger(ledger.model_copy(update={'scope':scope,'slots':(slot.model_copy(update={'identity':old_identity}),)}))
    large=result.model_copy(update={'completion_tokens':4000,'total_tokens':4001})
    one=slot.model_copy(update={'settlement':large})
    two=one.model_copy(update={'reserved_at':one.reserved_at+60,'identity':identity.model_copy(update={'attempt_id':'attempt_'+'b'*32})})
    with pytest.raises(DomainError):policy._ledger(ledger.model_copy(update={'slots':(one,two)}))


def test_wire_budget_requires_new_scope_and_candidate_stage(prepared_data):
    from sim2act.goal_applications import policy,generation_output_tokens,body,stage_tools
    from types import SimpleNamespace
    from sim2act.production_trial_sender import _wire
    _,_,_,receipt=scope(prepared_data)
    legacy=gate.parse_contract(receipt['contract'])
    extended=gate.parse_contract({**receipt['contract'],'generation_profile':PROFILE})
    selected=policy('intern-s2',extended.principal_id,extended.project_id,{'family':'natural_spec'},output_tokens=4096,natural_profile=PROFILE)
    messages=[{'role':'system','content':'synthetic'},{'role':'user','content':json.dumps({'server_ids':selected})}]
    read=stage_tools(SimpleNamespace(**selected),0)
    check=stage_tools(SimpleNamespace(**selected),1)
    assert [generation_output_tokens(messages,t,1024) for t in (read,check,[])]==[1024,4096,4096]
    _wire(extended,body(messages,check,4096),stage='generate')
    structured=json.loads(body(messages,check,4096))
    assert structured['thinking_mode'] is False
    structured.pop('thinking_mode')
    with pytest.raises(DomainError):_wire(extended,json.dumps(structured).encode(),stage='generate')
    with pytest.raises(DomainError):_wire(legacy,body(messages,check,4096),stage='generate')
    with pytest.raises(DomainError):_wire(extended,body(messages,read,4096),stage='generate')
    with pytest.raises(DomainError):policy('intern-s2',extended.principal_id,extended.project_id,{'family':'natural_spec'},output_tokens=4096)


def test_explicit_prepare_is_recoverable_and_cannot_reuse_other_scope_consent(prepared_data):
    from test_natural_trial_preparation import consent
    data,body=prepared_data;client=data[2]
    _,_,_,old=scope(prepared_data)
    base=f'/api/projects/{data[4]}/natural-trials/output4096'
    response=client.post(base+'/preparation',json={**body,'generation_profile':PROFILE})
    assert response.status_code==200,response.text
    receipt=response.json()
    assert receipt['contract']['generation_profile']==PROFILE and receipt['contract']['caps']==old['contract']['caps']
    assert client.get(base+'/preparation').json()['contract']==receipt['contract']
    assert client.post(base+'/consent',json=consent(old)).status_code==409
    assert client.post(base+'/consent',json=consent(receipt)).status_code==200


@pytest.mark.parametrize('bad_candidate,final_invalid',[(False,False),(True,False),(True,True)])
def test_core_reserves_same_4096_wire_without_changing_application_runtime(env,monkeypatch,bad_candidate,final_invalid):
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from test_natural_spec_apps import setup,generation_transport
    from sim2act.api import create_app
    from sim2act.worker import Worker
    from sim2act.db import attempts
    data=setup(env);store,settings,_,user,pid,_,card=data
    # Synthetic readiness projection only; no real production permit is issued.
    monkeypatch.setattr('sim2act.natural_generation_readiness.read',lambda *args:dict(availability='SELECTED_APPROVED_SCOPE',expected_version=card['version'],expected_fingerprint=card['fingerprint'],generation_request_key='natural-generation',generation_profile=PROFILE))
    client=TestClient(create_app(store,settings,production_selection={'synthetic':'projection'}))
    client.headers['Authorization']='Bearer synthetic-test-A'
    response=client.post(f"/api/projects/{pid}/goal-cards/{card['id']}/application-runs",json=dict(expected_version=card['version'],expected_fingerprint=card['fingerprint'],request_key='natural-generation',family='natural_spec'))
    assert response.status_code==202,response.text
    sent,base_transport=generation_transport(data,repair=bad_candidate)
    import httpx
    def respond_to_wire_names(request):
        raw=base_transport.handle_request(request).json()
        from sim2act.natural_wire_tools import ALIASES
        inverse={v:k for k,v in ALIASES.items()}
        for call in raw['choices'][0]['message'].get('tool_calls',[]):
            if bad_candidate and call['function']['name']=='spec.check_candidate':
                call['function']['arguments']=json.dumps({'candidate':'not a valid candidate object'})
            call['function']['name']=inverse[call['function']['name']]
        if final_invalid and len(sent)==3:raw['choices'][0]['message']['content']=json.dumps('still not a valid candidate')
        return httpx.Response(200,json=raw)
    transport=httpx.MockTransport(respond_to_wire_names)
    assert Worker(store,settings,goal_planner_transport=transport).once()
    run=client.get('/api/runs/'+response.json()['run_id']).json()
    if final_invalid:
        assert run['status']=='FAILED' and run['result'] is None,run
        assert len(sent)==3
        client.close();return
    assert run['status']=='PARTIAL',run
    assert [v['max_tokens'] for v in sent]==[1024,4096,4096]
    prompt=json.loads(sent[0]['messages'][1]['content'])
    assert prompt['generation_budget']['candidate_output_tokens']==4096
    assert prompt['generation_budget']['max_output_tokens']==1024
    assert run['contract']['snapshot']['application_generation']['app_limits']['max_output_tokens']==1024
    if bad_candidate:
        assert run['result']['app_created'] is False
        from sim2act.db import operations
        with store.tx() as c:
            receipt=c.execute(select(operations.c.receipt).where(operations.c.run_id==run['id'],operations.c.tool_ref=='spec.check_candidate')).scalar_one()
            assert receipt['data']['status']=='FAIL' and receipt['data']['project_writes']==0
    with store.tx() as c:
        rows=c.execute(select(attempts.c.reserved_tokens,attempts.c.parameters).where(attempts.c.run_id==run['id'])).all()
        assert sorted(v[1]['max_tokens'] for v in rows)==[1024,4096,4096]
    client.close()


def test_wire_budget_requires_new_scope_and_candidate_stage(prepared_data):
    from sim2act.goal_applications import policy,generation_output_tokens,body
    from sim2act.production_trial_sender import _wire
    _,_,_,receipt=scope(prepared_data)
    legacy=gate.parse_contract(receipt['contract'])
    extended=gate.parse_contract({**receipt['contract'],'generation_profile':PROFILE})
    selected=policy('intern-s2',extended.principal_id,extended.project_id,{'family':'natural_spec'},output_tokens=4096,natural_profile=PROFILE)
    messages=[{'role':'system','content':'synthetic'},{'role':'user','content':json.dumps({'server_ids':selected})}]
    read=[{'type':'function','function':{'name':'resource.read'}}]
    check=[{'type':'function','function':{'name':'spec.check_candidate'}}]
    assert [generation_output_tokens(messages,t,1024) for t in (read,check,[])]==[1024,4096,4096]
    _wire(extended,body(messages,check,4096),stage='generate')
    with pytest.raises(DomainError):_wire(legacy,body(messages,check,4096),stage='generate')
    with pytest.raises(DomainError):_wire(extended,body(messages,read,4096),stage='generate')
    with pytest.raises(DomainError):policy('intern-s2',extended.principal_id,extended.project_id,{'family':'natural_spec'},output_tokens=4096)
