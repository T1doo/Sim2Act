import hashlib
import json
import tarfile
from pathlib import Path

root = Path('/workspace/Sim2Act')
dest = root / 'docs/evidence/natural-result-navigation-20261018'
dest.mkdir(parents=True, exist_ok=True)
inputs = {
    'author': Path('/workspace/natural-result-navigation-evidence-20261018'),
    'independent': Path('/workspace/next-user-flow-independent-20261018'),
    'python-draft': Path('/workspace/natural-result-navigation-tests-draft-20261018'),
    'ui-draft': Path('/workspace/natural-result-navigation-ui-draft-20261018'),
}
manifest, text_rows = [], []
bundle = dest / 'raw-evidence.tar.gz'
with tarfile.open(bundle, 'w:gz') as archive:
    for label, source in inputs.items():
        for path in sorted(source.rglob('*')):
            if not path.is_file() or path.is_symlink() or (label != 'independent' and (
                path.suffix == '.pyc' or any(part in {'__pycache__', '.pytest_cache'} for part in path.parts))):
                continue
            relative = Path(label) / path.relative_to(source)
            data = path.read_bytes()
            copied = dest / 'originals' / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(data)
            archive.add(copied, arcname=str(relative), recursive=False)
            record = dict(path=str(relative), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            try:
                data.decode('utf-8')
                if b'\0' in data:
                    raise UnicodeError('binary')
                record['encoding'] = 'UTF-8'
                parts = []
                if len(data) > 200_000:
                    offset = 0
                    while offset < len(data):
                        end = min(offset + 180_000, len(data))
                        while end < len(data) and data[end] & 0xC0 == 0x80:
                            end -= 1
                        part = Path('text-parts') / relative.parent / (relative.name + f'.{len(parts)+1:03}.txt')
                        target = dest / part
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data[offset:end])
                        parts.append(dict(path=str(part), start_byte=offset, end_byte=end,
                            bytes=end-offset, sha256=hashlib.sha256(data[offset:end]).hexdigest()))
                        offset = end
                    record['text_parts'] = parts
                text_rows.append((relative, parts))
            except UnicodeError:
                record['encoding'] = 'BINARY_SYNTHETIC_DATABASE_OR_ARTIFACT'
            manifest.append(record)
(dest / 'raw-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
lines = ['# 可直接阅读的原件', '', 'originals保留原始bytes；大UTF-8文件按byte offset无损分段。SQLite均为合成夹具，二进制链接和hash保留。', '']
for relative, parts in text_rows:
    lines.append(f'- [{relative}](originals/{relative.as_posix()})')
    for part in parts:
        lines.append(f'  - [bytes {part["start_byte"]}–{part["end_byte"]}末端不含]({part["path"]})')
(dest / 'READABLE.md').write_text('\n'.join(lines) + '\n')
summary = dict(raw_files=len(manifest), raw_bytes=sum(row['bytes'] for row in manifest),
    utf8_files=len(text_rows), binary_files=len(manifest)-len(text_rows),
    bundle_bytes=bundle.stat().st_size, bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest())
(dest / 'package-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
