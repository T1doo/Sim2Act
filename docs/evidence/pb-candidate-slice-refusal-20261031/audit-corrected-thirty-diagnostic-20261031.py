import hashlib,importlib.util,json,sqlite3
from contextlib import closing
from pathlib import Path
root=Path('/workspace/Sim2Act');p=root/'scripts/diagnose_ordinary_thirty.py'
spec=importlib.util.spec_from_file_location('diagnose30',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
case=Path('/workspace/scratch/ordinary-thirty-negative-2ad32276-20261031/test_original_thirty_large_fai0')
db=case/'fixture.db';before=hashlib.sha256(db.read_bytes()).hexdigest()
with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as c:
 c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
 run=dict(c.execute('SELECT r.* FROM runs r JOIN internal_run_bindings b ON b.run_id=r.id ORDER BY r.created_at DESC LIMIT 1').fetchone());rid=run['id']
 attempt=dict(c.execute('SELECT * FROM attempts WHERE run_id=?',(rid,)).fetchone());oid=json.loads(attempt['parameters'])['natural_spec']['operation_id']
 op=dict(c.execute('SELECT * FROM operations WHERE id=?',(oid,)).fetchone())
 app=dict(c.execute('SELECT a.* FROM internal_app_runs a JOIN internal_run_bindings b ON b.app_run_id=a.id WHERE b.run_id=?',(rid,)).fetchone())
 typed=c.execute('SELECT count(*) FROM internal_instance_data WHERE instance_id=?',(app['instance_id'],)).fetchone()[0]
 events=[dict(r) for r in c.execute('SELECT * FROM events WHERE run_id=?',(rid,))]
 for e in events:e['data']=json.loads(e['data'])
 failures=[json.loads(x) for x in (case/'failure-observations.jsonl').read_text().splitlines()]
 usage=m.validate_negative_state(run,attempt,op,app,typed,events,failures)
 assert attempt['status']=='REJECTED_KNOWN'
assert hashlib.sha256(db.read_bytes()).hexdigest()==before
report=dict(status='PASS_CORRECTED_DIAGNOSTIC_ON_ORIGINAL_CLOSED_DATABASE',diagnostic_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),database_sha256=before,database_bytes_unchanged=True,actual_attempt_status=attempt['status'],known_usage=usage,budget_failure_observation_verified=True,goal_completed=False,new_mock_or_real_calls=0,reran_application=False)
Path('/workspace/scratch/corrected-thirty-diagnostic-final-readback-20261031.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
