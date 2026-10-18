import hashlib
import json
import pathlib
import sqlite3
import xml.etree.ElementTree as ET

BASE = pathlib.Path('/tmp/csv-material-independent-positive-805-20261018')
E = BASE / 'evidence'
fixture = E / 'pytest-temp/test_authorized_B_same_instanc0'
delivery = json.loads((fixture / 'actual-material-delivery.json').read_text())
before = json.loads((E / 'frozen-inputs-before.json').read_text())
after = json.loads((E / 'frozen-inputs-after.json').read_text())
command = json.loads((E / 'command.json').read_text())
assert command['exit_code'] == 0 and after['changes_during_test'] == []
cases = ET.parse(E / 'junit.xml').getroot().findall('.//testcase')
assert len(cases) == 1 and not cases[0].findall('./failure') and not cases[0].findall('./error')
db = fixture / 'fixture.db'
raw_before = db.read_bytes()
c = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
c.row_factory = sqlite3.Row
try:
    counts = {name:c.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0]
        for name in ('runs','internal_instances','app_drafts','grants','principals','attempts','reservations')}
    actual_runs = [dict(row) for row in c.execute('SELECT id,runtime_id,resource_refs,status,version,result,context FROM runs ORDER BY created_at')]
    owner_records = [dict(row) for row in c.execute('SELECT * FROM csv_owner_records ORDER BY sequence')]
    owner_seals = [dict(row) for row in c.execute('SELECT * FROM csv_owner_seals ORDER BY record_id')]
    material_ids = (delivery['preview']['context']['source']['resource_id'],delivery['request']['resource_id'])
    raw_materials = [dict(row) for row in c.execute('SELECT * FROM resources WHERE id IN (?,?) ORDER BY id',material_ids)]
finally:
    c.close()
assert db.read_bytes() == raw_before, 'Read-only evidence extraction changed DB bytes'
assert counts['attempts'] == counts['reservations'] == 0 and counts['runs'] == 4
assert all(row['status'] == 'SUCCEEDED' for row in actual_runs)
assert len(owner_records) == len(owner_seals) == 2
assert any(row['kind'] == 'DECIDE' and row['status'] == 'ACCEPTED' for row in owner_records)
for row in raw_materials:
    assert row['hash'] == hashlib.sha256(row['content'].encode()).hexdigest()

proof = dict(product_commit=command['product_commit'], actual_model_attempts=counts['attempts'],
    actual_model_reservations=counts['reservations'], counts=counts,
    actual_runs=actual_runs, original_A_owner_records=owner_records, original_A_owner_seals=owner_seals,
    actual_A_B_materials=raw_materials, database_sha256=hashlib.sha256(raw_before).hexdigest(),
    read_only_extraction_database_bytes_unchanged=True)
(E / 'actual-independent-database-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
http = json.loads((fixture / 'actual-http.json').read_text())
summary = dict(product_commit=command['product_commit'], pytest_nodes=1, pytest_passed=1,
    command_exit=command['exit_code'], original_git_blobs_verified=before['file_count'],
    frozen_product_files=sum(row['path'].startswith('src/') for row in before['files']),
    product_source_changes=0, only_observer_change='cached false/true; all remaining response fields exactly equal',
    actual_business_instance_id=delivery['new_run']['instance_id'],
    app_id=delivery['preview']['context']['app_id'], runtime_id=delivery['preview']['context']['runtime_id'],
    material_B_id=delivery['request']['resource_id'], material_B_sha256=delivery['B_sha256'],
    material_B_exact_bytes=delivery['B_bytes'], expected_independent_sum='18', expected_independent_count=2,
    check=delivery['check'], actual_check_result=delivery['check_result']['result'],
    adopted_release=delivery['version']['id'], adopted_revision=delivery['adopted']['revision'],
    data_version_at_adoption=delivery['adopted']['data_version'],
    new_business_run=delivery['new_run']['id'], actual_business_result=delivery['new_run']['result'],
    actual_result_version=delivery['new_run']['result_version'],
    owner={key:delivery['pending'][key] for key in ('content_access','owner_acceptance','sequence','history')},
    original_A_raw_rows_preserved_by_test=True,
    authority_tables_unchanged_by_test=delivery['unchanged_authority_tables'],
    no_real_models=True, actual_model_attempts=counts['attempts'], actual_reservations=counts['reservations'],
    main_client_http_trace_requests=len(http),
    cold_HTTP='Three successful GETs asserted in the one test; cold-client responses are not separately captured by the main-client HTTP fixture.',
    not_run=['Windows','PostgreSQL','remote CI','native browser','real models','real semantic or human acceptance'],
    original_805_failure='Preserved by parent; this is a separate corrected-observer run, not a replacement of the original failed result.')
(E / 'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')

readme = '''# Independent one-node material acceptance

Product freeze: `805afe60cdd94d6d4679e0da9c1f7fde752f67d2`.

Actual result: **1 passed**, four real synthetic NoModel Worker Runs. This is a separate corrected-observer run. The parent's original failed 805 result remains a failed original.

- [JUnit original](junit.xml), [stdout original](pytest.stdout.log), [exact command and timing](command.json).
- [39 main-client HTTP request/response originals](pytest-temp/test_authorized_B_same_instanc0/actual-http.json).
- [Complete delivery identity chain, CHECK, Release, CAS, business result and PENDING response](pytest-temp/test_authorized_B_same_instanc0/actual-material-delivery.json).
- [Actual retained SQLite fixture](pytest-temp/test_authorized_B_same_instanc0/fixture.db), [read-only raw material/Run/old-owner extraction](actual-independent-database-proof.json).
- [653 original Git blob/SHA256 input freezes](frozen-inputs-before.json), [post-run zero source/file drift proof](frozen-inputs-after.json), [original input archive](original-frozen-inputs.tar).
- [Original observer patch](cached-assertion-original.patch), [path-adapted applied patch](cached-assertion-applied.patch), [single hunk/patch SHA proof](observer-patch-proof.json).
- [Inspectable outcome summary](summary.json), [complete artifact checksums](artifact-checksums.json).

The only snapshot change was the explicit `cached:false` / `cached:true` assertion; all other response fields still require exact equality. All 129 `src/` files matched the original Git blobs before and after, and all 653 selected tracked inputs remained unchanged during the run.

The unchanged test fixes quantity, freezes saved Goal2 provenance at A, runs the new authorized B with independently fixed sum18/count2, adopts onto the same business instance, requires a new PENDING owner context, rejects old A acceptance, verifies old immutable rows, and asserts three cold-client GETs and a read-only database snapshot. The main-client trace captures 39 requests; those three cold-client responses are asserted by the test but are not separately captured by its main-client trace fixture.

No real model, Windows, PostgreSQL, remote CI, native browser, real semantic scenario or genuine human acceptance was executed. Only the requested single pytest node was run. B App-runtime grants were test-only preconditions established before the operation baseline; the complete Grant/principal/App tables were compared unchanged by the test.
'''
(E / 'README.md').write_text(readme)
files=[]
for path in sorted(E.rglob('*')):
    if path.is_file() and path.name != 'artifact-checksums.json':
        data=path.read_bytes()
        files.append(dict(path=str(path.relative_to(E)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(E / 'artifact-checksums.json').write_text(json.dumps(dict(file_count=len(files),files=files),indent=2)+'\n')
print(json.dumps(dict(status='PASS',files=len(files),frozen_files=before['file_count'],
    source_files=summary['frozen_product_files'],new_run=summary['new_business_run'],
    fixture_sha256=proof['database_sha256']),indent=2))
