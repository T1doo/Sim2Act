"""SQLite/MOCK local atomic writes; ordinary statement callbacks, no private SQL."""
import copy
import json
import time

import pytest
from sqlalchemy import event, insert, select, update
from test_natural_spec_apps import enqueue, ready, setup, transport

from sim2act import pa_spec_apps as spec
from sim2act.db import attempts, goal_cards, grants, meta, operations, resources, runs
from sim2act.errors import DomainError
from sim2act.worker import Worker


def local_case(env, monkeypatch):
    data = setup(env)
    store, settings = data[:2]
    _, _, release, inst, _ = ready(data)
    rid = enqueue(data, release, inst)
    sent = []
    worker = Worker(store, settings, goal_planner_transport=transport(sent))
    run = store.claim(worker.id, settings.lease_seconds)
    assert run['id'] == rid
    assert settings.lease_seconds == 30 and settings.run_seconds == 300
    clock = [time.time()]
    monkeypatch.setattr(time, 'time', lambda: clock[0])
    return data, worker, run, sent, clock


def snapshot(store):
    with store.tx() as c:
        return {t.name: sorted((dict(r) for r in c.execute(select(t)).mappings()),
            key=lambda r: json.dumps(r, sort_keys=True, default=str))
            for t in meta.sorted_tables}


def boundary(statement):
    sql = statement.lstrip().upper()
    for key, prefix in (
        ('prepared', 'INSERT INTO OPERATIONS '),
        ('intent', 'INSERT INTO OPERATION_INTENTS '),
        ('verified', 'UPDATE OPERATIONS SET '),
        ('context', 'UPDATE RUNS SET '),
        ('app_status', 'UPDATE INTERNAL_APP_RUNS SET '),
        ('event', 'INSERT INTO EVENTS '),
    ):
        if sql.startswith(prefix):
            return key
    return None


@pytest.mark.parametrize('fault', ['prepared', 'intent', 'verified', 'context', 'app_status', 'event'])
def test_local_atomic_group_rolls_back_at_each_actual_write(env, monkeypatch, tmp_path, fault):
    data, worker, run, sent, _ = local_case(env, monkeypatch)
    store = data[0]
    before = snapshot(store)
    reached = []

    def reject(c, cursor, statement, parameters, context, executemany):
        if not reached and boundary(statement) == fault:
            reached.append(fault)
            raise DomainError('VERSION_CONFLICT', 'Synthetic local write boundary failure')

    event.listen(store.engine, 'after_cursor_execute', reject)
    try:
        with pytest.raises(DomainError):
            spec.advance(worker, run)
    finally:
        event.remove(store.engine, 'after_cursor_execute', reject)
    assert reached == [fault]
    assert sent == []
    assert snapshot(store) == before
    (tmp_path/'local-write-rollback.json').write_text(json.dumps(dict(
        fault=fault, actual_write_completed=True, all_tables_identical=True,
        original_lease_seconds=30, original_run_seconds=300, fault_injection=True,
        clock_frozen_after_claim=True, real_model_requests=0), indent=2)+'\n')


