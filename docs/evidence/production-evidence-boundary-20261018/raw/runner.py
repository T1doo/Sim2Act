import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-evidence-boundary-20261018')
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
command = ['timeout', '--kill-after=15s', '180s', '/workspace/sim2act-venv/bin/python', '-m', 'pytest', '-vv', '-s',
    '-p', 'production_boundary_guard', '--basetemp=' + str(out / 'actual-tmp'), '--junitxml=' + str(out / 'junit.xml'),
    'tests/test_production_evidence.py',
    'tests/test_natural_trial_api.py::test_actual_claimed_generate_http_admission_denies_no_fee_override',
    'tests/test_natural_live_admission.py::test_default_real_deny_and_test_permit_is_not_live',
    'tests/test_production_trial_admission.py::test_arbitrary_callback_or_production_store_never_invoked']
record = dict(head=before['head'], command=command, cwd=str(repo), started_utc=datetime.datetime.now(datetime.UTC).isoformat())
(out / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
environment = dict(os.environ, PYTHONPATH=str(out), PRODUCTION_BOUNDARY_GUARD_PROOF=str(out / 'offline-guard.json'))
for key in ('SIM2ACT_TEST_DATABASE_URL', 'SIM2ACT_INTERN_TOKEN', 'INTERN_API_TOKEN', 'SIM2ACT_DATABASE_URL',
            'SIM2ACT_LIVE_ENABLED', 'SIM2ACT_MODEL_MODE', 'SIM2ACT_GOAL_PLANNER_PROVIDER'):
    environment.pop(key, None)
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
