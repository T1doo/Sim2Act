"""Archive only this task's known original outputs; gzip preserves decoded bytes."""
import gzip,hashlib,json
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/ordinary-goal-correction-evidence-20261017');dest=root/'docs/evidence/ordinary-goal-correction-20261017'
assert not dest.exists();dest.mkdir(parents=True)
sources={}
def add_tree(label,path):
 path=Path(path);assert path.exists(),str(path)
 for p in sorted(path.rglob('*')):
  if not p.is_file() or p.is_symlink() or any(q.is_symlink() for q in p.parents if q!=path.parent):continue
  if '__pycache__' in p.parts or p.suffix=='.pyc':continue
  sources[f'raw/{label}/{p.relative_to(path)}']=p
add_tree('author-meta',out)
roots={
 'initial-red':'/tmp/ordinary-correction-red-20261017',
 'api-dev-1':'/tmp/ordinary-correction-api-dev1-20261017',
 'api-dev-2':'/tmp/ordinary-correction-api-dev2-20261017',
 'success-dev-3':'/tmp/ordinary-correction-success-dev3-20261017',
 'ui-dev-4':'/tmp/ordinary-correction-ui-dev4-20261017',
 'ui-dev-5':'/tmp/ordinary-correction-ui-dev5-20261017',
 'final-gate-dev-6':'/tmp/ordinary-correction-final-gate-dev6-20261017',
 'body-gate-dev-7':'/tmp/ordinary-correction-body-gate-dev7-20261017',
 'author-superseded-7378':'/tmp/ordinary-goal-correction-author-final-7378b97e-r1-20261017',
 'migration-superseded-7378':'/tmp/ordinary-correction-migration-probe-7378b97e-20261017',
 'author-final-api':'/tmp/ordinary-goal-correction-author-final-d731199a-api-20261017',
 'author-final-pages':'/tmp/ordinary-goal-correction-author-final-d731199a-pages-20261017',
 'migration-final':'/tmp/ordinary-correction-migration-probe-d731199a-20261017'}
for label,path in roots.items():add_tree(label,path)
# Each independent manifest deliberately excludes its reproducible source/dependency inputs.
independent=json.loads((out/'independent-seals-verified.json').read_text())
for entry in independent['seals']:
 path=Path(entry['directory']);manifest=json.loads((path/'raw-manifest.json').read_text())
 for item in manifest['files']:
  p=path/item['path'];assert p.is_file() and p.stat().st_size==item['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'];sources[f"raw/{entry['label']}/{item['path']}"]=p
 for name in ('raw-manifest.json','raw-sha256sums.txt'):sources[f"raw/{entry['label']}/{name}"]=path/name
originals=[]
for archive,p in sorted(sources.items()):
 raw=p.read_bytes();encoding='gzip-mtime0' if p.suffix=='.db' or len(raw)>1_000_000 else 'identity';encoded=gzip.compress(raw,compresslevel=9,mtime=0) if encoding!='identity' else raw
 name=archive+('.gz' if encoding!='identity' else '');target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(encoded)
 originals.append(dict(original=str(p),archive=name,size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),encoding=encoding,encoded_sha256=hashlib.sha256(encoded).hexdigest()))
(dest/'artifact-map.json').write_text(json.dumps(dict(source='d731199a1fd6272e1a79e1c761a1461500fd5227',originals=originals),ensure_ascii=False,indent=2)+'\n')
(dest/'.gitattributes').write_text('raw/** -text whitespace=-trailing-space\nraw/**/*.md -text whitespace=cr-at-eol,-trailing-space\n')
print(json.dumps(dict(originals=len(originals),evidence_files_after_readme_and_sums=len(originals)+4,checksums=len(originals)+3)))
