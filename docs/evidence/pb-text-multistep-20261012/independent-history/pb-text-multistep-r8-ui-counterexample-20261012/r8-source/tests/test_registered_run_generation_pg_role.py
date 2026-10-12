"""Generate and execute with an actual existing-table CRUD-only PostgreSQL role."""

from sqlalchemy import event, select, text
from test_internal_lifecycle import create, limits, release
from test_persistent_app_runs import enqueue, worker
from test_registered_run_extraction import counts, generate, prepared

from sim2act.apps import load_draft
from sim2act.db import Store, grants
from sim2act.registered_run_extraction import options


def role_capabilities(store):
    with store.tx() as c:
        return dict(
            c.execute(
                text(
                    "SELECT r.rolsuper, r.rolcreatedb, r.rolcreaterole, "
                    "has_schema_privilege(current_user, current_schema(), 'CREATE') AS schema_create "
                    "FROM pg_roles r WHERE r.rolname = current_user"
                )
            )
            .mappings()
            .one()
        )


def schema_objects(store):
    with store.tx() as c:
        return list(
            c.execute(
                text(
                    "SELECT c.relname, c.relkind FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = current_schema() ORDER BY c.relname, c.relkind"
                )
            ).tuples()
        )


def test_pg_crud_role_generates_cached_candidate_and_cold_fresh_result(env, runtime_role):
    # Owner-side setup is explicit test provisioning of already-existing sources,
    # tables, credentials and grants; the product below obtains no DDL privilege.
    context = prepared(env)
    role_store = Store(runtime_role)
    cold = None
    statements = []

    def inspect_statement(_conn, _cursor, statement, _parameters, _context, _many):
        verb = statement.lstrip().split(None, 1)[0].upper()
        statements.append(verb)
        assert verb not in {"CREATE", "ALTER", "DROP", "GRANT", "REVOKE", "TRUNCATE"}

    event.listen(role_store.engine, "before_cursor_execute", inspect_statement)
    role_env = (role_store, env[1], env[2], *env[3:])
    try:
        capabilities = role_capabilities(role_store)
        assert capabilities == {
            "rolsuper": False,
            "rolcreatedb": False,
            "rolcreaterole": False,
            "schema_create": False,
        }
        inventory = schema_objects(role_store)
        before = counts(role_env)
        with role_store.tx() as c:
            initial_grants = [
                dict(r) for r in c.execute(select(grants).order_by(grants.c.id)).mappings()
            ]

        values = options(role_store, env[3], context[0]["id"], context[1]["run_id"], limits(env))
        assert values["source_proof_fingerprint"] == context[2]["source_proof_fingerprint"]
        assert context[3]["id"] in {t["id"] for t in values["targets"]}
        made = generate(role_env, context)
        cached = generate(role_env, context)
        assert made["id"] == cached["id"] and cached["cached"] and not made["cached"]
        assert made["model_requests"] == 0 and made["semantic_goal_acceptance"] == "NOT_RUN"
        with role_store.tx() as c:
            draft, _, _, _ = load_draft(role_store, c, env[3], made["id"], limits(env))
            assert draft["runtime_id"] == context[3]["runtime_id"]
        after_generation = counts(role_env)
        assert after_generation == {
            name: value + (1 if name == "app_drafts" else 0) for name, value in before.items()
        }

        derived_release, _, _ = release(role_env, made["id"], made["candidate_fingerprint"])
        derived_instance = create(role_env, derived_release)
        accepted = enqueue(role_env, derived_instance, derived_release, column="quantity")
        # New engine and empty process/session state; no initialize() or owner URL.
        cold = Store(runtime_role)
        event.listen(cold.engine, "before_cursor_execute", inspect_statement)
        assert worker(role_env, cold).once()
        result = cold.inspect(env[3], accepted["run_id"])
        assert result["status"] == "SUCCEEDED"
        assert result["result"]["column"] == "quantity" and result["result"]["sum"] == "5"
        assert result["result"]["source_hash"] == context[3]["source_hash"]
        assert result["result_version"] == 1 and accepted["run_id"] != context[1]["run_id"]
        after = counts(role_env)
        for name in ["principals", "grants", "attempts"]:
            assert after[name] == before[name]
        assert after["runs"] == before["runs"] + 1
        assert after["internal_app_runs"] == before["internal_app_runs"] + 1
        assert after["internal_instance_data"] == before["internal_instance_data"] + 1
        with role_store.tx() as c:
            assert initial_grants == [
                dict(r) for r in c.execute(select(grants).order_by(grants.c.id)).mappings()
            ]
        assert role_capabilities(role_store) == capabilities
        assert schema_objects(role_store) == inventory
        assert {"SELECT", "INSERT", "UPDATE"} <= set(statements)
    finally:
        if cold is not None:
            cold.engine.dispose()
        role_store.engine.dispose()
