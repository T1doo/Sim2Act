import json,sys,hashlib
from pathlib import Path
from sqlalchemy import select
from sim2act.db import Store,meta
from sim2act.config import Settings
from sim2act.errors import DomainError
root=Path(sys.argv[1]); proof=json.loads((root/'pb-controller-proof.json').read_text()); path=root/'fixture.db'
s=Store('sqlite:///'+str(path),test_only=True)
def snapshot():
 with s.engine.connect() as c:
  data={t.name:sorted((dict(r) for r in c.execute(select(t)).mappings()),key=lambda r:json.dumps(r,sort_keys=True,default=str)) for t in meta.sorted_tables}
  receipts=c.exec_driver_sql('SELECT * FROM local_lease_control_receipts ORDER BY commit_id').fetchall()
 return hashlib.sha256(json.dumps([data,[list(r) for r in receipts]],sort_keys=True,default=str).encode()).hexdigest()
before=snapshot();rt=s._enable_authoritative_leases(Settings('sqlite:///'+str(path),root,mode='mock'),create=False)
try:
 result=s.inspect(s.authenticate('synthetic-test-A'),proof['cold'])
 print(json.dumps({'api_readback':'PASS','status':result['status']}))
except (DomainError,KeyError) as e:
 print(json.dumps({'api_readback':'BLOCKED','error':getattr(e,'code',type(e).__name__)}))
finally:
 after=snapshot();assert before==after
 with s.engine.connect() as c:
  row=c.exec_driver_sql('SELECT status FROM runs WHERE id=?',(proof['cold'],)).scalar_one()
  verified=c.exec_driver_sql("SELECT count(*) FROM attempts WHERE status='VERIFIED'").scalar_one()
 with rt.authority.connection() as c:
  assert c.execute("SELECT count(*) FROM commits WHERE state!='ACKED'").fetchone()==(0,)
 assert row=='SUCCEEDED' and verified==4
 print(json.dumps({'database_reopen':'PASS','status':row,'all_table_and_protocol_rows_unchanged':True,'rows_sha256':before,'new_model_calls':0}))
 s.engine.dispose()
