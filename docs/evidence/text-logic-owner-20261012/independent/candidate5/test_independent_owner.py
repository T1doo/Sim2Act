"""Finite ordinary GoalCard/API authority tests; SIMULATED owner decisions only."""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest
from conftest import env  # noqa: F401 -- isolated native fixture
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, select, update
from test_owner_acceptance import choice_body, path, prepare, state
from test_registered_text_extraction import snapshot
from test_text_logic_owner import goal_path, own_goal, own_run, own_source_barrier, save_goal, setup_owner
from test_text_logic_reuse import revoke_source

from sim2act import app_owner_goals as own
from sim2act.api import create_app
from sim2act.db import delivery_graph_requests, fingerprint, goal_card_versions, grants


def current_goal_body(data, made, rid, key):
    value = data[2].get(goal_path(made)).json()
    head = value['head']
    return dict(expected_candidate_fingerprint=made['candidate_fingerprint'],
        expected_goal_version=head['version'] if head else 0,
        expected_goal_fingerprint=head['fingerprint'] if head else None,
        expected_binding_fingerprint=value['binding_fingerprint'], goal=own_goal(rid),
        applicability=['SIMULATED explicit scope for this target only'],
        consent='AUTHOR_THIS_APPLICATION_OWN_GOAL_AND_SCOPE', request_key=key)


def test_actual_own_goal_64th_65th_capacity_and_original_get(env):
    data, made, _, _, _, _, rid = setup_owner(env)
    first = None
    for n in range(1, 65):
        saved, _ = save_goal(data, made, rid, key=f'actual-goal-version-{n}',
                            applicability=[f'SIMULATED explicit scope version {n}'])
        assert saved['sequence'] == saved['goal_version'] == n
        first = saved if first is None else first
    before = snapshot(data[0])
    refused = data[2].post(goal_path(made), json=current_goal_body(data, made, rid, 'actual-version-65'))
    assert refused.status_code == 400 and refused.json()['error']['code'] == 'BUDGET_EXHAUSTED', refused.text
    assert snapshot(data[0]) == before
    recovered = data[2].get(goal_path(made), params={'request_key': first['request_key']})
    assert recovered.status_code == 200, recovered.text
    value = recovered.json()
    assert value['status'] == 'CURRENT' and value['sequence'] == value['head']['version'] == 64
    assert value['recovered']['goal_version'] == 1
    assert value['recovered']['binding_fingerprint'] == first['binding_fingerprint']
    assert snapshot(data[0]) == before


def test_prepared_decision_budget_change_above_cap_rejects_without_write(env):
    low_env = (env[0], replace(env[1], max_total_tokens=51200), *env[2:])
    data, made, release, instance, _, _, rid = setup_owner(low_env)
    save_goal(data, made, rid)
    job = own_run(data, made, release, instance)
    review, _ = prepare(data, release, instance, job)
    body = choice_body(review)
    before = snapshot(data[0])
    settings = replace(data[1], max_total_tokens=63000)
    with TestClient(create_app(data[0], settings)) as client:
        client.headers['Authorization'] = 'Bearer synthetic-test-A'
        response = client.post(path(instance) + '-requests', json=body)
        assert response.status_code == 409 and response.json()['error']['code'] == 'VERSION_CONFLICT', response.text
        assert snapshot(data[0]) == before
        value = client.get(path(instance), params={'request_key': review['request_key']}).json()
        assert value['owner_acceptance'] == 'STALE' and value['sequence'] == 1
        assert 'payload' not in value['recovered'] and 'record' not in value
        assert value['prepare_current']['current_limits']['max_total_tokens'] == 63000
        assert review['payload']['contract']['current_limits']['max_total_tokens'] == 51200
        current_data = (data[0], settings, client, *data[3:])
        fresh, _ = prepare(current_data, release, instance, job, key='fresh-prepare-above-cap')
        assert fresh['payload']['contract']['current_limits']['max_total_tokens'] == 63000
        assert fresh['sequence'] == 2
        assert state(current_data, instance)['owner_acceptance'] == 'PENDING'


@pytest.mark.parametrize('stage', ['prepared_user', 'decided_runtime'])
def test_target_revocation_rejects_decision_and_allows_exact_metadata_stop(env, stage):
    data, made, release, instance, _, old, rid = setup_owner(env)
    save_goal(data, made, rid)
    job = own_run(data, made, release, instance)
    review, _ = prepare(data, release, instance, job)
    decision = choice_body(review)
    if stage == 'decided_runtime':
        assert data[2].post(path(instance) + '-requests', json=decision).status_code == 201
    revoke_source(data, delete_content=False)
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == rid,
            grants.c.principal_id == (data[3] if stage == 'prepared_user' else made['runtime_id'])).values(revoked=True))
    barrier = own_source_barrier(data, old)
    with barrier:
        before = snapshot_metadata_owner(data[0], instance['id'])
        value = state(data, instance, review['request_key'])
        assert value['owner_acceptance'] == 'STALE' and value['content_access'] is False
        assert 'prepare_current' not in value and 'payload' not in value['recovered']
        if stage == 'prepared_user':
            response = data[2].post(path(instance) + '-requests', json=decision)
            assert response.status_code == 403 and response.json()['error']['code'] == 'GRANT_REVOKED', response.text
            assert snapshot_metadata_owner(data[0], instance['id']) == before
        last = value['latest']
        command = 'CANCEL' if stage == 'prepared_user' else 'REVOKE'
        request = dict(command=command, request_key='stop-after-target-revoked',
            expected_sequence=value['sequence'], target_id=last['id'],
            target_fingerprint=last['fingerprint'], reason='SIMULATED explicit metadata stop after target lost')
        response = data[2].post(path(instance) + '-requests', json=request)
        assert response.status_code == 201, response.text
        stopped = state(data, instance, request['request_key'])
        assert stopped['owner_acceptance'] == ('CANCELLED' if command == 'CANCEL' else 'REVOKED')
        assert stopped['content_access'] is False and 'prepare_current' not in stopped
        assert stopped['recovered']['request_key'] == request['request_key']
        assert 'payload' not in stopped['recovered']
        again = data[2].get(path(instance), params={'request_key': decision['request_key'] if stage == 'decided_runtime' else review['request_key']})
        assert again.status_code == 200 and 'payload' not in again.json()['recovered']
        assert not barrier.blocked


