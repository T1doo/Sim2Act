import datetime,hashlib,json,os,signal,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');sha='35eaa941f544ca016ddeeefb839178d316fc1c6b';prefix=Path('/workspace/scratch/graph-resolve-original30-35eaa941-20261101');meta=Path(str(prefix)+'-run.json')
assert not prefix.exists() and not meta.exists()
def frozen():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==sha and subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)==''
assert frozen();now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
command=[str(root/'.venv/bin/python'),'-m','pytest','-p','no:cacheprovider','--assert=plain','scripts/diagnose_ordinary_thirty.py','-p','graph_version_real_clock_profile','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
r=dict(observer_sha256=hashlib.sha256(Path('/workspace/scratch/graph_version_real_clock_profile.py').read_bytes()).hexdigest(),source_commit=sha,command=command,started_utc=now(),status='RUNNING',max_seconds=480,git_src_tree=subprocess.check_output(['git','rev-parse',sha+':src'],cwd=root,text=True).strip(),native_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'src/sim2act').glob('*.so'))},classification='ORIGINAL30_REAL_CLOCK_WITH_PASSIVE_OBSERVER_FIXED_MOCK_NO_CLOCK_OR_BUDGET_CHANGE')
meta.write_text(json.dumps(r,indent=2)+'\n');a=time.monotonic()
with Path(str(prefix)+'.log').open('w') as log:
 child=subprocess.Popen(command,cwd=root,env=os.environ.copy()|{'SIM2ACT_DIAGNOSTIC_SOURCE':sha},stdout=log,stderr=subprocess.STDOUT,start_new_session=True);r['pid']=child.pid;meta.write_text(json.dumps(r,indent=2)+'\n')
 try:r['returncode']=child.wait(timeout=480)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  r.update(returncode=child.returncode,timed_out=True)
r.update(status='COMPLETED',ended_utc=now(),wall_seconds=time.monotonic()-a,source_unchanged=frozen())
meta.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
raise SystemExit(r['returncode'] if r['source_unchanged'] else 2)
