"""Independent historical-payload corruption probe, isolated SQLite fixtures."""
import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import select, update

import test_owner_acceptance as author
from sim2act.db import internal_owner_records

OUT = Path('/tmp/owner-version-acceptance-review-20261011/history-green')
OUT.mkdir(exist_ok=True)


@pytest.mark.parametrize('command', ['PREPARE', 'DECIDE'])
def test_content_append_checks_all_authorized_prior_payloads(env, command):
    data, release, instance, job = author.flow(env)
    old, _ = author.prepare(data, release, instance, job)
    response = data[2].post(author.path(instance) + '-requests', json=author.choice_body(old))
    assert response.status_code == 201
    if command == 'PREPARE':
        body = {
            'command': 'PREPARE', 'request_key': 'after-corrupted-history', 'expected_sequence': 2,
            'expected_revision': instance['revision'],
            'expected_release_fingerprint': release['fingerprint'], 'run_ids': [job['id']],
        }
        expected_count = 2
    else:
        newest, _ = author.prepare(data, release, instance, job, key='newest-before-corruption')
        body = author.choice_body(newest, key='after-corrupted-history')
        expected_count = 3
    with data[0].tx() as c:
        before = dict(c.execute(select(internal_owner_records).where(internal_owner_records.c.id == old['id'])).mappings().one())
        altered = copy.deepcopy(before['payload'])
        altered['contract']['items'][0]['text'] = 'CONTROLLED altered historical criteria'
        c.execute(update(internal_owner_records).where(internal_owner_records.c.id == old['id']).values(payload=altered))
    # Metadata and independent seals are deliberately left at their original values.
    prior = data[2].get(author.path(instance))
    response = data[2].post(author.path(instance) + '-requests', json=body)
    after = data[2].get(author.path(instance))
    with data[0].tx() as c:
        records = [dict(r) for r in c.execute(select(internal_owner_records).where(internal_owner_records.c.instance_id == instance['id'])).mappings()]
    report = {
        'command': command, 'before_expected_records': expected_count,
        'mutated_only': 'earlier protected payload; original metadata/fingerprint/seal retained',
        'prior_get': {'status_code': prior.status_code, 'body': prior.json()},
        'post': {'status_code': response.status_code, 'body': response.json()},
        'after_get': {'status_code': after.status_code, 'body': after.json()},
        'actual_record_count': len(records),
        'semantic_owner_declarations': 'SIMULATED', 'live_models': 0,
    }
    (OUT / ('history-corruption-' + command.lower() + '.json')).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    assert prior.json()['owner_acceptance'] == 'STALE' and not prior.json()['content_access']
    assert response.status_code == 409, report
    assert len(records) == expected_count, report
