"""Explicit migration and least database role checks for isolated protocol records."""

import time

import pytest
from sqlalchemy import insert, inspect, select, text, update
from sqlalchemy.exc import DBAPIError

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, fingerprint, new_id, protocol_jobs, protocol_reviews


def test_api_construction_never_creates_protocol_tables(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "unmigrated.db"), test_only=True)
    assert not inspect(store.engine).get_table_names()
    create_app(store, Settings("unused", tmp_path))
    assert not inspect(store.engine).get_table_names()
    store.initialize()
    assert {
        "protocol_jobs",
        "protocol_reviews",
        "protocol_request_pools",
        "protocol_request_slots",
    } <= set(inspect(store.engine).get_table_names())
    store.engine.dispose()


def test_protocol_records_crud_under_existing_application_role(env, runtime_role):
    original, _, _, owner, _, project, _ = env
    store = Store(runtime_role)
    run, review = new_id("run"), new_id("review")
    snapshot = {"kind": "DATABASE_ROLE_CRUD_PROBE_ONLY"}
    with store.tx() as c:
        c.execute(
            insert(protocol_jobs).values(
                run_id=run,
                project_id=project,
                principal_id=owner,
                runtime_id=new_id("runtime"),
                kind="source",
                accepted_snapshot=snapshot,
                fingerprint=fingerprint(snapshot),
                created_at=time.time(),
            )
        )
        c.execute(
            update(protocol_jobs)
            .where(protocol_jobs.c.run_id == run)
            .values(
                result_snapshot=snapshot,
                result_fingerprint=fingerprint(snapshot),
                completed_fence=1,
            )
        )
        assert (
            c.execute(
                select(protocol_jobs.c.completed_fence).where(protocol_jobs.c.run_id == run)
            ).scalar()
            == 1
        )
        c.execute(
            insert(protocol_reviews).values(
                id=review,
                run_id=run,
                principal_id=owner,
                project_id=project,
                contract_id="CRUD_PROBE",
                payload=snapshot,
                fingerprint=fingerprint(snapshot),
                request_key="crud-only",
                created_at=time.time(),
            )
        )
        assert (
            c.execute(select(protocol_reviews.c.id).where(protocol_reviews.c.id == review)).scalar()
            == review
        )
    with pytest.raises(DBAPIError), store.tx() as c:
        c.execute(text("CREATE TABLE protocol_forbidden_ddl (id integer)"))
    with store.tx() as c:
        c.execute(protocol_reviews.delete().where(protocol_reviews.c.id == review))
        c.execute(protocol_jobs.delete().where(protocol_jobs.c.run_id == run))
    store.engine.dispose()


def test_shared_budget_tables_crud_use_business_role_and_deny_ddl(env, runtime_role):
    from sim2act.db import protocol_request_pools, protocol_request_slots

    store = Store(runtime_role)
    pid, aid = "crud-probe-pool", new_id("attempt")
    now = time.time()
    with store.tx() as c:
        c.execute(
            insert(protocol_request_pools).values(
                id=pid,
                mode="offline",
                request_limit=0,
                token_limit=0,
                reserved_requests=0,
                reserved_tokens=0,
                known_tokens=0,
                halted=True,
                halt_reason="CRUD_PROBE_ONLY",
                policy_fingerprint=fingerprint({"kind": "CRUD_PROBE_ONLY"}),
                version=1,
                created_at=now,
            )
        )
        c.execute(
            insert(protocol_request_slots).values(
                attempt_id=aid,
                pool_id=pid,
                ordinal=1,
                run_id="CRUD_PROBE_ONLY",
                fence=1,
                phase="source",
                request_fingerprint=fingerprint({}),
                reserved_tokens=0,
                status="STARTED",
                usage={"status": "unknown", "tokens": None},
                created_at=now,
            )
        )
        c.execute(
            update(protocol_request_pools)
            .where(protocol_request_pools.c.id == pid)
            .values(version=2)
        )
        c.execute(
            update(protocol_request_slots)
            .where(protocol_request_slots.c.attempt_id == aid)
            .values(status="UNKNOWN", error="CRUD_PROBE_ONLY")
        )
        assert (
            c.execute(
                select(protocol_request_pools.c.version).where(protocol_request_pools.c.id == pid)
            ).scalar_one()
            == 2
        )
        assert (
            c.execute(
                select(protocol_request_slots.c.status).where(
                    protocol_request_slots.c.attempt_id == aid
                )
            ).scalar_one()
            == "UNKNOWN"
        )
    with pytest.raises(DBAPIError), store.tx() as c:
        c.execute(text("CREATE TABLE protocol_pool_forbidden_ddl (id integer)"))
    with store.tx() as c:
        c.execute(protocol_request_slots.delete().where(protocol_request_slots.c.attempt_id == aid))
        c.execute(protocol_request_pools.delete().where(protocol_request_pools.c.id == pid))
    store.engine.dispose()
