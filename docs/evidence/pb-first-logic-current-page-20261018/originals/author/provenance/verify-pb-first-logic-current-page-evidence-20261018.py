import hashlib
import json
import tarfile
from pathlib import Path

root = Path('/workspace/Sim2Act/docs/evidence/pb-first-logic-current-page-20261018')
rows = json.loads((root / 'raw-manifest.json').read_text())
seen = set()
with tarfile.open(root / 'raw-evidence.tar.gz', 'r:gz') as archive:
    members = {member.name: member for member in archive.getmembers() if member.isfile()}
    assert set(members) == {row['path'] for row in rows}
    for row in rows:
        assert row['path'] not in seen
        seen.add(row['path'])
        data = (root / 'originals' / row['path']).read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
        assert archive.extractfile(members[row['path']]).read() == data
        if row.get('text_parts'):
            parts = []
            cursor = 0
            for part in row['text_parts']:
                piece = (root / part['path']).read_bytes()
                piece.decode('utf-8')
                assert part['start_byte'] == cursor and part['end_byte'] - cursor == len(piece) == part['bytes']
                assert hashlib.sha256(piece).hexdigest() == part['sha256']
                cursor = part['end_byte']
                parts.append(piece)
            assert b''.join(parts) == data and cursor == len(data)
summary = json.loads((root / 'package-summary.json').read_text())
assert summary['raw_files'] == len(rows)
assert summary['raw_bytes'] == sum(row['bytes'] for row in rows)
bundle = (root / 'raw-evidence.tar.gz').read_bytes()
assert summary['bundle_bytes'] == len(bundle)
assert summary['bundle_sha256'] == hashlib.sha256(bundle).hexdigest()
files = sorted(path for path in root.rglob('*') if path.is_file() and path.name != 'SHA256SUMS')
(root / 'SHA256SUMS').write_text(''.join(
    hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + str(path.relative_to(root)) + '\n'
    for path in files))
print(json.dumps(dict(verified_raw_files=len(rows), checksummed_files=len(files),
    total_evidence_files=len(files)+1, bundle_sha256=summary['bundle_sha256'])))