def snapshot_metadata_owner(store, iid):
    from sim2act.db import internal_owner_records, internal_owner_seals
    with store.tx() as c:
        rows = c.execute(select(internal_owner_records.c.id, internal_owner_records.c.fingerprint,
            internal_owner_records.c.sequence).where(internal_owner_records.c.instance_id == iid)).mappings().all()
        seals = c.execute(select(internal_owner_seals)).mappings().all()
        return rows, seals


def test_two_normal_goal_version_writers_have_one_effect_and_no_partial_rows(env):
    data, made, _, _, _, _, rid = setup_owner(env)
    first, _ = save_goal(data, made, rid)
    body = current_goal_body(data, made, rid, 'version-writer-a')
    other = copy.deepcopy(body)
    other['request_key'] = 'version-writer-b'
    other['goal']['title'] = 'Other explicit writer title'
    gate = Barrier(2)
    def submit(request):
        gate.wait(timeout=15)
        return data[2].post(goal_path(made), json=request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, [body, other]))
    assert sorted(r.status_code for r in responses) == [201, 409], [r.text for r in responses]
    winner = next(r.json() for r in responses if r.status_code == 201)
    value = data[2].get(goal_path(made)).json()
    assert value['sequence'] == value['head']['version'] == 2
    assert value['current']['binding_fingerprint'] == winner['binding_fingerprint']
    with data[0].tx() as c:
        native = c.execute(select(goal_card_versions.c.version).where(goal_card_versions.c.card_id == first['card_id'])).scalars().all()
        seals = c.execute(select(delivery_graph_requests.c.kind).where(delivery_graph_requests.c.app_id == made['id'],
            delivery_graph_requests.c.kind.in_([own.KIND, own.KIND + '_seal']))).scalars().all()
    assert sorted(native) == [1, 2] and len(seals) == 4
    recovered = data[2].get(goal_path(made), params={'request_key': first['request_key']}).json()
    assert recovered['recovered']['goal_version'] == 1 and recovered['head']['version'] == 2


def test_fault_after_second_goal_seal_rolls_back_native_and_both_seals(env):
    data, made, _, _, _, _, rid = setup_owner(env)
    save_goal(data, made, rid)
    body = current_goal_body(data, made, rid, 'fault-after-second-seal')
    before = snapshot(data[0])
    insert_count = 0
    def fault(conn, cursor, sql, args, context, many):
        nonlocal insert_count
        if sql.startswith('INSERT INTO delivery_graph_requests'):
            insert_count += 1
            if insert_count == 2:
                raise RuntimeError('SIMULATED fault after both goal seals inserted')
    event.listen(data[0].engine, 'after_cursor_execute', fault)
    try:
        with pytest.raises(RuntimeError, match='after both goal seals'):
            data[2].post(goal_path(made), json=body)
    finally:
        event.remove(data[0].engine, 'after_cursor_execute', fault)
    assert insert_count == 2 and snapshot(data[0]) == before


@pytest.mark.parametrize('kind', [own.KIND, own.KIND + '_seal'])
def test_either_goal_record_seal_missing_denies_current_and_does_not_append(env, kind):
    data, made, _, _, _, _, rid = setup_owner(env)
    saved, _ = save_goal(data, made, rid)
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.app_id == made['id'],
            delivery_graph_requests.c.request_key == saved['request_key'], delivery_graph_requests.c.kind == kind))
    before = snapshot(data[0])
    response = data[2].get(goal_path(made), params={'request_key': saved['request_key']})
    assert response.status_code == 409 and response.json()['error']['code'] == 'VERSION_CONFLICT', response.text
    assert snapshot(data[0]) == before


def test_single_goal_row_boolean_substitution_cannot_match_unchanged_other_seal(env):
    data, made, _, _, _, _, rid = setup_owner(env)
    saved, _ = save_goal(data, made, rid)
    with data[0].tx() as c:
        row = c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.app_id == made['id'],
            delivery_graph_requests.c.kind == own.KIND)).mappings().one()
        changed = copy.deepcopy(row['snapshot'])
        changed['response']['sequence'] = True
        c.execute(update(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == row['app_id'],
            delivery_graph_requests.c.principal_id == row['principal_id'],
            delivery_graph_requests.c.kind == row['kind'],
            delivery_graph_requests.c.request_key == row['request_key'])
            .values(snapshot=changed, fingerprint=fingerprint(changed)))
    before = snapshot(data[0])
    response = data[2].get(goal_path(made), params={'request_key': saved['request_key']})
    assert response.status_code == 409 and response.json()['error']['code'] == 'VERSION_CONFLICT', response.text
    assert snapshot(data[0]) == before
