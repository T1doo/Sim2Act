"""Authenticated real journal metadata, explicit offline SQLite producer, no LIVE authority."""

import time

from sqlalchemy import select
from test_natural_live_admission import started
from test_natural_trial_api import prepare

from sim2act import natural_trial_budget as old_budget
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import production_trial_journal as journal
from sim2act import production_trial_policy as policy
from sim2act.db import delivery_graph_requests, fingerprint, new_id


def test_production_reader_never_seeds_or_falls_back_and_keeps_false_authority(env):
    data, contract, approval = prepare(env, pb=True)
    contract = contract.model_copy(
        update={"quota_subject": admission.canonical_quota_subject(evidence.ACCOUNT_ID)}
    )
    approval = approval.model_copy(
        update={"expected_contract_fingerprint": fingerprint(contract.model_dump())}
    )
    store, _, client, user, pid = data[:5]
    base = f"/api/projects/{pid}/natural-trials/{contract.trial_key}"
    assert (
        client.post(
            base + "/approval",
            json=dict(contract=contract.model_dump(), approval=approval.model_dump()),
        ).status_code
        == 200
    )
    route = base + "/approvals/" + approval.request_key + "/production-journal"
    with store.tx() as c:
        before = list(c.execute(select(delivery_graph_requests)).mappings())
    missing = client.get(route)
    assert missing.status_code == 400 and missing.json()["error"]["code"] == "OUTCOME_UNKNOWN"
    with store.tx() as c:
        assert before == list(c.execute(select(delivery_graph_requests)).mappings())
    job = started(data, contract)
    scope = evidence.requirements_for(user, contract, approval.request_key)
    synthetic_source = policy.SourceVerificationResult(
        requirements_fingerprint=fingerprint(scope.model_dump()),
        account_id=evidence.ACCOUNT_ID,
        quota_subject=scope.quota_subject,
        provider=scope.provider,
        model=scope.model,
        endpoint=scope.endpoint,
        evidence_fingerprint="a" * 64,
        decision="ALLOW",
        legal_free_entitlement=True,
        enforced_non_chargeable=True,
        revoked=False,
        observed_at=time.time(),
        expires_at=contract.expires_at,
    )
    with store.tx() as c:
        context = policy.check_run(
            store,
            c,
            user,
            contract,
            approval.request_key,
            "generate",
            job["id"],
            job["version"],
            job["fence"],
            job["worker_id"],
        )
    wire = b'{"offline_metadata_only":true}'
    identity = policy.identity_for(context, synthetic_source, new_id("attempt"), wire)
    journal.reserve(
        store,
        user,
        contract,
        approval.request_key,
        identity,
        wire,
        synthetic_source,
        expected_revision=0,
    )
    with store.tx() as c:
        before = list(c.execute(select(delivery_graph_requests)).mappings())
    response = client.get(route)
    assert response.status_code == 200, response.text
    value = response.json()
    assert (
        value["live_allowed"]
        is value["dispatch_authorized"]
        is value["real_source_verified"]
        is False
    )
    assert value["ledger"]["scope"] == scope.model_dump() and len(value["ledger"]["slots"]) == 1
    assert value["ledger"]["slots"][0]["settlement"] is None
    with store.tx() as c:
        assert before == list(c.execute(select(delivery_graph_requests)).mappings())
        assert not c.execute(
            select(delivery_graph_requests).where(delivery_graph_requests.c.kind == old_budget.KIND)
        ).first()
    client.headers["Authorization"] = "Bearer synthetic-test-B"
    assert client.get(route).status_code == 403
    client.close()
