"""Observer only: original frozen synthetic DB opened physically read-only."""
import cProfile
import faulthandler
import hashlib
import json
import pstats
import signal
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import event

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store

source=Path('/workspace/local-record-state-evidence-20261018/shared-d5eadc70/test_natural_spec_page_actual_0/fixture.db')
out=Path('/workspace/pa-page-root-cause-20261018'); out.mkdir(exist_ok=True)
before=hashlib.sha256(source.read_bytes()).hexdigest()
raw=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True)
iid,rid=raw.execute('SELECT a.instance_id,b.run_id FROM internal_app_runs a JOIN internal_run_bindings b ON b.app_run_id=a.id').fetchone()
raw.close()
store=Store('sqlite:///file:'+str(source)+'?mode=ro&uri=true',test_only=True)
sql=Counter(); sql_time=Counter()
@event.listens_for(store.engine,'before_cursor_execute')
def before_sql(conn,cursor,statement,parameters,context,many):
    context._pa_probe_start=time.perf_counter(); context._pa_probe_sql=' '.join(statement.split())
    sql[context._pa_probe_sql]+=1
@event.listens_for(store.engine,'after_cursor_execute')
def after_sql(conn,cursor,statement,parameters,context,many):
    sql_time[context._pa_probe_sql]+=time.perf_counter()-context._pa_probe_start

settings=Settings(str(store.engine.url),out,mode='mock',live_enabled=False,token='',goal_planner_provider='intern-s2')
app=create_app(store,settings)
def instrument(original):
    def observed(*args,**kwargs):
        prof=cProfile.Profile(); prof.enable()
        try:return original(*args,**kwargs)
        finally:
            prof.disable(); prof.dump_stats(out/'request-profile.pstats')
            with (out/'request-profile.txt').open('w') as handle:
                pstats.Stats(prof,stream=handle).sort_stats('cumtime').print_stats(65)
    return observed
for route in app.routes:
    if getattr(route,'path',None)=='/api/internal/instances/{iid}':
        route.dependant.call=instrument(route.dependant.call)

def limit(*_):
    raise TimeoutError('Bounded read-only diagnosis exceeded 150 seconds')
signal.signal(signal.SIGALRM,limit); signal.alarm(150)
stacks=(out/'request-stacks.txt').open('w')
faulthandler.dump_traceback_later(20,repeat=True,file=stacks)
started=time.perf_counter(); result={'mode':'READ_ONLY_URI_NO_WORKER_NO_MODEL_NO_PRODUCT_EDITS','source_sha256_before':before,'instance_id':iid,'run_id':rid}
try:
    with TestClient(app) as client:
        client.headers['Authorization']='Bearer synthetic-test-A'
        response=client.get('/api/internal/instances/'+iid)
        result.update(status=response.status_code,elapsed_seconds=time.perf_counter()-started,response_bytes=len(response.content))
        (out/'instance-response.json').write_text(response.text)
except BaseException as error:
    result.update(error=repr(error),elapsed_seconds=time.perf_counter()-started)
    raise
finally:
    signal.alarm(0); faulthandler.cancel_dump_traceback_later(); stacks.close()
    store.engine.dispose()
    result['source_sha256_after']=hashlib.sha256(source.read_bytes()).hexdigest()
    result['source_unchanged']=result['source_sha256_after']==before
    (out/'readonly-request-result.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'sql-summary.json').write_text(json.dumps([{'sql':s,'count':n,'database_seconds':sql_time[s]} for s,n in sql.most_common()],indent=2)+'\n')
    print(json.dumps(result),flush=True)
