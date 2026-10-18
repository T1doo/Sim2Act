"""Copy exact closed non-DB evidence; never reopen or copy SQLite contents."""
import hashlib,json
from pathlib import Path
repo=Path('/workspace/Sim2Act')
target=repo/'docs/evidence/production-trial-stages-20261018'
target.mkdir(parents=True,exist_ok=False)
combined=[]
for label,root in (
 ('author',Path('/workspace/production-trial-stages-20261018')),
 ('review',Path('/workspace/production-trial-stages-review-20261018'))):
 manifest=root/'sealed-manifest.json'
 value=json.loads(manifest.read_text())
 names=sorted(value['files'])+['sealed-manifest.json']
 selected=[]
 for name in names:
  p=root/name
  assert p.is_file() and not p.is_symlink() and p.suffix not in ('.db','.db-wal','.db-shm')
  raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
  if name!='sealed-manifest.json':
   expected=value['files'][name]
   assert expected['sha256']==sha and expected['bytes']==len(raw)
  dest=target/label/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
  row=dict(source=str(p),target=str(dest.relative_to(repo)),bytes=len(raw),sha256=sha)
  selected.append(row);combined.append(row)
 record=dict(label=label,file_count=len(selected),total_bytes=sum(x['bytes'] for x in selected),
             database_files_copied=0,files=selected)
 (target/(label+'-selection.json')).write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({k:v for k,v in record.items() if k!='files'}))
(target/'selection.json').write_text(json.dumps(dict(file_count=len(combined),
    total_bytes=sum(x['bytes'] for x in combined),database_files_copied=0,files=combined),indent=2)+'\n')
