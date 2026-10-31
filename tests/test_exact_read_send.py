"""Late wire-boundary faults with synthetic transport only; never real networking."""

import copy
import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select, update
from test_exact_read import ExactModel, prepare

from sim2act.api import create_app
from sim2act.db import attempts, grants, quotas, reservations, runs
from sim2act.model import CapturedResponse, InternModel
from sim2act.worker import Worker


@pytest.mark.parametrize("fault", ["none", "reservation-delete", "reservation-subject", "attempt-status",
    "request-fingerprint", "first-unknown", "first-response", "worker-owner", "callback-revoke", "callback-worker",
    "reservation-time", "quota-blocked", "lower-wire-budget", "wire-thinking", "wire-tool-choice"])
def test_late_send_rechecks_actual_reserved_attempt_and_original_owner(env, monkeypatch, fault):
    settings=replace(env[1],mode="live",live_enabled=True,token="SYNTHETIC_TRANSPORT_ONLY")
    client=TestClient(create_app(env[0],settings));client.headers['Authorization']='Bearer synthetic-test-A'
    local=(env[0],settings,client,*env[3:])
    rid,resource,_,_=prepare(local)
    sends=[];model=ExactModel();connections=[];armed=[False]
    def callback(c):
        if not armed[0]:return
        armed[0]=False
        if fault=='callback-revoke':
            c.connection.driver_connection.execute('UPDATE grants SET revoked=1 WHERE resource_id=?',(resource,))
        else:
            c.connection.driver_connection.execute('UPDATE runs SET worker_id=? WHERE id=?',('worker_changed',rid))
    def connected(c):
        event.listen(c,'commit',callback)
    def synthetic_sender(adapter,body,wire_guard,*,_stop_event=None):
        assert _stop_event is not None
        phase=len(sends)
        trigger=phase==(1 if fault in {'first-unknown','first-response'} else 0)
        if trigger and fault!='none':
            with env[0].tx() as c:
                current=dict(c.execute(select(attempts).where(attempts.c.run_id==rid,attempts.c.status=='STARTED')).mappings().one())
                if fault=='reservation-delete':c.execute(delete(reservations).where(reservations.c.id==current['id']))
                elif fault=='reservation-subject':c.execute(update(reservations).where(reservations.c.id==current['id']).values(subject='other'))
                elif fault=='reservation-time':c.execute(update(reservations).where(reservations.c.id==current['id']).values(created_at=current['created_at']-1))
                elif fault=='quota-blocked':c.execute(update(quotas).values(blocked_until=current['created_at']+100))
                elif fault=='lower-wire-budget':
                    contexts=[cell.cell_contents for cell in wire_guard.__closure__
                              if type(cell.cell_contents) is dict and 'reserved_tokens' in cell.cell_contents]
                    assert len(contexts)==1
                    context=contexts[0];params=copy.deepcopy(current['parameters'])
                    from sim2act.db import fingerprint
                    payload=json.loads(body);payload['max_tokens']=512
                    reserved=len(json.dumps(payload,ensure_ascii=False).encode())+512
                    delta=current['reserved_tokens']-reserved;assert delta>0
                    params['max_tokens']=512;params['request_fingerprint']=fingerprint(payload)
                    context['reserved_tokens']-=delta
                    c.execute(update(attempts).where(attempts.c.id==current['id']).values(
                        parameters=params,reserved_tokens=current['reserved_tokens']-delta))
                    c.execute(update(runs).where(runs.c.id==rid).values(context=context))
                elif fault=='attempt-status':c.execute(update(attempts).where(attempts.c.id==current['id']).values(status='FAILED'))
                elif fault=='request-fingerprint':
                    params=copy.deepcopy(current['parameters']);params['request_fingerprint']='0'*64
                    c.execute(update(attempts).where(attempts.c.id==current['id']).values(parameters=params))
                elif fault in {'first-unknown','first-response'}:
                    prior=c.execute(select(attempts.c.id).where(attempts.c.run_id==rid,attempts.c.id!=current['id'])).scalar_one()
                    c.execute(update(attempts).where(attempts.c.id==prior).values(**(
                        {'status':'STARTED'} if fault=='first-unknown' else {'response':{'role':'assistant','content':'changed'}})))
                elif fault=='worker-owner':c.execute(update(runs).where(runs.c.id==rid).values(worker_id='worker_changed'))
            if fault.startswith('callback-'):
                armed[0]=True;event.listen(env[0].engine,'engine_connect',connected);connections.append(True)
        request=json.loads(body)
        assert request['thinking_mode'] is False
        assert request['tool_choice']==({'type':'function','function':{'name':'resource.read'}} if phase==0 else 'none')
        if fault=='wire-thinking':request['thinking_mode']=True
        if fault=='wire-tool-choice':request['tool_choice']='auto'
        wire_guard(httpx.Request('POST',InternModel.ENDPOINT,content=json.dumps(request,ensure_ascii=False).encode()))
        sends.append(body)
        raw=model.request(request['messages'],request['tools']);raw['model']='Intern-S2'
        return CapturedResponse(raw,json.dumps(raw).encode())
    monkeypatch.setattr(InternModel,'request_serialized_captured',synthetic_sender)
    try:
        assert Worker(env[0],settings).once()
    finally:
        if connections:event.remove(env[0].engine,'engine_connect',connected)
        client.close()
    expected=2 if fault=='none' else 1 if fault in {'first-unknown','first-response'} else 0
    assert len(sends)==expected
    with env[0].engine.connect() as c:
        r=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
        assert (r['status']=='SUCCEEDED')==(fault=='none')
        if fault=='lower-wire-budget':assert r['error']['message']=='Reserved output budget differs from the actual wire'


