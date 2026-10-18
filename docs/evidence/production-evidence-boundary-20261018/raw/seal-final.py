import hashlib
import json
from pathlib import Path

root = Path(__file__).parent
assert not (root / 'manifest-final.json').exists()
original = json.loads((root / 'manifest.json').read_text())
mismatch = [name for name, entry in original['files'].items()
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != entry['sha256']]
assert mismatch == ['close-attempt-2.stdout']
selected = sorted([p for p in root.iterdir() if p.is_file()] + list((root / 'actual-tmp').glob('*/*.json')))
manifest = dict(scope='FINAL SEALED raw execution evidence; prior manifest discrepancy preserved in closure-correction.json',
    files={str(p.relative_to(root)): dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in selected},
    retained_fixture_databases=original['retained_fixture_databases'])
target = root / 'manifest-final.json'
target.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(dict(raw_files=len(selected), raw_bytes=sum(e['bytes'] for e in manifest['files'].values()),
    manifest_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), mismatch_in_prior_manifest=mismatch)))
