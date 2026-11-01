from pathlib import Path
import sqlite3,json,hashlib
from sim2act.db import Store
from sim2act.config import Settings
root=Path('/workspace/scratch/lease-fence-large-cancel-v3-20261101/test_actual_large_writer_cance0');path=root/'fixture.db'
def snapshot():
 with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as c:
  names=c.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name").fetchall()
  data={n:sorted([list(r) for r in c.execute('SELECT * FROM "'+n+'"')],key=lambda r:json.dumps(r,default=str)) for n, in names}
 return hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()
before=snapshot();s=Store('sqlite:///'+str(path),test_only=True);rt=s._enable_authoritative_leases(Settings('sqlite:///'+str(path),root,mode='mock'),create=False)
with s.engine.connect() as c:rid=c.exec_driver_sql("SELECT id FROM runs WHERE status='CANCELLED'").scalar_one()
v=s.inspect(s.authenticate('synthetic-test-A'),rid);assert v['status']=='CANCELLED' and v['result'] is None
assert snapshot()==before
with rt.authority.connection() as c:assert c.execute('SELECT state FROM leases WHERE run_id=?',(rid,)).fetchone()==('CLOSED',)
s.engine.dispose();report={'source_commit':'5db5a71fe3cf73efe9a0201545a5427835ba09bb','status':'PASS','fresh_process_dispatch_readback':'CANCELLED','all_main_rows_sha256':before,'rows_unchanged':True,'new_model_calls':0,'control_state':'CLOSED'}
Path('/workspace/Sim2Act/docs/evidence/lease-control-final-fence-20261101/cancel-5db/fresh-process.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
