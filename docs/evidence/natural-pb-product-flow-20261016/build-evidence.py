from pathlib import Path
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET

root = Path('/workspace/Sim2Act')
base = Path('/workspace')
dest = root / 'docs/evidence/natural-pb-product-flow-20261016'
summaries = []
nodes = []
for label in ['product', 'first', 'shared']:
    stem = 'pb-guide-final-' + label
    tree = ET.parse(base / (stem + '.xml')).getroot()
    cases = list(tree.iter('testcase'))
    assert not list(tree.iter('failure')) and not list(tree.iter('error')) and not list(tree.iter('skipped'))
    keys = [c.attrib['classname'] + '::' + c.attrib['name'] for c in cases]
    nodes.extend(keys)
    summaries.append(dict(module=label, passed=len(cases), failures=0, skipped=0,
                          duration_seconds=sum(float(s.attrib.get('time', 0)) for s in tree.iter('testsuite')),
                          nodes=keys))
    for ext in ['.xml', '.log']:
        shutil.copy2(base / (stem + ext), dest / (stem + ext))
    source = base / stem
    for p in source.rglob('*'):
        if p.is_file() and p.suffix in ['.json', '.log', '.stderr', '.txt', '.xml']:
            target = dest / ('final-' + label) / p.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
assert len(nodes) == 11 and len(set(nodes)) == 11
freeze = json.loads((dest / 'pb-guide-freeze-source-hashes.json').read_text())
for name, sha in freeze['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, name
pb_dir = next((dest / 'final-product').glob('test_successful_source_to_pb_d0'))
pb = json.loads((pb_dir / 'result.json').read_text())
assert pb['status'] == 'PASS'
post_extract = [r for r in pb['requests'] if r['method'] == 'POST' and r['path'].endswith('/extractions')]
post_use = [r for r in pb['requests'] if r['method'] == 'POST' and r['path'].endswith('/pb-use-runs')]
assert len(post_extract) == len(post_use) == 1
assert post_extract[0]['status'] == 201 and post_extract[0]['delivery_fault'] == 'ACTUAL_ACCEPTED_201_REPLY_LOST_SYNTHETIC'
claims = []
for p in (dest / 'final-product').rglob('worker-claims-*.json'):
    d = json.loads(p.read_text())
    assert d['claims'][-1]['after']['status'] == 'SUCCEEDED'
    claims.append(dict(run_id=d['run_id'], actual_claims=len(d['claims']), status='SUCCEEDED'))
wire_counts = {name: len(json.loads((pb_dir / name).read_text())) for name in ['source-generation-wire.json', 'source-worker-wire.json', 'runtime-wire.json']}
assert wire_counts == {'source-generation-wire.json': 3, 'source-worker-wire.json': 1, 'runtime-wire.json': 1}
runtime = json.dumps(json.loads((pb_dir / 'runtime-wire.json').read_text()), ensure_ascii=False)
assert 'field beacon' in runtime and 'desk lamp' not in runtime and 'garden sensor' not in runtime
sha_checks = json.loads((dest / 'pb-guide-final-js-checks.json').read_text())
assert len(sha_checks) == 19 and all(r['exit_code'] == 0 for r in sha_checks)
assert 'All checks passed!' in (dest / 'pb-guide-final-ruff.log').read_text()
summary = dict(freeze=freeze['git_sha'], unique_tests=11, passed=11, failures=0, skipped=0,
               modules=summaries, frozen_source_and_test_files_unchanged=len(freeze['files']),
               pb=dict(checks=len(pb['checks']), visible_gestures=len(pb['actions']), boots=pb['boots'],
                       loaded_assets=len(pb['static_resource_loads']), extraction_posts=1, per_use_posts=1,
                       actual_accepted_reply_lost_then_original_key_get=True, worker_claims=claims,
                       mock_wire_counts=wire_counts, original_source_result_versions=[1], new_pb_result_versions=[1],
                       runtime_wire_contains_new_material_only=True, owner_acceptance='PENDING'),
               independent=dict(repeated_node_not_added_to_unique_count=True, dom_checks=38, isolated_checks=21,
                                scope='Read-only static and lightweight dynamic review; no remaining blocking finding'),
               static=dict(ruff='PASS', production_js_syntax=19),
               real_model_requests=0, windows='NOT_RUN', native_browser='NOT_RUN', pg='NOT_RUN', remote_ci='NOT_RUN',
               real_human_semantics='NOT_RUN', legacy_recovery_matrix='NOT_RUN', deployment='NOT_RUN',
               old_multiple_history_heartbeat_lock_issue='OPEN_NOT_RETESTED', old_unwritten_independent_report='NOT_RECOVERED')
(dest / 'final-verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
