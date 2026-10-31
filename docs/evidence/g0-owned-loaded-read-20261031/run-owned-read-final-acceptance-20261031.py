from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
s=Path('/workspace/scratch');repo=Path('/workspace/Sim2Act');python=repo/'.venv/bin/python';source=sys.argv[1]
assert len(source)==40 and all(c in '0123456789abcdef' for c in source)
meta=s/('owned-read-final-acceptance-'+source[:8]+'-20261031.json');assert not meta.exists()
scripts=['run-owned-read-final-pair-20261031.py','run-owned-read-final-first-reopen-20261031.py','compare-owned-read-final-pair-20261031.py','run-owned-read-final-large-cancel-20261031.py']
identity={n:hashlib.sha256((s/n).read_bytes()).hexdigest() for n in scripts}
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
r=dict(source_commit=source,started_utc=now(),status='RUNNING',scripts=identity,steps=[]);meta.write_text(json.dumps(r,indent=2)+'\n')
for n in scripts:
 assert all(hashlib.sha256((s/k).read_bytes()).hexdigest()==v for k,v in identity.items())
 cmd=[str(python),str(s/n),source];step=dict(script=n,started_utc=now(),command=cmd);print(json.dumps(dict(event='START',**step)),flush=True);a=time.monotonic()
 completed=subprocess.run(cmd,cwd=repo);step.update(returncode=completed.returncode,ended_utc=now(),seconds=time.monotonic()-a);r['steps'].append(step);meta.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(event='END',**step)),flush=True)
 if completed.returncode:
  r.update(status='STOPPED_AFTER_FAILURE',ended_utc=now());meta.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(completed.returncode)
r.update(status='COMPLETED',ended_utc=now());meta.write_text(json.dumps(r,indent=2)+'\n')
