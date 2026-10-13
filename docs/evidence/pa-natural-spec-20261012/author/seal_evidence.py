"""Archive this task's completed evidence and independently read it back."""
import hashlib
import json
import os
import shutil
import stat
import tarfile
from pathlib import Path

REPO = Path('/workspace/Sim2Act-pa-provider')
RUNTIME = Path('/workspace/pa-natural-spec-runtime-evidence-20261012')
DEST = REPO / 'docs/evidence/pa-natural-spec-20261012'

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')

def entries(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if '__pycache__' in path.parts or '.pytest_cache' in path.parts or path.name.endswith('-cache') or any(p.endswith('-cache') for p in path.parts):
            continue
        name = str(path.relative_to(root))
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            result[name] = dict(type='symlink', target=os.readlink(path), mode=mode)
        elif path.is_file():
            result[name] = dict(type='file', bytes=path.stat().st_size, sha256=sha(path), mode=mode)
        elif path.is_dir():
            result[name] = dict(type='directory', mode=mode)
        else:
            raise AssertionError(('unsupported evidence entry', name))
    return result

DEST.mkdir(parents=True, exist_ok=True)
result = {}
for label in ['author', 'independent']:
    root = RUNTIME / label
    manifest = entries(root)
    dump(DEST / (label + '-full-manifest.json'), manifest)
    archive_path = DEST / (label + '-complete.tar.gz')
    with tarfile.open(archive_path, 'w:gz', dereference=False) as archive:
        for name in manifest:
            archive.add(root / name, arcname=label + '/' + name, recursive=False)
    assert archive_path.stat().st_size < 100_000_000, 'Normal Git individual-file size exceeded'
    verified = set()
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in archive:
            assert member.name.startswith(label + '/')
            name = member.name[len(label) + 1:].rstrip('/')
            assert name not in verified
            expected = manifest[name]
            verified.add(name)
            assert member.mode == expected['mode']
            if expected['type'] == 'file':
                assert member.isfile() and member.size == expected['bytes']
                stream = archive.extractfile(member)
                digest = hashlib.sha256()
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
                assert digest.hexdigest() == expected['sha256'], name
            elif expected['type'] == 'symlink':
                assert member.issym() and member.linkname == expected['target'], name
            else:
                assert member.isdir(), name
    assert verified == set(manifest)
    assert entries(root) == manifest, 'Evidence changed during archive creation'
    result[label] = dict(entries=len(manifest), files=sum(v['type'] == 'file' for v in manifest.values()),
                         directories=sum(v['type'] == 'directory' for v in manifest.values()),
                         symlinks=sum(v['type'] == 'symlink' for v in manifest.values()),
                         archive_bytes=archive_path.stat().st_size, archive_sha256=sha(archive_path),
                         verified_entries=len(verified), source_bytes=sum(v.get('bytes', 0) for v in manifest.values()))
    # Small original review/result documents remain directly inspectable too.
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any('tmp' in p or 'fixtures' in p or 'source-reviewed' in p or 'cache' in p or 'probes' == p for p in relative.parts):
            continue
        if path.suffix not in {'.log', '.xml', '.json', '.md', '.txt', '.py', '.stdout', '.stderr', '.sha256', '.patch'}:
            continue
        target = DEST / label / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
dump(DEST / 'archive-verification.json', result)
print(json.dumps(result, indent=2))
