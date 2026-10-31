"""Single frozen-source save/reopen/writer-cancel acceptance; no old reruns."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
repo=Path('/workspace/Sim2Act');scratch=Path('/workspace/scratch')
source=sys.argv[1];assert len(source)==40 and all(c in '0123456789abcdef' for c in source)
python=repo/'.venv/bin/python';base=scratch/('cold-lifecycle-'+source[:8]+'-20261031')
meta=Path(str(base)+'-acceptance.json');assert not meta.exists()
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
prof=scratch/'owned_read_pair_profile_20261031.py';checker=scratch/'check-g0-owned-release-reopen-20261031.py'
identities={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (prof,checker)}
def frozen():
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==source
 assert subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in identities.items())
frozen()
result=dict(source_commit=source,status='RUNNING',started_utc=now(),identities=identities,
 classification='REAL_CLOCK_SYNTHETIC_FIXED_MOCK_TEST_SQLITE_NOT_PG_LIVE_WINDOWS',
 limits='One current-source invocation for two saves, first new-process reopen, then one actual-G1-writer cancellation. Same fixture/observer as earlier fresh d6/cda pair; this is a later candidate, not an adjacent randomized pair.',steps=[])
def save():meta.write_text(json.dumps(result,indent=2)+'\n')
save()
def pytest_once(label,test):
 frozen();prefix=Path(str(base)+'-'+label);assert not prefix.exists()
 command=[str(python),'-m','pytest','-p','owned_read_pair_profile_20261031','-p','no:cacheprovider','--assert=plain',test,'-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
 env=os.environ.copy();env.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join((str(repo/'src'),str(repo/'tests'),str(scratch))))
 r=dict(source_commit=source,label=label,status='RUNNING',started_utc=now(),command=command,max_seconds=900)
 path=Path(str(prefix)+'-run.json');path.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(event='START',**r)),flush=True);start=time.monotonic()
 with Path(str(prefix)+'.log').open('w') as log:
  p=subprocess.Popen(command,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  r['pid']=p.pid;path.write_text(json.dumps(r,indent=2)+'\n')
  try:r['returncode']=p.wait(timeout=900)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   r.update(returncode=p.returncode,timeout=True)
 r.update(status='COMPLETED',ended_utc=now(),seconds=time.monotonic()-start,
  final_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
  final_porcelain=subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True))
 path.write_text(json.dumps(r,indent=2)+'\n');result['steps'].append(r);save()
 print(json.dumps(dict(event='END',**r)),flush=True)
 frozen();assert r['returncode']==0, 'Keep failed original output; no further run'
 cases={p.resolve().parent for p in prefix.glob('*/snapshot-writer-timings.json')};assert len(cases)==1
 return prefix,cases.pop()
try:
 prefix,case=pytest_once('save','tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_control[complete]')
 # First new interpreter/database observation, before archival or SQL probes.
 out=Path(str(prefix)+'-first-reopen.json');record=Path(str(prefix)+'-first-reopen-command.json')
 assert not out.exists() and not record.exists();frozen()
 command=[str(python),str(checker),str(case),str(out)]
 r=dict(label='first-reopen',source_commit=source,command=command,started_utc=now(),status='RUNNING');record.write_text(json.dumps(r,indent=2)+'\n')
 start=time.monotonic();p=subprocess.run(command,cwd=repo,capture_output=True,text=True,timeout=30)
 r.update(status='COMPLETED',returncode=p.returncode,ended_utc=now(),seconds=time.monotonic()-start,stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest())
 record.write_text(json.dumps(r,indent=2)+'\n');result['steps'].append(r);save();print(json.dumps(dict(event='REOPEN',**r)),flush=True)
 assert p.returncode==0,(p.returncode,p.stdout,p.stderr);frozen()
 profile=json.loads((case/'use-effective-profile.json').read_text());timings=json.loads((case/'snapshot-writer-timings.json').read_text())
 assert not profile['errors'] and profile['open_timed_stack']==0 and len(timings['records'])==2
 assert all(r['outcome']=='COMMITTED' for r in timings['records'])
 assert len((case/'mock-exchanges.jsonl').read_text().splitlines())==7
 result['save_records']=timings['records'];save()
 prefix,case=pytest_once('cancel','tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_cancel_during_actual_g1_writer')
 timings=json.loads((case/'snapshot-writer-timings.json').read_text());control=json.loads((case/'large-control-result.json').read_text())
 assert len(timings['records'])==1 and timings['records'][0]['outcome']=='ROLLED_BACK'
 assert control['cancel_phase']=='G1' and control['writer_lock_probe']['no_mutation'] is True
 result['cancel_records']=timings['records'];frozen()
 recovery=scratch/'finish-cold-cancel-after-natural-expiry-20261031.py'
 recovery_root=Path(str(base)+'-default-recovery')
 command=[str(python),str(recovery),str(case/'fixture.db'),str(recovery_root),source,control['target_run']]
 r=dict(label='natural-expiry-default-recovery',source_commit=source,command=command,script_sha256=hashlib.sha256(recovery.read_bytes()).hexdigest(),started_utc=now(),status='RUNNING');start=time.monotonic()
 print(json.dumps(dict(event='START_RECOVERY',**r)),flush=True)
 child=subprocess.run(command,cwd=repo,capture_output=True,text=True,timeout=150)
 r.update(status='COMPLETED',returncode=child.returncode,ended_utc=now(),seconds=time.monotonic()-start,stdout_sha256=hashlib.sha256(child.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(child.stderr.encode()).hexdigest())
 result['steps'].append(r);save();print(json.dumps(dict(event='END_RECOVERY',**r)),flush=True)
 assert child.returncode==0,(child.returncode,child.stdout,child.stderr)
 result['default_recovery']=json.loads((recovery_root/'default-recovery.json').read_text());frozen()
 result.update(status='COMPLETED',ended_utc=now());save();print(json.dumps(result,indent=2))
except BaseException as e:
 result.update(status='STOPPED_AFTER_FAILURE',ended_utc=now(),error_type=type(e).__name__);save();raise
