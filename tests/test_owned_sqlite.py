"""Private creator/schema/cache qualification; zero model/Worker execution."""
# ruff: noqa: F811

import sqlite3
from types import FunctionType

import pytest
from sqlalchemy import select
from test_cold_accounted_sqlite import sql_facts  # noqa: F401

from sim2act import db
from sim2act._immutable_settlement import UnsupportedPlan
from sim2act._owned_g0_candidate import _SQL_EPOCH_HOOK
from sim2act._owned_sqlite import writer


def hook():
    return FunctionType(_SQL_EPOCH_HOOK, vars(db))


def test_private_driver_dialect_and_cache_are_new_and_destroyed(sql_facts):
    f = sql_facts
    with f.store.engine.connect() as old:
        original = old.connection.driver_connection
        original.set_trace_callback(lambda sql: pytest.fail("Old DB-API callback consumed"))
        try:
            with writer(f.worker, hook()) as owned:
                c = owned.connection
                assert c.engine is not f.store.engine
                assert f.store.owns_connection(c)
                assert owned.driver is not original
                assert c.dialect is not f.store.engine.dialect
                assert c.get_execution_options()["compiled_cache"] is None
                assert c.execute(select(db.runs.c.id)).first() is not None
                owned.check()
            assert not owned.active
        finally:
            original.set_trace_callback(None)
    with pytest.raises(sqlite3.ProgrammingError):
        owned.driver.execute("SELECT 1")


def test_actual_trigger_schema_rejected_before_business(sql_facts):
    f = sql_facts
    with f.store.tx() as c:
        c.exec_driver_sql(
            "CREATE TRIGGER untrusted_trigger AFTER UPDATE ON runs BEGIN SELECT 1; END"
        )
    with pytest.raises(UnsupportedPlan, match="schema"):
        with writer(f.worker, hook()):
            pytest.fail("Unknown schema entered business")


def test_actual_query_constant_change_is_not_a_baseline(sql_facts, monkeypatch):
    f = sql_facts
    monkeypatch.setattr(db, "_AUTHORITY_GRANTS_QUERY", select(db.grants))
    with pytest.raises(UnsupportedPlan, match="constant"):
        with writer(f.worker, hook()):
            pytest.fail("Changed authority query entered business")


def test_type_instance_processor_shadow_is_rejected(sql_facts, monkeypatch):
    f = sql_facts
    value = db.runs.c.context.type
    monkeypatch.setattr(value, "result_processor", lambda *args: lambda value: value)
    with pytest.raises(UnsupportedPlan, match="processor"):
        with writer(f.worker, hook()):
            pytest.fail("Unknown result processor entered business")


def test_connection_relation_rejects_other_store_and_expired_lifetime(sql_facts):
    f = sql_facts
    other = db.Store(str(f.store.engine.url), test_only=True)
    try:
        with writer(f.worker, hook()) as owned:
            c = owned.connection
            assert f.store.owns_connection(c)
            assert not other.owns_connection(c)
        assert not f.store.owns_connection(c)
    finally:
        other.engine.dispose()


def test_engine_drift_rejected_before_commit_and_original_pool_unchanged(sql_facts):
    f = sql_facts
    engine = f.store.engine
    with pytest.raises(UnsupportedPlan, match="provenance"):
        with writer(f.worker, hook()) as owned:
            original = owned.connection.engine
            owned.connection.engine = engine
            try:
                owned.check()
            finally:
                owned.connection.engine = original
    assert f.store.engine is engine


def test_operator_rejected_before_any_unknown_compiler_callback(sql_facts, monkeypatch):
    f = sql_facts
    expression = db._AUTHORIZED_RESOURCE_QUERY._where_criteria[0]

    def unknown(*args, **kwargs):
        pytest.fail("Unknown SQL operator executed")

    monkeypatch.setattr(expression, "operator", unknown)
    with pytest.raises(UnsupportedPlan, match="operator"):
        with writer(f.worker, hook()):
            pytest.fail("Unknown operator entered business")
