import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path('/workspace/pb-extraction-close-evidence-20261018')
reports = []
for name in ['backend', 'ui', 'final-backend', 'final-ui', 'qualified-backend', 'qualified-ui']:
    path = root / (name + '-junit.xml')
    if not path.exists():
        continue
    tree = ET.parse(path)
    cases = []
    for case in tree.iter('testcase'):
        result = 'PASS'
        if case.find('failure') is not None:
            result = 'FAIL'
        elif case.find('error') is not None:
            result = 'ERROR'
        elif case.find('skipped') is not None:
            result = 'SKIP'
        elif not case.get('name'):
            result = 'UNNAMED_NOT_QUALIFIED'
        cases.append(dict(name=case.get('name'), seconds=float(case.get('time', 0)), result=result))
    reports.append(dict(batch=name, cases=cases, exit_code=int((root / (name + '-exit.txt')).read_text()),
        suite_attributes=[node.attrib for node in tree.iter('testsuite')]))
pages = []
seeds = []
http_counts = {}
def real_entry(path, base):
    return not any(parent.is_symlink() for parent in [path, *path.parents]
        if parent.is_relative_to(base))

for folder in ['backend-data', 'ui-data', 'final-backend-data', 'final-ui-data',
    'qualified-backend-data', 'qualified-ui-data']:
    data = root / folder
    for path in sorted(data.glob('*/page-result.json')):
        if not real_entry(path, data):
            continue
        value = json.loads(path.read_text())
        pages.append(dict(batch=folder, scenario=value['scenario'], status=value['status'],
            checks=len(value['checks']), actions=len(value['actions']), api=len(value['requests']),
            assets=len(value['static_resource_loads']), boots=value['boots'],
            terminal_digest_observations=len(value.get('terminal_digest_observations', [])),
            page_worker_calls=value['worker_calls'], error=value.get('error')))
    for path in data.glob('pb-extraction-close-fresh-source-seed*/progress-summary.json'):
        if not real_entry(path, data):
            continue
        value = json.loads(path.read_text())
        seeds.append(dict(batch=folder, generation_requests=value['provider_requests'],
            source_requests=value['runtime_requests'], summary=value))
    counts = {}
    for path in data.glob('*/http/*-metadata.json'):
        if not real_entry(path, data):
            continue
        row = json.loads(path.read_text())
        counts[str(row['status'])] = counts.get(str(row['status']), 0) + 1
    http_counts[folder] = dict(total=sum(counts.values()), by_status=counts,
        seed_http=sum(1 for path in data.glob('pb-extraction-close-fresh-source-seed*/http/*-metadata.json')
            if real_entry(path, data)))
before = json.loads((root / 'execution-inputs-before.json').read_text())
after = json.loads((root / 'execution-inputs-after.json').read_text())
middle_before = json.loads((root / 'final-execution-inputs-before.json').read_text())
middle_after = json.loads((root / 'final-execution-inputs-after.json').read_text())
final_before = json.loads((root / 'qualified-execution-inputs-before.json').read_text())
final_after = json.loads((root / 'qualified-execution-inputs-after.json').read_text())
assert before['inputs'] == after['inputs']
assert final_before['inputs'] == final_after['inputs']
assert middle_before['inputs'] == middle_after['inputs']
changes = [name for name in sorted(before['inputs']) if before['inputs'][name] != final_before['inputs'][name]]
assert changes == ['src/sim2act/pb_extraction_terminals.py', 'src/sim2act/pb_natural_specs.py',
    'tests/test_pb_extraction_close.py'], changes
final_reports = [report for report in reports if report['batch'].startswith('qualified-')]
assert len(final_reports) == 2 and sum(len(row['cases']) for row in final_reports) == 9
assert all(row['exit_code'] == 0 and all(case['result'] == 'PASS' for case in row['cases']) for row in final_reports)
assert len(seeds) == 6 and all(row['generation_requests'] == 3 and row['source_requests'] == 1 for row in seeds)
result = dict(reports=reports, pages=pages, model_seeds=seeds,
    model_requests_total=sum(row['generation_requests'] + row['source_requests'] for row in seeds),
    real_model_requests=0, source_worker_calls=6, page_worker_calls=0,
    unique_focused_nodes=9, qualification_final_input_count=final_before['input_count'],
    qualification_final_production_count=final_before['production_count'],
    initial_source=before['head'], final_execution_source=final_before['head'],
    within_each_phase_input_drift=0, changed_inputs_between_phases=changes,
    actual_http=http_counts,
    scope_notes=['Every module/process fresh seed independently contributes generation3/sourceWorker1 Mock requests.',
        'Page delayed original POST and real WebCrypto result delivery are controlled fixtures; real two-connection SQLite overlap is backend scope.',
        'Resource read barrier is actual; complete private journal-cell read ordering is static source review, not a journal-cell runtime barrier.',
        'No native/Windows/PG/real semantic/model/remote CI/deployment qualification.'])
(root / 'execution-summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k not in {'reports', 'model_seeds', 'scope_notes'}}, ensure_ascii=False))
