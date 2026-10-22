"""Explicit existing-role test adapter; no provisioning or product fallback.

Only a pre-migrated empty isolated schema may receive the exact sealed rows.
SQL NULL in JSON columns is witnessed separately from JSON null.
"""

import gzip
import hashlib
import json
import os
import re
from pathlib import Path

from sqlalchemy import JSON, Boolean, Float, Integer, String, insert, inspect, null, select, text
from sqlalchemy.engine import make_url

from sim2act.db import fingerprint, meta

REPO = Path(__file__).parents[1]
FIXTURE_PATH = REPO / "docs/evidence/protocol-cold-review-http-20261022/fixture.json"


def runtime_spec(url, schema):
    """Validate before any connection; never infer an owner URL or public schema."""
    try:
        value = make_url(url)
        valid = (
            value.drivername == "postgresql+psycopg"
            and value.host in {"127.0.0.1", "::1"}
            and type(value.port) is int
            and 1 <= value.port <= 65535
            and value.username
            and value.password
            and value.database
            and re.fullmatch(r"test_[a-f0-9]{32}", schema)
        )
        if not valid:
            raise ValueError()
        # Query host/service/passfile/options may override libpq targets or identity.
        if value.query or any(name.startswith("PG") for name in os.environ):
            raise ValueError()
        # Test-session timeouts only; never change isolation, roles or server settings.
        bounded = value.update_query_dict(
            dict(
                connect_timeout="5",
                hostaddr=value.host,
                options="-cstatement_timeout=20000 -clock_timeout=10000",
            )
        )
        return bounded.render_as_string(hide_password=False), schema
    except (TypeError, ValueError, AttributeError):
        raise ValueError(
            "Explicit loopback app connection and isolated test schema required; values suppressed"
        ) from None


def capture(connection):
    result = {}
    for table in meta.sorted_tables:
        json_columns = [c for c in table.c if isinstance(c.type, JSON)]
        query = select(table, *(c.is_(None).label("__sql_null__" + c.name) for c in json_columns))
        values = []
        for row in connection.execute(query).mappings():
            values.append(
                dict(
                    values={c.name: row[c.name] for c in table.c},
                    json_sql_null=[c.name for c in json_columns if row["__sql_null__" + c.name]],
                )
            )
        result[table.name] = sorted(values, key=fingerprint)
    return result


def digest(records):
    return {name: sorted(fingerprint(row) for row in rows) for name, rows in records.items()}


def empty(connection):
    for table in meta.sorted_tables:
        if connection.execute(select(table).limit(1)).first() is not None:
            raise ValueError("Destination is not empty; no rows changed")


def restore(connection, records):
    """Caller owns one transaction; all representation checks precede writes."""
    if set(records) != set(meta.tables):
        raise ValueError("Complete declared table set required")
    for table in meta.sorted_tables:
        for row in records[table.name]:
            if set(row) != {"values", "json_sql_null"} or set(row["values"]) != set(table.c.keys()):
                raise ValueError("Complete exact columns required")
            witnesses = row["json_sql_null"]
            if len(set(witnesses)) != len(witnesses) or any(
                name not in table.c
                or not isinstance(table.c[name].type, JSON)
                or row["values"][name] is not None
                for name in witnesses
            ):
                raise ValueError("Invalid SQL NULL witness")
    if not connection.in_transaction():
        raise ValueError("Caller-owned transaction required")
    empty(connection)
    for table in meta.sorted_tables:
        for row in records[table.name]:
            values = dict(row["values"])
            for column in table.c:
                if isinstance(column.type, JSON) and values[column.name] is None:
                    values[column.name] = (
                        null() if column.name in row["json_sql_null"] else JSON.NULL
                    )
            connection.execute(insert(table).values(**values))
    if digest(capture(connection)) != digest(records):
        raise ValueError("Typed rows or SQL/JSON NULL representation changed; rollback required")


def read_sealed(root):
    """Copy qualified source bytes into an owned location; no initialize or rewrite."""
    fixture = json.loads(FIXTURE_PATH.read_text())
    archive = (REPO / fixture["archive"]).read_bytes()
    raw = gzip.decompress(archive)
    assert hashlib.sha256(archive).hexdigest() == fixture["archive_gzip_sha256"]
    assert hashlib.sha256(raw).hexdigest() == fixture["database_sha256"]
    manifest = json.loads((REPO / fixture["original_manifest"]).read_text())
    assert (
        manifest[fixture["original_database_manifest_key"]]["sha256"] == fixture["database_sha256"]
    )
    path = root / "sealed.sqlite"
    path.write_bytes(raw)
    for name, witness in fixture["sidecars"].items():
        data = (FIXTURE_PATH.parent / "fixture" / name).read_bytes()
        assert (
            manifest[witness["original_manifest_key"]]
            == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            == {"bytes": witness["bytes"], "sha256": witness["sha256"]}
        )
        (root / name).write_bytes(data)
        (root / name).with_suffix(".lock").write_bytes(b"")
    return fixture, path


