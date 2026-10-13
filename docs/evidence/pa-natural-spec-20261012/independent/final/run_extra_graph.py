from pathlib import Path
import subprocess,os,json,time
p=Path(__file__).resolve().parent;repo=Path('/workspace/Sim2Act-pa-provider');args=['/workspace/Sim2Act/.venv/bin/python','-m','pytest',str(p/'probes/test_independent_passing_graph.py'),'-q','--basetemp='+str(p/'extra-graph-fixtures'),'-o','cache_dir='+str(p/'extra-graph-cache'),'--junitxml='+str(p/'extra-graph.xml')]
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'src')+':'+str(repo/'tests'),NODE_PATH='/workspace/node-tools/node_modules')
start=time.time();(p/'extra-graph-command.json').write_text(json.dumps({'args':args,'cwd':str(repo),'started_at':start},indent=2)+'\n')
with (p/'extra-graph.stdout').open('w') as out,(p/'extra-graph.stderr').open('w') as err:r=subprocess.run(args,cwd=repo,env=env,stdout=out,stderr=err)
d={'returncode':r.returncode,'started_at':start,'ended_at':time.time(),'wall_seconds':time.time()-start,'args':args};(p/'extra-graph-exit.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d));raise SystemExit(r.returncode)
