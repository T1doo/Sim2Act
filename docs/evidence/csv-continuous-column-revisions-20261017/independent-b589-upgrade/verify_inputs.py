import hashlib
import json
from pathlib import Path
import subprocess

base=Path('/tmp/csv-upgrade-independent-b5898093-20261017')
snapshot=base/'snapshot'
before=json.loads((base/'inputs-before.json').read_text())
entries=[]
mismatches=[]
for old in before['entries']:
    content=(snapshot/old['path']).read_bytes()
    git_blob=subprocess.check_output(['git','hash-object','--stdin'],input=content,cwd='/workspace/Sim2Act').decode().strip()
    new={**old,'git_blob':git_blob,'sha256':hashlib.sha256(content).hexdigest(),'size':len(content)}
    if new!=old:
        mismatches.append(dict(path=old['path'],before=old,after=new))
    entries.append(new)
known={x['path'] for x in before['entries']}
extra_files=sorted(str(p.relative_to(snapshot)) for p in snapshot.rglob('*') if p.is_file() and not p.is_symlink() and str(p.relative_to(snapshot)) not in known)
# Path.rglob does not traverse runtime dependency symlinks on Python 3.12.
report=dict(sha=before['sha'],entries=entries,mismatches=mismatches,extra_files=extra_files,git_blob_checks=len(entries),all_input_bytes_unchanged=not mismatches and not extra_files)
(base/'inputs-after.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='entries'}))
if mismatches or extra_files:
    raise SystemExit(1)
