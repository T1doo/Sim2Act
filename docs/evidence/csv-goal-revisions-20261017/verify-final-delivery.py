from pathlib import Path
import gzip,hashlib,json,subprocess
root=Path('/workspace/Sim2Act'); evidence=root/'docs/evidence/csv-goal-revisions-20261017'
def git(*args): return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=root,text=True).strip()
head=git('rev-parse','HEAD'); branch=git('branch','--show-current')
actual={line.split()[1]:line.split()[0] for line in git('ls-remote','--heads','origin').splitlines()}
before={line.split()[1]:line.split()[0] for line in Path('/workspace/csv-goal-revision-evidence-20261017/remote-before.txt').read_text().splitlines()}
manifest=json.loads((evidence/'originals-manifest.json').read_text()); blockers=[]
for item in manifest:
    raw=(evidence/item['archive']).read_bytes()
    decoded=gzip.decompress(raw) if item['encoding']=='gzip' else raw
    if hashlib.sha256(raw).hexdigest()!=item['stored_sha256'] or hashlib.sha256(decoded).hexdigest()!=item['sha256']:
        blockers.append('archived original mismatch: '+item['archive'])
    p=Path(item['original'])
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
        blockers.append('original missing/changed: '+item['original'])
checksums=[]
for line in (evidence/'SHA256SUMS').read_text().splitlines():
    sha,path=line.split('  ',1)
    if hashlib.sha256((evidence/path).read_bytes()).hexdigest()!=sha: blockers.append('SHA entry mismatch: '+path)
    checksums.append(path)
expected_sums={str(p.relative_to(evidence)) for p in evidence.rglob('*') if p.is_file() and p!=evidence/'SHA256SUMS'}
if set(checksums)!=expected_sums: blockers.append('checksum index incomplete')
files=git('ls-files',str(evidence.relative_to(root))).splitlines()
expected={str(p.relative_to(root)) for p in evidence.rglob('*') if p.is_file()}
if set(files)!=expected: blockers.append('package file missing from Git')
for path in files:
    blob=subprocess.check_output(['git','-c','core.fsmonitor=false','show','HEAD:'+path],cwd=root)
    if blob!=(root/path).read_bytes(): blockers.append('Git blob mismatch: '+path)
inputs=json.loads(Path('/workspace/csv-goal-revision-evidence-20261017/author-b1b1b215/inputs-before.json').read_text())['files']
prod=[p for p in inputs if p.startswith('src/')]
for p in prod:
    if hashlib.sha256((root/p).read_bytes()).hexdigest()!=inputs[p]: blockers.append('production changed from tested b1: '+p)
changed={ref:(sha,actual.get(ref)) for ref,sha in before.items() if ref!='refs/heads/'+branch and actual.get(ref)!=sha}
if changed: blockers.append('baseline remote heads changed')
remote=actual.get('refs/heads/'+branch)
if remote!=head: blockers.append('remote target != local HEAD')
status=git('status','--porcelain=v1','--untracked-files=all')
if status: blockers.append('uncommitted/untracked files')
ancestor=subprocess.run(['git','-c','core.fsmonitor=false','merge-base','--is-ancestor','8fc70cc43a6ac81cd522249e8a3d367cd66c9238','HEAD'],cwd=root).returncode==0
if not ancestor: blockers.append('8fc ancestry missing')
report=dict(verification_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),head=head,branch=branch,remote_target_sha=remote,baseline_remote_heads=len(before),baseline_remote_changes=changed,main=actual.get('refs/heads/main'),actual_8fc_ancestor=ancestor,production_files_unchanged_from_b1=len(prod),originals_verified=len(manifest),package_git_blobs_verified=len(files),global_sha_entries_verified=len(checksums),status=status,unpushed_commits=int(git('rev-list','--count',remote+'..HEAD')) if remote else None,blockers=blockers)
Path('/workspace/csv-goal-revision-final-delivery-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(bool(blockers))
