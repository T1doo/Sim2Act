"""Actual three-operation SQL/node readers, synthetic response data; no model IO."""
import copy
import hashlib
import json
import sys

import pytest
from sqlalchemy import insert, select, update
from test_cold_accounted_native import native_segment
from test_cold_accounted_receipts import seed_receipts, setup
from test_cold_accounted_sqlite import sql_facts, forbid_execution

from sim2act import natural_spec_runtime as rt, pa_spec_apps as spec
from sim2act.contracts import AppManifest
from sim2act.db import attempts, fingerprint, new_id, operation_intents, operations, reservations, runs
from sim2act.errors import DomainError
from sim2act.goal_applications import response_archive


def seed_second(f):
    r=seed_receipts(f)
    b=f.cold_bound;plan=b['plan'];steps=plan['definition']['manifest']['workflow'];actions=plan['definition']['actions']
    first_model=r.pending;second_model=new_id('op')
    limits=AppManifest.model_validate(plan['definition']['manifest']).runtime_limits
    raw=dict(model='intern-s2',choices=[dict(message=dict(role='assistant',content=json.dumps(dict(items=[]))),finish_reason='stop')],
        usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2))
    value,usage=rt.parse(raw,b['source'],actions[1]['executor']['ref'],limits,100000)
    with f.store.tx() as c:
        first_intent=c.execute(select(operation_intents.c.request).where(operation_intents.c.operation_id==first_model)).scalar_one()
        first_receipt=spec.receipt_for(first_model,steps[1],actions[1],plan,first_intent,value)
        outputs={steps[0]['step_id']:copy.deepcopy(b['source']),steps[1]['step_id']:value}
        second_intent=spec.intent_for(steps[2],actions[2],plan,outputs,[r.proof,first_receipt])
        c.execute(update(operations).where(operations.c.id==first_model).values(status='VERIFIED',receipt=first_receipt))
        c.execute(insert(operations).values(id=second_model,run_id=f.cold_job['id'],call_id=steps[2]['step_id'],
            tool_ref=actions[2]['executor']['ref'],fingerprint=fingerprint(second_intent),status='DISPATCHED'))
        c.execute(insert(operation_intents).values(operation_id=second_model,request=second_intent))
        f.store.event(c,f.cold_job['id'],'SPEC_STEP_VERIFIED',dict(step_id=steps[1]['step_id'],operation_id=first_model,fence=1))
        total=0
        for ordinal,(oid,intent) in enumerate(((first_model,first_intent),(second_model,second_intent))):
            index=ordinal+1;aid=new_id('attempt');at=float(f.cold_job['created_at'])+.001*index
            meta=dict(operation_id=oid,step_id=steps[index]['step_id'],ordinal=ordinal,fence=1,run_version=1,
                created_at=f.cold_job['created_at'],deadline=f.cold_job['created_at']+limits.run_seconds,
                plan_fingerprint=plan['plan_fingerprint'],intent=intent,limits=limits.model_dump())
            messages=rt.messages(b,steps[index],actions[index],intent)
            wire=rt.body(messages,[],limits.max_output_tokens)
            reserved=len(wire)+limits.max_output_tokens;total+=reserved
            parameters=dict(pa_trial_binding=dict(version=f.binding.version),natural_spec=meta,request_fingerprint=fingerprint(dict(messages=messages,tools=[],model='intern-s2')),
                natural_spec_wire=dict(sha256=hashlib.sha256(wire).hexdigest(),bytes=len(wire),characters=len(wire.decode())))
            received_raw,evidence=response_archive(raw);response=dict(received_raw=received_raw,raw_evidence=evidence)
            c.execute(insert(attempts).values(id=aid,run_id=f.cold_job['id'],created_at=at,mode='LIVE',request_model='intern-s2',
                response_model='intern-s2',status='VERIFIED' if ordinal==0 else 'RECEIVED',parameters=parameters,
                reserved_tokens=reserved,response=response,usage=usage))
            slot=dict(id=aid,subject='synthetic',created_at=at,run_id=f.cold_job['id'])
            c.execute(insert(reservations).values(**slot))
            f.store.event(c,f.cold_job['id'],'MODEL_RESERVED',dict(attempt_id=aid,mode='live'))
            f.store.event(c,f.cold_job['id'],'NS_RESERVED',dict(attempt_id=aid,parameters_fingerprint=fingerprint(parameters),
                reserved_tokens=reserved,request_model='intern-s2',mode='LIVE',created_at=at,
                operation_id=oid,step_id=steps[index]['step_id'],fence=1,reservation_fingerprint=fingerprint(slot)))
            row=dict(c.execute(select(attempts).where(attempts.c.id==aid)).mappings().one())
            f.store.event(c,f.cold_job['id'],'NS_RECEIVED',dict(attempt_id=aid,response_fingerprint=fingerprint(response),
                reception_fingerprint=fingerprint(dict(row,status='RECEIVED'))))
            if ordinal==0:
                f.store.event(c,f.cold_job['id'],'NS_SETTLED',dict(attempt_id=aid,attempt_fingerprint=fingerprint(row),operation_id=oid))
                r.verified_attempt=aid
        context=dict(f.cold_job['context'],requests=2,reserved_tokens=total,messages=messages)
        f.cold_job['context']=context
        c.execute(update(runs).where(runs.c.id==f.cold_job['id']).values(context=context))
    r.pending=second_model;r.meta=dict(operation_id=second_model,ordinal=1,step_id=steps[2]['step_id'])
    return r


