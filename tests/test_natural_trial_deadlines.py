"""Fixed-clock deadline contracts; synthetic accounting is never LIVE permission."""
import json
import math
import time
from functools import partial
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from test_natural_trial_preparation import prepared_data, scope, consent  # noqa: F401
from test_natural_live_admission import frozen, started, permit, records
from sim2act import natural_live_admission as gate
from sim2act import natural_trial_budget as budget
from sim2act.db import Store, delivery_graph_requests, fingerprint
from sim2act.errors import DomainError


@pytest.fixture
def clock(monkeypatch):
    at=[time.time()+1]
    monkeypatch.setattr(time,'time',lambda:at[0])
    return at


def v2(prepared_data, clock):
    data, _, base, r=scope(prepared_data)
    assert r['contract']['namespace']=='natural-live-trial.v2'
    c=gate.parse_contract(r['contract'])
    assert c.review_expires_at==c.prepared_at+300
    assert c.execution_expires_at==c.prepared_at+3600==c.expires_at
    assert c.stage_handoff_seconds==900
    return data,base,r,c


def test_v2_frozen_review_boundary_and_restart_no_renewal(prepared_data, clock, tmp_path):
    data,base,r,c=v2(prepared_data,clock)
    client=data[2]
    clock[0]=c.review_expires_at-0.01
    approved=client.post(base+'/consent',json=consent(r))
    assert approved.status_code==200, approved.text
    snapshot=records(data[0])
    clock[0]=c.review_expires_at
    assert client.post(base+'/consent',json=consent(r)).status_code==409
    assert client.get(base+'/preparation').json()['contract']==r['contract']
    fresh=Store(str(data[0].engine.url),test_only=True)
    try:
        recovered=gate.recover(fresh,data[3],c,gate.parse_contract(r['contract']).stage_keys.generate+'_approval')
        assert recovered['approval']==approved.json()['approval']
        assert records(fresh)==snapshot
    finally:fresh.engine.dispose()
    (tmp_path/'DEADLINES_HTTP.json').write_text(json.dumps(dict(prepared=r,approved=approved.json(),recovered=recovered,clock=clock[0]),indent=2))


def test_unapproved_review_end_is_strict_and_cannot_change_deadlines(prepared_data, clock):
    data,base,r,c=v2(prepared_data,clock)
    clock[0]=c.review_expires_at
    assert data[2].post(base+'/consent',json=consent(r)).status_code==409
    assert data[2].get(base+'/preparation').json()['review_expired'] is True
    assert data[2].get(base+'/preparation').json()['expired'] is False
    assert data[2].post(base+'/end-preparation',json={'confirm_end':True}).status_code==200
    assert data[2].post(base+'/consent',json=consent(r)).status_code==409


@pytest.mark.parametrize("offset", [301,3590])
def test_v2_permit_execution_and_run_boundaries(prepared_data, clock, tmp_path, offset):
    data,base,r,c=v2(prepared_data,clock)
    assert data[2].post(base+'/consent',json=consent(r)).status_code==200
    # Initial review deadline passed: execution remains possible, never a fresh approval.
    clock[0]=c.prepared_at+offset
    job=started(data,c)
    body=SimpleNamespace(request_key=c.stage_keys.generate+'_approval')
    got=permit(data,c,body,job)
    assert got.expires_at==min(c.expires_at,job['created_at']+300)
    before=records(data[0])
    clock[0]=c.execution_expires_at
    with pytest.raises(DomainError):permit(data,c,body,job)
    request=budget.Reservation(request_key="past-execution",stage="generate",run_id=job["id"],expected_version=job["version"],fence=job["fence"],wire_sha256="a"*64,wire_bytes=100)
    with pytest.raises(DomainError) as error:
        budget.reserve(data[0],data[3],budget.scope_for(c,body.request_key),c,request,admission=gate.admit)
    assert error.value.code=="PERMISSION_DENIED" and records(data[0])==before
    assert data[2].get(base+'/preparation').json()['contract']==r['contract']
    (tmp_path/'PERMIT.json').write_text(json.dumps(dict(permit=got.model_dump(),execution_boundary_refused=True),indent=2))


