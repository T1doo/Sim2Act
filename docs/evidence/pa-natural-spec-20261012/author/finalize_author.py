"""Seal actual author results after the frozen pytest process exits."""
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act-pa-provider')
FROZEN = '82717272e61c2fa174ad8772e54cd9e9eb947c49'

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')

def xml_result(path):
    root = ET.parse(path).getroot()
    statuses = dict(PASS=0, FAIL=0, ERROR=0, SKIP=0)
    nodes = []
    for case in root.findall('.//testcase'):
        status = ('FAIL' if case.find('failure') is not None else
                  'ERROR' if case.find('error') is not None else
                  'SKIP' if case.find('skipped') is not None else 'PASS')
        node = case.attrib['classname'].replace('.', '/') + '.py::' + case.attrib['name']
        statuses[status] += 1
        nodes.append(dict(nodeid=node, status=status, seconds=float(case.attrib.get('time', 0))))
    assert len({x['nodeid'] for x in nodes}) == len(nodes), path
    suites = root.findall('testsuite') if root.tag != 'testsuite' else [root]
    return dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                counts=statuses, selected=len(nodes), unique=len(nodes), nodes=nodes,
                suite_seconds=sum(float(x.attrib.get('time', 0)) for x in suites))

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
assert head == FROZEN, head
before = json.loads((ROOT / 'final-source-before.json').read_text())
names = subprocess.check_output(['git', 'ls-files', '-z', 'src', 'tests', 'pyproject.toml'], cwd=REPO).decode().split('\0')
files = {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in names if name}
diff = {name: [before['files'].get(name), files.get(name)]
        for name in set(before['files']) | set(files) if before['files'].get(name) != files.get(name)}
assert not diff and len(files) == 434, diff
dump(ROOT / 'final-source-after.json', dict(head=head, files=files, differences=diff,
     selection='all git-tracked src/tests/pyproject; no suffix exclusion'))

actual = xml_result(ROOT / 'final.xml')
actual.update(head=head, process_exit=json.loads((ROOT / 'final-process-exit.json').read_text()),
              source_entries=len(files), source_differences=0, outer_wall_seconds='NOT_RECORDED')
log = (ROOT / 'final.log').read_text()
assert re.search(r'\b[0-9]+ passed\b', log), 'Pytest final summary not received'
actual['pytest_summary'] = log.splitlines()[-1]
dump(ROOT / 'final-results.json', actual)

history = [xml_result(p) for p in sorted(ROOT.glob('*.xml')) if p.name != 'final.xml']
dump(ROOT / 'historical-rounds.json', dict(rounds=history, warning='Historical rounds are separate executions and source states; do not add them to final node counts.',
     historical_failures=sum(x['counts']['FAIL'] for x in history), historical_errors=sum(x['counts']['ERROR'] for x in history)))

ui = []
for folder in sorted((ROOT / 'final-tmp').glob('test_natural_spec_page_actual*')):
    if folder.is_symlink():
        continue
    path = folder / 'results.json'
    if not path.exists():
        continue
    value = json.loads(path.read_text())
    ui.append(dict(scenario=value['scenario'], status=value['status'], checks=len(value['checks']),
                   distinct_assets=len(value['loaded_source_sha256']), asset_gets=len(value['static_resource_loads']),
                   browser=value['browser'], api=value['api'], results_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   path=str(path.relative_to(ROOT)), loaded_source_sha256=value['loaded_source_sha256']))
assert len(ui) == 5 and len({x['scenario'] for x in ui}) == 5, ui
dump(ROOT / 'final-ui-summary.json', dict(cases=ui, total_checks=sum(x['checks'] for x in ui),
     total_asset_gets=sum(x['asset_gets'] for x in ui), native_browser='NOT_RUN'))
print(json.dumps({k: v for k, v in actual.items() if k != 'nodes'}, ensure_ascii=False, indent=2))
