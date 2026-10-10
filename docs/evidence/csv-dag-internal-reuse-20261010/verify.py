"""Read-only exact frozen source and imported raw evidence verification."""
from pathlib import Path
import hashlib, json, subprocess, sys

root=Path(__file__).resolve().parent
freeze=json.loads((root/'source-freeze.json').read_text())
ref=sys.argv[1] if len(sys.argv)>1 else 'HEAD'
def sha(data):return hashlib.sha256(data).hexdigest()
def blob(path):return subprocess.check_output(['git','show',(':'+path if ref=='index' else ref+':'+path)])
for p,h in freeze['files'].items():
    assert sha(Path(p).read_bytes())==h==sha(blob(p)),p
receipt=json.loads((root/'copy-receipt.json').read_text())
for item in receipt['files']:
    p=root/item['path'];relative=str(p.relative_to(Path.cwd()))
    assert sha(p.read_bytes())==item['sha256']==sha(blob(relative)),relative
for directory in ('independent-807','independent-delta'):
    white=json.loads((root/directory/'COPY_WHITELIST.json').read_text())
    for item in white['files']:
        assert sha((root/directory/item['path']).read_bytes())==item['sha256']
gitdir=Path(subprocess.check_output(['git','rev-parse','--absolute-git-dir'],text=True).strip())
pending=[name for name in ('MERGE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','BISECT_LOG','rebase-merge','rebase-apply','sequencer') if (gitdir/name).exists()]
locks={str(p.relative_to(gitdir)):p.stat().st_size for p in gitdir.rglob('*.lock')}
assert not pending and all(k=='codex-index-refresh.lock' and v==0 for k,v in locks.items()),(pending,locks)
result=dict(reference=ref,source_freeze=freeze['source_sha'],source_files=len(freeze['files']),raw_evidence_files=len(receipt['files']),
    source_worktree_and_git_bytes_match=True,raw_evidence_worktree_and_git_bytes_match=True,independent_whitelists_match=True,pending_operations=pending,locks=locks)
print(json.dumps(result,indent=2))