def test_v1_original_bytes_and_300_second_lower_bound(prepared_data, clock, tmp_path):
    data,_=prepared_data
    c,body=frozen(data,ttl=300)
    raw=c.model_dump_json()
    receipt=gate.approve(data[0],data[3],c,body)
    job=started(data,c)
    request=budget.Reservation(request_key="v1-original-slot",stage="generate",run_id=job["id"],expected_version=job["version"],fence=job["fence"],wire_sha256="a"*64,wire_bytes=100)
    fee=gate.SyntheticOnlyFeeAuthority(fingerprint(c.model_dump()),c.quota_subject)
    budget.reserve(data[0],data[3],budget.scope_for(c,body.request_key),c,request,admission=partial(gate.admit,fee_authority=fee))
    before=records(data[0])
    clock[0]=c.expires_at
    assert gate.recover(data[0],data[3],c,body.request_key)['approval']==receipt['approval']
    assert records(data[0])==before and c.model_dump_json()==raw
    assert 'review_expires_at' not in json.loads(raw)
    assert (7-1)*60>300
    with pytest.raises(DomainError):gate.approve(data[0],data[3],c,body)
    (tmp_path/'V1_ORIGINAL.json').write_text(json.dumps(dict(contract=raw,records=before,seventh_earliest=360,expiry=300),indent=2))


def test_cross_review_deadline_rolls_back_both_approval_pairs(prepared_data, clock, monkeypatch):
    data,base,r,c=v2(prepared_data,clock)
    before=records(data[0]); original=gate._save
    def save(*args):
        original(*args)
        if args[3]==gate.APPROVE:clock[0]=c.review_expires_at
    monkeypatch.setattr(gate,'_save',save)
    assert data[2].post(base+'/consent',json=consent(r)).status_code==409
    assert records(data[0])==before


@pytest.mark.parametrize('field,value', [('review_expires_at',1),('execution_expires_at',1),
    ('expires_at',1),('prepared_at',float('inf')),('stage_handoff_seconds',901)])
def test_no_deadline_mutation_or_v1_upgrade_under_same_key(prepared_data,clock,field,value):
    data,base,r,c=v2(prepared_data,clock)
    bad=dict(r['contract'],**{field:value})
    with pytest.raises((ValueError,DomainError)):gate.parse_contract(bad)
    with pytest.raises((ValueError,DomainError)):gate.TrialContract.model_validate(r['contract'])
    from sim2act.natural_trial_api import ApprovalRequest
    body=gate.ApproveInput(expected_contract_fingerprint=fingerprint(c.model_dump()),
        request_key=c.stage_keys.generate+'_approval',consent=gate.CONSENT)
    parsed=ApprovalRequest.model_validate(dict(contract=c.model_dump(),approval=body.model_dump()))
    assert type(parsed.contract) is gate.TrialContractV2 and parsed.contract.model_dump()==c.model_dump()
    from sim2act.pa_trial_dispatch import PATrialBinding
    assert PATrialBinding(c,body.request_key).contract_fingerprint==r['review_token']


