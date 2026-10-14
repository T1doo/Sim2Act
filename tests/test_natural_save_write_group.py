"""Ordinary synthetic mutations after real typed INSERT; no cell/UDF observer."""
import copy
import json
import time
from dataclasses import replace

import pytest
from sqlalchemy import delete, event, select, update
from test_natural_spec_apps import enqueue, ready, setup, transport

from sim2act import pa_spec_apps as spec
from sim2act.db import (
    attempts,
    fingerprint,
    goal_cards,
    grants,
    internal_instance_data,
    internal_instances,
    meta,
    operations,
    resources,
    run_contracts,
    runs,
)
from sim2act.errors import DomainError
from sim2act.worker import Worker


@pytest.mark.parametrize('fault', [
    'lease', 'fence', 'version', 'cancel', 'stop', 'deadline', 'worker_tools',
    'owner_uid', 'owner_pid', 'owner_runtime', 'owner_worker', 'owner_deleted',
    'worker_deadline', 'live', 'read_revoke', 'save_revoke', 'read_expiry', 'save_expiry', 'goal', 'material',
    'context', 'typed', 'instance', 'receipt', 'audit', 'unknown', 'frozen_tools',
])
def test_typed_write_group_rechecks_owner_authority_budget_and_evidence(env, monkeypatch, tmp_path, fault):
    data = setup(env)
    store, settings = data[:2]
    origin, _, release, inst, _ = ready(data)
    rid = enqueue(data, release, inst)
    sent = []
    worker = Worker(store, settings, goal_planner_transport=transport(sent))
    run = store.claim(worker.id, settings.lease_seconds)
    assert run['id'] == rid
    for _ in range(3):
        assert spec.advance(worker, run)
    store.heartbeat(worker.id, rid, run['fence'], settings.lease_seconds)
    clock = [time.time()]
    monkeypatch.setattr(time, 'time', lambda: clock[0])

    def snapshot():
        with store.tx() as c:
            return {t.name: sorted((dict(row) for row in c.execute(select(t)).mappings()),
                key=lambda row: json.dumps(row, sort_keys=True, default=str))
                for t in meta.sorted_tables}

    before = snapshot()
    previous_context = next(x['context'] for x in before['runs'] if x['id'] == rid)
    original_contract = next(x for x in before['run_contracts'] if x['run_id'] == rid)
    reached = []

    def mutate(c, cursor, statement, parameters, context, executemany):
        if reached or not statement.lstrip().upper().startswith('INSERT INTO INTERNAL_INSTANCE_DATA '):
            return
        reached.append(fault)
        if fault in {'lease', 'fence', 'version', 'cancel'}:
            value = {'lease': dict(lease_until=clock[0] - 1),
                'fence': dict(fence=run['fence'] + 1),
                'version': dict(version=run['version'] + 1),
                'cancel': dict(cancel_intent=True)}[fault]
            c.execute(update(runs).where(runs.c.id == rid).values(**value))
        elif fault in {'owner_uid', 'owner_pid', 'owner_runtime', 'owner_worker'}:
            change = {'owner_uid': dict(principal_id=env[4]),
                'owner_pid': dict(project_id='different_project'),
                'owner_runtime': dict(runtime_id='different_runtime'),
                'owner_worker': dict(worker_id='different_worker')}[fault]
            c.execute(update(runs).where(runs.c.id == rid).values(**change))
        elif fault == 'owner_deleted':
            c.execute(delete(runs).where(runs.c.id == rid))
        elif fault == 'stop':
            worker.stop.set()
        elif fault == 'deadline':
            clock[0] = run['created_at'] + settings.run_seconds
        elif fault == 'worker_tools':
            worker.s = replace(worker.s, max_tools=2)
        elif fault == 'worker_deadline':
            worker.s = replace(worker.s, run_seconds=1)
        elif fault == 'live':
            worker.s = replace(worker.s, live_enabled=True)
        elif fault in {'read_revoke', 'save_revoke', 'read_expiry', 'save_expiry'}:
            resource = data[5] if fault.startswith('read_') else data[4]
            tool = 'resource.read' if fault.startswith('read_') else 'artifact.save_text'
            c.execute(update(grants).where(grants.c.resource_id == resource,
                grants.c.tool_ref == tool).values(**(dict(expires_at=clock[0] - 1) if fault.endswith('expiry') else dict(revoked=True))))
        elif fault == 'goal':
            c.execute(update(goal_cards).where(goal_cards.c.id == data[6]['id']).values(version=2))
        elif fault == 'material':
            c.execute(update(resources).where(resources.c.id == data[5]).values(hash='0' * 64))
        elif fault == 'context':
            c.execute(update(runs).where(runs.c.id == rid).values(context={**previous_context, 'tools': 999}))
        elif fault == 'typed':
            c.execute(update(internal_instance_data).where(internal_instance_data.c.instance_id == inst['id'])
                .values(data=dict(result={}), fingerprint='0' * 64))
        elif fault == 'instance':
            c.execute(update(internal_instances).where(internal_instances.c.id == inst['id'])
                .values(revision=inst['revision'] + 1))
        elif fault == 'receipt':
            c.execute(update(operations).where(operations.c.run_id == rid, operations.c.tool_ref == spec.SAVE)
                .values(receipt={}))
        elif fault == 'audit':
            c.execute(update(attempts).where(attempts.c.run_id == origin).values(parameters=dict(corrupt=True)))
        elif fault == 'unknown':
            c.execute(update(attempts).where(attempts.c.run_id == rid).values(status='STARTED'))
        elif fault == 'frozen_tools':
            frozen = copy.deepcopy(original_contract['snapshot'])
            frozen['limits']['max_tools'] = 2
            c.execute(update(run_contracts).where(run_contracts.c.run_id == rid)
                .values(snapshot=frozen, fingerprint=fingerprint(frozen)))

    event.listen(store.engine, 'after_cursor_execute', mutate)
    try:
        with pytest.raises(DomainError) as rejected:
            spec.advance(worker, run)
    finally:
        event.remove(store.engine, 'after_cursor_execute', mutate)
    assert reached == [fault]
    if fault in {"worker_tools", "worker_deadline"}:
        assert rejected.value.code == "BUDGET_EXHAUSTED"
    elif fault == "frozen_tools" or fault.startswith("owner_"):
        assert rejected.value.code == "VERSION_CONFLICT"
    assert len(sent) == 1
    assert snapshot() == before
    (tmp_path / 'typed-write-rollback.json').write_text(json.dumps(dict(
        fault=fault, boundary='after actual typed INSERT', error=rejected.value.public(),
        reached=reached, all_tables_identical=True, known_model_history_preserved=True,
        real_model_requests=0), indent=2) + '\n')
