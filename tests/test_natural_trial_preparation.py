"""Authenticated preparation/consent only: no Run, reservation or sender authority."""

import copy
import json
import time

import pytest
from sqlalchemy import select, update
from test_natural_spec_apps import COLD, material, setup

from sim2act import natural_live_admission as gate
from sim2act import natural_trial_preparation as prep
from sim2act.db import attempts, delivery_graph_requests, grants, runs


@pytest.fixture
def prepared_data(env, monkeypatch):
    data = setup(env)
    store, _, client, user, pid = data[:5]
    _, cold_card = material(client, pid, COLD)
    with store.tx() as c:
        project = store.own_project(c, user, pid)
        store.add_grants(c, user, project["runtime_id"], pid, pid, ["artifact.save_text"])
    body = dict(bindings=[dict(card_id=card["id"], expected_version=card["version"])
                         for card in (data[6], cold_card)])
    import httpx

    def no_external_http(*args, **kwargs):
        raise AssertionError('Preparation and consent must never make external HTTP calls')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', no_external_http)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', no_external_http)
    yield data, body
    client.close()


def business(store):
    with store.tx() as c:
        return dict(runs=[dict(r) for r in c.execute(select(runs)).mappings()],
                    attempts=[dict(r) for r in c.execute(select(attempts)).mappings()],
                    ledger=[dict(r) for r in c.execute(select(delivery_graph_requests).where(
                        ~delivery_graph_requests.c.kind.in_([prep.PREPARE, prep.PREPARE + "_seal",
                            gate.SCOPE, gate.SCOPE + "_seal", gate.APPROVE, gate.APPROVE + "_seal",
                            gate.REVOKE, gate.REVOKE + "_seal", gate.CLOSED, gate.CLOSED + "_seal"]))).mappings()])


def scope(prepared_data, key="original-preparation"):
    data, body = prepared_data
    base = f"/api/projects/{data[4]}/natural-trials/{key}"
    result = data[2].post(base + "/preparation", json=body)
    assert result.status_code == 200, result.text
    return data, body, base, result.json()


def consent(receipt):
    return dict(review_token=receipt["review_token"], confirm_exact_scope=True)


def test_server_contract_exact_consent_duplicate_cold_recover_and_withdraw(prepared_data, tmp_path):
    data, body = prepared_data
    client, store = data[2], data[0]
    before = business(store)
    data, body, base, r = scope(prepared_data)
    assert r["contract"]["caps"] == gate.TrialCaps().model_dump()
    assert len(r["contract"]["bindings"]) == 2
    assert r["approved"] is False and r["live_allowed"] is False
    assert r == client.post(base + "/preparation", json=body).json()
    approved = client.post(base + "/consent", json=consent(r))
    assert approved.status_code == 200, approved.text
    assert client.post(base + "/consent", json=consent(r)).json() == approved.json()
    recovered = client.get(base + "/preparation").json()
    assert recovered["approved"] is True and not recovered["revoked"]
    assert recovered["contract"] == r["contract"]
    withdrawn = client.post(base + "/withdrawal", json=dict(review_token=r["review_token"], confirm_withdrawal=True))
    assert withdrawn.status_code == 200 and withdrawn.json()["status"] == "REVOKED"
    assert client.get(base + "/preparation").json()["revoked"] is True
    assert client.post(base + "/consent", json=consent(r)).status_code == 409
    assert business(store) == before
    (tmp_path / "HTTP_RECEIPTS.json").write_text(json.dumps(dict(prepared=r, approved=approved.json(),
        recovered=recovered, withdrawn=withdrawn.json(), business_unchanged=True), indent=2))


@pytest.mark.parametrize("drift", ["goal", "resource", "permission", "identity", "project", "software", "expiry"])
def test_exact_drift_refuses_consent_without_partial_approval(prepared_data, monkeypatch, drift, tmp_path):
    data, _, base, r = scope(prepared_data)
    store, client = data[0], data[2]
    before = business(store)
    if drift == "goal":
        card = data[6]
        changed = copy.deepcopy(card["content"])
        changed["goal"] += " Changed"
        assert client.put(f"/api/goal-cards/{card['id']}", json=dict(changed, expected_version=card["version"])).status_code == 200
    elif drift == "resource":
        from sim2act.db import resources
        with store.tx() as c:
            c.execute(update(resources).where(resources.c.id == data[5]).values(hash="f" * 64))
    elif drift == "permission":
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
    elif drift == "identity":
        client.headers["Authorization"] = "Bearer synthetic-test-B"
    elif drift == "project":
        pid = client.post("/api/projects", json={"name": "other"}).json()["id"]
        base = base.replace(data[4], pid)
    elif drift == "software":
        monkeypatch.setattr(gate, "implementation", lambda: "e" * 64)
    else:
        at = time.time() + 301
        monkeypatch.setattr(gate.time, "time", lambda: at)
        read = client.get(base + "/preparation")
        assert read.json()["expired"] is True
        assert read.json()["contract"] == r["contract"]
    response = client.post(base + "/consent", json=consent(r))
    assert response.status_code == ({"resource": 400, "project": 400, "permission": 403, "identity": 403}.get(drift, 409)), response.text
    if drift in ("resource", "project"):
        assert response.json()["error"]["code"] == {"resource": "VERIFICATION_FAILED", "project": "OUTCOME_UNKNOWN"}[drift]
    with store.tx() as c:
        assert not c.execute(select(delivery_graph_requests).where(delivery_graph_requests.c.kind == gate.APPROVE)).first()
    assert business(store) == before
    (tmp_path / "HTTP_REFUSAL.json").write_text(json.dumps(dict(drift=drift,status=response.status_code, response=response.json(), no_partial_approval=True)))


