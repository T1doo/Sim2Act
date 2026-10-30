"""Existing full PB Cold input, real clocks/SQLite/loopback owner control.

The imported controller retains all its original happy-path assertions. The
cancel case accepts only its exact terminal-SUCCEEDED assertion as the expected
divergence, then independently checks preserved history and rollback evidence.
No artificial delay or replaced business function drives the timing.
"""

import ast
import hashlib
import json
import socket
import sqlite3
import threading
import time
import traceback
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
import uvicorn
from test_pb_spec_production_controller import (
    observe_original_lease_failures as observe_original_lease_failures,
    test_pb_production_original_source_extraction_explicit_use_and_cold as original_flow,
)
from test_spec_production_controller import no_real_http as no_real_http

from sim2act._sqlite_run_control import active_epochs
from sim2act.api import create_app


def read_db(store, query, values=()):
    c = sqlite3.connect(store.engine.url.database, timeout=.5)
    try:
        return c.execute(query, values).fetchall()
    finally:
        c.close()


def digest_rows(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',',':')).encode()).hexdigest()


@pytest.mark.parametrize('cancel', [True, False], ids=['owner-cancel-during-large-g0','uninterrupted-original-large-cold'])
def test_original_large_cold_control(env, tmp_path, monkeypatch, cancel):
    assert env[0].test_only and env[0].sqlite
    stopped = threading.Event()
    errors, tracked, result = [], [], dict(classification='REAL_CLOCK_MOCK_DEFINITION_FILE_SQLITE_NOT_LIVE_NOT_PG', cancel=cancel)
    server = listener = server_thread = None
    def save():
        result['epochs'] = [dict(run_id=e.header['id'], phase=e.phase, checks=e.checks,
            closed=e.closed, finished_normally=e.finished_normally, seconds=e.seconds,
            complete_g0_seconds=e.g0_seconds, observed_max_checkpoint_gap=e.max_check_gap,
            settlement_lease_margin=e.lease_margin) for _,e in tracked]
        (tmp_path/'large-control-result.json').write_text(json.dumps(result,indent=2)+'\n')
    def observer():
        nonlocal server, listener, server_thread
        handled = False
        eligibility = {}
        try:
            end = time.monotonic()+850
            while not stopped.is_set() and time.monotonic()<end:
                for store, epoch in active_epochs():
                    binding = getattr(epoch.worker,'pa_trial',None)
                    if (binding is None or epoch.header['runtime_id']==binding.contract.runtime_id
                            or store.engine.url.database != env[0].engine.url.database):
                        continue
                    if epoch not in eligibility:
                        refs=read_db(store,'SELECT resource_refs FROM runs WHERE id=?',(epoch.header['id'],))
                        eligibility[epoch]=bool(refs and json.loads(refs[0][0]) == [binding.contract.bindings[1].resource_id])
                    if not eligibility[epoch]:
                        continue
                    if not any(old is epoch for _,old in tracked):
                        tracked.append((store,epoch)); save()
                    # Demand actual large validation activity before control,
                    # rather than cancelling a queued/not-yet-started Run.
                    if (not cancel or handled or epoch.phase!='G0' or epoch.closed
                            or epoch.checks<1000 or time.monotonic()-epoch.started<3):
                        continue
                    handled = True
                    rid=epoch.header['id']
                    iid=read_db(store,'SELECT instance_id FROM internal_app_runs a JOIN internal_run_bindings b ON b.app_run_id=a.id WHERE b.run_id=?',(rid,))[0][0]
                    aid=read_db(store,"SELECT id FROM attempts WHERE run_id=? AND status='RECEIVED'",(rid,))[0][0]
                    prior=read_db(store,'SELECT * FROM attempts WHERE id<>? ORDER BY id',(aid,))
                    target_attempt=read_db(store,'SELECT * FROM attempts WHERE id=?',(aid,))
                    data_before=read_db(store,'SELECT * FROM internal_instance_data ORDER BY instance_id,version')
                    resources_before=read_db(store,'SELECT * FROM resources ORDER BY id')
                    archive_before=read_db(store,'SELECT * FROM delivery_graph_requests ORDER BY app_id,principal_id,kind,request_key')
                    result.update(target_run=rid,target_attempt=aid,g0_seconds_before_request=time.monotonic()-epoch.started,
                        prior_attempts_sha256=digest_rows(prior),prior_attempt_count=len(prior),typed_history_sha256=digest_rows(data_before),
                        received_attempt_sha256=digest_rows(target_attempt),resources_sha256=digest_rows(resources_before),archive_sha256=digest_rows(archive_before),
                        committed_lease_margin_before_control=read_db(store,'SELECT lease_until FROM runs WHERE id=?',(rid,))[0][0]-time.time())
                    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
                    base='http://127.0.0.1:'+str(listener.getsockname()[1])
                    server=uvicorn.Server(uvicorn.Config(create_app(store,epoch.worker.s),log_level='error',access_log=False))
                    server_thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);server_thread.start()
                    deadline=time.monotonic()+5
                    while not server.started and time.monotonic()<deadline:stopped.wait(.01)
                    assert server.started
                    def request(method,path,body=None):
                        raw=None if body is None else json.dumps(body).encode()
                        req=Request(base+path,data=raw,method=method,headers={'Authorization':'Bearer synthetic-test-A','Content-Type':'application/json'})
                        started=time.monotonic()
                        try:
                            with urlopen(req,timeout=8) as response:
                                return response.status,json.loads(response.read()),time.monotonic()-started
                        except HTTPError as error:
                            return error.code,json.loads(error.read()),time.monotonic()-started
                    path=f'/api/internal/instances/{iid}/runs/{rid}'
                    status,progress,elapsed=request('GET',path+'/control-progress')
                    assert status==200 and progress['status']=='RUNNING' and progress['content_access'] is False,progress
                    assert epoch.phase=='G0' and not epoch.closed
                    result['progress']=dict(http=status,seconds=elapsed,metadata=progress)
                    status,reply,elapsed=request('POST',path+'/commands',dict(command='cancel',version=progress['version']))
                    result['cancel_reply']=dict(http=status,seconds=elapsed,metadata=reply)
                    assert status==200 and reply['status']=='RECONCILING',reply
                    result['g0_interrupt_closed']=epoch.closed
                    # Subsequent original fail_owned is allowed to reconcile
                    # only after the original command committed its version.
                    result['_store']=store;result['_prior']=prior;result['_data']=data_before;result['_resources']=resources_before
                    result['_target_attempt']=target_attempt;result['_archive']=archive_before
                    save()
                stopped.wait(.01)
        except BaseException as error:
            errors.append(error);result['observer_error']=traceback.format_exc();save()
    # Do not serialize Store handles into the evidence file.
    original_save=save
    def save():
        private={key:result.pop(key) for key in list(result) if key.startswith('_')}
        try:original_save()
        finally:result.update(private)
    thread=threading.Thread(target=observer,daemon=True);thread.start()
    caught=None
    try:
        try:
            original_flow(env,tmp_path,monkeypatch)
        except AssertionError as error:
            caught=error
        if not cancel:
            assert caught is None, str(caught)
        else:
            assert caught is not None and not errors,errors
            source=Path(original_flow.__code__.co_filename)
            target=next(node.lineno for node in ast.walk(ast.parse(source.read_text()))
                if isinstance(node,ast.Assert) and ast.get_source_segment(source.read_text(),node.test)==
                'result.status_code == 200 and result.json()["status"] == "SUCCEEDED"')
            last=traceback.extract_tb(caught.__traceback__)[-1]
            assert Path(last.filename)==source and last.lineno==target,(last,target,str(caught))
    finally:
        stopped.set();thread.join(10)
        if server is not None:server.should_exit=True
        if server_thread is not None:server_thread.join(10)
        if listener is not None:listener.close()
        save()
    assert not thread.is_alive() and not errors,errors
    assert server_thread is None or not server_thread.is_alive()
    assert tracked and all(epoch.closed for _,epoch in tracked)
    if cancel:
        store=result.pop('_store');rid=result['target_run'];aid=result['target_attempt']
        assert read_db(store,'SELECT status FROM runs WHERE id=?',(rid,))[0][0]=='RECONCILING'
        assert read_db(store,'SELECT status FROM attempts WHERE id=?',(aid,))[0][0]=='RECEIVED'
        assert read_db(store,'SELECT * FROM attempts WHERE id=?',(aid,))==result.pop('_target_attempt')
        assert read_db(store,"SELECT o.status FROM operations o JOIN attempts a ON json_extract(a.parameters,'$.natural_spec.operation_id')=o.id WHERE a.id=?",(aid,))[0][0]=='DISPATCHED'
        assert read_db(store,"SELECT count(*) FROM events WHERE run_id=? AND kind IN ('NS_SETTLED','NS_REJECTED')",(rid,))[0][0]==0
        prior=result.pop('_prior')
        assert len(prior)==5 and read_db(store,'SELECT * FROM attempts WHERE id<>? ORDER BY id',(aid,))==prior
        assert read_db(store,'SELECT * FROM internal_instance_data ORDER BY instance_id,version')==result.pop('_data')
        assert read_db(store,'SELECT * FROM resources ORDER BY id')==result.pop('_resources')
        assert read_db(store,'SELECT * FROM delivery_graph_requests ORDER BY app_id,principal_id,kind,request_key')==result.pop('_archive')
        result['final']=dict(run='RECONCILING',attempt='RECEIVED',prior_history_unchanged=True,received_row_unchanged=True,archive_rows_unchanged=True,no_settled_or_rejected=True,no_new_typed_data=True,all_resource_rows_unchanged=True)
        assert not tracked[-1][1].finished_normally and tracked[-1][1].g0_seconds is None
    else:
        assert len(tracked)==2 and all(epoch.finished_normally and epoch.g0_seconds is not None and epoch.lease_margin>0 for _,epoch in tracked)
        result['final']=dict(original_full_flow='PASS',cold_model_intervals=2)
    exchanges=(tmp_path/'mock-exchanges.jsonl').read_text().splitlines()
    assert len(exchanges)==(6 if cancel else 7)
    result['mock_provider_requests']=len(exchanges)
    result['status']='PASS';save()