def test_actual_seven_slot_v2_worker_fixed_clock(env,monkeypatch,tmp_path):
    """Actual existing mock Worker/lineage/admission/accounting, never real provider.

    Clock advances in <=10s steps; real heartbeat renews only the current original
    30s lease, bounded by each original Run+300. No row/lease/guard overrides.
    """
    import hashlib
    import httpx
    from sqlalchemy import select
    from test_natural_spec_apps import setup,ready,enqueue,transport,SOURCE,COLD
    from sim2act.db import runs
    from sim2act.worker import Worker
    from sim2act.model import normalize_usage
    from sim2act.goal_applications import response_archive
    from sim2act import pb_natural_uses as use
    data=setup(env);store,settings,client,user,pid=data[:5]
    import threading
    clock_lock=threading.Lock()
    at=[time.time()+1]
    def ticking_time():
        with clock_lock:
            at[0]+=0.000001
            return at[0]
    monkeypatch.setattr(time,'time',ticking_time)
    old,_=frozen(data,ttl=3600)
    c=gate.TrialContractV2(**{**old.model_dump(),'namespace':'natural-live-trial.v2',
        'prepared_at':at[0],'review_expires_at':at[0]+300,
        'execution_expires_at':at[0]+3600,'expires_at':at[0]+3600})
    body=gate.ApproveInput(expected_contract_fingerprint=fingerprint(c.model_dump()),request_key='v2-full-approval',consent=gate.CONSENT)
    gate.approve(store,user,c,body);ledger_scope=budget.scope_for(c,body.request_key)
    fee=gate.SyntheticOnlyFeeAuthority(fingerprint(c.model_dump()),c.quota_subject)
    admitted=partial(gate.admit,fee_authority=fee); raw_handle=httpx.MockTransport.handle_request
    permits=[];wire=[];clock_events=[];active_heartbeats={}
    from sim2act import text_workflows,natural_spec_runtime
    original_process=text_workflows.process_job
    def observe_process(worker,run,advance_fn=None,*,_heartbeat_state=None):
        key=(worker.id,run['id'],run['fence'])
        active_heartbeats[key]=(worker,_heartbeat_state)
        try:
            return original_process(worker,run,advance_fn=advance_fn,_heartbeat_state=_heartbeat_state)
        finally:active_heartbeats.pop(key)
    monkeypatch.setattr(text_workflows,'process_job',observe_process)
    def advance(target):
        while True:
            with clock_lock:
                if at[0]>=target:break
                at[0]=min(target,at[0]+10)
            with store.tx() as conn:
                active=conn.execute(select(runs).where(runs.c.status=='RUNNING',runs.c.project_id==pid)).mappings().all()
            renewed=[]
            for job in active:
                entry=active_heartbeats.get((job['worker_id'],job['id'],job['fence']))
                state=None if entry is None else entry[1]
                deadline=min(c.expires_at,job['created_at']+300)
                if state is not None:
                    with state['lock']:
                        assert type(state['deadline']) in (int,float) and math.isfinite(state['deadline'])
                        deadline=min(deadline,state['deadline'])
                    # Invoke the actual synchronous runtime heartbeat. It alone
                    # commits lease renewal and updates the original shared state.
                    actual_worker=entry[0]
                    assert actual_worker.id==job['worker_id']
                    natural_spec_runtime.renew(actual_worker,job,deadline,_heartbeat_state=state)
                    with state['lock']:lease=state['lease_until']
                else:
                    lease=store.heartbeat(job['worker_id'],job['id'],job['fence'],30,
                        _deadline=deadline,_running_only=True)
                renewed.append(dict(run=job['id'],worker=job['worker_id'],fence=job['fence'],deadline=deadline,actual_lease=lease,original_runtime_renew=state is not None))
            clock_events.append(dict(at=at[0],renewals=renewed))
    def accountable(self,request):
        prior=budget.read(store,user,ledger_scope)['ledger']['last_reserved_at'] if wire else None
        if prior is not None:advance(max(at[0],prior+60))
        with store.tx() as conn:
            job=conn.execute(select(runs).where(runs.c.status=='RUNNING',runs.c.project_id==pid)).mappings().one()
            stage='generate' if job['runtime_id']==c.runtime_id else ('source' if job['resource_refs']==[c.bindings[0].resource_id] else 'cold')
            permit=admitted(store,conn,user,c,body.request_key,stage,job['id'],job['version'],job['fence'])
            permits.append(permit.model_dump())
        # Request bytes came from the actual existing InternModel/Worker mock transport.
        from sim2act.db import attempts
        with store.tx() as conn:
            attempt=conn.execute(select(attempts).where(attempts.c.run_id==job['id'],attempts.c.status=='STARTED')).mappings().one()
        reservation=budget.Reservation(request_key=attempt['id'],stage=stage,run_id=job['id'],
            expected_version=job['version'],fence=job['fence'],wire_sha256=hashlib.sha256(request.content).hexdigest(),wire_bytes=len(request.content))
        budget.reserve(store,user,ledger_scope,c,reservation,admission=admitted)
        with store.tx() as conn:admitted(store,conn,user,c,body.request_key,stage,job['id'],job['version'],job['fence'])
        response=raw_handle(self,request);_,archive=response_archive(response.json());usage=normalize_usage(response.json())
        settled=budget.settle(store,user,ledger_scope,c,budget.Settlement(request_key=attempt['id'],
            response_sha256=archive['sha256'],response_ascii_bytes=archive['bytes'],**usage['tokens']),admission=admitted)
        assert settled['ledger']['slots'][-1]['accepted']
        wire.append(dict(stage=stage,at=at[0],run_created_at=job['created_at'],lease_until=job['lease_until'],attempt=attempt['id']))
        return response
    async def async_accountable(self,request):
        await request.aread();return accountable(self,request)
    monkeypatch.setattr(httpx.MockTransport,'handle_async_request',async_accountable)
    generation,_,release,inst,_=ready(data,style='ordered')
    # Spend a bounded human handoff window. Source is approved near the original
    # Generate-acceptance+900 deadline, then legitimately executes after it.
    with store.tx() as conn:
        generation_at=conn.execute(select(runs.c.created_at).where(runs.c.id==generation)).scalar_one()
    advance(generation_at+880)
    source_id=enqueue(data,release,inst)
    review=gate.stage_review(store,user,c,body.request_key,'source',source_id)
    source=gate.StageApproveInput.model_validate(dict(authority=review['authority'],
        expected_authority_fingerprint=review['authority_fingerprint'],approval_key=body.request_key,
        request_key='v2-source',consent='BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL'))
    assert source.authority.stage_approval_expires_at==min(generation_at+900,c.expires_at)
    gate.approve_stage(store,user,c,source)
    assert Worker(store,settings,goal_planner_transport=transport([],SOURCE)).once()
    assert client.get('/api/runs/'+source_id).json()['status']=='SUCCEEDED'
    assert any(p['stage']=='source' and p['expires_at']>source.authority.stage_approval_expires_at for p in permits)
    target=c.bindings[1];current=client.get('/api/internal/instances/'+inst['id']).json()
    request=dict(expected_revision=current['revision'],expected_release_fingerprint=release['fingerprint'],
        expected_app_fingerprint=source.authority.candidate_fingerprint,expected_recipe_fingerprint=source.authority.recipe_fingerprint,
        resource_id=target.resource_id,card_id=target.card_id,expected_goal_version=target.goal_version,
        expected_goal_fingerprint=target.goal_fingerprint,expected_source_hash=target.source_hash,request_key=c.stage_keys.cold)
    route='/api/internal/instances/'+inst['id'];preview=client.post(route+'/pa-use-reviews',json=request)
    assert preview.status_code==200,preview.text
    made=client.post(route+'/pa-use-runs',json=dict(review=request,expected_review_fingerprint=preview.json()['review_fingerprint'],consent=use.PA_CONSENT))
    assert made.status_code==202,made.text
    cold_id=made.json()['run_id'];review=gate.stage_review(store,user,c,body.request_key,'cold',cold_id)
    cold=gate.StageApproveInput.model_validate(dict(authority=review['authority'],expected_authority_fingerprint=review['authority_fingerprint'],
        approval_key=body.request_key,request_key='v2-cold',consent=source.consent))
    gate.approve_stage(store,user,c,cold)
    assert Worker(store,settings,goal_planner_transport=transport([],COLD)).once()
    assert client.get('/api/runs/'+cold_id).json()['status']=='SUCCEEDED'
    result=budget.read(store,user,ledger_scope)
    assert result['reserved_requests']==7 and result['usage_status']=='KNOWN'
    times=[v['reserved_at'] for v in result['ledger']['slots']]
    assert all(b-a>=60 for a,b in zip(times,times[1:])) and times[-1]>c.prepared_at+300
    assert all(v['at']<v['run_created_at']+300 for v in wire)
    before=records(store)
    # Both original handoff and execution cutoffs fail closed; GET does not renew.
    with clock_lock:at[0]=cold.authority.stage_approval_expires_at
    with pytest.raises(DomainError):gate.approve_stage(store,user,c,cold)
    with pytest.raises(DomainError):gate.stage_review(store,user,c,body.request_key,'cold',cold_id)
    assert records(store)==before
    with clock_lock:at[0]=c.execution_expires_at
    with store.tx() as conn:
        with pytest.raises(DomainError):gate._approved(store,conn,user,c,body.request_key)
    assert gate.recover(store,user,c,body.request_key)['approval']['expires_at']==c.expires_at
    assert gate.recover_stage(store,user,c,body.request_key,'cold',cold.request_key)['request']==cold.model_dump()
    replay=budget.reserve(store,user,ledger_scope,c,budget.Reservation.model_validate(result['ledger']['slots'][0]['reservation']),admission=admitted)
    assert replay['duplicate'] and replay['dispatch_authorized'] is False and replay['ledger']==result['ledger']
    assert records(store)==before
    (tmp_path/'ACTUAL_V2_SEVEN_SLOTS.json').write_text(json.dumps(dict(contract=c.model_dump(),source=source.model_dump(),cold=cold.model_dump(),
        accounting=result,wire=wire,permits=permits,clock_events=clock_events,kind='OFFLINE_CONTROLLED_MICROTICK_CLOCK_EXISTING_WORKER_NOT_LIVE',clock_tick_seconds=0.000001,clock_tick_thread_serialized=True,actual_model_requests=0),indent=2))
    client.close()


