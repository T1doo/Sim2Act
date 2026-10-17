"""Archive only this task's exact original outputs; no source snapshots or old bundles."""
import gzip,hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/Sim2Act');base=root/'docs/evidence/ordinary-goal-human-review-20261017';base.mkdir(parents=True,exist_ok=True)
ind=Path('/tmp/ordinary-owner-review-independent-a3a4f4a-20261017');own=Path('/workspace/ordinary-owner-evidence-20261017')
assert (own/'final-execution.json').is_file() and (ind/'review.json').is_file()
origins=[('author-meta',own),('initial-red',Path('/tmp/ordinary-owner-initial-red-20261017')),('api-dev-1',Path('/tmp/ordinary-owner-dev-1')),('api-dev-2',Path('/tmp/ordinary-owner-dev-2')),('ui-dev-1',Path('/tmp/ordinary-owner-ui-dev-1')),('ui-dev-2',Path('/tmp/ordinary-owner-ui-dev-2')),('ui-dev-3',Path('/tmp/ordinary-owner-ui-dev-3')),('all-dev-4',Path('/tmp/ordinary-owner-dev-4')),('ui-dev-5',Path('/tmp/ordinary-owner-ui-dev-5')),('author-final',Path('/tmp/ordinary-owner-author-final-a3a4f4a5-20261017')),('independent-final',ind)]
items=[]
for label,origin in origins:
 assert origin.is_dir(),origin
 for path in sorted(origin.rglob('*')):
  if not path.is_file() or path.is_symlink():continue
  rel=path.relative_to(origin)
  if '__pycache__' in rel.parts or path.suffix=='.pyc' or (label=='independent-final' and rel.parts[0]=='snapshot'):continue
  data=path.read_bytes();compressed=path.suffix=='.db' or len(data)>1000000
  target=base/'raw'/label/rel;target=Path(str(target)+'.gz') if compressed else target;target.parent.mkdir(parents=True,exist_ok=True)
  encoded=gzip.compress(data,mtime=0) if compressed else data;target.write_bytes(encoded)
  assert (gzip.decompress(target.read_bytes()) if compressed else target.read_bytes())==data
  items.append(dict(original=str(path),archive=str(target.relative_to(base)),original_size=len(data),original_sha256=hashlib.sha256(data).hexdigest(),encoding='gzip-mtime0' if compressed else 'identity',archived_sha256=hashlib.sha256(encoded).hexdigest()))
(base/'artifact-map.json').write_text(json.dumps(dict(tested_product='a3a4f4a524a8eb39f14be7109dabfdd475c7d7e3',originals=items),ensure_ascii=False,indent=2)+'\n')
(base/'.gitattributes').write_text('raw/** -text whitespace=-trailing-space\nraw/**/*.md -text whitespace=cr-at-eol,-trailing-space\n')
print(json.dumps(dict(originals=len(items),original_bytes=sum(x['original_size'] for x in items),archived_bytes=sum((base/x['archive']).stat().st_size for x in items))))
