"""Passive per-history call/SQL counters; no parameters or fixture credentials."""
import contextvars, functools, hashlib, json, os, re, threading, time
from pathlib import Path
import pytest
from sqlalchemy import event

stack=contextvars.ContextVar('stability_profile_stack',default=())
active=contextvars.ContextVar('stability_profile_root',default=None)

@pytest.fixture(autouse=True)
def passive_history_profile(env, request):
    if request.node.nodeid not in (
        'tests/test_report_presentation_late_ui.py::test_actual_late_receipt_current_page_readback[same-checks]',
        'tests/test_resources_project_lock.py::test_pg_resources_graph_share_project_first_lock[resources-history]',
    ):
        yield
        return
    from sim2act import delivery_graph_apps as graph, report_presentations as presentation, report_manifest_apps as report, conditional_apps as named
    modules=[graph,presentation,report,named]
    roots={'delivery_graph_apps.history','report_presentations.history','report_manifest_apps.inspect'}
    names={'delivery_graph_apps':('history','current','load_family','build','expansion'),
        'report_presentations':('history','scope','load','build','readback'),
        'report_manifest_apps':('load','_fresh_origin','records','inspect'),
        'conditional_apps':('_load_validated_origin',)}
    records=[];lock=threading.Lock();originals=[]
    def wrap(fn,label):
        @functools.wraps(fn)
        def call(*args,**kwargs):
            root=active.get();root_token=None
            if root is None and label in roots:
                root=dict(operation=label,start=time.monotonic(),cpu_start=time.thread_time(),calls={},sql=[],thread=threading.get_ident())
                root_token=active.set(root)
                with lock:records.append(root)
            token=stack.set((*stack.get(),label));start=time.monotonic()
            try:return fn(*args,**kwargs)
            finally:
                if root is not None:
                    entry=root['calls'].setdefault(label,dict(count=0,seconds=0));entry['count']+=1;entry['seconds']+=time.monotonic()-start
                stack.reset(token)
                if root_token is not None:
                    root['wall_seconds']=time.monotonic()-root['start'];root['thread_cpu_seconds']=time.thread_time()-root['cpu_start'];active.reset(root_token)
        return call
    for module in modules:
        short=module.__name__.split('.')[-1]
        for name in names[short]:
            fn=getattr(module,name);originals.append((module,name,fn));setattr(module,name,wrap(fn,short+'.'+name))
    def before(conn,cursor,statement,parameters,context,executemany):
        root=active.get()
        if root is None:return
        clean=re.sub(r'test_[a-f0-9]+\.', '<fixture>.',statement)
        row=dict(start=time.monotonic(),kind=statement.split()[0],tables=sorted(set(re.findall(r'\b(?:FROM|JOIN|UPDATE|INTO)\s+([^\s,()]+)',clean))),
            locks='FOR UPDATE' in statement,stack=list(stack.get()),statement_sha256=hashlib.sha256(clean.encode()).hexdigest())
        root['sql'].append(row);context._stability_profile=(row,time.monotonic())
    def after(conn,cursor,statement,parameters,context,executemany):
        pair=getattr(context,'_stability_profile',None)
        if pair:pair[0]['seconds']=time.monotonic()-pair[1]
    event.listen(env[0].engine,'before_cursor_execute',before);event.listen(env[0].engine,'after_cursor_execute',after)
    try:yield
    finally:
        event.remove(env[0].engine,'before_cursor_execute',before);event.remove(env[0].engine,'after_cursor_execute',after)
        for module,name,fn in originals:setattr(module,name,fn)
        for r in records:
            r['sql_count']=len(r['sql']);r['sql_driver_seconds']=sum(v.get('seconds',0) for v in r['sql']);r['for_update_queries']=sum(v['locks'] for v in r['sql'])
        out=Path(os.environ['STABILITY_PROFILE_OUT']);out.mkdir(parents=True,exist_ok=True)
        filename=hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:12]+'.json'
        (out/filename).write_text(json.dumps(dict(node=request.node.nodeid,source_sha=os.environ['STABILITY_SOURCE_SHA'],records=records,
            passive_sqlalchemy_events=True,raw_test_observer_queries_not_counted=True,parameters_not_recorded=True),indent=2)+'\n')
