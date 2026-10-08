import json
import time
from pathlib import Path

import pytest
from conftest import env as original_env
from test_natural_activation_pg import waiting
from test_natural_goal_planning import authority, rows

from sim2act.db import attempts, events, operations, reservations, runs
from sim2act.errors import DomainError


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.delenv("SIM2ACT_TEST_DATABASE_URL", raising=False)
    fixture = original_env.__wrapped__(tmp_path)
    value = next(fixture)
    try:
        yield value
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def save(name, data):
    Path('/tmp/sim2act-lease-' + name + '.json').write_text(json.dumps(data, indent=2) + '\n')


def test_confirm_then_fresh_cancel_preserves_no_lease_and_authority(isolated_env):
    value, _, rid, sent, worker, body = waiting(isolated_env)
    store, _, client, *_ = value
    before = rows(store, runs)[0]
    authorized = authority(store)
    reply = client.post(f'/api/runs/{rid}/confirm-natural-plan', json=body)
    assert reply.status_code == 200, reply.text
    confirmed = rows(store, runs)[0]
    assert confirmed['status'] == 'QUEUED'
    assert confirmed['lease_until'] == 0 and confirmed['worker_id'] is None
    assert confirmed['fence'] == before['fence']
    assert confirmed['version'] == body['expected_version'] + 1
    with store.tx() as c, pytest.raises(DomainError) as stale:
        store.guard(c, rid, before['fence'])
    assert stale.value.code == 'VERSION_CONFLICT'
    repeated = client.post(f'/api/runs/{rid}/confirm-natural-plan', json=body)
    assert repeated.status_code == 200 and repeated.json() == reply.json()
    rejected = client.post(f'/api/runs/{rid}/commands', json={
        'command': 'cancel', 'version': body['expected_version']})
    assert rejected.status_code == 409
    fresh = client.post(f'/api/runs/{rid}/commands', json={
        'command': 'cancel', 'version': confirmed['version']})
    assert fresh.status_code == 200, fresh.text
    cancelled = rows(store, runs)[0]
    assert cancelled['status'] == 'CANCELLED' and cancelled['cancel_intent'] is True
    assert cancelled['version'] == confirmed['version'] + 1
    assert cancelled['lease_until'] == 0 and cancelled['worker_id'] is None
    assert not worker.once()
    assert len(sent) == len(rows(store, attempts)) == len(rows(store, reservations)) == 1
    assert not rows(store, operations) and cancelled['result'] is None
    assert len([e for e in rows(store, events) if e['kind'] == 'NL_PLAN_CONFIRMED']) == 1
    assert authority(store) == authorized
    save('fresh-cancel', {
        'source_sha': 'f9044237805e91438807d5acbf9b963ac8af83e4',
        'backend': 'SQLite', 'ordering': 'confirm, stale cancel rejected, fresh cancel accepted',
        'http_statuses': [reply.status_code, repeated.status_code, rejected.status_code, fresh.status_code],
        'versions': [before['version'], confirmed['version'], cancelled['version']],
        'fences': [before['fence'], confirmed['fence'], cancelled['fence']],
        'lease_until': cancelled['lease_until'], 'worker_id': cancelled['worker_id'],
        'provider_wires': len(sent), 'operations': 0, 'authority_unchanged': True,
        'limitations': 'Sequential SQLite; not actual PG concurrent race evidence'})


def test_confirm_claim_cancel_finish_preserves_fencing_and_release(isolated_env):
    value, _, rid, sent, worker, body = waiting(isolated_env)
    store, _, client, *_ = value
    authorized = authority(store)
    before = rows(store, runs)[0]
    reply = client.post(f'/api/runs/{rid}/confirm-natural-plan', json=body)
    assert reply.status_code == 200, reply.text
    confirmed = rows(store, runs)[0]
    claimed = store.claim(worker.id, 30)
    assert claimed['id'] == rid and claimed['status'] == 'RUNNING'
    assert claimed['fence'] == confirmed['fence'] + 1
    assert claimed['worker_id'] == worker.id and claimed['lease_until'] > time.time()
    with store.tx() as c:
        assert store.guard(c, rid, claimed['fence'])['worker_id'] == worker.id
        with pytest.raises(DomainError) as stale:
            store.guard(c, rid, before['fence'])
        assert stale.value.code == 'VERSION_CONFLICT'
    reply = client.post(f'/api/runs/{rid}/commands', json={
        'command': 'cancel', 'version': claimed['version']})
    assert reply.status_code == 200, reply.text
    assert rows(store, runs)[0]['status'] == 'CANCEL_REQUESTED'
    worker.finish(rid, claimed['fence'], 'PAUSED', verify_goal_source=True)
    cancelled = rows(store, runs)[0]
    assert cancelled['status'] == 'CANCELLED' and cancelled['lease_until'] == 0
    assert cancelled['version'] == claimed['version'] + 2
    with store.tx() as c, pytest.raises(DomainError) as stale:
        store.guard(c, rid, claimed['fence'])
    assert stale.value.code == 'VERSION_CONFLICT'
    assert not worker.once()
    assert not rows(store, operations) and cancelled['result'] is None
    assert len(sent) == len(rows(store, attempts)) == len(rows(store, reservations)) == 1
    assert authority(store) == authorized
    save('claim-cancel', {
        'source_sha': 'f9044237805e91438807d5acbf9b963ac8af83e4', 'backend': 'SQLite',
        'ordering': 'confirm, claim, fresh cancel, fenced finish',
        'versions': [before['version'], confirmed['version'], claimed['version'], cancelled['version']],
        'fences': [before['fence'], confirmed['fence'], claimed['fence'], cancelled['fence']],
        'lease_until': cancelled['lease_until'], 'provider_wires': len(sent),
        'operations': 0, 'authority_unchanged': True,
        'limitations': 'Sequential SQLite; not actual PG concurrent race evidence'})