@pytest.mark.parametrize('fault', [
    'lease', 'fence', 'version', 'cancel', 'stop', 'worker', 'read_revoke',
    'save_revoke', 'goal', 'material', 'unknown', 'receipt', 'context', 'deadline',
])
def test_local_atomic_group_final_guard_rejects_current_changes(env, monkeypatch, tmp_path, fault):
    data, worker, run, sent, clock = local_case(env, monkeypatch)
    store = data[0]
    before = snapshot(store)
    reached = []

    def mutate(c, cursor, statement, parameters, context, executemany):
        if reached or boundary(statement) != 'event':
            return
        reached.append(fault)
        if fault in {'lease', 'fence', 'version', 'cancel', 'worker'}:
            change = {'lease': dict(lease_until=clock[0]-1),
                'fence': dict(fence=run['fence']+1),
                'version': dict(version=run['version']+1),
                'cancel': dict(cancel_intent=True),
                'worker': dict(worker_id='different-worker')}[fault]
            c.execute(update(runs).where(runs.c.id == run['id']).values(**change))
        elif fault == 'stop':
            worker.stop.set()
        elif fault == 'deadline':
            clock[0] = run['created_at'] + worker.s.run_seconds
        elif fault in {'read_revoke', 'save_revoke'}:
            rid, tool = ((data[5], 'resource.read') if fault == 'read_revoke'
                else (data[4], 'artifact.save_text'))
            c.execute(update(grants).where(grants.c.resource_id == rid,
                grants.c.tool_ref == tool).values(revoked=True))
        elif fault == 'goal':
            c.execute(update(goal_cards).where(goal_cards.c.id == data[6]['id']).values(version=2))
        elif fault == 'material':
            c.execute(update(resources).where(resources.c.id == data[5]).values(hash='0'*64))
        elif fault == 'unknown':
            original = copy.deepcopy(before['attempts'][0])
            original.update(id='attempt_'+'f'*32, run_id=run['id'], status='STARTED')
            c.execute(insert(attempts).values(**original))
        elif fault == 'receipt':
            c.execute(update(operations).where(operations.c.run_id == run['id']).values(receipt={}))
        elif fault == 'context':
            c.execute(update(runs).where(runs.c.id == run['id'])
                .values(context={**run['context'], 'tools': 999}))

    event.listen(store.engine, 'after_cursor_execute', mutate)
    try:
        with pytest.raises(DomainError) as error:
            spec.advance(worker, run)
    finally:
        event.remove(store.engine, 'after_cursor_execute', mutate)
    assert reached == [fault]
    if fault == 'unknown':
        assert error.value.code == 'OUTCOME_UNKNOWN'
    assert sent == []
    assert snapshot(store) == before
    (tmp_path/'local-current-rollback.json').write_text(json.dumps(dict(
        fault=fault, boundary='after actual SPEC_STEP_VERIFIED INSERT',
        error=error.value.public(), all_tables_identical=True,
        original_lease_seconds=30, original_run_seconds=300, fault_injection=True,
        clock_frozen_after_claim=True, real_model_requests=0), indent=2)+'\n')


def test_local_pure_precedes_atomic_preparation_and_commits_once(env, monkeypatch):
    data, worker, run, sent, _ = local_case(env, monkeypatch)
    store = data[0]
    before = snapshot(store)
    writes, calculated = [], []
    original = spec.receipt_for
    known = {r['id'] for r in before['operations']}

    def receipt_for(oid, *args, **kwargs):
        if oid not in known and not calculated:
            assert writes == []
            calculated.append(oid)
        return original(oid, *args, **kwargs)

    def observe(c, cursor, statement, parameters, context, executemany):
        target = boundary(statement)
        if target is not None:
            writes.append(target)

    monkeypatch.setattr(spec, 'receipt_for', receipt_for)
    event.listen(store.engine, 'after_cursor_execute', observe)
    try:
        assert spec.advance(worker, run)
    finally:
        event.remove(store.engine, 'after_cursor_execute', observe)
    assert len(calculated) == 1
    assert writes == ['prepared', 'intent', 'verified', 'context', 'app_status', 'event']
    assert sent == []
    after = snapshot(store)
    changed = {name for name in before if before[name] != after[name]}
    assert changed == {'operations', 'operation_intents', 'runs', 'internal_app_runs', 'events'}
    written = [r for r in after['operations'] if r['run_id'] == run['id']]
    assert len(written) == 1 and written[0]['status'] == 'VERIFIED'
    current = next(r for r in after['runs'] if r['id'] == run['id'])
    assert current['context']['tools'] == run['context']['tools'] + 1
    assert current['version'] == run['version'] and current['lease_until'] == run['lease_until']
