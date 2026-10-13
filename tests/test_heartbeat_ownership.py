"""Lease renewal cannot cross expiry or another worker's ownership interval."""
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from test_foundation import enqueue

from sim2act import db
from sim2act.db import runs
from sim2act.errors import DomainError


@pytest.mark.parametrize("fault", ["elapsed", "wrong-worker"])
def test_heartbeat_final_write_requires_live_original_ownership(env, monkeypatch, fault):
    store = env[0]
    rid = enqueue(env, "heartbeat-final-" + fault)
    run = store.claim("original-worker", 30)
    now = [run["lease_until"] - 1]
    monkeypatch.setattr(db, "time", SimpleNamespace(time=lambda: now[0]))
    original = store.guard

    def delayed_guard(c, run_id, fence):
        value = original(c, run_id, fence)
        if fault == "elapsed":
            now[0] = value["lease_until"]
        return value

    monkeypatch.setattr(store, "guard", delayed_guard)
    with pytest.raises(DomainError, match="Heartbeat ownership"):
        store.heartbeat("original-worker" if fault == "elapsed" else "other-worker",
                        rid, run["fence"], 30)
    with store.tx() as c:
        saved = c.execute(select(runs.c.lease_until, runs.c.worker_id, runs.c.fence)
                          .where(runs.c.id == rid)).mappings().one()
    assert saved == {"lease_until": run["lease_until"], "worker_id": "original-worker",
                     "fence": run["fence"]}


def test_live_heartbeat_extends_only_same_interval(env):
    store = env[0]
    rid = enqueue(env, "heartbeat-valid")
    run = store.claim("original-worker", 30)
    store.heartbeat("original-worker", rid, run["fence"], 30)
    with store.tx() as c:
        saved = c.execute(select(runs.c.lease_until, runs.c.worker_id, runs.c.fence)
                          .where(runs.c.id == rid)).mappings().one()
    assert saved["lease_until"] > run["lease_until"]
    assert saved["worker_id"] == "original-worker" and saved["fence"] == run["fence"]


def test_authority_refresh_detects_expiry_without_a_write(env, monkeypatch):
    from sim2act.db import grants

    store, _, _, user, _, project, resource = env
    clock = [100.0]
    monkeypatch.setattr(db, "time", SimpleNamespace(time=lambda: clock[0]))
    with store.tx() as c:
        runtime = store.own_project(c, user, project)["runtime_id"]
        c.execute(db.update(grants).where(grants.c.resource_id == resource)
                  .values(expires_at=101.0))
        with store.proof_authorities(c) as authorities:
            store.authorize(c, user, runtime, project, resource, "resource.read")
        proof = {"_call_authorities": tuple(authorities)}
        epoch = c.info["source_proof_write_epoch"]
        clock[0] = 101.0
        with pytest.raises(DomainError, match="GRANT_REVOKED"):
            store.recheck_proof_authorities(c, proof)
        assert c.info["source_proof_write_epoch"] == epoch
