"""Absolute network budget vs rolling heartbeat, without changing business time."""
import threading,time
from types import SimpleNamespace
import pytest
from sim2act.production_trial_sender import _generation_http_deadline,_generation_network_watch
from sim2act.errors import DomainError


def fixture():
    now=time.time()
    return (SimpleNamespace(caps=SimpleNamespace(run_seconds=300),expires_at=now+250),
        SimpleNamespace(run_seconds=300),{'created_at':now},
        {'generation_heartbeat':True,'lock':threading.Lock(),'failure':None,'lease_until':now+30,'deadline':now+300},
        now+240,{'deadline':now+200})


def test_valid_rolling_lease_does_not_shorten_original_network_budget():
    args=fixture();deadline=_generation_http_deadline(*args)
    assert deadline==args[-1]['deadline'] and deadline>args[3]['lease_until']
    args[3]['lease_until']+=20
    assert _generation_http_deadline(*args)==deadline,'renewal cannot extend original HTTP deadline'


@pytest.mark.parametrize('fault',['lost','expired','absolute','source','controller'])
def test_lost_or_expired_authority_never_gets_more_network_time(fault):
    args=list(fixture())
    if fault=='lost':args[3]['failure']=RuntimeError('lost lease')
    elif fault=='expired':args[3]['lease_until']=time.time()-1
    elif fault=='absolute':args[3]['deadline']=time.time()-1
    elif fault=='source':args[4]=time.time()-1
    else:args[5]={'deadline':time.time()-1}
    with pytest.raises(DomainError):_generation_http_deadline(*args)


@pytest.mark.parametrize('fault',['lost','expired','cancel'])
def test_inflight_watch_stops_on_lost_lease_or_cancellation(fault):
    state=fixture()[3];worker=SimpleNamespace(stop=threading.Event())
    stopped,done,thread=_generation_network_watch(worker,state)
    try:
        assert not stopped.is_set()
        if fault=='cancel':worker.stop.set()
        else:
            with state['lock']:
                if fault=='lost':state['failure']=RuntimeError('heartbeat failed')
                else:state['lease_until']=time.time()-1
        assert stopped.wait(1)
    finally:done.set();thread.join(1)
    assert not thread.is_alive()


def test_watch_accepts_renewals_but_never_changes_absolute_deadline():
    args=fixture();state=args[3];worker=SimpleNamespace(stop=threading.Event())
    original=_generation_http_deadline(*args)
    stopped,done,thread=_generation_network_watch(worker,state)
    try:
        for _ in range(3):
            with state['lock']:state['lease_until']=time.time()+30
            assert not stopped.wait(.03)
        assert _generation_http_deadline(*args)==original
    finally:done.set();thread.join(1)
    assert not thread.is_alive()


@pytest.mark.parametrize('cancel',[False,True])
def test_actual_captured_http_waits_past_initial_lease_or_cancels(cancel):
    import asyncio,httpx
    from sim2act.model import InternModel
    args=list(fixture());state=args[3];worker=SimpleNamespace(stop=threading.Event())
    state['lease_until']=time.time()+1;state['deadline']=time.time()+5
    async def response(request):
        await asyncio.sleep(1.2)
        return httpx.Response(200,json={'received':True})
    provider=InternModel(SimpleNamespace(live_enabled=True,token='synthetic-not-provider-token',model='intern-s2'),httpx.MockTransport(response))
    stopped,done,thread=_generation_network_watch(worker,state)
    def change():
        time.sleep(.03)
        if cancel:worker.stop.set()
        else:
            with state['lock']:state['lease_until']=time.time()+5
    changer=threading.Thread(target=change);changer.start()
    try:
        call=lambda:provider.request_serialized_captured(b'{"model":"intern-s2"}',lambda request:{'deadline':_generation_http_deadline(*args)},_stop_event=stopped)
        if cancel:
            with pytest.raises(DomainError) as error:call()
            assert error.value.code=='MODEL_TIMEOUT_OR_TRUNCATED'
        else:assert call().parsed=={'received':True}
    finally:done.set();thread.join(1);changer.join(1)
    assert not thread.is_alive()
