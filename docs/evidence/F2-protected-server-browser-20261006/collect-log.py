"""Decode only bounded, explicitly named synthetic CI evidence from authorized GitHub log."""
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding='utf-8')
output = Path(__file__).resolve().parent
allowed = {'browser-results.json', 'desktop.png', 'mobile.png', 'failure.png'}
metadata, chunks = {}, {}
for line in text.splitlines():
    match = re.search(r'SIM2ACT_BROWSER_FILE (\{.+\})$', line)
    if match:
        item = json.loads(match[1]); name = item['name']
        assert name in allowed and name not in metadata
        assert 0 <= item['bytes'] <= 2_000_000 and 0 < item['chunks'] <= 700
        metadata[name] = item
    match = re.search(r'SIM2ACT_BROWSER_CHUNK (\S+) (\d+) ([A-Za-z0-9+/=]+)$', line)
    if match:
        name, number, data = match.groups(); number = int(number)
        assert name in allowed and number not in chunks.setdefault(name, {})
        chunks[name][number] = data
for name, item in metadata.items():
    pieces = chunks[name]
    assert sorted(pieces) == list(range(item['chunks']))
    data = base64.b64decode(''.join(pieces[n] for n in range(item['chunks'])), validate=True)
    assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    if name.endswith('.png'):
        assert data.startswith(b'\x89PNG\r\n\x1a\n')
    else:
        report = json.loads(data)
        assert report['commit'] == sys.argv[2]
    (output / name).write_bytes(data)
(output / 'evidence-receipts.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(json.dumps({'decoded':list(metadata), 'verified_length_sha256_chunk_order':True}))
