"""Run only after qualifications, logs, static review and all local DB owners close."""
import hashlib
import json
from pathlib import Path

root=Path('/workspace/production-trial-stages-20261018')
files={}
excluded=[]
for p in sorted(root.rglob('*')):
    if not p.is_file() or p.is_symlink():
        continue
    name=p.relative_to(root).as_posix()
    if '__pycache__' in p.parts or any(s.endswith('current') for s in p.parts):
        continue
    if p.suffix in ('.db','.db-wal','.db-shm') or name=='sealed-manifest.json':
        excluded.append(name)
        continue
    data=p.read_bytes()
    files[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
value={'scope':'THIS_ROUND_NEW_STAGES_AUTHOR_EVIDENCE_ONLY','files':files,
       'file_count':len(files),'total_bytes':sum(v['bytes'] for v in files.values()),
       'excluded_external_sqlite_fixtures_and_manifest':excluded,
       'database_hashes_in':'qualification-summary.json'}
payload=(json.dumps(value,indent=2)+'\n').encode()
path=root/'sealed-manifest.json'
assert not path.exists()
path.write_bytes(payload)
for name in files:(root/name).chmod(0o444)
path.chmod(0o444)
print(json.dumps({'manifest_sha256':hashlib.sha256(payload).hexdigest(),
                  'manifest_bytes':len(payload),'files':value['file_count'],
                  'raw_bytes':value['total_bytes']}))
