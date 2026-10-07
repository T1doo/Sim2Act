"""Synthetic PostgreSQL catalog oracles; not actual PostgreSQL role qualification."""

import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import UniqueConstraint, create_engine

from sim2act import db_readiness as readiness
from sim2act.db import meta


class Rows:
    def __init__(self, values):
        self.values = values

    def mappings(self):
        return self

    def one(self):
        assert len(self.values) == 1
        return self.values[0]

    def all(self):
        return self.values


class Catalog:
    def __init__(self):
        self.dialect = SimpleNamespace(name="postgresql")
        self.statements = []
        self.disposed = False
        self.fail = None
        self.data = {
            "schema": [{"schema_name": "synthetic_app", "usage": True, "create_allowed": False}],
            "roles": [
                {
                    key: False
                    for key in (
                        "superuser",
                        "create_database",
                        "create_role",
                        "bypass_rls",
                        "privileged_member",
                        "database_owner",
                        "schema_owner",
                    )
                }
            ],
            "relations": [],
            "columns": [],
            "keys": [],
        }
        for name, table in meta.tables.items():
            self.data["relations"].append(
                {
                    "name": name,
                    "kind": "r",
                    "resolves_here": True,
                    "owner": False,
                    **{"can_" + p.lower(): True for p in readiness.PRIVILEGES},
                }
            )
            self.data["columns"] += [
                {
                    "name": name,
                    "column_name": col.name,
                    "type_name": readiness.TYPES[type(col.type).__name__],
                    "type_modifier": -1,
                    "not_null": not col.nullable,
                }
                for col in table.columns
            ]
            self.data["keys"].append(
                {"name": name, "kind": "p", "columns": [c.name for c in table.primary_key.columns]}
            )
            self.data["keys"] += [
                {"name": name, "kind": "u", "columns": [col.name for col in key.columns]}
                for key in table.constraints
                if isinstance(key, UniqueConstraint)
            ]

    def connect(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def dispose(self):
        self.disposed = True

    def execute(self, statement, parameters=None):
        sql = str(statement)
        assert sql.lstrip().split()[0] == "SELECT"
        assert not any(
            word in sql.upper().split()
            for word in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "GRANT", "REVOKE")
        )
        self.statements.append((sql, parameters))
        if self.fail == "connection" or self.fail == "catalog" and sql != "SELECT 1":
            raise RuntimeError("postgresql://private-user:PRIVATE_PASSWORD@host/db TOKEN_SECRET")
        for query, label in [
            (readiness.SCHEMA, "schema"),
            (readiness.ROLES, "roles"),
            (readiness.RELATIONS, "relations"),
            (readiness.COLUMNS, "columns"),
            (readiness.KEYS, "keys"),
        ]:
            expected = (
                str(readiness.text(query).bindparams(readiness.bindparam("names", expanding=True)))
                if ":names" in query
                else query
            )
            if sql == expected:
                return Rows(copy.deepcopy(self.data[label]))
        assert sql == "SELECT 1"
        return Rows([{"value": 1}])


def reasons(result):
    return {c["reason"] for c in result["checks"] if c["status"] == "BLOCKED"}


def test_least_privilege_catalog_only_and_current_metadata_no_writes():
    engine = Catalog()
    before = copy.deepcopy(engine.data)
    result = readiness.inspect_database(engine)
    assert result["status"] == "STRUCTURAL_READY"
    assert result["qualification"] == "POSTGRESQL_CATALOG_ONLY"
    assert (
        result["business_writes"]
        == result["row_level_security"]
        == result["worker"]
        == result["identity"]
        == result["windows_native"]
        == "NOT_RUN"
    )
    assert result["r0_acceptance"] == "NOT_ACCEPTED"
    assert len(engine.statements) == 6 and engine.data == before
    assert all(
        p[1]["names"] == sorted(meta.tables) for p in engine.statements if p[1] and "names" in p[1]
    )


