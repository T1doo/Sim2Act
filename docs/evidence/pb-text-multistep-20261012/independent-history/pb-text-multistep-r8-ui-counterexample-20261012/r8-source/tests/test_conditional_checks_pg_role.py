"""Existing explicit migration and minimum CRUD role, checker issues only reads."""

from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import event
from test_conditional_checks import all_rows, request
from test_registered_run_generation_pg_role import role_capabilities, schema_objects

from sim2act.api import create_app
from sim2act.db import Store


def test_conditional_checker_existing_pg_role_never_writes_or_creates(env, runtime_role):
    body = request(env)
    before = all_rows(env[0])
    objects = schema_objects(env[0])
    role_store = Store(runtime_role)
    statements = []

    def inspect_statement(_conn, _cursor, statement, _parameters, _context, _many):
        verb = statement.lstrip().split(None, 1)[0].upper()
        statements.append(verb)
        assert verb == "SELECT", "Read-only checker must not issue DML/DDL or grant changes"

    try:
        assert role_capabilities(role_store) == {
            "rolsuper": False,
            "rolcreatedb": False,
            "rolcreaterole": False,
            "schema_create": False,
        }
        event.listen(role_store.engine, "before_cursor_execute", inspect_statement)
        with TestClient(
            create_app(role_store, replace(env[1], database_url=runtime_role))
        ) as client:
            response = client.post(
                f"/api/projects/{env[5]}/conditional-checks",
                json=body,
                headers={"Authorization": "Bearer synthetic-test-A"},
            )
            assert response.status_code == 200 and response.json()["check_status"] == "PASS"
        assert statements and all(v == "SELECT" for v in statements)
        assert all_rows(env[0]) == before and schema_objects(env[0]) == objects
    finally:
        role_store.engine.dispose()
