import datetime
import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/workspace/Sim2Act')
out = Path('/workspace/pb-extraction-close-final-delivery-20261018')
out.mkdir(exist_ok=True)

def git(*args, text=True):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=root, text=text)

head = git('rev-parse', 'HEAD').strip()
source = json.loads(Path('/workspace/pb-extraction-close-evidence-20261018/qualified-execution-inputs-before.json').read_text())['head']
branch = git('branch', '--show-current').strip()
assert branch == 'dev/pb-extraction-close-20261018'
assert not git('status', '--porcelain=v1', '--untracked-files=all')
heads = git('ls-remote', '--heads', 'origin')
(out / 'remote-heads.txt').write_text(heads)
remote = {line.split()[1]: line.split()[0] for line in heads.splitlines()}
assert remote['refs/heads/' + branch] == head
assert git('rev-list', '--left-right', '--count', 'HEAD...@{upstream}').strip() == '0\t0'
assert not git('rev-list', '@{upstream}..HEAD').strip()
for ancestor in ['8fc70cc43a6ac81cd522249e8a3d367cd66c9238',
    '3d1a3160fda6e9bfead96fae8a40935617270da4', source]:
    git('merge-base', '--is-ancestor', ancestor, 'HEAD')
changed = git('diff', '--name-only', source, 'HEAD').splitlines()
assert changed and all(name.startswith('docs/') for name in changed)
evidence = root / 'docs/evidence/pb-extraction-close-20261018'
paths = sorted(path for path in evidence.rglob('*') if path.is_file())
checksums = (evidence / 'SHA256SUMS').read_text().splitlines()
assert len(checksums) + 1 == len(paths)
for line in checksums:
    digest, name = line.split('  ', 1)
    assert hashlib.sha256((evidence / name).read_bytes()).hexdigest() == digest
process = subprocess.Popen(['git', '-c', 'core.fsmonitor=false', 'cat-file', '--batch'], cwd=root,
    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
try:
    for path in paths:
        name = str(path.relative_to(root))
        process.stdin.write(('HEAD:' + name + '\n').encode())
        process.stdin.flush()
        header = process.stdout.readline().decode().strip().split()
        assert len(header) == 3 and header[1] == 'blob', (name, header)
        blob = process.stdout.read(int(header[2]))
        assert process.stdout.read(1) == b'\n'
        assert blob == path.read_bytes(), name
finally:
    process.stdin.close()
    process.stdout.close()
    assert process.wait(timeout=20) == 0
subprocess.run(['/workspace/sim2act-venv/bin/python', '/workspace/pb-cold-inputs-20261018.py',
    str(out / 'final-inputs.json')], cwd=root, check=True, capture_output=True)
executed = json.loads(Path('/workspace/pb-extraction-close-evidence-20261018/qualified-execution-inputs-after.json').read_text())
delivered = json.loads((out / 'final-inputs.json').read_text())
assert executed['inputs'] == delivered['inputs']
initial = {line.split()[1]: line.split()[0] for line in
    Path('/workspace/pb-extraction-close-evidence-20261018/remote-heads-phase-start.txt').read_text().splitlines()}
other_changes = {ref: dict(before=initial.get(ref), after=remote.get(ref))
    for ref in set(initial) | set(remote) if ref != 'refs/heads/' + branch and initial.get(ref) != remote.get(ref)}
result = dict(time_utc=datetime.datetime.now(datetime.UTC).isoformat(), final_head=head,
    execution_source=source, branch=branch,
    own_remote_head=remote['refs/heads/' + branch], clean=True, ahead=0, behind=0,
    unpushed_commits=0, execution_inputs=delivered['input_count'], production_inputs=delivered['production_count'],
    input_byte_drift_since_execution=0, post_execution_changed_files=len(changed), post_execution_docs_only=True,
    evidence_files_git_blob_verified=len(paths), evidence_checksums_verified=len(checksums),
    remote_heads_before=len(initial), remote_heads_after=len(remote), other_remote_head_changes=other_changes,
    package=json.loads((evidence / 'package-summary.json').read_text()))
(out / 'final-delivery-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
