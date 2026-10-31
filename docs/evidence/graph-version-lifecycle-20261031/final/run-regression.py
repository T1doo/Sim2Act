import datetime,hashlib,json,os,signal,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');sha='4d0b16f2cce1d83363106aa00c05bc969e39ac23';prefix=Path('/workspace/scratch/graph-version-regression-4d0b16f2-20261031');meta=Path(str(prefix)+'-run.json')
assert not prefix.exists() and not meta.exists()
def frozen():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==sha and subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)==''
assert frozen();now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
command=[str(root/'.venv/bin/python'),'-m','pytest','-p','no:cacheprovider','--assert=plain','tests/test_cold_graph_versions.py','tests/test_cold_graph_structure.py','tests/test_cold_frontier_structure.py','tests/test_cold_accounted_native.py','tests/test_cold_accounted_receipts.py','tests/test_cold_accounted_component.py','tests/test_cold_extract_parse.py','tests/test_settlement_preparation_lifetime.py','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
r=dict(source_commit=sha,command=command,started_utc=now(),status='RUNNING',max_seconds=480,git_src_tree=subprocess.check_output(['git','rev-parse',sha+':src'],cwd=root,text=True).strip(),native_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'src/sim2act').glob('*.so'))},classification='GRAPH_VERSION_RELATED_REGRESSION_NO_MODEL_IO_NOT_PERFORMANCE')
meta.write_text(json.dumps(r,indent=2)+'\n');a=time.monotonic()
with Path(str(prefix)+'.log').open('w') as log:
 child=subprocess.Popen(command,cwd=root,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT,start_new_session=True);r['pid']=child.pid;meta.write_text(json.dumps(r,indent=2)+'\n')
 try:r['returncode']=child.wait(timeout=480)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  r.update(returncode=child.returncode,timed_out=True)
r.update(status='COMPLETED',ended_utc=now(),wall_seconds=time.monotonic()-a,source_unchanged=frozen())
meta.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
raise SystemExit(r['returncode'] if r['source_unchanged'] else 2)
