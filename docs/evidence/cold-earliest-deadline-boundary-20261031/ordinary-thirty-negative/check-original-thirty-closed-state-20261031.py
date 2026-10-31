"""Independent read-only audit of the single finished ordinary-30 diagnostic.

Does not rerun or repair the application. Records the failed overstrict test.
"""
import base64,datetime,hashlib,json,sqlite3
from contextlib import closing
from pathlib import Path
s=Path('/workspace/scratch');base=s/'ordinary-thirty-negative-2ad32276-20261031'
meta=json.loads(Path(str(base)+'-run.json').read_text())
assert meta['returncode']==1 and meta['source_unchanged']
assert hashlib.sha256((s/'test_original_thirty_large_20261031.py').read_bytes()).hexdigest()==meta['test_sha256']
roots={p.resolve().parent for p in base.glob('*/fixture.db')};assert len(roots)==1
root=roots.pop();db=root/'fixture.db';before=hashlib.sha256(db.read_bytes()).hexdigest()
def wal():
 p=Path(str(db)+'-wal')
 return {'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else 0,'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}
wal_before=wal();contracts=[]
def visit(value):
 if type(value)is dict:
  if value.get('path')=='P-B' and type(value.get('caps'))is dict and 'stage_keys'in value:contracts.append(value)
  for child in value.values():visit(child)
 elif type(value)is list:
  for child in value:visit(child)
def decode(value):return json.loads(value) if isinstance(value,str) else value
def fp(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=1)) as c:
 c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
 tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
 for table in tables:
  quoted='"'+table.replace('"','""')+'"'
  fields=[r[1] for r in c.execute('PRAGMA table_info('+quoted+')') if 'JSON' in r[2].upper()]
  for key in fields:
   qkey='"'+key.replace('"','""')+'"'
   for row in c.execute('SELECT '+qkey+' FROM '+quoted):
    if row[0] is not None:
     try:visit(json.loads(row[0]))
     except (ValueError,TypeError):pass
 assert contracts
 assert all(v['caps']['lease_seconds']==30 and 'settlement_seconds'not in v['caps'] and 'settlement_protocol'not in v['caps'] for v in contracts)
 run=dict(c.execute('SELECT r.* FROM runs r JOIN internal_run_bindings b ON b.run_id=r.id ORDER BY r.created_at DESC LIMIT 1').fetchone())
 rid=run['id'];attempts=[dict(r) for r in c.execute('SELECT * FROM attempts WHERE run_id=?',(rid,))];assert len(attempts)==1
 attempt=attempts[0];parameters=decode(attempt['parameters']);oid=parameters['natural_spec']['operation_id']
 op=dict(c.execute('SELECT * FROM operations WHERE id=? AND run_id=?',(oid,rid)).fetchone())
 app=dict(c.execute('SELECT a.* FROM internal_app_runs a JOIN internal_run_bindings b ON b.app_run_id=a.id WHERE b.run_id=?',(rid,)).fetchone())
 events=[dict(r) for r in c.execute('SELECT * FROM events WHERE run_id=? ORDER BY created_at',(rid,))]
 for r in events:r['data']=decode(r['data'])
 received=[r for r in events if r['kind']=='NS_RECEIVED'];rejected=[r for r in events if r['kind']=='NS_REJECTED']
 assert len(received)==len(rejected)==1 and rejected[0]['data']['error']=='BUDGET_EXHAUSTED'
 response=decode(attempt['response']);usage=decode(attempt['usage'])
 assert attempt['status']==op['status']=='REJECTED_KNOWN' and response is not None and usage['status']=='known'
 assert fp(response)==received[0]['data']['response_fingerprint']
 assert decode(op['receipt']) is None and decode(app['output']) is None and app['result_version'] is None
 assert run['status']=='RUNNING' and not run['cancel_intent'] and decode(run['result']) is None
 assert c.execute('SELECT count(*) FROM internal_instance_data WHERE instance_id=?',(app['instance_id'],)).fetchone()[0]==0
 assert not any(r['kind']in ('NS_SETTLED','NS_SETTLEMENT_LEASE_RESERVED') for r in events)
 assert not any(r['kind']=='SPEC_STEP_VERIFIED' and r['data'].get('operation_id')==oid for r in events)
 assert c.execute('SELECT count(*) FROM attempts').fetchone()[0]==6
 end=datetime.datetime.fromisoformat(meta['ended_utc']).timestamp()
 assert run['lease_until']<end<run['created_at']+300 and all(v['expires_at']>end for v in contracts)
 assert rejected[0]['created_at']<run['lease_until']
 assert len((root/'mock-exchanges.jsonl').read_text().splitlines())==6
 failure=[json.loads(x) for x in (root/'failure-observations.jsonl').read_text().splitlines()]
 target=[r for r in failure if r['run_id']==rid]
 assert len(target)==1 and target[0]['error']['code']=='BUDGET_EXHAUSTED' and target[0]['error']['message']=='Finite model settlement interval ended'
 wall_remainder=run['lease_until']-rejected[0]['created_at']
after=hashlib.sha256(db.read_bytes()).hexdigest();assert before==after
wal_after=wal();assert wal_before==wal_after or wal_before['bytes']==wal_after['bytes']==0
report={'source_commit':meta['source_commit'],'status':'PASS_READ_ONLY_NEGATIVE_BOUNDARY_AUDIT','application_goal_completed':False,
 'diagnostic_pytest_returncode':1,'diagnostic_assertion_failure_preserved':True,
 'diagnostic_error':'Overstrict newly written assumption RECEIVED; original budget-rejection protocol permits REJECTED_KNOWN. Reader also normalizes actual SQL JSON null and targets model operation by metadata id, not an arbitrary preceding read operation.',
 'contract_input':'Fresh ordinary TrialCaps approved through unchanged original gate.approve; only existing synthetic fixture configuration, no added entitlement/clock/production-code replacement',
 'persisted_ordinary_contract_occurrences':len(contracts),'lease_seconds':30,'has_extended_settlement_policy':False,
 'run_id':rid,'run_status':run['status'],'lease_expired_at_case_end':True,'node_run_and_trial_not_expired_at_case_end':True,
 'model_attempt_status':attempt['status'],'model_operation_status':op['status'],'response_fingerprint_matches_original_received_event':True,
 'known_usage':usage,'budget_rejection_recorded_before_wall_lease_seconds':wall_remainder,
 'specific_original_monotonic_trigger_recorded':False,'goal_output':None,'result_version':None,'typed_results':0,
 'model_verified_step_events':0,'model_settled_events':0,'extended_settlement_booking_events':0,
 'prior_read_operation_can_remain_verified':True,'fixed_mock_requests':6,'real_model_requests':0,'application_rerun_or_repair_performed':False,
 'database_bytes_unchanged':True,'database_sha256':after,'wal_before':wal_before,'wal_after':wal_after,
 'original_failure_observation':target[0]}
out=s/'ordinary-thirty-closed-state-audit-20261031.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','diagnostic_pytest_returncode','run_status','model_attempt_status','response_fingerprint_matches_original_received_event','known_usage','typed_results','database_bytes_unchanged','real_model_requests']}))
