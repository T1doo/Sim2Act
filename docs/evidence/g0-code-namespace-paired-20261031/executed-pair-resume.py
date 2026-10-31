from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time
repo=Path('/workspace/Sim2Act');scratch=Path('/workspace/scratch');python=repo/'.venv/bin/python'
now=lambda:datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
profiler=scratch/'paired_cold_profile_20261031.py'
old_path=scratch/'paired-cold-profile-r2-20261031.json';old=json.loads(old_path.read_text());sha=old['profiler_sha256']
assert old['status']=='STOPPED_INVALID_PROFILE' and len(old['runs'])==1
base=old['runs'][0];assert base['returncode']==0 and base['source_match_after'] and base['profiler_match_after']
def verify(manifest):
 root=Path(manifest['export_root'])
 return all((root/n).is_file() and hashlib.sha256((root/n).read_bytes()).hexdigest()==s for n,s in manifest['files'].items())
def report_ok(prefix):
 files=list({p.resolve() for p in prefix.glob('*/paired-profile.json')});assert len(files)==1
 case=files[0].parent;p=json.loads(files[0].read_text());control=json.loads((case/'large-control-result.json').read_text());snap=json.loads((case/'snapshot-writer-timings.json').read_text())
 assert p['errors']==[] and p['open_timed_stack']==0 and p['profiler_sha256']==sha
 assert len(p['epochs'])==4 and all(e['closed'] and e['finished'] for e in p['epochs'])
 assert len(control['epochs'])==len(snap['records'])==2 and not control['cancel']
 assert len(p['selections'])==2 and [s['epoch'] for s in p['selections']]==[3,4]
 for a,b,c in zip(p['epochs'][-2:],control['epochs'],snap['records'],strict=True):
  assert a['seconds']==b['seconds'] and a['g0_seconds']==b['complete_g0_seconds']
  assert b['closed'] and b['finished_normally'] and c['outcome']=='COMMITTED'
 assert len((case/'mock-exchanges.jsonl').read_text().splitlines())==7
 return str(files[0])
base_report=report_ok(scratch/'paired-cold-r2-baseline_fb60-20261031')
assert hashlib.sha256(profiler.read_bytes()).hexdigest()==sha
assert subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
for tag in ('a','b'):assert verify(json.loads((scratch/('paired-source-20261031-'+tag+'-manifest.json')).read_text()))
path=scratch/'paired-cold-profile-r2-resumed-20261031.json';assert not path.exists()
pair=dict(status='RUNNING',started_utc=now(),original_pair=str(old_path),original_pair_sha256=hashlib.sha256(old_path.read_bytes()).hexdigest(),
 correction='Wrapper expected two total epochs but original fixture has two small prelude epochs and two large Cold epochs. All four closed normally; large control/snapshot records match final two. Original failed-wrapper record preserved; baseline not rerun.',
 profiler_sha256=sha,baseline_report=base_report,maximum_total_business_runs=2,baseline_reused_without_rerun=True,runs=[base])
path.write_text(json.dumps(pair,indent=2)+'\n')
mp=scratch/'paired-source-20261031-b-manifest.json';m=json.loads(mp.read_text());root=Path(m['export_root']);prefix=scratch/'paired-cold-r2-current_68c-20261031';assert not prefix.exists()
command=[str(python),'-m','pytest','-p','paired_cold_profile_20261031','-p','no:cacheprovider','--assert=plain','tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_control[complete]','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
env=os.environ.copy();env.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join((str(root/'src'),str(root/'tests'),str(scratch))))
r=dict(source_commit=m['source_commit'],label='current_68c',command=command,cwd=str(root),export_manifest_sha256=hashlib.sha256(mp.read_bytes()).hexdigest(),profiler_sha256=sha,hash_seed='0',python=str(python),pythonpath_order=['own_export/src','own_export/tests','common_scratch'],maximum_seconds=900,source_match_before=True,status='RUNNING',started_utc=now())
meta=Path(str(prefix)+'-run.json');assert not meta.exists();meta.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(event='START',label=r['label'],at=r['started_utc'],source=r['source_commit'])),flush=True)
started=time.monotonic()
with Path(str(prefix)+'.log').open('w') as log:
 child=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);r['pid']=child.pid;meta.write_text(json.dumps(r,indent=2)+'\n')
 try:r['returncode']=child.wait(timeout=900)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  r.update(returncode=child.returncode,timeout=True)
r.update(status='COMPLETED',ended_utc=now(),seconds=time.monotonic()-started,source_match_after=verify(m),profiler_match_after=hashlib.sha256(profiler.read_bytes()).hexdigest()==sha)
meta.write_text(json.dumps(r,indent=2)+'\n');pair['runs'].append(r);path.write_text(json.dumps(pair,indent=2)+'\n')
assert r['returncode']==0 and r['source_match_after'] and r['profiler_match_after']
pair.update(status='COMPLETED',ended_utc=now(),current_report=report_ok(prefix));path.write_text(json.dumps(pair,indent=2)+'\n');print(json.dumps(dict(event='END',exit=r['returncode'],seconds=r['seconds'],at=r['ended_utc'])),flush=True)
