"""Pure file/Git/JSON audit. No product import, pytest, DB/SQL or network."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import stat
import subprocess
import xml.etree.ElementTree as ET

root=Path('/workspace/production-trial-source-20261018')
review=Path('/workspace/production-trial-source-review-20261018')
repo=Path('/workspace/Sim2Act')
freeze='ab838215af13c04281bbad441fd75b9a97839890'
base='9df8a2ecca3e2e9905200398aa7c7a4d53b891a0'
expected_manifest='7a0d61b98fcaf4405be5e40df9e8b6f9c5a5f0cb97ca06b43015deb939d0fa65'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def j(path):return json.loads(path.read_text())
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
def fp(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def receipt_slot(r):return r['journal']['ledger']['slots'][0]
def false_flags(v):return all(v[k] is False for k in ('live_allowed','dispatch_authorized','real_source_verified'))
def casepath(name):return root/'run-1/actual-tmp'/name

manifest_raw=(root/'sealed-manifest.json').read_bytes()
assert sha(manifest_raw)==expected_manifest
manifest=json.loads(manifest_raw)
entries=manifest['files']
assert len(entries)==manifest['files_excluding_manifest']==74
verified=[]
for name,item in entries.items():
    assert not Path(name).is_absolute() and '..' not in Path(name).parts and '.db' not in Path(name).suffixes
    p=root/name
    assert stat.S_ISREG(p.lstat().st_mode) and not p.is_symlink()
    raw=p.read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],name
    verified.append(dict(path=name,bytes=len(raw),sha256=sha(raw)))
assert sum(v['bytes'] for v in verified)==manifest['bytes_excluding_manifest']==374306
assert len(manifest_raw)==12107
closure=j(root/'closure.json')
db_stats=[]
for item in closure['physical_fixture_databases']:
    p=root/item['path'];meta=p.stat()
    assert stat.S_ISREG(meta.st_mode) and meta.st_size==item['bytes']
    db_stats.append(dict(path=item['path'],bytes_stat_only=meta.st_size,content_read_or_hash=False))
assert len(db_stats)==len({x['path'] for x in db_stats})==9
execution=j(root/'run-1/execution.json')
assert execution['source_commit']==freeze and execution['exit_code']==0
assert execution['command'][:3]==['timeout','--kill-after=15s','240s']
assert execution['command'][-1]=='tests/test_production_trial_source.py'
assert execution['old_19_12_8_nodes_rerun']==0
suite=ET.fromstring((root/'run-1/junit.xml').read_bytes()).find('testsuite')
nodes=suite.findall('testcase')
assert len(nodes)==len({n.attrib['name'] for n in nodes})==9
assert suite.attrib['tests']=='9' and suite.attrib['errors']==suite.attrib['failures']==suite.attrib['skipped']=='0'
assert all(len(n)==0 and n.attrib['classname']=='tests.test_production_trial_source' for n in nodes)
stdout=(root/'run-1/pytest.stdout').read_text()
assert stdout.count(' PASSED')==9 and '9 passed, 1 warning' in stdout
assert (root/'run-1/pytest.stderr').read_bytes()==b''
end_at=datetime.datetime.fromisoformat(execution['ended_utc']).timestamp()
before=j(root/'run-1/inputs-before.json');after=j(root/'run-1/inputs-after.json')
assert before==after and before['head']==freeze
assert len(before['inputs'])==707 and sum(p.startswith('src/') for p in before['inputs'])==138
current_non_db=0;compressed_db=[]
for name,item in before['inputs'].items():
    if '.db' in Path(name).suffixes:
        assert name.endswith('.db.gz') and (repo/name).stat().st_size==item['bytes']
        baseline_blob=git('ls-tree',base,'--',name).decode().split()[2]
        frozen_blob=git('ls-tree',freeze,'--',name).decode().split()[2]
        assert baseline_blob==frozen_blob
        compressed_db.append(dict(path=name,bytes_stat_only=item['bytes'],git_blob_unchanged=frozen_blob,content_read_or_hash=False))
        continue
    raw=(repo/name).read_bytes()
    assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],name
    current_non_db+=1
assert current_non_db==701 and len(compressed_db)==6
old_inputs=j(Path('/workspace/production-trial-sender-20261018/run-1/inputs-after.json'))['inputs']
changed=[name for name,item in old_inputs.items() if before['inputs'][name]!=item]
assert changed==['src/sim2act/production_trial_sender.py'] and len(old_inputs)==705
hb=j(root/'run-1/helpers-before.json');ha=j(root/'run-1/helpers-after.json')
assert hb==ha
for key,name in {'runner':'runner.py','guard':'offline_source_guard.py'}.items():
    raw=(root/'run-1'/name).read_bytes()
    assert len(raw)==hb[key]['bytes'] and sha(raw)==hb[key]['sha256']
assert git('rev-parse','HEAD').decode().strip()==freeze
for name in ('src/sim2act/production_trial_source.py','src/sim2act/production_trial_sender.py','tests/test_production_trial_source.py'):
    assert (root/'run-1/frozen-source'/name).read_bytes()==git('show',freeze+':'+name)==(repo/name).read_bytes()
static=j(review/'freeze-static-review.json')
assert static['freeze']==freeze and all(static['checks'].values())

normal_dir=casepath('test_owned_raw_source_contract0')
normal=j(normal_dir/'source-to-sender.json')
res=normal['resolution'];scope=normal['receipt']['journal']['ledger']['scope']
assert res['source']['requirements_fingerprint']==fp(scope)
assert res['source']['quota_subject']=='intern-ai-account-'+sha(res['source']['account_id'].encode())
assert false_flags(res) and false_flags(normal['receipt']) and false_flags(normal['duplicate'])
trace=normal['trace']
assert [v['step'] for v in trace]==['source_load','reserve','source_load','record_attempt','source_load','source_load','settle']
load_ids=[v['connection'] for v in trace if v['step']=='source_load']
assert len(set(load_ids))==4
assert trace[0]['connection']==trace[1]['connection'] and trace[2]['connection']==trace[3]['connection'] and trace[5]['connection']==trace[6]['connection']
assert all(v['decision']=='ALLOW' for v in trace if v['step']=='source_load')
assert normal['source_reads_for_send']==4 and normal['source_missing_duplicate_lookup_calls']==0
assert normal['complete_history_55_tables_strict_equal'] is True
assert normal['duplicate']['journal']['duplicate'] and not normal['duplicate']['journal']['changed'] and not normal['duplicate']['adapter_entered']
assert normal['duplicate']['journal']['ledger']==normal['receipt']['journal']['ledger']
assert normal['receipt']['business_accepted'] is False and receipt_slot(normal['receipt'])['accepted'] is True
assert receipt_slot(normal['receipt'])['settlement']['total_tokens']==8
assert 'raw_b64' not in json.dumps(res) and 'identity_confirmed' not in json.dumps(res)

common_fields={'issuer','requirements_fingerprint','account_id','provider','model','endpoint','observed_at','expires_at','role'}
role_fields={'identity':{'identity_confirmed'},'entitlement':{'legal_free_entitlement'},'enforcement':{'enforced_zero_charge','paid_cap','billable_fallback_disabled'},'status':{'revoked'}}
def parse_bundle(raw):
    def pairs(items):
        out={}
        for k,v in items:
            assert k not in out
            out[k]=v
        return out
    v=json.loads(raw,object_pairs_hook=pairs)
    assert len(raw)<=8192 and set(v)=={'version',*role_fields}
    assert v['version']=='UNINSTALLED_SYNTHETIC_ACCOUNT_SOURCE_V1'
    for role,fields in role_fields.items():
        part=v[role]
        assert set(part)==common_fields|fields and part['role']==role
        assert part['issuer']=='SIM2ACT_SYNTHETIC_FIXTURE_ONLY'
        assert part['provider']=='intern-ai' and part['model']=='intern-s2' and part['endpoint']=='https://chat.intern-ai.org.cn/api/v1/chat/completions'
        assert all(type(part[k]) in (float,int) and math.isfinite(part[k]) and part[k]>0 for k in ('observed_at','expires_at'))
        for field in fields-{'paid_cap'}:assert part[field] is None or type(part[field]) is bool
        if role=='enforcement':assert type(part['paid_cap']) is int and 0<=part['paid_cap']<=1000000000
    return v

def derive_decision(v,expected):
    parts=[v[k] for k in role_fields]
    if any(p['requirements_fingerprint']!=expected['requirements_fingerprint'] or p['account_id']!=expected['account_id'] or any(p[k]!=expected[k] for k in ('provider','model','endpoint')) for p in parts):return 'DENY','SOURCE_BINDING'
    if any(not p['observed_at']<=end_at<p['expires_at']<=expected['expires_at'] for p in parts):return 'DENY','SOURCE_TIME'
    facts=(v['identity']['identity_confirmed'],v['entitlement']['legal_free_entitlement'],v['enforcement']['enforced_zero_charge'],v['enforcement']['billable_fallback_disabled'])
    if v['status']['revoked'] is True or any(x is False for x in facts) or v['enforcement']['paid_cap']!=0:return 'DENY','SOURCE_REJECTED'
    if any(x is None for x in facts) or v['status']['revoked'] is None:return 'UNKNOWN','SOURCE_INCOMPLETE'
    return 'ALLOW','SYNTHETIC_CONTRACT_VALID'
raw=(normal_dir/'raw-synthetic-source.json').read_bytes();bundle=parse_bundle(raw)
assert sha(raw)==normal['raw_sha256']==res['raw_sha256']==res['source']['evidence_fingerprint']
assert len(raw)==normal['raw_bytes']==res['raw_bytes']==1936
assert derive_decision(bundle,res['source'])==(res['source']['decision'],res['reason'])==('ALLOW','SYNTHETIC_CONTRACT_VALID')
assert res['source']['observed_at']==max(bundle[r]['observed_at'] for r in role_fields)
assert res['source']['expires_at']==min(bundle[r]['expires_at'] for r in role_fields)
assert normal['receipt']['journal']['ledger']['slots'][0]['reserved_at']-res['source']['observed_at']>590
raw_audits=[dict(case='normal',bytes=len(raw),sha256=sha(raw),derived_decision='ALLOW')]
rejections={}
for idx,name in enumerate(('missing','wrong_account','cross_project','expired','revoked','inconsistent')):
    directory=casepath(f'test_unusable_server_source_ne{idx}')
    proof=j(directory/'source-rejection.json')
    assert proof['case']==name and proof['error']['code']=='LIVE_BLOCKED'
    assert proof['all_55_tables_strict_equal'] is True and proof['handler_calls']==0
    rs=proof['resolution']
    assert false_flags(rs)
    if name=='missing':
        assert rs['source']['decision']=='UNKNOWN' and rs['reason']=='SOURCE_MISSING'
        assert rs['raw_sha256'] is None and rs['source']['evidence_fingerprint']=='0'*64
    else:
        raw=(directory/'raw-synthetic-source.json').read_bytes();parsed=parse_bundle(raw)
        assert sha(raw)==rs['raw_sha256']==rs['source']['evidence_fingerprint'] and len(raw)==rs['raw_bytes']
        derived=derive_decision(parsed,rs['source'])
        assert derived==(rs['source']['decision'],rs['reason'])
        raw_audits.append(dict(case=name,bytes=len(raw),sha256=sha(raw),derived_decision=derived[0],derived_reason=derived[1]))
    if name=='cross_project':
        assert proof['sql_observer_positive_payload_reads']>0 and proof['foreign_source_payload_reads']==0
    if name=='inconsistent':
        mirror=proof['one_corrupt_mirror'];mr=mirror['resolution']
        assert mr['source']['decision']=='UNKNOWN' and mr['reason']=='SOURCE_INTEGRITY'
        assert mr['raw_sha256'] is None and mirror['one_pair_fingerprint']=='d'*64
        assert mirror['request_fingerprint_anchors_unchanged'] and mirror['all_55_tables_strict_equal'] and mirror['handler_calls']==0 and mirror['no_auto_repair']
        assert mirror['error']['code']=='LIVE_BLOCKED'
        raw=(directory/'raw-valid-before-mirror-corruption.json').read_bytes();valid=parse_bundle(raw)
        assert derive_decision(valid,rs['source'])==('ALLOW','SYNTHETIC_CONTRACT_VALID')
        raw_audits.append(dict(case='valid_before_single_mirror_corruption',bytes=len(raw),sha256=sha(raw),derived_decision='ALLOW'))
    rejections[name]=dict(decision=rs['source']['decision'],reason=rs['reason'],zero_handler=True,strict_55_table_equality_recorded=True)
assert len(raw_audits)==7
late=j(casepath('test_source_revoked_after_guar0')/'source-late-revocation.json')
assert late['trace']==['mock_handler_after_guard','server_status_revoked_committed']
late_slot=receipt_slot(late['receipt'])
assert late_slot['attempted'] and late_slot['settlement']['outcome']=='RECEIVED' and late_slot['settlement']['total_tokens']==8
assert not late_slot['accepted'] and late['receipt']['journal']['ledger']['halted']
assert late['same_original_key_handler_calls']==1 and late['recovery_55_tables_strict_equal'] and late['zero_refund_or_resend']
assert late['duplicate']['journal']['duplicate'] and not late['duplicate']['adapter_entered'] and late['duplicate']['journal']['ledger']==late['receipt']['journal']['ledger']
assert false_flags(late['receipt']) and false_flags(late['duplicate'])
boundary=j(casepath('test_new_entry_stays_offline_a0')/'source-boundary.json')
assert boundary['default_error']['code']=='LIVE_BLOCKED'
assert boundary['source_permission_error_propagated']['code']=='PERMISSION_DENIED'
assert boundary['new_entry_refusals_55_tables_strict_equal'] and boundary['refusals_handler_calls']==0
assert boundary['original_data_entry_mock_handler_calls']==1 and receipt_slot(boundary['original_data_entry_compatibility'])['accepted']
assert false_flags(boundary['original_data_entry_compatibility'])
states=[j(p) for p in (root/'run-1/actual-tmp').glob('*/source-state.json') if not p.parent.is_symlink()]
assert len(states)==9
assert all(s['protected_other_54_tables_strict_equal'] and s['source_rows_are_fixtures_not_provenance'] and s['real_provider_calls']==0 for s in states)
assert sum(s['mock_handler_calls'] for s in states)==3
guard=j(root/'run-1/offline-guard.json')
assert guard['attempts']==[] and guard['pytest_exitstatus']==0
assert all(guard['adapter_methods'].count(name)==3 for name in ('request_serialized_captured','_request_serialized','_deadline_request'))
assert len(guard['adapter_methods'])==9
pre=j(root/'pre-freeze-observations.json')
assert pre['product_tests_before_freeze']==0 and 'post-fix' in pre['static_p1']
assert 'no separate stderr' in pre['patch_context'] and 'transcribed' in pre['style_wrapper_assertion']
styles=j(root/'style-executions.json');corrected=j(root/'style-corrected-executions.json')
assert [v['exit_code'] for v in styles]==[1,0,0,1] and [v['exit_code'] for v in corrected]==[0,0]
result=dict(status='LIMITED_INDEPENDENT_REVIEW_PASS_NO_REMAINING_DEFINITE_P1_P2',freeze=freeze,author_manifest_sha256=expected_manifest,manifest_files_verified=74,manifest_bytes_verified=374306,manifest_bytes=12107,verified_non_db_files=verified,database_stat_only=db_stats,database_content_reads=0,qualification=dict(unique_nodes=9,executions=9,passed=9,failed=0,junit_seconds=float(suite.attrib['time']),outer_seconds=execution['elapsed_seconds'],old_19_12_8_nodes_rerun=0,subprocess_crash_windows_run=0),inputs=dict(before_after_map_equal=True,count=707,production_count=138,current_non_db_sha_verified=701,compressed_db_assets_stat_git_only=compressed_db,baseline_unchanged_inputs=704,baseline_unchanged_production=136,helpers_equal=True),raw_role_contracts_independently_parsed=raw_audits,rejected_cases=rejections,source_reload_trace=dict(loads=4,distinct_connection_objects=4,load_and_original_apply_connection_equal=True,missing_source_history_lookup_calls=0),synthetic_adapter_calls=3,mock_handler_calls=3,new_source_path_calls=2,old_data_compat_calls=1,real_provider_guard_attempts=0,reviewer_product_pytest_sql_db_http_network_executions=0,scope_limits=['Source schemas, issuer labels, hashes and pairs do not establish real producer/account/entitlement/enforcement/status/fee facts','No API/Worker or source/sender/LIVE registration, no valid LIVE permit','Full-row equality is an executed test oracle with exported receipts/fingerprints; DB rows not independently reconstructed','Normal fixture deletes source; inconsistent fixture leaves fingerprint damage, so final source DBs are not all claimed valid','No subprocess window qualified in this slice; no credit borrowed from earlier four processes','No complete generation/source/cold/UI, real provider/model/fees/semantics, PG, Windows/native or remote CI'])
(review/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('verified_non_db_files','database_stat_only')},ensure_ascii=False,indent=2))
