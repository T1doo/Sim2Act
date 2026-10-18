"""Pure Git/source byte bridge; no application import or evidence-run reads."""
from pathlib import Path
import ast, hashlib, json, subprocess

repo=Path('/workspace/Sim2Act')
review=Path('/workspace/production-trial-stages-review-20261018')
base='4bb3c26f5f67511795771c9187537aee4e852590'
prior='8fd545f75e350085a9e4615a2bea2779c66be31b'
freeze='cdcae63e6ca6294b98ee6764b832d2d001e4de05'
def git(*args):
    return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
def tree(ref):
    result={}
    for line in git('ls-tree','-r',ref,'src/sim2act').decode().splitlines():
        header,path=line.split('\t',1)
        result[path]=header.split()[2]
    return result
assert git('rev-parse','HEAD').decode().strip()==freeze
assert git('status','--porcelain')==b''
scope=json.loads(Path('/workspace/production-trial-stages-20261018/final-freeze-scope.json').read_bytes())
assert scope['source_freeze']==freeze and scope['baseline']==base
changed=git('diff','--name-only',base,freeze).decode().splitlines()
assert changed==scope['changed']
bridges=[]
for path, expected in scope['changed_blobs'].items():
    blob=git('rev-parse',freeze+':'+path).decode().strip()
    raw=(repo/path).read_bytes()
    assert blob==expected
    assert raw==git('show',freeze+':'+path)
    bridges.append({'path':path,'git_blob':blob,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
before,after=tree(base),tree(freeze)
prod_changed=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
assert len(before)==len(after)==138 and prod_changed==scope['production_changed']
assert len(after)-len(prod_changed)==130
prior_diff=git('diff','--name-only',prior,freeze).decode().splitlines()
assert prior_diff==['src/sim2act/goal_applications.py','tests/test_production_trial_stages.py']
prior_review=json.loads((review/'source-scope-single-reauth-verification.json').read_bytes())
by_path={b['path']:b for b in bridges}
assert by_path['src/sim2act/goal_applications.py']['sha256']==prior_review['current_single_reauth_source_sha256']
assert by_path['tests/test_production_trial_stages.py']['sha256']==prior_review['test_sha256_unchanged']
old=ast.parse(git('show',prior+':src/sim2act/goal_applications.py'))
new=ast.parse((repo/'src/sim2act/goal_applications.py').read_bytes())
old_fn=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='source_scope_gate')
new_fn=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_source_scope_gate')
new_fn.name=old_fn.name
assert ast.dump(old_fn,include_attributes=False)==ast.dump(new_fn,include_attributes=False)
result={'kind':'INDEPENDENT_FROZEN_GIT_SOURCE_BYTE_BRIDGE','status':'STATIC_PASS_ACTUAL_QUALIFICATION_PENDING',
        'source_freeze':freeze,'baseline':base,'previous_checkpoint':prior,'worktree_clean_at_check':True,
        'changed_since_checkpoint':prior_diff,'production_count':138,'production_changed_since_baseline':8,
        'production_unchanged_since_baseline':130,'changed_source_and_test_blobs_match_author_scope':True,
        'last_reviewed_goal_source_and_test_bytes_exact':True,'original_full_scope_function_AST_preserved':True,
        'files':bridges,'execution_plan':{'groups':['run-8-chain','run-8-negatives'],'expected_unique_nodes':4,
        'B_windows_only_if_executed':9,'failure_path':'NOT_QUALIFIED; missing or fixture-error B execution not inferred'},
        'limits':['No run8 artifacts read','No product, pytest, DB, SQL, network or private holdout access',
                  'No remote verification; parent-reported remote checkpoint remains 8fd',
                  'No source/test mutations by reviewer; reviewer directory remains unsealed']}
(review/'freeze-cdca-static-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
