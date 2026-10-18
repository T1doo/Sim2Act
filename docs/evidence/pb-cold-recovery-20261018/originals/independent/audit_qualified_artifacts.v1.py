"""Pure completed-artifact recomputation. No product/test imports or HTTP calls."""

import argparse
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/workspace/Sim2Act')
OUT = Path('/workspace/pb-cold-recovery-independent-20261018')
READ = {}
FIELDS = set('namespace principal_id project_id source_app_id source_instance_id source_run_id source_app_run_id source_release_id source_release_fingerprint source_result_version request_key request_fingerprint review_fingerprint candidate_fingerprint app_id runtime_id source_proof_fingerprint'.split())


def raw(path):
    value = path.read_bytes()
    READ[str(path)] = dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest())
    return value


def load(path):
    return json.loads(raw(path))


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canon(value).encode()).hexdigest()


def decode(value):
    try:
        return json.loads(value)
    except (ValueError, UnicodeDecodeError):
        return value.decode('utf-8')


def rowset(rows):
    return Counter(canon(row) for row in rows)


def observer(folder):
    summary = load(folder / 'progress-summary.json')
    progress = [json.loads(line) for line in raw(folder / 'progress.jsonl').splitlines()]
    assert [r['sequence'] for r in progress] == list(range(1, len(progress) + 1))
    assert progress[-1]['kind'] == 'test_end' and progress[-1]['passed'] is True
    assert summary['error_count'] == 0 and summary['watchdog_fired'] is False
    assert load(folder / 'errors.json') == []
    for path, value in load(folder / 'source-before.json').items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == value['sha256']
    assert load(folder / 'source-before.json') == load(folder / 'source-after.json')
    return summary


def http(folder):
    result = []
    for path in sorted((folder / 'http').glob('*-metadata.json')):
        meta = load(path)
        body = raw(folder / meta['response_file'])
        assert len(body) == meta['response_bytes']
        assert hashlib.sha256(body).hexdigest() == meta['response_sha256']
        request_meta = path.with_name(path.name.replace('-metadata.json', '-request-bytes.json'))
        request_proof = load(request_meta)
        request_bytes = raw(folder / request_proof['file'])
        assert len(request_bytes) == request_proof['bytes']
        assert hashlib.sha256(request_bytes).hexdigest() == request_proof['sha256']
        assert (json.loads(request_bytes) if request_bytes else None) == meta['request']
        meta['decoded_body'] = decode(body)
        result.append(meta)
    return result


def key(method, path, request, status, response):
    return method, path, canon(request), status, canon(response)


def database_metadata(folder, final):
    path = folder / 'fixture.db'
    before = raw(path)
    db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        counts = {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                  for name in ['runs', 'internal_app_runs', 'internal_instance_data',
                               'internal_releases', 'internal_instances', 'app_drafts',
                               'principals', 'grants', 'task_extractions', 'delivery_graph_requests']}
        statuses = db.execute('SELECT id,status FROM runs ORDER BY id').fetchall()
    finally:
        db.close()
    assert raw(path) == before
    assert all(counts[name] == len(final[name]) for name in counts)
    assert sorted(statuses) == sorted((r['id'], r['status']) for r in final['runs'])
    return dict(sha256=hashlib.sha256(before).hexdigest(), bytes_unchanged=True,
                counts=counts, run_statuses=statuses)


