"""Pure-file audit. Do not invoke against live evidence; requires --all-closed."""
import argparse
import base64
import collections
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def sha(data):
    return hashlib.sha256(data).hexdigest()


def is_db(path):
    return bool(re.search(r'\.(db|sqlite|sqlite3)($|[-.])', Path(path).name.lower()))


def regular(root, relative):
    path = root / relative
    assert not path.is_symlink(), ('symlink', relative)
    assert path.resolve().is_relative_to(root.resolve()), ('outside', relative)
    assert path.is_file(), ('missing', relative)
    return path


def read_json(path):
    assert not is_db(path), ('DB read forbidden', str(path))
    return json.loads(path.read_bytes())


def manifest_entries(value):
    entries = value.get('files', value) if isinstance(value, dict) else value
    if isinstance(entries, dict):
        return [{'path': name, **entry} for name, entry in entries.items()]
    assert isinstance(entries, list)
    return entries


def audit_manifest(root, name, expected_sha):
    path = regular(root, name)
    payload = path.read_bytes()
    assert sha(payload) == expected_sha
    value = json.loads(payload)
    verified, db_stats = [], []
    for entry in manifest_entries(value):
        relative = entry['path']
        item = regular(root, relative)
        size = item.stat().st_size
        if is_db(item):
            db_stats.append({'path': relative, 'bytes': size, 'stat_only': True})
            continue
        raw = item.read_bytes()
        assert len(raw) == entry['bytes'], relative
        assert sha(raw) == entry['sha256'], relative
        verified.append({'path': relative, 'bytes': len(raw), 'sha256': sha(raw)})
    for relative in value.get('excluded_external_sqlite_fixtures_and_manifest', []):
        if is_db(relative):
            item = regular(root, relative)
            db_stats.append({'path': relative, 'bytes': item.stat().st_size, 'stat_only': True})
    return {'manifest_sha256': sha(payload), 'non_db_files': len(verified),
            'non_db_bytes': sum(e['bytes'] for e in verified), 'files': verified,
            'db_stat_only': db_stats}


def audit_execution(folder):
    execution = read_json(folder / 'execution.json')
    assert 'exit_code' in execution and 'ended_utc' in execution, ('not closed', str(folder))
    before, after = [read_json(folder / n) for n in ('inputs-before.json', 'inputs-after.json')]
    assert before == after, ('input drift', str(folder))
    hbefore, hafter = [read_json(folder / n) for n in ('helpers-before.json', 'helpers-after.json')]
    assert hbefore == hafter, ('helper drift', str(folder))
    for name, entry in hbefore.items():
        copy = folder / ('runner.py' if name in ('run_stages.py', 'runner.py') else name)
        assert copy.is_file(), ('helper copy absent', str(copy))
        data = copy.read_bytes()
        assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], str(copy)
    cases = []
    junit = folder / 'junit.xml'
    if junit.is_file():
        for item in ET.fromstring(junit.read_bytes()).iter('testcase'):
            status = ('ERROR' if item.find('error') is not None else
                      'FAIL' if item.find('failure') is not None else
                      'SKIPPED' if item.find('skipped') is not None else 'PASS')
            cases.append({'name': item.get('name'), 'classname': item.get('classname'),
                          'status': status, 'seconds': item.get('time')})
    guard = read_json(folder / 'offline-guard.json')
    assert guard['attempts'] == [], ('forbidden IO guard', str(folder))
    methods = collections.Counter(m['method'] for m in guard['adapter_methods'])
    families = collections.Counter(m['family'] for m in guard['adapter_methods']
                                   if m['method'] == 'request_serialized_captured')
    for hb in guard.get('heartbeats', []):
        assert 0 < hb['lease_seconds'] <= 30
        assert hb['renewed_until'] <= hb['committed_at'] + 30.001
    return {'directory': folder.name, 'source_commit': execution['source_commit'],
            'exit_code': execution['exit_code'], 'elapsed_seconds': execution['elapsed_seconds'],
            'input_metadata_count': len(before['inputs']), 'input_metadata_zero_drift': True,
            'helper_metadata_zero_drift_and_copies_match': True, 'cases': cases,
            'adapter_method_counts': dict(methods), 'captured_adapter_families': dict(families),
            'forbidden_guard_attempts': [], 'successful_original_heartbeats': len(guard.get('heartbeats', []))}


