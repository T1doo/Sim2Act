"""Independent file-only checkpoint verification. Never imports application or opens SQLite."""
from pathlib import Path
import base64, collections, hashlib, json

root=Path('/workspace/production-trial-stages-20261018')
review=Path('/workspace/production-trial-stages-review-20261018')
def read(path):
    assert not path.is_symlink() and path.suffix not in ('.db','.sqlite','.sqlite3')
    return json.loads(path.read_bytes())
def digest(data): return hashlib.sha256(data).hexdigest()
audit=read(review/'closed-file-audit.json')
summary=read(root/'qualification-summary.json')
facts=read(root/'closed-checkpoint-facts.json')
guard=read(root/'run-8-chain/offline-guard.json')
freeze='cdcae63e6ca6294b98ee6764b832d2d001e4de05'
assert audit['current_qualification']['qualification_status']=='NOT_QUALIFIED'
runs=audit['executions']; statuses=audit['history']['junit_record_counts']
assert len(runs)==11 and statuses=={'ERROR':8,'PASS':5,'FAIL':1}
assert sum(statuses.values())==summary['total_executions']==14
assert summary['unique_nodes']==3 and summary['planned_unique_nodes']==4
assert summary['pass_count']==5 and summary['error_count']==8 and summary['failure_count']==1
adapters=sum(r['adapter_method_counts'].get('request_serialized_captured',0) for r in runs)
assert adapters==summary['actual_synthetic_adapter_entries']==33
current=[r for r in runs if r['directory'].startswith('run-8-')]
assert sum(r['adapter_method_counts'].get('request_serialized_captured',0) for r in current)==9
assert all(r['source_commit']==freeze and r['input_metadata_count']==652 for r in current)
assert all(r['forbidden_guard_attempts']==[] for r in runs)
assert summary['real_model_requests']==0 and summary['old_19_12_8_9_nodes_rerun']==0
assert facts['source_commit']==freeze and facts['post_execution_sqlite_read_only_export'] is True
assert facts['db_sha256_before']==facts['db_sha256_after'] and facts['db_bytes_unchanged'] is True
attempts=facts['actual_attempts']; ids={a['id'] for a in attempts}
assert len(ids)==7 and collections.Counter(a['status'] for a in attempts)=={'RECEIVED':3,'VERIFIED':4}
archive_checks=[]
for kind in ('pa_trial_request_body.v1','pa_trial_response_body.v1'):
    rows=[row for row in facts['archives'] if row['kind']==kind]
    seals=[row for row in facts['archives'] if row['kind']==kind+'_seal']
    assert len(rows)==len(seals)==7 and {row['request_key'] for row in rows}==ids
    for row in rows:
        pair=[s for s in seals if all(s[k]==row[k] for k in ('principal_id','app_id','request_key'))]
        assert len(pair)==1 and pair[0]['snapshot']==row['snapshot']
        body=row['snapshot']['response']
        raw=base64.b64decode(body['body_b64'],validate=True)
        assert body['attempt_id']==row['request_key'] and body['run_id']==row['app_id']
        assert len(raw)==body['byte_count'] and digest(raw)==body['sha256']
        assert body['received_complete'] is True
        if kind=='pa_trial_response_body.v1':
            parsed=json.loads(raw)
            canonical=json.dumps(parsed,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii')
            assert digest(canonical)==body['canonical_sha256'] and digest(raw)!=digest(canonical)
            assert parsed['usage']['total_tokens']==1000
        archive_checks.append({'kind':kind,'attempt_id':body['attempt_id'],'bytes':len(raw),
                               'sha256':digest(raw),'canonical_sha256':body.get('canonical_sha256')})
errors=[x for x in guard['passive_original_controller_checks'] if x.get('error')]
assert len(errors)==1 and errors[0]==facts['last_failed_original_check']
failed=errors[0]
assert failed['function']=='check_run' and failed['stage']=='cold' and failed['error']=='VERSION_CONFLICT'
hb=max((x for x in guard['heartbeats'] if x['run_id']==facts['last_committed_heartbeat']['run_id']),key=lambda x:x['committed_at'])
assert hb==facts['last_committed_heartbeat'] and hb['lease_seconds']==30
lease_overrun=failed['ended_at']-hb['renewed_until']
assert lease_overrun>0 and abs(lease_overrun-facts['check_ended_after_committed_lease_seconds'])<1e-9
assert failed['seconds']>30
current_deadlines=[x['deadline'] for x in guard['heartbeats'] if x['run_id']==hb['run_id'] and x.get('deadline') is not None]
cold_export=next(r for r in facts['runs'] if r['id']==hb['run_id'])
run_deadline=cold_export['created_at']+300
assert run_deadline in current_deadlines and run_deadline>failed['ended_at']
run_scalars=[{k:r.get(k) for k in ('id','status','version','lease_until')} | {'result_is_null':r['result'] is None} for r in facts['runs']]
assert collections.Counter(r['status'] for r in facts['runs'])=={'PARTIAL':1,'SUCCEEDED':1,'RUNNING':1}
cold=next(r for r in facts['runs'] if r['id']==hb['run_id'])
assert cold['status']=='RUNNING' and cold['result'] is None and cold['lease_until']==hb['renewed_until']
assert facts['owner_and_result_readback']=='NOT_RUN_AFTER_FIXTURE_ERROR' and facts['nine_prefix_rejection_windows']=='NOT_RUN'
negatives=[]
for relative,error in (
 ('run-8-negatives/actual-tmp/test_known_accounting_cannot_a0/business-schema-rejected.json','PERMISSION_DENIED'),
 ('run-8-negatives/actual-tmp/test_original_controller_store0/late-store-refused.json','VERSION_CONFLICT')):
    v=read(root/relative);slot=v['accounting']['ledger']['slots'][0]
    assert v['run']['status']=='FAILED' and v['run']['result'] is None and v['run']['error']['code']==error
    assert v['actual_handler_calls']==1 and v['no_resend'] is True
    assert slot['settlement']['total_tokens']==1000 and slot['accepted'] is True
    assert v['accounting']['live_allowed'] is False and v['accounting']['dispatch_authorized'] is False
    if error=='VERSION_CONFLICT':
        assert v['foreign_engine_sql']==0 and v['original_store_held'] is True and v['refused']==['VERSION_CONFLICT']
    negatives.append({'path':relative,'business_status':'FAILED','error':error,'handler_calls':1,'no_resend':True,
                      'known_usage':1000,'accounting_accepted_is_not_business_success':True,
                      'foreign_engine_sql':v.get('foreign_engine_sql')})
result={'kind':'INDEPENDENT_PURE_FILE_CHECKPOINT_AUDIT','qualification':'NOT_QUALIFIED',
        'source_freeze':freeze,'author_seal_sha256':audit['manifest']['manifest_sha256'],
        'author_non_db_files_verified':audit['manifest']['non_db_files'],'author_non_db_bytes_verified':audit['manifest']['non_db_bytes'],
        'db_stat_only_count':len(audit['manifest']['db_stat_only']),
        'history':{'execution_folders':11,'node_executions':14,'PASS':5,'ERROR':8,'FAIL':1,'actual_unique_junit_nodes':3,'planned_unique_nodes':4,
                   'synthetic_captured_adapter_entries':adapters,'real_model_requests':0},
        'final':{'node_executions':3,'PASS':2,'ERROR':1,'B':'NOTRUN','B_windows':'0/9 executed',
                 'chain_adapter_entries':7,'negative_adapter_entries':2,'owner_result_readback':'NOTRUN',
                 'chain_pytest_summary_seconds':594.87,'chain_junit_case_seconds':593.800,'chain_outer_seconds':601.1183520560007,
                 'negatives_pytest_summary_seconds':16.01,'negatives_outer_seconds':21.605561308002507},
        'known_product_blocker':{'description':'Cold current admission exceeds original lease before SAVE/terminal commit; result remains unavailable',
            'failed_check':failed,'last_committed_heartbeat':hb,'check_ended_after_lease_seconds':lease_overrun,
            'unexpired_original_run_deadline':run_deadline,
            'limit':'Outer caller and all rolled-back temporary fields are not fully captured; no assertion that lease is the sole possible simultaneous failed predicate.'},
        'author_export_file_checks':{'origin':'Author post-execution SQLite mode=ro export; reviewer reads only exported JSON, not DB',
            'export_sha256':digest((root/'closed-checkpoint-facts.json').read_bytes()),'archive_rows':len(facts['archives']),
            'actual_attempt_count':7,'attempt_status_counts':{'RECEIVED':3,'VERIFIED':4},'run_scalars':run_scalars,
            'PA_body_rows_decoded_with_matching_seals':14,'response_raw_canonical_distinct':7,'body_checks':archive_checks,
            'author_reported_database_hash_unchanged_not_recomputed':True},
        'final_negative_proofs':negatives,
        'limits':['Review did not execute product, pytest, application imports, DB/SQL, network or private holdout access',
                  'No independent reconstruction of DB state or full-table row equality',
                  'B proof/cache runtime revoke and no-write expiry windows unexecuted',
                  'No complete three-stage result/owner acceptance or LIVE/software qualification',
                  'Windows/native, PostgreSQL, remote CI, PB new-stage qualification and semantic/human acceptance unexecuted',
                  'Real API use has authorization per parent; current trustworthy balance/zero-fee enforcement/source installation remain unverified, not an authorization denial',
                  'Only existing 8fd checkpoint push receipt was reviewed; no endorsement of future push']}
(review/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'qualification':result['qualification'],'manifest_files':result['author_non_db_files_verified'],
                  'history':result['history'],'lease_overrun_seconds':lease_overrun,'B':'NOTRUN','raw_response_hashes':7},ensure_ascii=False))
