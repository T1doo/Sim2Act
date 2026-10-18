from pathlib import Path
import ast,copy,hashlib,json,subprocess
repo=Path('/workspace/Sim2Act');out=Path('/workspace/production-trial-stages-review-20261018');base='8fd545f75e350085a9e4615a2bea2779c66be31b'
def git(*a):return subprocess.check_output(['git','-c','core.fsmonitor=false',*a],cwd=repo).decode()
p='src/sim2act/goal_applications.py';old_text=git('show',base+':'+p);new_text=(repo/p).read_text()
old=ast.parse(old_text);new=ast.parse(new_text)
a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='source_scope_gate')
b=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_source_scope_gate')
assert old_text.splitlines()[a.lineno:a.end_lineno]==new_text.splitlines()[b.lineno:b.end_lineno]
a.name=b.name;assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
new.body=[n for n in new.body if not isinstance(n,ast.FunctionDef) or n.name not in ('source_scope_gate','_journal_scope_anchor')]
b.name='source_scope_gate';a.name='source_scope_gate'
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
p='tests/test_production_trial_stages.py';old=ast.parse(git('show',base+':'+p));new=ast.parse((repo/p).read_text())
for n in new.body:
 if isinstance(n,ast.ImportFrom) and n.module=='sim2act.db':n.names=[x for x in n.names if x.name!='grants']
fn=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='test_fresh_actual_prefix_rejects_incomplete_mixed_or_changed_proof_without_writes')
removed=[];kept=[]
for n in fn.body:
 if isinstance(n,ast.ImportFrom) and n.module=='sim2act' and any(x.name=='goal_applications' and x.asname=='ga' for x in n.names):removed.append('ga import')
 elif isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='expired':removed.append('two permission windows')
 else:kept.append(n)
fn.body=kept
assert removed==['ga import','two permission windows']
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
paths=['src/sim2act/goal_applications.py','tests/test_production_trial_stages.py']
record={'kind':'STATIC_WIP_FILE_GIT_AST_ONLY','base':base,'status':'NO_DEFINITE_P1_P2_PENDING_FREEZE_EXECUTION','original_source_scope_body_text_and_ast_identical':True,'remaining_goal_module_ast_identical_after_removing_wrapper_and_anchor':True,'old_test_module_ast_identical_except_grants_import_and_two_B_permission_windows':True,'windows':['actual hit with full gate once and reauthorization observed; SQL runtime READ revoke invalidates epoch','actual all-runtime-READ expiry after <=about2s; no intervening write; cached hit original GRANT_REVOKED and full gate still once'],'files':[{'path':p,'bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in paths],'limits':['No product/test/application imports or DB/SQL/network/model/credential operations','No runtime performance or qualification PASS claimed','Directory remains unsealed']}
(out/'source-scope-wip-ast-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':record['status'],'source_scope_body_text_ast_unchanged':True,'original_remaining_source_test_ast_unchanged':True}))
