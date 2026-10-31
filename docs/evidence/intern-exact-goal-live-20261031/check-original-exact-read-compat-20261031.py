import hashlib,json,shutil,sqlite3
from dataclasses import replace
from pathlib import Path
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.db import Store
from sim2act.synthetic_workspace import settings_for
original=Path('/workspace/scratch/exact-read-failed-original-9d74a3a17520-20261031')
copy=Path('/workspace/scratch/exact-read-direct-old-compat-20261031')
copy.mkdir(exist_ok=True)
db=original/'workspace/synthetic-workspace.db';before=hashlib.sha256(db.read_bytes()).hexdigest()
shutil.copy2(db,copy/db.name)
old=json.loads((original/'saved-run.json').read_text());request=json.loads((original/'report.json').read_text())
store=Store('sqlite:///'+str(copy/db.name)+'?timeout=30',test_only=True,workspace_serialized=True)
settings=replace(settings_for(copy),mode='live',live_enabled=True,token='SYNTHETIC_NO_SEND',max_requests=2,max_repairs=0,max_total_tokens=16384,max_output_tokens=1024,run_seconds=90)
def rows():
 con=sqlite3.connect(copy/db.name)
 result={n:con.execute('SELECT * FROM '+n+' ORDER BY 1').fetchall() for n in ['runs','attempts','reservations','events','run_contracts','quotas']};con.close()
 return result
prior=rows()
with TestClient(create_app(store,settings)) as client:
 client.headers['Authorization']='Bearer public-synthetic-blank-workspace'
 got=client.get('/api/runs/'+old['id']);assert got.status_code==200,got.text
 assert got.json()==old
 duplicate=client.post('/api/projects/'+request['project']+'/runs',json=request['request'])
 assert duplicate.status_code==202,duplicate.text
 assert duplicate.json()['run_id']==old['id']
 assert client.get('/api/runs/'+old['id']).json()==old
assert rows()==prior
store.engine.dispose()
assert hashlib.sha256(db.read_bytes()).hexdigest()==before
report={'classification':'OFFLINE_COPY_OF_ACTUAL_FAILED_9D_DB_NO_MODEL_SEND','original_source':'9d74a3a175204cd6afb74f068a755f4a1fb4f216','original_db_sha256':before,'same_failed_get':True,'same_request_same_run':True,'run_attempt_reservation_event_contract_quota_rows_unchanged':True,'original_db_unchanged':True,'real_requests':0}
(copy/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
