"""Private copy of completed G1-cancel case, original default reconciliation.
No provider/clock replacement, no model permission; outbound socket forbidden.
"""
from pathlib import Path
import hashlib,json,sqlite3,shutil,sys,time
from sqlalchemy import select
from fastapi.testclient import TestClient
from sim2act.db import Store,runs,attempts,internal_run_bindings,internal_app_runs
from sim2act.config import Settings
from sim2act.worker import Worker
from sim2act.api import create_app

def audit(name,args):
 if name=='socket.connect' and type(args[1]) is tuple and args[1][0] not in ('127.0.0.1','::1'):
  raise RuntimeError('No outbound connection in cancel reconciliation')
sys.addaudithook(audit)
source=Path(sys.argv[1]);target=Path(sys.argv[2]);target.mkdir(exist_ok=False)
wal=Path(str(source)+'-wal');assert not wal.exists() or wal.stat().st_size==0
before_sha=hashlib.sha256(source.read_bytes()).hexdigest();db=target/'fixture.db';shutil.copyfile(source,db)
def saved():
 c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
 try:return {t:c.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall() for t in ('attempts','operations','resources','delivery_graph_requests','internal_instance_data')}
 finally:c.close()
before=saved();expected={k:list(v) for k,v in before.items()};store=Store('sqlite:///'+str(db),test_only=True);settings=Settings(str(store.engine.url),target,mode='mock')
try:
 with store.tx() as c:
  row=dict(c.execute(select(runs).where(runs.c.status=='RECONCILING',runs.c.cancel_intent.is_(True))).mappings().one())
  iid=c.execute(select(internal_app_runs.c.instance_id).join(internal_run_bindings,internal_run_bindings.c.app_run_id==internal_app_runs.c.id).where(internal_run_bindings.c.run_id==row['id'])).scalar_one()
  received=dict(c.execute(select(attempts).where(attempts.c.run_id==row['id'],attempts.c.status=='RECEIVED')).mappings().one())
  operation_id=received['parameters']['natural_spec']['operation_id']
 for table,ident,old_status in [('attempts',received['id'],'RECEIVED'),('operations',operation_id,'DISPATCHED')]:
  connection=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
  try:columns=[r[1] for r in connection.execute('PRAGMA table_info('+table+')')]
  finally:connection.close()
  matches=[i for i,r in enumerate(expected[table]) if r[columns.index('id')]==ident]
  assert len(matches)==1
  i=matches[0];values=list(expected[table][i]);assert values[columns.index('status')]==old_status
  values[columns.index('status')]='REJECTED_KNOWN';expected[table][i]=tuple(values)

 worker=Worker(store,settings);claimed=worker.once()
 with store.tx() as c:after=dict(c.execute(select(runs).where(runs.c.id==row['id'])).mappings().one())
 assert after['status']=='CANCELLED'
 with TestClient(create_app(store,settings)) as client:
  client.headers['Authorization']='Bearer synthetic-test-A'
  response=client.post(f'/api/internal/instances/{iid}/runs/{row["id"]}/commands',json={'command':'cancel','version':after['version']})
  assert response.status_code==200 and response.json()['status']=='CANCELLED'
 assert saved()==expected
finally:store.engine.dispose()
second=Store('sqlite:///'+str(db),test_only=True)
try:
 again=Worker(second,settings).once()
 with second.tx() as c:final=dict(c.execute(select(runs).where(runs.c.id==row['id'])).mappings().one())
 assert final['status']=='CANCELLED' and saved()==expected and again is False
finally:second.engine.dispose()
assert hashlib.sha256(source.read_bytes()).hexdigest()==before_sha
result={'status':'PASS','source_commit':sys.argv[3],'scope':'DEFAULT_MOCK_WORKER_PRIVATE_COPY_OF_REAL_G1_CANCEL_FIXTURE_NOT_LIVE_NOT_PG','first_once':claimed,'after_first':after['status'],'repeat_cancel_http':response.status_code,'repeat_cancel_status':response.json()['status'],'second_fresh_store_once':again,'final':final['status'],'all_non_target_rows_unchanged':True,'target_status_only_transitions':{'attempt':'RECEIVED→REJECTED_KNOWN','operation':'DISPATCHED→REJECTED_KNOWN'},'target_response_usage_and_other_columns_unchanged':True,'source_database_unchanged':True,'source_db_sha256':before_sha,'new_model_attempts':0,'outbound_socket_guard':True,'lease_expired_at_start':row['lease_until']<time.time()}
(target/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
