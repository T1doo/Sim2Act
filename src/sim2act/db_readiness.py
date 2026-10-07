"""Read-only PostgreSQL catalog readiness, never installation or runtime acceptance."""

from sqlalchemy import UniqueConstraint, bindparam, text

from .db import meta

NAMESPACE = "application-database-readiness.v1"
PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")
TYPES = {
    "String": "varchar",
    "Integer": "int4",
    "Float": "float8",
    "Boolean": "bool",
    "JSON": "json",
}

SCHEMA = """SELECT pg_catalog.current_schema() AS schema_name,
    pg_catalog.has_schema_privilege(current_user, pg_catalog.current_schema(), 'USAGE') AS usage,
    pg_catalog.has_schema_privilege(current_user, pg_catalog.current_schema(), 'CREATE') AS create_allowed"""
ROLES = """SELECT pg_catalog.bool_or(r.rolsuper) AS superuser,
    pg_catalog.bool_or(r.rolcreatedb) AS create_database, pg_catalog.bool_or(r.rolcreaterole) AS create_role,
    pg_catalog.bool_or(r.rolbypassrls) AS bypass_rls,
    pg_catalog.bool_or(r.rolname IN ('pg_read_all_data', 'pg_write_all_data',
        'pg_read_server_files', 'pg_write_server_files', 'pg_execute_server_program',
        'pg_signal_backend', 'pg_checkpoint')) AS privileged_member,
    EXISTS(SELECT 1 FROM pg_catalog.pg_database d WHERE d.datname = pg_catalog.current_database()
        AND (pg_catalog.pg_has_role(current_user, d.datdba, 'MEMBER')
        OR pg_catalog.pg_has_role(session_user, d.datdba, 'MEMBER'))) AS database_owner,
    EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n WHERE n.nspname = :schema
        AND (pg_catalog.pg_has_role(current_user, n.nspowner, 'MEMBER')
        OR pg_catalog.pg_has_role(session_user, n.nspowner, 'MEMBER'))) AS schema_owner
    FROM pg_catalog.pg_roles r WHERE r.rolname IN (current_user, session_user)
        OR pg_catalog.pg_has_role(current_user, r.oid, 'MEMBER')
        OR pg_catalog.pg_has_role(session_user, r.oid, 'MEMBER')"""
RELATIONS = """SELECT c.relname AS name, c.relkind AS kind,
    pg_catalog.to_regclass(pg_catalog.quote_ident(c.relname)) = c.oid AS resolves_here,
    (pg_catalog.pg_has_role(current_user, c.relowner, 'MEMBER')
        OR pg_catalog.pg_has_role(session_user, c.relowner, 'MEMBER')) AS owner,
    pg_catalog.has_table_privilege(current_user, c.oid, 'SELECT') AS can_select,
    pg_catalog.has_table_privilege(current_user, c.oid, 'INSERT') AS can_insert,
    pg_catalog.has_table_privilege(current_user, c.oid, 'UPDATE') AS can_update,
    pg_catalog.has_table_privilege(current_user, c.oid, 'DELETE') AS can_delete
    FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = :schema AND c.relname IN :names"""
COLUMNS = """SELECT c.relname AS name, a.attname AS column_name,
    t.typname AS type_name, a.atttypmod AS type_modifier, a.attnotnull AS not_null
    FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
    JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
    WHERE n.nspname = :schema AND c.relname IN :names
        AND a.attnum > 0 AND NOT a.attisdropped"""
KEYS = """SELECT c.relname AS name, p.contype AS kind,
    pg_catalog.array_agg(a.attname::text ORDER BY o.ordinality) AS columns
    FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_catalog.pg_constraint p ON p.conrelid = c.oid
    CROSS JOIN LATERAL pg_catalog.unnest(p.conkey) WITH ORDINALITY AS o(attnum, ordinality)
    JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = o.attnum
    WHERE n.nspname = :schema AND c.relname IN :names AND p.contype IN ('p', 'u')
    GROUP BY c.relname, p.oid, p.contype"""


def _check(name, ok, reason, **details):
    return {
        "check": name,
        "status": "PASS" if ok else "BLOCKED",
        "reason": "NONE" if ok else reason,
        **details,
    }


def _report(checks):
    ready = bool(checks) and all(x["status"] == "PASS" for x in checks)
    return {
        "namespace": NAMESPACE,
        "version": 1,
        "status": "STRUCTURAL_READY" if ready else "BLOCKED",
        "qualification": "POSTGRESQL_CATALOG_ONLY" if ready else "NOT_ESTABLISHED",
        "checks": checks,
        "business_writes": "NOT_RUN",
        "row_level_security": "NOT_RUN",
        "identity": "NOT_RUN",
        "worker": "NOT_RUN",
        "windows_native": "NOT_RUN",
        "r0_acceptance": "NOT_ACCEPTED",
    }


def unavailable(reason="DATABASE_UNAVAILABLE"):
    """Fixed safe failure for engine/config construction; never include exception values."""
    if reason not in {"DATABASE_UNAVAILABLE", "CONFIGURATION_UNAVAILABLE", "PYTHON_UNSUPPORTED"}:
        reason = "CONFIGURATION_UNAVAILABLE"
    return _report([_check("connection", False, reason)])


