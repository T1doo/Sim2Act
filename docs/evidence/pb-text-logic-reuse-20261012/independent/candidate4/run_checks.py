import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path('/workspace/Sim2Act')
OUT = Path('/tmp/pb-text-logic-review-20261012/candidate4')
FREEZE = REPO / 'docs/evidence/pb-text-logic-reuse-20261012/candidate4-freeze.json'

def snapshot(label):
    spec = json.loads(FREEZE.read_text())
    actual = {}
    errors = []
    for relative, expected in spec['sha256'].items():
        path = REPO / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        actual[relative] = digest
        if digest != expected:
            errors.append({'path': relative, 'expected': expected, 'actual': digest})
    result = {'label': label, 'freeze_sha256': hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
              'base': spec['base'], 'checked_files': len(actual), 'mismatches': errors,
              'actual_sha256': actual}
    (OUT / (label + '-freeze-check.json')).write_text(json.dumps(result, indent=2))
    print(json.dumps({'label': label, 'checked_files': len(actual), 'mismatches': len(errors)}), flush=True)
    if errors:
        raise SystemExit(2)

def run(label, paths):
    snapshot(label + '-before')
    command = [str(REPO / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
               '--basetemp=' + str(OUT / (label + '-tmp')), '--junitxml=' + str(OUT / (label + '.xml')),
               *paths]
    (OUT / (label + '-command.json')).write_text(json.dumps(command, indent=2))
    run_env = dict(os.environ)
    # Explicitly select isolated per-test SQLite; never consume any configured PG URL.
    run_env.pop('SIM2ACT_TEST_DATABASE_URL', None)
    run_env['PYTHONDONTWRITEBYTECODE'] = '1'
    run_env['SIM2ACT_TEXT_LOGIC_EVIDENCE_DIR'] = str(OUT / 'ui-artifacts')
    started = time.time()
    with (OUT / (label + '.log')).open('w') as handle:
        result = subprocess.run(command, cwd=REPO, env=run_env, stdout=handle, stderr=subprocess.STDOUT)
    summary = {'label': label, 'exit_code': result.returncode, 'elapsed_seconds': time.time()-started,
               'command': command, 'database': 'isolated default SQLite',
               'cancelled_exact_install_probe': 'PERMANENT_NOT_VERIFIED; NOT_RUN'}
    (OUT / (label + '-result.json')).write_text(json.dumps(summary, indent=2))
    snapshot(label + '-after')
    print(json.dumps(summary), flush=True)
    print((OUT / (label + '.log')).read_text()[-6500:], flush=True)
    return result.returncode

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    raise SystemExit(run(sys.argv[1], sys.argv[2:]))
