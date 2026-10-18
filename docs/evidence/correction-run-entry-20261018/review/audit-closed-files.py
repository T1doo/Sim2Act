"""File-only audit of explicitly closed synthetic navigation outputs; no Git or product execution."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
root=Path('/workspace/correction-run-entry-20261018');repo=Path('/workspace/Sim2Act');review=Path('/workspace/correction-run-entry-review-20261018')
def sha(b):return hashlib.sha256(b).hexdigest()
def snapshot():
 result={}
 for p in sorted(root.rglob('*')):
  if p.is_symlink():continue
  if p.is_file():
   assert '.db' not in p.name and '.sqlite' not in p.name
   b=p.read_bytes();result[str(p.relative_to(root))]={'bytes':len(b),'sha256':sha(b)}
 return result
def read(n):return json.loads((root/n).read_bytes())
before=snapshot()
sealpath=root/'manifest.json'
author_seal_sha='f28d69256f11a7af2a640610a3597d1590667d1ffb1993bf06a998a8e18f4ee9'
assert sha(sealpath.read_bytes())==author_seal_sha
author_entries=json.loads(sealpath.read_bytes())['files']
assert len(author_entries)==16 and sum(e['bytes'] for e in author_entries)==54472
for e in author_entries:
 b=(root/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
assert len(before)==len(author_entries)+1
source=read('reviewed-source-map.json');assert len(source)==13
for path,e in source.items():
 b=(repo/path).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],path
wip=json.loads((review/'wip-static-observations.json').read_bytes())
for path in ('src/sim2act/web/owner-review.js','src/sim2act/web/index.html'):
 assert source[path]==wip['observed_unfrozen_bytes'][path]
proofs={}
for name,want,n in (('first-run.json','FAIL',19),('second-run.json','PASS',24),
 ('pytest-qualified-temp/test_verified_correction_run_e0/correction-run-entry.json','PASS',24),
 ('existing-navigation.json','PASS',36)):
 v=read(name);assert v['status']==want and len(v['checks'])==n
 for asset,fp in v['assets'].items():assert source['src/sim2act/web/'+asset]['sha256']==fp
 for case in v['cases']:
  assert all(call['method']=='GET' for call in case.get('calls',[]))
 proofs[name]={'status':want,'checks':n,'classification':v['classification'],'assets_match_current':True,
               'saved_navigation_cases':len(v['cases']),'error':v.get('error')}
qualified=read('pytest-qualified-temp/test_verified_correction_run_e0/correction-run-entry.json')
assert qualified['checks']==read('second-run.json')['checks']
assert qualified['worker']=='NOT_RUN' and qualified['real_model']=='NOT_RUN' and qualified['real_human_semantics']=='NOT_RUN'
junits={}
for name,expected in (('pytest.xml','FAIL'),('pytest-qualified.xml','PASS')):
 tree=ET.fromstring((root/name).read_bytes());cases=list(tree.iter('testcase'));assert len(cases)==1
 c=cases[0];status='FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'PASS'
 assert status==expected
 if expected=='FAIL':assert "Cannot find module 'jsdom'" in ''.join(tree.itertext())
 junits[name]={'name':c.get('name'),'status':status,'seconds':c.get('time')}
checks=[]
for i in range(1,6):
 c=read('check-'+str(i)+'.json');assert c['returncode']==0;checks.append(c)
code=(repo/'src/sim2act/web/owner-review.js').read_text()
start=code.index('$("correction-open-run").onclick=');end=code.index('$("correction-prepare").onclick=',start)
new=code[start:end]
assert 'showInternalInstance(v.iid,view)' in new and 'showInternalRun(target.rid,view,instance)' in new
assert 'selection=view.instanceGeneration+1,runSelection=view.runGeneration+1' in new
assert '"POST"' not in new and 'selectionCurrent=' not in new
backend=(repo/'src/sim2act/natural_spec_corrections.py').read_text()
assert 'spec.require(not hint(c,rid), "Corrections-of-corrections are outside this finite slice")' in backend
assert 'spec.require(not hint(c,rid))' in backend
production=(repo/'src/sim2act/production_evidence.py').read_text()
resolver=production[production.index('def resolve_account('):]
assert '_deny(SOURCE_MISSING)' in resolver and '-> NoReturn' in resolver
worker=(repo/'src/sim2act/worker.py').read_text();main=worker[worker.index('def main():'):]
assert 'w = Worker(Store(s.database_url), s)' in main and 'pa_trial=' not in main
binding=(repo/'src/sim2act/pa_trial_dispatch.py').read_text();gate=binding[binding.index('def _binding(worker):'):binding.index('def _admission(worker):')]
assert 'worker.store.test_only and worker.store.sqlite' in gate and 'worker.s.live_enabled is False and worker.s.token == ""' in gate
assert 'type(worker.goal_planner_transport) is httpx.MockTransport' in gate
assert snapshot()==before
result={'kind':'INDEPENDENT_FILE_AND_SOURCE_REVIEW_NO_PRODUCT_EXECUTION','conclusion':'FINITE_SYNTHETIC_NAVIGATION_PASS',
 'freeze_basis':'Exact reviewed-source-map.json file bytes; no Git/commit or future push verification by reviewer',
 'closed_author_files':before,'closed_author_file_count':len(before),'closed_author_raw_bytes':sum(v['bytes'] for v in before.values()),
 'author_manifest_sha256':author_seal_sha,'author_manifest_entries_verified':16,'author_manifest_raw_bytes':54472,'author_directory_sealed_at_final_audit':True,'closed_file_set_unchanged_during_audit':True,
 'reviewed_source_files':source,'production_two_files_match_prior_WIP_review':True,
 'proofs':proofs,'JUnit':junits,'new_unique_pytest_node':1,'pytest_executions':2,'pytest_PASS':1,'pytest_FAIL':1,
 'direct_new_Node_runs':{'first':'FAIL19checks','second':'PASS24checks'},
 'pytest_reexecutes_same_new_Node_scenario':'PASS24checks; duplicate validation, not a second unique case',
 'existing_synthetic_navigation':'PASS36checks; no backend/Worker qualification',
 'static_check_receipts':checks,'new_button_GET_only_source':True,'original_one_level_correction_guard_retained':True,
 'real_production_boundary':{'resolve_account':'Fixed SOURCE_MISSING after requirements_for, no source override',
 'production_preflight':'Original _approved before resolver; _qualified/admit retained but unreachable without source',
 'worker_main':'Creates ordinary Worker without pa_trial',
 'Journal':'Exact test_only SQLite/mock/livefalse/empty token/MockTransport; not a LIVE installation'},
 'limits':['JSDOM executes actual controllers against synthetic GET responses; PBUse/logic/switch renderers stubbed',
 'No actual backend HTTP, Worker, model, DB, real identity authorization or human semantic acceptance exercised in this new test',
 'Existing full correction CJS changed to use button but not rerun',
 'First unreachable-selection harness explanation supported by parent account and current reachable scenario; original pre-fix harness bytes not independently retained in this raw set',
 'First pytest missing-jsdom failure retained; NODE_PATH correction is environment/harness setup, not production change',
 'All24/36checks are assertions within synthetic harnesses, not that many pytest cases',
 'Reviewer did not call Git/auth/network/product/pytest/DB/SQL/private holdout; no old sealed writes or future push endorsement']}
(review/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'conclusion':result['conclusion'],'raw_files':len(before),'raw_bytes':result['closed_author_raw_bytes'],'source_files_matched':len(source),'new_checks':24,'existing_checks':36,'pytest':'1PASS+1retainedFAIL','product_runs_by_reviewer':0},ensure_ascii=False))
