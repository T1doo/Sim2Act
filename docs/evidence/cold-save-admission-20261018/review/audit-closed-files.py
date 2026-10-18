"""Pure-file independent audit; never imports application or opens SQLite."""
from pathlib import Path
import base64, collections, hashlib, json, subprocess, xml.etree.ElementTree as ET
root=Path('/workspace/cold-save-admission-20261018');review=Path('/workspace/cold-save-admission-review-20261018');repo=Path('/workspace/Sim2Act')
freeze='fd96df814e8c0fb6db6651ce77eb484951240ecc';sealsha='c6aa7ede21e01a16de2b9852cbc71a23542fba322fa5f9c7fab54916fc4e614e'
def sha(b): return hashlib.sha256(b).hexdigest()
def jsonread(p):
 assert not p.is_symlink() and '.db' not in p.name and '.sqlite' not in p.name
 return json.loads(p.read_bytes())
def safe(relative):
 p=root/relative;assert not p.is_symlink() and p.resolve().is_relative_to(root.resolve()) and p.is_file();return p
manifest=safe('sealed-manifest.json');assert sha(manifest.read_bytes())==sealsha
m=jsonread(manifest);verified=[]
for name,entry in m['files'].items():
 p=safe(name);assert '.db' not in p.name and '.sqlite' not in p.name
 b=p.read_bytes();assert len(b)==entry['bytes'] and sha(b)==entry['sha256'], name
 verified.append({'path':name,'bytes':len(b),'sha256':sha(b)})
assert len(verified)==m['file_count']==68 and sum(x['bytes'] for x in verified)==m['total_bytes']==2394591
stats=[{'path':n,'bytes':safe(n).stat().st_size,'stat_only':True} for n in m['excluded_external_databases']]
assert len(stats)==5
execution=jsonread(root/'fresh-once/execution.json');summary=jsonread(root/'closed-summary.json')
assert execution['source_commit']==freeze and execution['exit_code']==0 and execution['ended_utc']
names=['test_fresh_actual_prefix_rejects_incomplete_mixed_or_changed_proof_without_writes',
       'test_actual_pa_three_two_two_reaches_existing_results_and_pending_owner',
       'test_known_accounting_cannot_accept_wrong_original_business_schema',
       'test_original_controller_store_is_fixed_through_late_body_and_failure']
command=execution['command'];assert [x.split('::')[-1] for x in command if '::' in x]==names
assert '--maxfail=1' not in command and command[0]=='timeout' and '900s' in command
cases=[]
for x in ET.fromstring((root/'fresh-once/junit.xml').read_bytes()).iter('testcase'):
 assert x.get('name') and all(x.find(k) is None for k in ('failure','error','skipped'))
 cases.append({'name':x.get('name'),'seconds':x.get('time'),'status':'PASS'})
assert [x['name'] for x in cases]==names and len(cases)==4
before,after=[jsonread(root/'fresh-once'/n) for n in ('inputs-before.json','inputs-after.json')]
assert before==after and before['head']==freeze and len(before['inputs'])==652
hb,ha=[jsonread(root/'fresh-once'/n) for n in ('helpers-before.json','helpers-after.json')];assert hb==ha
for name,entry in hb.items():
 p=root/'fresh-once'/('runner.py' if name=='run_fresh.py' else name);b=p.read_bytes()
 assert len(b)==entry['bytes'] and sha(b)==entry['sha256']
static=jsonread(review/'static-verification.json')
for e in static['files']:
 raw=(repo/e['path']).read_bytes();copy=(root/'fresh-once/frozen-source'/e['path']).read_bytes()
 assert raw==copy and len(raw)==e['bytes'] and sha(raw)==e['sha256']
 assert before['inputs'][e['path']]['sha256']==e['sha256']
assert subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=repo).decode().strip()==freeze
B=jsonread(root/'fresh-once/actual-tmp/actual-prefix0/fresh-proof-rejections.json')
expected=['same-read-segment-then-write-invalidates','scope-cache-write-revoke','scope-cache-real-expiry',
          'only-accounting','mixed-backend','canonical','raw','aid','scope']
