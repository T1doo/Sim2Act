import datetime,json,os,signal,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');prefix=Path('/workspace/scratch/cold-deadline-profile-filtered-20261030')
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
command=['/usr/bin/strace','--seccomp-bpf','-f','-qq','-ttt','-T','-yy','-e','trace=fsync,fdatasync','-o',str(prefix)+'.trace',str(root/'.venv/bin/python'),'-m','pytest','--assert=plain','tests/test_cold_snapshot_profile.py::test_original_large_cold_scoped_profile','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
now=lambda:datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
result=dict(source_commit=sha,command=command,max_seconds=900,started_utc=now(),status='RUNNING',classification='PASSIVE_NATIVE_SQL_TIMING_AND_FILTERED_FSYNC_TRACE_ORIGINAL_LARGE_FIXED_MOCK_SQLITE_WAL')
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
meta.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['returncode']==0 else 1)
