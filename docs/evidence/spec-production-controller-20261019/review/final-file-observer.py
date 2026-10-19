"""Final bounded file audit; stdlib only, no product imports/DB/network."""
import ast
import collections
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

repo = Path('/workspace/Sim2Act')
author = Path('/workspace/spec-production-controller-audit-20261019')
review = Path(__file__).parent

def read(path):
    return json.loads(path.read_text())

def metadata(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

def cases(path):
    return [dict(id=c.get('classname', '') + '::' + c.get('name', ''),
        seconds=float(c.get('time', '0')),
        status='FAIL' if c.find('failure') is not None else
        'ERROR' if c.find('error') is not None else
        'SKIP' if c.find('skipped') is not None else 'PASS')
        for c in ET.parse(path).getroot().iter('testcase')]

batches = []
initial = cases(author / 'first-boundaries.xml')
batches.append(dict(name='first-boundaries', cases=initial,
    strict_pre_and_post_freeze=False, raw_stdout_saved=False))
copy_count = 0
for name in ('qualified-first', 'qualified-second', 'qualified-third', 'metadata-final'):
    root = author / name
    before, after = read(root / 'inputs-before.json'), read(root / 'inputs-after.json')
    assert before == after
    for rel, item in before.items():
        actual = metadata(root / 'inputs' / rel)
        assert (actual['bytes'], actual['sha256']) == (item['bytes'], item['sha256'])
        copy_count += 1
    execution = read(root / 'execution.json')
    values = cases(root / 'junit.xml')
    assert execution['exit'] == (1 if any(c['status'] in ('FAIL', 'ERROR') for c in values) else 0)
    batches.append(dict(name=name, cases=values, inputs=len(before),
        inputs_before_after_equal=True, copied_input_files_hash_verified=len(before),
        exit=execution['exit'], outer_seconds=execution['seconds'],
        strict_pre_and_post_freeze=True, raw_stdout_saved=True))

totals = collections.Counter(c['status'] for b in batches for c in b['cases'])
latest = {}
for batch in batches:
    latest.update({case['id']: case['status'] for case in batch['cases']})
assert dict(totals) == {'PASS': 13, 'FAIL': 2}
assert len(latest) == 7 and set(latest.values()) == {'PASS'}
final_map = read(author / 'metadata-final/inputs-before.json')
for rel, expected in final_map.items():
    current = metadata(repo / rel)
    assert (current['bytes'], current['sha256']) == (expected['bytes'], expected['sha256'])
assert len(final_map) == 151
controller_test = 'tests/test_spec_production_controller.py'
expected = read(author / 'qualified-third/inputs-before.json')[controller_test]
actual = metadata(repo / controller_test)
assert (actual['bytes'], actual['sha256']) == (expected['bytes'], expected['sha256'])

erratum = read(author / 'metadata-final-metadata-erratum.json')
assert erratum['real_HTTP_tripwire_in_this_batch'] is False
assert erratum['finite_explicit_MockTransport_requests'] == 4
def diagnostics(path):
    return sorted(re.sub(r':\d+(?::\d+)?:', ':', line)
        for line in path.read_text().splitlines() if ': error:' in line)
old_diagnostics = diagnostics(author / 'mypy-focused-baseline.stdout')
final_diagnostics = diagnostics(author / 'mypy-final.stdout')
assert len(old_diagnostics) == len(final_diagnostics) == 8 and old_diagnostics == final_diagnostics
assert read(author / 'mypy-final.execution.json')['exit'] == 1
assert all(item['exit'] == 0 for item in read(author / 'static-checks.json'))

revocation = read(author / 'qualified-third/actual/test_received_body_and_usage_s0/closed-state.json')
assert len(revocation) == 55 and len(revocation['attempts']) == 1
attempt = revocation['attempts'][0]
assert attempt['mode'] == 'LIVE' and attempt['usage']['status'] == 'known'
assert all(r['status'] != 'SUCCEEDED' and r['result'] is None for r in revocation['runs'])
ledger_rows = [r for r in revocation['delivery_graph_requests'] if r['kind'] in
    {'uninstalled-production-trial-journal.v1', 'uninstalled-production-trial-journal.v1_seal'}]
assert len(ledger_rows) == 2 and ledger_rows[0]['snapshot'] == ledger_rows[1]['snapshot']
ledger = ledger_rows[0]['snapshot']['response']['ledger']
assert ledger['halted'] is True and len(ledger['slots']) == 1
slot = ledger['slots'][0]
assert slot['attempted'] is True and slot['accepted'] is False and slot['settlement'] is not None
assert slot['settlement']['total_tokens'] == attempt['usage']['tokens']['total_tokens']
capture_rows = [r for r in revocation['delivery_graph_requests'] if r['kind'] in
    {'uninstalled-production-trial-capture.v1', 'uninstalled-production-trial-capture.v1_seal'}]
assert len(capture_rows) == 2 and capture_rows[0]['snapshot'] == capture_rows[1]['snapshot']
assert capture_rows[0]['snapshot']['response']['outcome'] == slot['settlement']

prod = ['api.py', 'app_jobs.py', 'db.py', 'goal_applications.py', 'natural_live_admission.py',
        'natural_source_archives.py', 'natural_spec_runtime.py', 'pa_spec_apps.py',
        'pa_trial_dispatch.py', 'production_evidence.py', 'production_trial_admission.py',
        'production_trial_sender.py', 'worker.py', 'spec_production.py']
source_hashes = {f'src/sim2act/{name}': metadata(repo / 'src/sim2act' / name) for name in prod}
for rel in [controller_test, 'tests/test_spec_production_result_metadata.py',
            'docs/F2/SpecProductionController20261019.md', 'docs/F2/Plan.md']:
    source_hashes[rel] = metadata(repo / rel)
supporting = ['first-boundaries.xml', 'qualified-first/junit.xml', 'qualified-first/pytest.stdout',
    'qualified-second/junit.xml', 'qualified-second/pytest.stdout',
    'qualified-third/junit.xml', 'qualified-third/pytest.stdout',
    'metadata-final/junit.xml', 'metadata-final/pytest.stdout',
    'metadata-final-metadata-erratum.json', 'metadata-bridge.json', 'closed-facts.json',
    'owner-artifact-read/observations.json', 'owner-artifact-read/state-before.json',
    'owner-artifact-read/state-after.json', 'qualification-history.json',
    'mypy-final.execution.json', 'mypy-final.stdout', 'mypy-focused-baseline.stdout',
    'static-checks.json']
supporting_hashes = {rel: metadata(author / rel) for rel in supporting}

print(json.dumps(dict(verdict='LIMITED_PASS_DEFAULT_CLOSED_SPEC_PRODUCTION_CONTROLLER',
    remaining_confirmed_P1_P2=[],
    scope='Static review plus closed synthetic file/AST audit only; independently executed product/tests/DB/network=0',
    batches=batches, unique_nodes_latest=latest, total_executions=sum(totals.values()),
    totals=dict(totals), copied_input_hashes_verified=copy_count,
    final_151_inputs_current_and_copies_equal=True, final_controller_test_equals_third=True,
    seven_request_bridge=read(review / 'closed-third-metadata-verification.json'),
    final_metadata_unit='PASS exact complete mock/live objects; LIVE only omits false zero; old single regression PASS',
    metadata_batch_guard_erratum=erratum,
    revocation_fact_independent_export_check=dict(tables=55, attempts=1,
        usage_total=slot['settlement']['total_tokens'], ledger_halted=True,
        slot_attempted=True, slot_accepted=False, capture_mirrors=2, no_successful_business_result=True),
    full55_default_and_public_rejection='Executed strict assertions in audited test source/JUnit; no separate before export for independent row delta reconstruction',
    mypy=dict(verdict='FAIL', baseline_targets=13, current_targets=14,
        same_errors_ignoring_lines=8, current_exit=1, no_new_diagnostics=True),
    ruff_and_source_test_diffcheck='Recorded author exit0; reviewer did not rerun',
    fixed_findings=['production provider forced synthetic mode/token',
        'tail source/lease expiry after long proof', 'public offline production binding bypass',
        'old no-CoreAttempt synthetic history regression', 'production body provenance mislabeled offline',
        'production natural result falsely reports real request zero'],
    defaults_and_boundary='Fixed resolve_account still SOURCE_MISSING; original software qualification not installed; exact P-A binding only; old synthetic branch not upgraded to LIVE',
    limitations=['Final production seven requests NOT_RERUN after two-line format change',
        'Old unpublished LIVE zero-field representation migration/compatibility NOT_SUPPORTED_OR_TESTED',
        'Synthetic tests substitute environment, fixed account source, and software qualification; not real service authority',
        'SourceReads proof reuse only original test_only SQLite; PG performance/concurrency unqualified',
        'Four owner/artifact ASGI GETs use third-round source; Source oldv1 owner metadata-only, Coldv2 current; no human PREPARE/DECIDE',
        'Metadata final lacked global real HTTP tripwire; exact finite MockTransport supplied by original helpers',
        'Real source/provider/model/semantics, Windows, native browser, PG concurrency, CI, deployment/publication NOT_RUN',
        'Initial two boundary cases lack raw stdout and strict pre/post freeze',
        'Author seal audited: all872 nonDB files SHA256,15DB stat-only,14 links; DB hashes not independently recomputed',
        'Packaging/commit/push not independently reviewed; no DB files opened or rehashed; no private holdout read'],
    observer_corrections=['Existing observer-correction.json corrects initial incomplete PG-upsert grep interpretation',
        'owner-artifact-static-review.json retains guessed nonexistent module rg exit2; corrected by actual paths',
        'Author metadata-final runner classification/tripwire wording corrected by separate erratum; original raw retained'],
    author_closure=read(review / 'author-seal-verification.json'),
    source_hashes=source_hashes, selected_author_raw_hashes=supporting_hashes), ensure_ascii=False, indent=2))
