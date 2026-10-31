import datetime,json,os,signal,subprocess,time,sys
from pathlib import Path
root=Path('/workspace/Sim2Act');source=sys.argv[1];prefix=Path('/workspace/scratch/owned-read-pre-final-large-cancel-'+source[:8]+'-20261031')
now=lambda:datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==source
assert subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)==''
assert not prefix.exists()
command=[str(root/'.venv/bin/python'),'-m','pytest','-p','owned_read_pair_profile_20261031','-p','no:cacheprovider','--assert=plain','tests/test_cold_snapshot_full_flow.py::test_same_large_cold_snapshot_cancel_during_actual_g1_writer','-q','--basetemp='+str(prefix),'--junitxml='+str(prefix)+'.xml']
env=os.environ.copy();env['PYTHONHASHSEED']='0';env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']='/workspace/scratch'+os.pathsep+env.get('PYTHONPATH','')
result=dict(source_commit=source,command=command,max_seconds=900,started_utc=now(),status='RUNNING',classification='REAL_CLOCK_FIXED_MOCK_FILE_SQLITE_WAL_COMPLETE_EFFECTIVE_CANDIDATE_OWNER_ACTUAL_G1_CANCEL_FIXED_MOCK_NOT_LIVE')
meta=Path(str(prefix)+'-run.json');meta.write_text(json.dumps(result,indent=2)+'\n');start=time.monotonic()
with open(str(prefix)+'.log','w') as out:
 p=subprocess.Popen(command,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True);result['pid']=p.pid;meta.write_text(json.dumps(result,indent=2)+'\n')
 try:result['returncode']=p.wait(timeout=900)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  result.update(returncode=p.returncode,timeout=True)
result.update(status='COMPLETED',seconds=time.monotonic()-start,ended_utc=now(),final_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),final_porcelain=subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True))
meta.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(result['returncode'])
