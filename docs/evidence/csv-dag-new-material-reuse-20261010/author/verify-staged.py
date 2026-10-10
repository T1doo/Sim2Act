import json,hashlib,subprocess
from pathlib import Path
repo=Path('/workspace/Sim2Act');r=Path('/tmp/sim2act-dag-new-csv-20261010');out=repo/'docs/evidence/csv-dag-new-material-reuse-20261010'
w=json.loads((out/'COPY_WHITELIST.json').read_text());freeze=json.loads((r/'source-freeze-complete-readback.json').read_text())
for f in w['files']:
    path=str((out/f['path']).relative_to(repo));b=(repo/path).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],path
    staged=subprocess.check_output(['git','show',':'+path],cwd=repo);assert staged==b,path
for f in freeze['files']:
    b=(repo/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['path']
    assert subprocess.check_output(['git','show',':'+f['path']],cwd=repo)==b,f['path']
staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=repo).decode().split('\0');assert all(not p or p.startswith('docs/') for p in staged),staged
result=dict(source_sha=freeze['source_sha'],staged_docs_only=True,root_gitattributes_unchanged=True,all373_non_docs_unchanged=True,preserved_files=len(w['files']),preserved_bytes=w['bytes'],all_worktree_staged_blobs_equal=True,COPY_WHITELIST_sha256=hashlib.sha256((out/'COPY_WHITELIST.json').read_bytes()).hexdigest(),LIVE=0)
(r/'staged-byte-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
