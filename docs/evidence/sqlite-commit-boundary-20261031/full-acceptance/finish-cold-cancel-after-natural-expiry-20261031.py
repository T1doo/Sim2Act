"""Fresh default worker on a private copy; wait for the real original lease."""
import datetime,hashlib,json,os,shutil,subprocess,sys,threading,time
from pathlib import Path
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store,runs,attempts,operations,internal_app_runs,internal_instance_data,internal_run_bindings,delivery_graph_requests,reservations,resources
from sim2act.model import MockModel,InternModel
from sim2act.worker import Worker
source=Path(sys.argv[1]);root=Path(sys.argv[2]);root.mkdir();sha=sys.argv[3];target=sys.argv[4]
assert not Path(str(source)+'-wal').exists() or Path(str(source)+'-wal').stat().st_size==0
before_sha=hashlib.sha256(source.read_bytes()).hexdigest();path=root/'fixture.db';shutil.copyfile(source,path)
store=Store('sqlite:///'+str(path),test_only=True);settings=Settings('sqlite:///'+str(path),root,mode='mock')
calls=[]
def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('Recovery cannot send')
MockModel.request=InternModel.request=forbidden;httpx.HTTPTransport.handle_request=forbidden
def state():
 with store.tx() as c:
  job=dict(c.execute(select(runs).where(runs.c.id==target)).mappings().one())
  app=dict(c.execute(select(internal_app_runs).join(internal_run_bindings,internal_run_bindings.c.app_run_id==internal_app_runs.c.id).where(internal_run_bindings.c.run_id==target)).mappings().one())
  a=dict(c.execute(select(attempts).where(attempts.c.run_id==job['id'])).mappings().one())
 return job,app,a
def pinned():
 with store.tx() as c:
  return {t.name:[dict(r) for r in c.execute(select(t)).mappings()] for t in
   (delivery_graph_requests,reservations,resources,internal_instance_data)}
job,app,row=state();original_pins=pinned();original=job.copy();before_row=row.copy()
worker=Worker(store,settings);end=time.monotonic()+min(135,max(0,job['lease_until']-time.time())+10)
start=time.monotonic();iterations=0
while time.monotonic()<end:
 iterations+=1;worker.once();job,app,row=state()
 if job['status']=='CANCELLED':break
 assert job['status']=='RECONCILING' and row==before_row
 threading.Event().wait(.2)
assert job['status']==app['status']=='CANCELLED' and row=={**before_row,'status':'REJECTED_KNOWN'}
assert job['version']==original['version']+1 and job['fence']==original['fence']+1 and job['lease_until']==0
assert pinned()==original_pins and not calls
with TestClient(create_app(store,settings)) as client:
 client.headers['Authorization']='Bearer synthetic-test-A'
 base_route=f'/api/internal/instances/{app["instance_id"]}/runs/{job["id"]}'
 progress=client.get(base_route+'/control-progress')
 assert progress.status_code==200 and progress.json()['status']=='CANCELLED'
 route=base_route+'/commands'
 replies=[client.post(route,json=dict(command='cancel',version=job['version'])) for _ in range(2)]
 assert all(r.status_code==200 and r.json()['status']=='CANCELLED' for r in replies)
assert state()[0]['version']==job['version']
store.engine.dispose();store=Store(settings.database_url,test_only=True)
assert Worker(store,settings).once() is False and state()[0]['status']=='CANCELLED' and not calls
store.engine.dispose()
code="""
import json,sys
from pathlib import Path
from sqlalchemy import select
from sim2act.db import Store,runs
from sim2act.config import Settings
from sim2act.worker import Worker
from sim2act.model import MockModel
def forbidden(*a,**k):raise AssertionError('New process cannot replay model')
MockModel.request=forbidden
s=Store(sys.argv[1],test_only=True)
w=Worker(s,Settings(sys.argv[1],Path(sys.argv[2]),mode='mock'))
worked=w.once()
with s.tx() as c:status=c.execute(select(runs.c.status).where(runs.c.id==sys.argv[3])).scalar_one()
print(json.dumps(dict(worked=worked,status=status)));s.engine.dispose()
"""
child=subprocess.run([sys.executable,'-c',code,settings.database_url,str(root),target],capture_output=True,text=True,timeout=30,check=True)
assert json.loads(child.stdout)==dict(worked=False,status='CANCELLED')
output=dict(status='PASS',source_commit=sha,classification='FRESH_PROCESS_REAL_NATURAL_EXPIRY_DEFAULT_WORKER_SYNTHETIC_SQLITE_NOT_LIVE_PG_WINDOWS',
 started_lease_until=original['lease_until'],finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 wait_and_recovery_seconds=time.monotonic()-start,iterations=iterations,original_version=original['version'],final_version=job['version'],
 original_fence=original['fence'],final_fence=job['fence'],run=job['status'],app=app['status'],attempt=row['status'],
 response_usage_unchanged=True,pinned_ledger_archives_reservations_resources_and_typed_data_unchanged=True,
 repeated_cancel_http=[r.status_code for r in replies],repeated_cancel_does_not_increment_version=True,
 fresh_store_worker_does_not_replay=True,fresh_process_worker_does_not_replay=True,control_progress_http=progress.status_code,model_requests=0,input_database_sha256=before_sha,
 input_database_unchanged=before_sha==hashlib.sha256(source.read_bytes()).hexdigest())
(root/'default-recovery.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output));store.engine.dispose()
