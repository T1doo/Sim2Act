"""Aggregate completed current suites; interrupted history is never a PASS input."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent


def read(path):
    return json.loads(path.read_text())


def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    suites = []
    seen = set()
    sources = []
    for label in ['frozen-backend', 'frozen-ui']:
        result = read(ROOT / f'{label}-result.json')
        assert result['returncode'] == 0, (label, result)
        assert not result['source_changes']
        cases = ET.parse(ROOT / f'{label}.xml').getroot().findall('.//testcase')
        nodes = [f"{c.attrib['classname']}::{c.attrib['name']}" for c in cases]
        assert len(nodes) == len(set(nodes))
        assert not (seen & set(nodes))
        seen.update(nodes)
        suites.append({'label': label, 'result': result, 'nodes': nodes})
        for side in ['before', 'after']:
            path = ROOT / f'{label}-source-{side}.json'
            current = read(path)
            assert current['head'] == 'bea218d546cd1578e5bf0450c9be9ad9b1667f4e'
            if sources:
                assert current['files'] == sources[0]['files']
            sources.append(current)
    dump('final-summary.json', {
        'tested_head': sources[0]['head'], 'unique_selected': len(seen),
        'passed': sum(x['result']['passed'] for x in suites),
        'failed': sum(x['result']['failed'] for x in suites),
        'errors': sum(x['result']['errors'] for x in suites),
        'skipped': sum(x['result']['skipped'] for x in suites),
        'source_files': len(sources[0]['files']), 'source_changes': [],
        'suites': suites, 'real_model_requests': 0, 'actual_model_fees': 0,
    })
    ui = []
    for path in sorted((ROOT / 'frozen-ui-tmp').glob('*/results.json')):
        if path.parent.is_symlink():
            continue
        data = read(path)
        assert data['status'] == 'PASS', path
        ui.append({
            'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'scenario': data.get('scenario', path.parent.name), 'status': data['status'],
            'checks': len(data['checks']), 'requests': len(data.get('requests', [])),
            'downloads': len(data.get('downloads', [])),
            'static_resource_loads': len(data.get('static_resource_loads', [])),
            'source_assets': data.get('loaded_source_sha256'),
        })
    dump('final-ui-summary.json', ui)
    observations = []
    for label in ['red-callback-r3', 'frozen-backend']:
        for path in sorted((ROOT / f'{label}-tmp').glob('*/callback-private-cells.json')):
            if path.parent.is_symlink():
                continue
            data = read(path)
            observations.append({key: data[key] for key in [
                'boundary', 'change', 'reached', 'error', 'observed', 'calibration',
                'lease_valid', 'deadline_valid', 'real_model_requests'
            ]} | {'label': label, 'path': str(path.relative_to(ROOT)),
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    dump('final-callback-observations.json', observations)
    print(json.dumps({'suites': len(suites), 'unique_cases': len(seen), 'ui_evidence': len(ui),
                      'callback_observations': len(observations)}))


if __name__ == '__main__':
    main()
