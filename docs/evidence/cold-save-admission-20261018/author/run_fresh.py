"""One fresh serial four-node qualification, with closed raw bytes and passive spans."""
import ast,datetime,hashlib,json,os,selectors,subprocess,sys,time
from pathlib import Path
repo=Path('/workspace/Sim2Act');author=Path('/workspace/cold-save-admission-20261018')
out=author/'fresh-once';out.mkdir(exist_ok=False)
expected='fd96df814e8c0fb6db6651ce77eb484951240ecc'
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
assert git('status','--porcelain')==b''
head=git('rev-parse','HEAD').decode().strip();assert head==expected
paths=sorted(p for p in git('ls-files').decode().splitlines() if p.startswith(('src/','tests/')) or p in ('pyproject.toml','uv.lock'))
helpers=[Path(__file__),author/'offline_stages_guard.py']
for p in helpers:ast.parse(p.read_bytes(),filename=str(p))
(out/'runner.py').write_bytes(Path(__file__).read_bytes());(out/'offline_stages_guard.py').write_bytes(helpers[1].read_bytes())
def inputs(name):
 value={'head':head,'inputs':{p:{'bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in paths}}
 (out/name).write_text(json.dumps(value,indent=2)+'\n');return value
def helper_state(name):
 value={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in helpers}
 (out/name).write_text(json.dumps(value,indent=2)+'\n');return value
before=inputs('inputs-before.json');hb=helper_state('helpers-before.json')
selected=['test_fresh_actual_prefix_rejects_incomplete_mixed_or_changed_proof_without_writes','test_actual_pa_three_two_two_reaches_existing_results_and_pending_owner','test_known_accounting_cannot_accept_wrong_original_business_schema','test_original_controller_store_is_fixed_through_late_body_and_failure']
command=['timeout','--kill-after=15s','900s','/workspace/sim2act-venv/bin/python','-m','pytest','-vv','-s','-p','offline_stages_guard','--basetemp='+str(out/'actual-tmp'),'--junitxml='+str(out/'junit.xml'),*['tests/test_production_trial_stages.py::'+n for n in selected]]
record={'source_commit':head,'baseline':'f89f8f4431a63e22a9f067cd74e3bdd4051d84ea','command':command,'cwd':str(repo),'started_utc':datetime.datetime.now(datetime.UTC).isoformat(),'old_19_12_8_9_nodes_rerun':0,'real_provider_calls':0,'group':'one_fresh_serial_B_A_C_D','B_independent_of_Cold_SAVE':True,'no_failfast':True}
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
environment={k:v for k,v in os.environ.items() if not k.startswith(('SIM2ACT_','INTERN_'))}
environment.update(PYTHONPATH=str(author),STAGES_GUARD_PROOF=str(out/'offline-guard.json'))
start=time.monotonic();last_progress=start;last_marker='started';buffer=b''
with (out/'pytest.stdout').open('wb') as stdout,(out/'pytest.stderr').open('wb') as stderr:
 process=subprocess.Popen(command,cwd=repo,env=environment,stdout=subprocess.PIPE,stderr=stderr)
 selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ);eof=False
 while not eof:
  for key,_ in selector.select(timeout=1):
   raw=os.read(key.fd,65536)
   if not raw:eof=True;break
   stdout.write(raw);stdout.flush();buffer+=raw
   while b'\n' in buffer:
    line,buffer=buffer.split(b'\n',1)
    if line.startswith((b'OFFLINE_CAPTURE_ENTRY',b'tests/test_production_trial_stages.py::')):
     last_marker=line.decode('utf-8','replace');print(last_marker,flush=True)
  if time.monotonic()-last_progress>=45:
   print(json.dumps({'progress_seconds':round(time.monotonic()-start,1),'last_marker':last_marker,'active_single_command':True}),flush=True);last_progress=time.monotonic()
 selector.close();code=process.wait()
after=inputs('inputs-after.json');ha=helper_state('helpers-after.json')
record.update(exit_code=code,elapsed_seconds=time.monotonic()-start,ended_utc=datetime.datetime.now(datetime.UTC).isoformat(),input_count=len(paths),production_count=sum(p.startswith('src/') for p in paths),input_drift=before!=after,helper_drift=hb!=ha)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
for p in git('diff','--name-only',record['baseline'],'HEAD').decode().splitlines():
 dest=out/'frozen-source'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((repo/p).read_bytes())
print(json.dumps(record),flush=True)
assert not record['input_drift'] and not record['helper_drift']
raise SystemExit(code)
