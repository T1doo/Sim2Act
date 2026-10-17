import hashlib,json,os,subprocess,sys,time
from pathlib import Path
repo=Path('/workspace/Sim2Act');root=Path('/workspace/csv-confirm-workspace-evidence-20261017')/sys.argv[1];root.mkdir()
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo)
def manifest():
 return {n:{'sha256':hashlib.sha256((repo/n).read_bytes()).hexdigest(),'git_sha256':hashlib.sha256(git('show','HEAD:'+n)).hexdigest()} for n in git('ls-files','src','tests').decode().splitlines()}
head=git('rev-parse','HEAD').decode().strip();before=manifest();(root/'source-before.json').write_text(json.dumps(dict(head=head,files=before),indent=2)+'\n')
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q',*sys.argv[2:],'--basetemp='+str(root/'data'),'--junitxml='+str(root/'junit.xml'),'-o','cache_dir='+str(root/'pytest-cache')]
start=time.time()
with (root/'pytest.log').open('wb') as f:r=subprocess.run(cmd,cwd=repo,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'NODE_PATH':str(repo/'scripts/engineering-ci/node_modules')})
(root/'command.json').write_text(json.dumps(dict(argv=cmd,returncode=r.returncode,seconds=time.time()-start,source=head),indent=2)+'\n')
after=manifest();(root/'source-after.json').write_text(json.dumps(dict(head=git('rev-parse','HEAD').decode().strip(),files=after),indent=2)+'\n');assert before==after and head==git('rev-parse','HEAD').decode().strip() and all(v['sha256']==v['git_sha256'] for v in after.values())
(root/'source-verification.json').write_text(json.dumps(dict(source=head,files=len(after),git_bytes_equal=True,before_after_equal=True,clean_worktree=not git('status','--porcelain').strip()),indent=2)+'\n')
print(json.dumps(dict(source=head,returncode=r.returncode,files=len(after),seconds=time.time()-start)),flush=True)
sys.exit(r.returncode)
