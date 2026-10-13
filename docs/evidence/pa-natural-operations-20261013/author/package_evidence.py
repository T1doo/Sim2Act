"""Package finalized local evidence; preserve diagnostics and verify every member."""
from pathlib import Path
import hashlib
import json
import shutil
import tarfile

ROOT = Path('/workspace/pa-natural-operations-evidence-20261013')
DEST = Path('/workspace/Sim2Act-pa-provider/docs/evidence/pa-natural-operations-20261013')
CACHE_NAMES = {'__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache', 'selected-cache'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def package(name):
    source = ROOT / name
    entries = []
    excluded = []
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source)
        if any(part in CACHE_NAMES for part in relative.parts):
            excluded.append(str(relative))
            continue
        row = {'path': str(relative)}
        if path.is_symlink():
            row.update(type='symlink', target=str(path.readlink()))
        elif path.is_dir():
            row.update(type='directory')
        elif path.is_file():
            content = path.read_bytes()
            row.update(type='file', bytes=len(content), sha256=sha(content))
        else:
            raise ValueError(f'Unexpected evidence object: {path}')
        entries.append(row)
    archive = DEST / f'{name}-complete.tar.gz'
    with tarfile.open(archive, 'w:gz', dereference=False) as bundle:
        for row in entries:
            bundle.add(source / row['path'], arcname=f"{name}/{row['path']}", recursive=False)
    verified = []
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        assert len(members) == len(entries)
        for row, member in zip(entries, members, strict=True):
            assert member.name == f"{name}/{row['path']}"
            if row['type'] == 'file':
                assert member.isfile()
                content = bundle.extractfile(member).read()
                assert len(content) == row['bytes'] and sha(content) == row['sha256']
            elif row['type'] == 'directory':
                assert member.isdir()
            else:
                assert member.issym() and member.linkname == row['target']
            verified.append(member.name)
    # Expose the compact original command/result/log/XML records without unpacking.
    direct = DEST / name
    direct.mkdir(exist_ok=True)
    copies = []
    for row in entries:
        if row['type'] != 'file' or '/' in row['path']:
            continue
        shutil.copyfile(source / row['path'], direct / row['path'])
        assert sha((direct / row['path']).read_bytes()) == row['sha256']
        copies.append(row['path'])
    manifest = {'source': str(source), 'entries': entries,
                'excluded_rebuildable_cache_entries': excluded, 'direct_copies': copies}
    manifest_path = DEST / f'{name}-full-manifest.json'
    dump(manifest_path, manifest)
    return {'name': name, 'archive': archive.name, 'bytes': archive.stat().st_size,
            'sha256': sha(archive.read_bytes()), 'members': len(entries),
            'files': sum(row['type'] == 'file' for row in entries),
            'directories': sum(row['type'] == 'directory' for row in entries),
            'symlinks': sum(row['type'] == 'symlink' for row in entries),
            'verified_members': len(verified), 'mismatches': 0,
            'manifest_sha256': sha(manifest_path.read_bytes())}


if __name__ == '__main__':
    DEST.mkdir(parents=True, exist_ok=True)
    reports = [package(name) for name in ('author', 'independent')]
    dump(DEST / 'archive-verification.json', reports)
    shutil.copyfile(Path(__file__), DEST / 'package_evidence.py')
    print(json.dumps(reports, ensure_ascii=False))
