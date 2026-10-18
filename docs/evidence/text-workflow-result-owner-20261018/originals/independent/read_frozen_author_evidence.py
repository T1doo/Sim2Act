"""Independently read and recompute saved evidence; this does not run the Worker/UI."""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

BASE = Path('/workspace/text-workflow-result-owner-evidence-20261018')
OUT = Path(__file__).parent
P = BASE / 'qualified-positive-temp/test_actual_two_inputs_same_in0'
facts = json.loads((P / 'text-owner-proof.json').read_text())
http = json.loads((P / 'text-owner-http.json').read_text())
checks = []
def check(value, label):
    assert value, label
    checks.append(label)

for name in ('first_contract', 'second_contract'):
    c = facts[name]
    material, output, chunks = c['material'], c['output'], []
    check(hashlib.sha256(material['content'].encode()).hexdigest() == material['hash'] == output['source_hash'], name + ': exact material SHA256')
    for side in ('a', 'b'):
        term = c['input']['term_' + side]
        quotes = [{'start_line': n, 'end_line': n, 'quote': line} for n, line in enumerate(material['content'].splitlines(), 1) if term in line]
        check(output['citations_' + side] == quotes, name + ': independent complete-line citations ' + side)
        chunks.append(side.upper() + ': ' + term)
        chunks.extend('L' + str(x['start_line']) + ': ' + x['quote'] for x in quotes)
        if not quotes:
            chunks.append('No literal matches')
    check(output['text'] == '\n'.join(chunks), name + ': independent complete report assembly')
    check([r['step_id'] for r in c['actual_operations']] == ['read', 'lookup_a', 'lookup_b', 'report'] and all(r['status'] == 'VERIFIED' for r in c['actual_operations']), name + ': four VERIFIED receipts')

first, second = facts['first_contract'], facts['second_contract']
check(first['run_id'] != second['run_id'] and first['app_run_id'] != second['app_run_id'], 'distinct Run and AppRun')
check(first['instance_id'] == second['instance_id'] == facts['same_business_instance'], 'same business instance')
check(first['result_version'] == 1 and second['result_version'] == 2, 'new typed result version')
check(facts['second_state']['owner_acceptance'] == 'PENDING' and facts['second_state']['sequence'] == 0 and facts['second_state']['history'] == [], 'new Run has empty PENDING journal')
check(facts['old_state']['owner_acceptance'] == 'STALE' and facts['old_state']['content_access'] is False and 'current' not in facts['old_state'] and 'payload' not in facts['old_state']['recovered'], 'old accepted receipt is metadata only after new result')
check(facts['cold_preview']['payload']['contract'] == first and facts['cold_decision']['current'] == first and facts['cold_decision']['owner_acceptance'] == 'ACCEPTED', 'cold GET bodies equal exact first contract and accepted state')
check(facts['actual_complete_runs'] == 2 and facts['actual_worker'] and facts['real_model_requests'] == 0, 'author actual Worker facts retain bounded zero-model scope')
decoded = [dict(row, response=json.loads(row['response']) if isinstance(row.get('response'), str) else row.get('response')) for row in http]
check(all(any(row['status'] == 200 and row['response'].get('id') == c['run_id'] and row['response'].get('status') == 'SUCCEEDED' for row in decoded if isinstance(row.get('response'), dict)) for c in (first, second)), 'raw HTTP includes both successful actual Run responses')

junits = {}
for name in ('frozen-backend-junit.xml', 'qualified-positive-junit.xml', 'qualified-ui-junit.xml', 'shared-regression-junit.xml', 'shared-pb-junit.xml'):
    path = BASE / name
    if path.exists():
        cases = []
        for c in ET.parse(path).iter('testcase'):
            cases.append({'name': c.attrib['name'], 'status': 'FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS', 'time': c.attrib.get('time')})
        junits[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'cases': cases}

