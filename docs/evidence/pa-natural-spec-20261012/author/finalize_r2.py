"""Summarize the actual frozen complete rerun without replacing red history."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def dump(name, value):
    (ROOT / name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')

def xml_result(path):
    root = ET.parse(path).getroot()
    counts = dict(PASS=0,FAIL=0,ERROR=0,SKIP=0)
    nodes = []
    for case in root.findall('.//testcase'):
        status = ('FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None
                  else 'SKIP' if case.find('skipped') is not None else 'PASS')
        node = dict(nodeid=case.attrib['classname'].replace('.','/')+'.py::'+case.attrib['name'],
                    status=status,seconds=float(case.attrib.get('time',0)))
        for tag in ['failure','error','skipped']:
            detail = case.find(tag)
            if detail is not None:
                node['diagnostic'] = detail.attrib.get('message','')
        counts[status] += 1
        nodes.append(node)
    assert len({x['nodeid'] for x in nodes}) == len(nodes)
    suites = root.findall('testsuite') if root.tag != 'testsuite' else [root]
    return dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),counts=counts,
                selected=len(nodes),nodes=nodes,suite_seconds=sum(float(x.attrib.get('time',0)) for x in suites))

result = xml_result(ROOT/'final-r2.xml')
receipt = json.loads((ROOT/'final-r2-process-exit.json').read_text())
assert result['selected'] == 231 and receipt['source_entries'] == 434 and receipt['source_differences'] == 0
result.update(process=receipt,pytest_summary=(ROOT/'final-r2.log').read_text().splitlines()[-1])
dump('final-r2-results.json',result)
history = [xml_result(path) for path in sorted(ROOT.glob('*.xml')) if path.name != 'final-r2.xml']
dump('historical-rounds-r2.json',dict(rounds=history,historical_failures=sum(x['counts']['FAIL'] for x in history),
     historical_errors=sum(x['counts']['ERROR'] for x in history),
     warning='Distinct previous executions and source states. Never add them to final rerun counts or relabel a failed run.'))
ui = []
for folder in sorted((ROOT/'final-r2-tmp').glob('test_natural_spec_page_actual*')):
    if folder.is_symlink():
        continue
    path = folder/'results.json'
    if not path.exists():
        continue
    value = json.loads(path.read_text())
    ui.append(dict(scenario=value['scenario'],status=value['status'],checks=len(value['checks']),
                   distinct_assets=len(value['loaded_source_sha256']),asset_gets=len(value['static_resource_loads']),
                   browser=value['browser'],api=value['api'],path=str(path.relative_to(ROOT)),
                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),loaded_source_sha256=value['loaded_source_sha256']))
assert len(ui) == 5 and len({x['scenario'] for x in ui}) == 5
dump('final-r2-ui-summary.json',dict(cases=ui,total_checks=sum(x['checks'] for x in ui),
     total_asset_gets=sum(x['asset_gets'] for x in ui),native_browser='NOT_RUN'))
print(json.dumps({k:v for k,v in result.items() if k!='nodes'},indent=2))
