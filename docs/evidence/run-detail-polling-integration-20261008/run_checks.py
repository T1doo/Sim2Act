"""Recheck original page aggregate and read recovery on exact reviewed bytes."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE='8bcafb0ce2735089f261748a385f16d127935fab'
REVIEWED='3fe824b826df6f1040989ddb5f821290dfc33e4b'
backend=sys.argv[1]
assert backend in {'sqlite','pg'}
assert os.environ['LIVE']=='0' and os.environ['SIM2ACT_LIVE_ENABLED']=='false'
assert bool(os.environ.get('SIM2ACT_TEST_DATABASE_URL'))==(backend=='pg')
assert not (OUT/(backend+'-summary.json')).exists()
selected=['tests/test_run_detail_polling.py','tests/test_natural_goal_ui.py::test_natural_goal_actual_http_ui[valid]','tests/test_product_integration.py','tests/test_background_poll.py','tests/test_task_read_failure.py']
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',REVIEWED],cwd=ROOT,text=True).splitlines()
paths=[p for p in paths if p.startswith(('src/','tests/','schemas/','scripts/','.github/workflows/')) or p in {'pyproject.toml','requirements.lock','requirements-windows.lock'}]
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
before=hashes()
for p in paths:assert before[p]==hashlib.sha256(subprocess.check_output(['git','show',REVIEWED+':'+p],cwd=ROOT)).hexdigest(),p
python=str(ROOT/'.venv/bin/python')
collection=subprocess.run([python,'-m','pytest','--collect-only','-q',*selected],cwd=ROOT,capture_output=True,text=True)
(OUT/(backend+'-collection.log')).write_text(collection.stdout+collection.stderr);assert collection.returncode==0
nodes=[s for s in collection.stdout.splitlines() if s.startswith('tests/') and '::' in s];assert len(nodes)==len(set(nodes))
(OUT/(backend+'-collection.json')).write_text(json.dumps(nodes,indent=2)+'\n')
base=Path('/tmp/sim2act-polling-integration-'+backend);xml=OUT/(backend+'.xml');start=time.monotonic()
with (OUT/(backend+'.log')).open('w') as log:
 result=subprocess.run([python,'-m','pytest','-q','-ra',*selected,'--basetemp='+str(base),'--junitxml='+str(xml)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
after=hashes();assert before==after
suite=ET.parse(xml).getroot().find('testsuite');assert suite is not None
summary={'integrated_source_sha':SOURCE,'reviewed_product_sha':REVIEWED,'collection':len(nodes),'seconds':time.monotonic()-start,'returncode':result.returncode,'source_matches_reviewed':True,'source_unchanged':before==after,'backend':backend,'LIVE':0}
for key in ['tests','failures','errors','skipped']:summary[key]=int(suite.attrib[key])
summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped'];assert summary['tests']==len(nodes)
(OUT/(backend+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n');(OUT/(backend+'-provenance.json')).write_text(json.dumps({'before':before,'after':after,'summary':summary},indent=2)+'\n')
for p in base.rglob('*'):
 if p.is_file() and p.name in {'results.json','failure.json','driver.log'}:
  target=OUT/(backend+'-proofs')/p.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
print(json.dumps(summary),flush=True);sys.exit(result.returncode)
