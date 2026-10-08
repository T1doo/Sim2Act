"""Frozen default testpaths, sequential backends and immutable first-round evidence."""
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
SOURCE='42b7a992524d9f2e00136711c70cb4e16f3e419b'
backend=sys.argv[1]
assert backend in {'sqlite','pg'}
assert os.environ['LIVE']=='0' and os.environ['SIM2ACT_LIVE_ENABLED']=='false'
assert bool(os.environ.get('SIM2ACT_TEST_DATABASE_URL'))==(backend=='pg')
assert not (OUT/(backend+'-summary.json')).exists(),'Never overwrite first-round evidence'
python=ROOT/'.venv/bin/python'
basetemp='/tmp/sim2act-convergence-first-'+backend
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',SOURCE],cwd=ROOT,text=True).splitlines()
selected=[p for p in paths if p.startswith(('src/','tests/','schemas/','scripts/','.github/workflows/')) or p in {'pyproject.toml','requirements.lock','requirements-windows.lock'}]
def hashes():return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in selected}
before=hashes()
for p in selected:
 original=subprocess.check_output(['git','show',SOURCE+':'+p],cwd=ROOT)
 assert hashlib.sha256(original).hexdigest()==before[p],p
collection=subprocess.run([str(python),'-m','pytest','--collect-only','-q'],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(OUT/(backend+'-collection.log')).write_text(collection.stdout)
assert collection.returncode==0
nodes=[s for s in collection.stdout.splitlines() if s.startswith('tests/') and '::' in s]
assert nodes==json.loads((OUT/'initial-collection.json').read_text()) and len(nodes)==len(set(nodes))==2051
(OUT/(backend+'-collection.json')).write_text(json.dumps(nodes,indent=2)+'\n')
xml=OUT/(backend+'-first.xml')
start=time.monotonic()
with (OUT/(backend+'-first.log')).open('w') as log:
 result=subprocess.run([str(python),'-m','pytest','-q','-ra','--basetemp='+basetemp,'--junitxml='+str(xml)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
seconds=time.monotonic()-start
after=hashes()
suite=ET.parse(xml).getroot().find('testsuite')
assert suite is not None
cases=suite.findall('testcase')
problems=[]
for case in cases:
 for tag in ['failure','error','skipped']:
  entry=case.find(tag)
  if entry is not None:problems.append(dict(classname=case.attrib.get('classname'),name=case.attrib.get('name'),kind=tag,message=entry.attrib.get('message'),detail=entry.text))
summary=dict(source_sha=SOURCE,backend=backend,tests=int(suite.attrib['tests']),collection=len(nodes),failures=int(suite.attrib['failures']),errors=int(suite.attrib['errors']),skipped=int(suite.attrib['skipped']),seconds=seconds,returncode=result.returncode,source_unchanged=before==after,LIVE=0,native_windows='NOT_RUN',native_edge='NOT_RUN',CI='NOT_RUN')
summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
(OUT/(backend+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
(OUT/(backend+'-problems.json')).write_text(json.dumps(problems,ensure_ascii=False,indent=2)+'\n')
(OUT/(backend+'-provenance.json')).write_text(json.dumps(dict(before=before,after=after,summary=summary),indent=2)+'\n')
for p in Path(basetemp).rglob('*'):
 if p.is_file() and p.name in {'results.json','driver.log','failure.json','upgrade-proof.json'}:
  target=OUT/(backend+'-actual-proofs')/p.relative_to(basetemp);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
assert before==after and summary['tests']==len(nodes)
print(json.dumps(summary),flush=True)
sys.exit(result.returncode)
