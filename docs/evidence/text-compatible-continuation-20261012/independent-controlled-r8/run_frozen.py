import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path('/workspace/Sim2Act')
OUT = Path('/tmp/text-continuation-ui-independent-20261012/final-r8')
FREEZE = Path('/tmp/text-continuation-r8-final-freeze.json')

def check(label):
    spec = json.loads(FREEZE.read_text())
    actual = {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in spec['source_tests']}
    differences = [{'path': p, 'expected': spec['source_tests'][p], 'actual': v}
                   for p, v in actual.items() if v != spec['source_tests'][p]]
    map_fp = hashlib.sha256(json.dumps(actual, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    pyproject = hashlib.sha256((REPO / 'pyproject.toml').read_bytes()).hexdigest()
    value = {'label': label, 'files': len(actual), 'differences': differences, 'map_fingerprint': map_fp,
             'pyproject_sha256': pyproject, 'freeze_sha256': hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
             'target_implementation': spec['target_implementation'], 'source_sha256': actual,
             'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
             'git_branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=REPO, text=True).strip()}
    (OUT / ('source-' + label + '.json')).write_text(json.dumps(value, indent=2))
    assert not differences and map_fp == spec['map_fingerprint'] and pyproject == spec['pyproject_sha256']
    assert value['git_head'] == spec['base_commit'] and value['git_branch'] == spec['branch']
    print(json.dumps({k: value[k] for k in ('label', 'files', 'map_fingerprint', 'pyproject_sha256', 'freeze_sha256')}), flush=True)
    return value

check('before')
env = dict(os.environ)
env['NODE_PATH'] = '/workspace/node-tools/node_modules'
command = ['node', str(OUT / 'controlled.cjs')]
started = time.time()
with (OUT / 'node-stdout.log').open('w') as stdout, (OUT / 'node-stderr.log').open('w') as stderr:
    result = subprocess.run(command, cwd=REPO, env=env, stdout=stdout, stderr=stderr)
(OUT / 'execution-result.json').write_text(json.dumps({'command': command, 'exit_code': result.returncode,
    'elapsed_seconds': time.time()-started, 'classification': 'CONTROLLED_OFFLINE_SOURCE_JSDOM',
    'http': 'NOT_RUN', 'worker': 'NOT_RUN', 'native': 'NOT_RUN', 'real_model': 'NOT_RUN'}, indent=2))
check('after')
print(json.dumps({'node_exit_code': result.returncode, 'elapsed_seconds': time.time()-started}), flush=True)
print((OUT / 'node-stdout.log').read_text(), flush=True)
if result.returncode:
    print((OUT / 'node-stderr.log').read_text(), flush=True)
raise SystemExit(result.returncode)
