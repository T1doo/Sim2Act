"""Three narrowly scoped cases; calibration FAIL never becomes product PASS."""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE='8bcafb0ce2735089f261748a385f16d127935fab'
assert os.environ['LIVE']=='0' and os.environ['SIM2ACT_LIVE_ENABLED']=='false'
assert os.environ['SIM2ACT_TEST_DATABASE_URL']=='postgresql+psycopg://sim2act_owned@/sim2act_owned?host=/tmp/sim2act-history-diagnostic-db/socket'
tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE],cwd=ROOT,text=True).splitlines()
paths=[p for p in tracked if p.startswith(('src/','tests/','schemas/','scripts/','.github/workflows/')) or p in {'pyproject.toml','requirements.lock','requirements-windows.lock'}]
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
before=hashes()
for p in paths:assert before[p]==hashlib.sha256(subprocess.check_output(['git','show',SOURCE+':'+p],cwd=ROOT)).hexdigest(),p
cases=[('normal-plan-validated','none','resources-plan'),('calibration-python','python_authorize_delay','resources-history'),('calibration-client-exit','client_exit_delay','resources-history')]
for name,fault,parameter in cases:
 assert not (OUT/(name+'-summary.json')).exists()
 node='tests/test_resources_project_lock.py::test_pg_resources_graph_share_project_first_lock['+parameter+']'
 env=dict(os.environ,PYTHONPATH=str(OUT),SIM2ACT_DIAGNOSTIC_OUT=str(OUT/name),SIM2ACT_DIAGNOSTIC_SOURCE=SOURCE,SIM2ACT_DIAGNOSTIC_FAULT=fault)
 base=Path('/tmp/sim2act-history-diagnostic-'+name)
 start=time.monotonic()
 with (OUT/(name+'.log')).open('w') as log:
  result=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','-p','diagnostic_plugin',node,'--basetemp='+str(base),'--junitxml='+str(OUT/(name+'.xml'))],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
 after=hashes();assert before==after
 summary={'source_sha':SOURCE,'node':node,'fault':fault,'calibration_only':fault!='none','returncode':result.returncode,'seconds':time.monotonic()-start,'source_unchanged':before==after,'plugin_sha256':hashlib.sha256((OUT/'diagnostic_plugin.py').read_bytes()).hexdigest(),'LIVE':0}
 (OUT/(name+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
 for p in base.rglob('resources-graph-pg-lock.json'):
  target=OUT/(name+'-proofs')/p.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 print(json.dumps(summary),flush=True)
 assert result.returncode==(0 if fault=='none' else 1)
(OUT/'source-provenance.json').write_text(json.dumps({'before':before,'after':hashes(),'source_sha':SOURCE},indent=2)+'\n')
