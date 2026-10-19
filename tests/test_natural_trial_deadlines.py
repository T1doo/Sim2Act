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
    """Original associated V2 controller with finite MockTransport payloads only.

    Only the stale literal software qualifier is replaced for this isolated
    synthetic fixture. No product anchor, account source or permission changes.
    Clock advances in <=10s steps; actual runtime heartbeat renews the original
    30s lease, bounded by each original Run+300. No row/lease/guard overrides.
    """
    import hashlib
    import threading
    from dataclasses import replace
    import httpx
    from sqlalchemy import select
    import test_natural_spec_apps as apps
    from sim2act.db import attempts, runs
    from sim2act.worker import Worker
    from sim2act import natural_trial_runs as coordinator
    from sim2act import pa_trial_dispatch as dispatch
    from sim2act import production_trial_admission as production
    from sim2act import pb_natural_uses as use

    data=apps.setup(env)
    subject=production.canonical_quota_subject('offline-v2-deadline-account')
    settings=replace(data[1],quota_subject=subject)
    data=(data[0],settings,*data[2:])
    store,settings,client,user,pid=data[:5]
    assert store.test_only and store.sqlite
    assert settings.mode=='mock' and settings.live_enabled is False and settings.token==''
    store.initialize(quota_subject=subject)
    clock_lock=threading.Lock()
    at=[time.time()+1]
    def ticking_time():
        with clock_lock:
            at[0]+=0.000001
            return at[0]
    monkeypatch.setattr(time,'time',ticking_time)
    old,_=frozen(data,ttl=3600)
    prepared_at=at[0]
    c=gate.TrialContractV2(**{**old.model_dump(),'namespace':'natural-live-trial.v2',
        'quota_subject':subject,'prepared_at':prepared_at,'review_expires_at':prepared_at+300,
        'execution_expires_at':prepared_at+3600,'expires_at':prepared_at+3600})
    assert c.caps.lease_seconds==settings.lease_seconds==30
    assert c.caps.run_seconds==settings.run_seconds==300
    assert c.review_expires_at==c.prepared_at+300
    assert c.execution_expires_at==c.expires_at==c.prepared_at+3600
    assert c.stage_handoff_seconds==900
    body=gate.ApproveInput(expected_contract_fingerprint=fingerprint(c.model_dump()),request_key='v2-full-approval',consent=gate.CONSENT)
    gate.approve(store,user,c,body)
    ledger_scope=budget.scope_for(c,body.request_key)
    account=production.AccountEvidence(principal_id=user,project_id=pid,trial_key=c.trial_key,
        contract_fingerprint=fingerprint(c.model_dump()),account_id='offline-v2-deadline-account',
        quota_subject=subject,evidence_sha256='a'*64,checked_at=time.time(),expires_at=c.expires_at,
        legal_free_entitlement=True,enforced_non_chargeable=True)
    binding=dispatch.PATrialBinding(c,body.request_key,
        production.OfflineRegistry((account,),production.OfflineSender()))
    # Explicit synthetic-only qualification stand-in. All actual controller,
    # association, account freshness, authorization and accounting guards remain.
    monkeypatch.setattr(production,'_qualified',lambda:None)
    workers=[]
    def refresh(worker):
        current=worker.pa_trial
        assert type(current) is dispatch.PATrialBinding
        assert current.contract==c and current.approval_key==body.request_key
        assert current.contract_fingerprint==binding.contract_fingerprint
        fresh=account.model_copy(update={'checked_at':time.time()})
        worker.pa_trial=replace(current,registry=production.OfflineRegistry((fresh,),binding.registry.sender))
    def worker_factory(model_transport):
        fresh=account.model_copy(update={'checked_at':time.time()})
        current=replace(binding,registry=production.OfflineRegistry((fresh,),binding.registry.sender))
        worker=Worker(store,settings,goal_planner_transport=model_transport,pa_trial=current)
        workers.append(worker)
        return worker

    permits=[];wire=[];clock_events=[];active_heartbeats={};paced_waits=[]
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
            for worker in tuple(workers):refresh(worker)
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
                    actual_worker=entry[0]
                    assert actual_worker.id==job['worker_id']
                    natural_spec_runtime.renew(actual_worker,job,deadline,_heartbeat_state=state)
                    with state['lock']:lease=state['lease_until']
                else:
                    lease=store.heartbeat(job['worker_id'],job['id'],job['fence'],30,
                        _deadline=deadline,_running_only=True)
                renewed.append(dict(run=job['id'],worker=job['worker_id'],fence=job['fence'],deadline=deadline,actual_lease=lease,original_runtime_renew=state is not None))
            clock_events.append(dict(at=at[0],renewals=renewed))

    # Advance before the real unreserved quota wait. The original wait still
    # validates unknown slots, shared quota, cancellation and unchanged deadlines.
    original_wait=dispatch.wait_unreserved
    def paced_wait(worker,run_id):
        assert worker in workers
        with store.tx() as conn:
            ledger=budget._ledger(conn,ledger_scope)
            prior=ledger['last_reserved_at']
        if prior is not None:advance(max(at[0],prior+60))
        refresh(worker)
        paced_waits.append(dict(run_id=run_id,at=at[0],last_reserved_at=prior))
        return original_wait(worker,run_id)
    monkeypatch.setattr(dispatch,'wait_unreserved',paced_wait)
    original_admit=gate.admit
    def observe_admit(*args,**kwargs):
        result=original_admit(*args,**kwargs)
        permits.append(result.model_dump())
        return result
    monkeypatch.setattr(gate,'admit',observe_admit)
    original_capture=dispatch.request_captured
    def observe_capture(worker,run,aid,serialized,original_guard,provider,*,_heartbeat_state=None):
        refresh(worker)  # same isolated account, fresh immediately before real send guards
        with store.tx() as conn:
            job=conn.execute(select(runs).where(runs.c.id==run['id'])).mappings().one()
        stage=dispatch._stage(worker.pa_trial,job)
        event=dict(stage=stage,at=at[0],run_created_at=job['created_at'],lease_until=job['lease_until'],
            attempt=aid,wire_sha256=hashlib.sha256(serialized).hexdigest(),wire_bytes=len(serialized))
        result=original_capture(worker,run,aid,serialized,original_guard,provider,_heartbeat_state=_heartbeat_state)
        wire.append(event)
        return result
    monkeypatch.setattr(dispatch,'request_captured',observe_capture)
    original_async=httpx.MockTransport.handle_async_request

    def ordinary_cannot_claim(run_id):
        assert Worker(store,settings).once() is False
        with store.tx() as conn:
            job=conn.execute(select(runs).where(runs.c.id==run_id)).mappings().one()
            assert job['status']=='QUEUED' and job['fence']==0
            assert not conn.execute(select(attempts.c.id).where(attempts.c.run_id==run_id)).first()
    def stage_input(current,pa_use=None):
        return coordinator.StageInput(instance_id=inst['id'],expected_revision=current['revision'],
            expected_release_fingerprint=release['fingerprint'],pa_use=pa_use)
    def checklist(run_id,content):
        result=client.get('/api/internal/instances/'+inst['id']+'/runs/'+run_id)
        assert result.status_code==200,result.text
        assert result.json()['status']=='SUCCEEDED'
        actual=result.json()['result']['checklist']
        assert actual['source_content']==content
        target=c.bindings[0 if content==apps.SOURCE else 1]
        assert actual['human_unresolved']==target.goal_snapshot.content.unresolved
        assert [item['kind'] for item in actual['items']]==['requirement','condition','exception','open_question']
        assert actual['items'][3]['decision_status']=='OPEN'
        assert actual['owner_acceptance']=='PENDING' and actual['semantic_goal_acceptance']=='NOT_RUN'
        return actual

    # Enqueue only through the original atomic controller, then reuse unchanged
    # finite generation payloads and the existing explicit save/release/instance.
    generation=coordinator.submit_generate(store,user,binding)['run_id']
    ordinary_cannot_claim(generation)
    generation_sent,generation_transport=apps.generation_transport(data,style='ordered')
    assert worker_factory(generation_transport).once()
    generated=client.get('/api/runs/'+generation)
    assert generated.status_code==200,generated.text
    result=generated.json()
    assert result['status']=='PARTIAL',generated.text
    sample=client.get(f'/api/projects/{pid}/natural-spec-model-runs/{generation}/sample-preview')
    assert sample.status_code==200,sample.text
    assert sample.json()['preview']['checklist']['items'][2]['kind']=='exception'
    assert apps.confirm(data,generation,result,False).status_code==403
    saved=apps.confirm(data,generation,result)
    assert saved.status_code==200,saved.text
    release,inst=apps.instance(data,saved.json()['id'])
    assert len(generation_sent)==3
    with store.tx() as conn:
        generation_at=conn.execute(select(runs.c.created_at).where(runs.c.id==generation)).scalar_one()
    advance(generation_at+880)
    source_id=coordinator.submit_stage(store,user,binding,'source',stage_input(inst))['run_id']
    ordinary_cannot_claim(source_id)
    review=gate.stage_review(store,user,c,body.request_key,'source',source_id)
    source=gate.StageApproveInput.model_validate(dict(authority=review['authority'],
        expected_authority_fingerprint=review['authority_fingerprint'],approval_key=body.request_key,
        request_key='v2-source',consent='BIND_ONLY_THIS_ACCEPTED_STAGE_RUN_APP_RELEASE_AND_COMPLETE_GOAL_TO_ORIGINAL_TRIAL'))
    assert source.authority.stage_approval_expires_at==min(generation_at+900,c.expires_at)
    gate.approve_stage(store,user,c,source)
    source_sent=[]
    assert worker_factory(apps.transport(source_sent,apps.SOURCE)).once()
    assert client.get('/api/runs/'+source_id).json()['status']=='SUCCEEDED'
    checklist(source_id,apps.SOURCE)
    assert any(p['stage']=='source' and p['expires_at']>source.authority.stage_approval_expires_at for p in permits)
    target=c.bindings[1];current=client.get('/api/internal/instances/'+inst['id']).json()
    request=dict(expected_revision=current['revision'],expected_release_fingerprint=release['fingerprint'],
        expected_app_fingerprint=source.authority.candidate_fingerprint,expected_recipe_fingerprint=source.authority.recipe_fingerprint,
        resource_id=target.resource_id,card_id=target.card_id,expected_goal_version=target.goal_version,
        expected_goal_fingerprint=target.goal_fingerprint,expected_source_hash=target.source_hash,request_key=c.stage_keys.cold)
    route='/api/internal/instances/'+inst['id'];preview=client.post(route+'/pa-use-reviews',json=request)
    assert preview.status_code==200,preview.text
    pa_use=use.PACommitInput.model_validate(dict(review=request,
        expected_review_fingerprint=preview.json()['review_fingerprint'],consent=use.PA_CONSENT))
    cold_id=coordinator.submit_stage(store,user,binding,'cold',stage_input(current,pa_use))['run_id']
    ordinary_cannot_claim(cold_id)
    review=gate.stage_review(store,user,c,body.request_key,'cold',cold_id)
    cold=gate.StageApproveInput.model_validate(dict(authority=review['authority'],expected_authority_fingerprint=review['authority_fingerprint'],
        approval_key=body.request_key,request_key='v2-cold',consent=source.consent))
    gate.approve_stage(store,user,c,cold)
    cold_sent=[]
    assert worker_factory(apps.transport(cold_sent,apps.COLD)).once()
    assert client.get('/api/runs/'+cold_id).json()['status']=='SUCCEEDED'
    checklist(cold_id,apps.COLD)
    assert len(source_sent)==len(cold_sent)==2
    assert httpx.MockTransport.handle_async_request is original_async
    result=budget.read(store,user,ledger_scope)
    assert result['reserved_requests']==7 and result['usage_status']=='KNOWN'
    assert result['ledger']['stage_runs']==dict(generate=generation,source=source_id,cold=cold_id)
    assert all(slot['accepted'] for slot in result['ledger']['slots'])
    assert [v['stage'] for v in wire]==['generate']*3+['source']*2+['cold']*2
    times=[v['reserved_at'] for v in result['ledger']['slots']]
    assert all(b-a>=60 for a,b in zip(times,times[1:])) and times[-1]>c.prepared_at+300
    assert all(v['at']<v['run_created_at']+300 for v in wire)
    assert len(paced_waits)==7
    for stage,rid in [('generate',generation),('source',source_id),('cold',cold_id)]:
        assert coordinator.recover(store,user,binding,stage)['run_id']==rid
    with store.tx() as conn:
        associated=conn.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.kind.in_([coordinator.ASSOCIATION,coordinator.ASSOCIATION+'_seal']))).mappings().all()
        assert len(associated)==12
        for stage,rid,count in [('generate',generation,3),('source',source_id,2),('cold',cold_id,2)]:
            actual=conn.execute(select(attempts).where(attempts.c.run_id==rid)).mappings().all()
            assert len(actual)==count
            assert all(a['parameters']['pa_trial_binding']==dict(version='pa-trial-dispatch.v1',
                trial_fingerprint=binding.contract_fingerprint,approval_key=binding.approval_key) for a in actual)
            assert all(a['mode']=='MOCK' for a in actual)
            assert all(a['status']==('RECEIVED' if stage=='generate' else 'VERIFIED') for a in actual)
            charge=[slot for slot in result['ledger']['slots'] if slot['reservation']['stage']==stage]
            assert {s['reservation']['request_key'] for s in charge}=={a['id'] for a in actual}
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
    fee=gate.SyntheticOnlyFeeAuthority(fingerprint(c.model_dump()),c.quota_subject)
    replay=budget.reserve(store,user,ledger_scope,c,budget.Reservation.model_validate(result['ledger']['slots'][0]['reservation']),admission=partial(gate.admit,fee_authority=fee))
    assert replay['duplicate'] and replay['dispatch_authorized'] is False and replay['ledger']==result['ledger']
    assert records(store)==before
    (tmp_path/'ACTUAL_V2_SEVEN_SLOTS.json').write_text(json.dumps(dict(contract=c.model_dump(),source=source.model_dump(),cold=cold.model_dump(),
        accounting=result,wire=wire,permits=permits,clock_events=clock_events,paced_waits=paced_waits,
        kind='OFFLINE_ASSOCIATED_V2_CONTROLLER_MICROTICK_CLOCK_NOT_LIVE',synthetic_qualification_override=True,
        actual_sends=7,stage_send_counts=[len(generation_sent),len(source_sent),len(cold_sent)],
        clock_tick_seconds=0.000001,clock_tick_thread_serialized=True,actual_model_requests=0),indent=2))
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
