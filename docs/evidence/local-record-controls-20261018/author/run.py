import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/local-record-controls-20261018')
paths=sorted(p for p in (root/'src/sim2act').rglob('*') if p.is_file() and p.suffix in {'.py','.js','.html','.css','.json'})
paths += [root/'tests'/name for name in ['test_local_record_apps.py','test_local_record_apps_ui.py','local_record_apps_ui.cjs','test_local_record_history.py','conftest.py','sql_private_barrier.py']]
def sources():return {str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
before=sources();(out/'input-before.json').write_text(json.dumps(before,indent=2)+'\n')
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env['NODE_PATH']='/workspace/node-tools/node_modules'
cmd=['timeout','--kill-after=15s','180s','/workspace/sim2act-venv/bin/python','-m','pytest','tests/test_local_record_apps_ui.py::test_local_record_page_explicit_flow_and_fenced_navigation_actual_http[controls]','-q','--junitxml='+str(out/'result.xml'),'--basetemp='+str(out/'pytest-temp')]
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
with (out/'pytest.stdout').open('wb') as stdout,(out/'pytest.stderr').open('wb') as stderr:p=subprocess.run(cmd,cwd=root,env=env,stdout=stdout,stderr=stderr)
after=sources();(out/'input-after.json').write_text(json.dumps(after,indent=2)+'\n')
record=dict(argv=cmd,started_at=start,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-t,returncode=p.returncode,source_drift=[k for k in before if before[k]!=after[k]],classification='ACTUAL_TESTCLIENT_HTTP_FULL_PAGE_JSDOM_LOCAL_RECORD_CONTROLS_NO_MODEL_OR_WORKER_CLAIM',real_model_calls=0,pg=False)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(p.returncode)
