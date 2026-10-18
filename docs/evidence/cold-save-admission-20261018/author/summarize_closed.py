"""Closed files only; no product imports, network, SQL or provider execution."""
import base64
import collections
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path('/workspace/cold-save-admission-20261018')
run = root / 'fresh-once'
load = lambda path: json.loads(path.read_bytes())
execution = load(run / 'execution.json')
assert 'exit_code' in execution and 'ended_utc' in execution
cases = []
for case in ET.fromstring((run / 'junit.xml').read_bytes()).iter('testcase'):
    verdict = ('ERROR' if case.find('error') is not None else
               'FAIL' if case.find('failure') is not None else
               'SKIP' if case.find('skipped') is not None else 'PASS')
    cases.append(dict(name=case.get('name'), seconds=case.get('time'), verdict=verdict))
guard = load(run / 'offline-guard.json')
assert guard['attempts'] == []
inputs_match = load(run / 'inputs-before.json') == load(run / 'inputs-after.json')
helpers_match = load(run / 'helpers-before.json') == load(run / 'helpers-after.json')
assert inputs_match and helpers_match
proof = run / 'actual-tmp/actual-prefix0/fresh-proof-rejections.json'
positive = run / 'actual-tmp/actual-prefix0/actual-pa-stages.json'
windows = load(proof) if proof.exists() else None
qualified = (execution['exit_code'] == 0 and len(cases) == 4
             and all(case['verdict'] == 'PASS' for case in cases))
body_checks, stage_ids, pairs = [], {}, []
if qualified:
    assert windows is not None and len(windows['cases']) == 9
    assert windows['clones_or_old_db_used'] is False
    assert windows['source'] == 'THIS_ROUND_ACTUAL_PREFIX_ONLY'
    value = load(positive)
    slots = value['accounting']['ledger']['slots']
    assert len(slots) == 7 and all(slot['accepted'] for slot in slots)
    assert collections.Counter(s['identity']['stage'] for s in slots) == dict(generate=3, source=2, cold=2)
    stage_ids = {s['identity']['stage']: s['identity']['run_id'] for s in slots}
    assert len(value['actual_attempts']) == 7 and len(value['bodies']) == 14
    for row in value['bodies']:
        body = row['snapshot']['response']
        raw = base64.b64decode(body['body_b64'], validate=True)
        assert len(raw) == body['byte_count'] and hashlib.sha256(raw).hexdigest() == body['sha256']
        if row['kind'] == 'pa_trial_response_body.v1':
            canonical = json.dumps(json.loads(raw), ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode('ascii')
            assert hashlib.sha256(canonical).hexdigest() == body['canonical_sha256'] != body['sha256']
            body_checks.append(dict(attempt_id=body['attempt_id'], raw_sha=body['sha256'], canonical_sha=body['canonical_sha256']))
    assert len(body_checks) == 7
    transactions = {tx['id']: tx for tx in guard['passive_transactions']}
    for stage in ('source', 'cold'):
        rid = stage_ids[stage]
        rows = [g for g in guard['passive_commit_guards'] if g['run_id'] == rid]
        pre = [g for g in rows if g['caller']['function'] == '_advance_local' and g['caller']['line'] == 1220]
        assert len(pre) == 1
        first = pre[0]
        post = [g for g in rows if g['caller']['function'] == '_advance_local'
                and g['caller']['line'] == 1261
                and g['transaction_observer_id'] == first['transaction_observer_id']
                and g['started_at'] >= first['ended_at']]
        assert len(post) == 1
        last = post[0]
        assert 'error' not in first and 'error' not in last
        assert last['write_epoch_at_start'] > first['write_epoch_at_end']
        assert last['read_segment_at_start'] and last['write_epoch_at_start'] == last['write_epoch_at_end']
        tx = transactions[first['transaction_observer_id']]
        pairs.append(dict(stage=stage, run_id=rid, pre_write_guard=first, post_write_guard=last,
            transaction=tx, lease_remaining_at_transaction_event_end=first['last_committed_lease_until']-tx['ended_at'],
            limit='Transaction end marker precedes driver commit completion; not a claim of full commit timing'))
adapter_entries = [a for a in guard['adapter_methods'] if a['method'] == 'request_serialized_captured']
databases = []
for path in sorted(root.rglob('*.db')):
    raw = path.read_bytes()
    databases.append(dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), copy_to_git=False))
summary = dict(status='FRESH_MOCK_QUALIFIED' if qualified else 'NOT_QUALIFIED', execution=execution,
    cases=cases, counts=dict(collections.Counter(c['verdict'] for c in cases)),
    source_sha=execution['source_commit'], input_maps_match=inputs_match, helper_maps_match=helpers_match,
    fresh_B_windows=len(windows['cases']) if windows else 0, stage_run_ids=stage_ids,
    response_body_checks=body_checks, SAVE_guard_pairs=pairs,
    actual_mock_adapter_entries=len(adapter_entries), real_model_calls=0,
    old_requests_replayed=0, old_19_12_8_9_nodes_rerun=0,
    prior_checkpoint_history='14 nodes =5PASS/8ERROR/1fixtureFAIL;33 mock adapter calls, preserved unchanged',
    targeted_component_first_command='exit1 after9 windows, correct changed-software rejection; no old trial installed',
    targeted_component_followup='exit0;2 expired lease refusals; prior9 windows not rerun',
    databases_external_only=databases,
    limits=['One fresh mock chain only, not a load/performance guarantee', 'Author pure-file summary, not independent DB reconstruction',
            'No real API, semantic/human acceptance, Windows/native, PG, CI or new PB/AT10 qualification'])
(root / 'closed-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('status','source_sha','counts','fresh_B_windows','actual_mock_adapter_entries','real_model_calls')}))
