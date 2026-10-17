import hashlib,io,json,subprocess,tarfile
from pathlib import Path
repo=Path('/workspace/Sim2Act');root=Path('/tmp/csv-continuous-upgrade-candidate-20261017');assert not root.exists();root.mkdir()
paths=['src','tests','schemas','pyproject.toml','docs/evidence/bounded-agent-offline-20261006','docs/evidence/model-protocol-preparation-20261006/materials','docs/evidence/protocol-store-loop-20261006/evaluation']
blob=subprocess.check_output(['git','archive','d74f2fed55b6067e5d3c34ca6e4348b92e75f48a',*paths],cwd=repo)
with tarfile.open(fileobj=io.BytesIO(blob)) as tar:tar.extractall(root,filter='data')
draft=Path('/tmp/csv-continuous-upgrade-draft-20261017');overlay=[]
for p in draft.rglob('*'):
 if p.is_file() and p.suffix in ('.py','.js','.cjs'):
  rel=p.relative_to(draft);(root/rel).write_bytes(p.read_bytes());overlay.append(str(rel))
dep=root/'scripts/engineering-ci/node_modules';dep.parent.mkdir(parents=True);dep.symlink_to('/workspace/Sim2Act/scripts/engineering-ci/node_modules',target_is_directory=True)
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and 'node_modules' not in p.parts and '__pycache__' not in p.parts}
out=Path('/workspace/csv-continuous-column-evidence-20261017/author-upgrade-candidate');out.mkdir()
(out/'inputs-before.json').write_text(json.dumps(dict(base_sha='d74f2fed55b6067e5d3c34ca6e4348b92e75f48a',snapshot=str(root),overlay=overlay,files=files),indent=2))
print(json.dumps(dict(snapshot=str(root),inputs=len(files),overlay=overlay),indent=2))
