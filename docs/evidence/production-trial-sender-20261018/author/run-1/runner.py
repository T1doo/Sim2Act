import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
repo=Path('/workspace/Sim2Act');out=Path('/workspace/production-trial-sender-20261018/run-1')
assert not (out/'execution.json').exists()
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
assert git('status','--porcelain')==b''
prior=json.loads(Path('/workspace/production-trial-journal-20261018/run-1/inputs-after.json').read_text())['inputs']
paths=sorted([*prior,'src/sim2act/production_trial_sender.py','tests/test_production_trial_sender.py'])
assert len(paths)==705
changed=[name for name,e in prior.items() if hashlib.sha256((repo/name).read_bytes()).hexdigest()!=e['sha256']]
assert changed==['src/sim2act/production_trial_journal.py']
def inputs(name):
 value=dict(head=git('rev-parse','HEAD').decode().strip(),inputs={p:dict(bytes=(repo/p).stat().st_size,sha256=hashlib.sha256((repo/p).read_bytes()).hexdigest()) for p in paths})
 (out/name).write_text(json.dumps(value,indent=2)+'\n');return value
before=inputs('inputs-before.json')
helpers={'runner':Path(__file__),'guard':out/'offline_sender_guard.py'}
def helper_state(name):
 value={k:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in helpers.items()}
 (out/name).write_text(json.dumps(value,indent=2)+'\n');return value
hbefore=helper_state('helpers-before.json')
cmd=['timeout','--kill-after=15s','240s','/workspace/sim2act-venv/bin/python','-m','pytest','-vv','-s','-p','offline_sender_guard','--basetemp='+str(out/'actual-tmp'),'--junitxml='+str(out/'junit.xml'),'tests/test_production_trial_sender.py']
record=dict(source_commit=before['head'],command=cmd,cwd=str(repo),started_utc=datetime.datetime.now(datetime.UTC).isoformat(),unchanged_baseline_inputs=702,unchanged_baseline_production=135,changed_baseline_inputs=changed,old_19_and_12_nodes_rerun=0)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
environment={k:v for k,v in os.environ.items() if not k.startswith(('SIM2ACT_','INTERN_'))}
environment.update(PYTHONPATH=str(out),SENDER_GUARD_PROOF=str(out/'offline-guard.json'))
start=time.monotonic()
with (out/'pytest.stdout').open('wb') as stdout,(out/'pytest.stderr').open('wb') as stderr:
 result=subprocess.run(cmd,cwd=repo,env=environment,stdout=stdout,stderr=stderr)
after=inputs('inputs-after.json');hafter=helper_state('helpers-after.json')
record.update(exit_code=result.returncode,elapsed_seconds=time.monotonic()-start,ended_utc=datetime.datetime.now(datetime.UTC).isoformat(),input_count=len(paths),production_count=sum(p.startswith('src/') for p in paths),input_drift=before!=after,helper_drift=hbefore!=hafter)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
for name in ('src/sim2act/production_trial_journal.py','src/sim2act/production_trial_sender.py','tests/test_production_trial_sender.py'):
 target=out/'frozen-source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((repo/name).read_bytes())
(out/'runner.py').write_bytes(Path(__file__).read_bytes())
assert not record['input_drift'] and not record['helper_drift']
print(json.dumps(record));raise SystemExit(result.returncode)
