"""Independent finite synthetic-negative checks. No provider, socket or repo writes."""
import copy,json,os,time
from pathlib import Path

import pytest
from conftest import env
from sqlalchemy import delete,event,insert,select,update
from sql_private_barrier import PrivateReadBarrier
from test_text_continuations import rows
from test_text_continuation_boundaries import RunCellObserver
from test_text_workflows import claimed,draft,enqueue,inspect,instance,material,once

from sim2act import text_workflows as flow
from sim2act.db import attempts,delivery_graph_requests,events,fingerprint,grants,internal_instance_data,internal_run_bindings,new_id,run_contracts,runs
from sim2act.errors import DomainError


def proof(env,rid):
    return env[2].get('/api/internal/app-run-jobs/'+rid+'/text-workflow-proof')


def record(name,**data):
    out=Path(os.environ['INDEPENDENT_TEXT_WORKFLOW_DIR']);out.mkdir(parents=True,exist_ok=True)
    (out/(name+'.json')).write_text(json.dumps({'classification':'INDEPENDENT_SYNTHETIC_FAULT_NOT_REAL_ATTACK',**data},indent=2)+'\n')


def completed(env):
    made,body=draft(env);release,inst=instance(env,made['id']);rid=enqueue(env,release,inst);once(env)
    assert inspect(env,inst,rid).status_code==200
    return made,body,release,inst,rid


def test_model_attempt_pollution_cannot_claim_zero_requests(env):
    made,body,release,inst,rid=completed(env)
    with env[0].tx() as c:
        assert c.execute(select(attempts.c.id).where(attempts.c.run_id==rid)).first() is None
        c.execute(insert(attempts).values(id=new_id('attempt'),run_id=rid,created_at=time.time(),mode='mock',
            request_model='synthetic-model-not-called',response_model='synthetic-model-not-called',status='SUCCEEDED',
            usage={'total_tokens':1},reserved_tokens=1,parameters={'synthetic':'persisted corruption only'},
            response={'synthetic':'No API/provider was called'},error=None,elapsed=0))
    before=rows(env[0]);reply=proof(env,rid);after=rows(env[0])
    record('attempt-pollution',status=reply.status_code,response=reply.json(),database_unchanged=after==before,
           actual_injected_attempts=1,no_model_called=True)
    assert reply.status_code in {400,409} and after==before,reply.text


def test_lost_independent_markers_and_broken_binding_do_not_read_revoked_run(env):
    made,body,release,inst,rid=completed(env)
    with env[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id==rid,
                  delivery_graph_requests.c.kind.in_([flow.RUN_META,flow.RUN_META+'_seal'])))
        c.execute(delete(events).where(events.c.run_id==rid,events.c.kind=='ACCEPTED'))
        c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id==rid).values(app_run_id='synthetic-missing-AppRun'))
        c.execute(update(grants).where(grants.c.principal_id==env[3],grants.c.resource_id==body['resource_id'],
                  grants.c.tool_ref=='resource.read').values(revoked=True))
    before=rows(env[0]);observer=RunCellObserver(env[0],rid)
    with observer:
        reply=inspect(env,inst,rid);cells=list(observer.blocked);sql=list(observer.statements)
    after=rows(env[0]);record('stripped-run-scope',status=reply.status_code,response=reply.json(),
                            protected_cell_evaluations=cells,sql=sql,database_unchanged=after==before)
    assert reply.status_code in {400,403,409},reply.text
    assert not cells and after==before,cells


def test_original_create_key_recovery_revoked_target_reads_no_source_bytes(env):
    made,body,release,inst,rid=completed(env)
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id==env[3],grants.c.resource_id==body['resource_id'],
                  grants.c.tool_ref=='resource.read').values(revoked=True))
    before=rows(env[0]);barrier=PrivateReadBarrier(env[0],{rid},{body['resource_id']})
    with barrier:
        reply=env[2].get(f"/api/projects/{env[5]}/text-workflow-requests/{body['request_key']}")
        cells=list(barrier.blocked);sql=list(barrier.statements)
    after=rows(env[0]);record('revoked-key-recovery',status=reply.status_code,response=reply.json(),
                            protected_cell_evaluations=cells,sql=sql,database_unchanged=after==before)
    assert reply.status_code==403 and not cells and after==before,reply.text