def audit_positive(path):
    value = read_json(path)
    accounting = value['accounting']
    ledger = accounting['ledger']
    slots = ledger['slots']
    assert len(slots) == 7 and not ledger['halted'] and all(s['accepted'] for s in slots)
    assert collections.Counter(s['identity']['stage'] for s in slots) == {'generate': 3, 'source': 2, 'cold': 2}
    attempts = value['actual_attempts']
    assert {a['id'] for a in attempts} == {s['identity']['attempt_id'] for s in slots}
    assert len(attempts) == 7
    actual_gaps = [b['reserved_at'] - a['reserved_at'] for a, b in zip(slots, slots[1:])]
    assert actual_gaps == value['gaps'] and all(g >= 60 for g in actual_gaps)
    responses, requests = 0, 0
    for entry in value['bodies']:
        body = entry['snapshot']['response']
        raw = base64.b64decode(body['body_b64'], validate=True)
        assert base64.b64encode(raw).decode('ascii') == body['body_b64']
        assert len(raw) == body['byte_count'] and sha(raw) == body['sha256']
        assert body['received_complete'] is True
        if entry['kind'] == 'pa_trial_response_body.v1':
            parsed = json.loads(raw)
            canonical = json.dumps(parsed, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode('ascii')
            assert sha(canonical) == body['canonical_sha256']
            assert sha(raw) != sha(canonical)
            responses += 1
        else:
            assert entry['kind'] == 'pa_trial_request_body.v1'
            requests += 1
    assert requests == responses == 7
    for stage in ('source', 'cold'):
        item = value['results'][stage]
        artifact = item['artifact']['resource']
        assert sha(artifact['content'].encode()) == artifact['hash']
        assert json.loads(artifact['content'])['source_content'] == item['result']['result']['checklist']['source_content']
        assert item['owner_review']['run_id'] == item['run_id']
        assert item['owner_review']['owner_acceptance'] == 'PENDING'
        assert item['history']['dispatch_authorized'] is False
    cold = value['results']['cold']
    source = value['results']['source']
    assert cold['owner_review']['content_access'] is True
    assert cold['owner_review']['current']['run_id'] == cold['run_id']
    assert cold['owner_review']['current']['material']['content'] == cold['result']['result']['checklist']['source_content']
    assert source['owner_review']['content_access'] is False
    assert source['owner_review']['invalidation_reason'] == 'VERSION_CONFLICT'
    assert value['real_provider_calls'] == 0 and value['live_installed'] is False
    assert value['semantic_acceptance'] == 'NOT_RUN'
    return {'path': str(path), 'sha256': sha(path.read_bytes()), 'slots': 7,
            'stage_calls': {'generate': 3, 'source': 2, 'cold': 2}, 'actual_attempts': 7,
            'raw_request_archives': requests, 'raw_response_archives': responses,
            'all_seven_response_raw_canonical_hashes_distinct': True,
            'current_cold_owner_content_access': True, 'source_prior_owner_content_access': False,
            'simulated_checklist_fact_source': 'saved fixture and recorded response only',
            'semantic_acceptance': 'NOT_RUN', 'live_installed': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all-closed', action='store_true')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', default='sealed-manifest.json')
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--positive-relative', required=True)
    parser.add_argument('--qualification-freeze', required=True)
    parser.add_argument('--qualified-run', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.all_closed, 'Explicit parent confirmation of all closed executions is required'
    root = args.root.resolve()
    manifest = audit_manifest(root, args.manifest, args.manifest_sha256)
    runs = [audit_execution(folder) for folder in sorted(root.glob('run-*'))
            if folder.is_dir() and not folder.is_symlink() and (folder / 'execution.json').is_file()]
    qualified = [run for run in runs if run['directory'] in args.qualified_run]
    assert len(qualified) == len(set(args.qualified_run)) == 2
    expected = {
        'test_actual_pa_three_two_two_reaches_existing_results_and_pending_owner',
        'test_fresh_actual_prefix_rejects_incomplete_mixed_or_changed_proof_without_writes',
        'test_known_accounting_cannot_accept_wrong_original_business_schema',
        'test_original_controller_store_is_fixed_through_late_body_and_failure',
    }
    selected_cases = [case for run in qualified for case in run['cases']]
    assert len(selected_cases) == 4 and {case['name'] for case in selected_cases} == expected
    assert all(run['source_commit'] == args.qualification_freeze and run['exit_code'] == 0 for run in qualified)
    assert all(case['status'] == 'PASS' for case in selected_cases)
    assert Path(args.positive_relative).parts[0] in args.qualified_run
    result = {'review_kind': 'INDEPENDENT_PURE_FILE_AUDIT_NO_PRODUCT_EXECUTION',
              'current_qualification': {'source': args.qualification_freeze,
                  'run_directories': args.qualified_run, 'unique_nodes': 4,
                  'cases': selected_cases, 'all_current_pass': True},
              'manifest': manifest, 'executions': runs,
              'positive': audit_positive(regular(root, args.positive_relative)),
              'limits': ['No DB contents opened or hashes recomputed',
                         'Input map metadata compared; DB/archive bytes not independently hashed',
                         'Full 55-table row equality rests on executed strict assertions plus retained proof, not an independent row reconstruction',
                         'No provider/Worker/model/API/product test rerun']}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'PURE_FILE_PASS', 'runs': len(runs),
                      'manifest_non_db_files': manifest['non_db_files'],
                      'manifest_non_db_bytes': manifest['non_db_bytes']}))


if __name__ == '__main__':
    main()
