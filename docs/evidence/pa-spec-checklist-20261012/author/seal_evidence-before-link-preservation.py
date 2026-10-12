import hashlib,json,tarfile,shutil,subprocess
from pathlib import Path
repo=Path('/workspace/Sim2Act-pa-provider');author=Path('/tmp/pa-spec-checklist-author-20261012');independent=Path('/tmp/pa-spec-checklist-independent-20261012');dest=repo/'docs/evidence/pa-spec-checklist-20261012'
def seal_tree(root,target):
    files={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}
    target.write_text(json.dumps(files,sort_keys=True,indent=2)+'\n');return files
for label,root in [('author',author),('independent',independent)]:
    manifest=seal_tree(root,dest/(label+'-full-manifest.json'))
    with tarfile.open(dest/(label+'-complete.tar.gz'),'w:gz') as archive:
        for name in manifest:archive.add(root/name,arcname=label+'/'+name,recursive=False)
    print(label,len(manifest),sum(v['bytes'] for v in manifest.values()),(dest/(label+'-complete.tar.gz')).stat().st_size)
    readable=dest/label;readable.mkdir(exist_ok=True)
    for p in root.glob('*'):
        if p.is_file() and p.suffix in {'.log','.xml','.json','.md','.txt','.py'}:
            shutil.copy2(p,readable/p.name)
print('sealed evidence only; source/test/UI unchanged')
