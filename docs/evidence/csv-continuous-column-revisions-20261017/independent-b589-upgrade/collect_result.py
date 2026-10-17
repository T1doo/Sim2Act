import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import xml.etree.ElementTree as ET

base=Path('/tmp/csv-upgrade-independent-b5898093-20261017')
snapshot=base/'snapshot'
xml=ET.parse(base/'junit.xml').getroot()
suites=[xml] if xml.tag=='testsuite' else list(xml.findall('testsuite'))
total={name:sum(int(suite.get(name,'0')) for suite in suites) for name in ('tests','failures','errors','skipped')}
assert total==dict(tests=2,failures=0,errors=0,skipped=0),total
page_dir=base/'artifacts/test_visible_current_effective0'
page=json.loads((page_dir/'page-result.json').read_text())
delivery=json.loads((page_dir/'actual-browser-delivery.json').read_text())
receipt=json.loads((base/'artifacts/test_exact_derive_receipt_is_f0/actual-derive-receipt.json').read_text())
assert page['status']=='PASS'
asset_checks=[]
for asset in page['assets']:
    relative='src/sim2act/web/'+('index.html' if asset['path']=='/' else asset['path'].lstrip('/'))
    actual=hashlib.sha256((snapshot/relative).read_bytes()).hexdigest()
    assert actual==asset['sha256'],(asset,relative,actual)
    asset_checks.append(dict(path=asset['path'],git_relative=relative,sha256=actual,match=True))
new=delivery['new']
assert new['result']['sum']=='30' and new['result_version']==3
assert delivery['instance']['revision']==3 and delivery['instance']['data_version']==3
assert delivery['contract']['goal']['goal']==delivery['old_value']['context']['goal']['snapshot']['content']['goal']
stale=[row for row in page['requests'] if row['method']=='GET' and row['path'].endswith('/delivery-graph') and row['status']==409]
derived=[row for row in page['requests'] if row['method']=='POST' and row['path'].endswith('/delivery-graph/derive')]
assert len(derived)==1 and derived[0]['status']==201 and derived[0]['delivery']=='ACTUAL_DERIVE_201_LOST'
assert stale
key=derived[0]['body']['request_key']
recovery=[row for row in page['requests'] if row['method']=='GET' and row['path'].endswith('/derive-requests/'+key) and row['status']==200]
assert recovery
run_states=[]
for dbfile in sorted((base/'artifacts').rglob('fixture.db')):
    connection=sqlite3.connect(dbfile.as_uri()+'?mode=ro',uri=True)
    connection.execute('PRAGMA query_only=ON')
    connection.row_factory=sqlite3.Row
    runs=[dict(row) for row in connection.execute('SELECT id,status,error FROM runs')]
    model_attempts=connection.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
    event_kinds=[dict(row) for row in connection.execute('SELECT kind,COUNT(*) AS count FROM events GROUP BY kind ORDER BY kind')]
    connection.close()
    assert model_attempts==0
    assert all(row['status']=='SUCCEEDED' for row in runs)
    run_states.append(dict(db_path=str(dbfile.relative_to(base)),model_attempts=model_attempts,runs=runs,event_kinds=event_kinds))
report=dict(sha='b589809375c89b4d93617d91c780a1e0f7f704e2',scope='Only two requested SQLite actual HTTP/JSDOM + deterministic CSV/NoModel cases',synthetic_prior_registry=True,actual_old_ce3_binary_upgrade=False,pytest=total,pytest_seconds=sum(float(suite.get('time','0')) for suite in suites),browser_check_count=len(page['checks']),browser_checks=page['checks'],loaded_assets=asset_checks,actual_stale_graph_conflicts=[dict(path=row['path'],status=row['status'],body=row['response']) for row in stale],actual_derive=derived[0],actual_original_key_recoveries=recovery,new_run=dict(id=new['id'],instance_id=new['instance_id'],release_id=new['release_id'],result_version=new['result_version'],result=new['result']),instance=dict(id=delivery['instance']['id'],revision=delivery['instance']['revision'],data_version=delivery['instance']['data_version']),goal_version=delivery['old_value']['context']['goal']['version'],derive_receipt_gets={key:dict(status=receipt[key]['status'],private_body_reads=len(receipt[key]['private_journal_body_selects']),database_unchanged=receipt[key]['database_before_fingerprint']==receipt[key]['database_after_fingerprint']) for key in ('exact_accepted_key','missing_original_key','revoked_current_authority')},db_states=run_states,not_executed=['Windows','PostgreSQL','remote CI','real model','other regression matrices'])
(base/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
manifest=[]
for file in sorted(base.rglob('*')):
    if file.is_file() and not file.is_symlink() and not file.is_relative_to(snapshot) and file.name!='evidence-sha256.json':
        content=file.read_bytes()
        manifest.append(dict(path=str(file.relative_to(base)),sha256=hashlib.sha256(content).hexdigest(),size=len(content)))
(base/'evidence-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ('sha','pytest','pytest_seconds','browser_check_count','derive_receipt_gets','new_run')},ensure_ascii=False))
