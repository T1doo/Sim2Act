import hashlib,json,os,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/csv-continuous-column-evidence-20261017/author-b589-old-pages');out.mkdir(exist_ok=True)
sha='b589809375c89b4d93617d91c780a1e0f7f704e2'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==sha
files=subprocess.check_output(['git','-c','core.fsmonitor=false','ls-files','src','tests','schemas','pyproject.toml','scripts/engineering-ci/package.json','scripts/engineering-ci/package-lock.json','docs/evidence/bounded-agent-offline-20261006','docs/evidence/model-protocol-preparation-20261006/materials','docs/evidence/protocol-store-loop-20261006/evaluation'],cwd=root,text=True).splitlines()
def hashes(): return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
before=hashes();(out/'inputs-before.json').write_text(json.dumps(dict(source_sha=sha,files=before),indent=2))
tests=['tests/test_csv_goal_revisions.py::test_visible_same_goal_revision_check_release_adopt_and_new_run[deliver]', 'tests/test_csv_goal_revisions.py::test_visible_same_goal_revision_check_release_adopt_and_new_run[lost]', 'tests/test_csv_goal_revisions.py::test_visible_same_goal_revision_check_release_adopt_and_new_run[lost-adoption]']
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q',*tests,'-o','tmp_path_retention_policy=all','-o','tmp_path_retention_count=99','--basetemp=/tmp/csv-continuous-author-b589-old-pages-20261017','--junitxml='+str(out/'junit.xml')]
env={**os.environ,'NODE_PATH':str(root/'scripts/engineering-ci/node_modules'),'PYTHONPATH':str(root/'src')};env.pop('SIM2ACT_TEST_DATABASE_URL',None)
(out/'command.json').write_text(json.dumps(dict(source_sha=sha,command=cmd,sqlite_forced=True,model_scope='NoModel/NoProvider/local mocks only',node_path=env['NODE_PATH']),indent=2))
started=time.time()
with (out/'pytest.log').open('w') as log:r=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
after=hashes();(out/'inputs-after.json').write_text(json.dumps(dict(source_sha=sha,files=after),indent=2))
cases=[dict(x.attrib,failures=[f.text for f in x.findall('failure')],errors=[f.text for f in x.findall('error')],skipped=bool(x.findall('skipped'))) for x in ET.parse(out/'junit.xml').iter('testcase')]
report=dict(source_sha=sha,returncode=r.returncode,wall_seconds=time.time()-started,source_inputs=len(files),source_unchanged=before==after,unique_cases=len({(x['classname'],x['name']) for x in cases}),passes=sum(not(x['failures'] or x['errors'] or x['skipped']) for x in cases),failures=sum(bool(x['failures'] or x['errors']) for x in cases),skips=sum(x['skipped'] for x in cases),cases=cases)
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2),flush=True)
raise SystemExit(0 if r.returncode==0 and before==after and len(cases)==3 else 1)
