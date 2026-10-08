"""Read-only phase observers; preserve the original test's gates and timeouts."""
import contextvars
import functools
import hashlib
import json
import os
import sys
import threading
import time
import traceback
from concurrent.futures import Future
from pathlib import Path

import psutil
import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine

LABEL=contextvars.ContextVar('owned_diagnostic_request',default=None)
OUT=Path(os.environ['SIM2ACT_DIAGNOSTIC_OUT'])
ROWS=[]
ROW_LOCK=threading.Lock()
START=time.monotonic()
FAULT_FIRED=False

def record(kind,**data):
    row={'t':time.monotonic()-START,'thread':threading.get_ident(),
         'thread_name':threading.current_thread().name,'request':LABEL.get(),'kind':kind,**data}
    with ROW_LOCK: ROWS.append(row)

def query_shape(query):
    value=str(query)
    return {'sql_kind':value.split(None,1)[0] if value.strip() else '',
            'sql_hash':hashlib.sha256(value.encode()).hexdigest(),
            'observer':value.startswith(('SELECT pg_backend_pid()', 'SET LOCAL statement_timeout')),
            'table_hint':next((x for x in ['projects','grants','resources','delivery_graph','app_drafts'] if x in value),None)}

def call_wrapper(original,name):
    @functools.wraps(original)
    def wrapped(*args,**kwargs):
        if LABEL.get() is None:return original(*args,**kwargs)
        global FAULT_FIRED
        start=time.monotonic();record(name+'.start')
        if name=='Store.authorize' and LABEL.get()=='graph' and os.environ.get('SIM2ACT_DIAGNOSTIC_FAULT')=='python_authorize_delay' and not FAULT_FIRED:
            FAULT_FIRED=True;record('CONTROLLED_FAULT.start',mode='python_authorize_delay',seconds=10.5)
            threading.Event().wait(10.5)
            record('CONTROLLED_FAULT.end',mode='python_authorize_delay')
        try:return original(*args,**kwargs)
        except BaseException as exc:
            record(name+'.error',error=type(exc).__name__);raise
        finally:record(name+'.end',seconds=time.monotonic()-start)
    return wrapped

