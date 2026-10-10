import json,sys,hashlib
from pathlib import Path
from fastapi.testclient import TestClient
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from test_csv_dag_instances import release
b=json.load(sys.stdin)
s=Store(b['database_url'],test_only=True)
if b['schema']: s.engine=s.engine.execution_options(schema_translate_map={None:b['schema']})
c=TestClient(create_app(s,Settings(b['database_url'],Path(b['root']),mode='mock')));c.headers['Authorization']='Bearer synthetic-test-A'
e=(s,Settings(b['database_url'],Path(b['root']),mode='mock'),c,b['owner'],b['other'],b['project'],b['resource'])
aid,rid,p,j,rel=release(e,with_report=True)
Path(b['out']).write_text(json.dumps(dict(release=rel,run_id=j['id'],app_id=aid,resource_id=rid,source_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src').rglob('*.py')}),indent=2)+'\n')
c.close();s.engine.dispose()
