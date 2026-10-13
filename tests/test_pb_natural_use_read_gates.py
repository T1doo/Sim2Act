"""Shared entry points authorize each accepted target before private row reads."""
import json
import re
import time

import pytest
from fastapi.testclient import TestClient
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import select, update
from test_natural_spec_apps import transport
from test_pb_natural_specs import drive_to_success
from test_pb_natural_uses import THIRD, prepared_use
from test_spec_app_operations import snapshot

from sim2act import pb_natural_uses as use
from sim2act.api import create_app
from sim2act.db import (
    Store,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
)
from sim2act.errors import DomainError


class TypedPrivateBarrier(PrivateReadBarrier):
    """Actual row-cell protection, including stored typed/AppRun bodies."""
    def __init__(self, store, rid, aid, resource):
        super().__init__(store, {rid}, {resource})
        self.full_binding_reads = []
        self.protected_ids = {rid, aid}
        self.rules.update({
            'internal_instance_data': (internal_instance_data, 'run_id', {aid}, {'data'}),
            'internal_app_runs': (internal_app_runs, 'id', {aid}, {'output', 'error'}),
        })

    def _trace(self, conn, cursor, statement, parameters, context, many):
        projection = statement.split("\nFROM", 1)[0]
        if (re.search(r'(?:SELECT |, )internal_run_bindings\.snapshot(?:,|\s|$)', projection)
                and any(identifier in repr(parameters) for identifier in self.protected_ids)):
            self.full_binding_reads.append(dict(sql=statement, parameters=repr(parameters)))
        return super()._trace(conn, cursor, statement, parameters, context, many)


def successful_target(env):
    data, app, release, inst, resource, goal, body, route = prepared_use(env, run_base=True)
    with data[0].tx() as c:
        previous = c.execute(select(internal_run_bindings.c.run_id).where(
            internal_run_bindings.c.snapshot['instance_id'].as_string() == inst['id'])).scalar_one()
    reviewed = data[2].post(route + '/pb-use-reviews', json=body)
    assert reviewed.status_code == 200, reviewed.text
    commit = dict(review=body, expected_review_fingerprint=reviewed.json()['review_fingerprint'], consent=use.CONSENT)
    response = data[2].post(route + '/pb-use-runs', json=commit)
    assert response.status_code == 202, response.text
    accepted = response.json()
    drive_to_success(data, accepted['run_id'], transport([], THIRD))
    generic = dict(expected_revision=inst['revision'], expected_release_fingerprint=release['fingerprint'],
        input={}, request_key=body['request_key'])
    return data, app, release, inst, resource, commit, route, previous, accepted, generic


def requests(app, inst, route, previous, commit, generic):
    return [
        ('list', 'GET', f"/api/internal/apps/{app['id']}/instances", None),
        ('instance', 'GET', route, None),
        ('old_authorized_run', 'GET', route + '/runs/' + previous, None),
        ('same_key', 'POST', route + '/pb-use-runs', commit),
        ('mismatched_same_key', 'POST', route + '/runs', generic),
    ]


@pytest.mark.parametrize("fault", ["revoke", "expiry"])
def test_revoked_or_expired_target_shared_reads(env, tmp_path, fault):
    data, app, release, inst, resource, commit, route, previous, accepted, generic = successful_target(env)
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == inst['runtime_id'],
            grants.c.resource_id == resource, grants.c.tool_ref == 'resource.read').values(
                **({'revoked': True} if fault == 'revoke' else {'expires_at': time.time() + 2})))
    if fault == 'expiry':
        time.sleep(2.1)
    before = snapshot(data[0])
    raw, guarded = [], []
    with TestClient(data[2].app, raise_server_exceptions=False) as client:
        client.headers['Authorization'] = 'Bearer synthetic-test-A'
        for name, method, path, body in requests(app, inst, route, previous, commit, generic):
            response = client.request(method, path, json=body)
            raw.append(dict(name=name, status=response.status_code, third_content_in_response=THIRD in response.text,
                response=response.text))
        for name, method, path, body in requests(app, inst, route, previous, commit, generic):
            with TypedPrivateBarrier(data[0], accepted['run_id'], accepted['app_run_id'], resource) as barrier:
                response = client.request(method, path, json=body)
                guarded.append(dict(name=name, status=response.status_code, blocked=barrier.blocked,
                    evaluated_count=len(barrier.evaluated), full_binding_reads=barrier.full_binding_reads, statements=barrier.statements))
    assert snapshot(data[0]) == before
    proof = dict(raw=raw, guarded=guarded, actual_worker=True, real_model_requests=0, no_writes=True)
    (tmp_path / 'shared-read-diagnostic.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    print(json.dumps(dict(raw=[{k:v for k,v in row.items() if k!='response'} for row in raw],
        guarded=[dict(name=row['name'],status=row['status'],blocked=row['blocked']) for row in guarded])))
    assert raw[0]['status'] == 403 and not raw[0]['third_content_in_response']
    assert all(not row['blocked'] and not row['full_binding_reads'] for row in guarded)
    assert [row['status'] for row in raw] == [403, 403, 200, 403, 403]
    assert [row['status'] for row in guarded] == [403, 403, 200, 403, 403]


