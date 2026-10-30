"""Read-only fresh-process check of the already-completed synthetic Cold DB."""
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

root = Path(sys.argv[1]).resolve()
meta=json.loads(Path(str(root.parent)+'-run.json').read_text())
assert meta['source_commit']=='f6c5e688584d1d9bfb649a7a3bc88074b1250196' and meta['returncode']==0
db = root / 'fixture.db'
before = hashlib.sha256(db.read_bytes()).hexdigest()
wal=Path(str(db)+'-wal')
wal_before=hashlib.sha256(wal.read_bytes()).hexdigest() if wal.exists() else None
proof = json.loads((root / 'pb-controller-proof.json').read_text())
expected = proof['result']
assert proof['classification'] == 'SYNTHETIC_MOCK_PRODUCTION_BRANCH_NOT_REAL_LIVE_EVIDENCE'
assert proof['real_models'] == 0
with closing(sqlite3.connect(db.as_uri()+'?mode=ro', uri=True, timeout=1)) as c:
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    run = dict(c.execute('SELECT * FROM runs WHERE id=?', (proof['cold'],)).fetchone())
    binding = dict(c.execute('SELECT * FROM internal_run_bindings WHERE run_id=?', (run['id'],)).fetchone())
    app = dict(c.execute('SELECT * FROM internal_app_runs WHERE id=?', (binding['app_run_id'],)).fetchone())
    typed = dict(c.execute('SELECT * FROM internal_instance_data WHERE instance_id=? AND version=?',
        (app['instance_id'], app['result_version'])).fetchone())
    assert run['id'] == expected['id'] and run['status'] == 'SUCCEEDED' and not run['cancel_intent']
    assert app['id'] == expected['app_run_id'] and app['instance_id'] == expected['instance_id']
    assert app['status'] == 'SUCCEEDED' and app['release_id'] == expected['release_id']
    assert app['result_version'] == expected['result_version'] == 1
    assert json.loads(app['output']) == expected['result']
    assert json.loads(typed['data'])['result'] == expected['result']
    assert typed['run_id'] == app['id'] and typed['release_id'] == app['release_id']
    assert typed['fingerprint'] == expected['known_effects'][0]['fingerprint']
    assert c.execute('SELECT count(*) FROM internal_instance_data WHERE instance_id=?', (app['instance_id'],)).fetchone()[0] == 1
    statuses = c.execute('SELECT status FROM attempts ORDER BY id').fetchall()
    assert len(statuses) == 7
    assert sorted(row[0] for row in statuses) == ['RECEIVED']*3 + ['VERIFIED']*4
    cold_statuses = c.execute('SELECT status FROM attempts WHERE run_id=?', (run['id'],)).fetchall()
    assert len(cold_statuses) == 2 and all(row[0] == 'VERIFIED' for row in cold_statuses)
    digest=hashlib.sha256()
    for (table,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
        rows=[tuple(row) for row in c.execute('SELECT * FROM "'+table.replace('"','""')+'" ORDER BY rowid')]
        digest.update(json.dumps([table,rows],ensure_ascii=True,separators=(',',':')).encode())
    logical=digest.hexdigest()
after = hashlib.sha256(db.read_bytes()).hexdigest()
assert before == after
wal_after=hashlib.sha256(wal.read_bytes()).hexdigest() if wal.exists() else None
empty_wal=hashlib.sha256(b'').hexdigest()
assert wal_after==wal_before or {wal_after,wal_before}<={None,empty_wal}
output = dict(status='PASS', classification='FRESH_PROCESS_READ_ONLY_SQLITE_WITH_WAL_NOT_WINDOWS_NOT_PG_NOT_LIVE',
    source_commit='f6c5e688584d1d9bfb649a7a3bc88074b1250196', run_id=run['id'],
    run_status=run['status'], result_version=1, instance_versions=1, cold_verified_attempts=2,
    all_attempts=7, generation_received_attempts=3, source_and_cold_verified_attempts=4,
    app_output_and_typed_result_equal_saved_http_result=True, database_unchanged=True,
    main_database_sha256=after,wal_sha256_before=wal_before,wal_sha256_after=wal_after,
    wal_physical_identity_unchanged=wal_before==wal_after,
    only_empty_wal_lifecycle=(wal_before!=wal_after),logical_database_sha256=logical,
    physical_identity_requires_main_and_wal=True,shm_is_transient_not_content_identity=True)
Path(sys.argv[2]).write_text(json.dumps(output, indent=2)+'\n')
print(json.dumps(output))
