import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

root = Path('/workspace/Sim2Act')
out = Path(__file__).parent
kind = sys.argv[1]
case = {
    'actual': 'tests/test_natural_result_navigation_ui.py::test_same_pb_instance_navigates_matching_owner_run_and_downloads_both_versions',
    'synthetic': 'tests/test_natural_application_entry.py::test_natural_entry_navigation_synthesized_api',
}['actual' if kind.startswith('actual') else 'synthetic']
cmd = ['timeout', '--kill-after=15s', '900s', '/workspace/sim2act-venv/bin/python',
    '-m', 'pytest', '-vv', '-s', '--basetemp=' + str(out / (kind + '-tmp')),
    '--junitxml=' + str(out / (kind + '-junit.xml')), case]
record = dict(kind=kind, command=cmd, cwd=str(root),
    started_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    head=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=root,text=True).strip(),
    classification='ACTUAL_HTTP_JSDOM' if kind.startswith('actual') else 'SYNTHETIC_GET_RENDERER_STUBS_NO_HTTP_WORKER')
(out / (kind + '-execution.json')).write_text(json.dumps(record, indent=2) + '\n')
started = time.monotonic()
with (out / (kind + '.stdout')).open('wb') as stdout, (out / (kind + '.stderr')).open('wb') as stderr:
    result = subprocess.run(cmd, cwd=root, stdout=stdout, stderr=stderr)
record.update(exit_code=result.returncode, duration_seconds=time.monotonic()-started,
    ended_utc=datetime.datetime.now(datetime.UTC).isoformat())
(out / (kind + '-execution.json')).write_text(json.dumps(record, indent=2) + '\n')
(out / (kind + '.exit')).write_text(str(result.returncode) + '\n')
print(json.dumps(record))
sys.exit(result.returncode)
