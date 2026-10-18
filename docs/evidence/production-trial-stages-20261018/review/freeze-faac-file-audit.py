from pathlib import Path
import ast, hashlib, json, subprocess
repo=Path('/workspace/Sim2Act'); out=Path('/workspace/production-trial-stages-review-20261018')
head='faac95dce3174c426295fda26e40acf14a11a9c1'; base='4bb3c26f5f67511795771c9187537aee4e852590'
def git(*a): return subprocess.check_output(['git','-c','core.fsmonitor=false',*a],cwd=repo).decode()
assert git('rev-parse','HEAD').strip()==head
assert not git('status','--porcelain')
scope=json.loads(Path('/workspace/production-trial-stages-20261018/final-freeze-scope.json').read_text())
assert scope['baseline']==base and scope['source_freeze']==head
changed=git('diff','--name-only',base,head).splitlines()
assert changed==scope['changed']
for p, blob in scope['changed_blobs'].items(): assert git('rev-parse',head+':'+p).strip()==blob
src={line.split('\t',1)[1]:line.split()[2] for line in git('ls-tree','-r',head,'--','src/').splitlines()}
old={line.split('\t',1)[1]:line.split()[2] for line in git('ls-tree','-r',base,'--','src/').splitlines()}
assert len(src)==len(old)==138
assert sum(src[p]!=old[p] for p in src)==8
fix=json.loads((out/'heartbeat-wip-fix-verification.json').read_text())
assert hashlib.sha256((repo/'src/sim2act/production_trial_sender.py').read_bytes()).hexdigest()==fix['sender_sha256']
prior=json.loads((out/'heartbeat-wip-finding.json').read_text())
for item in prior['files']:
 if item['path']!='src/sim2act/production_trial_sender.py': assert hashlib.sha256((repo/item['path']).read_bytes()).hexdigest()==item['sha256']
readseg=json.loads((out/'read-segment-wip-verification.json').read_text())
for item in readseg['files']:
 if item['path'] in ('src/sim2act/goal_applications.py','tests/test_production_trial_stages.py'): assert hashlib.sha256((repo/item['path']).read_bytes()).hexdigest()==item['sha256']
protected=['production_trial_journal.py','production_trial_policy.py','production_trial_source.py','production_evidence.py','production_trial_admission.py','model.py','natural_trial_runs.py','natural_trial_budget.py','config.py','pb_natural_specs.py','text_workflows.py']
for p in protected: assert src['src/sim2act/'+p]==old['src/sim2act/'+p]
result={'status':'STATIC_FREEZE_BRIDGE_PASS_ACTUAL_PENDING','head':head,'baseline':base,'git_clean_at_read':True,'production_count':138,'changed_production_count':8,'unchanged_production_count':130,'new_test_paths':['tests/test_production_trial_stages.py'],'author_source_scope_blobs_independently_matched':True,'reviewed_wip_and_post_heartbeat_fix_hashes_equal':True,'protected_baseline_blob_equal':['src/sim2act/'+p for p in protected],'files':[{'path':p,'bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in changed],'execution_input_maps':'NOT_AUDITED_PENDING_CLOSED_RUN6','not_done':['No product/pytest/DB/SQL/network/model/credential operations','No active run6 files inspected','No repository or sealed-directory writes'],'path_lookup_note':'Author source-scope file is at root final-freeze-scope.json; initial author/ prefixed read returned ENOENT before filename-only lookup. No product effect.'}
(out/'freeze-faac-static-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'head':head,'production_count':138,'changed_production_count':8,'source_scope_blobs':len(scope['changed_blobs'])}))
