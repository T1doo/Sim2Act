"""Pure closed-file/Git audit; does not import or execute product code/read DB."""
from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
repo=Path('/workspace/Sim2Act'); author=Path('/workspace/natural-trial-budget-view-20261018')
r=author/'attempt-2'; f=r/'actual-tmp/test_original_trial_budget_is_0'
out=Path('/workspace/natural-admission-design-review-20261018/closed-evidence-audit.json')
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda p:json.loads(p.read_text())
fp=lambda v:sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
a=load(f/'results.json'); proof=load(f/'proof.json'); fixture=load(f/'synthetic-ledger-fixture.json')
execution=load(r/'execution.json'); before=load(r/'inputs-before.json'); after=load(r/'inputs-after.json')
assert execution['exit_code']==0 and a['status']==proof['status']=='PASS'
assert before==after and len(before['inputs'])==697
source_drift=[p for p,h in before['inputs'].items() if sha((repo/p).read_bytes())!=h['sha256'] or (repo/p).stat().st_size!=h['bytes']]
assert not source_drift,source_drift
assert len(proof['production_sha256'])==133
for name,digest in proof['production_sha256'].items():assert sha((repo/name).read_bytes())==digest
http=a['requests'];assets=a['static_resource_loads'];controls=load(f/'fixture-http.json')
for row in http:
 assert row['method']=='GET'
 raw=row['response_text'].encode();assert sha(raw)==row['response_utf8_sha256']
 assert json.loads(row['response_text'])==row['response']
for row in controls:
 assert sha(row['response_text'].encode())==row['response_sha256']
for row in assets:
 path=repo/'src/sim2act/web'/(row['path'].lstrip('/') or 'index.html')
 assert row['status']==200 and path.stat().st_size==row['bytes'] and sha(path.read_bytes())==row['sha256']
assert len(http)==26 and len(assets)==27 and len(controls)==8
budget=[v for v in http if v['path'].endswith('/budget')]
assert [v['status'] for v in budget]==[409,200,200]
assert budget[0]['response']['error']['code']=='VERSION_CONFLICT'
main=a['main_preparation']; contract=main['contract']; accepted=main['approval']['approval']
assert fp(contract)==main['review_token']==main['approval']['contract_fingerprint']==accepted['contract_fingerprint']
assert fp(accepted)==main['approval']['approval_fingerprint']
key=accepted['request']['request_key'];assert accepted['request']['expected_contract_fingerprint']==fp(contract)
expected=dict(trial_key=contract['trial_key'],approval_key=key,contract_fingerprint=fp(contract),
 project_id=contract['project_id'],principal_id=contract['principal_id'],runtime_id=contract['runtime_id'],
 quota_subject=contract['quota_subject'],expires_at=contract['expires_at'])
for row in budget[1:]:
 value=row['response'];p=value['budget_projection'];slot=value['ledger']['slots'][0]
 assert value['scope']==expected and value['dispatch_authorized'] is False and value['live_admission']=='NOT_VERIFIED'
 assert value==fixture['settled'] and slot['reservation']==fixture['request']
 assert len(value['ledger']['slots'])==1 and value['ledger']['halted'] is True
 assert slot['settlement']['prompt_tokens']==5 and slot['settlement']['completion_tokens'] is None and slot['settlement']['total_tokens'] is None
 assert slot['accepted'] is False and value['usage_status']=='UNKNOWN' and value['total_tokens'] is None
 assert value['known_total_tokens']==0 and value['status']=='RECONCILING'
 assert p['held_requests']==1 and p['held_token_envelope']==1124 and p['unresolved_usage_requests']==1
 assert p['unreserved_request_capacity']==6 and p['unreserved_token_capacity']==192000-1124
 assert p['money']==dict(paid_cap=0,actual_paid=None,currency=None,status='UNKNOWN',fee_verification='NOT_LIVE_VERIFIED',live_allowed=False)
 for stage,limit in [('generate',3),('source',2),('cold',2)]:
  own=[s for s in value['ledger']['slots'] if s['reservation']['stage']==stage]; q=p['stages'][stage]
  assert q['request_limit']==limit and q['held_requests']==len(own)
  assert q['held_token_envelope']==sum(s['reservation']['wire_bytes']+1024 for s in own)
  assert q['run_id']==(own[0]['reservation']['run_id'] if own else None)
