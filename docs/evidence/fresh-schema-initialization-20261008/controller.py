import hashlib,json,os,secrets,subprocess,time
from pathlib import Path
from sqlalchemy import text
from sim2act.db import Store,new_id
root=Path('/tmp/sim2act-fresh-schema');repo=Path.cwd();name='sim2act-fresh-schema-'+secrets.token_hex(5);password=secrets.token_hex(24)
def run(args,**kw):return subprocess.run(args,check=True,capture_output=True,text=True,**kw)
started=False
try:
 run(['docker','run','-d','--name',name,'--label','sim2act.owner=fresh-schema-20261008','-e','POSTGRES_PASSWORD='+password,'-p','127.0.0.1::5432','postgres:17.11']);started=True
 port=run(['docker','port',name,'5432/tcp']).stdout.strip().rsplit(':',1)[1]
 for attempt in range(60):
  if subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
  time.sleep(.2)
 else:raise RuntimeError('owned PG readiness timed out')
 url=f'postgresql+psycopg://postgres:{password}@127.0.0.1:{port}/postgres'
 env=dict(os.environ,SIM2ACT_TEST_DATABASE_URL=url,PYTHONPATH='tests:src',NODE_PATH='/workspace/browser-tools/node_modules')
 nodes=['tests/test_fresh_schema_initialization.py','tests/test_app_previews.py','tests/test_local_task_retirement.py::test_application_role_completed_task_retirement_path','tests/test_bounded_agent_apps.py::test_runtime_role_existing_tables_no_ddl','tests/test_preview_extraction.py::test_pg_business_role_uses_explicit_migration_and_entire_extraction_path','tests/test_windows_phase_metrics.py']
 with (root/'pg.log').open('w') as log:
  p=subprocess.run(['/workspace/sim2act-pb-venv/bin/python','-m','pytest','-q','-p','windows_phase_metrics','--windows-metrics-output='+str(root/'pg-metrics.json'),*nodes,'--basetemp='+str(root/'fixtures'),'--junitxml='+str(root/'pg.xml')],env=env,stdout=log,stderr=subprocess.STDOUT)
 (root/'pg-exit.json').write_text(json.dumps({'exit_code':p.returncode})+'\n')
 if p.returncode:raise RuntimeError('PG regression failed; original log retained')
 # Benchmark old/new methods within one fresh owned PG; fixed six alternating groups.
 from sqlalchemy import event
 from sqlalchemy.dialects.postgresql.base import PGDialect
 original=PGDialect.has_table;counter={'has_table':0,'ddl':0};rows=[]
 def measured(*a,**kw):counter['has_table']+=1;return original(*a,**kw)
 PGDialect.has_table=measured
 try:
  for mode in ('normal','fresh','fresh','normal','normal','fresh'):
   counter.update(has_table=0,ddl=0);elapsed=0
   for _ in range(4):
    store=Store(url,test_only=True);schema=new_id('test')
    with store.engine.begin() as c:c.execute(text(f'CREATE SCHEMA "{schema}"'))
    store.engine=store.engine.execution_options(schema_translate_map={None:schema})
    def observe(_c,_cursor,_s,_p,context,_m):
     if context.isddl:counter['ddl']+=1
    event.listen(store.engine,'before_cursor_execute',observe)
    try:
     before=time.perf_counter();store.initialize(fresh_test_schema=schema if mode=='fresh' else None);elapsed+=time.perf_counter()-before
    finally:
     event.remove(store.engine,'before_cursor_execute',observe)
     with store.engine.begin() as c:c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
     store.engine.dispose()
   rows.append({'mode':mode,'schemas':4,'initialize_seconds':elapsed,**counter})
 finally:PGDialect.has_table=original
 (root/'benchmark.json').write_text(json.dumps({'platform':'Linux local PG17.11','samples':rows,'windows_savings':'UNKNOWN'},indent=2)+'\n')
 audit=Store(url,test_only=True)
 with audit.engine.connect() as c:
  schemas=c.execute(text("SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'test_%'")).scalar_one()
  roles=c.execute(text("SELECT count(*) FROM pg_roles WHERE rolname LIKE 'test_%'")).scalar_one()
  public=c.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")).scalar_one()
 audit.engine.dispose();assert schemas==roles==public==0
 (root/'cleanup.json').write_text(json.dumps({'owned_schemas':schemas,'owned_roles':roles,'public_tables':public,'provider_calls':0})+'\n')
finally:
 if started:
  run(['docker','rm','-f',name])
  assert subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
  p=root/'cleanup.json';data=json.loads(p.read_text()) if p.exists() else {};data['owned_container_removed']=True;p.write_text(json.dumps(data,indent=2)+'\n')
print('Controller complete; no private URL saved')
