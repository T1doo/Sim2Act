"""Irreversible original-key closure, tested through authenticated actual HTTP."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import delete, select
from test_natural_trial_preparation import prepared_data, scope, consent, business  # noqa: F401
from sim2act import natural_live_admission as gate
from sim2act import natural_trial_preparation as prep
from sim2act.db import delivery_graph_requests


def test_close_after_goal_revision_blocks_old_contract(prepared_data, tmp_path):
    data, _, base, r = scope(prepared_data)
    store, client, card = data[0], data[2], data[6]
    before = business(store)
    revised = client.put('/api/goal-cards/' + card['id'], json=dict(card['content'], goal=card['content']['goal']+' revised', expected_version=card['version']))
    assert revised.status_code == 200
    assert client.post(base+'/consent', json=consent(r)).status_code == 409
    assert client.get(base+'/consent-status').json()['status'] == 'PREPARED_NOT_APPROVED'
    closed = client.post(base+'/end-preparation', json={'confirm_end':True})
    assert closed.status_code == 200, closed.text
    assert closed.json()['status'] == 'PREPARATION_CLOSED_NO_APPROVAL'
    assert client.post(base+'/end-preparation', json={'confirm_end':True}).json() == closed.json()
    assert client.get(base+'/consent-status').json() == closed.json()
    old = client.post(base+'/approval', json=dict(contract=r['contract'], approval=dict(expected_contract_fingerprint=r['review_token'], request_key=prep.approval_key(gate.parse_contract(r['contract'])), consent='APPROVE_ONLY_THIS_EXACT_SEVEN_SLOT_ZERO_PAID_NATURAL_TRIAL')))
    assert old.status_code == 409 and 'closed' in old.text.lower(), old.text
    assert business(store) == before
    (tmp_path/'CLOSE_HTTP.json').write_text(json.dumps(dict(closed=closed.json(), old=old.json(), no_business_change=True),indent=2))


def test_close_fences_inflight_approval(prepared_data, monkeypatch, tmp_path):
    data, _, base, r = scope(prepared_data)
    client, store = data[2], data[0]
    entered, release = threading.Event(), threading.Event()
    original = gate.approve
    def paused(*a, **kw):
        entered.set()
        assert release.wait(10)
        return original(*a, **kw)
    monkeypatch.setattr(gate, 'approve', paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, base+'/consent', json=consent(r))
        try:
            assert entered.wait(10)
            closed = client.post(base+'/end-preparation', json={'confirm_end':True})
            assert closed.status_code == 200, closed.text
        finally: release.set()
        late = pending.result(10)
    assert late.status_code == 409 and 'closed' in late.text.lower(), late.text
    with store.tx() as c:
        assert not c.execute(select(delivery_graph_requests.c.request_key).where(delivery_graph_requests.c.kind.in_([gate.SCOPE,gate.APPROVE]))).first()
    (tmp_path/'RACE_HTTP.json').write_text(json.dumps(dict(close=closed.json(), late=late.json()),indent=2))


def test_approval_wins_close_refuses(prepared_data):
    data, _, base, r=scope(prepared_data)
    client=data[2]
    assert client.post(base+'/consent',json=consent(r)).status_code==200
    assert client.post(base+'/end-preparation',json={'confirm_end':True}).status_code==409
    assert client.get(base+'/preparation').json()['approved'] is True


@pytest.mark.parametrize('missing', ['preparation','seal'])
def test_partial_preparation_cannot_close(prepared_data, missing):
    data, _, base, _=scope(prepared_data)
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind == prep.PREPARE+('_seal' if missing=='seal' else '')))
    assert data[2].post(base+'/end-preparation',json={'confirm_end':True}).status_code in (400,409)


@pytest.mark.parametrize('missing', ['closed', 'seal'])
def test_partial_close_never_reopens(prepared_data, missing):
    data, _, base, r=scope(prepared_data)
    client=data[2]
    assert client.post(base+'/end-preparation',json={'confirm_end':True}).status_code==200
    with data[0].tx() as c:
        c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind == gate.CLOSED+('_seal' if missing=='seal' else '')))
    assert client.get(base+'/consent-status').status_code==409
    assert client.get(base+'/preparation').status_code==409
    assert client.post(base+'/end-preparation',json={'confirm_end':True}).status_code==409
    assert client.post(base+'/consent',json=consent(r)).status_code==409


def test_close_transaction_failure_has_no_partial_writes(prepared_data, monkeypatch):
    data, _, base, r=scope(prepared_data)
    original=gate._save
    def fail(*args):
        original(*args)
        raise ValueError('controlled close transaction failure after paired writes')
    monkeypatch.setattr(gate, '_save', fail)
    assert data[2].post(base+'/end-preparation',json={'confirm_end':True}).status_code==409
    assert data[2].get(base+'/consent-status').json()['status']=='PREPARED_NOT_APPROVED'
    monkeypatch.setattr(gate, '_save', original)
    assert data[2].post(base+'/consent',json=consent(r)).status_code==200


def test_close_requires_fresh_authority_and_explicit_strict_confirmation(prepared_data, monkeypatch):
    from sqlalchemy import update
    from sim2act.db import grants
    data, _, base, _=scope(prepared_data)
    store,client=data[0],data[2]
    for body in ({}, {'confirm_end':False}, {'confirm_end':True,'live_allowed':True}):
        assert client.post(base+'/end-preparation',json=body).status_code==422
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id==data[5]).values(revoked=True))
    def forbidden(*a, **kw):raise AssertionError('Private preparation pair read before READ authorization')
    monkeypatch.setattr(prep,'pair',forbidden)
    assert client.post(base+'/end-preparation',json={'confirm_end':True}).status_code==403


def test_closed_recovery_is_metadata_only_after_read_revocation(prepared_data, monkeypatch):
    from sqlalchemy import update
    from sim2act.db import grants
    data, _, base, _=scope(prepared_data)
    store,client=data[0],data[2]
    closed=client.post(base+'/end-preparation',json={'confirm_end':True})
    assert closed.status_code==200
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id==data[5]).values(revoked=True))
    def forbidden(*a, **kw):raise AssertionError('Metadata recovery read private preparation')
    monkeypatch.setattr(prep,'pair',forbidden)
    for path in ('/preparation','/consent-status'):
        response=client.get(base+path)
        assert response.status_code==200 and response.json()==closed.json()
        assert 'contract' not in response.json()
    client.headers['Authorization']='Bearer synthetic-test-B'
    assert client.get(base+'/consent-status').status_code==403
