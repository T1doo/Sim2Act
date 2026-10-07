"""One explicitly authorized frozen-source PG diagnostic, never auto-retried."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/workspace/Sim2Act-delivery-graph-combined-regression')
PREFIX = Path('/tmp/report-directory-hint-pg')
PRIVATE = Path(str(PREFIX) + '-pg-private.json')
RECORD = Path(str(PREFIX) + '-controller.json')
EXE = '/tmp/delivery-graph-combined-pg-venv/bin/python'


def run(expected):
    if RECORD.exists():
        raise ValueError('One-run record exists; no automatic retry or overwrite')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != expected:
        raise ValueError('Exact final freeze required')
    names = subprocess.check_output(['git', 'ls-files', 'src', 'tests', 'scripts', '.github'], cwd=ROOT, text=True).splitlines()
    hashes = {}
    for name in names:
        raw = (ROOT / name).read_bytes()
        if raw != subprocess.check_output(['git', 'show', expected + ':' + name], cwd=ROOT):
            raise ValueError('Source changed: ' + name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    state = json.loads(PRIVATE.read_text())
    info = json.loads(subprocess.check_output(['docker', 'inspect', state['container']]))[0]
    if info['Config']['Labels'].get('sim2act.report-directory-hint-pg') != '20261007':
        raise ValueError('Not the dedicated owner container')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env['NODE_PATH'] = '/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules'
    env['SIM2ACT_TEST_DATABASE_URL'] = state['url']
    command = [EXE, '-m', 'pytest', 'tests/test_report_manifest_apps_ui.py::test_report_manifest_real_http_dom', '-vv', '-ra', '--durations=30', '--junitxml=' + str(PREFIX) + '-private.xml', '--basetemp=' + str(PREFIX) + '-tests']
    record = {'source_commit': expected, 'source_files': hashes, 'command': command, 'node_timeout_seconds': 90, 'run_count': 1, 'started_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    with Path(str(PREFIX) + '-private.log').open('w') as log:
        os.chmod(log.name, 0o600)
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        record['pytest_pid'] = process.pid
        RECORD.write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps({'pytest_pid': process.pid, 'source_commit': expected}), flush=True)
        record['exit_code'] = process.wait()
    record['finished_at_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    RECORD.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'exit_code': record['exit_code']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha', required=True)
    run(parser.parse_args().source_sha)