def test_stage_handoff_exact_boundary_is_distinct_from_execution(prepared_data,clock):
    """Timing-only unit boundary, not a generated-source qualification fixture."""
    from sim2act.db import runs
    from sqlalchemy import update
    data,base,r,c=v2(prepared_data,clock)
    store,client,user,pid=data[0],data[2],data[3],data[4]
    assert client.post(base+'/consent',json=consent(r)).status_code==200
    predecessor=store.submit(user,pid,'synthetic timing metadata only',[],c.stage_keys.generate)
    with store.tx() as conn:
        conn.execute(update(runs).where(runs.c.id==predecessor).values(status='PARTIAL'))
        timing=gate._stage_deadlines(conn,user,c,'source',predecessor)
    authority=gate.StageAuthorityV2(contract_fingerprint=fingerprint(c.model_dump()),stage='source',
        run_id=predecessor,accepted_fingerprint='1'*64,app_run_id='timing-only',instance_id='timing-only',
        instance_revision=1,runtime_id=c.runtime_id,app_id='timing-only',candidate_fingerprint='2'*64,
        recipe_fingerprint='3'*64,release_id='timing-only',release_fingerprint='4'*64,
        generation_run_id=predecessor,generation_candidate_fingerprint='5'*64,
        target_goal_fingerprint='6'*64,authorization_fingerprint='7'*64,**timing)
    clock[0]=authority.stage_approval_expires_at-0.01
    gate._stage_review_window(authority)
    clock[0]=authority.stage_approval_expires_at
    with pytest.raises(DomainError):gate._stage_review_window(authority)
    with store.tx() as conn:
        assert gate._stage_deadlines(conn,user,c,'source',predecessor)==timing
        gate._approved(store,conn,user,c,c.stage_keys.generate+'_approval')
    # Execution remains active at the old handoff boundary; no fresh stage consent.
    assert clock[0]<c.execution_expires_at


def test_v1_approval_cannot_be_replaced_by_v2_under_same_key(prepared_data,clock,tmp_path):
    data,_=prepared_data;old,body=frozen(data,ttl=300)
    original=gate.approve(data[0],data[3],old,body);before=records(data[0])
    revised=gate.TrialContractV2(**{**old.model_dump(),'namespace':'natural-live-trial.v2',
        'prepared_at':clock[0],'review_expires_at':clock[0]+300,
        'execution_expires_at':clock[0]+3600,'expires_at':clock[0]+3600})
    response=data[2].post(f'/api/projects/{data[4]}/natural-trials/{old.trial_key}/approval',json=dict(
        contract=revised.model_dump(),approval=body.model_copy(update={'expected_contract_fingerprint':fingerprint(revised.model_dump())}).model_dump()))
    assert response.status_code in (400,409,422),response.text
    assert records(data[0])==before
    assert gate.recover(data[0],data[3],old,body.request_key)['approval']==original['approval']
    (tmp_path/'V1_REPLACE_REFUSED.json').write_text(json.dumps(dict(status=response.status_code,response=response.json(),original_unchanged=True),indent=2))
