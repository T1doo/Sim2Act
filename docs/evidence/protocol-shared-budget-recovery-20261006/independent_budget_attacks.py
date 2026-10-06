import copy
import pytest
from sqlalchemy import update,delete,select
from test_protocol_pool import env,claimed_source
from test_protocol_jobs import factory_for,wire
from sim2act.db import Store,attempts,protocol_jobs,fingerprint,runs
from sim2act.db import protocol_request_pools as pools,protocol_request_slots as slots
from sim2act.protocol_pool import initialize_pools,OFFLINE_POOL,require_pool,inspect_pool,_policy

def test_capacity_controller_policy_rewrite_accepted(tmp_path):
    store=Store('sqlite:///'+str(tmp_path/'capacity.db'),test_only=True);store.initialize();initialize_pools(store,0)
    with store.tx() as c:c.execute(update(pools).where(pools.c.id==OFFLINE_POOL).values(request_limit=14,policy_fingerprint=fingerprint(_policy('offline',14))))
    require_pool(store,OFFLINE_POOL)
    assert inspect_pool(store,OFFLINE_POOL)['request_limit']==14
    print('CAPACITY_0_TO_14_ACCEPTED')
    store.engine.dispose()

@pytest.mark.parametrize('change',['delete_slot_count','fence_phase','reserved_tokens','token_limit'])
def test_pool_anchor_rewrite_accepted(env,change):
    store,user,pid,a,b,worker,tmp=env
    _,run,snapshot=claimed_source(env)
    observed=factory_for(env,[wire({'synthetic':'known'})],'source_a');runner=worker.protocol_runner_factory(worker,run,snapshot)
    runner.call([{'role':'user','content':'synthetic accounting probe'}],[])
    with store.tx() as c:
        if change=='delete_slot_count':
            c.execute(delete(slots));c.execute(update(pools).where(pools.c.id==OFFLINE_POOL).values(reserved_requests=0,reserved_tokens=0,known_tokens=0))
        elif change=='fence_phase':c.execute(update(slots).values(fence=999,phase='unrelated'))
        elif change=='reserved_tokens':
            c.execute(update(slots).values(reserved_tokens=1));c.execute(update(pools).where(pools.c.id==OFFLINE_POOL).values(reserved_tokens=1))
        else:c.execute(update(pools).where(pools.c.id==OFFLINE_POOL).values(token_limit=999999))
    require_pool(store,OFFLINE_POOL)
    print('POOL_REWRITE_ACCEPTED',change)
    if change=='delete_slot_count':
        with store.tx() as c:c.execute(update(runs).where(runs.c.id==run['id']).values(status='PAUSED',lease_until=0))
        _,other,other_snapshot=claimed_source(env,'fresh-after-reset')
        observed2=factory_for(env,[wire({'synthetic':'refilled'})],'source_a');runner2=worker.protocol_runner_factory(worker,other,other_snapshot)
        runner2.call([{'role':'user','content':'after covert budget reset'}],[])
        assert len(observed2)==1
        with store.engine.connect() as c:assert len(c.execute(select(attempts)).all())==2
        print('COHERENT_DELETE_AND_COUNT_RESET_NEW_SEND',len(observed2))

def test_actual_global_token_overrun_not_halted(env):
    store,user,pid,a,b,worker,tmp=env
    _,run,snapshot=claimed_source(env)
    raw=wire({'synthetic':'known oversized usage'});raw['usage']={'prompt_tokens':99990,'completion_tokens':10,'total_tokens':100000}
    factory_for(env,[raw],'source_a');runner=worker.protocol_runner_factory(worker,run,snapshot)
    from sim2act.errors import DomainError
    with pytest.raises(DomainError):runner.call([{'role':'user','content':'synthetic overuse probe'}],[])
    require_pool(store,OFFLINE_POOL)
    summary=inspect_pool(store,OFFLINE_POOL)
    print('ACTUAL_GLOBAL_TOKEN_OVERRUN',summary['known_tokens'],'halted',summary['halted'])
    assert summary['known_tokens']==100000 and summary['halted'] is False

