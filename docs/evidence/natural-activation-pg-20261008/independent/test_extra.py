import copy,time,json
from types import SimpleNamespace
from sqlalchemy import select,update
from test_independent import *
from sim2act import worker as wm
from sim2act.db import events,run_contracts

def test_actual_ordinary_pre_reservation_aged65_blocks_final_sender(env,monkeypatch):
 v=setup(env);session,_=approved(v);s,settings,client=v[:3];ordinary=s.submit(env[3],v[5],'普通已占槽但未发送',[v[-2]],'actual-legacy-pending');legacy=Worker(s,settings);claimed=s.claim(legacy.id,settings.lease_seconds);assert claimed['id']==ordinary
 aid=legacy.reserve(ordinary,claimed['fence'],dict(claimed['context']))
 activated=submit(v,session).json()['run_id'];future=time.time()+65
 monkeypatch.setattr(a,'now',lambda:future);monkeypatch.setattr(wm,'time',SimpleNamespace(time=lambda:future,monotonic=time.monotonic))
 sent=[];assert Worker(s,settings,goal_planner_transport=httpx.MockTransport(lambda r:(sent.append(1),httpx.Response(200,json=hand(v)))[1])).once()
 ar=rows(s,attempts);assert not sent and len(ar)==2 and not rows(s,operations);assert any(x['id']==aid and x['status']=='STARTED' for x in ar)
 actual=client.get('/api/runs/'+activated).json();assert actual['error']['code']=='RATE_LIMITED';info=client.get('/api/natural-activations/'+session['id']).json();assert info['charged_requests']==1
 evidence(v,'actual-aged65.json',{'sent':0,'attempts':2,'ordinary_attempt_retained_started':True,'activation_reserved_not_refunded':info['charged_requests'],'error':'RATE_LIMITED'})

def test_deadline_mirror_and_event_coherent_float_change_reject(env):
 v=setup(env);session,_=approved(v);s,settings,client=v[:3];rid=submit(v,session).json()['run_id']
 with s.tx() as c:
  row=c.execute(select(runs).where(runs.c.id==rid)).mappings().one();ctx=copy.deepcopy(row['context']);ctx['natural_run_deadline']['deadline']+=1;ev=c.execute(select(events).where(events.c.run_id==rid,events.c.kind=='NL_RUN_DEADLINE_FROZEN')).mappings().one();c.execute(update(events).where(events.c.id==ev['id']).values(data=ctx['natural_run_deadline']));c.execute(update(runs).where(runs.c.id==rid).values(context=ctx))
 def fp():
  with s.tx() as c:return fingerprint({t.name:[dict(x) for x in c.execute(select(t)).mappings()] for t in runs.metadata.sorted_tables})
 before=fp();bad=client.get('/api/runs/'+rid);after=fp();assert bad.status_code==409 and before==after
 sent=[];assert Worker(s,settings,goal_planner_transport=httpx.MockTransport(lambda r:(sent.append(1),httpx.Response(200,json=hand(v)))[1])).once();assert not sent and not rows(s,attempts) and not rows(s,operations)
 evidence(v,'deadline-tamper.json',{'get':409,'before_fp':before,'after_fp':after,'sent':0,'attempts':0,'operations':0})
