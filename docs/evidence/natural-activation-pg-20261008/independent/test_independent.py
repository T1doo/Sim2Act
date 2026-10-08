import asyncio,json,time
from dataclasses import replace
from pathlib import Path
import httpx,pytest
from sqlalchemy import select
from conftest import env
from test_natural_activation_flow import setup,approved,submit
from sim2act import natural_activations as a,goal_planner as gp
from sim2act.db import attempts,operations,quotas,reservations,runs,fingerprint
from sim2act.worker import Worker
from sim2act.model import InternModel,MockModel
from sim2act.errors import DomainError

def rows(s,t):
 with s.tx() as c:return [dict(x) for x in c.execute(select(t)).mappings()]
def evidence(v,name,data):Path(v[1].data_dir/name).write_text(json.dumps(data,indent=2))
def hand(v):
 return {'model':'Intern-S2','usage':{'prompt_tokens':11,'completion_tokens':22,'total_tokens':33},'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps({'version':'natural-goal-plan.v1','source_goal_fingerprint':v[-1]['sum_quantity_z']['fingerprint'],'interpretation':{'objective':'independent sum','assumptions':['meaning unknown'],'unresolved':['not accepted']},'steps':[{'id':'sum_q','tool_ref':'data.aggregate_csv','resource_id':v[-2],'column':'quantity_z','depends_on':[]}]})}}]}
@pytest.mark.parametrize('point',['aged_before_claim','aged_before_guard','aged_after_response'])
def test_frozen_age_never_executes(env,monkeypatch,point):
 v=setup(env);session,_=approved(v);rid=submit(v,session).json()['run_id'];s,settings,client=v[:3];created=rows(s,runs)[0]['created_at'];sent=[]
 def handler(req):
  sent.append(1)
  if point=='aged_after_response':monkeypatch.setattr(a,'now',lambda:created+121)
  return httpx.Response(200,json=hand(v))
 if point=='aged_before_claim':monkeypatch.setattr(a,'now',lambda:created+121)
 if point=='aged_before_guard':
  original=gp.configured_provider
  def provider(w):
   model=original(w);orig=model.request_serialized
   def send(body,guard):monkeypatch.setattr(a,'now',lambda:created+121);return orig(body,guard)
   model.request_serialized=send;return model
  monkeypatch.setattr(gp,'configured_provider',provider)
 assert Worker(s,settings,goal_planner_transport=httpx.MockTransport(handler)).once();assert not rows(s,operations);assert len(sent)==(1 if point=='aged_after_response' else 0)
 ar=rows(s,attempts);assert len(ar)==(0 if point=='aged_before_claim' else 1)
 if point=='aged_after_response':assert ar[0]['response'] and ar[0]['usage']['tokens']['total_tokens']==33
 assert client.get('/api/runs/'+rid).status_code==200
 evidence(v,point+'.json',{'sent':len(sent),'attempts':len(ar),'operations':0,'known_usage':ar[0]['usage'] if ar else None,'ledger_charge':client.get('/api/natural-activations/'+session['id']).json()['charged_requests']})
def test_account_cooldown_blocks_ordinary_sender(env,monkeypatch):
 v=setup(env);session,_=approved(v);s,settings,client=v[:3];first=submit(v,session).json()['run_id'];sent=[]
 assert Worker(s,settings,goal_planner_transport=httpx.MockTransport(lambda r:(sent.append(1),httpx.Response(200,json=hand(v)))[1])).once()
 ordinary=s.submit(env[3],v[5],'普通材料读取',[v[-2]],'ind-ordinary')
 monkeypatch.setattr(MockModel,'request',lambda *args:pytest.fail('ordinary sender bypassed cooldown'))
 assert Worker(s,settings).once();assert len(rows(s,attempts))==1 and len(rows(s,reservations))==1 and len(sent)==1 and not rows(s,operations)
 state=client.get('/api/runs/'+ordinary).json();assert state['error']['code']=='RATE_LIMITED'
 evidence(v,'ordinary-cooldown.json',{'ordinary_state':state['status'],'error':state['error']['code'],'attempts':1,'quota_blocked_until':rows(s,quotas)[0]['blocked_until'],'first_run':first})
def test_both_cooperative_closers_bounded(env):
 trace=[]
 class Stream(httpx.AsyncByteStream):
  async def __aiter__(self):trace.append('read');await asyncio.sleep(1);yield b'{}'
  async def aclose(self):trace.append('response-close');await asyncio.sleep(1);trace.append('response-closed')
 class Transport(httpx.MockTransport):
  async def aclose(self):trace.append('transport-close');await asyncio.sleep(1);trace.append('transport-closed')
 async def handler(req):return httpx.Response(200,stream=Stream())
 model=InternModel(replace(env[1],live_enabled=True,token='synthetic-only'),transport=Transport(handler));start=time.monotonic()
 with pytest.raises(DomainError) as e:model.request_serialized(b'{}',lambda r:{'deadline':time.time()+.04})
 elapsed=time.monotonic()-start;assert e.value.code=='MODEL_TIMEOUT_OR_TRUNCATED' and elapsed<.25;assert trace==['read','response-close','transport-close'],trace
 (env[1].data_dir/'close.json').write_text(json.dumps({'elapsed':elapsed,'trace':trace,'code':e.value.code}))
