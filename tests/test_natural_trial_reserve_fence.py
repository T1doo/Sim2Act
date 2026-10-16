"""Real V2 admission/SQLite quota races. No model, fee qualification or HTTP IO."""
import json
from functools import partial

import pytest
from test_natural_trial_deadlines import clock,v2  # noqa: F401
from test_natural_trial_preparation import prepared_data,consent  # noqa: F401
from test_natural_live_admission import started,records
from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as budget
from sim2act.db import fingerprint
from sim2act.errors import DomainError


@pytest.mark.parametrize('boundary',['execution','run','permit','lease'])
@pytest.mark.parametrize('quota_exists',[False,True])
def test_quota_wait_crosses_original_boundary_atomically(prepared_data,clock,monkeypatch,tmp_path,boundary,quota_exists):
    data,base,receipt,contract=v2(prepared_data,clock)
    store,client,user=data[0],data[2],data[3]
    approved=client.post(base+'/consent',json=consent(receipt))
    assert approved.status_code==200,approved.text
    if boundary=='execution':clock[0]=contract.execution_expires_at-1
    else:clock[0]=contract.review_expires_at+1
    job=started(data,contract)
    if boundary=='execution':cutoff=contract.execution_expires_at
    elif boundary=='run':
        cutoff=job['created_at']+300
        while clock[0]<cutoff-1:
            clock[0]=min(cutoff-1,clock[0]+10)
            store.heartbeat(job['worker_id'],job['id'],job['fence'],30,_deadline=cutoff,_running_only=True)
    elif boundary=='lease':cutoff=job['lease_until']
    else:cutoff=clock[0]+1
    scope=budget.scope_for(contract,contract.stage_keys.generate+'_approval')
    request=budget.Reservation(request_key='cross-final-boundary',stage='generate',run_id=job['id'],
        expected_version=job['version'],fence=job['fence'],wire_sha256='a'*64,wire_bytes=100)
    fee=gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()),contract.quota_subject)
    calls=[]
    def admission(*args):
        permit=gate.admit(*args,fee_authority=fee)
        calls.append(permit.model_dump())
        if boundary=='permit':
            # A trusted controller may narrow a permit. A later fresh admission
            # must never silently replace this original shorter deadline.
            permit=permit.model_copy(update={'expires_at':cutoff if len(calls)==1 else contract.execution_expires_at})
        return permit
    if quota_exists:
        with store.tx() as conn:budget._quota(conn,scope.quota_subject)
    before=records(store)
    original=budget._quota
    def crosses(*args):
        result=original(*args)
        clock[0]=cutoff
        return result
    monkeypatch.setattr(budget,'_quota',crosses)
    status='unexpected-reservation';error=None;result=None
    try:result=budget.reserve(store,user,scope,contract,request,admission=admission)
    except DomainError as caught:status='refused';error=dict(code=caught.code,message=caught.message)
    after=records(store)
    proof=dict(boundary=boundary,quota_exists=quota_exists,cutoff=cutoff,final_clock=clock[0],status=status,
        error=error,result=result,before=before,after=after,all_accounting_rows_unchanged=before==after,
        initial_contract=receipt,approval=approved.json(),run=dict(job),admission_calls=calls,
        actual_provider_requests=0)
    (tmp_path/'QUOTA_RACE.json').write_text(json.dumps(proof,indent=2))
    assert status=='refused',json.dumps(proof)
    assert after==before


def test_original_expired_replay_remains_history_only(prepared_data,clock,monkeypatch,tmp_path):
    data,base,receipt,contract=v2(prepared_data,clock);store,client,user=data[0],data[2],data[3]
    assert client.post(base+'/consent',json=consent(receipt)).status_code==200
    job=started(data,contract);scope=budget.scope_for(contract,contract.stage_keys.generate+'_approval')
    fee=gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()),contract.quota_subject)
    admission=partial(gate.admit,fee_authority=fee)
    request=budget.Reservation(request_key='original-replay',stage='generate',run_id=job['id'],expected_version=job['version'],fence=job['fence'],wire_sha256='b'*64,wire_bytes=100)
    first=budget.reserve(store,user,scope,contract,request,admission=admission);before=records(store)
    clock[0]=contract.execution_expires_at
    def forbidden(*args):raise AssertionError('Expired original-key replay called active/quota')
    monkeypatch.setattr(budget,'_quota',forbidden)
    replay=budget.reserve(store,user,scope,contract,request,admission=forbidden)
    assert replay['duplicate'] and replay['dispatch_authorized'] is False and replay['ledger']==first['ledger']
    assert records(store)==before
    (tmp_path/'REPLAY.json').write_text(json.dumps(dict(first=first,replay=replay,rows_unchanged=True),indent=2))


@pytest.mark.parametrize('write_kind',[budget.KIND+'.quota',budget.KIND])
def test_write_wait_rolls_back_all_rows(prepared_data,clock,monkeypatch,tmp_path,write_kind):
    data,body=prepared_data;store,client,user=data[0],data[2],data[3]
    base=f'/api/projects/{data[4]}/natural-trials/write-boundary'
    http=[]
    def call(method,path,body=None):
        response=client.request(method,path,json=body)
        http.append(dict(method=method,path=path,request_json=body,status=response.status_code,
                         response_text=response.text))
        assert response.status_code==200,response.text
        return response.json()
    receipt=call('POST',base+'/preparation',body)
    contract=gate.parse_contract(receipt['contract'])
    call('POST',base+'/consent',consent(receipt))
    clock[0]=contract.execution_expires_at-1
    job=started(data,contract);scope=budget.scope_for(contract,contract.stage_keys.generate+'_approval')
    request=budget.Reservation(request_key='write-wait',stage='generate',run_id=job['id'],
        expected_version=job['version'],fence=job['fence'],wire_sha256='c'*64,wire_bytes=100)
    fee=gate.SyntheticOnlyFeeAuthority(fingerprint(contract.model_dump()),contract.quota_subject)
    before=records(store);original=budget._write;written=[]
    def crosses(*args,**kwargs):
        result=original(*args,**kwargs);written.append(args[3])
        if args[3]==write_kind:clock[0]=contract.execution_expires_at
        return result
    monkeypatch.setattr(budget,'_write',crosses)
    with pytest.raises(DomainError):
        budget.reserve(store,user,scope,contract,request,admission=partial(gate.admit,fee_authority=fee))
    assert write_kind in written and records(store)==before
    call('GET',base+'/preparation')
    assert records(store)==before
    (tmp_path/'HTTP_RAW.json').write_text(json.dumps(http,indent=2))
    (tmp_path/'WRITE_ROLLBACK.json').write_text(json.dumps(dict(write_kind=write_kind,written=written,
        cutoff=contract.execution_expires_at,final_clock=clock[0],before=before,after=records(store),
        all_rows_unchanged=True,provider_requests=0),indent=2))
