"""Sequential, source-hashed follow-up; never overwrite any first round."""
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
SOURCE=subprocess.check_output(['git','rev-parse','3fe824b'],cwd=ROOT,text=True).strip()
backend=sys.argv[1]
assert backend in {'sqlite','pg'}
assert os.environ['LIVE']=='0' and os.environ['SIM2ACT_LIVE_ENABLED']=='false'
assert bool(os.environ.get('SIM2ACT_TEST_DATABASE_URL'))==(backend=='pg')
assert not (OUT/(backend+'-target-summary.json')).exists()
base=json.loads((OUT/'fix-selection-files.json').read_text())
extra=['tests/test_background_poll.py','tests/test_task_read_failure.py','tests/test_application_use.py','tests/test_natural_receipt_candidate.py','tests/test_natural_ui_drain.py','tests/test_product_integration_fixture.py','tests/test_agent_ui_replay.py','tests/test_run_detail_polling.py']
files=sorted(set(extra if backend=='sqlite' else base+extra))
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE],cwd=ROOT,text=True).splitlines()
selected=[p for p in paths if p.startswith(('src/','tests/','schemas/','scripts/','.github/workflows/')) or p in {'pyproject.toml','requirements.lock','requirements-windows.lock'}]
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in selected}
before=hashes()
for p in selected:
 assert before[p]==hashlib.sha256(subprocess.check_output(['git','show',SOURCE+':'+p],cwd=ROOT)).hexdigest(),p
python=str(ROOT/'.venv/bin/python')
collection=subprocess.run([python,'-m','pytest','--collect-only','-q',*files],cwd=ROOT,capture_output=True,text=True)
(OUT/(backend+'-target-collection.log')).write_text(collection.stdout+collection.stderr)
assert collection.returncode==0
nodes=[s for s in collection.stdout.splitlines() if s.startswith('tests/') and '::' in s]
assert len(nodes)==len(set(nodes))
(OUT/(backend+'-target-collection.json')).write_text(json.dumps(nodes,indent=2)+'\n')
xml=OUT/(backend+'-target.xml')
tmp=Path('/tmp/sim2act-convergence-target-'+backend)
start=time.monotonic()
with (OUT/(backend+'-target.log')).open('w') as log:
 result=subprocess.run([python,'-m','pytest','-q','-ra',*files,'--basetemp='+str(tmp),'--junitxml='+str(xml)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
seconds=time.monotonic()-start
after=hashes();assert before==after
suite=ET.parse(xml).getroot().find('testsuite');assert suite is not None
summary={'source_sha':SOURCE,'backend':backend,'selection':files,'collection':len(nodes),'seconds':seconds,'returncode':result.returncode,'source_unchanged':before==after,'LIVE':0}
for key in ['tests','failures','errors','skipped']:summary[key]=int(suite.attrib[key])
summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
assert summary['tests']==len(nodes)
(OUT/(backend+'-target-summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
(OUT/(backend+'-target-provenance.json')).write_text(json.dumps({'before':before,'after':after,'summary':summary},indent=2)+'\n')
for p in tmp.rglob('*'):
 if p.is_file() and p.name in {'results.json','failure.json','driver.log'}:
  target=OUT/(backend+'-target-proofs')/p.relative_to(tmp);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
print(json.dumps(summary),flush=True)
sys.exit(result.returncode)
