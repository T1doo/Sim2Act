from pathlib import Path
import sqlite3,json,hashlib
from sim2act.db import Store
root=Path('/workspace/csv-owner-evidence-20261017/additive-sqlite-probe');root.mkdir(exist_ok=True)
source=next(Path('/tmp/csv-owner-red-20261017').glob('test_*/fixture.db'))
copy=root/'fixture.db';assert not copy.exists()
a=sqlite3.connect(source);b=sqlite3.connect(copy);a.backup(b);a.close();b.close()
def snapshot():
 with sqlite3.connect(copy) as c:
  names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  return {n:sorted([list(r) for r in c.execute('SELECT * FROM "'+n.replace('"','""')+'"')],key=repr) for n in names}
before=snapshot();assert 'csv_owner_records' not in before and 'csv_owner_seals' not in before
store=Store('sqlite:///'+str(copy),test_only=True)
store.initialize();after=snapshot();store.initialize();again=snapshot();store.engine.dispose()
assert all(after[n]==rows for n,rows in before.items()) and after==again
assert set(after)-set(before)=={'csv_owner_records','csv_owner_seals'} and not after['csv_owner_records'] and not after['csv_owner_seals']
proof=dict(source_fixture=str(source),source_fixture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_software='b8725ced with red test837b2178; this task own newly produced synthetic fixture',current_software='d6255ee782ddd84aeabb31ffac782376defa5871',existing_tables=len(before),new_tables=['csv_owner_records','csv_owner_seals'],existing_rows_unchanged=True,second_initialize_identical=True,scope='AUTHOR_ONLY_SYNTHETIC_SQLITE_ADDITIVE_SCHEMA; NOT_PG_NOT_REAL_OLD_USER_LIBRARY; not part of21 pytest nodes; no Run/Worker/model executed',first_attempt='default python could not import sqlalchemy before mkdir/DB copy; explicit venv retry')
(root/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2));(root/'after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2));(root/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2));print(json.dumps(proof,ensure_ascii=False,indent=2))