def test_authorized_cold_normal_paths_and_cross_instance_scope(env, tmp_path):
    data, app, release, inst, resource, commit, route, previous, accepted, generic = successful_target(env)
    other = data[2].post(f"/api/internal/releases/{release['id']}/instances", json=dict(
        expected_release_fingerprint=release['fingerprint'], request_key='read-gate-other-instance'))
    assert other.status_code == 201, other.text
    other_route = '/api/internal/instances/' + other.json()['id']
    before = snapshot(data[0])
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1]), raise_server_exceptions=False) as client:
            client.headers['Authorization'] = 'Bearer synthetic-test-A'
            for name, method, path, body in requests(app, inst, route, previous, commit, generic):
                response = client.request(method, path, json=body)
                assert response.status_code == (409 if name == 'mismatched_same_key' else 202 if name == 'same_key' else 200), response.text
                if name in ('list', 'instance'):
                    assert THIRD in response.text
                if name == 'old_authorized_run':
                    assert THIRD not in response.text
                if name == 'same_key':
                    assert response.json()['run_id'] == accepted['run_id'] and response.json()['cached']
            for header in ['synthetic-test-A', 'synthetic-test-B']:
                client.headers['Authorization'] = 'Bearer ' + header
                with TypedPrivateBarrier(cold, accepted['run_id'], accepted['app_run_id'], resource) as barrier:
                    for path in [other_route + '/runs/' + accepted['run_id'],
                        other_route + '/runs/' + accepted['run_id'] + '/control-status']:
                        response = client.get(path)
                        assert response.status_code in (403, 409), response.text
                    assert not barrier.blocked and not barrier.full_binding_reads
            (tmp_path / 'normal-cross-proof.json').write_text(json.dumps(dict(
                accepted=accepted, cold=True, same_key_cached=True, wrong_instance_private_reads=0,
                other_user_private_reads=0, actual_worker=True, real_model_requests=0), indent=2))
    finally:
        cold.engine.dispose()
    assert snapshot(data[0]) == before


