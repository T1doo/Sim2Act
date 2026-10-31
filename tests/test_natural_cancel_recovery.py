"""Default recovery of an actual large Cold writer-cancel database.

Input is the preserved synthetic real-clock/FixedMock fixture, not fabricated
terminal rows. No model, source resolver or current material read is allowed.
"""
import gzip
import hashlib
import json
import os
import subprocess
import sys
import sqlite3
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, insert, select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (Store, attempts, delivery_graph_requests, events, grants,
    internal_app_runs, internal_instance_data, operation_intents, operations, reservations, resources, runs)
from sim2act.worker import Worker

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'docs/evidence/owned-read-retraction-20261031/full-acceptance'


@pytest.fixture
def cancelled(tmp_path, monkeypatch):
    raw = gzip.decompress((EVIDENCE/'cancel-fixture.db.gz').read_bytes())
    manifest = json.loads((EVIDENCE/'archive-manifest.json').read_text())
    expected = next(r['source_sha256'] for r in manifest['items'] if r['file']=='cancel-fixture.db.gz')
    assert hashlib.sha256(raw).hexdigest() == expected
    path = tmp_path/'actual-cancel.db';path.write_bytes(raw)
    store = Store('sqlite:///'+str(path), test_only=True)
    settings = Settings('sqlite:///'+str(path), tmp_path, mode='mock')
    with store.tx() as c:
        job = dict(c.execute(select(runs).where(runs.c.status=='RECONCILING',
            runs.c.cancel_intent.is_(True))).mappings().one())
        row = dict(c.execute(select(attempts).where(attempts.c.run_id==job['id'],
            attempts.c.status=='RECEIVED')).mappings().one())
        op = dict(c.execute(select(operations).where(
            operations.c.id==row['parameters']['natural_spec']['operation_id'])).mappings().one())
    import time
    assert job['lease_until'] < time.time()  # Naturally expired; never rewrite clock/lease.
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Recovery must not send, resolve current authority or read current material')
    from sim2act import natural_live_admission, spec_production, tools
    from sim2act.model import MockModel, InternModel
    monkeypatch.setattr(MockModel, 'request', forbidden)
    monkeypatch.setattr(InternModel, 'request', forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)
    monkeypatch.setattr(natural_live_admission, '_current', forbidden)
    monkeypatch.setattr(natural_live_admission, 'authorized_read', forbidden)
    monkeypatch.setattr(spec_production, 'source', forbidden)
    monkeypatch.setattr(tools, 'authorized_read', forbidden)
    def sql_guard(c, cursor, statement, parameters, context, many):
        assert not ('resources.content' in statement.lower()), 'Current resource body read'
    event.listen(store.engine, 'before_cursor_execute', sql_guard)
    yield store, settings, job, row, op, calls
    event.remove(store.engine, 'before_cursor_execute', sql_guard)
    store.engine.dispose()


def snapshot(store):
    with store.tx() as c:
        result = {t.name:[dict(r) for r in c.execute(select(t)).mappings()]
            for t in (runs,attempts,operations,internal_app_runs,internal_instance_data,
                      reservations,delivery_graph_requests,operation_intents,events)}
    # The test oracle compares the synthetic fixture's bodies outside the
    # guarded application engine. Product recovery remains forbidden to read
    # resources.content throughout every default Worker/API call.
    with sqlite3.connect(store.engine.url.database) as c:
        result['resources'] = c.execute('SELECT * FROM resources ORDER BY id').fetchall()
    return result


def test_default_once_closes_actual_received_without_replay_and_repeated_cancel_is_idempotent(cancelled):
    store, settings, job, row, op, calls = cancelled
    before = snapshot(store)
    assert Worker(store, settings).once() is True
    after = snapshot(store)
    current = next(r for r in after['runs'] if r['id']==job['id'])
    assert current['status']=='CANCELLED' and current['version']==job['version']+1
    assert current['fence']==job['fence']+1 and current['lease_until']==0
    got = next(r for r in after['attempts'] if r['id']==row['id'])
    assert got=={**row,'status':'REJECTED_KNOWN'}
    got = next(r for r in after['operations'] if r['id']==op['id'])
    assert got=={**op,'status':'REJECTED_KNOWN'}
    for table in ('reservations','delivery_graph_requests','resources','internal_instance_data'):
        assert after[table]==before[table]
    iid = next(r['instance_id'] for r in after['internal_app_runs'] if r['status']=='CANCELLED')
    with TestClient(create_app(store,settings)) as client:
        client.headers['Authorization']='Bearer synthetic-test-A'
        route=f'/api/internal/instances/{iid}/runs/{job["id"]}'
        for _ in range(2):
            reply=client.post(route+'/commands',json=dict(command='cancel',version=current['version']))
            assert reply.status_code==200 and reply.json()['status']=='CANCELLED'
        stale=client.post(route+'/commands',json=dict(command='cancel',version=job['version']))
        assert stale.status_code==409
    assert snapshot(store)==after and Worker(store,settings).once() is False and calls==[]


