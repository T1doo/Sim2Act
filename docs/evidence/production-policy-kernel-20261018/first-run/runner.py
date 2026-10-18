import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

repo = Path('/workspace/Sim2Act')
out = Path('/workspace/production-policy-kernel-20261018')
assert not (out / 'execution.json').exists()


def inputs(name):
    paths = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'ls-files', '-z'], cwd=repo).decode().split('\0')
    selected = sorted(p for p in paths if p and (p.startswith(('src/', 'tests/', 'scripts/', '.github/'))
        or p in {'.gitattributes', 'pyproject.toml', 'requirements.lock', 'requirements-windows.lock'}))
    result = dict(head=subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
        inputs={p: dict(bytes=(repo / p).stat().st_size, sha256=hashlib.sha256((repo / p).read_bytes()).hexdigest()) for p in selected})
    (out / name).write_text(json.dumps(result, indent=2) + '\n')
    return result


before = inputs('inputs-before.json')
assert not subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=repo)
helpers = {name: dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    for name, path in [('runner', Path(__file__)), ('guard', out / 'offline_policy_guard.py')]}
(out / 'helpers-before.json').write_text(json.dumps(helpers, indent=2) + '\n')
command = ['timeout', '--kill-after=15s', '240s', '/workspace/sim2act-venv/bin/python', '-m', 'pytest', '-vv', '-s',
    '-p', 'offline_policy_guard', '--basetemp=' + str(out / 'actual-tmp'), '--junitxml=' + str(out / 'junit.xml'),
    'tests/test_production_trial_policy.py',
    'tests/test_natural_live_admission.py::test_default_real_deny_and_test_permit_is_not_live',
    'tests/test_natural_live_admission.py::test_user_free_claim_or_arbitrary_authority_never_called',
    'tests/test_natural_live_admission.py::test_synthetic_authority_never_works_as_production',
    'tests/test_natural_live_admission.py::test_permission_loss_denies_before_private_approval_read',
    'tests/test_natural_live_admission.py::test_fresh_run_cancel_fence_version_lease_identity_rejected']
record = dict(source_commit=before['head'], command=command, cwd=str(repo), started_utc=datetime.datetime.now(datetime.UTC).isoformat())
(out / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
environment = dict(os.environ, PYTHONPATH=str(out), POLICY_GUARD_PROOF=str(out / 'offline-guard.json'))
for name in ('SIM2ACT_TEST_DATABASE_URL', 'SIM2ACT_INTERN_TOKEN', 'INTERN_API_TOKEN', 'SIM2ACT_DATABASE_URL',
             'SIM2ACT_LIVE_ENABLED', 'SIM2ACT_MODEL_MODE', 'SIM2ACT_GOAL_PLANNER_PROVIDER'):
    environment.pop(name, None)
start = time.monotonic()
with (out / 'pytest.stdout').open('wb') as stdout, (out / 'pytest.stderr').open('wb') as stderr:
    result = subprocess.run(command, cwd=repo, env=environment, stdout=stdout, stderr=stderr)
after = inputs('inputs-after.json')
after_helpers = {name: dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    for name, path in [('runner', Path(__file__)), ('guard', out / 'offline_policy_guard.py')]}
(out / 'helpers-after.json').write_text(json.dumps(after_helpers, indent=2) + '\n')
record.update(exit_code=result.returncode, elapsed_seconds=time.monotonic() - start,
    ended_utc=datetime.datetime.now(datetime.UTC).isoformat(), input_count=len(before['inputs']),
    production_count=sum(p.startswith('src/') for p in before['inputs']),
    input_drift=before != after, helper_drift=helpers != after_helpers)
(out / 'execution.json').write_text(json.dumps(record, indent=2) + '\n')
assert not record['input_drift'] and not record['helper_drift']
print(json.dumps(record))
raise SystemExit(result.returncode)