def test_revocation_control_and_raw_reader_use_only_authorized_metadata(env, tmp_path):
    from sim2act import lifecycle

    data, app, release, inst, resource, goal, body, route = prepared_use(env)
    checked = data[2].post(route + '/pb-use-reviews', json=body)
    assert checked.status_code == 200, checked.text
    accepted = data[2].post(route + '/pb-use-runs', json=dict(review=body,
        expected_review_fingerprint=checked.json()['review_fingerprint'], consent=use.CONSENT)).json()
    rid, aid = accepted['run_id'], accepted['app_run_id']
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.principal_id == inst['runtime_id'],
            grants.c.resource_id == resource).values(revoked=True))
    with TestClient(data[2].app, raise_server_exceptions=False) as client:
        client.headers['Authorization'] = 'Bearer synthetic-test-A'
        with TypedPrivateBarrier(data[0], rid, aid, resource) as barrier:
            with pytest.raises(DomainError) as missing_context:
                with data[0].tx() as c:
                    lifecycle.data_rows(c, inst['id'])
            assert missing_context.value.code == 'PERMISSION_DENIED'
            status = client.get(route + '/runs/' + rid + '/control-status')
            assert status.status_code == 200 and status.json()['content_access'] is False, status.text
            paused = client.post(route + '/runs/' + rid + '/commands', json=dict(command='pause', version=status.json()['version']))
            assert paused.status_code == 200 and paused.json()['status'] == 'PAUSED', paused.text
            version = client.get(route + '/runs/' + rid + '/control-status').json()['version']
            resume = client.post(route + '/runs/' + rid + '/commands', json=dict(command='resume', version=version))
            assert resume.status_code == 403, resume.text
            # Snapshot is itself privileged test inspection, performed outside the barrier.
            cancelled = client.post(route + '/runs/' + rid + '/commands', json=dict(command='cancel', version=version))
            assert cancelled.status_code == 200 and cancelled.json()['status'] == 'CANCELLED', cancelled.text
            assert not barrier.blocked and not barrier.full_binding_reads
            proof = dict(status=status.json(), pause=paused.json(), resume=resume.json(), cancel=cancelled.json(),
                blocked=barrier.blocked, full_binding_reads=barrier.full_binding_reads, statements=barrier.statements,
                raw_reader_fail_closed=True, real_model_requests=0)
    after = snapshot(data[0])
    assert not [row for row in after['internal_instance_data'] if row['run_id'] == aid]
    (tmp_path / 'control-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2))


def test_corrupted_result_scope_and_missing_control_metadata_fail_before_body(env, tmp_path):
    import copy

    from sqlalchemy import delete, insert

    from sim2act.db import delivery_graph_requests, new_id

    data, app, release, inst, resource, commit, route, previous, accepted, generic = successful_target(env)
    other = data[2].post(f"/api/internal/releases/{release['id']}/instances", json=dict(
        expected_release_fingerprint=release['fingerprint'], request_key='fault-other-instance'))
    assert other.status_code == 201, other.text
    foreign_id = new_id('iapprun')
    rid, aid = accepted['run_id'], accepted['app_run_id']
    with data[0].tx() as c:
        app_copy = dict(c.execute(select(internal_app_runs).where(internal_app_runs.c.id == aid)).mappings().one())
        app_copy.update(id=foreign_id, instance_id=other.json()['id'], request_key='fault-foreign-result')
        c.execute(insert(internal_app_runs).values(**app_copy))
        c.execute(update(internal_instance_data).where(internal_instance_data.c.run_id == aid).values(run_id=foreign_id))
    checks=[]
    with TestClient(data[2].app, raise_server_exceptions=False) as client:
        client.headers['Authorization'] = 'Bearer synthetic-test-A'
        with TypedPrivateBarrier(data[0], rid, foreign_id, resource) as barrier:
            for path in [route, f"/api/internal/apps/{app['id']}/instances"]:
                response = client.get(path)
                assert response.status_code == 409, response.text
            assert not barrier.blocked and not barrier.full_binding_reads
            checks.append(dict(fault='foreign_typed_row', blocked=barrier.blocked, statements=barrier.statements))
        with data[0].tx() as c:
            c.execute(update(internal_instance_data).where(internal_instance_data.c.run_id == foreign_id).values(run_id=aid))
            c.execute(update(grants).where(grants.c.principal_id == inst['runtime_id'],
                grants.c.resource_id == resource).values(revoked=True))
            c.execute(delete(delivery_graph_requests).where(
                ((delivery_graph_requests.c.app_id == rid) & delivery_graph_requests.c.kind.in_([
                    'pa_spec_run_scope', 'pa_spec_run_scope_seal', use.META, use.META + '_seal']))
                | ((delivery_graph_requests.c.app_id == inst['id']) & delivery_graph_requests.c.kind.in_([
                    use.USE, use.USE + '_seal']))))
            binding = c.execute(select(internal_run_bindings.c.snapshot).where(internal_run_bindings.c.run_id == rid)).scalar_one()
            snap = copy.deepcopy(binding)
            snap.pop('pb_use')
            c.execute(update(internal_run_bindings).where(internal_run_bindings.c.run_id == rid).values(snapshot=snap))
        before = snapshot(data[0])
        with TypedPrivateBarrier(data[0], rid, aid, resource) as barrier:
            for path in [route + '/runs/' + rid + '/control-status', route,
                f"/api/internal/apps/{app['id']}/instances"]:
                response = client.get(path)
                assert response.status_code in (403, 409), response.text
            assert not barrier.blocked and not barrier.full_binding_reads
            checks.append(dict(fault='missing_all_hints', blocked=barrier.blocked, statements=barrier.statements))
        assert snapshot(data[0]) == before
    (tmp_path / 'corruption-proof.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2))
