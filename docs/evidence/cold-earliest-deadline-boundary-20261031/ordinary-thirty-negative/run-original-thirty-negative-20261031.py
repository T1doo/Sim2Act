import datetime,hashlib,json,os,signal,subprocess,time
from pathlib import Path
repo=Path('/workspace/Sim2Act');s=Path('/workspace/scratch');export=s/'deadline-matched-candidate-20261031'
manifest=json.loads(Path(str(export)+'-manifest.json').read_text());source=manifest['source_commit']
assert source=='2ad3227621b48793a4d03747463b33207139147e'
assert all(hashlib.sha256((export/n).read_bytes()).hexdigest()==v for n,v in manifest['files'].items())
prefix=s/'ordinary-thirty-negative-2ad32276-20261031';assert not prefix.exists()
test=s/'test_original_thirty_large_20261031.py';prof=s/'owned_read_pair_profile_20261031.py'
command=[str(repo/'.venv/bin/python'),'-m','pytest','-p','owned_read_pair_profile_20261031','-p','no:cacheprovider','--assert=plain',str(test),'-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
env={**os.environ,'PYTHONHASHSEED':'0','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':os.pathsep.join((str(export/'src'),str(export/'tests'),str(s)))}
meta=Path(str(prefix)+'-run.json');r={'source_commit':source,'root':str(export),'command':command,'status':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'maximum_seconds':900,'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'observer_sha256':hashlib.sha256(prof.read_bytes()).hexdigest(),'scope':'Single old-30 contract input negative, same original controller/helper source restored before app calls; no clock/authorization replacement, no retry','root_has_only_unrelated_documentation_changes':True}
meta.write_text(json.dumps(r,indent=2)+'\n');a=time.monotonic()
with Path(str(prefix)+'.log').open('w') as log:
 p=subprocess.Popen(command,cwd=export,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 r['pid']=p.pid;meta.write_text(json.dumps(r,indent=2)+'\n')
 try:r['returncode']=p.wait(timeout=900)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  r.update(returncode=p.returncode,timeout=True)
r.update(status='COMPLETED' if r['returncode']==0 else 'FAILED_NO_AUTOMATIC_RETRY',seconds=time.monotonic()-a,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_unchanged=all(hashlib.sha256((export/n).read_bytes()).hexdigest()==v for n,v in manifest['files'].items()))
meta.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(r['returncode'])
