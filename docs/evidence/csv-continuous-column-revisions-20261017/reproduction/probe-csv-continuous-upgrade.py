import json,shutil,time
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,app_drafts,internal_instances
src=Path('/tmp/csv-continuous-dev-first-20261017/test_current_effective_parent_0/fixture.db')
root=Path('/tmp/csv-continuous-upgrade-probe-20261017');root.mkdir(exist_ok=True)
dst=root/'fixture.db';assert not dst.exists();shutil.copyfile(src,dst)
url='sqlite:///'+str(dst);store=Store(url,test_only=True);settings=Settings(url,root,mode='mock')
with store.tx() as c:
 rows=c.execute(select(internal_instances).where(internal_instances.c.revision==2)).mappings().all();assert len(rows)==1;instance=dict(rows[0])
 draft=c.execute(select(app_drafts).where(app_drafts.c.id==instance['source_app_id'])).mappings().one();fp=draft['fingerprint']
client=TestClient(create_app(store,settings));client.headers['Authorization']='Bearer synthetic-test-A';trace=[]
def request(method,path,body=None):
 start=time.time();r=client.request(method,path,json=body);trace.append(dict(method=method,path=path,body=body,status=r.status_code,response=r.json(),elapsed_seconds=time.time()-start));return r
base=f"/api/projects/{instance['project_id']}/apps/{instance['source_app_id']}/delivery-graph";path=f"/api/internal/instances/{instance['id']}/csv-goal-revisions/context"
try:
 request('GET',f"/api/internal/instances/{instance['id']}")
 before=request('GET',path)
 derive=request('POST',base+'/derive',dict(request_key='explicit-upgrade-baseline',expected_candidate_fingerprint=fp))
 after=request('GET',path)
 print(json.dumps(dict(before=before.status_code,before_error=before.json().get('error'),derive=derive.status_code,after=after.status_code,after_error=after.json().get('error')),ensure_ascii=False),flush=True)
finally:
 (root/'actual-http.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2));client.close();store.engine.dispose()
