import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/ordinary-owner-evidence-20261017');os.chdir(root)
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],text=True).strip()
sha=git('rev-parse','HEAD');assert sha=='a3a4f4a524a8eb39f14be7109dabfdd475c7d7e3';assert not git('status','--porcelain')
protected=json.loads(Path('/workspace/csv-confirm-workspace-corrected-final-delivery-verification.json').read_text())['protected_eighteen_refs'];protected['dev/csv-report-confirm-workspace-20261017']='83d716fcab99cffec99e07c867e6114c64e17f9b'
refs=subprocess.check_output(['git','-c','core.fsmonitor=false','ls-remote','origin',*[f'refs/heads/{b}' for b in protected]],text=True)
actual={line.split()[1].removeprefix('refs/heads/'):line.split()[0] for line in refs.splitlines()};assert actual==protected
assert git('merge-base',sha,protected['dev/csv-report-confirm-workspace-20261017'])==protected['dev/csv-report-confirm-workspace-20261017']
(out/'preflight.json').write_text(json.dumps(dict(sha=sha,branch=git('branch','--show-current'),protected_nineteen_refs=protected,actual_remote=actual,clean=True,sole_writer=True,default_network_git_read=True,capacity=subprocess.check_output(['df','-h','/workspace','/tmp'],text=True)),indent=2)+'\n')
files=subprocess.check_output(['git','ls-files','-z','src','tests','schemas','pyproject.toml']).decode().split('\0');files=sorted(f for f in files if f)
def hashes():return {f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files}
before=hashes();(out/'final-inputs-before.json').write_text(json.dumps(dict(sha=sha,files=before),indent=2)+'\n')
commands=[['/workspace/sim2act-venv/bin/ruff','check','src/sim2act/api.py','src/sim2act/contracts.py','src/sim2act/db.py','src/sim2act/goal_runs.py','src/sim2act/owner_acceptance.py','src/sim2act/ordinary_owner_review.py','tests/test_ordinary_owner_review.py','tests/test_ordinary_owner_ui.py'],['node','--check','src/sim2act/web/app.js'],['node','--check','src/sim2act/web/ordinary-owner.js'],['git','-c','core.fsmonitor=false','diff','--check']]
results=[]
for index,cmd in enumerate(commands):
 r=subprocess.run(cmd,capture_output=True,text=True);(out/f'final-static-{index}.log').write_text(r.stdout+r.stderr);results.append(dict(command=cmd,rc=r.returncode));assert not r.returncode
cases=['tests/test_ordinary_owner_review.py','tests/test_ordinary_owner_ui.py','tests/test_goal_card_runs.py::test_complete_saved_conditions_reach_normal_worker_and_new_receipts','tests/test_goal_card_run_ui.py::test_saved_goal_execution_ui','tests/test_natural_spec_owner_acceptance.py::test_exact_goal_result_explicit_human_declaration[False-pa]','tests/test_natural_spec_owner_acceptance.py::test_exact_goal_result_explicit_human_declaration[True-pb]','tests/test_owner_acceptance.py::test_owner_exact_explicit_decision[accept]','tests/test_ordinary_csv_report.py::test_visible_prospective_csv_report[workspace-unconfirmed]']
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q',*cases,'--basetemp=/tmp/ordinary-owner-author-final-a3a4f4a5-20261017','--junitxml='+str(out/'final-junit.xml'),'-p','ordinary_owner_evidence_plugin']
env={**os.environ,'NODE_PATH':str(root/'scripts/engineering-ci/node_modules'),'PYTHONPATH':str(out)+os.pathsep+str(root/'src'),'OWNER_EVIDENCE_OUTPUT':str(out)}
started=time.time()
with (out/'final-pytest.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
results.append(dict(command=cmd,rc=r.returncode,seconds=time.time()-started));after=hashes();(out/'final-inputs-after.json').write_text(json.dumps(dict(sha=sha,files=after),indent=2)+'\n');(out/'final-execution.json').write_text(json.dumps(dict(sha=sha,commands=results,source_test_schema_input_count=len(files),inputs_unchanged=before==after,worktree_clean=not git('status','--porcelain')),indent=2)+'\n');print(json.dumps(results[-1]));assert before==after;sys.exit(r.returncode)
