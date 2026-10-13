from pathlib import Path
import os,subprocess,time,json
r=Path(__file__).resolve().parent;repo=Path('/workspace/Sim2Act-pa-provider');args=['/workspace/Sim2Act/.venv/bin/python','-m','pytest',str(r/'probes/test_independent_raw_response_scope.py'),'-q','--basetemp='+str(r/'extra-fixtures'),'-o','cache_dir='+str(r/'extra-cache'),'--junitxml='+str(r/'extra.xml')]
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'src')+':'+str(repo/'tests'),NODE_PATH='/workspace/node-tools/node_modules');start=time.time()
(r/'extra-command.json').write_text(json.dumps({'args':args,'cwd':str(repo),'started_at':start},indent=2)+'\n')
with (r/'extra.stdout').open('w') as out,(r/'extra.stderr').open('w') as err:p=subprocess.run(args,cwd=repo,env=env,stdout=out,stderr=err)
data={'returncode':p.returncode,'started_at':start,'ended_at':time.time(),'wall_seconds':time.time()-start,'args':args};(r/'extra-exit.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data));raise SystemExit(p.returncode)
