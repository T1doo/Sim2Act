import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-trial-source-20261018/run-1')
out.mkdir(exist_ok=False)
old_guard = Path('/workspace/production-trial-sender-20261018/run-1/offline_sender_guard.py').read_text()
(out/'offline_source_guard.py').write_text(old_guard.replace('SENDER_GUARD_PROOF','SOURCE_GUARD_PROOF').replace('Uninstalled sender qualification','Uninstalled source qualification'))

def git(*args):
    return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)

assert git('status','--porcelain') == b''
assert git('rev-parse','HEAD').decode().strip() == 'ab838215af13c04281bbad441fd75b9a97839890'
prior = json.loads(Path('/workspace/production-trial-sender-20261018/run-1/inputs-after.json').read_text())['inputs']
paths = sorted([*prior,'src/sim2act/production_trial_source.py','tests/test_production_trial_source.py'])
assert len(paths)==707
changed = [name for name,item in prior.items() if hashlib.sha256((repo/name).read_bytes()).hexdigest()!=item['sha256']]
assert changed == ['src/sim2act/production_trial_sender.py']

def inputs(name):
    value = dict(head=git('rev-parse','HEAD').decode().strip(),inputs={name:dict(bytes=(repo/name).stat().st_size,sha256=hashlib.sha256((repo/name).read_bytes()).hexdigest()) for name in paths})
    (out/name).write_text(json.dumps(value,indent=2)+'\n')
    return value

helpers = dict(runner=Path(__file__),guard=out/'offline_source_guard.py')
def helper_state(name):
    value = {name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for name,p in helpers.items()}
    (out/name).write_text(json.dumps(value,indent=2)+'\n')
    return value

before = inputs('inputs-before.json')
hbefore = helper_state('helpers-before.json')
command = ['timeout','--kill-after=15s','240s','/workspace/sim2act-venv/bin/python','-m','pytest','-vv','-s','-p','offline_source_guard','--basetemp='+str(out/'actual-tmp'),'--junitxml='+str(out/'junit.xml'),'tests/test_production_trial_source.py']
record = dict(source_commit=before['head'],baseline='9df8a2ecca3e2e9905200398aa7c7a4d53b891a0',command=command,cwd=str(repo),started_utc=datetime.datetime.now(datetime.UTC).isoformat(),changed_baseline_inputs=changed,unchanged_baseline_inputs=704,unchanged_baseline_production=136,old_19_12_8_nodes_rerun=0)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
environment = {key:value for key,value in os.environ.items() if not key.startswith(('SIM2ACT_','INTERN_'))}
environment.update(PYTHONPATH=str(out),SOURCE_GUARD_PROOF=str(out/'offline-guard.json'))
start = time.monotonic()
with (out/'pytest.stdout').open('wb') as stdout,(out/'pytest.stderr').open('wb') as stderr:
    result = subprocess.run(command,cwd=repo,env=environment,stdout=stdout,stderr=stderr)
after = inputs('inputs-after.json')
hafter = helper_state('helpers-after.json')
record.update(exit_code=result.returncode,elapsed_seconds=time.monotonic()-start,ended_utc=datetime.datetime.now(datetime.UTC).isoformat(),input_count=len(paths),production_count=sum(name.startswith('src/') for name in paths),input_drift=before!=after,helper_drift=hbefore!=hafter)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
for name in ('src/sim2act/production_trial_source.py','src/sim2act/production_trial_sender.py','tests/test_production_trial_source.py'):
    target = out/'frozen-source'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes((repo/name).read_bytes())
(out/'runner.py').write_bytes(Path(__file__).read_bytes())
assert not record['input_drift'] and not record['helper_drift']
print(json.dumps(record))
raise SystemExit(result.returncode)
