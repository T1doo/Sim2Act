"""One original large flow with passive, scoped CPython function timing.

No callee, input, SQL or business clock is replaced by the profiler. Times
include instrumentation, and nested inclusive values must not be added.
"""

import json
import sys
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite

from test_cold_snapshot_full_flow import snapshots
from test_cold_control_full_flow import test_original_large_cold_control as large_flow
from test_spec_production_controller import no_real_http as no_real_http
from test_pb_spec_production_controller import observe_original_lease_failures as observe_original_lease_failures

from sim2act import natural_spec_runtime as runtime
from sim2act import natural_live_admission as gate
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as dispatch
from sim2act import _cold_base_segment as base
from sim2act import _cold_policy_segment as policy
from sim2act import _cold_graph_structure_guard as structure


@contextmanager
def profile(opened,tmp_path):
    monitor=sys.monitoring
    slot=next(i for i in (4,3,5) if monitor.get_tool(i) is None)
    targets=[(runtime._ColdGraphRead.check,'graph.check'),
        (runtime._ColdGraphRead._check_dynamic,'graph.dynamic'),
        (runtime._ColdGraphRead.input_bytes,'graph.input_bytes'),
        (runtime._ColdTrialGraph.commit,'graph.commit'),
        (runtime._ColdTrialGraph._typed_parameter_models,'graph.typed_parameters'),
        (runtime._ColdTrialGraph._typed_values_from_models,'graph.typed_values'),
        (runtime._cold_binding_limits_facet,'binding'),
        (runtime._ModelSettlementRead.check,'proof.check'),
        (runtime._ModelSettlementRead._inputs_current,'proof.inputs_current'),
        (runtime._ModelSettlementRead._inputs_key,'proof.inputs_key'),
        (runtime._ModelSettlementRead.live,'proof.live'),
        (runtime._cold_audit_seed,'graph.audit_seed'),
        (gate._trial_typed_storage,'typed.storage'),
        (gate._trial_typed_values,'typed.values'),
        (spec._cold_receipts,'receipts'),
        (dispatch._graph_journal_chain,'journal.chain'),
        (base.fixed_serializers,'schema.fixed_serializers'),
        (policy._schema_current,'schema.current'),
        (structure.select,'structure.select'),
        (structure.select_frontier,'structure.frontier'),
        (structure._qualified,'structure.qualify'),
        (runtime._cold_graph_bytes,'graph.serialize'),
        (Connection.commit,'sql.commit'),
        (SQLiteDialect_pysqlite.do_commit,'sql.driver_commit')]
    codes={fn.__code__:name for fn,name in targets}
    stacks,records,epochs,sql={}, {}, [], {}
    attached=[]
    native_sites={structure.select.__code__,structure.select_frontier.__code__,
        runtime._cold_graph_bytes.__code__,SQLiteDialect_pysqlite.do_commit.__code__}
    native_entries={structure._NATIVE_MATCH:'native.compare',structure._NATIVE_SNAPSHOT:'native.capture'}
    def current():
        if not opened:return
        control=opened[0]._local_model_control
        epoch=getattr(control.local,'epoch',None) if control is not None else None
        if epoch is not None and not any(e is epoch for e in epochs):epochs.append(epoch)
        return epoch
    def aggregate(phase,name,elapsed,child=0):
        entry=records.setdefault(phase,{}).setdefault(name,dict(calls=0,inclusive_seconds=0.,exclusive_among_targets_seconds=0.))
        entry['calls']+=1;entry['inclusive_seconds']+=elapsed;entry['exclusive_among_targets_seconds']+=elapsed-child
    def before(c,cursor,statement,parameters,context,many):
        epoch=current()
        if epoch is None:return
        verb=statement.lstrip().partition(' ')[0].upper()
        sql[id(context)]=(epoch,verb,time.monotonic())
        if verb in ('INSERT','UPDATE','DELETE'):
            boundaries.setdefault(id(epoch),{}).setdefault('first_dml_wall',time.time())
    def after(c,cursor,statement,parameters,context,many):
        old=sql.pop(id(context),None)
        if old:aggregate(old[0].phase,'sql.execute.'+old[1],time.monotonic()-old[2])
    def failed(context):
        old=sql.pop(id(context.execution_context),None)
        if old:aggregate(old[0].phase,'sql.failed.'+old[1],time.monotonic()-old[2])
    boundaries={}
    def push(token,name):
        epoch=current()
        if epoch is None:return
        if not attached:
            engine=opened[0].engine
            for kind,fn in [('before_cursor_execute',before),('after_cursor_execute',after),('handle_error',failed)]:
                event.listen(engine,kind,fn);attached.append((engine,kind,fn))
        if name=='sql.commit':boundaries.setdefault(id(epoch),{})['commit_start_wall']=time.time()
        stacks.setdefault(threading.get_ident(),[]).append([token,name,epoch,time.monotonic(),0.])
    def pop(token):
        frames=stacks.get(threading.get_ident(),[])
        if not frames or frames[-1][0]!=token:return
        _,name,epoch,started,child=frames.pop();elapsed=time.monotonic()-started
        aggregate(epoch.phase,name,elapsed,child)
        if name=='sql.commit':boundaries.setdefault(id(epoch),{})['commit_end_wall']=time.time()
        if frames:frames[-1][4]+=elapsed
    def start(code,offset):push(code,codes[code])
    def end(code,offset,value=None):pop(code)
    def native_name(callee,arg0):
        # Bound C methods are freshly materialized: identify their exact owner
        # type and name rather than the transient bound method's identity.
        for fn,name in native_entries.items():
            if callee is fn:return name
        owner=getattr(callee,'__self__',None)
        if owner is None:owner=arg0
        name=getattr(callee,'__name__',None)
        if type(owner) is runtime._ColdGraphPickler and name=='dump':return 'pickle.dump'
        if type(owner).__module__=='sqlite3' and name=='commit':return 'sqlite.commit'
    def call(code,offset,callee,arg0):
        name=native_name(callee,arg0)
        if name:push((code,offset),name)
    def returned(code,offset,callee,arg0):
        if native_name(callee,arg0):pop((code,offset))
    monitor.use_tool_id(slot,'Sim2Act scoped Cold passive timing')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,start)
        monitor.register_callback(slot,monitor.events.PY_RETURN,end)
        monitor.register_callback(slot,monitor.events.PY_UNWIND,end)
        monitor.register_callback(slot,monitor.events.CALL,call)
        monitor.register_callback(slot,monitor.events.C_RETURN,returned)
        monitor.register_callback(slot,monitor.events.C_RAISE,returned)
        for code in codes:monitor.set_local_events(slot,code,monitor.events.PY_START|monitor.events.PY_RETURN
            | (monitor.events.CALL if code in native_sites else 0))
        monitor.set_events(slot,monitor.events.PY_UNWIND)
        yield records
    finally:
        monitor.set_events(slot,0)
        for code in codes:monitor.set_local_events(slot,code,0)
        for kind in (monitor.events.PY_START,monitor.events.PY_RETURN,monitor.events.PY_UNWIND,
                monitor.events.CALL,monitor.events.C_RETURN,monitor.events.C_RAISE):
            monitor.register_callback(slot,kind,None)
        monitor.free_tool_id(slot)
        for engine,kind,fn in attached:event.remove(engine,kind,fn)
        (tmp_path/'passive-profile.json').write_text(json.dumps(dict(
            classification='PASSIVELY_INSTRUMENTED_ORIGINAL_LARGE_COLD_FIXED_MOCK_SQLITE_WAL',
            records=records,pending_frames=sum(map(len,stacks.values())),pending_sql=len(sql),
            epochs=[dict(ordinal=i+1,**boundaries.get(id(e),{})) for i,e in enumerate(epochs)],
            limitations='Instrumentation included; exclusive subtracts only observed target children; inclusive overlaps. SQL execute excludes fetch/materialization. Native compare includes Python reducers. Commit includes I/O; correlate fsync trace independently.'),indent=2)+'\n')


