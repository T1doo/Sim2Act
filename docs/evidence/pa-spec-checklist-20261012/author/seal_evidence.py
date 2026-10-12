import hashlib,json,tarfile,shutil,os,stat
from pathlib import Path
repo=Path('/workspace/Sim2Act-pa-provider');author=Path('/tmp/pa-spec-checklist-author-20261012');independent=Path('/tmp/pa-spec-checklist-independent-20261012');dest=repo/'docs/evidence/pa-spec-checklist-20261012'
def seal_tree(root,target):
    entries={}
    for p in sorted(root.rglob('*')):
        if '__pycache__' in p.parts or '.pytest_cache' in p.parts:continue
        name=str(p.relative_to(root));mode=stat.S_IMODE(p.lstat().st_mode)
        if p.is_symlink():entries[name]=dict(type='symlink',target=os.readlink(p),mode=mode)
        elif p.is_file():entries[name]=dict(type='file',bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=mode)
        elif p.is_dir():entries[name]=dict(type='directory',mode=mode)
    target.write_text(json.dumps(entries,sort_keys=True,indent=2)+'\n');return entries
results={}
for label,root in [('author',author),('independent',independent)]:
    manifest=seal_tree(root,dest/(label+'-full-manifest.json'));archive_path=dest/(label+'-complete.tar.gz')
    with tarfile.open(archive_path,'w:gz') as archive:
        for name in manifest:archive.add(root/name,arcname=label+'/'+name,recursive=False)
    verified=set()
    with tarfile.open(archive_path,'r:gz') as archive:
        for member in archive:
            assert member.name.startswith(label+'/');name=member.name[len(label)+1:].rstrip('/');expected=manifest[name];assert name not in verified;verified.add(name)
            assert member.mode==expected['mode']
            if expected['type']=='file':
                assert member.isfile() and member.size==expected['bytes']
                content=archive.extractfile(member);digest=hashlib.sha256()
                while chunk:=content.read(1024*1024):digest.update(chunk)
                assert digest.hexdigest()==expected['sha256']
            elif expected['type']=='symlink':assert member.issym() and member.linkname==expected['target']
            else:assert member.isdir()
    assert verified==set(manifest)
    results[label]=dict(entries=len(manifest),files=sum(v['type']=='file' for v in manifest.values()),directories=sum(v['type']=='directory' for v in manifest.values()),symlinks=sum(v['type']=='symlink' for v in manifest.values()),archive_bytes=archive_path.stat().st_size,archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),verified_entries=len(verified))
    readable=dest/label;readable.mkdir(exist_ok=True)
    for p in root.glob('*'):
        if p.is_file() and p.suffix in {'.log','.xml','.json','.md','.txt','.py'}:shutil.copy2(p,readable/p.name)
(dest/'archive-verification.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
