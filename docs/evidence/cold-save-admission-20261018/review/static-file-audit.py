"""Pure Git/AST check only; no application imports or execution evidence reads."""
from pathlib import Path
import ast, copy, hashlib, json, subprocess
repo=Path('/workspace/Sim2Act');out=Path('/workspace/cold-save-admission-review-20261018')
base='f89f8f4431a63e22a9f067cd74e3bdd4051d84ea';freeze='fd96df814e8c0fb6db6651ce77eb484951240ecc'
def git(*args): return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
def blob(ref,p): return git('show',ref+':'+p)
def tree(ref):
 return {line.split('\t',1)[1]:line.split('\t',1)[0].split()[2] for line in git('ls-tree','-r',ref,'src/sim2act').decode().splitlines()}
def functions(data): return {n.name:n for n in ast.parse(data).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
def dump(n): return ast.dump(n,include_attributes=False)
assert git('rev-parse','HEAD').decode().strip()==freeze and git('status','--porcelain')==b''
paths=git('diff','--name-only',base,freeze).decode().splitlines()
assert paths==['src/sim2act/pa_spec_apps.py','tests/test_production_trial_stages.py']
p=paths[0];old=ast.parse(blob(base,p));new=ast.parse(blob(freeze,p));normalized=copy.deepcopy(new)
fn=next(x for x in normalized.body if isinstance(x,ast.FunctionDef) and x.name=='_advance_local')
indices=[]
for i,node in enumerate(fn.body):
 if not isinstance(node,ast.With) or len(node.body)!=1 or not isinstance(node.body[0],ast.Assign): continue
 assign=node.body[0]
 if (len(assign.targets)==1 and isinstance(assign.targets[0],ast.Name) and assign.targets[0].id=='live'
     and isinstance(assign.value,ast.Call) and isinstance(assign.value.func,ast.Name) and assign.value.func.id=='commit_guard'):
  assert isinstance(fn.body[i-1],ast.ImportFrom) and fn.body[i-1].module=='pa_trial_dispatch'
  assert [n.name for n in fn.body[i-1].names]==['_journal_reads']
  assert dump(node.items[0].context_expr)==dump(ast.parse('_journal_reads(worker, c)',mode='eval').body)
  indices.append(i)
assert len(indices)==1
i=indices[0];fn.body[i-1:i+1]=fn.body[i].body
assert dump(old)==dump(normalized)
testpath=paths[1];ot,nt=functions(blob(base,testpath)),functions(blob(freeze,testpath))
unchanged_tests=['test_actual_pa_three_two_two_reaches_existing_results_and_pending_owner',
                 'test_known_accounting_cannot_accept_wrong_original_business_schema',
                 'test_original_controller_store_is_fixed_through_late_body_and_failure']
assert all(dump(ot[n])==dump(nt[n]) for n in unchanged_tests)
oldB=ot['test_fresh_actual_prefix_rejects_incomplete_mixed_or_changed_proof_without_writes']
newB=nt['_generation_proof_rejections']
old_asserts=[dump(x) for x in ast.walk(oldB) if isinstance(x,ast.Assert)]
new_asserts=[dump(x) for x in ast.walk(newB) if isinstance(x,ast.Assert)]
assert old_asserts==new_asserts
# Original nine-window code remains exact after removing only t alias assignment and provenance output.
assert dump(ast.Module(body=oldB.body[1:-1],type_ignores=[]))==dump(ast.Module(body=newB.body[:-1],type_ignores=[]))
before,after=tree(base),tree(freeze)
changed=[k for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)]
assert len(before)==len(after)==138 and changed==[p]
files=[]
for path in paths:
 raw=(repo/path).read_bytes();assert raw==blob(freeze,path)
 files.append({'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob':git('rev-parse',freeze+':'+path).decode().strip()})
result={'kind':'INDEPENDENT_READ_ONLY_STATIC_GIT_AST_REVIEW','status':'NO_NEW_DEFINITE_P1_P2_ACTUAL_COLD_SAVE_NOT_YET_QUALIFIED',
 'baseline':base,'source_freeze':freeze,'worktree_clean_at_review':True,'changed_paths':paths,'files':files,
 'production_count':138,'changed_production':1,'unchanged_production_Git_blobs':137,
 'entire_production_AST_identical_after_removing_only_new_import_and_read_context_wrapper':True,
 'original_guards_calls_and_write_sequence_preserved':True,'unchanged_full_A_C_D_test_AST':unchanged_tests,
 'B_all_original_assert_AST_and_nine_window_body_preserved':True,
 'fixture_change':'generated_prefix performs this-round actual gen3 before yielding; B depends on it. actual_prefix continues full same-fixture Source2+Cold2; no stored-prefix replay.',
 'context_boundary':'Existing exact JournalTrialBinding only; pinned Store/connection/current transaction; existing SourceReads thread/driver/write epoch fencing and invalidation unchanged; legacy returns nullcontext.',
 'limits':['No product/pytest/Worker/model/application import/DB/SQL/network/private holdout access',
           'No author run artifacts read','Old sealed evidence/review directories not modified',
           'Component stale-lease diagnostics do not qualify Cold SAVE or predict runtime improvement',
           'No future push or complete current-stage qualification endorsed','New review directory remains unsealed']}
(out/'static-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
