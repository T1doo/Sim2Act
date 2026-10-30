"""Same original large Cold fixture with explicit read-to-write local capability."""

import ast
import json
import threading
import time
import traceback
from pathlib import Path

import pytest
from sqlalchemy import select, update
import test_pb_spec_production_controller as controller_test
from test_cold_control_full_flow import (
    digest_rows, read_db, original_flow,
    test_original_large_cold_control as large_control_flow,
    no_real_http as no_real_http,
    observe_original_lease_failures as observe_original_lease_failures,
)

from sim2act._sqlite_run_control import active_epochs
from sim2act.db import Store, grants, resources


def snapshots(monkeypatch, database_url):
    opened=[]
    def cold_store(*args, **kwargs):
        if args[0]!=database_url:
            return Store(*args, **kwargs)
        store=Store(*args, **kwargs, local_model_snapshots=True)
        opened.append(store)
        return store
    # Only the original test's explicit fresh Cold Store is selected, without
    # modifying the production worker, source callbacks or original assertions.
    monkeypatch.setattr(controller_test, 'Store', cold_store)
    return opened


@pytest.mark.parametrize('cancel', [False, True], ids=['complete','cancel'])
def test_same_large_cold_snapshot_control(env, tmp_path, monkeypatch, cancel):
    opened=snapshots(monkeypatch,env[1].database_url)
    try:
        large_control_flow(env,tmp_path,monkeypatch,cancel)
        assert len(opened)==1
        records=list(opened[0]._local_model_snapshot_records)
        assert len(records)==(1 if cancel else 2)
        assert all(r['outcome']==('ROLLED_BACK' if cancel else 'COMMITTED') for r in records)
        if cancel:
            assert records[0]['writer_seconds'] is None
        else:
            assert all(r['writer_seconds'] is not None and r['writer_seconds']<r['seconds'] for r in records)
    finally:
        (tmp_path/'snapshot-writer-timings.json').write_text(json.dumps(dict(
            classification='ORIGINAL_LARGE_COLD_REAL_CLOCK_FILE_SQLITE_WAL_FIXED_MOCK',
            cancel=cancel,records=[r for s in opened for r in s._local_model_snapshot_records]),indent=2)+'\n')


@pytest.mark.parametrize('change', ['input-content','revoke'])
def test_same_large_cold_conflict_cannot_settle_old_snapshot(env,tmp_path,monkeypatch,change):
    opened=snapshots(monkeypatch,env[1].database_url)
    stop=threading.Event()
    errors=[]
    observed={}
    def mutate():
        try:
            end=time.monotonic()+850
            while not stop.is_set() and time.monotonic()<end:
                for store,epoch in active_epochs():
                    if store not in opened or epoch.phase!='G0' or epoch.checks<1000 or time.monotonic()-epoch.started<3:
                        continue
                    rid=epoch.header['id']
                    ref=json.loads(read_db(store,'SELECT resource_refs FROM runs WHERE id=?',(rid,))[0][0])[0]
                    aid=read_db(store,"SELECT id FROM attempts WHERE run_id=? AND status='RECEIVED'",(rid,))[0][0]
                    observed.update(store=store,rid=rid,aid=aid,
                        attempt=read_db(store,'SELECT * FROM attempts WHERE id=?',(aid,)),
                        typed=read_db(store,'SELECT * FROM internal_instance_data ORDER BY instance_id,version'),
                        archive=read_db(store,'SELECT * FROM delivery_graph_requests ORDER BY app_id,principal_id,kind,request_key'))
                    started=time.monotonic()
                    with store.tx() as c:
                        if change=='revoke':
                            result=c.execute(update(grants).where(grants.c.resource_id==ref,
                                grants.c.principal_id==epoch.header['principal_id'],grants.c.tool_ref=='resource.read')
                                .values(revoked=True,revision=grants.c.revision+1))
                        else:
                            # Synthetic fixture edit is intentionally not a valid
                            # current source. Stale G0 must not authorize writes.
                            old=c.execute(select(resources.c.content).where(resources.c.id==ref)).scalar_one()
                            result=c.execute(update(resources).where(resources.c.id==ref).values(content=old+'\nConcurrent synthetic edit'))
                        assert result.rowcount>0
                    observed['concurrent_commit_seconds']=time.monotonic()-started
                    observed['committed_while_g0_open']=epoch.phase=='G0' and not epoch.closed
                    return
                stop.wait(.01)
            raise AssertionError('Did not observe the actual large G0')
        except BaseException as error:
            errors.append(error)
    thread=threading.Thread(target=mutate,daemon=True);thread.start()
    caught=None
    try:
        try:
            original_flow(env,tmp_path,monkeypatch)
        except AssertionError as error:
            caught=error
    finally:
        stop.set();thread.join(10)
    assert not thread.is_alive() and not errors,errors
    assert caught is not None
    source=Path(original_flow.__code__.co_filename)
    line=next(n.lineno for n in ast.walk(ast.parse(source.read_text())) if isinstance(n,ast.Assert)
        and ast.get_source_segment(source.read_text(),n.test)=='result.status_code == 200 and result.json()["status"] == "SUCCEEDED"')
    last=traceback.extract_tb(caught.__traceback__)[-1]
    assert Path(last.filename)==source and last.lineno==line,(last,line,str(caught))
    assert len(opened)==1 and observed['committed_while_g0_open']
    store,rid,aid=observed['store'],observed['rid'],observed['aid']
    assert read_db(store,'SELECT * FROM attempts WHERE id=?',(aid,))==observed['attempt']
    assert read_db(store,'SELECT * FROM internal_instance_data ORDER BY instance_id,version')==observed['typed']
    assert read_db(store,'SELECT * FROM delivery_graph_requests ORDER BY app_id,principal_id,kind,request_key')==observed['archive']
    assert read_db(store,"SELECT count(*) FROM events WHERE run_id=? AND kind IN ('NS_SETTLED','NS_REJECTED')",(rid,))[0][0]==0
    state=read_db(store,'SELECT status FROM runs WHERE id=?',(rid,))[0][0]
    assert state=='WAITING_RESOURCE'
    assert read_db(store,"SELECT o.status FROM operations o JOIN attempts a ON json_extract(a.parameters,'$.natural_spec.operation_id')=o.id WHERE a.id=?",(aid,))[0][0]=='DISPATCHED'
    records=list(store._local_model_snapshot_records)
    assert len(records)==1 and records[0]['outcome']=='ROLLED_BACK'
    exchanges=(tmp_path/'mock-exchanges.jsonl').read_text().splitlines()
    assert len(exchanges)==6
    (tmp_path/'snapshot-conflict-result.json').write_text(json.dumps(dict(status='PASS',
        classification='ORIGINAL_LARGE_COLD_REAL_CLOCK_FILE_SQLITE_WAL_FIXED_MOCK',change=change,
        concurrent_commit_seconds=observed['concurrent_commit_seconds'],committed_while_g0_open=True,
        final_state=state,received_attempt_unchanged=True,typed_history_unchanged=True,
        archive_unchanged=True,no_settled_or_rejected=True,mock_provider_requests=6,records=records),indent=2)+'\n')
