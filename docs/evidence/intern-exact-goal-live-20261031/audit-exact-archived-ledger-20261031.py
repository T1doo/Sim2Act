"""Read archived synthetic SQLite copies independently; no application imports or IO."""
import gzip,hashlib,json,sqlite3,tempfile
from pathlib import Path
root=Path('/workspace/Sim2Act/docs/evidence/intern-exact-goal-live-20261031')
report=json.loads((root/'accepted/report.json').read_text());old_report=json.loads((root/'failed-original/report.json').read_text())
with tempfile.TemporaryDirectory(prefix='exact-ledger-audit-') as tmp:
 cons={}
 for name in ['accepted','failed-original']:
  raw=gzip.decompress((root/name/'workspace/synthetic-workspace.db.gz').read_bytes())
  wal=root/name/'workspace/synthetic-workspace.db-wal.gz'
  assert not wal.exists() or gzip.decompress(wal.read_bytes())==b''
  file=Path(tmp)/(name+'.db');file.write_bytes(raw)
  con=sqlite3.connect('file:'+str(file)+'?mode=ro&immutable=1',uri=True);con.row_factory=sqlite3.Row;cons[name]=con
  assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  if name=='failed-original':assert hashlib.sha256(raw).hexdigest()=='0f96f4f1a4872c18207493d9c1fc75fc0de119f7acc99c2f0bf681b20b364b60'
 for table in ['runs','attempts','reservations','events','run_contracts']:
  query='SELECT * FROM '+table+' WHERE '+('id' if table=='runs' else 'run_id')+'=? ORDER BY 1'
  assert [tuple(x) for x in cons['accepted'].execute(query,(old_report['run_id'],))]==[tuple(x) for x in cons['failed-original'].execute(query,(old_report['run_id'],))]
 con=cons['accepted'];rid=report['run_id']
 run=dict(con.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone());context=json.loads(run['context']);result=json.loads(run['result'])
 aa=[dict(x) for x in con.execute('SELECT * FROM attempts WHERE run_id=? ORDER BY created_at',(rid,))]
 rr=[dict(x) for x in con.execute('SELECT * FROM reservations WHERE run_id=?',(rid,))]
 oo=[dict(x) for x in con.execute('SELECT * FROM operations WHERE run_id=?',(rid,))]
 assert run['status']=='SUCCEEDED' and len(aa)==len(rr)==2 and len(oo)==1 and oo[0]['status']=='VERIFIED'
 assert con.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==3
 assert con.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==3
 assert len({r['subject'] for r in con.execute('SELECT * FROM reservations')})==1
 tools=[{'type':'function','function':{'name':'resource.read','description':'resource.read','parameters':{'type':'object','properties':{'resource_id':{'type':'string'}},'required':['resource_id'],'additionalProperties':False}}}]
 for i,a in enumerate(aa):
  params=json.loads(a['parameters']);assert a['status']=='RECEIVED' and a['mode']=='LIVE' and a['response_model']=='Intern-S2'
  assert params['exact_read_request_protocol']=='exact-read-direct.v1'
  body={'model':'intern-s2','messages':context['messages'][:2 if i==0 else 4],'tools':tools,'stream':False,'max_tokens':params['max_tokens'],'thinking_mode':False,'tool_choice':{'type':'function','function':{'name':'resource.read'}} if i==0 else 'none'}
  fingerprint=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
  assert params['request_fingerprint']==fingerprint
  assert a['reserved_tokens']==len(json.dumps(body,ensure_ascii=False).encode())+params['max_tokens']
  assert json.loads(a['response'])==context['messages'][2 if i==0 else 4]
 assert json.loads(result['answer'])=={'content':report['input']} and result['read_result']['content']==report['input']
 assert result['goal_acceptance']=='PASS_EXACT_READ_CONTRACT' and result['task_acceptance']['whole_task_accepted'] is True
 unknown=[dict(x) for x in con.execute('SELECT * FROM attempts WHERE run_id=?',(old_report['run_id'],))]
 assert len(unknown)==1 and unknown[0]['status']=='FAILED' and json.loads(unknown[0]['usage'])=={'status':'unknown','tokens':None}
 for c in cons.values():c.close()
result={'classification':'INDEPENDENT_PYTHON_STDLIB_READONLY_ARCHIVED_SQLITE_AUDIT','application_commit':report['source_commit'],'integrity_checks':'OK_BOTH_ARCHIVES','nonempty_wal':False,'prior_failed_rows_exact_equal':True,'prior_unknown_preserved':True,'total_attempts_in_original_ledger':3,'new_attempts_received':2,'total_reservations':3,'same_quota_subject':True,'full_wire_fingerprints_and_conservative_bytes_recomputed':True,'full_source_and_final_answer_equal':True,'model_requests_during_audit':0}
(root/'archived-ledger-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
