"""Frozen affected-suite evidence orchestration; uses only owned test resources."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
out = root / 'docs/evidence/fixed-csv-dag-20261008'
suite = json.loads((root / 'docs/evidence/column-binding-patch-20261008/sqlite-provenance.json').read_text())['suite'] + [
    'tests/test_column_patch_controls.py', 'tests/test_column_patch_keys.py',
    'tests/test_csv_dag.py', 'tests/test_csv_dag_boundaries.py', 'tests/test_csv_dag_ui.py',
    'tests/test_foundation.py', 'tests/test_model_budget.py', 'tests/test_reconciliation.py',
    'tests/test_runtime_coordination.py', 'tests/test_persistent_app_runs.py',
    'tests/test_contract_semantics.py', 'tests/test_install_preflight.py',
    'tests/test_lifecycle.py', 'tests/test_internal_api.py',
    'tests/test_protocol_recovery.py', 'tests/test_conditional_run_bindings.py',
]
suite = list(dict.fromkeys(suite))
name = sys.argv[1]
fixture = '/tmp/sim2act-dag-final-' + name
files = subprocess.check_output(['git', 'ls-files', 'src', 'tests'], text=True).splitlines()
def hashes():
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in files}
before = hashes()
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
with (out / (name + '.log')).open('w') as log:
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *suite, '--basetemp=' + fixture,
        '--junitxml=' + str(out / (name + '.xml'))], stdout=log, stderr=subprocess.STDOUT,
        env={**os.environ, 'LIVE': '0', 'NODE_PATH': '/tmp/sim2act-dag-node/node_modules'})
after = hashes()
(out / (name + '-provenance.json')).write_text(json.dumps(dict(source_sha=sha, suite=suite,
    returncode=result.returncode, before=before, after=after, source_unchanged=before == after,
    model_mode='mock', live=0, fixture_root=fixture), indent=2))
raise SystemExit(result.returncode)
