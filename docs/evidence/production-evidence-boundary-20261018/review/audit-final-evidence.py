"""Pure closed-file/Git/AST verification; never imports product or reads DB bytes."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re,subprocess,xml.etree.ElementTree as E
repo=Path('/workspace/Sim2Act'); raw=Path('/workspace/production-evidence-boundary-20261018')
review=Path('/workspace/production-evidence-resolver-review-20261018')
freeze='8cd9d0040150dbd28a68bb622f5e6822577dad42';base='494cf2e1490967f8cf8621bb48b52fa00713436d'
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text())
fp=lambda d:sha(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
git=lambda *args:subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
manifest_bytes=(raw/'manifest-final.json').read_bytes();m=json.loads(manifest_bytes)
assert sha(manifest_bytes)=='69a5feae66810641bb31c38ce435b6b3163705471d065dc13e99e46291deb4df'
assert len(m['files'])==34 and sum(v['bytes'] for v in m['files'].values())==650709
aliases=[];physical=set()
for name,h in m['files'].items():
 p=raw/name;assert not name.endswith(('.db','-journal','-wal','-shm'))
 b=p.read_bytes();assert len(b)==h['bytes'] and sha(b)==h['sha256'],name
 real=str(p.resolve());physical.add(real)
 if any(v.is_symlink() for v in [p,*p.parents] if v!=raw.parent):aliases.append(name)
db=[]
for name,h in m['retained_fixture_databases'].items():
 p=raw/name;assert p.stat().st_size==h['bytes'] and h['copied_to_repo'] is False
 db.append({'path':name,'bytes_stat_verified':h['bytes'],'sha256_review':'author supplied only, no DB bytes/SQL read','physical_path':str(p.resolve())})
assert len(db)==11
before=load(raw/'inputs-before.json');after=load(raw/'inputs-after.json')
assert before==after and len(before['inputs'])==699
assert before['head']==after['head']==freeze
for name,h in before['inputs'].items():
 p=repo/name;b=p.read_bytes();assert len(b)==h['bytes'] and sha(b)==h['sha256'],name
prod=[p for p in before['inputs'] if p.startswith('src/sim2act/')]
assert len(prod)==134
for name in prod:assert (repo/name).read_bytes()==git('show',freeze+':'+name),name
assert git('rev-parse','HEAD').decode().strip()==freeze
changed=git('diff','--name-only',base,freeze,'--','src').decode().splitlines()
assert changed==['src/sim2act/production_evidence.py','src/sim2act/production_trial_admission.py']
old=ast.parse(git('show',base+':src/sim2act/production_trial_admission.py').decode())
new=ast.parse((repo/'src/sim2act/production_trial_admission.py').read_text())
fn=lambda tree,name:next(x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==name)
for name in ['_resolve','_qualified','canonical_quota_subject','dispatch_offline']:
 assert ast.dump(fn(old,name),include_attributes=False)==ast.dump(fn(new,name),include_attributes=False),name
bridge=json.loads(re.search(r'```json\n(.*?)\n```',(review/'implementation-review-fix.md').read_text(),re.S).group(1))
for h in bridge:assert sha((repo/h['path']).read_bytes())==h['sha256'],h['path']
execution=load(raw/'execution.json');assert execution['exit_code']==0 and execution['head']==freeze and execution['input_drift'] is False
cases=E.parse(raw/'junit.xml').findall('.//testcase')
assert len(cases)==9 and len({(v.get('classname'),v.get('name')) for v in cases})==9
assert all(all(v.find(k) is None for k in ['failure','error','skipped']) for v in cases)
assert '9 passed' in (raw/'pytest.stdout').read_text() and (raw/'pytest.stderr').stat().st_size==0
proof=load(raw/'actual-tmp/test_actual_production_routes_0/actual-production-boundary-proof.json')
http=proof['actual_http'];assert len(http)==21 and Counter(v['status'] for v in http)==Counter({400:4,403:3,422:14})
missing=[v for v in http if v['status']==400]
assert Counter(v['path'].rsplit('/',1)[-1] for v in missing)==Counter({'admission':2,'production-admission':2})
message='No reviewed production account evidence source is supported'
for v in missing:
 assert v['method']=='POST' and v['response']['error']['code']=='LIVE_BLOCKED' and v['response']['error']['message']==message and v['response']['error']['safe_retry'] is False
assert len(proof['source_calls'])==4
for requirements,v in zip(proof['source_calls'],missing):
 c=v['request']['contract'];r=requirements
 expected=dict(namespace='production-account-requirements.v1',principal_id=c['principal_id'],project_id=c['project_id'],runtime_id=c['runtime_id'],trial_key=c['trial_key'],approval_key=v['request']['approval_key'],contract_fingerprint=fp(c),software_fingerprint=c['software_fingerprint'],authorization_fingerprint=c['authorization_fingerprint'],provider='intern-ai',model=c['model'],endpoint=c['endpoint'],quota_subject=c['quota_subject'],expires_at=c['expires_at'],paid_cap=0)
 assert r==expected
 for b in c['bindings']:
  assert sha(b['content'].encode())==b['source_hash'] and fp(b['goal_snapshot'])==b['goal_fingerprint']
windows=proof['table_windows'];assert len(windows)==2
assert [v['phase'] for v in windows]==['owner-duplicates-extra-fields-and-foreign-scope','current-read-revoked-before-source']
for w in windows:
 assert w['strict_all_rows_equal'] is True and len(w['tables'])==55
 assert all(v['before_sha256']==v['after_sha256'] for v in w['tables'].values())
assert proof['literal_software_qualification']=='NOT_REACHED' and proof['downstream_calls']==[] and proof['provider_or_credential_calls']==[]
assert proof['worker_once_calls']==proof['model_calls']==proof['live_permits']==0 and proof['actual_fee_authority']=='ABSENT'
guard=load(raw/'offline-guard.json');assert guard['forbidden_attempts']==[] and guard['pytest_exitstatus']==0
positive=load(raw/'actual-tmp/test_complete_candidate_is_onl0/diagnostic.json')
assert positive['data_consistent'] is True and positive['source_verification']=='SOURCE_UNVERIFIED' and positive['fee_verification']=='NOT_VERIFIED' and positive['live_allowed'] is positive['dispatch_authorized'] is False
refusals=load(raw/'actual-tmp/test_candidate_binding_unknown0/candidate-refusals.json');assert len(refusals)==15 and all(v['code']=='LIVE_BLOCKED' for v in refusals)
projections=load(raw/'actual-tmp/test_original_contract_project0/original-contract-projections.json');assert len(projections)==3 and all(v['paid_cap']==0 for v in projections)
correction=load(raw/'closure-correction.json');assert correction['product_source_or_test_change'] is False and correction['passed_test_reexecution'] is False
old_manifest=load(raw/'manifest.json');old_stdout=old_manifest['files']['close-attempt-2.stdout']
assert old_stdout['bytes']==0 and old_stdout['sha256']==sha(b'') and (raw/'close-attempt-2.stdout').stat().st_size>0
first=load(raw/'close-attempt-1-tool-result.json');assert first['exit_code']==1 and 'pb_trial_dispatch.py' in first['observed_fatal'] and 'not a separately captured raw stderr' in first['record_kind']
result=dict(status='PASS_PURE_FILE_GIT_AST_VERIFICATION_NO_PRODUCT_EXECUTION',source_freeze=freeze,baseline=base,
 author_final_manifest_sha256=sha(manifest_bytes),author_manifest_path_entries=34,author_manifest_bytes=650709,
 author_non_db_distinct_physical_files=len(physical),author_manifest_alias_path_entries=aliases,
 author_db_path_entries_stat_only=11,author_db_distinct_physical_files=len({v['physical_path'] for v in db}),db_metadata_only=db,
 inputs=699,production=134,input_drift=False,postfix_to_freeze_bytes_equal=True,
 source_changes=changed,unchanged_function_ast=['_resolve','_qualified','canonical_quota_subject','dispatch_offline'],
 unique_nodes=9,executions=9,passed=9,failed=0,junit_suite_seconds=float(E.parse(raw/'junit.xml').find('.//testsuite').get('time')),outer_seconds=execution['elapsed_seconds'],
 asgi_structured_request_response_records=21,asgi_status_counts=dict(Counter(str(v['status']) for v in http)),production_source_calls=4,
 diagnostic='Fully matching synthetic data remains SOURCE_UNVERIFIED/NOT_VERIFIED/livefalse/dispatchfalse; not evidence of actual account/entitlement.',
 table_scope='Two executed exact55table equality assertions with retained per-table FP/rowcounts; reviewer checked stored FP equality and source oracle, not original rows or DB.',
 source_absent=True,literal_software_qualification='NOT_REACHED',guard_forbidden_attempts=[],
 helper_issues='Both closure helper issues retained, no product/test rerun or failure; first observed tool-result metadata not captured raw stderr; original manifest zero stdout hash superseded without overwrite.',
 qualification_limits=['ASGI/TestClient synthetic only; not native browser or real network HTTP','No production evidence source/resolver installation, zero-fee authority, sender, valid LIVE permit, credentials, provider/model/Worker calls','No production software qualification PASS claimed; retained downstream gates NOT_REACHED','No Windows/PG/CI/real semantic/actual fees or old cancelled window qualification'],
 reviewer_scope='Pure files/Git/AST only. No product imports/tests/HTTP/DB/SQL/network or repo writes. Author directory never written.')
with (review/'verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='db_metadata_only'},ensure_ascii=False,indent=2))