def audit_seed(folder):
    summary = observer(folder)
    proof = load(folder / 'seed-source-proof.json')
    before_after = load(folder / 'source-worker-claims.json')
    assert len(load(folder / 'model-wire.json')) == proof['generation_model_requests'] == 3
    assert len(load(folder / 'runtime-wire.json')) == proof['source_model_requests'] == 1
    assert proof['source_worker_calls'] == before_after['worker_calls'] == 1
    assert before_after['once_returned'] is True
    assert before_after['before']['header']['status'] == 'QUEUED'
    assert before_after['after']['header']['status'] == 'SUCCEEDED'
    assert len(before_after['after']['claims']) == 1
    assert before_after['before']['clock'] == before_after['after']['clock']
    assert before_after['before']['header']['created_at'] == before_after['after']['header']['created_at']
    assert proof['real_model_requests'] == proof['fabricated_rows'] == proof['extra_run_worker_calls'] == 0
    assert proof['extra_run_status'] == 'CANCELLED'
    copy = load(folder / 'seed-copy-provenance.json')
    assert copy['all_owned_connections_closed'] is True and copy['row_changes_for_copy'] == 0
    assert hashlib.sha256(raw(Path(copy['sealed']))).hexdigest() == copy['sealed_sha256']
    assert hashlib.sha256(raw(Path(copy['original']))).hexdigest() == copy['original_sha256'] == copy['sealed_sha256']
    responses = http(folder)
    assert len(responses) == summary['http_responses']
    return proof, load(folder / 'seed-rows.json'), dict(folder=str(folder), sealed_sha256=copy['sealed_sha256'],
        generation_mock_requests=3, source_worker_mock_requests=1, source_worker_claims=1,
        extra_cancelled_run_worker_calls=0, http_responses=len(responses), elapsed_seconds=summary['elapsed_seconds'])


