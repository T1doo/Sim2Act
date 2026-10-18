import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/project-run-results-20261018')
assert not (out / 'execution.json').exists()


def inputs(name):
    paths = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'ls-files', '-z'], cwd=repo).decode().split('\0')
    selected = sorted(p for p in paths if p and (p.startswith(('src/', 'tests/', 'scripts/', '.github/'))
        or p in {'.gitattributes', 'pyproject.toml', 'requirements.lock', 'requirements-windows.lock'}))
    value = dict(head=subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
        inputs={p: dict(bytes=(repo / p).stat().st_size, sha256=hashlib.sha256((repo / p).read_bytes()).hexdigest()) for p in selected})
    (out / name).write_text(json.dumps(value, indent=2) + '\n')
    return value


before = inputs('inputs-before.json')
assert not subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=repo)
command = ['timeout', '--kill-after=15s', '480s', '/workspace/sim2act-venv/bin/python', '-m', 'pytest', '-vv', '-s',
    '--basetemp=' + str(out / 'actual-tmp'), '--junitxml=' + str(out / 'junit.xml'), 'tests/test_project_run_result_ui.py']
record = dict(head=before['head'], command=command, cwd=str(repo), started_utc=datetime.datetime.now(datetime.UTC).isoformat())
(out / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
environment = dict(os.environ, NODE_PATH=str(repo / 'scripts/engineering-ci/node_modules'))
environment.pop('SIM2ACT_TEST_DATABASE_URL', None)
start = time.monotonic()
with (out / 'pytest.stdout').open('wb') as stdout, (out / 'pytest.stderr').open('wb') as stderr:
    result = subprocess.run(command, cwd=repo, stdout=stdout, stderr=stderr, env=environment)
after = inputs('inputs-after.json')
record.update(exit_code=result.returncode, elapsed_seconds=time.monotonic() - start,
    ended_utc=datetime.datetime.now(datetime.UTC).isoformat(), input_count=len(before['inputs']),
    production_count=sum(p.startswith('src/') for p in before['inputs']), input_drift=before['inputs'] != after['inputs'])
(out / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
assert not record['input_drift']
print(json.dumps(record))
raise SystemExit(result.returncode)