def test_unknown_original_key_and_changed_key_scope_never_create(prepared_data):
    data, body, base, r = scope(prepared_data)
    client = data[2]
    before = business(data[0])
    changed = copy.deepcopy(body)
    changed["bindings"].reverse()
    assert client.post(base + "/preparation", json=changed).status_code == 409
    assert client.post(base + "/consent", json=dict(review_token="f"*64,confirm_exact_scope=True)).status_code == 409
    missing = client.get(base.replace("original-preparation", "missing-key") + "/preparation")
    assert missing.status_code == 400 and missing.json()["error"]["code"] == "OUTCOME_UNKNOWN"
    for extra in ("live_allowed", "fee_authority", "caps", "contract", "software_fingerprint"):
        assert client.post(base + "/preparation", json=dict(body, **{extra: True})).status_code == 422
        assert client.post(base + "/consent", json=dict(consent(r), **{extra: True})).status_code == 422
    assert client.post(base + "/consent", json=dict(review_token=r["review_token"], confirm_exact_scope=False)).status_code == 422
    assert business(data[0]) == before


def test_revoke_after_permission_removed_is_metadata_only_and_read_gated(prepared_data, monkeypatch):
    data, _, base, r = scope(prepared_data)
    store, client = data[0], data[2]
    assert client.post(base + "/consent", json=consent(r)).status_code == 200
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
    reads = []
    original = prep.pair
    monkeypatch.setattr(prep, "pair", lambda *a, **kw: (reads.append(True), original(*a, **kw))[1])
    assert client.get(base + "/preparation").status_code == 403 and not reads
    metadata = client.get(base + "/consent-status")
    assert metadata.status_code == 200 and metadata.json()["approved"]
    withdraw = dict(review_token=metadata.json()["review_token"], confirm_withdrawal=True)
    assert client.post(base + "/withdrawal", json=withdraw).status_code == 200
    assert client.post(base + "/withdrawal", json=withdraw).status_code == 200
    assert client.get(base + "/consent-status").json()["revoked"] is True
    assert not reads and business(store)["runs"] == business(store)["attempts"] == []


@pytest.mark.parametrize("missing", [None, prep.PREPARE, prep.PREPARE + "_seal"])
def test_duplicate_prepare_revoked_or_partial_pair_never_reads_private_body(prepared_data, missing):
    from sqlalchemy import delete, event

    data, body, base, _ = scope(prepared_data)
    store, client = data[0], data[2]
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == data[5]).values(revoked=True))
        if missing:
            c.execute(delete(delivery_graph_requests).where(delivery_graph_requests.c.kind == missing))
    private_reads = []

    def observe(conn, clauseelement, multiparams, params, execution_options):
        if any(column is delivery_graph_requests.c.snapshot
               for column in getattr(clauseelement, 'selected_columns', [])):
            private_reads.append(True)

    event.listen(store.engine, 'before_execute', observe)
    try:
        response = client.post(base + '/preparation', json=body)
        assert response.status_code == (400 if missing == prep.PREPARE else 403), response.text
        assert not private_reads
    finally:
        event.remove(store.engine, 'before_execute', observe)


def test_prepare_write_failure_rolls_back_all_paired_metadata(prepared_data, monkeypatch):
    data, body = prepared_data
    store, client = data[0], data[2]
    before = business(store)
    original = prep.remember

    def broken(*args):
        original(*args)
        raise ValueError('controlled failure after both preparation writes')

    monkeypatch.setattr(prep, 'remember', broken)
    response = client.post(f'/api/projects/{data[4]}/natural-trials/rolled-back/preparation', json=body)
    assert response.status_code == 409
    with store.tx() as c:
        assert not c.execute(select(delivery_graph_requests.c.request_key).where(
            delivery_graph_requests.c.kind.in_([prep.PREPARE, prep.PREPARE + '_seal']))).first()
    assert business(store) == before
