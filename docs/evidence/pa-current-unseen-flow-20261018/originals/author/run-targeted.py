import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

root=Path('/workspace/Sim2Act')
out=Path(__file__).parent
cmd=['timeout','--kill-after=15s','900s','/workspace/sim2act-venv/bin/python','-m','pytest','-vv','-s',
    '--basetemp='+str(out/'actual-tmp'),'--junitxml='+str(out/'actual-junit.xml'),
    'tests/test_pa_unseen_input_ui.py::test_pa_saved_unseen_input_after_explicit_simulated_owner_acceptance']
record=dict(command=cmd,cwd=str(root),classification='ONE_ACTUAL_HTTP_JSDOM_PA_UNSEEN_AND_OVERSIZED_INPUT',
    started_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    head=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=root,text=True).strip())
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
start=time.monotonic()
with (out/'actual.stdout').open('wb') as stdout,(out/'actual.stderr').open('wb') as stderr:
    result=subprocess.run(cmd,cwd=root,stdout=stdout,stderr=stderr)
record.update(exit_code=result.returncode,duration_seconds=time.monotonic()-start,
    ended_utc=datetime.datetime.now(datetime.UTC).isoformat())
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'actual.exit').write_text(str(result.returncode)+'\n')
print(json.dumps(record))
sys.exit(result.returncode)
