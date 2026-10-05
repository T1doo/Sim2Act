import asyncio,tempfile
from pathlib import Path
import uvicorn
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
root=Path(tempfile.mkdtemp(prefix='sim2act-goal-candidate-'))
store=Store('sqlite:///'+str(root/'fixture.db'),test_only=True);store.initialize()
store.user('SYNTHETIC race/candidate','synthetic-candidate-browser')
app=create_app(store,Settings('sqlite:///'+str(root/'fixture.db'),root,mode='mock'))
cid=None
@app.middleware('http')
async def delayed_card_read(request,call_next):
 if request.method=='GET' and request.url.path==f'/api/goal-cards/{cid}': await asyncio.sleep(2)
 return await call_next(request)
with TestClient(app) as c:
 c.headers.update({'Authorization':'Bearer synthetic-candidate-browser'})
 pa=c.post('/api/projects',json={'name':'SYNTHETIC 项目A'}).json()['id']
 pb=c.post('/api/projects',json={'name':'SYNTHETIC 项目B'}).json()['id']
 rid=c.post(f'/api/projects/{pa}/resources',json={'name':'合成销售.csv','format':'csv','content':'amount,quantity\n1.25,7\n2.75,8\n'}).json()['id']
 data={'title':'项目A固定汇总目标','goal':'汇总所选CSV的数值列','known':['合成销售材料'],'assumptions':[],'unresolved':['真实语义尚未验收'],'constraints':['只读不外发'],'acceptance_checks':['列合计与材料一致'],'resource_refs':[rid]}
 cid=c.post(f'/api/projects/{pa}/goal-cards',json=data).json()['id']
print(f'SYNTHETIC race fixture pa={pa} pb={pb} card={cid} rid={rid} port=8070',flush=True)
uvicorn.run(app,host='127.0.0.1',port=8070,access_log=False)
