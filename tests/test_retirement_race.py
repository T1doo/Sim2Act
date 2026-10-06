"""Real PG transaction barriers; no mocked authorization or SQLite lock evidence."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event, select, text
from test_goal_candidates import setup_card
from test_local_task_retirement import setup_completed

import sim2act.apps as apps
import sim2act.local_tasks as tasks
from sim2act.db import app_drafts, grants, principals, resources


@pytest.mark.parametrize("consumer", ["direct", "goal", "revision", "run"])
@pytest.mark.parametrize("first", ["retirement", "consumer"])
def test_pg_retirement_consumers_serialize_and_recheck(env, monkeypatch, consumer, first):
    store, settings, client, _, _, pid, source = env
    if store.sqlite:
        pytest.skip("Real PostgreSQL transaction lock/barrier regression")
    task, target, _, retirement = setup_completed(env)
    if consumer == "revision":
        cid, content = setup_card(env, [target])
    else:
        cid, content = (
            None,
            {
                "title": "race",
                "goal": "fixed sum",
                "known": [],
                "assumptions": [],
                "unresolved": [],
                "constraints": [],
                "acceptance_checks": [],
                "resource_refs": [source],
            },
        )
    before_grants = None
    with store.tx() as c:
        before_grants = c.execute(select(grants.c.id)).scalars().all()
        before_principals = c.execute(select(principals.c.id)).scalars().all()
    reached = threading.Event()
    release = threading.Event()
    second_started = threading.Event()
    project_lock_query = threading.Event()
    pids = {}
    real_insert = tasks.insert
    real_persist = apps.persist_csv_candidate

    def gate_insert(table):
        if table is tasks.resource_retirements and first == "retirement":
            reached.set()
            assert release.wait(10), "barrier release timeout"
        return real_insert(table)

    def gate_persist(c, *args, **kwargs):
        if first == "consumer" and consumer == "direct":
            reached.set()
            assert release.wait(10)
        return real_persist(c, *args, **kwargs)

    monkeypatch.setattr(tasks, "insert", gate_insert)
    monkeypatch.setattr(apps, "persist_csv_candidate", gate_persist)

    def before_execute(conn, cursor, statement, params, context, executemany):
        name = threading.current_thread().name
        if name.endswith("_1"):
            if "FROM " in statement and "projects" in statement and "FOR UPDATE" in statement:
                project_lock_query.set()
            second_started.set()
        # Pause other consumers just before their first persistence INSERT.
        table = {"goal": "goal_cards", "revision": "goal_card_versions", "run": "runs"}.get(
            consumer
        )
        if (
            first == "consumer"
            and name.endswith("_0")
            and table
            and statement.startswith("INSERT INTO ")
            and table in statement
        ):
            reached.set()
            assert release.wait(10)
        if name not in pids:
            # driver connection, same backend as this transaction; no SQLAlchemy recursion.
            cur = conn.connection.cursor()
            cur.execute("select pg_backend_pid()")
            pids[name] = cur.fetchone()[0]
            cur.close()

    event.listen(store.engine, "before_cursor_execute", before_execute)

    from types import SimpleNamespace

    from sim2act.contracts import Limits
    from sim2act.errors import DomainError
    from sim2act.goals import create_card, revise_card

    def result(call, status):
        try:
            value = call()
            return SimpleNamespace(status_code=status, json=lambda: value)
        except DomainError as exc:
            value = exc.public()
            code = (
                409
                if exc.code == "VERSION_CONFLICT"
                else 403
                if exc.code in {"PERMISSION_DENIED", "GRANT_REVOKED"}
                else 400
            )
            return SimpleNamespace(status_code=code, json=lambda: value)

    def create_consumer():
        user = env[3]
        if consumer == "direct":
            return result(
                lambda: apps.create_csv_draft(
                    store,
                    user,
                    pid,
                    "race",
                    source,
                    "fixed",
                    Limits(**{k: getattr(settings, k) for k in Limits.model_fields}),
                ),
                201,
            )
        if consumer == "goal":
            return result(lambda: create_card(store, user, pid, content), 201)
        if consumer == "revision":
            return result(
                lambda: revise_card(
                    store, user, cid, {**content, "resource_refs": [target, source]}, 1
                ),
                200,
            )
        return result(lambda: store.submit(user, pid, "fixed", [source], "race"), 202)

    def retirement_command():
        return result(lambda: tasks.retire_task_source(store, env[3], task["id"], retirement), 200)

    try:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pg_barrier") as pool:
            one = pool.submit(retirement_command if first == "retirement" else create_consumer)
            assert reached.wait(10), "first transaction did not reach pre-write barrier"
            two = pool.submit(create_consumer if first == "retirement" else retirement_command)
            assert second_started.wait(10)
            deadline = time.monotonic() + 5
            blocked = False
            while time.monotonic() < deadline:
                pid_two = pids.get("pg_barrier_1")
                if pid_two:
                    with store.engine.connect() as c:
                        blocked = bool(
                            c.execute(
                                text("select pg_blocking_pids(:pid)"), {"pid": pid_two}
                            ).scalar_one()
                        )
                if blocked:
                    break
                time.sleep(0.01)
            # Save the observed blocker before release; do not strand worker cleanup.
            shared = project_lock_query.is_set()
            release.set()
            a, b = one.result(timeout=10), two.result(timeout=10)
        retired, created = (a, b) if first == "retirement" else (b, a)
        print(
            {
                "consumer": consumer,
                "first": first,
                "blocked": blocked,
                "shared_project_lock": shared,
                "retirement_status": retired.status_code,
                "creation_status": created.status_code,
            }
        )
        assert blocked, "second real PG backend did not block on first transaction"
        assert shared, f"{consumer}/{first}: consumer is missing shared project FOR UPDATE lock"
        if first == "retirement":
            assert retired.status_code == 200
            assert created.status_code == 400, created.json()
            assert client.get(f"/api/resources/{source}").status_code == 400
            with store.tx() as c:
                assert c.execute(select(grants.c.id)).scalars().all() == before_grants
                assert c.execute(select(principals.c.id)).scalars().all() == before_principals
                assert not c.execute(select(app_drafts.c.id)).first()
        else:
            assert created.status_code in (200, 201, 202), created.json()
            assert retired.status_code == 409, retired.json()
            assert client.get(f"/api/resources/{source}").status_code == 200
            if consumer == "direct":
                assert client.get(f"/api/apps/{created.json()['id']}").status_code == 200
        with store.tx() as c:
            old = c.execute(select(resources).where(resources.c.id == source)).mappings().one()
            assert bool(old["content"]) == (first == "consumer")
    finally:
        release.set()
        event.remove(store.engine, "before_cursor_execute", before_execute)


def test_pg_fixed_at10_subitems_after_serialization(env):
    if env[0].sqlite:
        pytest.skip("PG completed-task/fresh Store retirement subitems")
    # Reuse the exact cold-Store/typed new and bad input oracle fixture, never F1 promotion.
    from test_local_task_retirement import (
        test_completed_task_retired_source_cold_client_new_input_and_failure,
    )

    test_completed_task_retired_source_cold_client_new_input_and_failure(env)
