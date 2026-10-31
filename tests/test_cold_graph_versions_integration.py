"""One actual C1 five-write/G1 save with the default version layer.

Finite original configured Mock fixture, virtual BUSINESS time only. This is
Graph protocol semantics, never real-clock ordinary30 acceptance/live/PG.
"""
from contextlib import contextmanager
import hashlib
import json
import sys
import threading

import pytest
from sqlalchemy import select
import test_natural_spec_apps as apps
from cold_configured_tail_fixture import MockCap,build_prefix,close_case,restore_case
from cold_semantic_clock import SemanticClock
from test_cold_configured_semantic_tail import TailStop
from sim2act import natural_spec_runtime as runtime,_cold_graph_versions as versions
from sim2act.db import attempts,operations


def test_default_version_layer_through_original_writes_postproof_and_commit(tmp_path,monkeypatch):
    clock=SemanticClock(monkeypatch);cap=MockCap(monkeypatch)
    cap.exchange_limit,cap.method_limit=6,8
    threads_before=set(threading.enumerate())
    with monkeypatch.context() as patch:template=build_prefix(tmp_path/'prefix',patch,clock,cap)
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    ctor=runtime._ColdGraphRead.__init__.__code__
    observed=[];exports=[]
    def returned(code,offset,result):
        graph=sys._getframe(1).f_locals['self']
        version=graph.content_version()
        assert type(version) is versions.VERSION
        observed.append((graph,version))
    monitor.use_tool_id(slot,'Real Graph versions through default Cold writer')
    try:
        monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        monitor.set_local_events(slot,ctor,monitor.events.PY_RETURN)
        with monkeypatch.context() as patch:
            case=restore_case(template,tmp_path/'candidate',patch,clock);cap.new_case()
            context=runtime._model_settlement_read
            advance=runtime.advance_model
            state={'normal_post':False}
            @contextmanager
            def post(*args,**kwargs):
                with context(*args,**kwargs) as result:
                    proof=result[2]
                    assert proof is not None and proof.state=='READY'
                    graph=proof.post_graph.guard
                    version=graph.content_version()
                    assert proof._post_graph_version is version
                    assert proof.inputs['post_graph']['raw'] is version.raw
                    assert proof.inputs['post_graph']['key'] is version.key
                    assert hashlib.sha256(version.raw).hexdigest()==version.key
                    exports.append({'phase':graph.phase,'sequence':version.sequence,
                        'bytes':len(version.raw),'sha256':version.key})
                    yield result
                assert proof.state=='CLOSED' and not proof.active
                state['normal_post']=True
            def advanced(*args,**kwargs):
                result=advance(*args,**kwargs)
                if state['normal_post']:
                    assert result is True
                    raise TailStop()  # Original tx has committed before advance returns.
                return result
            patch.setattr(runtime,'_model_settlement_read',post)
            patch.setattr(runtime,'advance_model',advanced)
            try:
                worker=case.factory(case.store,case.data[1],goal_planner_transport=apps.transport([],apps.COLD))
                with pytest.raises(TailStop):worker.once()
                assert (cap.case_exchanges,cap.case_methods)==(1,1)
                with case.store.tx() as c:
                    rows=[dict(r) for r in c.execute(select(attempts).where(attempts.c.run_id==template.cold_id)).mappings()]
                    model_ops=[dict(r) for r in c.execute(select(operations).where(operations.c.run_id==template.cold_id,
                        operations.c.tool_ref.in_(list(runtime.codec.MODEL_KINDS)))).mappings()]
                assert len(rows)==1 and rows[0]['status']=='VERIFIED'
                assert len(model_ops)==1 and model_ops[0]['status']=='VERIFIED'
                assert observed and exports and all(not graph.active for graph,_ in observed)
                report=dict(classification='CONFIGURED_VIRTUAL_BUSINESS_CLOCK_ONE_COLD_SQLITE_W5_G1_COMMIT_NOT_ORIGINAL30',
                    default_graph_version_layer=True,all_original_G1_executed=True,
                    version_scopes=[dict(phase=g.phase,initial_sequence=v.sequence) for g,v in observed],
                    postproof_exports=exports,one_cold_attempt='VERIFIED',operation='VERIFIED',
                    two_cold_goal_completed=False,new_real_models=0,fixed_mock_exchanges=cap.exchanges,
                    source_fixture_qualification='Existing three configured synthetic substitutes, not formal account/PG',
                    budgets_raised=False)
                (tmp_path/'graph-version-vertical-result.json').write_text(json.dumps(report,indent=2)+'\n')
            finally:close_case(case,clock)
    finally:
        monitor.set_local_events(slot,ctor,0)
        monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
    assert hashlib.sha256(template.path.read_bytes()).hexdigest()==template.sha256
    assert not any(t.is_alive() for t in threading.enumerate() if t not in threads_before)
