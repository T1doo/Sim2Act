import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path('/workspace/Sim2Act')
OUT = Path('/tmp/own-goal-read-error-review-20261012/final')
FREEZE = REPO / 'docs/evidence/own-goal-read-errors-20261012/freeze.json'

def snapshot(label):
    spec = json.loads(FREEZE.read_text())
    actual, errors = {}, []
    for relative, expected in spec['git_deliverable_files'].items():
        path = REPO / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        actual[relative] = digest
        if digest != expected:
            errors.append({'path': relative, 'expected': expected, 'actual': digest})
    paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', 'src', 'tests'], cwd=REPO, text=True).splitlines()
    path_difference = {'extra': sorted(set(paths) - set(actual)), 'missing': sorted(set(actual) - set(paths))}
    map_fp = hashlib.sha256(json.dumps(actual, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    result = {'label': label, 'freeze_sha256': hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
        'base': spec['base'], 'branch': spec['branch'], 'checked_files': len(actual), 'mismatches': errors,
        'path_difference': path_difference, 'source_tests_fingerprint': map_fp,
        'ignored_metadata_excluded': spec['ignored_metadata_excluded'], 'actual_sha256': actual}
    (OUT / (label + '-freeze-check.json')).write_text(json.dumps(result, indent=2))
    print(json.dumps({k:result[k] for k in ('label','checked_files','source_tests_fingerprint','path_difference')}, ensure_ascii=False), flush=True)
    if errors or any(path_difference.values()) or map_fp != spec['source_tests_fingerprint']:
        raise SystemExit(2)

def run(label, paths):
    snapshot(label + '-before')
    command = [str(REPO / '.venv/bin/python'), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--basetemp=' + str(OUT / (label + '-tmp')), '--junitxml=' + str(OUT / (label + '.xml')), *paths]
    (OUT / (label + '-command.json')).write_text(json.dumps(command, indent=2))
    run_env = dict(os.environ)
    run_env.pop('SIM2ACT_TEST_DATABASE_URL', None)
    run_env['PYTHONDONTWRITEBYTECODE'] = '1'
    run_env['NODE_PATH'] = '/workspace/node-tools/node_modules'
    run_env['SIM2ACT_TEXT_OWNER_UI_EVIDENCE_DIR'] = str(OUT / (label + '-artifacts'))
    run_env['SIM2ACT_OWN_GOAL_READ_EVIDENCE'] = str(OUT / (label + '-artifacts'))
    run_env.pop('SIM2ACT_OWN_GOAL_READ_SOURCE', None)
    if label == 'before-exact-a747':
        run_env['SIM2ACT_OWN_GOAL_READ_SOURCE'] = str(OUT / 'a747-owner-review.js')
    run_env['PYTHONPATH'] = str(REPO / 'tests') + os.pathsep + str(REPO / 'src')
    started = time.time()
    with (OUT / (label + '.log')).open('w') as handle:
        result = subprocess.run(command, cwd=REPO, env=run_env, stdout=handle, stderr=subprocess.STDOUT)
    summary = {'label': label, 'exit_code': result.returncode, 'elapsed_seconds': time.time()-started,
        'command': command, 'database': 'isolated per-test SQLite',
        'cancelled_exact_install_probe': 'PERMANENT_NOT_VERIFIED; NOT_RUN',
        'socket_native': 'NOT_RUN', 'real_human_semantic_acceptance': 'NOT_RUN', 'formal_publication': False}
    (OUT / (label + '-result.json')).write_text(json.dumps(summary, indent=2))
    snapshot(label + '-after')
    print(json.dumps(summary), flush=True)
    print((OUT / (label + '.log')).read_text()[-7500:], flush=True)
    return result.returncode

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    raise SystemExit(run(sys.argv[1], sys.argv[2:]))