def test_original_large_cold_scoped_profile(env,tmp_path,monkeypatch):
    opened=snapshots(monkeypatch,env[1].database_url)
    with profile(opened,tmp_path) as measured:
        large_flow(env,tmp_path,monkeypatch,False)
    assert len(opened)==1
    assert json.loads((tmp_path/'passive-profile.json').read_text())['pending_frames']==0
    assert measured['G1']['graph.commit']['calls']==2
    assert len(opened[0]._local_model_snapshot_records)==2
    assert all(r['outcome']=='COMMITTED' for r in opened[0]._local_model_snapshot_records)
    (tmp_path/'snapshot-writer-timings.json').write_text(json.dumps(list(opened[0]._local_model_snapshot_records),indent=2)+'\n')


def test_scoped_profile_pairs_native_success_failure_and_real_sql(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'timing-probe.db'))
    epoch=SimpleNamespace(phase='G1')
    opened=[SimpleNamespace(engine=engine,_local_model_control=SimpleNamespace(local=SimpleNamespace(epoch=epoch)))]
    try:
        with profile(opened,tmp_path) as measured:
            assert runtime._cold_graph_bytes({'synthetic':[1,2]})
            with pytest.raises(runtime.DomainError):runtime._cold_graph_bytes(object())
            with engine.connect() as c:
                c.exec_driver_sql('CREATE TABLE probe (value INTEGER)')
                c.exec_driver_sql('INSERT INTO probe VALUES (1)')
                c.commit()
        result=json.loads((tmp_path/'passive-profile.json').read_text())
        assert result['pending_frames']==result['pending_sql']==0
        assert measured['G1']['pickle.dump']['calls']==2
        assert measured['G1']['sqlite.commit']['calls']==1
        assert measured['G1']['sql.execute.INSERT']['calls']==1
        assert result['epochs'][0]['first_dml_wall']<=result['epochs'][0]['commit_start_wall']<=result['epochs'][0]['commit_end_wall']
    finally:engine.dispose()