def test_expiry_after_typed_insert_rolls_back_complete_terminal_append(env,monkeypatch):
    made,body=draft(env);release,inst=instance(env,made['id']);rid=enqueue(env,release,inst)
    worker,run=claimed(env,rid)
    for _ in range(4):assert flow.advance(worker,run)
    worker.store.heartbeat(worker.id,rid,run['fence'],lease_seconds=120)
    with env[0].tx() as c:
        assert c.execute(select(runs.c.lease_until).where(runs.c.id==rid)).scalar_one()>run['created_at']+60.001
    before=rows(env[0]);assert len([o for o in before['operations'] if o['run_id']==rid])==4
    state={'expired':False,'hits':0};original=time.time
    def clock():return run['created_at']+60.001 if state['expired'] else original()
    def expire_after_insert(conn,cursor,statement,parameters,context,many):
        if statement.lstrip().startswith('INSERT INTO internal_instance_data'):
            state['hits']+=1;state['expired']=True
    monkeypatch.setattr(time,'time',clock)
    event.listen(env[0].engine,'after_cursor_execute',expire_after_insert)
    try:
        with pytest.raises(DomainError) as caught:flow.advance(worker,run)
    finally:event.remove(env[0].engine,'after_cursor_execute',expire_after_insert)
    after=rows(env[0]);record('terminal-expiry-corrected',code=caught.value.code,typed_insert_hook_hits=state['hits'],
                            database_unchanged=after==before,kept_operation_ids=[o['id'] for o in after['operations'] if o['run_id']==rid])
    assert caught.value.code=='BUDGET_EXHAUSTED' and state['hits']==1 and after==before


def test_second_extraction_hop_rejected_after_real_four_receipts(env):
    made,body,release,inst,rid=completed(env)
    target,card=material(env,'Cedar first target\nQuartz next target\n','md')
    derived,_=draft(env,target,card,rid,'independent-hop-one')
    tr,ti=instance(env,derived['id'],dict(term_a='Cedar',term_b='Quartz',emit_report=True))
    r2=enqueue(env,tr,ti,dict(term_a='Cedar',term_b='Quartz',emit_report=True),'independent-derived-run');once(env)
    actual=proof(env,r2);assert actual.status_code==200 and actual.json()['extraction_depth']==1
    third,thirdcard=material(env,'Jade third target\nOnyx next target\n','txt')
    before=rows(env[0]);reply=env[2].get(f"/api/projects/{env[5]}/text-workflow-options",params=dict(card_id=thirdcard['id'],source_run_id=r2))
    after=rows(env[0]);record('second-hop',status=reply.status_code,response=reply.json(),database_unchanged=after==before,
                           derived_source_status=actual.status_code,derived_receipts=len(actual.json()['steps']))
    assert reply.status_code==409 and after==before,reply.text


def test_resigned_frozen_goal_constraints_cannot_replace_accepted_native_goal(env):
    made,body=draft(env);release,inst=instance(env,made['id']);rid=enqueue(env,release,inst)
    with env[0].tx() as c:
        frozen=copy.deepcopy(c.execute(select(run_contracts.c.snapshot).where(run_contracts.c.run_id==rid)).scalar_one())
        frozen['goal']['constraints']=['synthetic constraint replacement']
        c.execute(update(run_contracts).where(run_contracts.c.run_id==rid).values(snapshot=frozen,fingerprint=fingerprint(frozen)))
    before=rows(env[0]);reply=inspect(env,inst,rid);after=rows(env[0])
    record('resigned-goal-contract',status=reply.status_code,response=reply.json(),database_unchanged=after==before,
           replacement_uses_valid_hash=True,original_goal_binding_untouched=True)
    assert reply.status_code==409 and after==before,reply.text

"""Synthetic valid-width Python equality counterexample, no source/seal rewrite."""
import copy,json
from pathlib import Path
from conftest import env
from sqlalchemy import select,update
from test_text_continuations import rows
from test_text_workflows import draft,instance,enqueue,once,inspect
from sim2act.db import internal_run_bindings,internal_app_runs

def test_app_run_boolean_input_cannot_be_integer_width_equal(env):
    made,_=draft(env);release,inst=instance(env,made['id']);rid=enqueue(env,release,inst);once(env)
    with env[0].tx() as c:
        aid=c.execute(select(internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id==rid)).scalar_one()
        value=copy.deepcopy(c.execute(select(internal_app_runs.c.input).where(internal_app_runs.c.id==aid)).scalar_one())
        assert value['emit_report'] is True
        value['emit_report']=1
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id==aid).values(input=value))
    before=rows(env[0]);reply=inspect(env,inst,rid)
    source=env[2].get(f'/api/internal/app-run-jobs/{rid}/text-workflow-proof');after=rows(env[0])
    proof={'classification':'SYNTHETIC_PERSISTED_INPUT_WIDTH_FAULT_NOT_REAL_ATTACK','status':reply.status_code,
           'response':reply.json(),'source_status':source.status_code,'source_response':source.json(),
           'database_unchanged':after==before,'original_binding_and_fingerprints_untouched':True}
    Path('/tmp/pb-text-multistep-independent-r10-20261012/input-width.json').write_text(json.dumps(proof,indent=2)+'\n')
    assert reply.status_code in {400,409} and source.status_code in {400,409} and after==before,proof
