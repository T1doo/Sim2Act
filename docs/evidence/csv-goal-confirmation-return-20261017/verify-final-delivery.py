import gzip,hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/Sim2Act'); package=root/'docs/evidence/csv-goal-confirmation-return-20261017'
raw=Path('/workspace/csv-goal-confirmation-return-evidence-20261017')
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,text=True).strip()
def refs(text):return {ref:sha for sha,ref in (line.split() for line in text.splitlines() if line.strip())}
def h(data):return hashlib.sha256(data).hexdigest()
head=git('rev-parse','HEAD');branch=git('branch','--show-current')
assert branch=='dev/csv-goal-confirmation-return-20261017'
assert git('status','--porcelain')==''
before=refs((raw/'remote-before.txt').read_text());after=refs(git('ls-remote','--heads','origin'))
assert after['refs/heads/'+branch]==head
changes={ref:dict(before=sha,after=after.get(ref)) for ref,sha in before.items() if after.get(ref)!=sha}
assert not changes,changes
assert subprocess.run(['git','-c','core.fsmonitor=false','merge-base','--is-ancestor','8fc70cc43a6ac81cd522249e8a3d367cd66c9238','HEAD'],cwd=root).returncode==0
manifest=json.loads((package/'ORIGINALS.json').read_text())
for x in manifest:
 data=(package/x['saved']).read_bytes();assert h(data)==x['stored_sha256']
 if x['encoding']=='gzip':data=gzip.decompress(data)
 assert len(data)==x['bytes'] and h(data)==x['sha256']
covered=set()
for line in (package/'SHA256SUMS').read_text().splitlines():
 sha,p=line.split('  ',1);assert h((package/p).read_bytes())==sha;covered.add(p)
actual={str(p.relative_to(package)) for p in package.rglob('*') if p.is_file() and p!=package/'SHA256SUMS'}
assert actual==covered,(actual-covered,covered-actual)
tracked=git('ls-files','docs/evidence/csv-goal-confirmation-return-20261017').splitlines()
assert len(tracked)==len(actual)+1
last=json.loads((raw/'author-refined-849a931f/inputs-after.json').read_text())['files']
assert all(h((root/p).read_bytes())==sha for p,sha in last.items())
report=dict(status='PASS_BOUNDED',branch=branch,local_head=head,remote_head=after['refs/heads/'+branch],baseline_remote_heads=len(before),baseline_remote_changes=changes,main_before=before['refs/heads/main'],main_after=after['refs/heads/main'],originals_verified=len(manifest),sqlite_copies=sum(Path(x['original']).suffix in ('.db','.sqlite','.sqlite3') for x in manifest),global_checksums_verified=len(covered),package_git_files=len(tracked),current_inputs_matching849=len(last),working_tree_clean=True,unpushed_commit_difference=0,uncommitted_difference=0,blockers=[])
(raw/'final-delivery-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
