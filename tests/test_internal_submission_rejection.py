"""Only a fresh rejected transaction supplies exact negative acceptance evidence."""
import copy
from contextlib import contextmanager

import pytest
from sqlalchemy import update
from test_pb_natural_uses import prepared_use
from test_spec_app_operations import snapshot

from sim2act import app_jobs
from sim2act import pb_natural_uses as use
from sim2act.db import fingerprint, grants, internal_instances
from sim2act.errors import DomainError


def test_fresh_rejection_exact_body_and_existing_key_has_no_negative_proof(env, tmp_path, monkeypatch):
    data, _, _, inst, resource, _, body, route = prepared_use(env)
    checked = data[2].post(route + '/pb-use-reviews', json=body).json()
    good = dict(review=body, expected_review_fingerprint=checked['review_fingerprint'], consent=use.CONSENT)
    bad = {**good, 'expected_review_fingerprint': '0' * 64}
    before = snapshot(data[0])
    response = data[2].post(route + '/pb-use-runs', json=bad)
    assert response.status_code == 409
    proof = response.json()['error']['submission_rejection']
    assert proof['request_fingerprint'] == fingerprint(bad)
    assert proof['request_key'] == body['request_key'] and proof['phase'] == 'TX_ROLLED_BACK'
    assert snapshot(data[0]) == before
    for field, invalid in [('expected_revision', 'wrong'), ('expected_revision', 0), ('expected_goal_version', None)]:
        malformed = copy.deepcopy(good)
        malformed['review'][field] = invalid
        reply = data[2].post(route + '/pb-use-runs', json=malformed)
        assert reply.status_code == 422
        assert reply.json()['submission_rejection']['request_fingerprint'] == fingerprint(malformed)
        assert snapshot(data[0]) == before
    def fail_after_insert(*args, **kwargs):
        raise DomainError('INVALID_INPUT', 'synthetic seal failure after insert')
    with monkeypatch.context() as patch:
        patch.setattr(use, 'seal', fail_after_insert)
        rolled = data[2].post(route + '/pb-use-runs', json=good)
    assert rolled.status_code == 400 and rolled.json()['error']['submission_rejection']['phase'] == 'TX_ROLLED_BACK'
    assert snapshot(data[0]) == before
    accepted = data[2].post(route + '/pb-use-runs', json=good)
    assert accepted.status_code == 202
    after = snapshot(data[0])
    for request in (bad, malformed):
        reply = data[2].post(route + '/pb-use-runs', json=request)
        assert reply.status_code in (409, 422)
        assert 'submission_rejection' not in reply.json()
        assert 'submission_rejection' not in reply.json().get('error', {})
        assert snapshot(data[0]) == after
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == inst['runtime_id'], grants.c.resource_id == resource, grants.c.tool_ref == 'resource.read').values(revoked=True))
    revoked = snapshot(data[0])
    replay = data[2].post(route + '/pb-use-runs', json=good)
    assert replay.status_code == 403 and 'submission_rejection' not in replay.json()['error']
    assert snapshot(data[0]) == revoked
    with data[0].tx() as c:
        c.execute(update(internal_instances).where(internal_instances.c.id == inst['id']).values(principal_id=data[6]))
    foreign = snapshot(data[0])
    malformed['review']['request_key'] = 'foreign-instance-new-key'
    denied = data[2].post(route + '/pb-use-runs', json=malformed)
    assert denied.status_code == 422 and 'submission_rejection' not in denied.json()
    assert snapshot(data[0]) == foreign
    (tmp_path / 'proof.json').write_text(__import__('json').dumps(dict(rejected=response.json(), accepted=accepted.json(), real_model_requests=0), indent=2))


@pytest.mark.parametrize('failure', ['commit', 'rollback', 'unknown'])
def test_commit_rollback_and_unknown_failures_never_supply_rejection_proof(failure):
    class Store:
        @contextmanager
        def tx(self):
            try:
                yield object()
            except DomainError:
                if failure == 'rollback':
                    raise DomainError('VERSION_CONFLICT', 'rollback failed') from None
                raise
            if failure == 'commit':
                raise DomainError('VERSION_CONFLICT', 'commit effect unknown')
    guard = dict(proof={'acceptance': 'NOT_ACCEPTED'})
    with pytest.raises(DomainError) as caught:
        with app_jobs.submission_tx(Store(), guard):
            if failure != 'commit':
                raise DomainError('OUTCOME_UNKNOWN' if failure == 'unknown' else 'INVALID_INPUT')
    assert caught.value.submission_rejection is None
