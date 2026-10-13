import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

repo = Path('/workspace/Sim2Act-pa-provider')
root = Path('/workspace/pa-natural-operations-evidence-20261013/independent')
label = sys.argv[1]
args = sys.argv[2:]

def dump(name, value):
    (root / f'{label}-{name}.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def source():
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard',
                                      'src', 'tests', 'pyproject.toml'], cwd=repo, text=True).splitlines()
    return dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
                files={name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in sorted(set(names))})

before = source()
dump('source-before', before)
command = ['/workspace/Sim2Act/.venv/bin/python', '-m', 'pytest', '-q', *args,
           '--basetemp=' + str(root / (label + '-tmp')),
           '--junitxml=' + str(root / (label + '.xml')),
           '-o', 'cache_dir=' + str(root / (label + '-cache'))]
environment = dict(os.environ)
environment.pop('SIM2ACT_TEST_DATABASE_URL', None)
safe_environment = dict(PYTHONPATH=str(repo / 'src') + ':' + str(repo / 'tests'),
                        NODE_PATH='/workspace/node-tools/node_modules', PYTHONDONTWRITEBYTECODE='1')
environment.update(safe_environment)
dump('command', dict(argv=command, cwd=str(repo), explicit_environment=safe_environment))
start = time.time()
with (root / (label + '.stdout')).open('w') as out, (root / (label + '.stderr')).open('w') as err:
    completed = subprocess.run(command, cwd=repo, env=environment, stdout=out, stderr=err)
wall = time.time() - start
after = source()
dump('source-after', after)
changes = [name for name in sorted(set(before['files']) | set(after['files']))
           if before['files'].get(name) != after['files'].get(name)]
result = dict(returncode=completed.returncode, wall_seconds=wall, started=start,
              source_changes=changes, before_count=len(before['files']), after_count=len(after['files']))
xml = root / (label + '.xml')
if xml.exists():
    cases = ET.parse(xml).getroot().findall('.//testcase')
    result.update(selected=len(cases), failed=sum(c.find('failure') is not None for c in cases),
                  errors=sum(c.find('error') is not None for c in cases),
                  skipped=sum(c.find('skipped') is not None for c in cases))
    result['passed'] = result['selected'] - result['failed'] - result['errors'] - result['skipped']
    result['xml_sha256'] = hashlib.sha256(xml.read_bytes()).hexdigest()
dump('result', result)
print(json.dumps(result))
sys.exit(completed.returncode or bool(changes))