def test_original_eight_second_contract_keeps_old_wire_and_duplicate_key(env,monkeypatch):
    from sim2act import exact_read
    original=exact_read.select_policy
    def legacy(*args,**kwargs):
        policy=original(*args,**kwargs)
        if kwargs.get('prior') is None:
            policy['exact_read'].pop('request_protocol')
            policy['exact_read']['request_timeout_seconds']=8
        return policy
    monkeypatch.setattr(exact_read,'select_policy',legacy)
    rid,_,body,_=prepare(env)
    monkeypatch.setattr(exact_read,'select_policy',original)
    assert env[2].post(f'/api/projects/{env[5]}/runs',json=body).json()['run_id']==rid
    assert Worker(env[0],env[1],ExactModel()).once()
    result=env[2].get('/api/runs/'+rid).json()
    assert result['status']=='SUCCEEDED'
    spec=result['contract']['snapshot']['exact_read']
    assert spec['request_timeout_seconds']==8 and 'request_protocol' not in spec
    with env[0].engine.connect() as c:
        aa=c.execute(select(attempts).where(attempts.c.run_id==rid)).mappings().all()
        assert len(aa)==2 and all('exact_read_request_protocol' not in a['parameters'] for a in aa)
        contract=env[0].frozen_contract(c,c.execute(select(runs).where(runs.c.id==rid)).mappings().one())
        payload=exact_read.wire_payload(contract,[],[],1024)
        assert set(payload)=={'model','messages','tools','stream','max_tokens'}


@pytest.mark.parametrize('stopped_response',['returned','captured-error'])
def test_stop_after_received_response_never_dispatches_and_keeps_real_usage(env,monkeypatch,stopped_response):
    from sim2act.db import operations
    from sim2act.model import _RequestDeadlineError
    settings=replace(env[1],mode='live',live_enabled=True,token='SYNTHETIC_TRANSPORT_ONLY')
    client=TestClient(create_app(env[0],settings));client.headers['Authorization']='Bearer synthetic-test-A'
    rid,_,_,_=prepare((env[0],settings,client,*env[3:]))
    worker=Worker(env[0],settings)
    def stopped(adapter,body,guard,*,_stop_event=None):
        guard(httpx.Request('POST',InternModel.ENDPOINT,content=body))
        payload=json.loads(body);raw=ExactModel().request(payload['messages'],payload['tools'])
        raw['model']='Intern-S2';worker.stop.set()
        if stopped_response=='captured-error':
            failure=_RequestDeadlineError('MODEL_TIMEOUT_OR_TRUNCATED','Synthetic stop after complete response')
            failure._received_response=raw
            raise failure
        return CapturedResponse(raw,json.dumps(raw).encode())
    monkeypatch.setattr(InternModel,'request_serialized_captured',stopped)
    assert worker.once()
    with env[0].engine.connect() as c:
        run=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
        assert run['status']==('PAUSED' if stopped_response=='returned' else 'FAILED')
        aa=c.execute(select(attempts).where(attempts.c.run_id==rid)).mappings().all()
        assert len(aa)==1 and aa[0]['usage']['tokens']['total_tokens']==20
        assert aa[0]['response_model']=='Intern-S2'
        assert not c.execute(select(operations).where(operations.c.run_id==rid)).first()
    client.close()