def qualify(connection, schema):
    """Read-only test-role/schema proof. Denial never triggers provisioning."""
    if (
        connection.dialect.name != "postgresql"
        or not re.fullmatch(r"test_[a-f0-9]{32}", schema)
        or connection.get_execution_options().get("schema_translate_map") != {None: schema}
    ):
        raise ValueError("Actual PostgreSQL and explicit isolated schema required")
    role = dict(
        connection.execute(
            text(
                "SELECT current_user AS actor, session_user AS session_actor, "
                "r.rolsuper, r.rolcreatedb, r.rolcreaterole, r.rolreplication, r.rolbypassrls, "
                "current_setting('transaction_isolation') AS isolation "
                "FROM pg_catalog.pg_roles r WHERE r.rolname=current_user"
            )
        )
        .mappings()
        .one()
    )
    if (
        role["actor"] != role["session_actor"]
        or any(
            role[k]
            for k in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls")
        )
        or role["isolation"] != "read committed"
    ):
        raise ValueError(
            "Existing non-admin app role / original READ COMMITTED test contract required"
        )
    namespace = (
        connection.execute(
            text(
                "SELECT pg_catalog.has_schema_privilege(current_user,n.oid,'USAGE') AS usage, "
                "pg_catalog.has_schema_privilege(current_user,n.oid,'CREATE') AS create_schema, "
                "pg_catalog.pg_has_role(current_user,n.nspowner,'MEMBER') AS owner_member "
                "FROM pg_catalog.pg_namespace n WHERE n.nspname=:schema"
            ),
            dict(schema=schema),
        )
        .mappings()
        .one_or_none()
    )
    if (
        not namespace
        or not namespace["usage"]
        or namespace["create_schema"]
        or namespace["owner_member"]
    ):
        raise ValueError("Preexisting app USAGE without schema ownership/CREATE required")
    tables = list(
        connection.execute(
            text(
                "SELECT c.relname, c.relkind, "
                "pg_catalog.pg_has_role(current_user,c.relowner,'MEMBER') AS owner_member, "
                "pg_catalog.has_table_privilege(current_user,c.oid,'SELECT') AS can_select, "
                "pg_catalog.has_table_privilege(current_user,c.oid,'INSERT') AS can_insert, "
                "pg_catalog.has_table_privilege(current_user,c.oid,'UPDATE') AS can_update, "
                "pg_catalog.has_table_privilege(current_user,c.oid,'DELETE') AS can_delete "
                "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON c.relnamespace=n.oid "
                "WHERE n.nspname=:schema AND c.relkind IN ('r','p','v','m','f')"
            ),
            dict(schema=schema),
        ).mappings()
    )
    if {r["relname"] for r in tables} != set(meta.tables) or any(
        row["relkind"] != "r"
        or row["owner_member"]
        or not all(row[k] for k in ("can_select", "can_insert", "can_update", "can_delete"))
        for row in tables
    ):
        raise ValueError(
            "Existing exact table set and individual CRUD privileges, without ownership, required"
        )
    inspector = inspect(connection)
    families = (JSON, Boolean, Integer, Float, String)
    for table in meta.sorted_tables:
        actual = {
            column["name"]: column for column in inspector.get_columns(table.name, schema=schema)
        }
        if set(actual) != set(table.c.keys()) or any(
            not any(
                isinstance(column.type, family) and isinstance(actual[column.name]["type"], family)
                for family in families
            )
            or actual[column.name]["nullable"] != column.nullable
            for column in table.c
        ):
            raise ValueError(
                "Existing table columns/types/nullability do not match declared schema"
            )
        if set(
            inspector.get_pk_constraint(table.name, schema=schema)["constrained_columns"]
        ) != set(table.primary_key.columns.keys()):
            raise ValueError("Existing primary key differs")
    unique = inspector.get_unique_constraints("protocol_reviews", schema=schema)
    if not any(set(item["column_names"]) == {"run_id", "request_key"} for item in unique):
        raise ValueError("Existing original-key unique constraint required")
    empty(connection)
    return dict(role=role, tables=len(tables), schema=schema, ddl_or_grants_issued=False)