def _rows(c, query, schema, names):
    statement = text(query).bindparams(bindparam("names", expanding=True))
    return c.execute(statement, {"schema": schema, "names": names}).mappings().all()


def _validate_catalog(c):
    checks = []
    schema = c.execute(text(SCHEMA)).mappings().one()
    if (
        set(schema) != {"schema_name", "usage", "create_allowed"}
        or not isinstance(schema["schema_name"], str)
        or not schema["schema_name"]
        or type(schema["usage"]) is not bool
        or type(schema["create_allowed"]) is not bool
    ):
        return [_check("schema", False, "SCHEMA_UNAVAILABLE")]
    checks.append(_check("schema_usage", schema["usage"], "SCHEMA_USAGE_REQUIRED"))
    checks.append(_check("schema_create", not schema["create_allowed"], "EXCESSIVE_AUTHORITY"))
    roles = c.execute(text(ROLES), {"schema": schema["schema_name"]}).mappings().one()
    role_keys = {
        "superuser",
        "create_database",
        "create_role",
        "bypass_rls",
        "privileged_member",
        "database_owner",
        "schema_owner",
    }
    if set(roles) != role_keys or any(type(roles[k]) is not bool for k in role_keys):
        return [*checks, _check("role", False, "ROLE_INTROSPECTION_UNAVAILABLE")]
    checks.append(_check("role", not any(roles.values()), "EXCESSIVE_AUTHORITY"))
    names = sorted(meta.tables)
    tables = _rows(c, RELATIONS, schema["schema_name"], names)
    columns = _rows(c, COLUMNS, schema["schema_name"], names)
    keys = _rows(c, KEYS, schema["schema_name"], names)
    table_fields = {
        "name",
        "kind",
        "resolves_here",
        "owner",
        "can_select",
        "can_insert",
        "can_update",
        "can_delete",
    }
    if (
        len({r["name"] for r in tables}) != len(tables)
        or any(set(r) != table_fields or r["name"] not in meta.tables for r in tables)
        or any(type(r[k]) is not bool for r in tables for k in table_fields - {"name", "kind"})
        or any(
            set(r) != {"name", "column_name", "type_name", "type_modifier", "not_null"}
            or r["name"] not in meta.tables
            or type(r["not_null"]) is not bool
            or type(r["type_modifier"]) is not int
            for r in columns
        )
        or any(
            set(r) != {"name", "kind", "columns"}
            or r["name"] not in meta.tables
            or r["kind"] not in {"p", "u"}
            or not isinstance(r["columns"], list)
            or not all(isinstance(x, str) for x in r["columns"])
            for r in keys
        )
    ):
        return [*checks, _check("catalog", False, "CATALOG_UNAVAILABLE")]
    found = {r["name"]: r for r in tables}
    missing = sorted(set(names) - set(found))
    checks.append(_check("tables", not missing, "TABLES_MISSING", tables=missing))
    damaged = []
    for name, table in meta.tables.items():
        if name not in found:
            continue
        actual = [
            (r["column_name"], r["type_name"], r["type_modifier"], r["not_null"])
            for r in columns
            if r["name"] == name
        ]
        expected = [
            (col.name, TYPES.get(type(col.type).__name__), -1, not col.nullable)
            for col in table.columns
        ]
        expected_keys = {("p", tuple(col.name for col in table.primary_key.columns))}
        expected_keys |= {
            ("u", tuple(col.name for col in constraint.columns))
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        actual_keys = {(r["kind"], tuple(r["columns"])) for r in keys if r["name"] == name}
        if (
            any(t is None for _, t, _, _ in expected)
            or sorted(actual) != sorted(expected)
            or actual_keys != expected_keys
            or found[name]["kind"] not in {"r", "p"}
        ):
            damaged.append(name)
    checks.append(_check("metadata", not damaged, "SCHEMA_MISMATCH", tables=sorted(damaged)))
    shadowed = sorted(name for name, row in found.items() if not row["resolves_here"])
    checks.append(_check("resolution", not shadowed, "SCHEMA_RESOLUTION_MISMATCH", tables=shadowed))
    owned = sorted(name for name, row in found.items() if row["owner"])
    checks.append(_check("table_owner", not owned, "EXCESSIVE_AUTHORITY", tables=owned))
    absent_privileges = [
        {"table": name, "privilege": privilege}
        for name, row in sorted(found.items())
        for privilege in PRIVILEGES
        if not row["can_" + privilege.lower()]
    ]
    checks.append(
        _check(
            "crud", not absent_privileges, "TABLE_PRIVILEGES_REQUIRED", missing=absent_privileges
        )
    )
    return checks


def inspect_database(engine):
    """No writes or automatic repairs; PostgreSQL-only qualification fails closed."""
    try:
        dialect = engine.dialect.name
    except Exception:
        return _report([_check("dialect", False, "DIALECT_UNAVAILABLE")])
    if dialect != "postgresql":
        return _report([_check("dialect", False, "POSTGRESQL_REQUIRED")])
    checks = []
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
            checks.append(_check("connection", True, "DATABASE_UNAVAILABLE"))
            checks.extend(_validate_catalog(c))
    except Exception:
        checks.append(
            _check(
                "connection" if not checks else "catalog",
                False,
                "DATABASE_UNAVAILABLE" if not checks else "CATALOG_UNAVAILABLE",
            )
        )
    return _report(checks)
