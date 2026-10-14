"""Actual authenticated HTTP trial interface, SQLite synthetic only."""

import copy

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from test_natural_live_admission import frozen, started
from test_natural_spec_apps import recipe, setup

from sim2act import natural_live_admission as gate
from sim2act.db import delivery_graph_requests, fingerprint, runs
from sim2act.errors import DomainError
from sim2act.natural_trial_api import ApprovalRequest


def prepare(env, pb=False):
    data = setup(env)
    contract, body = frozen(data)
    if pb:
        contract = gate.PBTrialContract(**contract.model_dump(), path="P-B",
            extraction_request_key="exact-pb-extraction", extraction_recipe=recipe("ordered"))
        body = body.model_copy(update={"expected_contract_fingerprint": fingerprint(contract.model_dump())})
    return data, contract, body


@pytest.mark.parametrize("pb", [False, True])
def test_http_exact_approval_recovery_revoke_and_identity(env, pb):
    data, contract, body = prepare(env, pb)
    store, _, client, user, pid = data[:5]
    path = f"/api/projects/{pid}/natural-trials/{contract.trial_key}"
    payload = dict(contract=contract.model_dump(), approval=body.model_dump())
    response = client.post(path + "/approval", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["live_allowed"] is False
    assert client.post(path + "/approval", json=payload).json() == response.json()
    with store.tx() as c:
        count = len(c.execute(select(delivery_graph_requests)).all())
        run_count = len(c.execute(select(runs)).all())
    read = path + "/approvals/" + body.request_key
    assert client.get(read).status_code == 200
    assert client.get(path + "/approvals/wrong-key").status_code == 409
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert client.get(read).status_code == 403
    assert client.post(path + "/approval", json=payload).status_code == 403
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    revoke = gate.RevokeInput(expected_contract_fingerprint=fingerprint(contract.model_dump()),
        request_key="only-original-revoke", consent="REVOKE_ONLY_THIS_EXACT_NATURAL_TRIAL")
    assert client.post(path + "/revocation", json=dict(contract=contract.model_dump(),
        revocation=revoke.model_dump())).json()["status"] == "REVOKED"
    assert client.get(read).json()["revoked"] is True
    assert client.post(path + "/approval", json=payload).status_code == 409
    with store.tx() as c:
        assert len(c.execute(select(delivery_graph_requests)).all()) == count + 2
        assert len(c.execute(select(runs)).all()) == run_count
    client.close()


@pytest.mark.parametrize("pb", [False, True])
def test_actual_claimed_generate_http_admission_denies_no_fee_override(env, pb):
    data, contract, body = prepare(env, pb)
    client, pid = data[2], data[4]
    path = f"/api/projects/{pid}/natural-trials/{contract.trial_key}"
    assert client.post(path + "/approval", json=dict(contract=contract.model_dump(),
        approval=body.model_dump())).status_code == 200
    job = started(data, contract)
    payload = dict(contract=contract.model_dump(), approval_key=body.request_key,
        stage="generate", run_id=job["id"], expected_version=job["version"], fence=job["fence"])
    with data[0].tx() as c:
        before = [dict(r) for r in c.execute(select(delivery_graph_requests)).mappings()]
    denied = client.post(path + "/admission", json=payload)
    assert denied.status_code == 400 and denied.json()["error"]["code"] == "LIVE_BLOCKED", denied.text
    for key in ("fee_authority", "free", "live_allowed"):
        extra = copy.deepcopy(payload)
        extra[key] = True
        assert client.post(path + "/admission", json=extra).status_code == 422
    with data[0].tx() as c:
        assert [dict(r) for r in c.execute(select(delivery_graph_requests)).mappings()] == before
    client.close()


def test_pb_contract_required_exact_recipe_key_and_old_pa_shape(env):
    data, pa, _ = prepare(env)
    assert "path" not in pa.model_dump() and "extraction_recipe" not in pa.model_dump()
    base = dict(pa.model_dump(), path="P-B", extraction_request_key="pb-extract",
                extraction_recipe=recipe("ordered"))
    parsed = ApprovalRequest(contract=base, approval=dict(
        expected_contract_fingerprint=fingerprint(base), request_key="approval", consent=gate.CONSENT))
    assert isinstance(parsed.contract, gate.PBTrialContract)
    for field in ("extraction_recipe", "extraction_request_key"):
        bad = copy.deepcopy(base)
        del bad[field]
        with pytest.raises(ValidationError):
            gate.PBTrialContract.model_validate(bad)
    bad = copy.deepcopy(base)
    bad["extraction_request_key"] = pa.stage_keys.source
    with pytest.raises(DomainError):
        gate.PBTrialContract.model_validate(bad)
    data[2].close()


def test_original_http_read_denies_revoked_resource_before_private_pair(env, monkeypatch):
    from sqlalchemy import update

    from sim2act.db import grants

    data, contract, body = prepare(env)
    client = data[2]
    path = f"/api/projects/{data[4]}/natural-trials/{contract.trial_key}"
    assert client.post(path + "/approval", json=dict(contract=contract.model_dump(),
        approval=body.model_dump())).status_code == 200
    with data[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == contract.bindings[0].resource_id)
                  .values(revoked=True))
    reads = []
    original = gate._saved

    def observed(*args):
        reads.append(True)
        return original(*args)

    monkeypatch.setattr(gate, "_saved", observed)
    response = client.get(path + "/approvals/" + body.request_key)
    assert response.status_code == 403 and not reads
    data[2].close()
