import datetime
import json
import os
from pathlib import Path
import subprocess

base=Path('/tmp/csv-upgrade-independent-b5898093-20261017')
snapshot=base/'snapshot'
command=['/workspace/sim2act-venv/bin/python','-m','pytest','-vv','-s','-p','no:cacheprovider','--basetemp',str(base/'artifacts'),'--junitxml',str(base/'junit.xml'),'tests/test_csv_derive_receipt.py','tests/test_csv_column_revisions.py::test_visible_current_effective_revision_and_fenced_recovery[same-navigation]']
env={key:os.environ[key] for key in ('PATH','LANG','LC_ALL','TMPDIR','USER','LOGNAME') if key in os.environ}
env.update(PYTHONPATH=str(snapshot/'src')+':'+str(snapshot/'tests'),PYTHONDONTWRITEBYTECODE='1',NODE_PATH='/workspace/Sim2Act/scripts/engineering-ci/node_modules',SIM2ACT_LIVE_ENABLED='false')
record=dict(sha='b589809375c89b4d93617d91c780a1e0f7f704e2',argv=command,cwd=str(snapshot),explicit_env=env,start=datetime.datetime.now(datetime.timezone.utc).isoformat(),network='No model/network calls requested; only synthetic deterministic CSV + NoModel Worker')
(base/'run-command.json').write_text(json.dumps(record,indent=2)+'\n')
with (base/'commands.txt').open('a') as out:
    out.write('Pytest command: '+repr(command)+'\nCWD: '+str(snapshot)+'\n')
print(json.dumps(dict(state='STARTED',argv=command,log=str(base/'pytest.log'))),flush=True)
try:
    with (base/'pytest.log').open('w') as log:
        process=subprocess.Popen(command,cwd=snapshot,env=env,stdout=log,stderr=subprocess.STDOUT,text=True)
        record['pid']=process.pid
        (base/'run-command.json').write_text(json.dumps(record,indent=2)+'\n')
        code=process.wait(timeout=1800)
except subprocess.TimeoutExpired:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    code=124
finally:
    record.update(exit_code=code,end=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (base/'run-command.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(state='COMPLETE',exit_code=code,log=str(base/'pytest.log'))),flush=True)
raise SystemExit(code)