def event_name(obj,frame):
    for _ in range(2):
        if frame is None:break
        for name in ['reached','release','request_started']:
            values=frame.f_locals.get(name)
            if isinstance(values,dict):
                for key,val in values.items():
                    if val is obj:return name+'.'+key
        frame=frame.f_back
    return None

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    global START,FAULT_FIRED
    START=time.monotonic();ROWS.clear();FAULT_FIRED=False
    patch=pytest.MonkeyPatch()
    store=item.funcargs['env'][0]
    request=TestClient.request
    @functools.wraps(request)
    def request_wrapper(self,method,url,*args,**kwargs):
        label=self.headers.get('x-test-lock-request')
        if label not in {'resources','graph'}:return request(self,method,url,*args,**kwargs)
        token=LABEL.set(label);start=time.monotonic();record('http.start',method=method,path=str(url))
        try:
            result=request(self,method,url,*args,**kwargs);record('http.response',status=result.status_code);return result
        finally:record('http.end',seconds=time.monotonic()-start);LABEL.reset(token)
    patch.setattr(TestClient,'request',request_wrapper)
    for name in ['__enter__','__exit__']:
        original=getattr(TestClient,name)
        @functools.wraps(original)
        def context_call(self,*args,_original=original,_name=name,**kwargs):
            watched=threading.current_thread().name.startswith('ThreadPoolExecutor')
            start=time.monotonic()
            if watched:record('client.'+_name+'.start')
            try:
                if watched and _name=='__exit__' and self.headers.get('x-test-lock-request')=='resources' and os.environ.get('SIM2ACT_DIAGNOSTIC_FAULT')=='client_exit_delay':
                    record('CONTROLLED_FAULT.start',mode='client_exit_delay',seconds=10.5)
                    threading.Event().wait(10.5)
                    record('CONTROLLED_FAULT.end',mode='client_exit_delay')
                return _original(self,*args,**kwargs)
            finally:
                if watched:record('client.'+_name+'.end',seconds=time.monotonic()-start)
        patch.setattr(TestClient,name,context_call)
    execute=psycopg.Cursor.execute
    @functools.wraps(execute)
    def cursor_execute(self,query,*args,**kwargs):
        if LABEL.get() is None:return execute(self,query,*args,**kwargs)
        start=time.monotonic();shape=query_shape(query);record('cursor.start',backend=self.connection.info.backend_pid,**shape)
        try:return execute(self,query,*args,**kwargs)
        except BaseException as exc:
            record('cursor.error',error=type(exc).__name__,sqlstate=getattr(exc,'sqlstate',None));raise
        finally:record('cursor.end',seconds=time.monotonic()-start,backend=self.connection.info.backend_pid,**shape)
    patch.setattr(psycopg.Cursor,'execute',cursor_execute)
    for name in ['commit','rollback']:
        patch.setattr(psycopg.Connection,name,call_wrapper(getattr(psycopg.Connection,name),'dbapi.'+name))
    patch.setattr(Engine,'connect',call_wrapper(Engine.connect,'pool.acquire'))
    for name in ['wait','set']:
        original=getattr(threading.Event,name)
        @functools.wraps(original)
        def gate(self,*args,_original=original,_name=name,**kwargs):
            name=event_name(self,sys._getframe(1))
            if name is None:return _original(self,*args,**kwargs)
            start=time.monotonic();record('gate.'+_name+'.start',gate=name,args=args)
            try:
                if watched and _name=='__exit__' and self.headers.get('x-test-lock-request')=='resources' and os.environ.get('SIM2ACT_DIAGNOSTIC_FAULT')=='client_exit_delay':
                    record('CONTROLLED_FAULT.start',mode='client_exit_delay',seconds=10.5)
                    threading.Event().wait(10.5)
                    record('CONTROLLED_FAULT.end',mode='client_exit_delay')
                return _original(self,*args,**kwargs)
            finally:record('gate.'+_name+'.end',gate=name,seconds=time.monotonic()-start)
        patch.setattr(threading.Event,name,gate)
    result=Future.result
    @functools.wraps(result)
    def future_result(self,timeout=None):
        if timeout!=10:return result(self,timeout=timeout)
        start=time.monotonic();record('future.wait.start',timeout=timeout,state=self._state)
        try:return result(self,timeout=timeout)
        except TimeoutError:
            stacks={str(tid):traceback.format_stack(frame) for tid,frame in sys._current_frames().items()}
            record('future.timeout',state=self._state,stacks=stacks)
            # Read only this task's private database, after the unchanged failure.
            try:
                with psycopg.connect(dbname='sim2act_owned',user='sim2act_owned',
                        host='/tmp/sim2act-history-diagnostic-db/socket',connect_timeout=2) as c:
                    rows=c.execute("SELECT pid,state,wait_event_type,wait_event,xact_start,query_start,pg_blocking_pids(pid),query FROM pg_stat_activity WHERE datname=current_database()").fetchall()
                record('future.timeout.pg_activity',rows=rows)
            except BaseException as diagnostic_error:
                record('future.timeout.diagnostic_error',error=type(diagnostic_error).__name__)
            raise
        finally:record('future.wait.end',seconds=time.monotonic()-start,state=self._state)
    patch.setattr(Future,'result',future_result)
    from sim2act import delivery_graph_apps,report_manifest_apps
    from sim2act.db import Store
    for module,names in [(delivery_graph_apps,['history','current','build','load_family','expansion']),
                         (report_manifest_apps,['load']),(Store,['lock_project','authorize'])]:
        for name in names:
            patch.setattr(module,name,call_wrapper(getattr(module,name),module.__name__+'.'+name))
    def checkout(conn,rec,proxy):
        if LABEL.get():record('pool.checkout',backend=conn.info.backend_pid,pool=store.engine.pool.status())
    def checkin(conn,rec):
        if LABEL.get():record('pool.checkin',backend=conn.info.backend_pid if conn else None,pool=store.engine.pool.status())
    event.listen(store.engine,'checkout',checkout);event.listen(store.engine,'checkin',checkin)
    stop=threading.Event();process=psutil.Process()
    def sample():
        while not stop.wait(.5):
            record('resource.sample',cpu=process.cpu_times()._asdict(),rss=process.memory_info().rss,
                   threads=process.num_threads(),load=os.getloadavg())
    sampler=threading.Thread(target=sample,name='owned-diagnostic-sampler',daemon=True);sampler.start()
    record('case.start',node=item.nodeid,source_sha=os.environ['SIM2ACT_DIAGNOSTIC_SOURCE'])
    try:
        yield
    finally:
        record('case.end');stop.set();sampler.join(2)
        event.remove(store.engine,'checkout',checkout);event.remove(store.engine,'checkin',checkin)
        patch.undo()
        OUT.mkdir(parents=True,exist_ok=True)
        name=item.nodeid.split('::')[-1].replace('/','_')
        (OUT/(name+'.json')).write_text(json.dumps(ROWS,indent=2,default=str)+'\n')
