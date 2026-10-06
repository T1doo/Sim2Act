import pytest
from test_protocol_pool import env
import independent_budget_attacks as old
from sim2act.errors import DomainError
@pytest.mark.parametrize('field',['delete_slot_count','fence_phase','reserved_tokens','token_limit'])
def test_original_pool_attacks_now_rejected(env,field):
    with pytest.raises(DomainError):old.test_pool_anchor_rewrite_accepted(env,field)
def test_controller_genesis_capacity_rewrite_now_rejected(tmp_path):
    with pytest.raises(DomainError):old.test_capacity_controller_policy_rewrite_accepted(tmp_path)
def test_actual_overusage_now_stops_global_pool(env):
    with pytest.raises(DomainError):old.test_actual_global_token_overrun_not_halted(env)
def test_actual_overusage_halt_flag_reset_now_rejected(env):
    with pytest.raises(DomainError):old.test_actual_overrun_halt_flag_reset_new_send(env)

def test_stripped_namespace_never_generic_claims(env):
    import copy
    from sqlalchemy import delete,select,update
    from test_protocol_pool import claimed_source
    from sim2act.db import events,protocol_jobs,runs
    from sim2act.protocol_jobs import is_protocol_job
    store,user,pid,a,b,worker,tmp=env
    _,run,_=claimed_source(env)
    with store.tx() as c:
        c.execute(delete(protocol_jobs).where(protocol_jobs.c.run_id==run['id']))
        c.execute(delete(events).where(events.c.run_id==run['id'],events.c.kind=='PROTOCOL_ACCEPTED'))
        context=copy.deepcopy(run['context']);context.pop('kind')
        c.execute(update(runs).where(runs.c.id==run['id']).values(context=context,lease_until=0))
    assert is_protocol_job(store,run['id']) is True
    assert store.claim(worker.id,30) is None
    with store.tx() as c:
        row=c.execute(select(runs).where(runs.c.id==run['id'])).mappings().one()
        assert row['status']=='WAITING_RESOURCE' and row['fence']==run['fence']+1

def test_malformed_usage_is_domain_error_and_durable_stop(env):
    from sqlalchemy import select,update
    from test_protocol_pool import claimed_source
    from test_protocol_jobs import factory_for,wire
    from sim2act.db import protocol_request_slots as slots, protocol_request_pools as pools
    from sim2act.protocol_pool import OFFLINE_POOL,require_pool
    store,user,pid,a,b,worker,tmp=env
    _,run,snapshot=claimed_source(env)
    factory_for(env,[wire({'synthetic':'known'})],'source_a')
    worker.protocol_runner_factory(worker,run,snapshot).call([{'role':'user','content':'shape probe'}],[])
    with store.tx() as c:c.execute(update(slots).values(usage={'status':'known','tokens':None}))
    with pytest.raises(DomainError) as exc:require_pool(store,OFFLINE_POOL)
    assert exc.value.code=='OUTCOME_UNKNOWN'
    with store.engine.connect() as c:assert c.execute(select(pools.c.halted).where(pools.c.id==OFFLINE_POOL)).scalar_one() is True
