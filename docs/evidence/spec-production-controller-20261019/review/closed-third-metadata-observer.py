"""Stdlib file/AST audit only. Does not import product code or open SQLite."""
import ast
import base64
import collections
import copy
import hashlib
import json
from pathlib import Path

repo = Path('/workspace/Sim2Act')
author = Path('/workspace/spec-production-controller-audit-20261019')
closed = author / 'qualified-third'
case = closed / 'actual/test_live_shaped_spec_generati0'

def read(path):
    return json.loads(path.read_text())

def sha(value):
    return hashlib.sha256(value).hexdigest()

def fp(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode())

def node_dump(tree):
    return ast.dump(tree, include_attributes=False)

old = ast.parse((closed / 'inputs/src/sim2act/pa_spec_apps.py').read_text())
new = ast.parse((repo / 'src/sim2act/pa_spec_apps.py').read_text())
functions = lambda tree: {n.name: node_dump(n) for n in tree.body
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
old_functions, new_functions = functions(old), functions(new)
changed = [name for name in old_functions if old_functions[name] != new_functions[name]]
assert changed == ['_bound', 'result_ref']

class Normalize(ast.NodeTransformer):
    removed_keyword = 0
    removed_condition = 0

    def visit_Call(self, node):
        self.generic_visit(node)
        target = node_dump(ast.parse('contract.mode', mode='eval').body)
        kept = []
        for keyword in node.keywords:
            if keyword.arg == 'run_mode' and node_dump(keyword.value) == target:
                self.removed_keyword += 1
            else:
                kept.append(keyword)
        node.keywords = kept
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        expected = ast.parse('natural.is_candidate(binding["draft"]["candidate"]) and '
                             'binding["run_mode"] == "mock"', mode='eval').body
        if node_dump(node) == node_dump(expected):
            self.removed_condition += 1
            return node.values[0]
        return node

normalize = Normalize()
normalized = normalize.visit(copy.deepcopy(new))
assert (normalize.removed_keyword, normalize.removed_condition) == (1, 1)
assert node_dump(old) == node_dump(normalized)
assert old_functions['verify_job'] == new_functions['verify_job']
assert old_functions['_advance_local'] == new_functions['_advance_local']
freeze = read(closed / 'inputs-before.json')
changed_package = [p for p, value in freeze.items() if p.startswith('src/')
    and sha((repo / p).read_bytes()) != value['sha256']]
assert changed_package == ['src/sim2act/pa_spec_apps.py']

state = read(case / 'closed-state.json')
proof = read(case / 'controller-proof.json')
assert len(state) == 55
rows = state['delivery_graph_requests']
for row in rows:
    assert fp(row['snapshot']) == row['fingerprint']
    assert fp(row['snapshot']['request']) == row['request_fingerprint']
for row in state['run_contracts']:
    assert fp(row['snapshot']) == row['fingerprint']
by_attempt = {r['id']: r for r in state['attempts']}
by_run = {r['id']: r for r in state['runs']}
by_contract = {r['run_id']: r for r in state['run_contracts']}
journals = [r for r in rows if r['kind'] in
    {'uninstalled-production-trial-journal.v1', 'uninstalled-production-trial-journal.v1_seal'}]
assert len(journals) == 2 and journals[0]['snapshot'] == journals[1]['snapshot']
ledger = journals[0]['snapshot']['response']['ledger']
slots = ledger['slots']
assert len(slots) == 7 and not ledger['halted']
assert all(s['accepted'] is True and s['attempted'] is True for s in slots)
assert collections.Counter(s['identity']['stage'] for s in slots) == {'generate': 3, 'source': 2, 'cold': 2}
assert set(by_attempt) == {s['identity']['attempt_id'] for s in slots}
exchanges = [json.loads(line) for line in (case / 'mock-exchanges.jsonl').read_text().splitlines()]
assert len(exchanges) == 7
attempt_facts = []
for slot, exchange in zip(slots, exchanges, strict=True):
    identity = slot['identity']
    attempt = by_attempt[identity['attempt_id']]
    job = by_run[identity['run_id']]
    frozen = by_contract[job['id']]['snapshot']
    assert exchange['status'] == 200
    assert attempt['run_id'] == job['id'] and attempt['mode'] == 'LIVE' and frozen['mode'] == 'live'
    marker = attempt['parameters']['pa_trial_binding']
    assert marker['version'] == 'spec-production-controller.v1'
    assert marker['account_id'] == identity['account_id'] and marker['worker_id'] == identity['worker_id']
    assert marker['run_version'] == identity['version'] and marker['fence'] == identity['fence']
    assert job['runtime_id'] == identity['runtime_id'] and job['id'] == proof[
        'generation' if identity['stage'] == 'generate' else identity['stage']]
    pair = [r for r in rows if r['request_key'] == identity['attempt_id'] and r['kind'] in
        {'uninstalled-production-trial-capture.v1', 'uninstalled-production-trial-capture.v1_seal'}]
    assert len(pair) == 2 and pair[0]['snapshot'] == pair[1]['snapshot']
    capture = pair[0]['snapshot']
    assert capture['request']['identity'] == identity
    captured = capture['response']
    assert captured['provenance'] == 'SPEC_PRODUCTION_CONTROLLER'
    request = base64.b64decode(exchange['request_b64'], validate=True)
    response = base64.b64decode(exchange['response_b64'], validate=True)
    assert sha(request) == identity['wire_sha256'] and len(request) == identity['wire_bytes']
    assert sha(response) == captured['raw_sha256'] == slot['settlement']['response_sha256']
    assert captured['raw_bytes'] == len(response) and base64.b64decode(captured['body_b64'], validate=True) == response
    assert captured['outcome'] == slot['settlement']
    assert attempt['usage']['status'] == 'known'
    assert all(attempt['usage']['tokens'][name] == slot['settlement'][name]
               for name in ('prompt_tokens', 'completion_tokens', 'total_tokens'))
    attempt_facts.append(dict(stage=identity['stage'], attempt_id=identity['attempt_id'],
        run_id=job['id'], status=job['status'], reserved_at=slot['reserved_at'],
        request_sha256=sha(request), response_sha256=sha(response)))
gaps = [b['reserved_at'] - a['reserved_at'] for a, b in zip(attempt_facts, attempt_facts[1:])]
assert all(gap >= 60 for gap in gaps)
body_rows = [r for r in rows if r['kind'] in {'natural_source_request_body.v1',
    'natural_source_request_body.v1_seal', 'natural_source_response_body.v1',
    'natural_source_response_body.v1_seal'}]
assert len(body_rows) == 16
for row in body_rows:
    body = row['snapshot']['response']
    assert body['provenance'] == 'SPEC_PRODUCTION_CONTROLLER'
    assert body['received_complete'] is True and body['omission'] == 'NONE'
    raw = base64.b64decode(body['body_b64'], validate=True)
    assert len(raw) == body['byte_count'] and sha(raw) == body['sha256']

bridge = read(author / 'metadata-bridge.json')
projections = []
for item in bridge['runs']:
    original = by_run[item['run_id']]['result']
    assert item['original'] == original and original['real_model_requests'] == 0
    assert item['final_projection'] == {k: v for k, v in original.items() if k != 'real_model_requests'}
    assert original['model_requests'] == item['final_projection']['model_requests'] == 2
    assert by_contract[item['run_id']]['snapshot']['mode'] == item['run_mode_from_actual_bound'] == 'live'
    assert by_run[item['run_id']]['status'] == 'SUCCEEDED'
    assert original['result_version'] == (1 if item['stage'] == 'source' else 2)
    projections.append(dict(stage=item['stage'], run_id=item['run_id'],
        original_fingerprint=fp(original), final_projection_fingerprint=fp(item['final_projection']),
        only_removed_key='real_model_requests'))
assert by_run[proof['generation']]['status'] == 'PARTIAL'

before = read(author / 'owner-artifact-read/state-before.json')
after = read(author / 'owner-artifact-read/state-after.json')
assert len(before) == len(after) == 55 and before == after
observations = read(author / 'owner-artifact-read/observations.json')
assert len(observations) == 4 and all(r['method'] == 'GET' and r['status'] == 200 for r in observations)
owner_access = []
for observation in observations:
    stage, body = observation['stage'], observation['body']
    job = by_run[proof[stage]]
    result = job['result']
    assert body['run_id'] == job['id'] and body['instance_id'] == result['instance_id']
    assert body['principal_id'] == job['principal_id'] and body['project_id'] == job['project_id']
    if observation['kind'] == 'artifact':
        assert body['app_run_id'] == result['app_run_id'] and body['release_id'] == result['release_id']
        assert body['result_version'] == result['result_version']
        resource = body['resource']
        assert sha(resource['content'].encode()) == resource['hash']
    else:
        assert body['owner_acceptance'] == 'PENDING' and body['sequence'] == 0
        if stage == 'source':
            assert body['content_access'] is False and body['invalidation_reason'] == 'VERSION_CONFLICT'
            assert 'current' not in body
        else:
            assert body['content_access'] is True and body['current']['result_version'] == 2
        owner_access.append(dict(stage=stage, content_access=body['content_access']))

print(json.dumps(dict(verdict='PASS_LIMITED_FILE_AST_BRIDGE', changed_functions=changed,
    exact_normalization_counts=[normalize.removed_keyword, normalize.removed_condition],
    other_package_files_unchanged=True, graph_row_hashes_recomputed=len(rows),
    seven_attempts=attempt_facts, reservation_gaps_seconds=gaps,
    archive_rows_with_raw_byte_hash_recomputed=len(body_rows),
    result_projections=projections, owner_artifact_GETs=4, owner_access=owner_access,
    all55_owner_artifact_tables_equal=True,
    author_product_recomputation='metadata-bridge bound/receipts and 55-table equality are author executed observations; reviewer independently checked exported facts and AST only',
    final_seven_requests='NOT_RERUN', old_WIP_LIVE_migration='NOT_SUPPORTED_OR_TESTED',
    metadata_final_in_progress='NOT_READ', reviewer_product_test_DB_network_execution=0), indent=2))
