"""Real receive transaction handoff; scoped faults only after original commits."""
import copy
import json
from contextlib import contextmanager

import pytest
from conftest import env  # noqa: F401
from sqlalchemy import select, update
from test_natural_spec_apps import enqueue, ready, setup, transport

from sim2act.db import attempts, events, internal_instance_data, runs
from sim2act.worker import Worker


@pytest.mark.parametrize('damage', ['owner', 'wire', 'competing_response'])
def test_received_commit_handoff_never_changes_competing_history(env, monkeypatch, tmp_path, damage):  # noqa: F811
    data = setup(env)
    store, settings, client = data[:3]
    _, _, release, inst, _ = ready(data)
    rid = enqueue(data, release, inst, key='original-handoff')
    other = store.user('other isolated owner', 'other-isolated-owner')
    second = client.post('/api/projects', json=dict(name='isolated other project'))
    assert second.status_code == 201
    with store.tx() as c:
        project = store.own_project(c, data[3], second.json()['id'])
        other_runtime = project['runtime_id']
    sent, held = [], {}
    original_tx = store.tx

    def mutate(raw, payload):
        held['armed'] = True

    @contextmanager
    def interleave(*args, **kwargs):
        # Every owning transaction remains the real Store.tx/SQLite transaction.
        with original_tx(*args, **kwargs) as c:
            yield c
        if not held.get('armed') or held.get('fired'):
            return
        with original_tx() as c:
            row = c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().first()
            if row is None or row['status'] != 'RECEIVED':
                return
            held['fired'] = True
            if damage == 'owner':
                c.execute(update(runs).where(runs.c.id == rid).values(
                    principal_id=other, project_id=second.json()['id'], runtime_id=other_runtime))
            elif damage == 'wire':
                parameters = copy.deepcopy(row['parameters'])
                parameters['natural_spec_wire']['sha256'] = 'f' * 64
                c.execute(update(attempts).where(attempts.c.id == row['id']).values(parameters=parameters))
            else:
                c.execute(update(attempts).where(attempts.c.id == row['id'])
                    .values(response={'competing': 'immutable fixture damage'}))
            held['attempt'] = dict(c.execute(select(attempts).where(
                attempts.c.id == row['id'])).mappings().one())
            held['events'] = [dict(r) for r in c.execute(select(events).where(
                events.c.run_id == rid, events.c.kind == 'NS_REJECTED')).mappings()]

    monkeypatch.setattr(store, 'tx', interleave)
    assert Worker(store, settings, goal_planner_transport=transport(sent, mutate=mutate)).once()
    assert held.get('fired') and len(sent) == 1
    with original_tx() as c:
        current = dict(c.execute(select(attempts).where(attempts.c.id == held['attempt']['id'])).mappings().one())
        assert current == held['attempt']
        assert [dict(r) for r in c.execute(select(events).where(
            events.c.run_id == rid, events.c.kind == 'NS_REJECTED')).mappings()] == held['events']
        assert not c.execute(select(internal_instance_data).where(
            internal_instance_data.c.instance_id == inst['id'])).first()
    (tmp_path / 'HANDOFF_HISTORY.json').write_text(json.dumps(dict(damage=damage,
        original_receive_committed=True, competing_history_unchanged=True,
        model_dispatches=len(sent), attempt=current), indent=2))
