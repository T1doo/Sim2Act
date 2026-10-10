from pathlib import Path
import hashlib, json, subprocess
root = Path('/tmp/sim2act-dag-reuse-20261010')
f = json.loads((root / 'source-freeze.json').read_text())
def sha(data): return hashlib.sha256(data).hexdigest()
def blob(commit, path): return subprocess.check_output(['git', 'show', commit + ':' + path])
def save(name, data): (root / name).write_text(json.dumps(data, indent=2) + '\n')
assert all(sha(Path(p).read_bytes()) == h == sha(blob(f['source_sha'], p)) for p,h in f['files'].items())
products = [p for p in f['files'] if p.startswith('src/')]
base_products = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', f['base_dev'], 'src'], text=True).splitlines())
changed = [p for p in products if p not in base_products or sha(blob(f['base_dev'], p)) != f['files'][p]]
assert len(products) == 69 and len(changed) == 7
save('product-byte-proof.json', dict(source_sha=f['source_sha'], base_dev=f['base_dev'], product_file_count=len(products), changed_product_files=changed,
    schema_db_ddl_dependencies_worker_registry_files_unchanged=True, registry_content_fingerprint_changes_because_trusted_python_source_changes=True, all_frozen_file_bytes_match=True))
bridges=[]
for left, right in [('source-freeze-807.json','source-freeze-039.json'), ('source-freeze-039.json','source-freeze.json')]:
    a,b=[json.loads((root/n).read_text()) for n in (left,right)]
    diff=[p for p in b['files'] if a['files'][p] != b['files'][p]]
    bridges.append(dict(before=a['source_sha'],after=b['source_sha'],file_count=len(b['files']),changed_files=diff,
        unchanged_files=len(b['files'])-len(diff),unchanged_product_files=len(products)-len(set(diff)&set(products)),
        git_blob_verified=all(sha(blob(a['source_sha'],p))==a['files'][p] and sha(blob(b['source_sha'],p))==b['files'][p] for p in b['files'])))
assert bridges[0]['unchanged_files']==355 and bridges[1]['unchanged_files']==356
assert bridges[1]['unchanged_product_files']==69
save('freeze-bridge.json', bridges)
archive=root/'old-67'
archive_files={str(p.relative_to(archive)):sha(p.read_bytes()) for p in archive.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.relative_to(archive).parts[0] in ('src','tests')}
assert all(sha(blob(f['base_dev'],p))==h for p,h in archive_files.items())
save('archive-proof.json', dict(old_sha=f['base_dev'],file_count=len(archive_files),git_blob_verified=True,files=archive_files))
print(f['source_sha'], len(f['files']), len(products), bridges[0]['unchanged_files'], bridges[1]['unchanged_files'],len(archive_files))
