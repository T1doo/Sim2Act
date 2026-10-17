import gzip,hashlib,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
repo=Path('/workspace/Sim2Act');out=Path('/workspace/ordinary-goal-md-evidence-20261017');ind=Path('/tmp/ordinary-goal-md-independent-1bacf0bb-20261017');base=repo/'docs/evidence/ordinary-goal-md-delivery-20261017';base.mkdir(parents=True,exist_ok=True)
seal={'review.json':'1b4a493046f036e79c706c78c720cca34895ace50f9392bc1ea83dfbe676625d','proof.json':'cd07db22725daa69470235dc4328f592989b0601fd1fbbc9ff522c10c6c52b5d','raw-manifest.json':'c79ad7689459ca95b0b1bc7e44a1b19a4562de84fc2beb5ad6e8bf2610f11158','raw-sha256sums.txt':'71c449d9e76fd5be8229b964212bc83fe3b25c8e36ba4c4e7b4770e34eab2558'}
for name,sha in seal.items():assert hashlib.sha256((ind/name).read_bytes()).hexdigest()==sha
manifest=json.loads((ind/'raw-manifest.json').read_text());assert len(manifest['files'])==84
for f in manifest['files']:
 data=(ind/f['path']).read_bytes();assert len(data)==f['size'] and hashlib.sha256(data).hexdigest()==f['sha256']
(out/'independent-seal-verified.json').write_text(json.dumps(dict(directory=str(ind),stopped_writing=True,verified_manifest_entries=84,hashes=seal),indent=2)+'\n')
g=['git','-c','core.fsmonitor=false'];red=subprocess.check_output(g+['rev-parse','1bacf0bb^'],cwd=repo,text=True).strip();assert red=='07afe21d034a22a397ebadd13bfa699cf1093671';assert not subprocess.check_output(g+['diff','28506343f7513b2f97476f38dca6bd7b71e08b6f',red,'--','src','schemas'],cwd=repo)
(out/'red-provenance.json').write_text(json.dumps(dict(product_base='28506343f7513b2f97476f38dca6bd7b71e08b6f',test_commit=red,product_source_identical=True,actual_first_failure='HTTP404 missing reviewable-artifact-runs route',other_development_failures_preserved_not_counted_as_acceptance=True),indent=2)+'\n')
assert json.loads((out/'final-execution.json').read_text())['clean_worktree']
branch='dev/ordinary-goal-md-delivery-20261017';remote=subprocess.check_output(g+['ls-remote','origin','refs/heads/'+branch],cwd=repo,text=True);assert not remote
(out/'new-branch-remote-before-push.json').write_text(json.dumps(dict(branch=branch,actual_ls_remote_output=remote,new_branch_absent=True),indent=2)+'\n')
origins=[('author-meta',out),('initial-red',Path('/tmp/ordinary-goal-md-red-20261017')),('api-dev-1',Path('/tmp/ordinary-goal-md-dev-1')),('ui-dev-1',Path('/tmp/ordinary-goal-md-ui-dev-1')),('all-dev-2',Path('/tmp/ordinary-goal-md-dev-2')),('all-dev-3',Path('/tmp/ordinary-goal-md-dev-3')),('author-final',Path('/tmp/ordinary-goal-md-author-final-1bacf0bb-20261017')),('independent-final',ind)]
items=[]
for label,origin in origins:
 assert origin.is_dir(),origin
 for path in sorted(origin.rglob('*')):
  if not path.is_file() or path.is_symlink():continue
  rel=path.relative_to(origin)
  if '__pycache__' in rel.parts or path.suffix=='.pyc' or (label=='independent-final' and rel.parts[0]=='snapshot'):continue
  data=path.read_bytes();compressed=path.suffix=='.db' or len(data)>1000000;target=base/'raw'/label/rel
  if compressed:target=Path(str(target)+'.gz')
  target.parent.mkdir(parents=True,exist_ok=True);encoded=gzip.compress(data,mtime=0) if compressed else data;target.write_bytes(encoded)
  assert (gzip.decompress(encoded) if compressed else encoded)==data
  items.append(dict(original=str(path),archive=str(target.relative_to(base)),size=len(data),sha256=hashlib.sha256(data).hexdigest(),encoding='gzip-mtime0' if compressed else 'identity',encoded_sha256=hashlib.sha256(encoded).hexdigest()))
(base/'artifact-map.json').write_text(json.dumps(dict(source='1bacf0bb015fedafa57d6ea27b8eb2b51292859e',originals=items),ensure_ascii=False,indent=2)+'\n');(base/'.gitattributes').write_text('raw/** -text whitespace=-trailing-space\nraw/**/*.md -text whitespace=cr-at-eol,-trailing-space\n')
print(json.dumps(dict(originals=len(items),raw_bytes=sum(x['size'] for x in items),archive_bytes=sum((base/x['archive']).stat().st_size for x in items))))
