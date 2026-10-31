from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time
repo=Path('/workspace/Sim2Act');s=Path('/workspace/scratch');source='8c794051f2be2fee9ec07b99f58f7f2959f3247e';prefix=s/'expected-post-actual-shadow-8c794051-20261031';assert not prefix.exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==source and subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
files={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo/'tools/expected_post_prototype').glob('*') if p.is_file()}
for name,sha in files.items():assert hashlib.sha256(subprocess.check_output(['git','show',source+':'+name],cwd=repo)).hexdigest()==sha
cmd=[str(repo/'.venv/bin/python'),'-m','pytest','tools/expected_post_prototype/probe_actual_g1.py','-q','-p','no:cacheprovider','--assert=plain','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml'];env=os.environ.copy();env.update(PYTHONPATH=str(repo)+os.pathsep+str(repo/'tests'),PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0');now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
r=dict(source_commit=source,application_source='c6a42c783fd92818654b02e5fb469675877c632a',tool_files=files,command=cmd,max_seconds=240,started_utc=now(),status='RUNNING',classification='SYNTHETIC_ONE_COLD_VIRTUAL_TIME_DATA_SHADOW_ONLY');meta=Path(str(prefix)+'-run.json');meta.write_text(json.dumps(r,indent=2)+'\n');a=time.monotonic()
with Path(str(prefix)+'.log').open('w') as log:
 child=subprocess.Popen(cmd,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);r['pid']=child.pid;meta.write_text(json.dumps(r,indent=2)+'\n')
 try:r['returncode']=child.wait(timeout=240)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGTERM)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
  r.update(returncode=child.returncode,timeout=True)
r.update(status='COMPLETED',seconds=time.monotonic()-a,ended_utc=now(),source_unchanged=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==source and subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)=='',files_unchanged=all(hashlib.sha256((repo/n).read_bytes()).hexdigest()==sha for n,sha in files.items()));meta.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);raise SystemExit(0 if r['returncode']==0 and r['source_unchanged'] and r['files_unchanged'] else 1)