@pytest.mark.parametrize('damage', ['response','usage','body-seal','received-anchor','reservation',
    'intent','unknown-operation','started','cancel-intent','live-owner','phase-seal'])
def test_invalid_receipt_or_live_owner_never_partially_closes(cancelled, damage):
    store, settings, job, row, op, calls=cancelled
    with store.tx() as c:
        if damage=='response':
            c.execute(update(attempts).where(attempts.c.id==row['id']).values(response={}))
        elif damage=='usage':
            c.execute(update(attempts).where(attempts.c.id==row['id']).values(usage={'status':'unknown','tokens':None}))
        elif damage=='body-seal':
            from sim2act.natural_source_archives import RESPONSE
            c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id==job['id'],
                delivery_graph_requests.c.kind==RESPONSE+'_seal',delivery_graph_requests.c.request_key==row['id']))
        elif damage=='received-anchor':
            c.execute(delete(events).where(events.c.run_id==job['id'],events.c.kind=='NS_RECEIVED'))
        elif damage=='reservation':c.execute(delete(reservations).where(reservations.c.id==row['id']))
        elif damage=='intent':c.execute(update(operations).where(operations.c.id==op['id']).values(fingerprint='f'*64))
        elif damage=='unknown-operation':
            c.execute(insert(operations).values(id='synthetic-unknown-extra',run_id=job['id'],call_id='unknown',
                fingerprint='a'*64,tool_ref='resource.read',status='DISPATCHED'))
        elif damage=='started':c.execute(update(attempts).where(attempts.c.id==row['id']).values(status='STARTED'))
        elif damage=='cancel-intent':c.execute(update(runs).where(runs.c.id==job['id']).values(cancel_intent=False))
        elif damage=='live-owner':
            import time
            c.execute(update(runs).where(runs.c.id==job['id']).values(lease_until=time.time()+30))
        else:
            from sim2act import natural_live_admission as gate
            c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.principal_id==job['principal_id'],
                delivery_graph_requests.c.kind==gate.PHASE+'_seal',delivery_graph_requests.c.request_key=='cold'))
    before=snapshot(store)
    assert Worker(store,settings).once() is False
    assert snapshot(store)==before and calls==[]


def test_revocation_does_not_prevent_receipt_only_cancel(cancelled):
    store,settings,job,row,op,calls=cancelled
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.project_id==job['project_id']).values(revoked=True))
    assert Worker(store,settings).once() is True and calls==[]
    with store.tx() as c:assert c.execute(select(runs.c.status).where(runs.c.id==job['id'])).scalar_one()=='CANCELLED'


@pytest.mark.parametrize('damage',['run-version','run-result','ledger','ledger-resealed','capture','app-status','app-output','intent'])
def test_late_event_failure_rolls_back_received_operation_anchor_and_terminal(cancelled, monkeypatch, damage):
    store,settings,job,row,op,calls=cancelled
    before=snapshot(store);original=store.event
    def broken(c,rid,kind,data):
        original(c,rid,kind,data)
        if kind=='COLD_CANCEL_RECOVERED':
            if damage=='run-version':
                c.execute(update(runs).where(runs.c.id==rid).values(version=job['version']+8))
            elif damage=='run-result':
                c.execute(update(runs).where(runs.c.id==rid).values(result={'unexpected':'late output'}))
            elif damage=='ledger':
                from sim2act.production_trial_journal import KIND
                c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id==job['project_id'],
                    delivery_graph_requests.c.kind==KIND+'_seal'))
            elif damage=='ledger-resealed':
                import copy
                from sim2act import production_trial_journal as journal
                saved=c.execute(select(delivery_graph_requests).where(
                    delivery_graph_requests.c.kind==journal.KIND,
                    delivery_graph_requests.c.app_id==job['project_id'])).mappings().one()
                prior=saved['snapshot'];current=copy.deepcopy(prior)
                ledger=current['response']['ledger'];ledger['halted']=True
                next(s for s in ledger['slots'] if s['identity']['attempt_id']==row['id'])['accepted']=False
                journal._cas_pair(c,saved['principal_id'],saved['app_id'],journal.KIND,
                    saved['request_key'],prior,current)
            elif damage=='capture':
                from sim2act.production_trial_sender import CAPTURE
                c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id==rid,
                    delivery_graph_requests.c.kind==CAPTURE+'_seal',delivery_graph_requests.c.request_key==row['id']))
            elif damage=='app-status':
                c.execute(update(internal_app_runs).where(internal_app_runs.c.status=='CANCELLED').values(status='SUCCEEDED'))
            elif damage=='app-output':
                c.execute(update(internal_app_runs).where(internal_app_runs.c.status=='CANCELLED')
                    .values(output={'unexpected':'late output'},result_version=1))
            else:
                c.execute(update(operation_intents).where(operation_intents.c.operation_id==op['id'])
                    .values(request={'tool':'synthetic-corruption'}))
    monkeypatch.setattr(store,'event',broken)
    assert Worker(store,settings).once() is False
    assert snapshot(store)==before and calls==[]