@pytest.mark.parametrize('bounded',[False,True])
@pytest.mark.parametrize('representation',['raw','owned'])
def test_original_three_operation_proof_and_exact_future_roots(sql_facts,bounded,representation):
    from sim2act._cold_accounted_native import _bounded_settlement_config
    f=sql_facts;r=seed_second(f)
    with f.store.tx() as c:
        expected=spec.receipts(f.store,c,f.cold_job,f.cold_bound,pending_id=r.pending)
    def prepare_binding(graph):
        if representation=='owned':
            from sim2act import _cold_source_packet as source
            f.cold_bound['draft']=source.own_fact(graph,'test-second-cold-draft',f.cold_bound['draft'])
            f.cold_bound['plan']=spec._bound_plan_from_facts(f.cold_bound['draft'],{'input':{}},f.cold_bound['source'])
    with f.store.tx() as c,native_segment(f,c,receipt_setup=setup(f,c,r),binding_setup=prepare_binding,
        config=_bounded_settlement_config() if bounded else None) as s:
        assert s.cohort.route=='OWNED',s.candidate.selection_record()
        closure=s.candidate.receipt;before=set(s.graph.inputs)
        pending=(' '+r.pending)[1:]
        assert pending==r.pending and pending is not r.pending
        result=spec._cold_receipts(f.store,c,f.cold_job,f.cold_bound,r.reader,pending_id=pending)
        assert result==expected and len(result[1])==2
        assert set(s.graph.inputs)-before==set(closure.names)
        assert closure.phase=='DONE' and r.reader._node_proofs==[closure.node_proof_key]
        assert r.reader._raw[closure.node_input_key] is closure.node_inputs


@pytest.mark.parametrize('damage',['forged-node','changed-attempt','stop','revoke',
    'closure-method','reader-method','method-code','frame-default','budget-pointer'])
def test_three_operation_cannot_skip_original_proof_or_dynamic_checks(sql_facts,damage):
    from sim2act.db import grants
    f=sql_facts;r=seed_second(f);reached=False;calls=[];restored=None
    def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('unknown callback executed')
    try:
        def with_foreign_budget(graph):
            graph.add('synthetic-foreign-admin',(1000000,1000000))
            return setup(f,graph.connection,r)(graph)
        with pytest.raises(DomainError),f.store.tx() as c,native_segment(f,c,receipt_setup=with_foreign_budget) as s:
            assert s.cohort.route=='OWNED'
            reached=True;closure=s.candidate.receipt
            if damage=='forged-node':
                closure.begin(f.store,c,f.cold_job,f.cold_bound,r.reader,r.pending,False)
                r.reader.pin_receipt_binding(f.cold_bound)
                r.reader._put(closure.node_input_key,{'forged':'not original producer'})
            elif damage=='changed-attempt':
                r.reader._raw['attempts'][0]['response']['received_raw']='changed'
            elif damage=='stop':f.worker.stop.set()
            elif damage=='revoke':c.execute(update(grants).values(revoked=True))
            elif damage=='closure-method':closure._node_added=forbidden
            elif damage=='reader-method':r.reader.node_proof=forbidden
            elif damage=='budget-pointer':
                closure.admin_name='synthetic-foreign-admin'
                closure.phase_limits=s.graph.inputs[closure.admin_name]
            elif damage=='frame-default':
                fn=type(closure)._node_added;restored=(fn,'__defaults__',fn.__defaults__)
                fn.__defaults__=(forbidden,)
            else:
                fn=type(closure)._node_added;restored=(fn,'__code__',fn.__code__)
                fn.__code__=(lambda *args,**kwargs:None).__code__
            spec._cold_receipts(f.store,c,f.cold_job,f.cold_bound,r.reader,pending_id=r.pending)
    finally:
        if restored:setattr(*restored)
    assert reached and not s.mode.active and not s.graph.active
    assert calls==[]


