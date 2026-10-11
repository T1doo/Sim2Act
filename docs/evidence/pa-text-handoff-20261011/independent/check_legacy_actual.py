"""Read an actual previous-round SQLite record through current source; don't fabricate raw."""
import hashlib
import json
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, app_drafts, attempts, run_contracts

out=Path('/tmp/pa-text-handoff-review-20261011')
source=Path('/tmp/pa-independent-review-20261011/root-temp/test_goal_feedback_repair_rele0/fixture.db')
digest=lambda:hashlib.sha256(source.read_bytes()).hexdigest()
before=digest()
dest=out/'legacy-actual-copy.db'
src=sqlite3.connect(f'file:{source}?mode=ro',uri=True)
sink=sqlite3.connect(dest)
src.backup(sink);src.close();sink.close()
store=Store('sqlite:///'+str(dest),test_only=True)
with store.tx() as c:
    apps=c.execute(select(app_drafts)).mappings().all()
    attempt_rows=c.execute(select(attempts)).mappings().all()
    contracts=c.execute(select(run_contracts.c.snapshot)).scalars().all()
assert apps
assert all('response_archive_policy' not in value['application_generation'] for value in contracts if value.get('application_generation'))
assert all('generation_received_raw' not in row['parameters'] for row in attempt_rows)
client=TestClient(create_app(store,Settings('sqlite:///'+str(dest),out,mode='mock')))
client.headers.update({'Authorization':'Bearer synthetic-test-A'})
reads=[{'app_id':item['id'],'status':client.get('/api/apps/'+item['id']).status_code} for item in apps]
with store.tx() as c:
    after_rows=c.execute(select(attempts)).mappings().all()
assert all(read['status']==200 for read in reads),reads
assert [dict(row) for row in after_rows]==[dict(row) for row in attempt_rows]
assert digest()==before
result={'status':'PASS','actual_previous_round_source':str(source),'source_sha256_before':before,'source_sha256_after':digest(),'apps':reads,'no_raw_invented':True,'live_requests':0,'semantic':'NOT_RUN','native_browser':'NOT_RUN'}
(out/'legacy-actual.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
client.close();store.engine.dispose()
