"""Fresh-schema optimization gates; real PG required for catalog/DDL assertions."""

import os
from contextlib import contextmanager

import pytest
from sqlalchemy import event, inspect, select, text

from sim2act.db import Store, meta, new_id, quotas


@contextmanager
def owned_schema():
    url = os.environ.get("SIM2ACT_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires explicit isolated PostgreSQL")
    store = Store(url, test_only=True)
    schema = new_id("test")
    with store.engine.begin() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
    store.engine = store.engine.execution_options(schema_translate_map={None: schema})
    try:
        yield store, schema
    finally:
        with store.engine.begin() as c:
            c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        store.engine.dispose()


def relation_count(store, schema):
    with store.engine.connect() as c:
        return c.execute(
            text(
                "SELECT count(*) FROM pg_class r JOIN pg_namespace n "
                "ON n.oid=r.relnamespace WHERE n.nspname=:schema"
            ),
            {"schema": schema},
        ).scalar_one()


def descriptor(store, schema):
    catalog = inspect(store.engine)
    result = {}
    for name in sorted(catalog.get_table_names(schema=schema)):
        cols = [
            (r["name"], str(r["type"]), r["nullable"], r["default"])
            for r in catalog.get_columns(name, schema=schema)
        ]
        foreign = catalog.get_foreign_keys(name, schema=schema)
        for r in foreign:
            if r["referred_schema"] == schema:
                r["referred_schema"] = "OWNED"
        result[name] = {
            "columns": cols,
            "primary": catalog.get_pk_constraint(name, schema=schema),
            "unique": catalog.get_unique_constraints(name, schema=schema),
            "indexes": catalog.get_indexes(name, schema=schema),
            "foreign": foreign,
        }
    return result


def test_fresh_matches_normal_tables_constraints_indexes_and_seed():
    with owned_schema() as (old, old_schema), owned_schema() as (new, new_schema):
        old.initialize()
        new.initialize(fresh_test_schema=new_schema)
        assert descriptor(old, old_schema) == descriptor(new, new_schema)
        assert len(descriptor(new, new_schema)) == len(meta.tables)
        for store in (old, new):
            with store.engine.connect() as c:
                assert c.execute(select(quotas.c.subject, quotas.c.blocked_until)).all() == [
                    ("default-intern-account", 0)
                ]
            store.initialize()  # Ordinary migration remains idempotent on the populated schema.
            with store.engine.connect() as c:
                assert len(c.execute(select(quotas)).all()) == 1


@pytest.mark.parametrize(
    "damage", ["production", "wrong_map", "public", "missing", "nonempty", "not_owned"]
)
def test_fresh_refusals_before_any_ddl(damage):
    with owned_schema() as (store, schema):
        role = None
        try:
            if damage == "production":
                store.test_only = False
            elif damage == "wrong_map":
                store.engine = store.engine.execution_options(schema_translate_map={None: "public"})
            elif damage == "public":
                schema = "public"
            elif damage == "missing":
                with store.engine.begin() as c:
                    c.execute(text(f'DROP SCHEMA "{schema}"'))
            elif damage == "nonempty":
                with store.engine.begin() as c:
                    c.execute(text(f'CREATE TABLE "{schema}".sentinel (value integer)'))
            else:
                role = new_id("test_app")
                with store.engine.begin() as c:
                    c.execute(text(f'CREATE ROLE "{role}" NOSUPERUSER NOCREATEDB NOCREATEROLE'))
                    c.execute(text(f'ALTER SCHEMA "{schema}" OWNER TO "{role}"'))
            observed = []

            def observe(_c, _cursor, _sql, _params, context, _many):
                if context.isddl:
                    observed.append(True)

            event.listen(store.engine, "before_cursor_execute", observe)
            try:
                with pytest.raises(ValueError):
                    store.initialize(fresh_test_schema=schema)
                assert observed == []
            finally:
                event.remove(store.engine, "before_cursor_execute", observe)
        finally:
            # Restore only this fixture's schema/role, including refused missing-schema case.
            with store.engine.begin() as c:
                if damage == "missing":
                    c.execute(text(f'CREATE SCHEMA "{schema}"'))
                if role:
                    c.execute(text(f'ALTER SCHEMA "{schema}" OWNER TO CURRENT_USER'))
                    c.execute(text(f'DROP ROLE "{role}"'))


def test_partial_ddl_failure_rolls_back_owned_fresh_schema():
    with owned_schema() as (store, schema):
        seen = []

        def fail(_c, _cursor, _sql, _params, context, _many):
            if context.isddl:
                seen.append(True)
                if len(seen) == 3:
                    raise RuntimeError("synthetic DDL failure")

        event.listen(store.engine, "before_cursor_execute", fail)
        try:
            with pytest.raises(RuntimeError, match="synthetic DDL failure"):
                store.initialize(fresh_test_schema=schema)
        finally:
            event.remove(store.engine, "before_cursor_execute", fail)
        assert relation_count(store, schema) == 0
        store.initialize(fresh_test_schema=schema)
        assert len(descriptor(store, schema)) == len(meta.tables)


def test_sqlite_fresh_opt_in_refused_without_ddl(tmp_path):
    store = Store("sqlite:///" + str(tmp_path / "guard.db"), test_only=True)
    try:
        with pytest.raises(ValueError):
            store.initialize(fresh_test_schema=new_id("test"))
        assert inspect(store.engine).get_table_names() == []
        store.initialize()
        store.initialize()
        assert len(inspect(store.engine).get_table_names()) == len(meta.tables)
    finally:
        store.engine.dispose()
