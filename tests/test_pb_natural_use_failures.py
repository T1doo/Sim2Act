"""Actual worker rejects late per-use results without changing saved logic."""
import json
import time

import pytest
from sqlalchemy import insert, select, update
from test_natural_spec_apps import transport
from test_pb_natural_uses import THIRD, prepared_use
from test_spec_app_operations import snapshot

from sim2act import natural_specs as natural
from sim2act import pb_natural_uses as use
from sim2act.db import (
    attempts,
    goal_cards,
    grants,
    internal_instance_data,
    internal_instances,
    new_id,
    operations,
    runs,
)
from sim2act.worker import Worker


@pytest.mark.parametrize('fault', ['target_revoke', 'cancel', 'bad_output', 'goal', 'instance_revision', 'fence'])
def test_late_third_input_result_never_saves(env, tmp_path, fault):
    data, app, release, inst, resource, goal, body, route = prepared_use(env)
    checked = data[2].post(route + '/pb-use-reviews', json=body).json()
    commit = dict(review=body, expected_review_fingerprint=checked['review_fingerprint'], consent=use.CONSENT)
    response = data[2].post(route + '/pb-use-runs', json=commit)
    assert response.status_code == 202, response.text
    rid = response.json()['run_id']
    before = snapshot(data[0])
    sent = []

    def mutate(raw, payload):
        if fault == 'bad_output':
            value = json.loads(raw['choices'][0]['message']['content'])
            value['items'][0]['citations'][0]['quote'] = 'not the third material'
            raw['choices'][0]['message']['content'] = json.dumps(value)
        else:
            with data[0].tx() as c:
                if fault == 'cancel':
                    c.execute(update(runs).where(runs.c.id == rid).values(cancel_intent=True))
                elif fault == 'goal':
                    c.execute(update(goal_cards).where(goal_cards.c.id == goal['id']).values(version=2))
                elif fault == 'instance_revision':
                    c.execute(update(internal_instances).where(internal_instances.c.id == inst['id']).values(revision=2))
                elif fault == 'fence':
                    c.execute(update(runs).where(runs.c.id == rid).values(fence=99))
                else:
                    c.execute(update(grants).where(grants.c.principal_id == inst['runtime_id'],
                        grants.c.resource_id == resource).values(revoked=True))

    assert Worker(data[0], data[1], goal_planner_transport=transport(sent, THIRD, mutate)).once()
    with data[0].tx() as c:
        assert not c.execute(select(internal_instance_data).where(internal_instance_data.c.run_id == rid)).first()
        assert not c.execute(select(operations).where(operations.c.run_id == rid,
            operations.c.tool_ref == natural.SAVE)).first()
        job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        attempt = dict(c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings().one())
        assert job['status'] != 'SUCCEEDED'
        assert attempt['status'] == 'REJECTED_KNOWN' and attempt['response']['received_raw']
    assert len(sent) == 1
    after = snapshot(data[0])
    for table in ['app_drafts', 'internal_releases', 'internal_instance_data']:
        assert before[table] == after[table]
    (tmp_path / 'late-proof.json').write_text(json.dumps(dict(fault=fault, run=job, attempt=attempt,
        real_model_requests=0, typed_saves=0), indent=2))


def test_natural_grant_expiry_invalidates_confirmation(env, tmp_path):
    data, app, release, inst, resource, goal, body, route = prepared_use(env)
    expires = time.time() + 30
    with data[0].tx() as c:
        c.execute(insert(grants).values(id=new_id('grant'), principal_id=inst['runtime_id'],
            project_id=data[4], resource_id=resource, tool_ref=natural.READ,
            expires_at=expires, revision=1, revoked=False))
    checked = data[2].post(route + '/pb-use-reviews', json=body)
    assert checked.status_code == 200, checked.text
    assert checked.json()['approved_grant_state'][0]['effective'] is True
    before = snapshot(data[0])
    time.sleep(max(0, expires - time.time()) + 0.1)
    assert time.time() >= expires
    assert snapshot(data[0]) == before
    commit = dict(review=body, expected_review_fingerprint=checked.json()['review_fingerprint'], consent=use.CONSENT)
    rejected = data[2].post(route + '/pb-use-runs', json=commit)
    assert rejected.status_code == 409, rejected.text
    assert snapshot(data[0]) == before
    (tmp_path / 'natural-expiry-proof.json').write_text(json.dumps(dict(
        preview=checked.json(), expires_at=expires, confirmed_after=time.time(),
        rejected=rejected.json(), grants_unchanged=True, real_model_requests=0), indent=2))
