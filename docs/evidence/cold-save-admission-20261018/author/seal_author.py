"""Seal closed author files; SQLite fixtures stay external and are never copied."""
import hashlib,json,re
from pathlib import Path
root=Path('/workspace/cold-save-admission-20261018')
files={};excluded=[]
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.is_symlink() or '__pycache__' in p.parts:continue
 name=p.relative_to(root).as_posix()
 if name=='sealed-manifest.json':continue
 if re.search(r'\.(db|sqlite|sqlite3)($|[-.])',p.name.lower()):
  excluded.append(name);continue
 raw=p.read_bytes();files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
value={'scope':'COLD_SAVE_ADMISSION_AUTHOR_CLOSED_FILES_ONLY','source_sha':'fd96df814e8c0fb6db6651ce77eb484951240ecc','qualification':'FRESH_MOCK_QUALIFIED_NOT_LIVE','files':files,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files.values()),'excluded_external_databases':excluded,'database_hashes_in':'closed-summary.json'}
raw=(json.dumps(value,indent=2)+'\n').encode();p=root/'sealed-manifest.json';assert not p.exists();p.write_bytes(raw)
for name in files:(root/name).chmod(0o444)
p.chmod(0o444)
print(json.dumps({'manifest_sha256':hashlib.sha256(raw).hexdigest(),'manifest_bytes':len(raw),'files':len(files),'raw_bytes':value['total_bytes'],'database_files_excluded':len(excluded)}))
