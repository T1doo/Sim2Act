import os,sys,pathlib,json,hashlib,subprocess,time,datetime
out=pathlib.Path(__file__).parent;snap=out/'snapshot';batch=sys.argv[1];folder=out/batch;folder.mkdir()
inputs=json.loads((out/'input-source.json').read_text())
def capture():
 rows=[]
 for r in inputs['inputs']:
  data=(snap/r['path']).read_bytes();rows.append(dict(path=r['path'],git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),size=len(data)))
 return dict(source_sha=inputs['source_sha'],inputs=rows,equals_git_input=rows==inputs['inputs'])
before=capture();assert before['equals_git_input'];(folder/'source-before.json').write_text(json.dumps(before,indent=2)+'\n')
selectors=json.loads((out/'selectors.json').read_text())[batch]
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q',*selectors,'--basetemp='+str(folder/'data'),'--junitxml='+str(folder/'junit.xml'),'-o','cache_dir='+str(folder/'pytest-cache')]
env=os.environ.copy();env.update(PYTHONPATH='src',NODE_PATH='/workspace/Sim2Act/scripts/engineering-ci/node_modules',PYTHONDONTWRITEBYTECODE='1');env.pop('SIM2ACT_TEST_DATABASE_URL',None)
(folder/'command.json').write_text(json.dumps(dict(argv=cmd,cwd=str(snap),environment_overrides={k:env[k]for k in ['PYTHONPATH','NODE_PATH','PYTHONDONTWRITEBYTECODE']},unset=['SIM2ACT_TEST_DATABASE_URL']),indent=2)+'\n')
started=time.time()
with(folder/'pytest.log').open('wb')as log:result=subprocess.run(cmd,cwd=snap,env=env,stdout=log,stderr=subprocess.STDOUT)
(folder/'terminal.json').write_text(json.dumps(dict(returncode=result.returncode,started_utc=datetime.datetime.fromtimestamp(started,datetime.timezone.utc).isoformat(),ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.time()-started),indent=2)+'\n')
after=capture();(folder/'source-after.json').write_text(json.dumps(after,indent=2)+'\n')
print(json.dumps(dict(batch=batch,returncode=result.returncode,input_count=len(after['inputs']),source_unchanged=after['equals_git_input'],wall_seconds=time.time()-started)))
sys.exit(result.returncode)
