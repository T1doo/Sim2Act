"""One original large flow with passive, scoped CPython function timing.

No callee, input, SQL or business clock is replaced by the profiler. Times
include instrumentation, and nested inclusive values must not be added.
"""

import json
import sys
import threading
import time
from contextlib import contextmanager

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
        (structure._qualified,'structure.qualify')]
    codes={fn.__code__:name for fn,name in targets}
    stacks,records={},{}
    def start(code,offset):
        if not opened:return
        control=opened[0]._local_model_control
        epoch=getattr(control.local,'epoch',None) if control is not None else None
        if epoch is None:return
        stacks.setdefault(threading.get_ident(),[]).append([code,epoch.phase,time.monotonic(),0.])
    def end(code,offset,value=None):
        frames=stacks.get(threading.get_ident(),[])
        if not frames or frames[-1][0] is not code:return
        _,phase,started,child=frames.pop();elapsed=time.monotonic()-started
        entry=records.setdefault(phase,{}).setdefault(codes[code],dict(calls=0,inclusive_seconds=0.,exclusive_among_targets_seconds=0.))
        entry['calls']+=1;entry['inclusive_seconds']+=elapsed;entry['exclusive_among_targets_seconds']+=elapsed-child
        if frames:frames[-1][3]+=elapsed
    monitor.use_tool_id(slot,'Sim2Act scoped Cold passive timing')
    try:
        monitor.register_callback(slot,monitor.events.PY_START,start)
        monitor.register_callback(slot,monitor.events.PY_RETURN,end)
        monitor.register_callback(slot,monitor.events.PY_UNWIND,end)
        for code in codes:monitor.set_local_events(slot,code,monitor.events.PY_START|monitor.events.PY_RETURN)
        monitor.set_events(slot,monitor.events.PY_UNWIND)
        yield records
    finally:
        monitor.set_events(slot,0)
        for code in codes:monitor.set_local_events(slot,code,0)
        for kind in (monitor.events.PY_START,monitor.events.PY_RETURN,monitor.events.PY_UNWIND):
            monitor.register_callback(slot,kind,None)
        monitor.free_tool_id(slot)
        (tmp_path/'passive-profile.json').write_text(json.dumps(dict(
            classification='PASSIVELY_INSTRUMENTED_ORIGINAL_LARGE_COLD_FIXED_MOCK_SQLITE_WAL',
            records=records,pending_frames=sum(map(len,stacks.values())),
            limitations='Instrumentation included; exclusive subtracts only observed target children; inclusive overlaps.'),indent=2)+'\n')


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
