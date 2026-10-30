import datetime,json,os,signal,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');source='9523d3e2bd5e6429c0a3744d0c2ec22e0a8abafc'
now=lambda:datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
cases=[('revoke','tests/test_cold_snapshot_full_flow.py::test_same_large_cold_conflict_cannot_settle_old_snapshot[revoke]')]
for name,node in cases:
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==source
 assert subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)==''
 prefix=Path('/workspace/scratch/cold-deadline-'+name+'-20261030')
 assert not prefix.exists() and not Path(str(prefix)+'-run.json').exists()
 command=[str(root/'.venv/bin/python'),'-m','pytest','--assert=plain',node,'-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
 result=dict(source_commit=source,command=command,max_seconds=900,started_utc=now(),status='RUNNING',classification='UNINSTRUMENTED_ORIGINAL_LARGE_COLD_REAL_CLOCK_FIXED_MOCK_SQLITE_WAL',case=name)
 meta=Path(str(prefix)+'-run.json');meta.write_text(json.dumps(result,indent=2)+'\n');started=time.monotonic()
 with open(str(prefix)+'.log','w') as out:
  p=subprocess.Popen(command,cwd=root,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
  result['pid']=p.pid;meta.write_text(json.dumps(result,indent=2)+'\n')
  try:result['returncode']=p.wait(timeout=900)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   result['returncode']=p.returncode;result['timeout']=True
 result.update(status='COMPLETED',seconds=time.monotonic()-started,ended_utc=now(),final_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),final_porcelain=subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True))
 meta.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
 if result['returncode']!=0:raise SystemExit(1)
