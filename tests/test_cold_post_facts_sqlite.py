"""Cold post facts are data only; prewrite continuation and Run identity stay old."""
import pytest
from sqlalchemy import select,update
from accounted_sqlite_fixture import seed_cold,segment
from test_cold_accounted_sqlite import sql_facts
from sim2act import natural_spec_runtime as runtime,_cold_source_packet as owned
from sim2act.db import runs
from sim2act.errors import DomainError


@pytest.mark.parametrize('phase',['pre','post'])
def test_only_post_cold_rows_transfer_and_original_job_root_is_retained(sql_facts,phase):
    f=sql_facts;seed_cold(f)
    with f.store.tx() as c,segment(f,c,phase=phase) as s:
        job=c.execute(select(runs).where(runs.c.id==f.cold_job['id'])).mappings().one()
        s.graph.add('current',dict(job))
        reader=runtime._cold_run_facts(f.store,c,job,s.graph)
        assert reader._source_owned is (phase=='post')
        assert s.graph.inputs[reader.key]['job'] is job
        rows=reader.attempt_rows()
        assert len(rows)==0
        assert type(rows) is list  # Original sorted public read protocol.
        assert owned.image.is_kind(reader._get('attempts'),'l') if phase=='post' else type(reader._get('attempts')) is list
        original={'outputs':{'one':['synthetic']},'proved':[]}
        value=reader.produced_value('receipt-phase',original)
        if phase=='post':
            assert owned.image.is_kind(value,'d')
            original['outputs']['one'].append('producer mutation')
            assert owned.image.plain(value)=={'outputs':{'one':['synthetic']},'proved':[]}
            assert owned.image.same(owned.fact(s.graph,reader.key+':produced:receipt-phase:1'),value)
        else:assert value is original
        reader.check(f.store,c,job)


@pytest.mark.parametrize('damage',['sql','job-copy','root-copy'])
def test_post_transfer_does_not_cache_transaction_or_run_identity(sql_facts,damage):
    f=sql_facts;seed_cold(f);reached=False
    with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='post') as s:
        job=c.execute(select(runs).where(runs.c.id==f.cold_job['id'])).mappings().one()
        s.graph.add('current',dict(job))
        reader=runtime._cold_run_facts(f.store,c,job,s.graph)
        reader.attempt_rows()
        if damage=='sql':
            c.execute(update(runs).where(runs.c.id==job['id']).values(version=job['version']+1))
        elif damage=='job-copy':reader.job=dict(job)
        else:s.graph.inputs[reader.key]=dict(job=dict(job))
        reached=True
        reader.check(f.store,c,job)
    assert reached


def _read_actual_post(data,worker,rid,full,store,*,pending):
    from sim2act import pa_spec_apps as spec,pb_natural_specs as pb
    with store.tx() as c,pb._source_reads(store,c):
        changes=c.connection.driver_connection.total_changes
        job=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
        assert job['status']==('RUNNING' if pending else 'SUCCEEDED')
        binding=spec.bound(store,c,job['principal_id'],job,full)
        reference=spec.receipts(store,c,job,binding,allow_pending=True)
        roles=dict(source=full.model_copy(deep=True),generate=None,platform=full,
            trial=full.model_copy(deep=True),per_use=full.model_copy(deep=True))
        with runtime._cold_graph_read(worker,c,dict(current=dict(job)),roles,'post') as guard:
            facts=runtime._cold_run_facts(store,c,job,guard)
            assert facts._source_owned
            assert guard.inputs[facts.key]['job'] is job
            manifest=spec.AppManifest.model_validate(binding['draft']['candidate']['manifest'])
            runtime._counters_from_facts(store,c,job,manifest,facts)
            outputs,proved=spec._cold_receipts(store,c,job,binding,facts,allow_pending=True)
            assert owned.image.compat((outputs,proved))==reference
            assert owned.image.is_kind(facts._get('attempts'),'l')
            if pending:
                assert any(row['status']=='RECEIVED' for row in facts.attempt_rows())
                assert any(name.startswith('node-proof:pending:') for name in facts._node_proofs)
            else:
                assert len(facts.attempt_rows())==2
                assert all(row['status']=='VERIFIED' for row in facts.attempt_rows())
                assert len(facts._node_proofs)==2
            assert owned.image.is_kind(outputs,'d') and owned.image.is_kind(proved,'l')
            facts.checked_receipts(binding,outputs,proved)
        assert c.connection.driver_connection.total_changes==changes


def _actual_completed_cold_post(data,worker,rid,full,store):
    from test_pb_natural_specs import drive_to_success
    from test_natural_spec_apps import transport
    from test_pb_natural_uses import THIRD
    import sys
    # Observe the original writer entry after the actual receive commit. This
    # data-only post-shaped read checks the pending consumer, not a W5/G1 pass.
    # No callee, SQL row, clock, status or authority result is replaced.
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    target=runtime._model_settlement_writer.__wrapped__.__code__
    pending_reads=[]
    def pending_reader(code,offset):
        frame=sys._getframe(1)
        if not pending_reads and frame.f_locals['job']['id']==rid:
            pending_reads.append(True)
            _read_actual_post(data,worker,rid,full,store,pending=True)
    sent=[]
    monitor.use_tool_id(slot,'Read-only actual received Cold facts protocol')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,pending_reader)
        monitor.set_local_events(slot,target,monitor.events.PY_START)
        drive_to_success(data,rid,transport(sent,THIRD))
    finally:
        monitor.set_local_events(slot,target,0)
        monitor.register_callback(slot,monitor.events.PY_START,None)
        monitor.free_tool_id(slot)
    assert pending_reads==[True] and len(sent)==2
    _read_actual_post(data,worker,rid,full,store,pending=False)


def test_real_nonempty_post_cold_verified_proofs_and_receipt_result(tmp_path,monkeypatch):
    from test_cold_binding_graph_integration import test_plain_pb_first_binding_producer_equals_public_complete_ancestry
    test_plain_pb_first_binding_producer_equals_public_complete_ancestry(
        tmp_path,monkeypatch,_post_facts_case=True)
