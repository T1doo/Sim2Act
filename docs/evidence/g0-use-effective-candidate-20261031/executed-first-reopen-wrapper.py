from pathlib import Path
import subprocess,json,hashlib,datetime,time
repo=Path('/workspace/Sim2Act');scratch=Path('/workspace/scratch');source='e28680b3d14481c815c20a6628eedbf5e7a700c2'
prefix=scratch/'use-effective-candidate_e28680b3-20261031';metadata=json.loads(Path(str(prefix)+'-run.json').read_text())
assert metadata['status']=='COMPLETED' and metadata['returncode']==0 and metadata['final_source_commit']==metadata['source_commit']==source and metadata['final_porcelain']==''
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==source
assert subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)==''
cases={p.resolve().parent for p in prefix.glob('*/snapshot-writer-timings.json')};assert len(cases)==1;case=cases.pop()
output=Path(str(prefix)+'-first-fresh-reopen.json');record=Path(str(prefix)+'-first-fresh-reopen-command.json');assert not output.exists() and not record.exists()
checker=scratch/'check-g0-owned-release-reopen-20261031.py';command=[str(repo/'.venv/bin/python'),str(checker),str(case),str(output)]
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
r=dict(source_commit=source,command=command,cwd=str(repo),checker_sha256=hashlib.sha256(checker.read_bytes()).hexdigest(),started_utc=now(),status='RUNNING')
record.write_text(json.dumps(r,indent=2)+'\n');a=time.monotonic();child=subprocess.run(command,cwd=repo,capture_output=True,text=True,timeout=30)
r.update(status='COMPLETED',returncode=child.returncode,seconds=time.monotonic()-a,ended_utc=now(),stdout_sha256=hashlib.sha256(child.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(child.stderr.encode()).hexdigest())
record.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
assert child.returncode==0,(child.returncode,child.stdout,child.stderr)
print(output.read_text())
