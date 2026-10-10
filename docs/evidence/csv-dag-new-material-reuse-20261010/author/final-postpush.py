import subprocess,json,hashlib
from pathlib import Path
r=Path('/tmp/sim2act-dag-new-csv-20261010');repo=Path('/workspace/Sim2Act');source='709e0978c15236ed86bafc095d4cdf1301ad756c';main='6f688e4dd80b5c81d41aecde90e360d3629f9c21'
def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
head=git('rev-parse','HEAD');branch=git('branch','--show-current');assert branch=='dev/f1-foundation'
remote=git('ls-remote','origin','refs/heads/dev/f1-foundation','refs/heads/dev/csv-new-material-reuse-20261010','refs/heads/main');refs={line.split()[1]:line.split()[0] for line in remote.splitlines()}
assert refs=={'refs/heads/dev/f1-foundation':head,'refs/heads/dev/csv-new-material-reuse-20261010':source,'refs/heads/main':main}
assert git('rev-parse','origin/dev/f1-foundation')==head and git('rev-parse','origin/dev/csv-new-material-reuse-20261010')==source
subprocess.run(['git','merge-base','--is-ancestor',source,head],cwd=repo,check=True)
changes=git('diff','--name-only',source,head).splitlines();assert changes and all(p.startswith('docs/') for p in changes)
freeze=json.loads((r/'source-freeze-complete-readback.json').read_text())
for f in freeze['files']:
    b=(repo/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
    assert subprocess.check_output(['git','show',head+':'+f['path']],cwd=repo)==b
assert not git('status','--porcelain')
counts=git('rev-list','--left-right','--count','origin/dev/f1-foundation...HEAD');assert counts=='0\t0'
out=repo/'docs/evidence/csv-dag-new-material-reuse-20261010';w=json.loads((out/'COPY_WHITELIST.json').read_text())
for f in w['files']:
    path=str((out/f['path']).relative_to(repo));b=(repo/path).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'];assert subprocess.check_output(['git','show',head+':'+path],cwd=repo)==b
default=git('ls-remote','--symref','origin','HEAD');assert 'refs/heads/main' in default and main in default
result=dict(source_sha=source,final_dev_sha=head,branch=branch,remote_refs=refs,default_HEAD=default,source_ancestor_of_final=True,evidence_docs_only=True,non_docs373_and_src70_preserved=True,main_unchanged=True,local_worktree_clean=True,unpublished_commits=0,behind_commits=0,artifact_files=len(w['files']),artifact_bytes=w['bytes'],artifact_sha256=hashlib.sha256((out/'COPY_WHITELIST.json').read_bytes()).hexdigest(),all_artifacts_Git_worktree_exact=True,known_lock='.git/codex-index-refresh.lock0bytes retained',PROJECT='PENDING/BLOCKED_PARTIAL',overall='NOT_ACCEPTED',LIVE=0)
(r/'final-postpush-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
