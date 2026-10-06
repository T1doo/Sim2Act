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
    assert {"protocol_jobs", "protocol_reviews"} <= set(inspect(store.engine).get_table_names())
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
