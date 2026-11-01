import importlib.util,json,sqlite3,hashlib
from pathlib import Path
from contextlib import closing
from sim2act import natural_live_admission as gate,_owned_pb_contract as owner
root=Path('/workspace/Sim2Act');case=Path('/workspace/scratch/graph-original-edge-original30-3c0f1ee4-20261101/test_original_thirty_large_goa0')
spec=importlib.util.spec_from_file_location('ordinary_saved_validation',root/'scripts/diagnose_ordinary_thirty.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
observed=json.loads((case/'ordinary-thirty-observed.json').read_text());assert observed['source_commit']=='3c0f1ee4d5200ae500756bb7998fbaa86fdc8ae4'
assert len(observed['records'])==1 and observed['records'][0]['outcome']=='ROLLED_BACK' and observed['records'][0]['writer_seconds'] is None
failures=[json.loads(x) for x in (case/'failure-observations.jsonl').read_text().splitlines()];assert len(failures)==1
rid=failures[0]['run_id'];db=case/'fixture.db';before=hashlib.sha256(db.read_bytes()).hexdigest()
with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=1)) as c:
 c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
 run=dict(c.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone())
 attempts=[dict(r) for r in c.execute('SELECT * FROM attempts WHERE run_id=?',(rid,))];assert len(attempts)==1
 attempt=attempts[0];operation_id=json.loads(attempt['parameters'])['natural_spec']['operation_id']
 operation=dict(c.execute('SELECT * FROM operations WHERE id=? AND run_id=?',(operation_id,rid)).fetchone())
 app=dict(c.execute('SELECT a.* FROM internal_app_runs a JOIN internal_run_bindings b ON b.app_run_id=a.id WHERE b.run_id=?',(rid,)).fetchone())
 typed=c.execute('SELECT count(*) FROM internal_instance_data WHERE instance_id=?',(app['instance_id'],)).fetchone()[0]
 events=[dict(r) for r in c.execute('SELECT * FROM events WHERE run_id=?',(rid,))]
 for row in events:row['data']=json.loads(row['data'])
 usage=d.validate_negative_state(run,attempt,operation,app,typed,d.selected_negative_events(events,attempt['id']),failures)
 scopes=c.execute('SELECT snapshot FROM delivery_graph_requests WHERE kind=?',(gate.SCOPE,)).fetchall();assert len(scopes)==1
 original=gate.PBTrialContract.model_validate(json.loads(scopes[0][0])['request']);d.require_ordinary_caps(original)
 frozen=owner.issue_data(original);assert owner.is_owned(frozen);d.require_ordinary_caps(frozen)
 count=c.execute('SELECT count(*) FROM attempts').fetchone()[0];assert count==6
 assert not any(e['kind']=='NS_SETTLEMENT_LEASE_RESERVED' for e in events)
assert hashlib.sha256(db.read_bytes()).hexdigest()==before
out={'status':'PASS_SAVED_NEGATIVE_VALIDATION_NOT_GOAL_SUCCESS','source_commit':observed['source_commit'],'original_diagnostic_exit':1,'original_diagnostic_error':'obsolete Python type(caps) assertion; original output retained',
 'validation_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fixed_diagnostic_sha256':hashlib.sha256((root/'scripts/diagnose_ordinary_thirty.py').read_bytes()).hexdigest(),
 'run_status':run['status'],'attempt_status':attempt['status'],'operation_status':operation['status'],'typed_results':typed,'received_known_usage_preserved':usage,'caps_original_exact_schema':'TrialCaps','extended_lease_events':0,
 'records':observed['records'],'mock_calls':count,'real_calls':0,'new_business_runs':0,'database_content_unchanged':True,'database_sha256':before}
Path('/workspace/scratch/pb-owned-original30-saved-negative-validation-20261101.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
