"""Byte-preserving archive of owned synthetic evidence; never source snapshots/cache."""
import gzip,hashlib,json
from pathlib import Path
root=Path('/workspace/Sim2Act');target=root/'docs/evidence/csv-full-report-workflows-20261017'
assert not target.exists(),target
target.mkdir(parents=True)
entries=[]
def sha(data):return hashlib.sha256(data).hexdigest()
def add(source,relative):
 assert source.is_file() and not source.is_symlink(),source
 raw=source.read_bytes();compressed=source.suffix in('.db','.sqlite')or len(raw)>1024*1024
 payload=gzip.compress(raw,mtime=0)if compressed else raw
 path=target/relative
 if compressed:path=Path(str(path)+'.gz')
 assert not path.exists(),path
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
 entries.append(dict(original=str(source),path=str(path.relative_to(target)),encoding='gzip'if compressed else'identity',original_bytes=len(raw),original_sha256=sha(raw),stored_bytes=len(payload),stored_sha256=sha(payload)))
def tree(source,tag):
 assert source.is_dir(),source
 for p in sorted(source.rglob('*')):
  if not p.is_file()or p.is_symlink()or '__pycache__'in p.parts:continue
  if any(x.is_symlink()for x in p.parents if x!=source and source in x.parents):continue
  add(p,Path('raw')/tag/p.relative_to(source))
def independent(source,tag):
 manifest=source/'raw-manifest.json';value=json.loads(manifest.read_text());files=value['files'];assert value['count']==len(files)
 for item in files:
  rel=Path(item['path']);assert not rel.is_absolute() and '..' not in rel.parts
  p=source/rel;assert p.is_relative_to(source)and sha(p.read_bytes())==item['sha256'];add(p,Path('raw')/tag/item['path'])
 for name in('raw-manifest.json','SHA256SUMS'):add(source/name,Path('raw')/tag/name)
tree(Path('/workspace/csv-full-report-evidence-20261017'),'author-evidence')
for suffix in('dev-reg','dev-api','dev-api2','dev-pages','dev-pages2','dev-pages3','dev-extra','dev-final'):
 tree(Path('/tmp/csv-full-report-'+suffix),'development-'+suffix)
for short in('4a4a228f','436c49cb'):
 tree(Path('/tmp/csv-full-report-author-'+short+'-20261017'),'author-'+short)
 independent(Path('/tmp/csv-full-report-independent-'+short+'-20261017'),'independent-'+short)
for name in('run-csv-full-report-author.py','run-csv-full-report-author-refine.py','probe-csv-full-report-migration.py','build-csv-full-report-admission.py','archive-csv-full-report-evidence.py','check-csv-full-report-static.py'):
 add(Path('/workspace')/name,Path('runners')/name)
(target/'artifact-map.json').write_text(json.dumps(dict(files=entries,count=len(entries),excludes='reconstructible Git snapshots, cache, pyc and duplicate pytest current symlinks; original files were not changed'),ensure_ascii=False,indent=2))
print(json.dumps(dict(materials=len(entries),sqlite=sum(x['original'].endswith(('.db','.sqlite'))for x in entries),decoded_bytes=sum(x['original_bytes']for x in entries),stored_bytes=sum(x['stored_bytes']for x in entries))))
