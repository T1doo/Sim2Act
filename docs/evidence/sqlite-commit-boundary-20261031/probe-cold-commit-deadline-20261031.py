import datetime,json,sys,threading,time
from pathlib import Path
from sqlalchemy import event
sys.path.insert(0,'/workspace/Sim2Act/tests')
from test_sqlite_model_snapshot import opened
from sim2act import _sqlite_model_snapshot as snapshots
root=Path('/workspace/scratch/cold-commit-deadline-before-20261031');root.mkdir()
store=opened(root);token=(time.monotonic()+.15,time.time()+.15);observed={}
with snapshots.transaction(store,settlement_interval=token) as c:
 c.exec_driver_sql('SELECT value FROM probe').scalar();snapshots.promote(c)
 c.exec_driver_sql("UPDATE probe SET value='expired-commit'")
 def callback(connection):
  observed['callback_entered_before_deadline']=time.monotonic()<token[0]
  threading.Event().wait(.2)
  observed['callback_ended_after_deadline']=time.monotonic()>=token[0] and time.time()>=token[1]
 event.listen(c,'commit',callback)
 assert time.monotonic()<token[0] and time.time()<token[1]
with store.tx() as c:observed['value']=c.exec_driver_sql('SELECT value FROM probe').scalar()
observed.update(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit='e7b0916b12e7459fed5c90f5502dde5d7c148420',records=list(store._local_model_snapshot_records),model_requests=0,classification='REAL_CLOCK_LOCAL_SQLITE_POST_CHECK_COMMIT_CALLBACK_COUNTEREXAMPLE_NOT_LARGE_FLOW_TIMING')
(root/'counterexample.json').write_text(json.dumps(observed,indent=2)+'\n');print(json.dumps(observed,indent=2));store.engine.dispose()