def test_actual_overrun_halt_flag_reset_new_send(env):
    store,user,pid,a,b,worker,tmp=env
    _,run,snapshot=claimed_source(env)
    raw=wire({'synthetic':'known oversized usage'});raw['usage']={'prompt_tokens':99990,'completion_tokens':10,'total_tokens':100000}
    factory_for(env,[raw],'source_a');runner=worker.protocol_runner_factory(worker,run,snapshot)
    from sim2act.errors import DomainError
    with pytest.raises(DomainError):runner.call([{'role':'user','content':'synthetic overuse probe'}],[])
    assert inspect_pool(store,OFFLINE_POOL)['halted'] is True
    with store.tx() as c:
        c.execute(update(pools).where(pools.c.id==OFFLINE_POOL).values(halted=False,halt_reason=None))
        c.execute(update(runs).where(runs.c.id==run['id']).values(status='PAUSED',lease_until=0))
    require_pool(store,OFFLINE_POOL)
    _,other,other_snapshot=claimed_source(env,'new-after-halt-reset')
    observed=factory_for(env,[wire({'synthetic':'new after overrun halt reset'})],'source_a')
    worker.protocol_runner_factory(worker,other,other_snapshot).call([{'role':'user','content':'must be blocked by actual usage'}],[])
    assert len(observed)==1
    print('ACTUAL_OVERUSE_HALT_RESET_NEW_SEND',len(observed))

def test_stripped_namespace_markers_generic_claim_requeues(env):
    from sim2act.db import events
    from sim2act.protocol_jobs import is_protocol_job
    store,user,pid,a,b,worker,tmp=env
    _,run,_=claimed_source(env)
    with store.tx() as c:
        c.execute(delete(protocol_jobs).where(protocol_jobs.c.run_id==run['id']))
        c.execute(delete(events).where(events.c.run_id==run['id'],events.c.kind=='PROTOCOL_ACCEPTED'))
        context=copy.deepcopy(run['context']);context.pop('kind')
        c.execute(update(runs).where(runs.c.id==run['id']).values(context=context,lease_until=0))
    assert is_protocol_job(store,run['id']) is True
    reopened=store.claim(worker.id,30)
    print('STRIPPED_NAMESPACE_CLAIM',None if reopened is None else reopened['status'])
    assert reopened is not None and reopened['id']==run['id'] and reopened['status']=='RUNNING'

def test_malformed_usage_raises_non_domain_without_persisting_halt(env):
    store,user,pid,a,b,worker,tmp=env
    _,run,snapshot=claimed_source(env)
    factory_for(env,[wire({'synthetic':'known'})],'source_a')
    worker.protocol_runner_factory(worker,run,snapshot).call([{'role':'user','content':'shape probe'}],[])
    with store.tx() as c:c.execute(update(slots).values(usage={'status':'known','tokens':None}))
    with pytest.raises(TypeError):require_pool(store,OFFLINE_POOL)
    with store.engine.connect() as c:assert c.execute(select(pools.c.halted).where(pools.c.id==OFFLINE_POOL)).scalar_one() is False
    print('MALFORMED_USAGE_TYPEERROR_NO_DURABLE_HALT')

def test_pg_reservation_sent_body_late_mutation(env,monkeypatch):
    store,user,pid,a,b,worker,tmp=env
    _,run,snapshot=claimed_source(env)
    observed=factory_for(env,[wire({'synthetic':'known'})],'source_a')
    runner=worker.protocol_runner_factory(worker,run,snapshot)
    messages=[{'role':'user','content':'small'}]
    original=store.event
    def event(c,rid,kind,data=None):
        value=original(c,rid,kind,data)
        if kind=='MODEL_RESERVED':messages[0]['content']='x'*6000
        return value
    monkeypatch.setattr(store,'event',event)
    runner.call(messages,[])
    with store.tx() as c:
        recorded=c.execute(select(attempts).where(attempts.c.run_id==run['id'])).mappings().one()
        actualfp=fingerprint({'messages':observed[0]['messages'],'tools':observed[0]['tools'],'model':observed[0]['model']})
        assert recorded['parameters']['request_fingerprint']!=actualfp
        assert recorded['reserved_tokens']<len(observed[0]['messages'][0]['content'])
        print('PG_FP_SENT_WIRE_MISMATCH_RESERVED',recorded['reserved_tokens'],'ACTUAL_MESSAGE_BYTES',len(observed[0]['messages'][0]['content']))
    require_pool(store,OFFLINE_POOL)
