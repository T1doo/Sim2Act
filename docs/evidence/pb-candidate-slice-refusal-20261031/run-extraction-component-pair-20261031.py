from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
s=Path('/workspace/scratch');repo=Path('/workspace/Sim2Act');python=repo/'.venv/bin/python';now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
m=json.loads((s/'deadline-matched-candidate-20261031-manifest.json').read_text());prof=s/'extraction_component_profile_20261031.py';profsha=hashlib.sha256(prof.read_bytes()).hexdigest()
changed=subprocess.check_output(['git','diff','--name-only'],cwd=repo,text=True).splitlines();snapshot={n:hashlib.sha256((repo/n).read_bytes()).hexdigest() for n in changed}
out=s/'extraction-component-pair-20261031.json';assert not out.exists()
pair=dict(status='RUNNING',started_utc=now(),baseline_source=m['source_commit'],candidate_parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),candidate_files=snapshot,profiler_sha256=profsha,max_seconds_each=120,maximum_runs=2,runs=[]);out.write_text(json.dumps(pair,indent=2)+'\n')
for label,root in [('baseline_2ad',Path(m['export_root'])),('candidate_working',repo)]:
 assert all(hashlib.sha256((Path(m['export_root'])/n).read_bytes()).hexdigest()==sha for n,sha in m['files'].items())
 assert all(hashlib.sha256((repo/n).read_bytes()).hexdigest()==sha for n,sha in snapshot.items())
 prefix=s/('extraction-component-'+label+'-20261031');assert not prefix.exists()
 command=[str(python),'-m','pytest','-p','extraction_component_profile_20261031','-p','no:cacheprovider','--assert=plain','tests/test_cold_binding_graph_integration.py::test_plain_pb_first_binding_producer_equals_public_complete_ancestry','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
 env=os.environ.copy();env.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join((str(root/'src'),str(root/'tests'),str(s))))
 r=dict(label=label,cwd=str(root),command=command,started_utc=now(),status='RUNNING');print(json.dumps(dict(event='START',label=label,at=r['started_utc'])),flush=True);a=time.monotonic()
 with Path(str(prefix)+'.log').open('w') as log:
  try:p=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120);r['returncode']=p.returncode
  except subprocess.TimeoutExpired:r.update(returncode=None,timeout=True)
 r.update(status='COMPLETED',seconds=time.monotonic()-a,ended_utc=now());pair['runs'].append(r);out.write_text(json.dumps(pair,indent=2)+'\n');print(json.dumps(r),flush=True)
 if r['returncode']!=0:pair.update(status='STOPPED_AFTER_FAILURE',ended_utc=now());out.write_text(json.dumps(pair,indent=2)+'\n');raise SystemExit(1)
 files={p.resolve() for p in prefix.glob('*/extraction-component-profile.json')};assert len(files)==1;profile=json.loads(files.pop().read_text());assert profile['errors']==[] and profile['profiler_sha256']==profsha;r['profile']=profile
 assert all(hashlib.sha256((repo/n).read_bytes()).hexdigest()==sha for n,sha in snapshot.items()) and hashlib.sha256(prof.read_bytes()).hexdigest()==profsha
pair.update(status='COMPLETED',ended_utc=now());out.write_text(json.dumps(pair,indent=2)+'\n')