@pytest.mark.parametrize("privilege", readiness.PRIVILEGES)
def test_each_crud_privilege_is_required_separately(privilege):
    engine = Catalog()
    engine.data["relations"][0]["can_" + privilege.lower()] = False
    result = readiness.inspect_database(engine)
    assert result["status"] == "BLOCKED" and reasons(result) == {"TABLE_PRIVILEGES_REQUIRED"}
    assert next(x for x in result["checks"] if x["check"] == "crud")["missing"] == [
        {"table": "principals", "privilege": privilege}
    ]
    assert all("'" + x + "'" in readiness.RELATIONS for x in readiness.PRIVILEGES)


@pytest.mark.parametrize(
    "key",
    [
        "superuser",
        "create_database",
        "create_role",
        "bypass_rls",
        "privileged_member",
        "database_owner",
        "schema_owner",
    ],
)
def test_current_session_or_reachable_privileged_owner_is_blocked(key):
    engine = Catalog()
    engine.data["roles"][0][key] = True
    result = readiness.inspect_database(engine)
    assert result["status"] == "BLOCKED" and "EXCESSIVE_AUTHORITY" in reasons(result)
    assert "session_user" in readiness.ROLES and "'MEMBER'" in readiness.ROLES


@pytest.mark.parametrize(
    "damage,reason",
    [
        ("empty", "TABLES_MISSING"),
        ("old", "TABLES_MISSING"),
        ("shadow", "SCHEMA_RESOLUTION_MISMATCH"),
        ("owner", "EXCESSIVE_AUTHORITY"),
        ("column", "SCHEMA_MISMATCH"),
        ("column_type", "SCHEMA_MISMATCH"),
        ("column_limit", "SCHEMA_MISMATCH"),
        ("nullability", "SCHEMA_MISMATCH"),
        ("key", "SCHEMA_MISMATCH"),
        ("create", "EXCESSIVE_AUTHORITY"),
        ("usage", "SCHEMA_USAGE_REQUIRED"),
        ("no_schema", "SCHEMA_UNAVAILABLE"),
        ("role_unavailable", "ROLE_INTROSPECTION_UNAVAILABLE"),
        ("role_bool", "ROLE_INTROSPECTION_UNAVAILABLE"),
        ("bad_catalog", "CATALOG_UNAVAILABLE"),
    ],
)
def test_unprepared_or_damaged_catalog_fails_closed(damage, reason):
    engine = Catalog()
    if damage == "empty":
        engine.data["relations"] = []
    elif damage == "old":
        engine.data["relations"].pop()
    elif damage == "shadow":
        engine.data["relations"][0]["resolves_here"] = False
    elif damage == "owner":
        engine.data["relations"][0]["owner"] = True
    elif damage == "column":
        engine.data["columns"].pop()
    elif damage == "column_type":
        engine.data["columns"][0]["type_name"] = "int4"
    elif damage == "column_limit":
        engine.data["columns"][0]["type_modifier"] = 5
    elif damage == "nullability":
        engine.data["columns"][0]["not_null"] = False
    elif damage == "key":
        engine.data["keys"].pop()
    elif damage == "create":
        engine.data["schema"][0]["create_allowed"] = True
    elif damage == "usage":
        engine.data["schema"][0]["usage"] = False
    elif damage == "no_schema":
        engine.data["schema"][0]["schema_name"] = None
    elif damage == "role_unavailable":
        engine.data["roles"][0] = {}
    elif damage == "role_bool":
        engine.data["roles"][0]["superuser"] = 0
    else:
        engine.data["relations"][0]["owner"] = 0
    before = copy.deepcopy(engine.data)
    result = readiness.inspect_database(engine)
    assert result["status"] == "BLOCKED" and reason in reasons(result)
    assert engine.data == before


@pytest.mark.parametrize(
    "failure,reason", [("connection", "DATABASE_UNAVAILABLE"), ("catalog", "CATALOG_UNAVAILABLE")]
)
def test_failure_never_serializes_raw_error_or_credentials(failure, reason):
    engine = Catalog()
    engine.fail = failure
    result = readiness.inspect_database(engine)
    assert result["status"] == "BLOCKED" and reason in reasons(result)
    output = json.dumps(result)
    assert all(
        s not in output
        for s in ("PRIVATE_PASSWORD", "TOKEN_SECRET", "private-user", "postgresql://")
    )


