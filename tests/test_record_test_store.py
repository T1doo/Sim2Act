"""No PG connection: fail closed before cold reopen and inspect scoped PG SQL."""

import json

import psycopg
import pytest
from record_test_store import reopen_record_test_store
from sqlalchemy import insert, select, update

from sim2act.db import Store, internal_instance_data, internal_instances, operations, resources

SCHEMA = "test_" + "a" * 32


def forbid_connection(*args, **kwargs):
    raise AssertionError("Compile-only fixture checks must never connect to PostgreSQL")


def render(store, statement):
    mapping = store.engine.get_execution_options().get("schema_translate_map")
    return str(statement.compile(dialect=store.engine.dialect,
        schema_translate_map=mapping, render_schema_translate=mapping is not None))


@pytest.mark.parametrize("compiled_alias", [False, True])
def test_record_cold_reopen_keeps_pg_schema_in_read_receipt_cas_and_event_sql(monkeypatch, tmp_path, compiled_alias):
    monkeypatch.setattr(psycopg, "connect", forbid_connection)
    # A nonconnecting compiler fixture, with no login/password or real PG server.
    source = Store("postgresql+psycopg:///compile_only", test_only=True)
    source.engine = source.engine.execution_options(schema_translate_map={None: SCHEMA,
        **({"_none": SCHEMA} if compiled_alias else {})})
    cold = reopen_record_test_store(source)
    legacy = Store(source.engine.url.render_as_string(hide_password=False), test_only=True)
    try:
        statements = [select(resources.c.content), select(operations.c.receipt),
            update(internal_instances).where(internal_instances.c.revision == 1,
                internal_instances.c.data_version == 2).values(data_version=3),
            insert(internal_instance_data).values(instance_id="synthetic", version=3)]
        actual = [render(cold, statement) for statement in statements]
        old = [render(legacy, statement) for statement in statements]
        for sql in actual:
            assert SCHEMA + "." in sql and "public." not in sql and "__[SCHEMA" not in sql
        assert all(SCHEMA not in sql for sql in old)
        assert "revision =" in actual[2] and "data_version =" in actual[2]
        assert cold.engine.pool is not source.engine.pool
        assert cold.engine.get_execution_options()["schema_translate_map"] is not source.engine.get_execution_options()["schema_translate_map"]
        (tmp_path / "compile-only-pg-sql.json").write_text(json.dumps(dict(
            classification="PG_DIALECT_COMPILATION_NO_DATABASE_CONNECTION", previous=old, current=actual,
            actual_postgresql="NOT_RUN", transactions="NOT_RUN", server_restart="NOT_RUN"), indent=2))
    finally:
        for store in [cold, legacy, source]:
            store.engine.dispose()


@pytest.mark.parametrize("mapping", [None, {}, {None: "public"}, {None: None},
    {None: "test_bad"}, {None: SCHEMA, "other": "public"},
    {"_none": SCHEMA}, {None: SCHEMA, "_none": "public"}])
def test_record_pg_reopen_rejects_unowned_scope_before_any_connection(monkeypatch, mapping):
    monkeypatch.setattr(psycopg, "connect", forbid_connection)
    source = Store("postgresql+psycopg:///compile_only", test_only=True)
    try:
        if mapping is not None:
            source.engine = source.engine.execution_options(schema_translate_map=mapping)
        with pytest.raises(ValueError, match="owned PostgreSQL test schema"):
            reopen_record_test_store(source)
    finally:
        source.engine.dispose()


def test_record_reopen_rejects_production_store_before_connection(monkeypatch):
    monkeypatch.setattr(psycopg, "connect", forbid_connection)
    source = Store("postgresql+psycopg:///compile_only")
    try:
        with pytest.raises(ValueError, match="explicit record test Store"):
            reopen_record_test_store(source)
    finally:
        source.engine.dispose()