assert fixture['consent_is_live_authority'] is False and fixture['valid_live_tokens_created']==fixture['worker_once_calls']==0
assert len(fixture['permits'])==3 and all(p['scope']=='SYNTHETIC_ONLY' and p['live_allowed'] is False for p in fixture['permits'])
held=a['delayed_actual_budget_response']
assert held['status']==200 and held['server_received'] and held['response_complete_before_hold'] and held['released']
assert held['scope_before_release']==held['scope_after_release']
assert held['scope_before_release']['entry']['key']=='empty-budget-view' and held['scope_before_release']['budget_output']==''
assert held['response_utf8_sha256']==http[held['request_index']]['response_utf8_sha256']
assert a['other_project_scope']['budget_output']==a['other_project_scope']['trial_scope']=='' and a['other_project_scope']['budget_read_disabled'] is True
assert a['empty_budget_failure']['scope_after_failure']['entry']['state']=='unknown'
assert a['empty_budget_failure']['scope_after_failure']['trial_scope']==a['empty_budget_failure']['scope_after_failure']['budget_output']==''
assert proof['before_fingerprint']==proof['after_fingerprint'] and len(proof['protected_tables_unchanged'])==len(proof['table_fingerprints'])==55
assert proof['changed_tables']==[] and proof['provider_calls']==[] and a['downloads']==[] and a['page_errors']==[]
assert load(f/'provider-calls.json')==[]
assert proof['page_post_requests']==proof['page_worker_calls']==proof['real_model_requests']==proof['valid_live_tokens_created']==0
helpers=a['synthetic_validator_checks'];assert len(helpers)==4
assert [q['outcome'] for q in helpers]==['ACCEPTED','REJECTED','REJECTED','REJECTED']
assert all(q['classification']=='SYNTHETIC_VALIDATOR_ONLY_NOT_HTTP' for q in helpers)
assert len(a['checks'])==48 and sum(s.startswith('isolated synthetic validator rejects:') for s in a['checks'])==3
assert len(a['actions'])==14 and a['boots']==1
first=ET.parse(author/'junit.xml').findall('.//testcase');second=ET.parse(r/'junit.xml').findall('.//testcase')
assert len(first)==3 and sum(t.find('failure') is not None for t in first)==1
assert len(second)==1 and second[0].find('failure') is None and second[0].find('error') is None
assert first[0].get('name')==second[0].get('name')
prior='85b65963ec91d723185164a4f6ee708fc8e19a27';freeze='8e2cce44597a0a5adf057d47271b85ab6d763ed6'
run=lambda *args:subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo,text=True)
assert run('rev-parse','HEAD').strip()==freeze
changed=run('diff','--name-only',prior,freeze).splitlines()
assert changed==['tests/natural_trial_budget_view_ui.cjs']
assert run('diff','--numstat',prior,freeze).splitlines()==['1\t0\ttests/natural_trial_budget_view_ui.cjs']
assert run('diff','--name-only','fae2a3d7de3978671ca9c1c1c19cb8012e731eeb',freeze,'--','src').splitlines()==['src/sim2act/web/index.html','src/sim2act/web/natural-goal.js']
paths=[r/'execution.json',r/'junit.xml',r/'inputs-before.json',r/'inputs-after.json',f/'results.json',f/'proof.json',f/'fixture-http.json',f/'synthetic-ledger-fixture.json',f/'provider-calls.json',f/'driver.stdout',f/'driver.stderr']
report=dict(status='PASS_PURE_FILE_GIT_AUDIT_NOT_PRODUCT_EXECUTION',freeze=freeze,
 current_unique_nodes_pass=3,total_node_executions=4,total_pass=3,total_fail=1,
 ui_checks_labels=48,actual_page_flow_check_labels=45,synthetic_negative_check_labels_included=3,
 synthetic_helper_records=4,page_actions=14,page_api_gets=26,served_assets=27,page_http=53,
 captured_fixture_http=8,captured_total_http=61,boots=1,actual_budget_statuses=[409,200,200],
 frozen_inputs=697,production_files=133,input_drift=source_drift,
 unknown_usage=dict(prompt_tokens=5,completion_tokens=None,total_tokens=None,known_total_components=0,held_requests=1,envelope=1124),
 limits='One P-A ledger view with only generate stage occupied, not actual three-stage Worker/model trial or P-B UI; source/cold empty rows only.',
 table_evidence='55-table before==after was asserted during author pytest; retained proof has whole-snapshot FP plus per-table FP/rowcounts, not raw rows; reviewer did not independently recompute rows/read DB.',
 qualification='Two deny PASS under 85b preserved via sole unused-CJS-line bridge; UI FAIL under85b retained; UI PASS under8e. No all-green full-suite claim.',
 reviewer_scope='Pure closed files/Git only; no product/tests/HTTP/Worker/model/DB/SQL/network execution or repo writes.',
 raw_files=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in paths])
with out.open('x',encoding='utf-8') as h:json.dump(report,h,ensure_ascii=False,indent=2);h.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='raw_files'},ensure_ascii=False,indent=2))
