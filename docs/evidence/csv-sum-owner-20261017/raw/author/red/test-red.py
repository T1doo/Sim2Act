"""Synthetic prospective CSV sum-only owner declarations; never a model claim."""
from test_persistent_app_runs import setup


def test_prospective_csv_sum_scope(env):
    release, instance, _, _ = setup(env)
    response = env[2].post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
        expected_revision=instance['revision'], expected_release_fingerprint=release['fingerprint'],
        input={'column': 'amount'}, request_key='freeze-csv-scope',
        csv_review='FREEZE_SUM_ONLY_WITHOUT_MD',
    ))
    assert response.status_code == 202, response.text
    state = env[2].get(f"/api/internal/instances/{instance['id']}/runs/{response.json()['run_id']}/csv-owner-review")
    assert state.status_code == 200, state.text
    assert state.json()['content_access'] is False
