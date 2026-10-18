import datetime, hashlib, json, subprocess, sys
from pathlib import Path
root=Path('/workspace/Sim2Act')
tracked=subprocess.check_output(['git','-c','core.fsmonitor=false','ls-files','-z'],cwd=root).decode().split('\0')
paths=sorted(p for p in tracked if p and (p.startswith(('src/','tests/','scripts/','.github/')) or p in {'.gitattributes','pyproject.toml','requirements.lock','requirements-windows.lock'}))
inputs={p:dict(bytes=(root/p).stat().st_size,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in paths}
head=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=root,text=True).strip()
out=dict(head=head,time_utc=datetime.datetime.now(datetime.UTC).isoformat(),input_count=len(inputs),production_count=sum(p.startswith('src/') for p in inputs),inputs=inputs)
Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='inputs'}))
