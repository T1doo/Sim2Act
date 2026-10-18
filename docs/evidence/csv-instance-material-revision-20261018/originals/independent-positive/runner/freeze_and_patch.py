import hashlib
import io
import json
import pathlib
import subprocess
import tarfile

BASE = pathlib.Path('/tmp/csv-material-independent-positive-805-20261018')
SOURCE = BASE / 'source'
EVIDENCE = BASE / 'evidence'
REPO = pathlib.Path('/workspace/Sim2Act')
SHA = '805afe60cdd94d6d4679e0da9c1f7fde752f67d2'
PATHS = ['src', 'tests', 'schemas', 'pyproject.toml', 'docs/evidence/bounded-agent-offline-20261006']


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=REPO)


def write(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


tar = git('archive', '--format=tar', SHA, '--', *PATHS)
(EVIDENCE / 'original-frozen-inputs.tar').write_bytes(tar)
with tarfile.open(fileobj=io.BytesIO(tar)) as archived:
    archived.extractall(SOURCE, filter='data')

entries = []
for line in git('ls-tree', '-r', '-z', SHA, '--', *PATHS).split(b'\0'):
    if not line:
        continue
    metadata, raw_path = line.split(b'\t', 1)
    mode, kind, blob = metadata.decode().split()
    path = raw_path.decode()
    data = (SOURCE / path).read_bytes()
    actual_blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert kind == 'blob' and actual_blob == blob, path
    entries.append(dict(path=path, git_mode=mode, git_blob=blob,
        sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
write('frozen-inputs-before.json', dict(product_commit=SHA, archive_sha256=hashlib.sha256(tar).hexdigest(),
    paths=PATHS, file_count=len(entries), files=entries))

original_patch = pathlib.Path('/tmp/csv-material-acceptance-20261018/cached-assertion-only.patch').read_bytes()
(EVIDENCE / 'cached-assertion-original.patch').write_bytes(original_patch)
lines = original_patch.decode().splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith('diff --git '):
        lines[i] = 'diff --git a/tests/test_csv_material_revisions.py b/tests/test_csv_material_revisions.py\n'
    elif line.startswith('--- '):
        lines[i] = '--- a/tests/test_csv_material_revisions.py\n'
    elif line.startswith('+++ '):
        lines[i] = '+++ b/tests/test_csv_material_revisions.py\n'
patch = ''.join(lines).encode()
adapted = EVIDENCE / 'cached-assertion-applied.patch'
adapted.write_bytes(patch)
applied = subprocess.run(['git', 'apply', '--no-index', '--check', str(adapted)], cwd=SOURCE,
    capture_output=True, text=True)
assert applied.returncode == 0, applied.stderr
applied = subprocess.run(['git', 'apply', '--no-index', str(adapted)], cwd=SOURCE,
    capture_output=True, text=True)
assert applied.returncode == 0, applied.stderr
changes = []
for entry in entries:
    data = (SOURCE / entry['path']).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry['sha256']:
        changes.append(dict(path=entry['path'], original_sha256=entry['sha256'], applied_sha256=digest))
assert [item['path'] for item in changes] == ['tests/test_csv_material_revisions.py'], changes
write('observer-patch-proof.json', dict(product_commit=SHA,
    original_patch_sha256=hashlib.sha256(original_patch).hexdigest(),
    applied_patch_sha256=hashlib.sha256(patch).hexdigest(),
    patch_modification='Only patch path headers changed for the isolated snapshot; the hunk is byte-identical.',
    changes=changes, product_source_changes=0, check_output=applied.stdout + applied.stderr,
    tests_executed=0))
