from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,sys,time
repo=Path('/workspace/Sim2Act');scratch=Path('/workspace/scratch');python=repo/'.venv/bin/python';source=sys.argv[1]
assert len(source)==40 and all(c in '0123456789abcdef' for c in source)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==source
assert subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
prof=scratch/'owned_read_pair_profile_20261031.py';prof_sha=hashlib.sha256(prof.read_bytes()).hexdigest();diag=scratch/'use-effective-shape-20261031/_cold_graph_structure.cpython-312-x86_64-linux-gnu.so';diag_sha=hashlib.sha256(diag.read_bytes()).hexdigest()
now=lambda:datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
pair_path=scratch/('owned-read-final-pair-'+source[:8]+'-20261031.json');assert not pair_path.exists()
pair=dict(status='RUNNING',started_utc=now(),candidate_source=source,baseline_source='52f54c2750813058b11b6332248667de0c413acd',profiler_sha256=prof_sha,diagnostic_binary_sha256=diag_sha,maximum_runs=2,maximum_seconds_each=900,runs=[])
pair_path.write_text(json.dumps(pair,indent=2)+'\n')
manifest_path=scratch/'owned-read-baseline-52f54c27-20261031-manifest.json';manifest=json.loads(manifest_path.read_text());assert manifest['source_commit']=='52f54c2750813058b11b6332248667de0c413acd'
def export_ok():
 root=Path(manifest['export_root'])
 return all((root/n).is_file() and hashlib.sha256((root/n).read_bytes()).hexdigest()==sha for n,sha in manifest['files'].items())
for label,root,sha in [('baseline_52f54',Path(manifest['export_root']),manifest['source_commit']),('candidate_'+source[:8],repo,source)]:
 assert export_ok() and hashlib.sha256(prof.read_bytes()).hexdigest()==prof_sha and hashlib.sha256(diag.read_bytes()).hexdigest()==diag_sha
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==source and subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
 prefix=scratch/('owned-read-final-'+label+'-20261031');assert not prefix.exists()
 command=[str(python),'-m','pytest','-p','owned_read_pair_profile_20261031','-p','no:cacheprovider','--assert=plain','tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_control[complete]','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
 env=os.environ.copy();env.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join((str(root/'src'),str(root/'tests'),str(scratch))))
 r=dict(source_commit=sha,label=label,cwd=str(root),command=command,profiler_sha256=prof_sha,diagnostic_binary_sha256=diag_sha,hash_seed='0',max_seconds=900,started_utc=now(),status='RUNNING',source_match_before=True)
 meta=Path(str(prefix)+'-run.json');meta.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(event='START',label=label,source=sha,at=r['started_utc'])),flush=True);a=time.monotonic()
 with Path(str(prefix)+'.log').open('w') as log:
  child=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);r['pid']=child.pid;meta.write_text(json.dumps(r,indent=2)+'\n')
  try:r['returncode']=child.wait(timeout=900)
  except subprocess.TimeoutExpired:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
   r.update(returncode=child.returncode,timeout=True)
 finalhead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();dirty=subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)
 r.update(status='COMPLETED',seconds=time.monotonic()-a,ended_utc=now(),source_match_after=export_ok() and finalhead==source and dirty=='',profiler_match_after=hashlib.sha256(prof.read_bytes()).hexdigest()==prof_sha,diagnostic_match_after=hashlib.sha256(diag.read_bytes()).hexdigest()==diag_sha,final_source_commit=sha if label=='baseline_52f54' else finalhead,final_porcelain=dirty)
 meta.write_text(json.dumps(r,indent=2)+'\n');pair['runs'].append(r);pair_path.write_text(json.dumps(pair,indent=2)+'\n');print(json.dumps(dict(event='END',label=label,exit=r['returncode'],seconds=r['seconds'],at=r['ended_utc'])),flush=True)
 if r['returncode']!=0 or not r['source_match_after'] or not r['profiler_match_after'] or not r['diagnostic_match_after']:
  pair.update(status='STOPPED_AFTER_FAILURE',ended_utc=now());pair_path.write_text(json.dumps(pair,indent=2)+'\n');raise SystemExit(1)
 files={p.resolve() for p in prefix.glob('*/use-effective-profile.json')};assert len(files)==1;report=json.loads(files.pop().read_text())
 case=next(iter({p.resolve().parent for p in prefix.glob('*/use-effective-profile.json')}))
 control=json.loads((case/'large-control-result.json').read_text());snapshot=json.loads((case/'snapshot-writer-timings.json').read_text());proof=json.loads((case/'pb-controller-proof.json').read_text())
 valid=(len(control['epochs'])==len(snapshot['records'])==2 and all(e['outcome']=='COMMITTED' for e in snapshot['records']) and all(e['closed'] and e['finished_normally'] and e['run_id']==proof['cold'] for e in control['epochs']) and len(report['epochs'])==4 and all(e['seconds']==c['seconds'] and e['g0_seconds']==c['complete_g0_seconds'] for e,c in zip(report['epochs'][-2:],control['epochs'],strict=True)) and [e['epoch'] for e in report['selections']]==[3,4] and all(e['record']['route']=='OWNED' for e in report['selections']) and len((case/'mock-exchanges.jsonl').read_text().splitlines())==7 and report['runtime_module']==str(root/'src/sim2act/natural_spec_runtime.py') and report['profiler_sha256']==prof_sha and report['diagnostic_binary_sha256']==diag_sha)
 if report['errors'] or report['open_timed_stack'] or not valid or not all(e['closed'] and e['finished'] for e in report['epochs']):
  pair.update(status='STOPPED_INVALID_PROFILE',ended_utc=now(),errors=report['errors'],open_stack=report['open_timed_stack']);pair_path.write_text(json.dumps(pair,indent=2)+'\n');raise SystemExit(2)
pair.update(status='COMPLETED',ended_utc=now(),limits='One same-fixture fixed-order baseline52f54/current pair, identical passive observer including numeric-only capsule reads. Observer overhead included. FixedMock/test_onlySQLite, not a distribution/SLA/formal PG/live/Windows claim.')
pair_path.write_text(json.dumps(pair,indent=2)+'\n')
