import datetime
import json
import os
import subprocess
import time
from pathlib import Path

repo=Path('/workspace/Sim2Act')
out=Path('/workspace/pb-first-logic-current-page-evidence-20261018')
assert not (out/'execution.json').exists(), 'Check any prior run outcome before considering a bounded separate attempt'
head=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=repo,text=True).strip()
assert not subprocess.check_output(['git','-c','core.fsmonitor=false','status','--porcelain=v1','--untracked-files=all'],cwd=repo,text=True)
command=['timeout','--kill-after=15s','1200s','/workspace/sim2act-venv/bin/python','-m','pytest','-vv','-s',
    '--basetemp='+str(out/'actual-tmp'),'--junitxml='+str(out/'actual-junit.xml'),
    'tests/test_pb_first_logic_current_page_ui.py']
record=dict(command=command,cwd=str(repo),classification='ONE_ACTUAL_HTTP_JSDOM_PB_FIRST_LOCAL_LOGIC_COMPLETE_PAGE',started_utc=datetime.datetime.now(datetime.UTC).isoformat(),head=head)
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
started=time.monotonic()
with (out/'actual.stdout').open('wb') as stdout,(out/'actual.stderr').open('wb') as stderr:
    result=subprocess.run(command,cwd=repo,stdout=stdout,stderr=stderr,env={**os.environ,'NODE_PATH':str(repo/'scripts/engineering-ci/node_modules')})
record.update(exit_code=result.returncode,duration_seconds=time.monotonic()-started,ended_utc=datetime.datetime.now(datetime.UTC).isoformat())
(out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'actual.exit').write_text(str(result.returncode)+'\n')
print(json.dumps(record))
raise SystemExit(result.returncode)
