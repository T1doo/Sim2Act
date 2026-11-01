"""Exactly one frozen, bounded business run; real clock, unchanged observer."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
root=Path('/workspace/Sim2Act');source,kind=sys.argv[1:]
targets={
 'original30':('scripts/diagnose_ordinary_thirty.py',600,'ORIGINAL30_REAL_CLOCK_FIXED_MOCK_NO_CLOCK_OR_BUDGET_CHANGE'),
 'signed120':('tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_control[complete]',900,'EXPLICIT_SIGNED120_TWO_COLD_REAL_CLOCK_NOT_ORDINARY30'),
 'cancel':('tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_cancel_during_actual_g1_writer',600,'EXPLICIT_SIGNED120_REAL_G1_WRITER_CANCEL_ROLLBACK_NOT_ORDINARY30'),
}
target,limit,classification=targets[kind]
prefix=Path('/workspace/scratch/graph-original-edge-'+kind+'-'+source[:8]+'-20261101')
metadata=Path(str(prefix)+'-run.json')
assert not prefix.exists() and not metadata.exists()
def frozen():
 return (subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==source
  and not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip())
assert frozen()
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
observer=Path('/workspace/scratch/graph_version_real_clock_profile.py' if kind=='original30' else '/workspace/scratch/graph_version_real_clock_profile_detailed.py')
assert hashlib.sha256(observer.read_bytes()).hexdigest()==('63460fa737336465214b4048650eb19c7b897a4c60bb26de378e40f073d60a96' if kind=='original30' else '4e8e38f2f87dc22c24ba0a88f484f79f975b8a101b605c789f3f89afed98c3b9')
command=[str(root/'.venv/bin/python'),'-m','pytest','-p','no:cacheprovider','--assert=plain',target,
 '-p',observer.stem,'-p','graph_dictionary_counts','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
record=dict(source_commit=source,classification=classification,command=command,
 observer_sha256=hashlib.sha256(observer.read_bytes()).hexdigest(),started_utc=now(),status='RUNNING',
 max_seconds=limit,git_src_tree=subprocess.check_output(['git','rev-parse',source+':src'],cwd=root,text=True).strip(),
 native_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'src/sim2act').glob('*.so'))})
metadata.write_text(json.dumps(record,indent=2)+'\n')
begin=time.monotonic()
env=os.environ.copy()|{'SIM2ACT_DIAGNOSTIC_SOURCE':source}
with Path(str(prefix)+'.log').open('w') as log:
 child=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 record['pid']=child.pid;metadata.write_text(json.dumps(record,indent=2)+'\n')
 try:record['returncode']=child.wait(timeout=limit)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  record.update(returncode=child.returncode,timed_out=True)
record.update(status='COMPLETED',ended_utc=now(),wall_seconds=time.monotonic()-begin,source_unchanged=frozen())
metadata.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
raise SystemExit(record['returncode'] if record['source_unchanged'] else 2)
