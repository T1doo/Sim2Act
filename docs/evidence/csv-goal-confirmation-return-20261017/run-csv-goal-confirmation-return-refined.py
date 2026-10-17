import hashlib,json,os,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path('/workspace/Sim2Act')
out=Path('/workspace/csv-goal-confirmation-return-evidence-20261017/author-refined-849a931f');out.mkdir(exist_ok=True)
sha=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=root,text=True).strip()
assert sha=='849a931f7dbb8926ca9cbe166c3cfba3527dbf0a'
files=subprocess.check_output(['git','-c','core.fsmonitor=false','ls-files','src','tests','schemas','pyproject.toml','scripts/engineering-ci/package.json','scripts/engineering-ci/package-lock.json'],cwd=root,text=True).splitlines()
def hashes():return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
before=hashes();(out/'inputs-before.json').write_text(json.dumps(dict(source_sha=sha,files=before),indent=2))
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','tests/test_csv_goal_revisions.py::test_visible_same_goal_revision_check_release_adopt_and_new_run[return-adoption]','-o','tmp_path_retention_policy=all','-o','tmp_path_retention_count=99','--basetemp=/tmp/csv-goal-confirmation-return-author-refined-849a931f-20261017','--junitxml='+str(out/'junit.xml')]
(out/'command.json').write_text(json.dumps(dict(source_sha=sha,command=cmd,scope='One test-oracle correction rerun; production unchanged from776, not all21 rerun.'),indent=2))
env={**os.environ,'NODE_PATH':str(root/'scripts/engineering-ci/node_modules'),'PYTHONPATH':str(root/'src')};env.pop('SIM2ACT_TEST_DATABASE_URL',None)
start=time.time()
with (out/'pytest.log').open('w') as log:r=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,env=env)
after=hashes();(out/'inputs-after.json').write_text(json.dumps(dict(source_sha=sha,files=after),indent=2))
cases=[dict(c.attrib,failures=[f.text for f in c.findall('failure')],errors=[f.text for f in c.findall('error')],skipped=bool(c.findall('skipped'))) for c in ET.parse(out/'junit.xml').iter('testcase')]
value=dict(source_sha=sha,returncode=r.returncode,wall_seconds=time.time()-start,source_inputs=len(files),source_unchanged=before==after,actual_executions=len(cases),cases=cases)
(out/'report.json').write_text(json.dumps(value,ensure_ascii=False,indent=2));print(json.dumps(value,ensure_ascii=False,indent=2),flush=True)
raise SystemExit(r.returncode or (0 if before==after else 2))