def test_two_default_workers_commit_recovery_once(cancelled):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    store,settings,job,row,op,calls=cancelled
    other=Store(settings.database_url,test_only=True);barrier=Barrier(2)
    def work(selected):
        worker=Worker(selected,settings);barrier.wait(timeout=5);return worker.once()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(work,selected) for selected in (store,other)]
            assert sorted(f.result(timeout=20) for f in futures)==[False,True]
        with store.tx() as c:
            assert len(c.execute(select(events.c.id).where(events.c.run_id==job['id'],
                events.c.kind=='COLD_CANCEL_RECOVERED')).all())==1
            assert c.execute(select(runs.c.version).where(runs.c.id==job['id'])).scalar_one()==job['version']+1
        assert calls==[]
    finally:other.engine.dispose()


def test_repeat_pending_cancel_preserves_version_and_received_history(cancelled):
    store,settings,job,row,op,calls=cancelled
    from sim2act.db import internal_run_bindings
    with store.tx() as c:
        iid=c.execute(select(internal_app_runs.c.instance_id).join(internal_run_bindings,
            internal_run_bindings.c.app_run_id==internal_app_runs.c.id).where(
                internal_run_bindings.c.run_id==job['id'])).scalar_one()
    before=snapshot(store)
    with TestClient(create_app(store,settings)) as client:
        client.headers['Authorization']='Bearer synthetic-test-A'
        for _ in range(2):
            reply=client.post(f'/api/internal/instances/{iid}/runs/{job["id"]}/commands',
                json=dict(command='cancel',version=job['version']))
            assert reply.status_code==200 and reply.json()['status']=='RECONCILING'
    assert snapshot(store)==before and calls==[]


def test_known_charge_with_denied_business_admission_can_only_cancel(cancelled):
    """Reachable denied-last-slot variant; never fabricate business acceptance."""
    import copy
    from sim2act import production_trial_journal as journal
    store,settings,job,row,op,calls=cancelled
    with store.tx() as c:
        saved=c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.kind==journal.KIND,
            delivery_graph_requests.c.principal_id==job['principal_id'],
            delivery_graph_requests.c.app_id==job['project_id'])).mappings().one()
        previous=saved['snapshot'];current=copy.deepcopy(previous)
        ledger=current['response']['ledger'];ledger['halted']=True
        slot=next(s for s in ledger['slots'] if s['identity']['attempt_id']==row['id'])
        assert slot['settlement']['outcome']=='RECEIVED';slot['accepted']=False
        from sim2act.production_trial_policy import Ledger, _ledger
        _ledger(Ledger.model_validate_json(json.dumps(ledger)))
        journal._cas_pair(c,saved['principal_id'],saved['app_id'],journal.KIND,
                          saved['request_key'],previous,current)
    before=snapshot(store)
    assert Worker(store,settings).once() is True and calls==[]
    after=snapshot(store)
    assert before['delivery_graph_requests']==after['delivery_graph_requests']
    assert next(r for r in after['attempts'] if r['id']==row['id'])=={**row,'status':'REJECTED_KNOWN'}


def test_new_interpreter_default_worker_recovers_then_reopens_without_replay(cancelled):
    store,settings,job,row,op,calls=cancelled
    script='''
import json,sys
from pathlib import Path
from sqlalchemy import select
from sim2act.db import Store,runs
from sim2act.config import Settings
from sim2act.worker import Worker
from sim2act.model import MockModel
def forbidden(*args,**kwargs):raise AssertionError('No model replay during process recovery')
MockModel.request=forbidden
s=Store(sys.argv[1],test_only=True);w=Worker(s,Settings(sys.argv[1],Path(sys.argv[2]),mode='mock'))
worked=w.once()
with s.tx() as c:r=c.execute(select(runs.c.status).where(runs.c.id==sys.argv[3])).scalar_one()
print(json.dumps(dict(worked=worked,status=r)));s.engine.dispose()
'''
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')
    command=[sys.executable,'-c',script,settings.database_url,str(settings.data_dir),job['id']]
    for expected in (True,False):
        result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=30,check=True)
        assert json.loads(result.stdout)==dict(worked=expected,status='CANCELLED')
    assert calls==[]
