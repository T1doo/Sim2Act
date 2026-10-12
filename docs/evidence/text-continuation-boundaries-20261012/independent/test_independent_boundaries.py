"""Small independent synthetic-corruption checks; these are not real attacks.

Only approved fixture clones are mutated. Never resign accepted old objects.
SQL barriers deny SQLite cell evaluation; whole-table snapshots compare writes.
"""
import json, os
from pathlib import Path

from sqlalchemy import delete, select, update
from sqlalchemy.exc import DatabaseError
from sql_private_barrier import PrivateReadBarrier
from test_text_continuations import legacy, legacy_failure, path, prepared, rows
from sim2act.db import internal_app_runs, internal_run_bindings, new_id, operations, runs


def prepare_command(data):
    _, _, client, info=data
    reply=client.get('/api/projects/'+info['project']+'/software-continuation-options')
    assert reply.status_code==200,reply.text
    chosen=next(x for x in reply.json()['items'] if x['id']==info['instance']['id'])
    body=dict(expected_revision=chosen['revision'],expected_release_fingerprint=chosen['release_fingerprint'],
              expected_candidate_fingerprint=chosen['fingerprint'],expected_source_implementation=chosen['source_implementation'],
              input={'term':'Alpha'},request_key='independent-boundary-preflight')
    return path(info).replace('software-continuations','software-continuation-preflights'),body


def save(info,case,**evidence):
    folder=Path(os.environ['INDEPENDENT_BOUNDARY_DIR']);folder.mkdir(parents=True,exist_ok=True)
    name=('a747' if info.get('goal') else '233')+'-'+case
    (folder/(name+'.json')).write_text(json.dumps(dict(classification='SYNTHETIC_PERSISTED_CORRUPTION_NOT_REAL_ATTACK',**evidence),indent=2)+'\n')


def test_foreign_link_real_denying_cell_barrier(legacy):
    store,_,client,info=legacy
    url,body=prepare_command(legacy)
    with store.tx() as c:
        foreign=dict(c.execute(select(runs).where(runs.c.id==info['successful_old_run_id'])).mappings().one())
        fid=new_id('independent_foreign')
        foreign.update(id=fid,request_key='independent-foreign-run',principal_id=new_id('foreignuser'),
                       project_id=new_id('foreignproject'),runtime_id=new_id('foreignruntime'),
                       context={'private':'foreign context sentinel'},result={'private':'foreign result sentinel'})
        c.execute(runs.insert().values(**foreign))
        c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id==info['successful_old_run_id']).values(run_id=fid))
    before=rows(store)
    barrier=PrivateReadBarrier(store,{fid});barrier.rules={'runs':barrier.rules['runs']}
    with barrier:
        try:
            with store.tx() as c:
                c.execute(select(runs.c.context).where(runs.c.id==fid)).first()
        except DatabaseError:
            pass
        else:
            raise AssertionError('Independent protected-cell calibration did not reject')
        calibration=list(barrier.blocked);assert calibration
        barrier.blocked.clear();barrier.evaluated.clear();barrier.statements.clear()
        reply=client.post(url,json=body)
        cells=list(barrier.blocked);statements=list(barrier.statements)
    after=rows(store)
    save(info,'foreign-deny-barrier',calibration=calibration,protected_cell_evaluations=cells,sql=statements,
         status=reply.status_code,response=reply.json(),database_unchanged=after==before)
    assert reply.status_code==409,reply.text
    assert after==before and not cells
    scoped=[s for s in statements if 'FROM runs' in s['sql'] and 'runs.context' in s['sql']]
    assert scoped and all(all('runs.'+field+' = ' in s['sql'] for field in ['principal_id','project_id','runtime_id']) for s in scoped)


def test_app_run_principal_rejected_before_linked_run_cells(legacy):
    store,_,client,info=legacy
    _,_,body=prepared(legacy)
    with store.tx() as c:
        aid=c.execute(select(internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id==info['successful_old_run_id'])).scalar_one()
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id==aid).values(principal_id=new_id('foreignapprunowner')))
    before=rows(store)
    barrier=PrivateReadBarrier(store,{info['successful_old_run_id']});barrier.rules={'runs':barrier.rules['runs']}
    with barrier:
        reply=client.post(path(info),json=body)
        cells=list(barrier.blocked);statements=list(barrier.statements)
    after=rows(store)
    save(info,'app-run-owner',protected_cell_evaluations=cells,sql=statements,status=reply.status_code,
         response=reply.json(),database_unchanged=after==before)
    assert reply.status_code==409 and after==before and not cells,reply.text


def test_typed_result_without_selected_app_run_is_not_retained(legacy):
    store,_,client,info=legacy
    _,_,body=prepared(legacy)
    with store.tx() as c:
        aid=c.execute(select(internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id==info['successful_old_run_id'])).scalar_one()
        c.execute(delete(internal_run_bindings).where(internal_run_bindings.c.app_run_id==aid))
        c.execute(delete(internal_app_runs).where(internal_app_runs.c.id==aid))
    before=rows(store)
    reply=client.post(path(info),json=body)
    after=rows(store)
    save(info,'orphan-typed',status=reply.status_code,response=reply.json(),database_unchanged=after==before,
         typed_rows_preserved=after['internal_instance_data']==before['internal_instance_data'])
    assert reply.status_code==409 and after==before,reply.text


def test_failed_only_verified_operation_blocks_late_commit(legacy_failure):
    store,_,client,info=legacy_failure
    _,_,body=prepared(legacy_failure)
    with store.tx() as c:
        failed=info['failed_old_run_id']
        op=c.execute(select(operations.c.id).where(operations.c.run_id==failed,operations.c.call_id=='instance_result')).scalar_one()
        c.execute(update(operations).where(operations.c.id==op).values(status='VERIFIED'))
    before=rows(store)
    reply=client.post(path(info),json=body)
    after=rows(store)
    save(info,'failed-verified-only',status=reply.status_code,response=reply.json(),database_unchanged=after==before,
         failed_run=failed,typed_rows_preserved=after['internal_instance_data']==before['internal_instance_data'])
    assert reply.status_code in {400,409} and after==before,reply.text
