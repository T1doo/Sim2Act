from pathlib import Path
import ast
import hashlib
import json
import subprocess

repo=Path('/workspace/Sim2Act')
out=Path('/workspace/production-trial-stages-review-20261018')
base='9c0d7bda64a745ad614e1d94cf0442e368d38ed9'
def git(*args):
    return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo).decode()
def funcs(text):
    return {n.name:n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
p='src/sim2act/goal_applications.py'
old=funcs(git('show',base+':'+p))['verified_candidate']
new=funcs((repo/p).read_text())['_verified_candidate']
old.name=new.name
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
pa='src/sim2act/natural_live_admission.py'
old=funcs(git('show',base+':'+pa))['_stage_current']
new=funcs((repo/pa).read_text())['_stage_current_read']
old_body=[n for n in old.body if not isinstance(n,ast.ImportFrom)]
new_body=list(new.body)
assert isinstance(old_body[0],ast.Expr) and isinstance(old_body[0].value,ast.Constant)
old_body=old_body[1:]
assert [ast.dump(n,include_attributes=False) for n in old_body]==[ast.dump(n,include_attributes=False) for n in new_body]
assert not git('diff',base,'--','src/sim2act/pb_natural_specs.py','src/sim2act/db.py')
paths=git('diff','--name-only',base).splitlines()
record={
 'kind':'STATIC_WIP_FILE_GIT_AST_REVIEW', 'base_head':git('rev-parse','HEAD').strip(),
 'not_frozen':True, 'status':'NO_DEFINITE_P1_P2_PENDING_FREEZE_AND_ACTUAL_QUALIFICATION',
 'changed_paths':paths, 'original_verified_candidate_body_ast_identical':True,
 'original_stage_current_read_body_ast_identical':True,
 'source_reads_and_write_epoch_hooks_unchanged':True,
 'files':[{'path':p,'bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in paths],
 'observations':[
  'Complete first proof remains; stored and reused results are deep copies.',
  'Distinct cache namespace and full Run/limits fingerprints; exact SourceReads connection/transaction/driver/thread/epoch current check.',
  'Current source_scope_gate before lookup and collected authorities rechecked on every hit.',
  'Any non-SELECT on the original connection invalidates existing token and increments existing epoch.',
  'Current test proves cached result exists/deepcopy and write invalidation, not independently counted full-proof call count.',
  'Global verified_candidate wrapper may also opt in if an existing SourceReads call encounters a three-journal-marker generation; ordinary old marker paths fall back unchanged.'
 ],
 'not_done':['No product/test/application imports','No DB/SQL/HTTP/network/model/credentials','No profile or run-4 raw audit','No repository or old sealed directory writes']
}
(out/'read-segment-wip-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':record['status'],'original_bodies_ast_identical':True,'changed_paths':paths},ensure_ascii=False))
