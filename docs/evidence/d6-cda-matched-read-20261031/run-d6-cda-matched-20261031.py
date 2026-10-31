from pathlib import Path
import subprocess,os,sys,json,datetime,time,hashlib,signal
repo=Path('/workspace/Sim2Act');s=Path('/workspace/scratch');python=repo/'.venv/bin/python';keeper='2082be487c62cf7529f5cbb4bedfdb17f934a62f';out=s/'d6-cda-fresh-matched-20261031.json';assert not out.exists()
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
prof=s/'owned_read_pair_profile_20261031.py';profsha=hashlib.sha256(prof.read_bytes()).hexdigest();diag=s/'use-effective-shape-20261031/_cold_graph_structure.cpython-312-x86_64-linux-gnu.so';diagsha=hashlib.sha256(diag.read_bytes()).hexdigest()
manifests=[json.loads((s/('matched-'+name+'-source-20261031-manifest.json')).read_text()) for name in ('d6d07','cda0')]
def valid_exports():return all(all((Path(m['export_root'])/n).is_file() and hashlib.sha256((Path(m['export_root'])/n).read_bytes()).hexdigest()==v for n,v in m['files'].items()) for m in manifests)
def frozen():return subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==keeper and subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)=='' and valid_exports() and hashlib.sha256(prof.read_bytes()).hexdigest()==profsha and hashlib.sha256(diag.read_bytes()).hexdigest()==diagsha
assert frozen()
r=dict(status='RUNNING',keeper_head=keeper,baseline_source=manifests[0]['source_commit'],candidate_source=manifests[1]['source_commit'],started_utc=now(),profiler_sha256=profsha,diagnostic_sha256=diagsha,maximum_runs=2,maximum_seconds_each=900,runs=[]);out.write_text(json.dumps(r,indent=2)+'\n')
for label,m in zip(('d6d07','cda0'),manifests,strict=True):
 assert frozen();root=Path(m['export_root']);prefix=s/('d6-cda-fresh-'+label+'-20261031');assert not prefix.exists()
 command=[str(python),'-m','pytest','-p','owned_read_pair_profile_20261031','-p','no:cacheprovider','--assert=plain','tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_control[complete]','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
 env=os.environ.copy();env.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join((str(root/'src'),str(root/'tests'),str(s))))
 step=dict(label=label,source_commit=m['source_commit'],root=str(root),command=command,status='RUNNING',started_utc=now(),profiler_sha256=profsha,diagnostic_sha256=diagsha,maximum_seconds=900)
 meta=Path(str(prefix)+'-run.json');meta.write_text(json.dumps(step,indent=2)+'\n');print(json.dumps(dict(event='START',label=label,source=m['source_commit'],at=step['started_utc'])),flush=True);a=time.monotonic()
 with Path(str(prefix)+'.log').open('w') as log:
  child=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);step['pid']=child.pid;meta.write_text(json.dumps(step,indent=2)+'\n')
  try:step['returncode']=child.wait(timeout=900)
  except subprocess.TimeoutExpired:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
   step.update(returncode=child.returncode,timeout=True)
 step.update(status='COMPLETED',ended_utc=now(),seconds=time.monotonic()-a,source_unchanged=frozen());meta.write_text(json.dumps(step,indent=2)+'\n');r['runs'].append(step);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(event='END',label=label,exit=step['returncode'],seconds=step['seconds'],at=step['ended_utc'])),flush=True)
 if step['returncode'] or not step['source_unchanged']:
  r.update(status='STOPPED_AFTER_FAILURE',ended_utc=now());out.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(1)
 cases={p.resolve().parent for p in prefix.glob('*/use-effective-profile.json')};assert len(cases)==1;case=cases.pop();p=json.loads((case/'use-effective-profile.json').read_text());t=json.loads((case/'snapshot-writer-timings.json').read_text())
 assert not p['errors'] and p['open_timed_stack']==0 and p['runtime_module']==str(root/'src/sim2act/natural_spec_runtime.py') and p['profiler_sha256']==profsha
 assert len(t['records'])==2 and all(x['outcome']=='COMMITTED' for x in t['records']) and len((case/'mock-exchanges.jsonl').read_text().splitlines())==7
 step['records']=t['records'];step['case_path']=str(case);meta.write_text(json.dumps(step,indent=2)+'\n');out.write_text(json.dumps(r,indent=2)+'\n')
r.update(status='COMPLETED',ended_utc=now(),limits='Fresh exact-source d6/cda sequential fixed-order comparison, same original synthetic fixture/input recipe/hashseed/interpreter/native binaries/observer; real UUIDs/clocks differ. All observer overhead retained. Each twoCold saves7FixedMock,0real. No SLA/stable causality/livePG/Windows claim.');out.write_text(json.dumps(r,indent=2)+'\n')
