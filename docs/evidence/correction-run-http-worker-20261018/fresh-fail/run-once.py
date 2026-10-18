import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/correction-run-http-worker-20261018')
paths=sorted(p for p in (root/'src/sim2act').rglob('*') if p.is_file() and p.suffix in {'.py','.js','.html','.css','.json'})
paths+=sorted(p for p in (root/'tests').rglob('*') if p.is_file() and p.suffix in {'.py','.cjs'})
paths += [root/'pyproject.toml']
def sources():
 return {str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
before=sources();(out/'input-before.json').write_text(json.dumps(before,indent=2)+'\n')
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env['NODE_PATH']='/workspace/node-tools/node_modules'
cmd=['timeout','--signal=TERM','--kill-after=15s','600s','/workspace/sim2act-venv/bin/python','-m','pytest','tests/test_natural_spec_corrections_ui.py::test_visible_rejection_correction_and_independent_owner[pa-normal]','-q','--junitxml='+str(out/'result.xml'),'--basetemp='+str(out/'pytest-temp')]
started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
with (out/'pytest.stdout').open('wb') as stdout,(out/'pytest.stderr').open('wb') as stderr:
 p=subprocess.run(cmd,cwd=root,env=env,stdout=stdout,stderr=stderr)
after=sources();(out/'input-after.json').write_text(json.dumps(after,indent=2)+'\n')
record=dict(argv=cmd,started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-t,returncode=p.returncode,source_drift=[k for k in before if before[k]!=after[k]],classification='ACTUAL_TESTCLIENT_HTTP_JSDOM_ACTUAL_WORKER_SYNTHETIC_MODEL_AND_HUMAN_CHOICES',real_model_requests=0,pg=False)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
raise SystemExit(p.returncode)
