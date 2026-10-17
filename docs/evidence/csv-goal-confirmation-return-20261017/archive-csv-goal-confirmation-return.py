import gzip,hashlib,json,shutil
from pathlib import Path

repo=Path('/workspace/Sim2Act')
raw=Path('/workspace/csv-goal-confirmation-return-evidence-20261017')
dest=repo/'docs/evidence/csv-goal-confirmation-return-20261017'
assert not dest.exists(), 'Do not overwrite an existing evidence package'
dest.mkdir(parents=True)
roots=[
 ('author-originals',raw),
 ('author-776-original-data',Path('/tmp/csv-goal-confirmation-return-author-776d7658-original-20261017')),
 ('author-776-confirmation-data',Path('/tmp/csv-goal-confirmation-return-author-776d7658-confirmation-return-20261017')),
 ('author-849-refined-data',Path('/tmp/csv-goal-confirmation-return-author-refined-849a931f-20261017')),
 ('development-data',Path('/tmp/csv-goal-confirmation-return-dev-20261017')),
 ('development-safety-data',Path('/tmp/csv-goal-confirmation-return-dev-safety-20261017')),
 ('independent-776',Path('/tmp/csv-goal-confirmation-independent-776d7658-20261017')),
 ('independent-849',Path('/tmp/csv-goal-confirmation-independent-849a931f-20261017')),
]
manifest=[]
for prefix,root in roots:
 assert root.is_dir(),root
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root)
  if not p.is_file() or p.is_symlink() or any(x in rel.parts for x in ('snapshot','__pycache__','.pytest_cache','node_modules')) or any(x.endswith('current') for x in rel.parts):continue
  data=p.read_bytes()
  compressed=p.suffix in ('.db','.sqlite','.sqlite3','.log','.xml') or len(data)>1024*1024
  name=prefix+'/'+str(rel)+('.gz' if compressed else '')
  target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
  manifest.append(dict(original=str(p),saved=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),encoding='gzip' if compressed else 'identity',stored_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
for name in ('run-csv-goal-confirmation-return-author.py','run-csv-goal-confirmation-return-refined.py','verify-csv-goal-confirmation-return-pages.py','archive-csv-goal-confirmation-return.py'):
 p=Path('/workspace')/name;shutil.copyfile(p,dest/name)
(dest/'ORIGINALS.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
report=dict(original_files=len(manifest),sqlite_copies=sum(Path(x['original']).suffix in ('.db','.sqlite','.sqlite3') for x in manifest),original_bytes=sum(x['bytes'] for x in manifest),stored_bytes=sum((dest/x['saved']).stat().st_size for x in manifest),all_decoded_originals_verified=all(hashlib.sha256(gzip.decompress((dest/x['saved']).read_bytes()) if x['encoding']=='gzip' else (dest/x['saved']).read_bytes()).hexdigest()==x['sha256'] for x in manifest))
(dest/'archive-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
