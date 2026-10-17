import hashlib, io, json, os, subprocess, tarfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path('/workspace/Sim2Act')
SHA='8bbbd1f3b6d2d9ee6671aca4729883385087da1f'
GOLD='docs/evidence/bounded-agent-offline-20261006/independent-gold.json'
GIT=['git','-c','core.fsmonitor=false']
env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*args): return subprocess.check_output(GIT+list(args),cwd=REPO,env=env)
def dump(name,data): (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def digest(data): return hashlib.sha256(data).hexdigest()
actual=git('rev-parse','HEAD').decode().strip()
assert actual==SHA,actual
paths=['src','tests','schemas','pyproject.toml',GOLD]
index=[]
for row in git('ls-tree','-rz',SHA,'--',*paths).split(b'\0'):
 if not row:continue
 meta,path=row.split(b'\t',1);mode,kind,blob=meta.decode().split()
 assert kind=='blob'
 index.append(dict(path=path.decode(),git_blob=blob,mode=mode))
archive=git('archive',SHA,'--',*paths)
snapshot=ROOT/'snapshot';snapshot.mkdir()
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(snapshot,filter='data')
dep=snapshot/'scripts/engineering-ci/node_modules';dep.parent.mkdir(parents=True);dep.symlink_to('/workspace/Sim2Act/scripts/engineering-ci/node_modules',target_is_directory=True)
def inputs(base):
 result=[]
 for item in index:
  data=(base/item['path']).read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  result.append(dict(item,sha256=digest(data),bytes=len(data),matches_git=blob==item['git_blob']))
 return result
before=inputs(snapshot)
assert all(i['matches_git'] for i in before)
shared_before=inputs(REPO);assert before==shared_before
source=dict(source_sha=SHA,archive_sha256=digest(archive),count=len(before),inputs=before)
dump('source-before.json',source)
dump('shared-source-before.json',dict(head=actual,count=len(shared_before),inputs=shared_before))
args=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','tests/test_csv_goal_revisions.py::test_visible_same_goal_revision_check_release_adopt_and_new_run[deliver]','--basetemp='+str(ROOT/'data'),'--junitxml='+str(ROOT/'junit.xml'),'-o','cache_dir='+str(ROOT/'pytest-cache')]
testenv=dict(env,PYTHONPATH=str(snapshot/'src'),NODE_PATH='/workspace/Sim2Act/scripts/engineering-ci/node_modules',PYTHONDONTWRITEBYTECODE='1')
removed='SIM2ACT_TEST_DATABASE_URL' in testenv
testenv.pop('SIM2ACT_TEST_DATABASE_URL',None)
dump('command.json',dict(argv=args,cwd=str(snapshot),environment={'PYTHONPATH':str(snapshot/'src'),'NODE_PATH':testenv['NODE_PATH'],'PYTHONDONTWRITEBYTECODE':'1','GIT_OPTIONAL_LOCKS':'0','SIM2ACT_TEST_DATABASE_URL':'UNSET'},database_env_was_present=removed,automatic_retries=0,source_sha=SHA))
print('SOURCE',SHA,'INPUTS',len(before),flush=True)
start=time.time()
with (ROOT/'pytest.log').open('wb') as log:
 process=subprocess.Popen(args,cwd=snapshot,env=testenv,stdout=log,stderr=subprocess.STDOUT)
 code=process.wait()
terminal=dict(returncode=code,wall_seconds=time.time()-start,source_sha=SHA)
dump('terminal.json',terminal)
after=inputs(snapshot)
dump('source-after.json',dict(source_sha=SHA,count=len(after),equal_to_before=after==before,all_match_git=all(i['matches_git'] for i in after),inputs=after))
shared_after=inputs(REPO)
dump('shared-source-after.json',dict(head=git('rev-parse','HEAD').decode().strip(),count=len(shared_after),equal_to_frozen=shared_after==before,inputs=shared_after))
print(json.dumps(terminal),flush=True)
print('INPUTS_UNCHANGED',after==before,'ROOT_INPUTS_UNCHANGED',shared_after==before,flush=True)
raise SystemExit(code)
