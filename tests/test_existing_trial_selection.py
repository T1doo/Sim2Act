"""Actual authenticated existing-scope recovery; synthetic SQLite, no PG/LIVE."""

import pytest
from sqlalchemy import select
from test_natural_trial_api import prepare

from sim2act import natural_live_admission as gate
from sim2act.db import delivery_graph_requests, fingerprint, runs
from sim2act.production_evidence import ACCOUNT_ID
from sim2act.production_trial_admission import canonical_quota_subject


@pytest.mark.parametrize("pb", [False, True])
@pytest.mark.parametrize("configured", [False, True])
def test_existing_original_approval_exports_only_metadata_and_never_rebinds(env, pb, configured):
    data, contract, body = prepare(env, pb)
    if configured:
        contract = contract.model_copy(
            update={"quota_subject": canonical_quota_subject(ACCOUNT_ID)}
        )
        body = body.model_copy(
            update={"expected_contract_fingerprint": fingerprint(contract.model_dump())}
        )
    client, pid = data[2], data[4]
    base = f"/api/projects/{pid}/natural-trials/{contract.trial_key}"
    approved = client.post(
        base + "/approval", json=dict(contract=contract.model_dump(), approval=body.model_dump())
    )
    assert approved.status_code == 200, approved.text
    with data[0].tx() as c:
        before = [dict(r) for r in c.execute(select(delivery_graph_requests)).mappings()]
    path = base + f"/approvals/{body.request_key}/worker-selection"
    response = client.get(path)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["path"] == ("P-B" if pb else "P-A")
    assert (
        value["live_allowed"] is False
        and value["actual_model_requests"] == value["new_runs"] == value["new_slots"] == 0
    )
    assert value["contract_fingerprint"] == fingerprint(contract.model_dump())
    if configured:
        assert value["worker_selection"] == dict(
            user=data[3],
            project=pid,
            trial=contract.trial_key,
            approval=body.request_key,
            account=ACCOUNT_ID,
        )
    else:
        assert (
            value["worker_selection"] is None
            and value["selection_blocked_reason"] == "ORIGINAL_SCOPE_NOT_CONFIGURED_ACCOUNT"
        )
    assert client.get(path).json() == value
    with data[0].tx() as c:
        assert before == [dict(r) for r in c.execute(select(delivery_graph_requests)).mappings()]
        assert not c.execute(select(runs)).first()
    assert client.get(path.replace(body.request_key, "wrong-key")).status_code == 409
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert client.get(path).status_code == 403
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    revocation = gate.RevokeInput(
        expected_contract_fingerprint=fingerprint(contract.model_dump()),
        request_key="explicit-existing-revoke",
        consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL",
    )
    assert (
        client.post(
            base + "/revocation",
            json=dict(contract=contract.model_dump(), revocation=revocation.model_dump()),
        ).status_code
        == 200
    )
    assert client.get(path).status_code == 409
    client.close()
