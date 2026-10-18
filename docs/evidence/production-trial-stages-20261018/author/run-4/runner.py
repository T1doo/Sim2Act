import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

repo = Path('/workspace/Sim2Act')
author = Path('/workspace/production-trial-stages-20261018')
out = author / 'run-4'
out.mkdir(exist_ok=False)
(out/'runner.py').write_bytes(Path(__file__).read_bytes())
(out/'offline_stages_guard.py').write_bytes((author/'offline_stages_guard.py').read_bytes())

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=repo)

assert git('status', '--porcelain') == b''
head = git('rev-parse', 'HEAD').decode().strip()
paths = sorted(p for p in git('ls-files').decode().splitlines()
               if p.startswith(('src/', 'tests/')) or p in ('pyproject.toml', 'uv.lock'))

def inputs(name):
    value = dict(head=head, inputs={p: dict(bytes=(repo/p).stat().st_size,
        sha256=hashlib.sha256((repo/p).read_bytes()).hexdigest()) for p in paths})
    (out/name).write_text(json.dumps(value, indent=2)+'\n')
    return value

helpers = [Path(__file__), author/'offline_stages_guard.py']
def helper_state(name):
    value = {p.name: dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in helpers}
    (out/name).write_text(json.dumps(value, indent=2)+'\n')
    return value

before, hbefore = inputs('inputs-before.json'), helper_state('helpers-before.json')
command = ['timeout', '--kill-after=15s', '900s', '/workspace/sim2act-venv/bin/python',
    '-m', 'pytest', '-vv', '-s', '--maxfail=1', '-p', 'offline_stages_guard',
    '--basetemp='+str(out/'actual-tmp'), '--junitxml='+str(out/'junit.xml'),
    'tests/test_production_trial_stages.py']
record = dict(source_commit=head, baseline='4bb3c26f5f67511795771c9187537aee4e852590',
    command=command, cwd=str(repo), started_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    old_19_12_8_9_nodes_rerun=0, real_provider_calls=0)
(out/'execution.json').write_text(json.dumps(record, indent=2)+'\n')
environment = {k:v for k,v in os.environ.items() if not k.startswith(('SIM2ACT_', 'INTERN_'))}
environment.update(PYTHONPATH=str(author), STAGES_GUARD_PROOF=str(out/'offline-guard.json'))
start = time.monotonic()
with (out/'pytest.stdout').open('wb') as stdout, (out/'pytest.stderr').open('wb') as stderr:
    result = subprocess.run(command, cwd=repo, env=environment, stdout=stdout, stderr=stderr)
after, hafter = inputs('inputs-after.json'), helper_state('helpers-after.json')
record.update(exit_code=result.returncode, elapsed_seconds=time.monotonic()-start,
    ended_utc=datetime.datetime.now(datetime.UTC).isoformat(), input_count=len(paths),
    production_count=sum(p.startswith('src/') for p in paths), input_drift=before != after,
    helper_drift=hbefore != hafter)
(out/'execution.json').write_text(json.dumps(record, indent=2)+'\n')
for p in git('diff', '--name-only', '4bb3c26f5f67511795771c9187537aee4e852590', 'HEAD').decode().splitlines():
    target = out/'frozen-source'/p
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((repo/p).read_bytes())
print(json.dumps(record))
assert not record['input_drift'] and not record['helper_drift']
raise SystemExit(result.returncode)