def test_receipt_phase_full_deepcopy_order_alias_and_scalar_identity():
    from sim2act._cold_accounted_receipts import _receipt_phase_same
    shared={'nested':[{'text':'synthetic'}]};outputs={'read':shared};proved=[{'data':shared}]
    def phase():return copy.deepcopy(dict(pending_id='pending',allow_pending=False,index=1,outputs=outputs,proved=proved))
    assert _receipt_phase_same(phase(),outputs,proved,'pending',100,200)
    for damage in ('extra','alias','original','order','index'):
        value=phase()
        if damage=='extra':value['unmetered']=['new']
        elif damage=='alias':value['proved'][0]['data']=copy.deepcopy(value['proved'][0]['data'])
        elif damage=='original':value['outputs']=outputs
        elif damage=='order':value['proved'][0]['data']={'nested':[]}
        else:value['index']=True
        assert not _receipt_phase_same(value,outputs,proved,'pending',100,200)
    assert not _receipt_phase_same(phase(),outputs,proved,'pending',1,200)
    assert not _receipt_phase_same(phase(),outputs,proved,'pending',100,1)


@pytest.mark.parametrize('damage',['meta','limits','action','correction','phase-extra','phase-original'])
def test_original_builder_return_cannot_expand_or_rebind_future_inputs(sql_facts,damage):
    f=sql_facts;r=seed_second(f);injected=[]
    monitor=sys.monitoring;slot=next(i for i in (3,5,4) if monitor.get_tool(i) is None)
    code=rt._node_proof_inputs.__code__
    def returned(actual,offset,value):
        if injected:return
        frame=sys._getframe(1);assert frame.f_code is code
        injected.append(True)
        if damage=='meta':value['meta']=dict(value['meta'])
        elif damage=='limits':value['node_limits']=dict(value['node_limits'])
        elif damage=='action':value['action']=dict(rt._source_owned_code.image.plain(value['action']))
        elif damage=='correction':value['human_correction']={'new':'unmetered field'}
        elif damage=='phase-extra':value['receipt_phase']['extra']=['new']
        else:
            receipt=frame.f_back.f_back.f_back
            assert receipt.f_code is spec._receipts.__code__
            value['receipt_phase']['outputs']=receipt.f_locals['outputs']
    monitor.use_tool_id(slot,'Original three-operation input publication mutation')
    try:
        monitor.register_callback(slot,monitor.events.PY_RETURN,returned)
        monitor.set_local_events(slot,code,monitor.events.PY_RETURN)
        with pytest.raises(DomainError),f.store.tx() as c,native_segment(f,c,receipt_setup=setup(f,c,r)) as s:
            assert s.cohort.route=='OWNED'
            spec._cold_receipts(f.store,c,f.cold_job,f.cold_bound,r.reader,pending_id=r.pending)
    finally:
        monitor.set_local_events(slot,code,0);monitor.register_callback(slot,monitor.events.PY_RETURN,None);monitor.free_tool_id(slot)
    assert injected and not s.graph.active and not s.mode.active


def test_unknown_model_metadata_declines_then_original_validation_rejects(sql_facts):
    f=sql_facts;r=seed_second(f)
    with f.store.tx() as c:
        c.execute(update(attempts).where(attempts.c.id==r.verified_attempt).values(
            parameters={'natural_spec':None}))
    with pytest.raises(DomainError),f.store.tx() as c,native_segment(f,c,receipt_setup=setup(f,c,r)) as s:
        assert s.cohort.route=='LEGACY'
        assert s.candidate.selection['reason']=='receipt_model_attempts'
        assert not s.candidate.mode.scope._issued
        spec._cold_receipts(f.store,c,f.cold_job,f.cold_bound,r.reader,pending_id=r.pending)