assert [x['case'] for x in B['cases']]==expected and all(x['refused'] and x['all_55_tables_unchanged_in_window'] for x in B['cases'])
assert B['source']=='THIS_ROUND_ACTUAL_PREFIX_ONLY' and B['clones_or_old_db_used'] is False and B['new_model_requests']==0
assert B['cases'][1]['full_scope_entries']==2 and B['cases'][2]['full_scope_entries']==1
assert all(B['cases'][i]['hit_authority_rechecks']>0 and B['cases'][i]['real_clock'] for i in (1,2))
P=jsonread(root/'fresh-once/actual-tmp/actual-prefix0/actual-pa-stages.json')
slots=P['accounting']['ledger']['slots'];assert len(slots)==7 and all(s['accepted'] for s in slots) and not P['accounting']['ledger']['halted']
assert collections.Counter(s['identity']['stage'] for s in slots)=={'generate':3,'source':2,'cold':2}
assert {s['identity']['attempt_id'] for s in slots}=={a['id'] for a in P['actual_attempts']} and len(P['actual_attempts'])==7
assert collections.Counter(a['status'] for a in P['actual_attempts'])=={'RECEIVED':3,'VERIFIED':4}
gaps=[b['reserved_at']-a['reserved_at'] for a,b in zip(slots,slots[1:])];assert gaps==P['gaps'] and min(gaps)>=60
bodychecks=[]
assert collections.Counter(x['kind'] for x in P['bodies'])=={'pa_trial_request_body.v1':7,'pa_trial_response_body.v1':7}
for x in P['bodies']:
 b=x['snapshot']['response'];raw=base64.b64decode(b['body_b64'],validate=True)
 assert len(raw)==b['byte_count'] and sha(raw)==b['sha256'] and b['received_complete'] is True
 assert b['attempt_id']==x['request_key'] and b['run_id']==x['app_id']
 if x['kind']=='pa_trial_response_body.v1':
  c=json.dumps(json.loads(raw),ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii')
  assert sha(c)==b['canonical_sha256'] and sha(c)!=sha(raw)
  bodychecks.append({'attempt_id':b['attempt_id'],'raw_sha256':sha(raw),'canonical_sha256':sha(c),'raw_bytes':len(raw)})
results={}
for stage,version in (('source',1),('cold',2)):
 x=P['results'][stage];artifact=x['artifact'];resource=artifact['resource'];r=x['result'];owner=x['owner_review']
 assert r['status']=='SUCCEEDED' and r['result_version']==version and owner['owner_acceptance']=='PENDING'
 assert sha(resource['content'].encode())==resource['hash']
 assert json.loads(resource['content'])['source_content']==r['result']['checklist']['source_content']
 assert owner['run_id']==x['run_id']==artifact['run_id']==r['id'] and artifact['result_version']==version
 assert x['history']['dispatch_authorized'] is False and x['history']['new_model_requests']==0
 assert artifact['formal_publication_enabled'] is False
 results[stage]={'run_id':x['run_id'],'status':r['status'],'result_version':version,'artifact_sha256':resource['hash'],'owner':'PENDING','owner_content_access':owner['content_access']}
source,cold=P['results']['source'],P['results']['cold']
assert source['artifact']['instance_id']==cold['artifact']['instance_id'] and source['artifact']['release_id']==cold['artifact']['release_id']
assert source['owner_review']['content_access'] is False and source['owner_review']['invalidation_reason']=='VERSION_CONFLICT'
assert cold['owner_review']['content_access'] is True and cold['owner_review']['current']['run_id']==cold['run_id']
assert cold['owner_review']['current']['material']['content']==cold['result']['result']['checklist']['source_content']
assert P['real_provider_calls']==0 and P['live_installed'] is False and P['semantic_acceptance']=='NOT_RUN'
G=jsonread(root/'fresh-once/offline-guard.json');assert G['attempts']==[] and G['pytest_exitstatus']==0 and G['guard_starts_before_module_fixture'] is True
methods=collections.Counter(x['method'] for x in G['adapter_methods']);assert methods=={'request_serialized_captured':9,'_request_serialized':9,'_deadline_request':9}
assert not any(x.get('error') for x in G['passive_original_controller_checks'])
for h in G['heartbeats']:
 assert 0<h['lease_seconds']<=30 and h['renewed_until']<=h['committed_at']+30.001
pairs=[]
for stage in ('source','cold'):
 rid=results[stage]['run_id'];pre=[x for x in G['passive_commit_guards'] if x['run_id']==rid and x['caller']['line']==1220 and x['delta']==1]
 assert len(pre)==1;pre=pre[0]
 post=[x for x in G['passive_commit_guards'] if x['run_id']==rid and x['caller']['line']==1261 and x['delta']==1 and x['transaction_observer_id']==pre['transaction_observer_id']]
 assert len(post)==1;post=post[0]
 assert all(pre[k]==post[k] for k in ('connection_id','transaction_id','thread','transaction_observer_id'))
 assert post['write_epoch_at_start']>pre['write_epoch_at_end']
 for x in (pre,post):
  assert not x.get('error') and x['read_segment_at_start'] and x['read_segment_at_end'] and x['write_epoch_at_start']==x['write_epoch_at_end'] and x['lease_remaining_at_end']>0
 tx=[x for x in G['passive_transactions'] if x['id']==pre['transaction_observer_id']];assert len(tx)==1;tx=tx[0]
 assert tx['outcome']=='commit_event_before_driver_commit' and tx['ended_at']<post['returned_lease_until']
 pair={'stage':stage,'run_id':rid,'pre_write_guard':pre,'post_write_guard':post,'transaction':tx,
       'lease_remaining_at_transaction_event_end':post['returned_lease_until']-tx['ended_at'],
       'limit':'SQLAlchemy event occurs before driver commit completion; successful business readback is separate evidence of completion.'}
 pairs.append(pair)
for pair,saved in zip(pairs,summary['SAVE_guard_pairs']):
 assert all(pair[k]==saved[k] for k in ('stage','run_id','pre_write_guard','post_write_guard','transaction','lease_remaining_at_transaction_event_end'))
negative=[]
for relative,error in (
 ('fresh-once/actual-tmp/test_known_accounting_cannot_a0/business-schema-rejected.json','PERMISSION_DENIED'),
 ('fresh-once/actual-tmp/test_original_controller_store0/late-store-refused.json','VERSION_CONFLICT')):
 x=jsonread(root/relative);assert x['run']['status']=='FAILED' and x['run']['result'] is None and x['run']['error']['code']==error
 assert x['actual_handler_calls']==1 and x['no_resend'] is True
 assert x['accounting']['live_allowed'] is False and x['accounting']['dispatch_authorized'] is False
 if error=='VERSION_CONFLICT': assert x['foreign_engine_sql']==0 and x['original_store_held'] is True and x['refused']==['VERSION_CONFLICT']
 negative.append({'path':relative,'error':error,'handler_calls':1,'no_resend':True,'foreign_engine_sql':x.get('foreign_engine_sql')})
component=jsonread(root/'expired-lease-regression/expired-lease-regression.json')
assert component['original_fixture_unchanged'] and component['original_fixture_sha_before']==component['original_fixture_sha_after']
assert component['old_trial_binding_installed'] is False and component['generation_nine_windows_rerun_in_this_command'] is False
assert len(component['expired_lease_rejections'])==2 and all(x['code']=='VERSION_CONFLICT' and x['message']=='Stale worker lease' and x['all_55_tables_unchanged'] for x in component['expired_lease_rejections'])
assert jsonread(root/'targeted-execution.json')['exit_code']==1 and 'Trial software changed' in (root/'targeted.stderr').read_text()
assert jsonread(root/'expired-lease-execution.json')['exit_code']==0
reconnect=jsonread(root/'reconnection-checkpoint.json');assert reconnect['matching_prior_commands_active']==[] and reconnect['fresh_chain_started'] is False and reconnect['unknown_processes_or_locks_deleted'] is False
for name in ('expired-admission-diagnosis.json','proof-prefix/expired-admission-diagnosis.json'):
 d=jsonread(root/name);assert d['fixture_unchanged'] and d['fixture_sha_before']==d['fixture_sha_after']
 assert all(x['error']['code']=='VERSION_CONFLICT' and x['expired_lease_not_bypassed'] for x in d['results'])
assert summary['actual_mock_adapter_entries']==9 and summary['real_model_calls']==0 and summary['old_requests_replayed']==0
result={'kind':'INDEPENDENT_PURE_FILE_GIT_REVIEW_NO_PRODUCT_EXECUTION','qualification':'FRESH_MOCK_QUALIFIED_NOT_LIVE_OR_FULL_F2',
 'source_freeze':freeze,'author_seal_sha256':sealsha,'author_files_verified':len(verified),'author_raw_bytes_verified':sum(x['bytes'] for x in verified),
 'verified_files':verified,'external_DB_stat_only':stats,'current_source_test_bytes_match_frozen_copies_and_static_review':True,
 'static_review':'static-verification.json','execution':execution,'junit_cases':cases,'PASS':4,'pytest_summary_seconds':540.32,
 'input_count':652,'production_count':138,'input_and_helpers_zero_drift':True,'B_nine_windows':B,
 'chain_slots':7,'stage_calls':{'generate':3,'source':2,'cold':2},'actual_attempts':7,'min_real_slot_gap_seconds':min(gaps),
 'request_bodies_verified':7,'response_raw_canonical_verified':bodychecks,'result_and_owner':results,
 'same_instance_and_release':True,'synthetic_adapter_entries':9,'chain_adapter_entries':7,'negative_adapter_entries':2,'real_model_requests':0,
 'guard_attempts':[],'passive_SAVE_guard_pairs':pairs,'negative_proofs':negative,
 'component_scope':{'first_targeted_exit':1,'first_reason':'Correct changed-software rejection, not a fresh pytest failure',
 'followup_exit':0,'old_trial_binding_installed':False,'two_expired_lease_guards_rejected':True,
 'source_fixture_hash_unchanged_author_report_only':True,'nine_prior_derivative_windows_not_fresh_qualification':True},
 'reconnection':'Closed exit0 established before continuing; unknown-process-id recovery retained; no duplicate fresh launch or lock/process deletion',
 'prior_checkpoint':'Retained unchanged NOT_QUALIFIED:14 JUnit records=5PASS/8ERROR/1fixtureFAIL;33 synthetic adapter entries. This round adds4PASS/9 entries; no historical failure rewritten.',
 'limits':['Reviewer did not execute product/pytest/Worker/model/application imports/DB/SQL/network or private holdout access',
 'Full55-table row equality rests on executed strict test assertions and retained proof, not reviewer DB reconstruction',
 'Single mock execution is not performance/load guarantee; prior31.750s complete failure was not reproduced',
 'Transaction event timing precedes native driver commit completion',
 'No browser requalification, real API, semantic/human acceptance, Windows/native, PG, remote CI or new PB/AT10 qualification',
 'Source/gates remain uninstalled for LIVE; real API authorization itself is not claimed missing',
 'No future push endorsed; old sealed directories were never modified']}
(review/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'FINITE_FILE_AUDIT_PASS','qualification':result['qualification'],'files':68,'bytes':2394591,'fresh_pytest_PASS':4,'B_windows':9,'mock_entries':9,'real_model':0,'Cold_post_guard_lease_remaining':pairs[1]['post_write_guard']['lease_remaining_at_end']},ensure_ascii=False))
