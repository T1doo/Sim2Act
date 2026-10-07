"""Prepared owned PostgreSQL16 oracle. Inert until explicit parent GO/private config."""

import json
import os
import re
import secrets
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import MetaData, create_engine, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateTable

from sim2act.db import Store, fingerprint, meta
from sim2act.db_readiness import inspect_database

CHECKER_SOURCE = "4591e91d7c2caf1c27411c236df73fc0bb99ea43"
CASES = (
    "empty",
    "healthy",
    "missing_table",
    "missing_select",
    "missing_insert",
    "missing_update",
    "missing_delete",
    "superuser",
    "schema_owner",
    "table_owner",
    "database_owner",
    "member_owner_noinherit",
    "member_create_inherit",
    "member_create_noinherit",
    "session_create_setrole",
    "varchar_modifier",
    "missing_unique",
    "missing_primary",
    "temporary_shadow",
    "partition_parent",
    "view_kind",
    "catalog_unavailable",
    "bad_password",
)
IDENT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def quoted(value):
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise RuntimeError("Owned fixture identifier rejected")
    return '"' + value + '"'


def owned_config():
    if os.environ.get("SIM2ACT_R0_READINESS_ROOT_GO") != CHECKER_SOURCE:
        pytest.skip("R0 PostgreSQL oracle waits for parent GO and private owned fixture")
    path = Path(os.environ.get("SIM2ACT_R0_READINESS_FIXTURE_CONFIG", ""))
    try:
        if os.name != "nt" and path.stat().st_mode & 0o077:
            raise ValueError
        config = json.loads(path.read_text())
        if set(config) != {"owner_url", "container", "owner_label"}:
            raise ValueError
        url = make_url(config["owner_url"])
        if (
            url.drivername != "postgresql+psycopg"
            or url.host != "127.0.0.1"
            or not url.port
            or url.query
            or url.username != "postgres"
            or not url.password
            or not re.fullmatch(r"r0_readiness_[a-f0-9]{16}", url.database or "")
            or not re.fullmatch(r"sim2act-r0-readiness-[a-f0-9]{16}", config["container"])
            or not re.fullmatch(r"[a-f0-9]{32}", config["owner_label"])
        ):
            raise ValueError
        inspected = subprocess.run(
            ["docker", "inspect", config["container"]],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        info = json.loads(inspected.stdout)[0]
        labels = info["Config"]["Labels"]
        bindings = info["NetworkSettings"]["Ports"]["5432/tcp"]
        if (
            labels.get("io.sim2act.fixture.scope") != "r0-db-readiness"
            or labels.get("io.sim2act.fixture.owner") != config["owner_label"]
            or len(bindings) != 1
            or bindings[0]["HostIp"] != "127.0.0.1"
            or int(bindings[0]["HostPort"]) != url.port
        ):
            raise ValueError
        return config, url
    except Exception:
        raise RuntimeError(
            "Private owned PostgreSQL fixture validation failed; values suppressed"
        ) from None


class OwnedPG:
    def __init__(self, config, url):
        self.url = url
        self.owner = Store(config["owner_url"])
        self.schema = "r0_schema_" + secrets.token_hex(12)
        self.roles = {}
        self.engines = []
        self.setup_sources = []

    def __repr__(self):
        return "OwnedR0PGFixture(values_suppressed)"

    def ddl(self, statement):
        try:
            with self.owner.engine.begin() as c:
                c.execute(text(statement))
        except Exception:
            raise RuntimeError("Owned fixture preparation failed; values suppressed") from None

    def new_role(self):
        name = "r0_role_" + secrets.token_hex(12)
        password = secrets.token_hex(24)
        try:
            with self.owner.engine.begin() as c:
                c.execute(
                    text(
                        f"CREATE ROLE {quoted(name)} LOGIN PASSWORD '{password}' "
                        "NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
                    )
                )
        except Exception:
            raise RuntimeError("Owned role preparation failed; values suppressed") from None
        self.roles[name] = password
        return name

    def provision(self, empty=False):
        self.ddl(f"CREATE SCHEMA {quoted(self.schema)}")
        if not empty:
            migration = Store(self.url.render_as_string(hide_password=False))
            migration.engine = migration.engine.execution_options(
                schema_translate_map={None: self.schema}
            )
            try:
                migration.initialize("synthetic-r0-readiness-" + secrets.token_hex(12))
            except Exception:
                raise RuntimeError("Explicit fixture migration failed; values suppressed") from None
            finally:
                migration.engine.dispose()
            self.setup_sources.append("Store.initialize (explicit synthetic migration)")
        app = self.new_role()
        self.ddl(f"GRANT USAGE ON SCHEMA {quoted(self.schema)} TO {quoted(app)}")
        self.ddl(
            f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {quoted(self.schema)} TO {quoted(app)}"
        )
        return app

    def login(self, role, *, wrong_password=False, effective_role=None, temporary_shadow=False):
        url = self.url.set(
            username=role,
            password="incorrect-synthetic-password" if wrong_password else self.roles[role],
        )
        engine = create_engine(
            url, connect_args={"options": "-csearch_path=" + self.schema}, pool_pre_ping=False
        )
        if effective_role or temporary_shadow:

            @event.listens_for(engine, "connect")
            def fixture_session(dbapi, _record):
                try:
                    with dbapi.cursor() as cursor:
                        if effective_role:
                            cursor.execute("SET ROLE " + quoted(effective_role))
                        if temporary_shadow:
                            cursor.execute(
                                f"CREATE TEMP TABLE projects (LIKE {quoted(self.schema)}.projects INCLUDING ALL)"
                            )
                    dbapi.commit()
                except Exception:
                    raise RuntimeError(
                        "Owned fixture session setup failed; values suppressed"
                    ) from None

        self.engines.append(engine)
        return engine

    def snapshot(self):
        try:
            with self.owner.engine.connect() as c:
                names = (
                    c.execute(
                        text(
                            "SELECT relname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=:schema AND c.relkind IN ('r','p','v')"
                        ),
                        {"schema": self.schema},
                    )
                    .scalars()
                    .all()
                )
                rows = {}
                counts = {}
                scoped = c.execution_options(schema_translate_map={None: self.schema})
                for name, table in meta.tables.items():
                    if name in names:
                        actual = [dict(row) for row in scoped.execute(select(table)).mappings()]
                        rows[name] = sorted(actual, key=fingerprint)
                        counts[name] = len(actual)
                    else:
                        rows[name] = "ABSENT"
                        counts[name] = None
                catalog = (
                    c.execute(
                        text(
                            "SELECT n.nspname,c.relname,c.relkind,c.relowner,c.relacl::text FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=:schema OR n.nspname LIKE 'pg_temp_%' OR (n.nspname='pg_catalog' AND c.relname='pg_roles') ORDER BY n.nspname,c.relname"
                        ),
                        {"schema": self.schema},
                    )
                    .tuples()
                    .all()
                )
                columns = (
                    c.execute(
                        text(
                            "SELECT c.relname,a.attname,a.atttypid,a.atttypmod,a.attnotnull FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid WHERE n.nspname=:schema AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum"
                        ),
                        {"schema": self.schema},
                    )
                    .tuples()
                    .all()
                )
                constraints = (
                    c.execute(
                        text(
                            "SELECT c.relname,p.contype,p.conkey::text,pg_catalog.pg_get_constraintdef(p.oid) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_constraint p ON p.conrelid=c.oid WHERE n.nspname=:schema ORDER BY c.relname,p.conname"
                        ),
                        {"schema": self.schema},
                    )
                    .tuples()
                    .all()
                )
                roles = (
                    c.execute(
                        text(
                            "SELECT oid,rolname,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolbypassrls FROM pg_catalog.pg_roles WHERE rolname LIKE 'r0_role_%' ORDER BY oid"
                        )
                    )
                    .tuples()
                    .all()
                )
                members = (
                    c.execute(
                        text(
                            "SELECT roleid,member,grantor,admin_option,inherit_option,set_option FROM pg_catalog.pg_auth_members WHERE roleid IN (SELECT oid FROM pg_catalog.pg_roles WHERE rolname LIKE 'r0_role_%') OR member IN (SELECT oid FROM pg_catalog.pg_roles WHERE rolname LIKE 'r0_role_%') ORDER BY roleid,member"
                        )
                    )
                    .tuples()
                    .all()
                )
                schema = (
                    c.execute(
                        text(
                            "SELECT nspowner,nspacl::text FROM pg_catalog.pg_namespace WHERE nspname=:schema"
                        ),
                        {"schema": self.schema},
                    )
                    .tuples()
                    .all()
                )
                database = (
                    c.execute(
                        text(
                            "SELECT datdba,datacl::text FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database()"
                        )
                    )
                    .tuples()
                    .all()
                )
            assert all(counts.get(name) in {0, None} for name in ("principals", "grants", "runs"))
            return {
                "schema_catalog_authority": fingerprint(
                    [
                        [list(row) for row in group]
                        for group in [
                            catalog,
                            columns,
                            constraints,
                            roles,
                            members,
                            schema,
                            database,
                        ]
                    ]
                ),
                "business_rows": fingerprint(rows),
                "counts": counts,
            }
        except Exception:
            raise RuntimeError("Owned before/after snapshot failed; values suppressed") from None

    def close(self):
        for engine in self.engines:
            engine.dispose()
        self.ddl(f"ALTER DATABASE {quoted(self.url.database)} OWNER TO postgres")
        self.ddl(f"DROP SCHEMA IF EXISTS {quoted(self.schema)} CASCADE")
        for role in reversed(self.roles):
            self.ddl(f"DROP OWNED BY {quoted(role)}")
            self.ddl(f"DROP ROLE {quoted(role)}")
        self.owner.engine.dispose()


def damage(ctx, app, case):
    schema = quoted(ctx.schema)
    other = None
    if case == "missing_table":
        ctx.ddl(f"DROP TABLE {schema}.delivery_graph_scope_jobs")
    elif case.startswith("missing_") and case.split("_")[1].upper() in {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
    }:
        ctx.ddl(f"REVOKE {case.split('_')[1].upper()} ON {schema}.principals FROM {quoted(app)}")
    elif case == "superuser":
        ctx.ddl(f"ALTER ROLE {quoted(app)} SUPERUSER")
    elif case == "schema_owner":
        ctx.ddl(f"ALTER SCHEMA {schema} OWNER TO {quoted(app)}")
    elif case == "table_owner":
        ctx.ddl(f"ALTER TABLE {schema}.principals OWNER TO {quoted(app)}")
    elif case == "database_owner":
        ctx.ddl(f"ALTER DATABASE {quoted(ctx.url.database)} OWNER TO {quoted(app)}")
    elif case in {"member_owner_noinherit", "member_create_inherit", "member_create_noinherit"}:
        other = ctx.new_role()
        if case == "member_owner_noinherit":
            ctx.ddl(f"ALTER TABLE {schema}.principals OWNER TO {quoted(other)}")
        else:
            ctx.ddl(f"GRANT CREATE ON SCHEMA {schema} TO {quoted(other)}")
        ctx.ddl(f"ALTER ROLE {quoted(app)} {'NOINHERIT' if 'noinherit' in case else 'INHERIT'}")
        ctx.ddl(f"GRANT {quoted(other)} TO {quoted(app)}")
    elif case == "session_create_setrole":
        other = ctx.new_role()  # L has no owner/admin flags; A remains least role.
        ctx.ddl(f"GRANT CREATE,USAGE ON SCHEMA {schema} TO {quoted(other)}")
        ctx.ddl(f"GRANT {quoted(app)} TO {quoted(other)}")
    elif case == "varchar_modifier":
        ctx.ddl(f"ALTER TABLE {schema}.principals ALTER COLUMN name TYPE varchar(1)")
    elif case == "missing_unique":
        ctx.ddl(f"ALTER TABLE {schema}.principals DROP CONSTRAINT principals_token_hash_key")
    elif case == "missing_primary":
        ctx.ddl(f"ALTER TABLE {schema}.principals DROP CONSTRAINT principals_pkey")
    elif case in {"partition_parent", "view_kind"}:
        ctx.ddl(f"DROP TABLE {schema}.projects")
        if case == "partition_parent":
            table = meta.tables["projects"].to_metadata(MetaData(), schema=ctx.schema)
            ctx.ddl(
                str(CreateTable(table).compile(dialect=ctx.owner.engine.dialect))
                + " PARTITION BY RANGE (id)"
            )
        else:
            ctx.ddl(
                f"CREATE VIEW {schema}.projects AS SELECT NULL::varchar AS id,NULL::varchar AS owner_id,NULL::varchar AS runtime_id,NULL::varchar AS name WHERE false"
            )
        ctx.ddl(f"GRANT SELECT,INSERT,UPDATE,DELETE ON {schema}.projects TO {quoted(app)}")
    elif case == "catalog_unavailable":
        ctx.ddl("REVOKE SELECT ON pg_catalog.pg_roles FROM PUBLIC")
    return other


@pytest.mark.parametrize("case", CASES)
def test_owned_postgresql_readiness_once_no_checker_mutation(case, tmp_path):
    config, url = owned_config()
    ctx = OwnedPG(config, url)
    actual = None
    try:
        app = ctx.provision(empty=case == "empty")
        other = damage(ctx, app, case)
        engine = ctx.login(
            other if case == "session_create_setrole" else app,
            wrong_password=case == "bad_password",
            effective_role=app if case == "session_create_setrole" else None,
            temporary_shadow=case == "temporary_shadow",
        )
        # Fixture sessions (SETROLE/TEMP) precede baseline; never counted as checker work.
        if case in {"temporary_shadow", "session_create_setrole"}:
            with engine.connect() as c:
                if case == "session_create_setrole":
                    facts = (
                        c.execute(
                            text(
                                "SELECT current_user<>session_user AS distinct_roles,pg_catalog.has_schema_privilege(current_user,pg_catalog.current_schema(),'CREATE') AS current_create,pg_catalog.has_schema_privilege(session_user,pg_catalog.current_schema(),'CREATE') AS login_create"
                            )
                        )
                        .mappings()
                        .one()
                    )
                    assert dict(facts) == {
                        "distinct_roles": True,
                        "current_create": False,
                        "login_create": True,
                    }
        membership_facts = None
        if case.startswith("member_"):
            with engine.connect() as c:
                membership_facts = dict(
                    c.execute(
                        text(
                            "SELECT pg_catalog.pg_has_role(current_user,:role,'MEMBER') AS member,pg_catalog.pg_has_role(current_user,:role,'USAGE') AS inherited,pg_catalog.has_schema_privilege(current_user,pg_catalog.current_schema(),'CREATE') AS current_create"
                        ),
                        {"role": other},
                    )
                    .mappings()
                    .one()
                )
            assert membership_facts["member"] is True
            assert membership_facts["inherited"] is ("noinherit" not in case)
            if case == "member_create_noinherit":
                assert membership_facts["current_create"] is False
        before = ctx.snapshot()
        statements = []

        def only_select(_conn, _cursor, query, _params, _context, _many):
            assert query.lstrip().split()[0] == "SELECT"
            statements.append(query)

        event.listen(engine, "before_cursor_execute", only_select)
        try:
            actual = inspect_database(engine)
        finally:
            event.remove(engine, "before_cursor_execute", only_select)
        after = ctx.snapshot()
        assert before == after
        expected = "STRUCTURAL_READY" if case == "healthy" else "BLOCKED"
        assert actual["status"] == expected
        blocked = {item["reason"] for item in actual["checks"] if item["status"] == "BLOCKED"}
        expected_reason = None
        if case in {"empty", "missing_table"}:
            expected_reason = "TABLES_MISSING"
        elif case in {"missing_select", "missing_insert", "missing_update", "missing_delete"}:
            expected_reason = "TABLE_PRIVILEGES_REQUIRED"
            missing = next(item["missing"] for item in actual["checks"] if item["check"] == "crud")
            assert missing == [{"table": "principals", "privilege": case.split("_")[1].upper()}]
        elif case in {
            "superuser",
            "schema_owner",
            "table_owner",
            "database_owner",
            "member_owner_noinherit",
            "member_create_inherit",
            "member_create_noinherit",
            "session_create_setrole",
        }:
            expected_reason = "EXCESSIVE_AUTHORITY"
        elif case in {
            "varchar_modifier",
            "missing_unique",
            "missing_primary",
            "partition_parent",
            "view_kind",
        }:
            expected_reason = "SCHEMA_MISMATCH"
        elif case == "temporary_shadow":
            expected_reason = "SCHEMA_RESOLUTION_MISMATCH"
        elif case == "catalog_unavailable":
            expected_reason = "CATALOG_UNAVAILABLE"
        elif case == "bad_password":
            expected_reason = "DATABASE_UNAVAILABLE"
        if expected_reason:
            assert expected_reason in blocked
        else:
            assert not blocked
        assert all(
            actual[key] == "NOT_RUN"
            for key in (
                "business_writes",
                "row_level_security",
                "identity",
                "worker",
                "windows_native",
            )
        )
        output = json.dumps(actual)
        assert str(url) not in output and url.password not in output
        assert all(password not in output for password in ctx.roles.values())
        record = {
            "checker_source": CHECKER_SOURCE,
            "case": case,
            "result": actual,
            "checker_select_count": len(statements),
            "before": before,
            "after": after,
            "expected": expected,
            "expected_reason": expected_reason,
            "membership_facts": membership_facts,
            "provider_requests": 0,
        }
        (tmp_path / "safe-pg-result.json").write_text(json.dumps(record, indent=2))
    finally:
        if case == "catalog_unavailable":
            ctx.ddl("GRANT SELECT ON pg_catalog.pg_roles TO PUBLIC")
        ctx.close()
