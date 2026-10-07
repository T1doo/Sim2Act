"""Owned regression controller. Execute only after parent sends exact freeze/GO."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/workspace/Sim2Act-report-preview-combined-regression')
OWNED = Path('/tmp')
NODE_PATH = '/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules'


def verify_source(expected):
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if actual != expected:
        raise ValueError('Current HEAD differs from explicitly frozen source')
    files = subprocess.check_output(['git', 'ls-files', 'src', 'tests', 'scripts', '.github'], cwd=ROOT, text=True).splitlines()
    hashes = {}
    for name in files:
        raw = (ROOT / name).read_bytes()
        frozen = subprocess.check_output(['git', 'show', expected + ':' + name], cwd=ROOT)
        if raw != frozen:
            raise ValueError('Frozen tracked file mismatch: ' + name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return hashes


def run(phase, expected):
    hashes = verify_source(expected)
    if phase == 'pg':
        previous = json.loads((OWNED / 'report-preview-combined-sqlite-controller.json').read_text())
        if previous['source_commit'] != expected or previous.get('exit_code') != 0:
            raise ValueError('Same-source complete SQLite exit0 is required before PostgreSQL')
    record_path = OWNED / ('report-preview-combined-' + phase + '-controller.json')
    if record_path.exists():
        raise ValueError('Controller record already exists: no automatic rerun/overwrite')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('SIM2ACT_TEST_DATABASE_URL', None)
    env['NODE_PATH'] = NODE_PATH
    if phase == 'pg':
        state = json.loads((OWNED / 'report-preview-combined-pg-private.json').read_text())
        env['SIM2ACT_TEST_DATABASE_URL'] = state['url']
    private = '-private' if phase == 'pg' else ''
    logfile = OWNED / ('report-preview-combined-' + phase + private + '.log')
    junit = OWNED / ('report-preview-combined-' + phase + '-junit' + private + '.xml')
    basetemp = OWNED / ('report-preview-combined-' + expected[:12] + '-' + phase + '-tests')
    command = ['/tmp/report-preview-combined-' + phase + '-venv/bin/python', '-m', 'pytest', '-q', '-ra', '--durations=30', '--junitxml=' + str(junit), '--basetemp=' + str(basetemp)]
    record = {'source_commit': expected, 'source_files': hashes, 'phase': phase, 'command': command, 'started_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'log': str(logfile)}
    with logfile.open('w') as stream:
        logfile.chmod(0o600)
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        record['pytest_pid'] = process.pid
        record_path.write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps({'phase': phase, 'source_commit': expected, 'pytest_pid': process.pid}), flush=True)
        record['exit_code'] = process.wait()
    record['finished_at_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'phase': phase, 'exit_code': record['exit_code']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['sqlite', 'pg'])
    parser.add_argument('--source-sha', required=True)
    args = parser.parse_args()
    run(args.phase, args.source_sha)
