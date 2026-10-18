"""Read only this round's closed synthetic SQLite facts; never run product/model code."""
import base64,hashlib,json,sqlite3
from pathlib import Path
root=Path('/workspace/production-trial-stages-20261018');out=root/'run-8-chain'
execution=json.loads((out/'execution.json').read_text());assert 'exit_code' in execution
path=out/'actual-tmp/actual-prefix0/fixture.db'
before=hashlib.sha256(path.read_bytes()).hexdigest()
c=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
json_fields={'snapshot','parameters','usage','response','result','error','resource_refs'}
def decode(row):
 value=dict(row)
 for k in json_fields & value.keys():
  if value[k] is not None:value[k]=json.loads(value[k])
 return value
try:
 run_rows=[decode(x) for x in c.execute('select id,principal_id,project_id,runtime_id,status,version,fence,worker_id,created_at,lease_until,cancel_intent,request_key,result,error,resource_refs from runs order by created_at,id')]
 actual=[decode(x) for x in c.execute('select id,run_id,status,parameters,usage,response,elapsed from attempts order by created_at,id')]
 kinds=['pa_trial_request_body.v1','pa_trial_response_body.v1','natural_source_request_body.v1','natural_source_response_body.v1','uninstalled-production-trial-capture.v1','uninstalled-production-trial-journal.v1']
 tags=kinds+[k+'_seal' for k in kinds]
 archives=[decode(x) for x in c.execute('select principal_id,app_id,kind,request_key,snapshot,fingerprint,request_fingerprint from delivery_graph_requests where kind in ('+','.join('?' for _ in tags)+') order by kind,app_id,request_key',tags)]
 events=[decode(x) for x in c.execute('select id,run_id,created_at,kind from events order by created_at,id')]
finally:c.close()
after=hashlib.sha256(path.read_bytes()).hexdigest();assert before==after
ledger=[r for r in archives if r['kind']=='uninstalled-production-trial-journal.v1'][0]['snapshot']['response']['ledger']
responses=[r for r in archives if r['kind']=='pa_trial_response_body.v1']
body_checks=[]
for r in responses:
 b=r['snapshot']['response'];raw=base64.b64decode(b['body_b64'],validate=True)
 assert hashlib.sha256(raw).hexdigest()==b['sha256'] and len(raw)==b['byte_count']
 body_checks.append(dict(attempt_id=b['attempt_id'],bytes=len(raw),raw_sha256=b['sha256'],canonical_sha256=b['canonical_sha256'],raw_canonical_distinct=b['sha256']!=b['canonical_sha256']))
assert len(actual)==len(responses)==len(ledger['slots'])==7 and all(b['raw_canonical_distinct'] for b in body_checks)
guard=json.loads((out/'offline-guard.json').read_text())
errors=[x for x in guard['passive_original_controller_checks'] if x.get('error')]
assert len(errors)==1 and errors[0]['stage']=='cold' and errors[0]['error']=='VERSION_CONFLICT'
last_hb=guard['heartbeats'][-1]
value=dict(status='NOT_QUALIFIED_COLD_RESULT_NOT_COMMITTED',source_commit=execution['source_commit'],
 post_execution_sqlite_read_only_export=True,product_or_model_calls=0,database=str(path),
 db_sha256_before=before,db_sha256_after=after,db_bytes_unchanged=True,
 actual_attempts=actual,runs=run_rows,archives=archives,events=events,body_checks=body_checks,
 accounting_accepted_all_seven=all(s['accepted'] for s in ledger['slots']),accounting_is_not_business_success=True,
 last_failed_original_check=errors[0],last_committed_heartbeat=last_hb,
 check_ended_after_committed_lease_seconds=errors[0]['ended_at']-last_hb['renewed_until'],
 owner_and_result_readback='NOT_RUN_AFTER_FIXTURE_ERROR',nine_prefix_rejection_windows='NOT_RUN',
 real_model_requests=0,semantic_or_human_acceptance='NOT_RUN')
(root/'closed-checkpoint-facts.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'source_commit':execution['source_commit'],'attempts':len(actual),'pa_response_bodies':len(responses),'archive_rows':len(archives),'runs':[{k:r[k] for k in ('id','status','version')} for r in run_rows],'lease_overrun_seconds':value['check_ended_after_committed_lease_seconds'],'db_bytes_unchanged':True}))