def test_sqlite_and_unknown_dialect_cannot_qualify_postgresql():
    engine = create_engine("sqlite://")  # No tables, schema initialization or connection.
    try:
        assert reasons(readiness.inspect_database(engine)) == {"POSTGRESQL_REQUIRED"}
    finally:
        engine.dispose()
    engine = Catalog()
    engine.dialect.name = "unknown"
    assert reasons(readiness.inspect_database(engine)) == {"POSTGRESQL_REQUIRED"}
    assert not engine.statements


@pytest.mark.parametrize("healthy", [False, True])
def test_doctor_closed_json_exit_and_no_state_file_or_start(tmp_path, monkeypatch, capsys, healthy):
    spec = importlib.util.spec_from_file_location(
        "readiness_manage", Path(__file__).parents[1] / "scripts/manage.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from sim2act import config, db

    engine = Catalog()
    if not healthy:
        engine.data["relations"] = []
    (tmp_path / "processes.json").write_text("not JSON; doctor must not read process state")
    monkeypatch.setattr(
        config.Settings,
        "from_env",
        lambda: SimpleNamespace(database_url="PRIVATE_DSN", data_dir=tmp_path, mode="mock"),
    )
    monkeypatch.setattr(db, "Store", lambda _url: SimpleNamespace(engine=engine))
    monkeypatch.setattr(module.sys, "argv", ["manage.py", "doctor"])
    monkeypatch.setattr(
        module.subprocess, "Popen", lambda *a, **k: pytest.fail("Doctor started a process")
    )
    if healthy:
        module.main()
    else:
        with pytest.raises(SystemExit) as error:
            module.main()
        assert error.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == ("STRUCTURAL_READY" if healthy else "BLOCKED")
    assert result["database"] == "UP" and result["mode"] == "MOCK"
    assert "PRIVATE_DSN" not in json.dumps(result) and engine.disposed
    assert (
        tmp_path / "processes.json"
    ).read_text() == "not JSON; doctor must not read process state"


def test_catalog_references_cannot_be_shadowed_by_user_schema():
    for query in [
        readiness.SCHEMA,
        readiness.ROLES,
        readiness.RELATIONS,
        readiness.COLUMNS,
        readiness.KEYS,
    ]:
        for table in [
            "pg_roles",
            "pg_database",
            "pg_namespace",
            "pg_class",
            "pg_attribute",
            "pg_type",
            "pg_constraint",
        ]:
            if table in query:
                assert "pg_catalog." + table in query
    assert "pg_catalog.has_table_privilege" in readiness.RELATIONS
    assert "pg_catalog.to_regclass" in readiness.RELATIONS


def test_unknown_engine_and_unavailable_reason_do_not_expose_values():
    assert reasons(readiness.inspect_database(None)) == {"DIALECT_UNAVAILABLE"}
    report = readiness.unavailable("PRIVATE_PASSWORD")
    assert reasons(report) == {"CONFIGURATION_UNAVAILABLE"}
    assert "PRIVATE_PASSWORD" not in json.dumps(report)


def test_doctor_bad_configuration_is_safe_json(monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location(
        "readiness_manage_bad_config", Path(__file__).parents[1] / "scripts/manage.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from sim2act import config

    def bad():
        raise ValueError("postgresql://user:PRIVATE_PASSWORD@host/db")

    monkeypatch.setattr(config.Settings, "from_env", bad)
    monkeypatch.setattr(module.sys, "argv", ["manage.py", "doctor"])
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 1
    report = json.loads(capsys.readouterr().out)
    assert reasons(report) == {"CONFIGURATION_UNAVAILABLE"}
    assert "PRIVATE_PASSWORD" not in json.dumps(report) and report["database"] == "OFFLINE"
