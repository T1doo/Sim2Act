import hashlib,json,os,subprocess,time
from pathlib import Path
repo=Path('/workspace/Sim2Act');draft=Path('/tmp/csv-continuous-upgrade-draft-20261017');raw=Path('/workspace/csv-continuous-column-evidence-20261017')
base='d74f2fed55b6067e5d3c34ca6e4348b92e75f48a';branch='dev/csv-continuous-upgrade-review-20261017'
index=Path('/tmp/csv-continuous-upgrade-freeze-'+str(time.time_ns())+'.index');assert not index.exists()
env={**os.environ,'GIT_INDEX_FILE':str(index)}
def git(*args,data=None):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo,env=env,input=data).decode().strip()
assert git('rev-parse','HEAD')==base
assert subprocess.check_output(['git','-c','core.fsmonitor=false','status','--porcelain'],cwd=repo).decode().strip()==''
git('read-tree',base);overlays={}
for p in sorted(draft.rglob('*')):
 if p.is_file() and p.suffix in ('.py','.js','.cjs'):
  rel=str(p.relative_to(draft));data=p.read_bytes();blob=git('hash-object','-w','--stdin',data=data)
  git('update-index','--add','--cacheinfo','100644',blob,rel);overlays[rel]=dict(blob=blob,sha256=hashlib.sha256(data).hexdigest())
tree=git('write-tree');sha=git('commit-tree',tree,'-p',base,data=b'Recover an existing CSV graph anchor through its exact derive receipt\n\nRead current anchors without mutation, derive only the exact stale-baseline conflict, and recover a lost accepted derive by its original key.\n')
git('update-ref','refs/heads/'+branch,sha,'0'*40)
assert git('rev-parse','HEAD')==base
assert subprocess.check_output(['git','-c','core.fsmonitor=false','status','--porcelain'],cwd=repo).decode().strip()==''
report=dict(base_sha=base,frozen_sha=sha,local_review_branch=branch,index=str(index),tree=tree,overlay=overlays,current_checkout_unchanged=True)
(raw/'isolated-upgrade-freeze.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
