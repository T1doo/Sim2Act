from pathlib import Path
import ast
import hashlib
import json
import subprocess

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-trial-stages-review-20261018')
head = '9c0d7bda64a745ad614e1d94cf0442e368d38ed9'
prior = 'c37736161c69562745078cbc8ee59d95c1f6d287'
p = 'src/sim2act/pa_trial_dispatch.py'
def git(*args):
    return subprocess.check_output(['git','-c','core.fsmonitor=false',*args], cwd=repo).decode()
def src(ref, name):
    return git('show',f'{ref}:{name}')
def funcs(text):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
assert git('rev-parse','HEAD').strip()==head
assert not git('status','--porcelain')
assert git('diff','--name-only',prior,head).splitlines()==[p]
old,new=funcs(src(prior,p)),funcs(src(head,p))
assert old.keys()==new.keys()
changed=sorted(k for k in new if new[k]!=old[k])
assert changed==['check_journal_claim','journal_stage_accounted']
text=src(head,p)
history=text[text.index('def journal_stage_accounted('):]
assert history.index('gate.require(job_scope_gate(store, c, user, rid))') < history.index('app_key = c.execute') < history.index('actual = c.execute(select(attempts)')
assert 'internal_app_runs.c.id == phase.authority.app_run_id' in history
assert 'internal_app_runs.c.instance_id == phase.authority.instance_id' in history
assert 'internal_app_runs.c.principal_id == user' in history
assert 'owner["request_key"] == "internal:" + phase.authority.app_run_id' in history
admission=src(head,'src/sim2act/natural_live_admission.py')
assert 'bound["app_run"]["request_key"] == getattr(contract.stage_keys, stage)' in admission
jobs=src(head,'src/sim2act/app_jobs.py')
assert 'request_key="internal:" + aid' in jobs
assert 'request_key=key,' in jobs
unchanged=['src/sim2act/production_trial_sender.py','tests/test_production_trial_stages.py','src/sim2act/natural_live_admission.py','src/sim2act/db.py','src/sim2act/app_jobs.py','src/sim2act/pa_spec_apps.py']
assert not git('diff','--name-only',prior,head,'--',*unchanged)
result={
 'review':'STATIC_FILE_GIT_AST_ONLY', 'status':'NO_DEFINITE_P1_P2_PENDING_RUN4',
 'head':head,'previous':prior,'git_clean_at_read':True,'only_changed_path':p,
 'changed_function_asts':changed,
 'key_contract':{'generate':'Core Run.request_key == contract.stage_keys.generate', 'source_cold':'AppRun.request_key == stage key; Core Run.request_key == internal:<phase.app_run_id>'},
 'historical_scalar_join_after_scope_before_attempt_payload':True,
 'claim_ns_original_full_stage_and_phase_validation_preserved':True,
 'unchanged_paths_vs_previous':unchanged,
 'path':p,'bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest(),
 'limits':['No product/test/application imports executed','No DB/SQL/HTTP/network/credential reads','No active run-4 artifacts read','Run-3 ERROR details are parent-reported, not raw-audited in this static step','Directory remains unsealed pending actual evidence']
}
(out/'freeze-9c0-static-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'head':head,'changed_function_asts':changed},ensure_ascii=False))
