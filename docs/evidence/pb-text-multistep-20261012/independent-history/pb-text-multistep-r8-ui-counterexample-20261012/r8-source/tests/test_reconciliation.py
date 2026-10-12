import json
import time

import pytest
from sqlalchemy import select, update

from sim2act.db import attempts, events, grants, operations, runs
from sim2act.errors import DomainError
from sim2act.model import MockModel
from sim2act.tools import definitions
from sim2act.worker import Worker


def lost_attempt(env):
    store, s, client, a, b, pid, res = env
    rid = store.submit(a, pid, "synthetic recoverable request", [res], "unknown")
    run = store.claim("lost-worker", 30)
    ctx = dict(run["context"])
    ctx["messages"] = [
        {"role": "user", "content": json.dumps({"goal": run["goal"], "resource_refs": [res]})}
    ]
    worker = Worker(store, s)
    aid = worker.reserve(rid, run["fence"], ctx)
    response = MockModel().request(ctx["messages"], definitions())
    with store.tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(lease_until=time.time() - 1))
    assert store.claim("recover", 30) is None
    version = client.get(f"/api/runs/{rid}").json()["version"]
    fp = client.get(f"/api/runs/{rid}/unresolved-attempts").json()[0]["request_fingerprint"]
    body = {
        "attempt_id": aid,
        "version": version,
        "decision": "record_response",
        "expected_fingerprint": fp,
        "evidence": "SYNTHETIC saved response fixture",
        "acknowledge_unknown_cost": True,
        "response": response,
    }
    return rid, aid, run, body


def test_AT06_import_is_audited_paused_and_requires_explicit_resume(env):
    store, s, client, a, b, pid, res = env
    rid, aid, old, body = lost_attempt(env)
    result = client.post(f"/api/runs/{rid}/reconcile", json=body)
    assert (
        result.status_code == 200
        and result.json()["status"] == "PAUSED"
        and result.json()["tools_dispatched"] == 0
    )
    with store.engine.connect() as c:
        assert not c.execute(select(operations).where(operations.c.run_id == rid)).first()
        row = c.execute(select(attempts).where(attempts.c.id == aid)).mappings().one()
        assert row["status"] == "RECONCILED_RESPONSE" and row["usage"]["status"] == "unknown"
        audit = c.execute(
            select(events.c.data).where(
                events.c.run_id == rid, events.c.kind == "ATTEMPT_RECONCILED"
            )
        ).scalar_one()
        assert audit["provenance"] == "USER_SUPPLIED" and audit["principal_id"] == a
    assert client.post(f"/api/runs/{rid}/reconcile", json=body).status_code == 409
    with pytest.raises(DomainError):
        Worker(store, s).finish(rid, old["fence"], "FAILED")
    v = client.get(f"/api/runs/{rid}").json()["version"]
    assert (
        client.post(
            f"/api/runs/{rid}/commands", json={"command": "resume", "version": v}
        ).status_code
        == 200
    )
    Worker(store, s).once()
    assert client.get(f"/api/runs/{rid}").json()["status"] == "PARTIAL"


@pytest.mark.parametrize(
    "mutation",
    [
        {"expected_fingerprint": "0" * 64},
        {"acknowledge_unknown_cost": False},
        {"evidence": " "},
        {"response": {"model": "gpt", "choices": []}},
        {
            "response": {
                "model": "MOCK-intern-contract",
                "choices": [
                    {"finish_reason": "length", "message": {"role": "assistant", "content": "half"}}
                ],
            }
        },
    ],
)
def test_reconcile_rejects_changed_unacknowledged_or_partial_evidence(env, mutation):
    store, s, client, a, b, pid, res = env
    rid, aid, old, body = lost_attempt(env)
    assert client.post(f"/api/runs/{rid}/reconcile", json=body | mutation).status_code == 400
    assert client.get(f"/api/runs/{rid}").json()["status"] == "WAITING_RESOURCE"
    with store.engine.connect() as c:
        assert (
            c.execute(select(attempts.c.status).where(attempts.c.id == aid)).scalar_one()
            == "STARTED"
        )


def test_AT04_other_subject_cannot_inspect_or_resolve_unknown(env):
    rid, aid, old, body = lost_attempt(env)
    client = env[2]
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert client.get(f"/api/runs/{rid}/unresolved-attempts").status_code == 403
    assert client.post(f"/api/runs/{rid}/reconcile", json=body).status_code == 403


def test_AT08_import_rechecks_revocation_but_owner_can_close_unknown_cost(env):
    store, s, client, a, b, pid, res = env
    rid, aid, old, body = lost_attempt(env)
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == res).values(revoked=True))
    assert client.post(f"/api/runs/{rid}/reconcile", json=body).status_code == 403
    closed = client.post(
        f"/api/runs/{rid}/reconcile", json=body | {"decision": "close_unknown", "response": None}
    )
    assert closed.status_code == 200 and closed.json()["status"] == "CANCELLED"
    assert closed.json()["usage"]["status"] == "unknown"
    assert client.get(f"/api/runs/{rid}/unresolved-attempts").json() == []
    assert Worker(store, s).once() is False


def test_raw_response_duplicate_keys_are_rejected(env):
    rid, aid, old, body = lost_attempt(env)
    raw = '{"model":"MOCK-intern-contract","model":"gpt","choices":[]}'
    assert (
        env[2]
        .post(f"/api/runs/{rid}/reconcile", json=body | {"response": None, "response_json": raw})
        .status_code
        == 400
    )


def test_cancel_intent_is_not_reversed_by_import(env):
    store, s, client, a, b, pid, res = env
    rid, aid, old, body = lost_attempt(env)
    cancellation = client.post(
        f"/api/runs/{rid}/commands", json={"command": "cancel", "version": body["version"]}
    )
    assert cancellation.json()["status"] == "RECONCILING"
    body["version"] += 1
    imported = client.post(f"/api/runs/{rid}/reconcile", json=body)
    assert imported.status_code == 200 and imported.json()["status"] == "CANCELLED"
    assert Worker(store, s).once() is False


def test_reconciliation_cannot_mark_unknown_tool_effect_as_known(env):
    from sqlalchemy import insert

    from sim2act.db import new_id

    store, s, client, a, b, pid, res = env
    rid, aid, old, body = lost_attempt(env)
    with store.tx() as c:
        c.execute(
            insert(operations).values(
                id=new_id("op"), run_id=rid, call_id="synthetic-unknown", status="OUTCOME_UNKNOWN"
            )
        )
    assert (
        client.post(
            f"/api/runs/{rid}/reconcile",
            json=body | {"decision": "close_unknown", "response": None},
        ).json()["error"]["code"]
        == "OUTCOME_UNKNOWN"
    )
