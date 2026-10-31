from pathlib import Path
import datetime,hashlib,json,shutil,sys
from fastapi.testclient import TestClient
from sqlalchemy import select
from sim2act.db import Store,runs,attempts,internal_run_bindings,internal_app_runs
from sim2act.config import Settings
from sim2act.worker import Worker
from sim2act.api import create_app
source=Path('/workspace/scratch/owned-retraction-66c6853c-20261031-cancel/test_same_large_cold_snapshot_0/fixture.db')
root=Path('/workspace/scratch/cold-cancel-default-before-20261031');root.mkdir()
assert not Path(str(source)+'-wal').exists() or Path(str(source)+'-wal').stat().st_size==0
copy=root/'fixture.db';shutil.copyfile(source,copy)
store=Store('sqlite:///'+str(copy),test_only=True);settings=Settings(store.engine.url.render_as_string(hide_password=False),root,mode='mock')
with store.tx() as c:
 row=dict(c.execute(select(runs).where(runs.c.status=='RECONCILING',runs.c.cancel_intent.is_(True))).mappings().one())
 aid=c.execute(select(attempts.c.id).where(attempts.c.run_id==row['id'],attempts.c.status=='RECEIVED')).scalar_one()
 iid=c.execute(select(internal_app_runs.c.instance_id).join(internal_run_bindings,internal_run_bindings.c.app_run_id==internal_app_runs.c.id).where(internal_run_bindings.c.run_id==row['id'])).scalar_one()
assert row['lease_until']<__import__('time').time()
worker=Worker(store,settings);claimed=worker.once()
with store.tx() as c:after=dict(c.execute(select(runs).where(runs.c.id==row['id'])).mappings().one())
with TestClient(create_app(store,settings)) as client:
 client.headers['Authorization']='Bearer synthetic-test-A'
 path=f'/api/internal/instances/{iid}/runs/{row["id"]}'
 response=client.post(path+'/commands',json=dict(command='cancel',version=after['version']))
 assert response.status_code==200
 reply=response.json()
store.engine.dispose();second=Store('sqlite:///'+str(copy),test_only=True);again=Worker(second,settings).once()
with second.tx() as c:final=dict(c.execute(select(runs).where(runs.c.id==row['id'])).mappings().one())
r=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),at=datetime.datetime.now(datetime.timezone.utc).isoformat(),run_id=row['id'],attempt_id=aid,instance_id=iid,first_once=claimed,after_first=after['status'],repeat_cancel_http=response.status_code,repeat_cancel=reply,second_fresh_store_once=again,final=final['status'],before_version=row['version'],final_version=final['version'],lease_expired=True,model_requests=0,source_database_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==hashlib.sha256(copy.read_bytes()).hexdigest())
(root/'reproduction.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
second.engine.dispose()
