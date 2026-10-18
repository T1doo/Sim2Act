import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import time

BASE = pathlib.Path('/tmp/csv-material-independent-positive-805-20261018')
SOURCE = BASE / 'source'
EVIDENCE = BASE / 'evidence'
PYTHON = '/workspace/sim2act-venv/bin/python'
command = [PYTHON, '-m', 'pytest', '-vv', '-s', '-p', 'no:cacheprovider',
    '--basetemp=' + str(EVIDENCE / 'pytest-temp'), '--junitxml=' + str(EVIDENCE / 'junit.xml'),
    'tests/test_csv_material_revisions.py::test_authorized_B_same_instance_check_cas_result_pending_and_immutable_A']
environment = dict(os.environ, PYTHONPATH=str(SOURCE / 'src') + ':' + str(SOURCE / 'tests'),
    PYTHONDONTWRITEBYTECODE='1')
environment.pop('SIM2ACT_TEST_DATABASE_URL', None)
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
monotonic = time.monotonic()
record = dict(product_commit='805afe60cdd94d6d4679e0da9c1f7fde752f67d2', cwd=str(SOURCE),
    command=command, pythonpath=environment['PYTHONPATH'], started_utc=start,
    database='fresh isolated SQLite under pytest basetemp', actual_model='NoModel fixture; mock Settings',
    test_node_count=1)
(EVIDENCE / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
with (EVIDENCE / 'pytest.stdout.log').open('w') as stream:
    process = subprocess.run(command, cwd=SOURCE, env=environment, stdout=stream, stderr=subprocess.STDOUT)
record.update(exit_code=process.returncode, finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    duration_seconds=time.monotonic()-monotonic)
(EVIDENCE / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
before = json.loads((EVIDENCE / 'frozen-inputs-before.json').read_text())
patch = json.loads((EVIDENCE / 'observer-patch-proof.json').read_text())
expected_test = patch['changes'][0]['applied_sha256']
changes = []
for entry in before['files']:
    path = SOURCE / entry['path']
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    expected = expected_test if entry['path'] == 'tests/test_csv_material_revisions.py' else entry['sha256']
    if actual != expected:
        changes.append(dict(path=entry['path'], expected_sha256=expected, actual_sha256=actual))
(EVIDENCE / 'frozen-inputs-after.json').write_text(json.dumps(dict(
    product_commit=record['product_commit'], original_git_blobs_verified=len(before['files']),
    expected_observer_patch=patch['changes'], changes_during_test=changes,
    product_source_changes_during_test=sum(item['path'].startswith('src/') for item in changes)), indent=2) + '\n')
assert not changes, changes
print(json.dumps(record, indent=2), flush=True)
raise SystemExit(process.returncode)
