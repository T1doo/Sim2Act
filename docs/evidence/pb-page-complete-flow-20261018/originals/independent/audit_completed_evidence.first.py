"""Independent raw-artifact audit only. Never imports application/test modules."""

import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


REPO = Path('/workspace/Sim2Act')
EVIDENCE = Path('/workspace/pb-page-complete-evidence-20261018')
OUT = Path('/workspace/pb-page-complete-independent-20261018')
read_files = {}


def raw(path):
    data = path.read_bytes()
    read_files[str(path)] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data


def load(path):
    return json.loads(raw(path))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def response_value(data):
    try:
        return json.loads(data)
    except (ValueError, UnicodeDecodeError):
        return data.decode('utf-8')


def main():
    junit = ET.fromstring(raw(EVIDENCE / 'full-pb.xml'))
    cases = list(junit.iter('testcase'))
    assert len(cases) == 1
    case = cases[0]
    assert case.attrib['name'] == 'test_successful_source_to_pb_directory_and_new_material'
    assert all(case.find(name) is None for name in ['failure', 'error', 'skipped'])
    scenes = [p for p in (EVIDENCE / 'full-pb').iterdir()
              if p.is_dir() and not p.is_symlink() and (p / 'result.json').exists()]
    assert len(scenes) == 1
    scene = scenes[0]
    result = load(scene / 'result.json')
    assert result['status'] == 'PASS' and result['error'] is None
    assert len(result['checks']) == 63 and result['boots'] == 3
    assert result['real_model'] == result['native_browser'] == result['real_human_semantic_acceptance'] == 'NOT_RUN'
    assert result['run_id'] != result['source_run']
    info = load(scene / 'info.json')
    assert result['source_run'] == info['source_run']
    assert result['target_input'] != result['use_input']

    progress = [json.loads(line) for line in raw(scene / 'progress.jsonl').splitlines()]
    assert [e['sequence'] for e in progress] == list(range(1, len(progress) + 1))
    assert progress[0]['kind'] == 'test_start' and progress[-1]['kind'] == 'test_end'
    assert progress[-1]['passed'] is True and progress[-1]['watchdog_fired'] is False
    assert progress[-1]['node_exit_code'] == 0
    assert not [e for e in progress if e['kind'].endswith('_error')]
    summary = load(scene / 'progress-summary.json')
    assert summary['error_count'] == 0 and summary['watchdog_fired'] is False
    assert load(scene / 'errors.json') == []
    generation = load(scene / 'source-generation-wire.json')
    source = load(scene / 'source-worker-wire.json')
    runtime = load(scene / 'runtime-wire.json')
    assert [len(generation), len(source), len(runtime)] == [3, 1, 1]
    assert load(scene / 'model-wire.json') == generation
    generation_observation = load(scene / 'fixture-generation-observation.json')
    assert generation_observation['ready_returned'] is True
    assert generation_observation['exported_requests'] == 3

    claims = [load(p) for p in sorted(scene.glob('worker-claims-*.json'))]
    assert {p['run_id'] for p in claims} == {result['source_run'], result['run_id']}
    for claim in claims:
        assert 1 <= len(claim['claims']) <= claim['max_claims'] == 3
        assert claim['claims'][-1]['after']['status'] == 'SUCCEEDED'
        for item in claim['claims']:
            assert item['claimed'] is True
            assert item['before']['created_at'] == item['after']['created_at'] == claim['accepted_clock']['created_at']
            assert item['after']['fence'] > item['before']['fence']
            assert not item['after']['cancel_intent']
            assert item['before']['principal_id'] == item['after']['principal_id']
            assert item['before']['project_id'] == item['after']['project_id'] == info['project']

    metadata = []
    available = Counter()
    for path in sorted((scene / 'http').glob('*-metadata.json')):
        item = load(path)
        body = raw(scene / item['response_file'])
        assert len(body) == item['response_bytes']
        assert hashlib.sha256(body).hexdigest() == item['response_sha256']
        item['_value'] = response_value(body)
        metadata.append(item)
        available[(item['method'], item['path'], canonical(item['request']), item['status'], canonical(item['_value']))] += 1
    assert len(metadata) == summary['http_responses']
    assert len(metadata) == len([p for p in progress if p['kind'] == 'http_response_saved'])
    for request in result['requests']:
        value = request.get('response', request.get('response_text'))
        key = request['method'], request['path'], canonical(request.get('body')), request['status'], canonical(value)
        assert available[key] > 0, (request['method'], request['path'], request['status'])
        available[key] -= 1
    for asset in result['static_resource_loads']:
        path = REPO / 'src/sim2act/web' / ('index.html' if asset['path'] == '/' else asset['path'].lstrip('/'))
        expected = hashlib.sha256(raw(path)).hexdigest()
        assert asset['status'] == 200 and asset['sha256'] == expected
        assert any(m['path'] == asset['path'] and m['status'] == 200 and m['response_sha256'] == expected for m in metadata)

    owner_gets = [m for m in metadata if m['method'] == 'GET' and m['path'].endswith('/runs/' + result['run_id'] + '/spec-owner-review')]
    owner_posts = [m for m in metadata if m['method'] == 'POST' and m['path'].endswith('/spec-owner-review')]
    assert len(owner_gets) >= 2 and not owner_posts
    for item in owner_gets:
        assert item['status'] == 200
        assert item['_value']['owner_acceptance'] == 'PENDING'
        contract = item['_value']['current']
        assert contract['run_id'] == result['run_id'] and contract['result_version'] == 1
        assert contract['material']['resource_id'] == result['use_input']['resource_id']
        assert contract['source_goal']['card_id'] == result['use_input']['goal_id']
        assert contract['output']['checklist']['source_content'] == info['next_content']
    extracted = [r for r in result['requests'] if r['method'] == 'POST' and r['path'].endswith('/extractions')]
    use_runs = [r for r in result['requests'] if r['method'] == 'POST' and r['path'].endswith('/pb-use-runs')]
    assert len(extracted) == len(use_runs) == 1
    assert extracted[0]['status'] == 201 and extracted[0]['delivery_fault'] == 'ACTUAL_ACCEPTED_201_REPLY_LOST_SYNTHETIC'
    assert use_runs[0]['status'] == 202
    assert not [r for r in result['requests'] if r['method'] == 'POST' and 'application-provider-scopes' in r['path']]
    denied = [m for m in metadata if m['status'] == 403]
    assert any(m['path'] == '/api/apps/' + result['app_id'] for m in denied)
    assert any(m['path'] == '/api/apps/' + info['source_app'] for m in denied)

    proof = load(scene / 'source-preservation-proof.json')
    assert proof['original_result_versions'] == proof['new_pb_result_versions'] == [1]
    assert proof['source_run'] == info['source_run'] and proof['new_pb_instance'] == result['instance_id']
    assert proof['original_result_rows_unchanged'] is proof['original_artifact_row_unchanged'] is True
    assert proof['real_model_requests'] == 0
    checkpoints = load(scene / 'checkpoints.json')
    boundary = load(scene / 'boundary-receipts.json')
    assert len(boundary) == 2 and [r['status'] for r in boundary] == [200, 200]
    db = scene / 'fixture.db'
    db_before = raw(db)
    con = sqlite3.connect(db.as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        runs = con.execute('SELECT id,status FROM runs ORDER BY id').fetchall()
        versions = con.execute('SELECT instance_id,version FROM internal_instance_data ORDER BY instance_id,version').fetchall()
        owner_count = con.execute('SELECT count(*) FROM natural_owner_records').fetchone()[0]
        extraction_count = con.execute('SELECT count(*) FROM task_extractions').fetchone()[0]
    finally:
        con.close()
    assert raw(db) == db_before
    assert sorted(runs) == sorted([(result['source_run'], 'SUCCEEDED'), (result['run_id'], 'SUCCEEDED')])
    assert sorted(versions) == sorted([(info['source_instance'], 1), (result['instance_id'], 1)])
    assert owner_count == 0 and extraction_count == 1
    after = load(EVIDENCE / 'inputs-after.json')
    before = load(EVIDENCE / 'inputs-before.json')
    assert after['inputs'] == before['inputs']
    current_changes = [p for p, v in before['inputs'].items() if hashlib.sha256((REPO / p).read_bytes()).hexdigest() != v['sha256']]
    assert not current_changes
    report = dict(classification='NON_AUTHOR_RAW_READBACK_AND_PURE_RECOMPUTATION_ONLY',
        recorded_utc=datetime.now(UTC).isoformat(), qualification_freeze=before['head'],
        junit_cases=1, junit_seconds=float(case.attrib['time']), checks=len(result['checks']),
        actions=len(result['actions']), boots=result['boots'], page_api_requests=len(result['requests']),
        served_assets=len(result['static_resource_loads']), total_observed_http=len(metadata),
        observed_extra_fixture_and_boundary_http=len(metadata)-len(result['requests'])-len(result['static_resource_loads']),
        observed_mock_requests=dict(generation=len(generation), source_worker=len(source), pb_worker=len(runtime)),
        worker_claims={c['run_id']: len(c['claims']) for c in claims},
        checkpoints=len(checkpoints), owner_gets=len(owner_gets), owner_posts=len(owner_posts),
        final_db_readonly=dict(runs=runs, result_versions=versions, natural_owner_records=owner_count, task_extractions=extraction_count, bytes_unchanged=True),
        source_preservation=proof, complete_input_count=len(before['inputs']), input_changes=current_changes,
        product_tests_executed_by_reviewer=0, watchdog_fired=False,
        scope_limits=['manual decision remains PENDING; no owner POST', 'PB first v1 only; no PB v1 to v2 claim',
                      'original source preservation denominator is original test source_unchanged, not all run/event rows',
                      'permanently cancelled precise install digest concurrency comparison remains NOT_VERIFIED',
                      'no real models, real semantic acceptance, native browser, Windows, PG, remote CI or deployment qualification'],
        read_files=read_files)
    (OUT / 'completed-raw-evidence-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['read_files', 'source_preservation']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
