import collections
import hashlib
import inspect
import json
import os
import time
from pathlib import Path

import pytest
from sqlalchemy import event, select
from conftest import env as base_env
from test_conditional_apps import saved, authority
from test_conditional_run_bindings import env as bounded_env
from sim2act import conditional_apps as named, conditional_runs, protocol_jobs, report_manifest_apps as manifest
from sim2act.contracts import Limits
from sim2act.db import meta, fingerprint


def test_bounded_profile(tmp_path,monkeypatch):
    monkeypatch.setenv('SIM2ACT_TEST_DATABASE_URL','sqlite:///'+str(tmp_path/'only-profile.sqlite'))
    setup=base_env.__wrapped__(tmp_path)
    base=next(setup)
    context=bounded_env.__wrapped__(base)
    store, settings, client, user, _, pid, *_=context
    caps=Limits(**{k:getattr(settings,k) for k in Limits.model_fields})
    draft,body,wires=saved(context,tmp_path)
    assert len(wires)==3
    counts=collections.Counter(); sql=collections.Counter(); calls=collections.Counter(); phases={}
    with store.tx() as c:
        jobs=c.execute(select(protocol_jobs._table().c.run_id,protocol_jobs._table().c.kind)).all()
        phases=dict(jobs)
    active=False
    def wrap(original,label):
        def call(*args,**kwargs):
            if active:
                rid=args[3] if label in {'verified_pending','_plan'} else None
                caller=inspect.currentframe().f_back
                calls[label+':'+(phases.get(rid,'other') if rid else 'all')]+=1
                counts[label+':'+caller.f_globals.get('__name__','')+'.'+caller.f_code.co_name]+=1
            return original(*args,**kwargs)
        return call
    # Every module-level alias is patched to one original wrapper; local imports see it too.
    for label in ['verified_pending','_plan']:
        original=getattr(protocol_jobs,label)
        wrapped=wrap(original,label)
        for module in [protocol_jobs,named,manifest,conditional_runs]:
            if getattr(module,label,None) is original:
                monkeypatch.setattr(module,label,wrapped)
    original=conditional_runs.source_completion
    wrapped=wrap(original,'source_completion')
    for module in [conditional_runs,protocol_jobs,named,manifest]:
        if getattr(module,'source_completion',None) is original:
            monkeypatch.setattr(module,'source_completion',wrapped)
    def statement(_conn,_cursor,text,_params,_execution,_many):
        if active:
            sql[text.split(None,1)[0].upper()]+=1
            for table in meta.tables:
                if ' '+table+'.' in text or ' '+table+'\n' in text or ' '+table+' ' in text:
                    sql['table:'+table]+=1
    event.listen(store.engine,'before_cursor_execute',statement)
    def domain():
        with store.tx() as c:
            return fingerprint({table.name:sorted([dict(r) for r in c.execute(select(table)).mappings()],key=fingerprint) for table in meta.sorted_tables})
    results=[]
    def measure(label,fn,allow_writes=False):
        nonlocal active
        before=domain(); auth=authority(context)
        counts.clear();calls.clear();sql.clear(); active=True
        began=time.perf_counter()
        value=fn()
        elapsed=time.perf_counter()-began
        active=False
        after=domain()
        assert authority(context)==auth
        assert allow_writes or before==after
        results.append(dict(label=label,wall_seconds=elapsed,sql=dict(sql),calls=dict(calls),caller_counts=dict(counts),domain_unchanged=before==after,authority_unchanged=True))
        return value
    try:
        def load_named():
            with store.tx() as c:return named.load(store,c,user,pid,draft['id'])
        measure('named.load same transaction',load_named)
        promotion=f'/api/projects/{pid}/conditional-apps/{draft["id"]}/manifest-preview'
        request=dict(expected_app_fingerprint=draft['fingerprint'],request_key='profile-promote')
        def promote():
            r=client.post(promotion,json=request);assert r.status_code==201,r.text;return r.json()
        app=measure('HTTP first manifest promotion',promote,True)
        measure('HTTP same-key cached manifest promotion',promote)
        def direct_manifest():
            with store.tx() as c:return manifest.load(store,c,user,app['id'],caps,pid)
        measure('manifest.load same transaction',direct_manifest)
        def inspect_app():
            r=client.get(f'/api/projects/{pid}/apps/{app["id"]}');assert r.status_code==200,r.text;return r.json()
        measure('HTTP scoped manifest inspect empty history',inspect_app)
        assert len(wires)==3
        report=dict(source='1258e5bfa5a423c251ab133fb0775ad7a1bba544',mode='SQLite/OFFLINE fixed MockTransport fixture',setup_model_requests=3,profile_new_model_requests=0,network_calls=0,measurements=results)
        Path('/tmp/report-origin-1258e5b/result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    finally:
        active=False
        event.remove(store.engine,'before_cursor_execute',statement)
        setup.close()
