from pathlib import Path
import datetime, hashlib, json, os, subprocess, time

ROOT=Path('/workspace/Sim2Act')
OUT=Path(__file__).parent
freeze=ROOT/'docs/evidence/pb-cold-recovery-20261011/candidate3-source-freeze.json'
manifest=json.loads(freeze.read_text())
def capture(suffix):
    actual={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in manifest['sha256']}
    differences=[name for name in actual if actual[name]!=manifest['sha256'][name]]
    (OUT/f'source-{suffix}.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'count':len(actual),'differences':differences,'sha256':actual},indent=2)+'\n')
    assert not differences
capture('before')
env={**os.environ,'PYTHONPATH':'src:tests','NODE_PATH':'/workspace/node-tools/node_modules'}
env.pop('SIM2ACT_TEST_DATABASE_URL',None)
cmd=[str(ROOT/'.venv/bin/python'),'-m','pytest','-q','-p','conftest',str(OUT/'test_project_source_budget.py'),'--basetemp',str(OUT/'budget-red-db'),'--junitxml',str(OUT/'budget-red.xml')]
start=time.monotonic()
with (OUT/'budget-red.log').open('x') as log:
    process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    status={'status':'RUNNING','pid':process.pid,'argv':cmd,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (OUT/'budget-red-process.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    code=process.wait()
status.update(status='COMPLETED',exit_code=code,elapsed_seconds=round(time.monotonic()-start,3),completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'budget-red-process.json').write_text(json.dumps(status,indent=2)+'\n')
capture('after')
print(json.dumps(status),flush=True)
print((OUT/'budget-red.log').read_text()[-6000:],flush=True)
raise SystemExit(code)
