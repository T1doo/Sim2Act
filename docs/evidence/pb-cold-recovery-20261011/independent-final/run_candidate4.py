from pathlib import Path
import datetime, json, os, subprocess, sys, time

ROOT=Path('/workspace/Sim2Act')
OUT=Path(__file__).parent
OLD=OUT.parent
kind=sys.argv[1]
selected={
    'new':['tests/test_registered_text_recovery.py','tests/test_registered_text_recovery_ui.py'],
    'existing':['tests/test_registered_text_extraction.py','tests/test_registered_text_ui.py'],
    'extra':[str(OLD/'test_independent_journal_gates.py'),str(OLD/'test_poison_project_source_v3.py'),str(OLD/'test_late_latest_digest_v2.py')],
    'budget':[str(OUT/'budget/test_project_source_budget_v2.py')],
}[kind]
cmd=[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',*(['-p','conftest'] if kind in {'extra','budget'} else []),*selected,'-o',f'cache_dir={OUT}/.pytest_cache-{kind}','--basetemp',str(OUT/(kind+'-db')),'--junitxml',str(OUT/(kind+'.xml'))]
env={**os.environ,'PYTHONPATH':'src:tests','NODE_PATH':'/workspace/node-tools/node_modules','SIM2ACT_PB_EVIDENCE_DIR':str(OUT/'existing-pages'),'SIM2ACT_COLD_EVIDENCE_DIR':str(OUT/'cold-pages'),'COLD_PROBE_PREFIX':'candidate4/extra-','COLD_POISON_PAGE_PREFIX':'candidate4/extra-cold-pages','COLD_LATEST_PAGE_PREFIX':'candidate4/extra-latest-pages'}
env.pop('SIM2ACT_TEST_DATABASE_URL',None)
start=time.monotonic()
with (OUT/(kind+'.log')).open('x') as log:
    process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    status={'status':'RUNNING','pid':process.pid,'argv':cmd,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'group':kind}
    (OUT/(kind+'-process.json')).write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    code=process.wait()
status.update(status='COMPLETED',exit_code=code,elapsed_seconds=round(time.monotonic()-start,3),completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/(kind+'-process.json')).write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status),flush=True)
print((OUT/(kind+'.log')).read_text()[-6500:],flush=True)
raise SystemExit(code)
