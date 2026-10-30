"""Real archived synthetic SQL facts and all original post resolver/join gates.

No Worker/model/transport execution; this is not the full large Cold flow.
"""
import json
from pathlib import Path
import pickletools
import time
import pytest
from accounted_sqlite_fixture import segment
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_accounted_sqlite import forbid_execution as forbid_execution, resolve
from sim2act import _cold_archive_packet as packet, pa_trial_dispatch as dispatch
from sim2act.natural_spec_runtime import _cold_graph_bytes
from sim2act.errors import DomainError


def shown(value, memo=None):
    # Test-only display reconstruction, preserving packet aliases and the exact
    # SAME original immutable leaves for a fair representation comparison.
    if memo is None:memo={}
    if type(value) is not packet._View:return value
    key=(id(tuple.__getitem__(value,0)),tuple.__getitem__(value,2))
    if key in memo:return memo[key]
    if value._body()[0]=='dict':
        result={};memo[key]=result
        result.update((k,shown(value[k],memo)) for k in value)
    elif value._body()[0]=='list':
        result=[];memo[key]=result
        result.extend(shown(v,memo) for v in value)
    else:
        result=tuple(shown(v,memo) for v in value);memo[key]=result
    return result


def test_actual_post_producer_complete_consumers_and_legacy_equivalence(sql_facts,tmp_path):
    f=sql_facts
    with f.store.tx() as c, segment(f,c) as pre:
        old=resolve(pre)
    with f.store.tx() as c, segment(f,c,phase='post') as post:
        new=resolve(post)
        assert packet.is_packet(new) and post.graph.inputs[packet.KEY] is new
        receipt,requests,responses=packet.bound(post.graph,new)
        assert shown(receipt)==old.public_receipt
        assert shown(requests)==old.request_bodies and shown(responses)==old.response_bodies
        dispatch._graph_pb_archive_chain(post.graph,f.store,c,f.binding,post.state,new,post.source)
        assert packet.read(new)[0]['source_run_id']==f.source_id
        # All legacy source raw/model facts still receive the original checks.
        post.graph.check(f.store,c)
        values=post.graph.input_bytes(_snapshot_values=True)
        old_values=dict(values,inputs=dict(values['inputs']))
        old_values['inputs'].pop(packet.KEY)
        same_receipt,same_requests,same_responses=shown(packet.bound(post.graph,new))
        old_values['inputs']['diagnostic:trial-output']=dict(archive=dict(
            public_receipt=same_receipt, request_bodies=same_requests,response_bodies=same_responses))
        new_values=dict(values,inputs=dict(values['inputs']))
        new_values['inputs']['diagnostic:trial-output']=dict(archive=new)
        def measure(v):
            wire=_cold_graph_bytes(v)
            prefix=b'SIM2ACT_COLD_GRAPH_PICKLE_V2\x00'
            assert wire.startswith(prefix)
            names=[op.name for op,arg,pos in pickletools.genops(wire[len(prefix):])]
            return dict(encoded_bytes=len(wire),dict_nodes=names.count('EMPTY_DICT'),
                list_nodes=names.count('EMPTY_LIST'),tuple_opcodes=sum(n.startswith('TUPLE') for n in names))
        (tmp_path/'archive-representation.json').write_text(json.dumps(dict(
            classification='REAL_SQL_SYNTHETIC_RESOLVER_COMPLETE_JOIN_DETACHED_REPRESENTATION_NOT_WORKER_FLOW',
            old=measure(old_values),new=measure(new_values),metadata_bytes=len(new[1]),
            leaf_count=len(new[2]),real_model_calls=0,worker_executions=0),indent=2)+'\n')


@pytest.mark.parametrize('change',['decoder','join','view'])
def test_real_post_consumer_rejects_changed_code_before_join(sql_facts,monkeypatch,change):
    f=sql_facts
    with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='post') as post:
        new=resolve(post)
        if change=='decoder':monkeypatch.setattr(packet,'read',lambda p:('forged',))
        if change=='join':monkeypatch.setattr(dispatch,'_archive_chain_values',lambda *a,**k:None)
        if change=='view':monkeypatch.setattr(packet._View,'__getitem__',lambda self,k:'forged')
        dispatch._graph_pb_archive_chain(post.graph,f.store,c,f.binding,post.state,new,post.source)


@pytest.mark.parametrize('change',['unmigrated-alias','stop','transaction'])
def test_owned_archive_does_not_exempt_other_data_or_lifecycle(sql_facts,change):
    f=sql_facts
    # This SQL-only fixture never runs Worker/settlement(); provide the same
    # finite original interval the real settlement establishes before G0.
    f.worker._settlement_interval=(time.monotonic()+120,time.time()+120)
    with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='post') as post:
        new=resolve(post)
        if change=='unmigrated-alias':post.source[1][0]['usage']['tokens']['total_tokens']+=1
        if change=='stop':f.worker.stop.set()
        if change=='transaction':c.rollback()
        dispatch._graph_pb_archive_chain(post.graph,f.store,c,f.binding,post.state,new,post.source)


def test_callback_cannot_change_view_semantics_after_entry_guard(sql_facts,monkeypatch):
    import sys
    from sim2act import natural_live_admission as gate
    f=sql_facts;events=[];changed=[];original=gate._graph_trial_pin
    with pytest.raises(DomainError),f.store.tx() as c,segment(f,c,phase='post') as post:
        new=resolve(post)
        def callback(*args,**kwargs):
            original(*args,**kwargs)
            frame=sys._getframe(1)
            while frame is not None:
                if frame.f_code.co_name=='owned_continuation':
                    changed.append(True)
                    monkeypatch.setattr(packet._View,'__getitem__',lambda *a:events.append('bad-view'))
                    break
                frame=frame.f_back
        monkeypatch.setattr(gate,'_graph_trial_pin',callback)
        dispatch._graph_pb_archive_chain(post.graph,f.store,c,f.binding,post.state,new,post.source)
    assert changed and events==[]
