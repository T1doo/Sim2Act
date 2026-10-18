import datetime
import json
import subprocess
import sys
from pathlib import Path

root = Path('/workspace/Sim2Act')
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/workspace/pb-extraction-close-evidence-20261018')
out.mkdir(parents=True, exist_ok=True)
commands = [
    ['/workspace/sim2act-venv/bin/ruff', 'check', 'src/sim2act/pb_extraction_terminals.py',
     'src/sim2act/pb_natural_specs.py', 'tests/test_pb_extraction_close.py',
     'tests/test_pb_extraction_close_ui.py'],
    ['node', '--check', 'src/sim2act/web/internal.js'],
    ['node', '--check', 'tests/pb_extraction_close_ui.cjs'],
    ['/workspace/sim2act-venv/bin/python', '-m', 'py_compile',
     'src/sim2act/pb_extraction_terminals.py', 'src/sim2act/pb_natural_specs.py',
     'tests/test_pb_extraction_close.py', 'tests/test_pb_extraction_close_ui.py'],
    ['git', '-c', 'core.fsmonitor=false', 'diff', '--check'],
]
results = []
for index, command in enumerate(commands, 1):
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    (out / f'static-{index}-stdout.txt').write_text(result.stdout)
    (out / f'static-{index}-stderr.txt').write_text(result.stderr)
    results.append(dict(command=command, exit_code=result.returncode))
(out / 'static-checks.json').write_text(json.dumps(dict(
    time_utc=datetime.datetime.now(datetime.UTC).isoformat(), results=results), indent=2) + '\n')
assert all(row['exit_code'] == 0 for row in results), results
print(json.dumps(dict(static_commands=len(results), all_passed=True)))