ui, seen_ui_paths = [], set()
source_hashes = json.loads((OUT / 'freeze-source-integrity.json').read_text())['source_files']
for path in sorted((BASE / 'qualified-ui-temp').glob('*/page-result.json')):
    if path.resolve() in seen_ui_paths:
        continue
    seen_ui_paths.add(path.resolve())
    result = json.loads(path.read_text())
    assets = result['static_resource_loads']
    before = json.loads((path.parent / 'source-before.json').read_text())
    after = json.loads((path.parent / 'source-after.json').read_text())
    assert before == after
    monitored_production = set(before) & set(source_hashes)
    omitted_production = set(source_hashes) - set(before)
    monitored_tests = set(before) - set(source_hashes)
    assert omitted_production == {'src/sim2act/text_software_anchors.json', 'src/sim2act/text_software_qualification.json'}
    assert monitored_tests == {'tests/test_text_workflow_owner_ui.py', 'tests/text_workflow_owner_ui.cjs'}
    assert all(before[name]['sha256'] == source_hashes[name]['sha256'] and before[name]['bytes'] == source_hashes[name]['bytes'] for name in monitored_production)
    for name in monitored_tests:
        blob = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', 'show', '89c4d6ef9d223d99bd664311ed61d15943b96d7a:' + name], cwd='/workspace/Sim2Act')
        assert before[name] == {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
    ipc = json.loads((path.parent / 'ipc.json').read_text())
    page_http = [item['value'] for item in ipc if item['direction'] == 'NODE_TO_PYTHON' and item['value'].get('method') in ('GET', 'POST') and item['value'].get('path', '').startswith('/api/')]
    run_summary = json.loads((path.parent / 'run-summary.json').read_text())
    assert run_summary['status'] == 'PASS' and run_summary['real_model_requests'] == 0
    asset_checks = []
    for asset in assets:
        source = 'src/sim2act/web/' + asset['path'].lstrip('/') if asset['path'] != '/' else 'src/sim2act/web/index.html'
        if source not in source_hashes:
            raise AssertionError('Unexpected observed asset ' + source)
        assert asset['sha256'] == source_hashes[source]['sha256'], source
        asset_checks.append({'path': source, 'exact_freeze_equal': True})
    ui.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'status': result.get('status'), 'scenario': result['scenario'], 'qualification_role': result['qualification_role'], 'classification': result['classification'], 'checks': result['checks'], 'asset_observations': len(assets), 'asset_checks': asset_checks, 'production_sources_monitored_before_after': len(monitored_production), 'test_inputs_monitored_before_after': len(monitored_tests), 'production_sources_unmonitored_by_author_ui_manifest': sorted(omitted_production), 'monitored_source_changes': [], 'page_api_http_count': len(page_http), 'run_summary': run_summary, 'top_level_keys': list(result)})

result = {'classification': 'INDEPENDENT_READBACK_OF_AUTHOR_QUALIFIED_RAW_EVIDENCE_NOT_RERUN',
    'production_freeze': 'd7251b79d4dc17af6665f7a93eef8ffcfefa8603',
    'qualified_test_head': '89c4d6ef9d223d99bd664311ed61d15943b96d7a',
    'checks': checks, 'raw_http_count': len(http),
    'evidence_hashes': {name: hashlib.sha256((P / name).read_bytes()).hexdigest() for name in ('text-owner-proof.json', 'text-owner-http.json')},
    'junit_readbacks': junits, 'ui_readbacks': ui,
    'limitations': [
        'Actual Worker execution and separate cold Store/TestClient come from author test code plus qualified JUnit; this reviewer did not run them.',
        'The saved source/citations/report were independently recomputed. This is not an additional product case.',
        'Frozen backend original positive observer failure remains in raw JUnit; its positive replacement passed separately.',
        'An initial readback assertion expected parsed dictionaries; actual HTTP originals preserve response bodies as strings. Only this audit parser was corrected to decode those strings.',
        'No native browser, real model, PG, Windows, remote CI or complete product acceptance claim.']}
(OUT / 'freeze-author-evidence-independent-readback.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'independent_positive_checks': len(checks), 'raw_http': len(http),
    'junit_files': list(junits), 'ui': [{'status': x['status'], 'checks': len(x['checks']), 'assets': x['asset_observations']} for x in ui]}, indent=2))
