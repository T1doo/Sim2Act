"""Independent standard-library archive check; no application imports or model IO."""
import gzip,hashlib,json,sqlite3,tempfile
from pathlib import Path
root=Path('/workspace/Sim2Act/docs/evidence/finite-lease-and-installed-v2-20261031')
report=json.loads((root/'accepted-v2/report.json').read_text())
with tempfile.TemporaryDirectory(prefix='final-finite-audit-') as tmp:
 cons={}
 for name,label in [('final','closed-final-workspace'),('prior','rejected-v1-workspace')]:
  raw=gzip.decompress((root/label/'synthetic-workspace.db.gz').read_bytes())
  wal=root/label/'synthetic-workspace.db-wal.gz';assert not wal.exists() or gzip.decompress(wal.read_bytes())==b''
  p=Path(tmp)/(name+'.db');p.write_bytes(raw)
  c=sqlite3.connect('file:'+str(p)+'?mode=ro&immutable=1',uri=True);c.row_factory=sqlite3.Row
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';cons[name]=c
 oldids=[r[0] for r in cons['prior'].execute('SELECT id FROM runs ORDER BY id')]
 assert len(oldids)==4
 for rid in oldids:
  for table in ['runs','attempts','reservations','events','run_contracts']:
   sql='SELECT * FROM '+table+' WHERE '+('id' if table=='runs' else 'run_id')+'=? ORDER BY 1'
   assert [tuple(r) for r in cons['prior'].execute(sql,(rid,))]==[tuple(r) for r in cons['final'].execute(sql,(rid,))]
 c=cons['final'];rid=report['run_id'];run=dict(c.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone());ctx=json.loads(run['context']);result=json.loads(run['result'])
 spec=json.loads(c.execute('SELECT snapshot FROM run_contracts WHERE run_id=?',(rid,)).fetchone()[0])['exact_read']
 assert spec['request_protocol']=='exact-read-direct.v2' and spec['request_timeout_seconds']==25
 aa=[dict(x) for x in c.execute('SELECT * FROM attempts WHERE run_id=? ORDER BY created_at',(rid,))]
 assert len(aa)==2 and c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==9 and c.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]==9
 assert c.execute('SELECT COUNT(*) FROM operations WHERE run_id=? AND status=?',(rid,'VERIFIED')).fetchone()[0]==1
 assert 'Do not add explanations' in ctx['messages'][0]['content'] and 'A\\nB\\n' in ctx['messages'][0]['content']
 tool=[{'type':'function','function':{'name':'resource.read','description':'resource.read','parameters':{'type':'object','properties':{'resource_id':{'type':'string'}},'required':['resource_id'],'additionalProperties':False}}}]
 for i,a in enumerate(aa):
  params=json.loads(a['parameters']);assert a['status']=='RECEIVED' and a['mode']=='LIVE' and a['response_model']=='Intern-S2' and params['exact_read_request_protocol']=='exact-read-direct.v2'
  wire={'model':'intern-s2','messages':ctx['messages'][:2 if i==0 else 4],'tools':tool,'stream':False,'max_tokens':params['max_tokens'],'thinking_mode':False,'tool_choice':{'type':'function','function':{'name':'resource.read'}} if i==0 else 'none'}
  fp=hashlib.sha256(json.dumps(wire,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
  assert fp==params['request_fingerprint'] and a['reserved_tokens']==len(json.dumps(wire,ensure_ascii=False).encode())+params['max_tokens']
  assert json.loads(a['response'])==ctx['messages'][2 if i==0 else 4]
 assert run['status']=='SUCCEEDED' and json.loads(result['answer'])=={'content':report['input']} and result['read_result']['content']==report['input']
 assert result['task_acceptance']['whole_task_accepted'] is True and result['task_acceptance']['general_semantic_acceptance']=='NOT_RUN' and result['task_acceptance']['owner_acceptance']=='PENDING'
 for con in cons.values():con.close()
result={'source_commit':report['source_commit'],'stdlib_only_readonly_immutable_copies':True,'model_requests_during_audit':0,'both_integrity_checks':'ok','nonempty_wal':False,'all_four_prior_runs_five_tables_unchanged':True,'unknown_and_format_failure_and_success_preserved':True,'total_attempts_and_reservations':9,'new_received_requests':2,'new_strict_verbatim_goal':'PASS','new_full_wire_fingerprints_and_bytes_recomputed':True,'v2_system_instruction_persisted':True}
(root/'independent-archived-ledger-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
