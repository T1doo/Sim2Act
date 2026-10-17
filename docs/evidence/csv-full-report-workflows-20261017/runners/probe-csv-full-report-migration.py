"""Author-only additive migration probe on an owned synthetic copy, not user DB."""
import hashlib,json,sqlite3
from pathlib import Path
from sim2act.db import Store
out=Path('/workspace/csv-full-report-evidence-20261017/migration');out.mkdir(exist_ok=True)
source=Path('/tmp/csv-full-report-dev-reg/test_prospective_csv_report0/fixture.db')
assert source.is_file()
target=out/'synthetic-migration.sqlite'
assert not target.exists()
read=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True);copy=sqlite3.connect(target);read.backup(copy);read.close()
new=('csv_report_workflows','csv_report_workflow_uses')
for name in new:
    assert copy.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]==0
    copy.execute('DROP TABLE '+name)
copy.commit()
def snapshot(connection):
    tables=connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return {name:{'schema':schema,'rows':connection.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall()}for name,schema in tables}
before=snapshot(copy);copy.close()
store=Store('sqlite:///'+str(target),test_only=True);store.initialize();store.engine.dispose()
copy=sqlite3.connect(target);after=snapshot(copy);copy.close()
assert all(after[name]==value for name,value in before.items())
assert set(after)-set(before)==set(new)
assert all(after[name]['rows']==[]for name in new)
store=Store('sqlite:///'+str(target),test_only=True);store.initialize();store.engine.dispose()
copy=sqlite3.connect(target);again=snapshot(copy);copy.close();assert after==again
(out/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2));(out/'after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2));(out/'second-init.json').write_text(json.dumps(again,ensure_ascii=False,indent=2))
result=dict(status='PASS',scope='AUTHOR_ONLY_OWNED_SYNTHETIC_SQLITE_ADDITIVE_PROBE',source=str(source),target=str(target),old_tables=len(before),new_tables=list(new),old_schema_and_rows_unchanged=True,new_tables_empty=True,second_init_identical=True,real_user_database=False,worker_or_model=False,process_restart=False,postgres=False,database_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
