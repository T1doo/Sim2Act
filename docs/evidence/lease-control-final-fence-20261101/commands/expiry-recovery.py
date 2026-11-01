import sqlite3,json,subprocess,hashlib
from pathlib import Path
from sim2act.db import Store
from sim2act.config import Settings
from sim2act.worker import Worker
expected='31edad3f734efd923ffc28a2af487802fff2b4c2'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==expected
root=Path('/workspace/scratch/lease-fence-large-cancel-v1-20261101/test_actual_large_writer_cance0');p=root/'fixture.db'
prior=root/'before-expiry-recovery.sqlite';assert prior.is_file()
with sqlite3.connect(p) as current,sqlite3.connect(root/'after-first-expiry-recovery.sqlite') as saved:current.backup(saved)
identity=p.stat().st_dev,p.stat().st_ino
with sqlite3.connect(prior) as saved,sqlite3.connect(p) as current:saved.backup(current)
assert (p.stat().st_dev,p.stat().st_ino)==identity
s=Store('sqlite:///'+str(p),test_only=True);settings=Settings('sqlite:///'+str(p),root,mode='mock');rt=s._enable_authoritative_leases(settings,create=False)
def protected():
 with s.engine.connect() as c:
  names=['attempts','operations','operation_intents','internal_instance_data','delivery_graph_requests','run_contracts','local_lease_control_receipts']
  data={name:sorted([list(r) for r in c.exec_driver_sql('SELECT * FROM '+name)],key=lambda r:json.dumps(r,default=str)) for name in names}
 return hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()
before=protected()
with s.engine.connect() as c:rid,user=c.exec_driver_sql("SELECT id,principal_id FROM runs WHERE status='RUNNING'").one()
assert Worker(s,settings).once() is False
value=s.inspect(user,rid);assert value['status']=='FAILED' and value['error']['code']=='BUDGET_EXHAUSTED'
assert Worker(s,settings).once() is False
assert protected()==before
with rt.authority.connection() as c:assert c.execute('SELECT state FROM leases WHERE run_id=?',(rid,)).fetchone()==('CLOSED',)
report={'source_commit':expected,'status':'PASS','scenario':'original before-image, control already CLOSED as crash-before-main-close case','run_status':'FAILED','error':'BUDGET_EXHAUSTED','protected_rows_sha256':before,'original_timestamps_unchanged':True,'new_model_requests':0,'repeat_no_replay':True}
Path('/workspace/scratch/lease-fence-frozen-expiry-recovery-31edad3-20261101.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));s.engine.dispose()