def audit_scene(folder, seed, initial):
    summary = observer(folder)
    proof, page, info = load(folder / 'proof.json'), load(folder / 'page-result.json'), load(folder / 'info.json')
    assert proof['status'] == page['status'] == 'PASS' and page['error'] is None
    assert page['page_errors'] == [] and page['worker_calls'] == proof['page_worker_calls'] == 0
    assert not load(folder / 'model-wire.json') and not load(folder / 'runtime-wire.json')
    assert page['real_model'] == page['native_browser'] == page['real_human_semantic_acceptance'] == 'NOT_RUN'
    assert summary['latest']['node_exit_code'] == proof['node_exit_code'] == 0
    clone = load(folder / 'clone-provenance.json')
    assert clone['byte_identical'] is clone['row_identical'] is True
    assert clone['fixture_row_mutations'] == 0
    assert clone['source_sha256'] == clone['target_sha256_before_open'] == seed['sealed_sha256']
    requests = page['requests']
    base = '/api/projects/' + info['project'] + '/natural-spec-task-runs/' + info['source_run']
    posts = [r for r in requests if r['method'] == 'POST' and r['path'] == base + '/extractions']
    assert len(posts) == 1 and posts[0]['status'] == 201
    accepted = posts[0]['response']
    assert posts[0]['delivery_fault'] == 'ACTUAL_ACCEPTED_201_REPLY_LOST_CONTROLLED'
    assert all(r['method'] == 'GET' or r['path'] in {base + '/extraction-reviews', base + '/extractions'} for r in requests)
    ticket = page['ticket']
    assert set(ticket) == FIELDS and len(ticket) == 17
    assert all(isinstance(v, str) or type(v) is int for v in ticket.values())
    reviewed = accepted['reviewed']
    reviewed_body = {k: v for k, v in reviewed.items() if k != 'review_fingerprint'}
    source = reviewed['source_proof']
    expected = dict(namespace='pb-natural-extraction-recovery.v1', principal_id=info['principal'], project_id=info['project'],
        source_app_id=info['source_app'], source_instance_id=info['source_instance'], source_run_id=info['source_run'],
        source_app_run_id=info['source_app_run'], source_release_id=info['source_release'],
        source_release_fingerprint=info['source_release_fingerprint'], source_result_version=info['source_result_version'],
        request_key=posts[0]['body']['review']['request_key'], request_fingerprint=digest(posts[0]['body']),
        review_fingerprint=digest(reviewed_body), candidate_fingerprint=digest(reviewed['candidate']),
        app_id=reviewed['app_id'], runtime_id=reviewed['runtime_id'], source_proof_fingerprint=digest(source))
    assert ticket == expected
    assert ticket['request_fingerprint'] == accepted['request_fingerprint']
    assert ticket['review_fingerprint'] == reviewed['review_fingerprint']
    assert source['app_run_id'] == ticket['source_app_run_id'] and source['release_id'] == ticket['source_release_id']
    assert source['release_fingerprint'] == ticket['source_release_fingerprint'] and source['result_version'] == ticket['source_result_version']
    assert accepted['new_model_requests'] == accepted['project_writes'] == 0
    assert accepted['owner_acceptance'] == 'PENDING' and accepted['semantic_status'] == 'UNKNOWN'
    assert accepted['formal_publication_enabled'] is False

    responses = http(folder)
    assert len(responses) == summary['http_responses']
    available = Counter(key(m['method'], m['path'], m['request'], m['status'], m['decoded_body']) for m in responses)
    for r in requests:
        k = key(r['method'], r['path'], r.get('body'), r['status'], r.get('response', r.get('response_text')))
        assert available[k] > 0, k[:4]
        available[k] -= 1
    assets = page['static_resource_loads']
    for asset in assets:
        path = ROOT / 'src/sim2act/web' / (asset['path'].lstrip('/') or 'index.html')
        content = raw(path)
        assert asset['status'] == 200 and hashlib.sha256(content).hexdigest() == asset['sha256']
        k = key('GET', asset['path'], None, 200, content.decode('utf-8'))
        assert available[k] > 0
        available[k] -= 1
    assert {a['boot'] for a in assets} == set(range(1, page['boots'] + 1))
    assert all({a['path'] for a in assets if a['boot'] == n} == {a['path'] for a in assets if a['boot'] == 1} for n in range(1, page['boots'] + 1))

    revocations = load(folder / 'revocations.json')
    barriers = load(folder / 'authorization-barriers.json')
    assert len(revocations) == len(barriers) == (1 if page['scenario'] == 'boundary' else 0)
    extra = Counter()
    for k, count in available.items():
        if count:
            extra[k[:2]] += count
    if revocations:
        revoke = revocations[0]
        assert extra == Counter({('GET', '/api/projects/' + info['project'] + '/grants'): 1, ('POST', revoke['path']): 1})
        assert barriers[0]['status'] == 403 and not barriers[0]['blocked']
    else:
        assert not extra
    final = load(folder / 'final-rows.json')
    baseline = json.loads(json.dumps(initial))
    if revocations and any(r['id'] == revocations[0]['selected_grant']['id'] for r in baseline['grants']):
        selected = revocations[0]['selected_grant']
        for row in baseline['grants']:
            if row['id'] == selected['id']:
                assert row == selected
                row.update(revoked=True, revision=selected['revision'] + 1)
    allowed = {'app_drafts', 'principals', 'grants', 'task_extractions', 'delivery_graph_requests'}
    assert set(final) == set(baseline)
    fresh = {}
    for table in baseline:
        old_rows, new_rows = rowset(baseline[table]), rowset(final[table])
        assert not old_rows - new_rows, table
        if table not in allowed:
            assert old_rows == new_rows, table
        else:
            fresh[table] = [json.loads(row) for row, count in (new_rows - old_rows).items() for _ in range(count)]
    assert {t: len(v) for t, v in fresh.items()} == dict(app_drafts=1, principals=1, grants=2, task_extractions=1, delivery_graph_requests=4)
    app, marker = fresh['app_drafts'][0], fresh['task_extractions'][0]
    assert app['id'] == marker['app_id'] == ticket['app_id'] == proof['extracted_app']
    assert app['runtime_id'] == ticket['runtime_id'] == fresh['principals'][0]['id']
    assert app['fingerprint'] == digest(app['candidate']) == ticket['candidate_fingerprint']
    assert marker['task_id'] == info['source_run'] and marker['request_key'] == ticket['request_key']
    assert marker['request_fingerprint'] == ticket['request_fingerprint']
    assert {(r['principal_id'], r['resource_id'], r['tool_ref']) for r in fresh['grants']} == {
        (ticket['runtime_id'], info['target_resource'], 'resource.read'), (ticket['runtime_id'], info['project'], 'artifact.save_text')}
    if revocations and revocations[0]['kind'] == 'target':
        selected = revocations[0]['selected_grant']
        assert next(r for r in fresh['grants'] if r['id'] == selected['id']) == {**selected, 'revoked': True, 'revision': selected['revision'] + 1}
    db = database_metadata(folder, final)
    observations = page['digest_observations']
    if page['scenario'] == 'navigation':
        assert len(observations) == 1
        observed = observations[0]
        assert observed['classification'] == 'ACTUAL_WEBCRYPTO_SHA256_RESULT_DELIVERY_HOLD_DURING_GET_ONLY_RECOVERY'
        assert observed['actual_result_computed_before_hold'] is observed['delivered'] is True
        assert bytes.fromhex(observed['input_hex']) == canon(posts[0]['body']).encode()
        assert observed['input_utf8'].encode() == bytes.fromhex(observed['input_hex'])
        assert observed['actual_digest_hex'] == hashlib.sha256(bytes.fromhex(observed['input_hex'])).hexdigest() == ticket['request_fingerprint']
    if page['scenario'] == 'boundary' and page['revoke_kind'] == 'source':
        unknown = [r for r in requests if r['status'] == 400 and r.get('response', {}).get('error', {}).get('code') == 'OUTCOME_UNKNOWN']
        assert len(unknown) == 1 and unknown[0]['method'] == 'GET' and unknown[0]['response']['error']['effect_known'] is False
    if page['scenario'] == 'platform':
        assert any(e['event'] == 'BUSY' for e in page['lock_events'])
        actual_key_reads = [r for r in requests if r['method'] == 'GET' and r['path'] == base + '/extractions/by-key/' + ticket['request_key'] and r['status'] == 200]
        assert len(actual_key_reads) == 2
    return dict(folder=str(folder), scenario=page['scenario'], revoke_kind=page['revoke_kind'],
        checks=len(page['checks']), actions=len(page['actions']), boots=page['boots'],
        page_api_requests=len(requests), served_assets=len(assets), observed_http=len(responses),
        non_page_fixture_http=sum(extra.values()), accepted_extractions=1, page_worker_calls=0,
        ticket_fields=len(ticket), app_id=ticket['app_id'], request_key=ticket['request_key'],
        exact_accepted_request_and_review_hashes=True, full_seed_rows_preserved_except_explicit_revoke=True,
        appended_counts={t: len(v) for t, v in fresh.items()}, db_readonly=db,
        digest_delivery_observations=len(observations), authorization_barriers=len(barriers),
        barrier_evaluated_private_cells=[b['evaluated'] for b in barriers], elapsed_seconds=summary['elapsed_seconds'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite-dir', type=Path, required=True)
    parser.add_argument('--inputs-before', type=Path, required=True)
    parser.add_argument('--output-name', required=True)
    parser.add_argument('--full-suite-xml', type=Path)
    args = parser.parse_args()
    folders = [p for p in args.suite_dir.iterdir() if p.is_dir() and not p.is_symlink()]
    seeds = [p for p in folders if (p / 'seed-source-proof.json').exists()]
    assert len(seeds) == 1
    _, initial, seed_summary = audit_seed(seeds[0])
    completed = []
    for folder in folders:
        if (folder / 'proof.json').exists() and (folder / 'progress-summary.json').exists():
            if load(folder / 'proof.json')['status'] == 'PASS':
                completed.append(audit_scene(folder, seed_summary, initial))
    assert completed
    qualification = 'PARTIAL_COMPLETED_ARTIFACT_READBACK_NOT_FULL_BATCH_QUALIFICATION'
    junit = []
    if args.full_suite_xml:
        tree = ET.fromstring(raw(args.full_suite_xml))
        for case in tree.iter('testcase'):
            assert not any(case.find(tag) is not None for tag in ['error', 'failure', 'skipped'])
            junit.append(dict(case.attrib))
        assert len(junit) == len(completed) == 5
        assert {(c['scenario'], c['revoke_kind']) for c in completed} == {('flow', None), ('navigation', None), ('boundary', 'source'), ('boundary', 'target'), ('platform', None)}
        qualification = 'FIVE_COMPLETED_ACTUAL_HTTP_CASES_RAW_READBACK'
    before = load(args.inputs_before)
    changes = [p for p, v in before['inputs'].items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != v['sha256']]
    assert not changes
    result = dict(classification=qualification, recorded_utc=datetime.now(UTC).isoformat(),
        qualification_freeze=before['head'], input_count=len(before['inputs']), input_changes=changes,
        seed=seed_summary, completed_actual_http_cases=len(completed), scenes=completed, junit=junit,
        product_or_protocol_functions_executed_by_reviewer=0, real_model_requests=0,
        read_files_count=len(READ), read_files=READ)
    path = OUT / args.output_name
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'read_files'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
