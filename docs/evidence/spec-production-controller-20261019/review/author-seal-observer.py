"""Hash sealed nonDB evidence and links; DB files get stat-only checks."""
import hashlib
import json
import os
from pathlib import Path

root = Path('/workspace/spec-production-controller-audit-20261019')
seal_path = root / 'sealed-manifest.json'
seal_bytes = seal_path.read_bytes()
seal_sha = hashlib.sha256(seal_bytes).hexdigest()
assert seal_sha == '622d7e23417e0b98397e255c58fa4e199279709af85efc815428046d64f18f1f'
seal = json.loads(seal_bytes)
hashed = []
stat_only = []
for rel, expected in seal['files'].items():
    relative = Path(rel)
    assert not relative.is_absolute() and '..' not in relative.parts
    path = root / relative
    assert not path.is_symlink() and path.is_file()
    assert path.stat().st_size == expected['bytes']
    if any(suffix in path.name.lower() for suffix in ('.db', '.sqlite')):
        stat_only.append(rel)
    else:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected['sha256']
        hashed.append(rel)
links = seal['symlink_inventory']
for rel, target in links.items():
    assert (root / rel).is_symlink() and os.readlink(root / rel) == target
physical_files = []
physical_links = []
for parent, dirs, files in os.walk(root, followlinks=False):
    for name in dirs[:]:
        path = Path(parent) / name
        if path.is_symlink():
            physical_links.append(str(path.relative_to(root)))
            dirs.remove(name)
    for name in files:
        path = Path(parent) / name
        if path.is_symlink():
            physical_links.append(str(path.relative_to(root)))
        elif path != seal_path:
            physical_files.append(str(path.relative_to(root)))
assert set(physical_files) == set(seal['files'])
assert set(physical_links) == set(links)
assert len(physical_files) == 887 and len(links) == 14
assert sum(x['bytes'] for x in seal['files'].values()) == 36797552
print(json.dumps(dict(verdict='PASS_NONDB_SHA_DB_STAT_ONLY_LINKS',
    manifest=dict(path=str(seal_path), bytes=len(seal_bytes), sha256=seal_sha),
    manifest_regular_files=len(physical_files), manifest_regular_bytes=36797552,
    nonDB_files_sha256_verified=len(hashed), nonDB_bytes_sha256_verified=sum(seal['files'][x]['bytes'] for x in hashed),
    DB_files_stat_only=len(stat_only), DB_paths=stat_only,
    DB_content_opened_or_hashed=False, symlink_targets_verified=len(links),
    exact_physical_inventory=True, author_seal_self_excluded_from_payload=True,
    limitations='No DB byte-hash recomputation or queries. No product/test/network execution.'), indent=2))
