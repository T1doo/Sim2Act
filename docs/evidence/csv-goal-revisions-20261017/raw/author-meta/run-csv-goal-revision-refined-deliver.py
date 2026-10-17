import hashlib,json,os,pathlib,subprocess,time,xml.etree.ElementTree as ET
root=pathlib.Path('/workspace/Sim2Act')
out=pathlib.Path('/workspace/csv-goal-revision-evidence-20261017/author-refined-deliver')
out.mkdir(exist_ok=True)
files=subprocess.check_output(['git','-c','core.fsmonitor=false','ls-files','src','tests','pyproject.toml','scripts/engineering-ci/package.json','scripts/engineering-ci/package-lock.json'],cwd=root,text=True).splitlines()
def hashes(): return {f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}
sha=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=root,text=True).strip()
before=hashes();(out/'inputs-before.json').write_text(json.dumps(dict(sha=sha,files=before),indent=2))
cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q','tests/test_csv_goal_revisions.py::test_visible_same_goal_revision_check_release_adopt_and_new_run[deliver]','--basetemp=/tmp/csv-goal-revision-author-refined-deliver-20261017','--junitxml='+str(out/'junit.xml')]
(out/'command.json').write_text(json.dumps(dict(command=cmd,source_sha=sha,scope='synthetic SQLite/ASGI/JSDOM, original CSV Worker; no real provider, no PG/Windows/remote CI/deployment'),indent=2))
start=time.time()
with (out/'pytest.log').open('w') as log: result=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'NODE_PATH':str(root/'scripts/engineering-ci/node_modules'),'PYTHONPATH':str(root/'src')})
after=hashes();(out/'inputs-after.json').write_text(json.dumps(dict(sha=sha,files=after),indent=2))
suites=ET.parse(out/'junit.xml').getroot();cases=[dict(x.attrib,failures=[f.text for f in x.findall('failure')],errors=[f.text for f in x.findall('error')],skipped=bool(x.findall('skipped'))) for x in suites.iter('testcase')]
report=dict(source_sha=sha,returncode=result.returncode,wall_seconds=time.time()-start,source_inputs=len(files),source_unchanged=before==after,cases=cases)
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2),flush=True)
raise SystemExit(result.returncode or (0 if before==after else 2))
