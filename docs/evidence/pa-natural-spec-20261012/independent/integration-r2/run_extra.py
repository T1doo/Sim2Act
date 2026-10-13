from pathlib import Path
import os,subprocess,time,json
p=Path(__file__).resolve().parent;repo=Path('/workspace/Sim2Act-pa-provider');args=['/workspace/Sim2Act/.venv/bin/python','-m','pytest',str(p/'probes/test_independent_queue_cancel_cas.py'),'-q','--basetemp='+str(p/'extra-fixtures'),'-o','cache_dir='+str(p/'extra-cache'),'--junitxml='+str(p/'extra.xml')]
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'src')+':'+str(repo/'tests'),NODE_PATH='/workspace/node-tools/node_modules')
start=time.time();(p/'extra-command.json').write_text(json.dumps({'args':args,'cwd':str(repo),'started_at':start},indent=2)+'\n')
with (p/'extra.stdout').open('w') as o,(p/'extra.stderr').open('w') as e:done=subprocess.run(args,cwd=repo,env=env,stdout=o,stderr=e)
r={'returncode':done.returncode,'started_at':start,'ended_at':time.time(),'wall_seconds':time.time()-start,'args':args};(p/'extra-exit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(done.returncode)
