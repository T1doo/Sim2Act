"""Validate global hard cap and conservative crash/error halting without network."""
import json
import tempfile
from pathlib import Path

import httpx

from send_guard import ENDPOINT, Guard
from sim2act.errors import DomainError
from sim2act.tools import definitions

out=Path(__file__).resolve().parent
checks=[]
with tempfile.TemporaryDirectory(prefix='at02-guard-offline-') as root:
    p=Path(root);groups=[{'label':'A','resource_id':'res_'+'a'*32},{'label':'B','resource_id':'res_'+'b'*32}]
    (p/'fixture.json').write_text(json.dumps({'groups':groups}))
    g=Guard(p);g.save({'requests':[],'blocked':[],'halted':False})
    calls=[]
    def original(client,request,**kwargs):
        calls.append(1)
        return httpx.Response(200,json={'model':'Intern-S2','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'42'}}],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
    def request(n):
        return httpx.Request('POST',ENDPOINT,json={'model':'intern-s2','max_tokens':512,'stream':False,'tools':definitions(),'messages':[{'role':'user','content':json.dumps({'goal':'Read; echo.','resource_refs':[groups[n%2]['resource_id']]})}]})
    for n in range(4):
        g.send(original,None,request(n))
        j=json.loads(g.path.read_text());j['last_response_at']=0;g.save(j) # OFFLINE avoid artificial wait, never used live.
    try:g.send(original,None,request(0))
    except DomainError:checks.append('fifth request blocked before original; exactly four called')
    assert len(calls)==4
    g.save({'requests':[],'blocked':[],'halted':False})
    def crash(client,request,**kwargs):raise httpx.ReadTimeout('SYNTHETIC offline timeout')
    try:g.send(crash,None,request(0))
    except httpx.ReadTimeout:pass
    assert json.loads(g.path.read_text())['halted']
    try:g.send(original,None,request(1))
    except DomainError:checks.append('unknown/error consumes durable slot and halts next sender')
    assert len(calls)==4 and len(json.loads(g.path.read_text())['requests'])==1
    g.save({'requests':[],'blocked':[],'halted':False})
    oversized=request(0);body=json.loads(oversized.content);body['messages'].append({'role':'assistant','content':'x'*2000})
    try:g.send(original,None,httpx.Request('POST',ENDPOINT,json=body))
    except DomainError:checks.append('oversized complete body rejected before any slot/network')
    assert len(json.loads(g.path.read_text())['requests'])==0 and len(calls)==4
    g.save({'requests':[],'blocked':[],'halted':False})
    def invalid(client,request,**kwargs):return httpx.Response(200,content=b'not json')
    g.send(invalid,None,request(0))
    assert json.loads(g.path.read_text())['halted']
    try:g.send(original,None,request(1))
    except DomainError:checks.append('HTTP200 malformed reply halts all subsequent sends')
    assert len(calls)==4
(out/'guard-offline-results.json').write_text(json.dumps({'kind':'MOCK transport-boundary logic only','external_requests':0,'checks':checks,'status':'PASS'},indent=2)+'\n')
print('Global guard offline: 4 PASS; external requests 0')
