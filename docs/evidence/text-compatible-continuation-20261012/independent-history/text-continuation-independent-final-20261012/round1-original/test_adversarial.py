"""Read-only product review; every fault writes only its own copied /tmp DB."""
import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import event, select, update

from test_text_continuations import continued, legacy, path, rows
from sql_private_barrier import PrivateReadBarrier
from sim2act import text_continuations as cont
from sim2act.db import app_drafts, grants, internal_approvals, internal_releases, task_extractions
from sim2act.errors import DomainError

EVIDENCE = Path('/tmp/text-continuation-independent-final-20261012/adversarial')


def save(info, name, value):
    EVIDENCE.mkdir(exist_ok=True)
    stem = ('a747' if info.get('goal') else '233') + '-' + name
    (EVIDENCE / (stem + '.json')).write_text(json.dumps(value, default=str, indent=2) + '\n')


def protected(store, ids):
    b = PrivateReadBarrier(store, set())
    b.rules['internal_approvals'] = (internal_approvals, 'id', set(ids), {'payload'})
    return b


def test_discriminator_stripped_revoked_target_no_private_projection(legacy):
    store, _, client, info = legacy
    approval, _, _, receipt = continued(legacy)
    with store.tx() as c:
        row = c.execute(select(task_extractions).where(task_extractions.c.app_id == info['app']['id'])).mappings().one()
        snapshot = copy.deepcopy(row['snapshot']); snapshot.pop('kind')
        c.execute(update(task_extractions).where(task_extractions.c.app_id == info['app']['id']).values(snapshot=snapshot))
        c.execute(update(grants).where(grants.c.principal_id == info['owner'], grants.c.resource_id == info['resource']).values(revoked=True))
        release_approval = c.execute(select(internal_releases.c.approval_id).where(internal_releases.c.id == receipt['release_id'])).scalar_one()
    before = rows(store)
    b = protected(store, {info['logic']['id'], approval['approval_id']})
    calls, projections = [], []
    private = {'app_drafts': {'candidate'}, 'internal_approvals': {'payload'},
               'internal_releases': {'snapshot'}, 'runs': {'context', 'result', 'goal'},
               'internal_run_bindings': {'snapshot'}}
    def capture(_c, _cursor, sql, params, context, _many):
        statement = getattr(getattr(context, 'compiled', None), 'statement', None)
        names = []
        for col in getattr(statement, 'selected_columns', []):
            table = getattr(getattr(col, 'table', None), 'name', None)
            if table in private and getattr(col, 'name', None) in private[table]:
                names.append(table + '.' + col.name)
        if names:
            projections.append({'path': current[0], 'columns': names, 'sql': sql, 'params': repr(params)})
    current = ['']
    event.listen(store.engine, 'before_cursor_execute', capture)
    try:
        with b:
            urls = ['/api/apps/' + info['app']['id'],
                    '/api/internal/releases/' + receipt['release_id'],
                    '/api/internal/approvals/' + release_approval,
                    path(info) + '?request_key=exact-commit',
                    '/api/internal/apps/' + info['app']['id'] + '/releases']
            for url in urls:
                current[0] = url
                response = client.get(url)
                calls.append({'path': url, 'status': response.status_code, 'body': response.json()})
    finally:
        event.remove(store.engine, 'before_cursor_execute', capture)
        save(info, 'stripped-revoked', {'calls': calls, 'full_private_projections': projections,
                                       'barrier': b.blocked, 'evaluated_cells': b.evaluated, 'sql': b.statements})
    assert rows(store) == before
    assert all(r['status'] == 403 for r in calls), calls
    assert not b.blocked
    assert not projections, projections


def test_foreign_release_approval_deny_before_private_cell(legacy):
    store, _, client, info = legacy
    approval, _, _, receipt = continued(legacy)
    with store.tx() as c:
        release_approval = c.execute(select(internal_releases.c.approval_id).where(internal_releases.c.id == receipt['release_id'])).scalar_one()
    store.user('Independent foreign synthetic reviewer', 'independent-foreign-token')
    before = rows(store)
    b = protected(store, {info['logic']['id'], approval['approval_id'], release_approval})
    b.rules['internal_releases'] = (internal_releases, 'id', {receipt['release_id']}, {'snapshot'})
    calls = []
    try:
        client.headers['Authorization'] = 'Bearer independent-foreign-token'
        with b:
            for url in ['/api/internal/releases/' + receipt['release_id'],
                        '/api/internal/approvals/' + release_approval,
                        '/api/internal/approvals/' + approval['approval_id'],
                        path(info) + '?request_key=exact-commit']:
                r = client.get(url);calls.append({'path': url, 'status': r.status_code})
    finally:
        client.headers['Authorization'] = 'Bearer synthetic-test-A'
        save(info, 'foreign', {'calls': calls, 'barrier': b.blocked, 'evaluated_cells': b.evaluated, 'sql': b.statements})
    assert all(r['status'] == 403 for r in calls), calls
    assert not b.blocked and rows(store) == before


def test_unknown_authority_implementation_denies_preflight_zero_writes(legacy):
    store, _, client, info = legacy
    with store.tx() as c:
        a = c.execute(select(internal_approvals).where(internal_approvals.c.id == info['logic']['id'])).mappings().one()
        p = copy.deepcopy(a['payload']);p['implementation_fingerprint'] = '0' * 64
        c.execute(update(internal_approvals).where(internal_approvals.c.id == a['id']).values(payload=p))
    before = rows(store)
    chosen = next(x for x in client.get('/api/projects/' + info['project'] + '/software-continuation-options').json()['items']
                  if x['id'] == info['instance']['id'])
    request = dict(expected_revision=chosen['revision'], expected_release_fingerprint=chosen['release_fingerprint'],
                   expected_candidate_fingerprint=chosen['fingerprint'], expected_source_implementation='0' * 64,
                   input={'term': 'Alpha'}, request_key='independent-unknown-software')
    r = client.post(path(info).replace('software-continuations', 'software-continuation-preflights'), json=request)
    save(info, 'unknown', {'status': r.status_code, 'body': r.json(), 'fault': 'unknown AUTH implementation marker only; seals not re-signed'})
    assert r.status_code == 409 and r.json()['error']['code'] == 'UNSUPPORTED_CAPABILITY', r.text
    assert rows(store) == before


def test_known_kernel_changed_bytes_fault_denied_without_source_edit(legacy, monkeypatch):
    store, _, _, info = legacy
    before = rows(store)
    original = Path.read_bytes
    def changed(p):
        b = original(p)
        return b + b'\n# independent hash-only fault injection\n' if p.name == 'text_apps.py' else b
    with monkeypatch.context() as m:
        m.setattr(Path, 'read_bytes', changed)
        with pytest.raises(DomainError) as e:
            cont.known(info['software_fp'])
        assert e.value.code == 'VERSION_CONFLICT'
    save(info, 'kernel', {'code': e.value.code, 'message': str(e.value), 'fault': 'Path.read_bytes simulated kernel difference; actual source untouched'})
    assert rows(store) == before


def test_private_cell_barrier_calibration_rejects_unconditional_auth_payload(legacy):
    store, _, _, info = legacy
    b = protected(store, {info['logic']['id']})
    try:
        with b, store.tx() as c:
            with pytest.raises(Exception):
                c.execute(select(internal_approvals.c.payload)).all()
    finally:
        save(info, 'calibration', {'blocked': b.blocked, 'evaluated_cells': b.evaluated, 'sql': b.statements})
    assert any(x.get('row_id') == info['logic']['id'] and x.get('column') == 'payload' for x in b.blocked)
