"""Reproduce frozen, partitioned SQLite/in-process/Node regression (no live API)."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PYTHON = ROOT / '.venv/bin/python'
SELECT = json.loads((OUT / 'selection.json').read_text())
ENV = os.environ.copy()
ENV['NODE_PATH'] = '/workspace/node-tools/node_modules'
assert not ENV.get('SIM2ACT_TEST_DATABASE_URL'), 'This evidence must use isolated SQLite'


def freeze():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ('src', 'tests', 'scripts') for p in sorted((ROOT / directory).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


if __name__ == '__main__':
    before = freeze()
    (OUT / 'frozen-before.json').write_text(json.dumps(before, indent=2) + '\n')
    with (OUT / 'full-collection.log').open('w') as f:
        collected = subprocess.run([str(PYTHON), '-m', 'pytest', '--collect-only', '-q',
            *SELECT['modules'], '-k', SELECT['deselection']], cwd=ROOT, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    assert collected.returncode == 0
    nodes = [s for s in (OUT / 'full-collection.log').read_text().splitlines() if s.startswith('tests/') and '::' in s]
    assert len(nodes) == len(set(nodes))
    assert set(SELECT['original_nodes']) <= set(nodes), 'Original 650 nodes must all be restored'
    counts = {m: sum(n.startswith(m + '::') for n in nodes) for m in SELECT['modules']}
    ui_modules = [m for m in SELECT['modules'] if m.endswith('_ui.py')]
    shards, weights = [[] for _ in range(4)], [0] * 4
    for module in sorted((m for m in counts if m not in ui_modules), key=lambda m: counts[m], reverse=True):
        chosen = weights.index(min(weights))
        shards[chosen].append(module)
        weights[chosen] += max(counts[module], 1)
    (OUT / 'partition.json').write_text(json.dumps({'nodes': nodes, 'shards': shards, 'ui_modules': ui_modules,
        'source_test_script_files': len(before), 'selected_node_count': len(nodes),
        'original_650_restored': True}, indent=2) + '\n')
    children = []
    started = time.monotonic()
    for index, modules in enumerate(shards):
        log = (OUT / f'full-{index}.log').open('w')
        argv = [str(PYTHON), '-m', 'pytest', '-q', *modules, '-k', SELECT['deselection'],
            f'--basetemp=/tmp/run-private-full-{index}', f'--junitxml={OUT}/full-{index}.xml']
        proc = subprocess.Popen(argv, cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
        children.append((index, proc, log, argv))
    (OUT / 'full-running.json').write_text(json.dumps({'children':[
        {'shard': i, 'pid': p.pid, 'argv': argv} for i, p, log, argv in children]}, indent=2)+'\n')
    statuses = []
    for index, proc, log, argv in children:
        code = proc.wait()
        log.close()
        statuses.append({'shard': index, 'exit_code': code})
        print(json.dumps(statuses[-1]), flush=True)
    # Existing DOM deadlines are unchanged. Run UI serially after backend
    # processes have exited, so parallel CPU contention does not invalidate
    # their original bounded waits.
    with (OUT / 'full-ui.log').open('w') as log:
        code = subprocess.run([str(PYTHON), '-m', 'pytest', '-q', *ui_modules,
            f'--basetemp=/tmp/run-private-full-ui', f'--junitxml={OUT}/full-ui.xml'],
            cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT).returncode
    statuses.append({'shard': 'ui', 'exit_code': code})
    after = freeze()
    (OUT / 'frozen-after.json').write_text(json.dumps(after, indent=2) + '\n')
    (OUT / 'full-exit.json').write_text(json.dumps({'statuses': statuses,
        'wall_seconds': time.monotonic() - started, 'code_unchanged': before == after}, indent=2)+'\n')
    assert before == after, 'Concurrent source/test/script mutation invalidates this run'
    sys.exit(1 if any(s['exit_code'] for s in statuses) else 0)
