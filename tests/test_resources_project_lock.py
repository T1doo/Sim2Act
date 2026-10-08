"""Real PG resource-list/REPORT graph lock-order regression, MOCK only.

Passive holds follow real authorization. Both request orders must serialize
at the project before grants; receipts expose physical backends and blockers.
"""

import contextvars
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, text, update
from test_app_previews import draft
from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import change, path, snapshot
from test_registered_run_generation_pg_role import role_capabilities, schema_objects
from test_report_manifest_apps import promoted

from sim2act.api import create_app
from sim2act.db import Store, grants


@pytest.mark.parametrize("operation", ["plan", "history"])
@pytest.mark.parametrize("first", ["resources", "graph"])
def test_pg_resources_graph_share_project_first_lock(env, tmp_path, monkeypatch, operation, first):
    store, settings, _, owner, _, pid, csv = env
    if store.sqlite:
        pytest.skip("Real PG multi-resource lock ordering regression")
    # Same trusted initial CSV peer + Report origins as actual REPORT DOM test.
    draft(env)
    bounded = bounded_env.__wrapped__(env)
    saved, _, _, _, wires = promoted(bounded, tmp_path)
    aid = saved["id"]
    base = path(env, aid)
    made = env[2].post(
        base + "/derive",
        json={
            "expected_candidate_fingerprint": saved["fingerprint"],
            "request_key": "barrier-derive",
        },
    )
    assert made.status_code == 201, made.text
    graph = made.json()
    body = change(graph, "barrier-plan")
    if operation == "history":
        seeded = env[2].post(base + "/plans", json=body)
        assert seeded.status_code == 201, seeded.text
        assert seeded.json()["receipt"]["revalidation_scope"] == "PROJECT"
    before = snapshot(env)
    source = saved["candidate"]["report_proof"]["source_resource_id"]
    target = saved["candidate"]["report_proof"]["target_resource_id"]
    assert len({csv, source, target}) == 3
    assert len(wires) == 3

    tag = contextvars.ContextVar("pg_resource_graph_request", default=None)
    reached = {name: threading.Event() for name in ("resources", "graph")}
    release = {name: threading.Event() for name in reached}
    request_started = {name: threading.Event() for name in reached}
    data_lock = threading.Lock()
    records, errors, pids = [], [], {}
    real_authorize = store.authorize

    def gated_authorize(c, principal, runtime, project_id, rid, tool):
        # Original DB authorization executes before the passive hold: no granted
        # identity, permission, query ordering, or application return is faked.
        result = real_authorize(c, principal, runtime, project_id, rid, tool)
        name = tag.get()
        at_gate = (name == "resources" and rid == csv) or (name == "graph" and rid == source)
        if at_gate and project_id == pid and tool == "resource.read" and not reached[name].is_set():
            reached[name].set()
            assert release[name].wait(8), "test barrier was not released"
        return result

    monkeypatch.setattr(store, "authorize", gated_authorize)
    app = create_app(store, settings)

    @app.middleware("http")
    async def request_tag(request, call_next):
        name = request.headers.get("x-test-lock-request")
        token = tag.set(name if name in reached else None)
        if name in request_started:
            request_started[name].set()
        try:
            return await call_next(request)
        finally:
            tag.reset(token)

    def before_cursor(conn, cursor, statement, parameters, context, executemany):
        name = tag.get()
        if name not in reached:
            return
        # Authentication and application transactions can use different pool
        # connections: associate the current SQL with its actual physical backend.
        # A driver cursor avoids SQLAlchemy event recursion. This test-only
        # observer is intentionally excluded from performance comparisons.
        with conn.connection.cursor() as raw:
            raw.execute("SELECT pg_backend_pid()")
            backend = raw.fetchone()[0]
            # Only this owned test transaction: no server/security config change.
            # Bounds abnormal SQL waits so executor shutdown cannot strand.
            raw.execute("SET LOCAL statement_timeout = '7000ms'")
        with data_lock:
            pids[name] = backend
        if "FOR UPDATE" in statement and ("grants" in statement or "projects" in statement):
            with data_lock:
                records.append(
                    {
                        "request": name,
                        "backend": pids[name],
                        "time": time.monotonic(),
                        "kind": "project" if "projects" in statement else "grant",
                        "statement": statement,
                        "parameters": repr(parameters),
                    }
                )

    def handle_error(context):
        name = tag.get()
        if name in reached:
            original = context.original_exception
            with data_lock:
                errors.append(
                    {
                        "request": name,
                        "backend": pids.get(name),
                        "sqlstate": getattr(original, "sqlstate", None),
                        "message": str(original),
                    }
                )

    event.listen(store.engine, "before_cursor_execute", before_cursor)
    event.listen(store.engine, "handle_error", handle_error)

    def observe_blocked(waiter, holder, seconds=2):
        deadline = time.monotonic() + seconds
        observations = []
        while time.monotonic() < deadline:
            if waiter in pids and holder in pids:
                with store.engine.connect() as c:
                    row = (
                        c.execute(
                            text(
                                "SELECT pg_blocking_pids(:pid) AS blockers, "
                                "(SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid) AS wait_type, "
                                "(SELECT query FROM pg_stat_activity WHERE pid=:pid) AS query"
                            ),
                            {"pid": pids[waiter]},
                        )
                        .mappings()
                        .one()
                    )
                value = {"waiter": waiter, "holder": holder, "time": time.monotonic(), **dict(row)}
                observations.append(value)
                if pids[holder] in value["blockers"]:
                    return value, observations
            time.sleep(0.01)
        return None, observations

    def request(name):
        with TestClient(app, raise_server_exceptions=False) as client:
            client.headers.update(
                {"Authorization": "Bearer synthetic-test-A", "x-test-lock-request": name}
            )
            if name == "resources":
                return client.get(f"/api/projects/{pid}/resources")
            if operation == "plan":
                return client.post(base + "/plans", json=body)
            return client.get(base + "/plans")

    second = "graph" if first == "resources" else "resources"
    receipt = {
        "first": first,
        "operation": operation,
        "resource_ids": {"csv": csv, "source": source, "target": target},
        "paths": {"resources": f"/api/projects/{pid}/resources", "graph": base + "/plans"},
        "old_cycle_observed": False,
        "project_first_observed": False,
        "blocking": [],
    }
    futures = {}
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                futures[first] = pool.submit(request, first)
                assert reached[first].wait(8), "first request did not acquire expected real grants"
                futures[second] = pool.submit(request, second)
                assert request_started[second].wait(5), "second HTTP request not started"
                # Candidate must stop at project lock. Baseline instead reaches
                # its grants gate, so exact same inputs can expose the old cycle.
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and not reached[second].is_set():
                    blocked, observations = observe_blocked(second, first, seconds=0.05)
                    receipt["blocking"].extend(observations)
                    if blocked:
                        receipt["project_first_observed"] = (
                            "projects" in blocked["query"]
                            and "FOR UPDATE" in blocked["query"]
                            and not any(
                                r["request"] == second and r["kind"] == "grant" for r in records
                            )
                        )
                        if receipt["project_first_observed"]:
                            break
                if reached[second].is_set():
                    # Both real grant sets are held on old code. Let resource
                    # listing next seek source while graph still holds source.
                    release["resources"].set()
                    blocked, observations = observe_blocked("resources", "graph")
                    receipt["blocking"].extend(observations)
                    receipt["source_wait_observed"] = bool(blocked and "grants" in blocked["query"])
                    # Graph now reaches CSV in PROJECT expansion: detector
                    # resolves cycle; either victim is legitimate old evidence.
                    release["graph"].set()
                else:
                    release[first].set()
                # Never wait/join while a Python barrier remains held.
                for gate in release.values():
                    gate.set()
                replies = {name: future.result(timeout=10) for name, future in futures.items()}
                receipt["statuses"] = {name: reply.status_code for name, reply in replies.items()}
                receipt["old_cycle_observed"] = any(e["sqlstate"] == "40P01" for e in errors)
            finally:
                for gate in release.values():
                    gate.set()
        after = snapshot(env)
        receipt["source_mutation_absent"] = all(
            before[k] == after[k] for k in before if not k.startswith("delivery_graph_")
        )
        receipt["wires"] = len(wires)
        assert receipt["project_first_observed"], receipt
        assert not errors, errors
        assert replies["resources"].status_code == 200, replies["resources"].text
        expected_status = 201 if operation == "plan" else 200
        assert replies["graph"].status_code == expected_status, replies["graph"].text
        assert {r["id"] for r in replies["resources"].json()} == {csv, source, target}
        answer = replies["graph"].json()
        plans = [answer] if operation == "plan" else answer["items"]
        assert len(plans) == 1
        assert all(
            p["receipt"]["revalidation_scope"] == "PROJECT"
            and p["receipt"]["patch_executed"] is False
            for p in plans
        )
        assert receipt["source_mutation_absent"] and len(wires) == 3
        if operation == "history":
            assert before == after
    finally:
        for gate in release.values():
            gate.set()
        event.remove(store.engine, "before_cursor_execute", before_cursor)
        event.remove(store.engine, "handle_error", handle_error)
        receipt.update(
            {
                "pids": pids,
                "sql": records,
                "sql_errors": errors,
                "reached": {k: v.is_set() for k, v in reached.items()},
            }
        )
        (tmp_path / "resources-graph-pg-lock.json").write_text(
            json.dumps(receipt, indent=2, default=str)
        )


def test_pg_resource_list_crud_role_retains_owner_runtime_and_expiry_filters(env, runtime_role):
    store, settings, _, owner, _, pid, resource = env
    role = Store(runtime_role, test_only=True)
    before = snapshot(env)
    objects = schema_objects(role)
    statements = []

    def observe(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lstrip().split(None, 1)[0])

    try:
        assert role_capabilities(role) == {
            "rolsuper": False,
            "rolcreatedb": False,
            "rolcreaterole": False,
            "schema_create": False,
        }
        event.listen(role.engine, "before_cursor_execute", observe)
        with TestClient(create_app(role, replace(settings, database_url=runtime_role))) as client:
            url = f"/api/projects/{pid}/resources"
            headers = {"Authorization": "Bearer synthetic-test-A"}
            visible = client.get(url, headers=headers)
            assert visible.status_code == 200 and [r["id"] for r in visible.json()] == [resource]
            assert (
                client.get(url, headers={"Authorization": "Bearer synthetic-test-B"}).status_code
                == 403
            )
            with store.tx() as c:
                originals = [
                    dict(r)
                    for r in c.execute(
                        select(grants).where(
                            grants.c.resource_id == resource, grants.c.tool_ref == "resource.read"
                        )
                    ).mappings()
                ]
            assert len(originals) == 2 and owner in {r["principal_id"] for r in originals}
            for original in originals:
                for damage in [dict(revoked=True), dict(expires_at=time.time() - 1)]:
                    try:
                        with store.tx() as c:
                            c.execute(
                                update(grants).where(grants.c.id == original["id"]).values(**damage)
                            )
                        denied = client.get(url, headers=headers)
                        assert denied.status_code == 200 and denied.json() == []
                    finally:
                        with store.tx() as c:
                            c.execute(
                                update(grants)
                                .where(grants.c.id == original["id"])
                                .values(
                                    revoked=original["revoked"], expires_at=original["expires_at"]
                                )
                            )
        assert statements and set(statements) == {"SELECT"}
        assert snapshot(env) == before and schema_objects(role) == objects
    finally:
        if event.contains(role.engine, "before_cursor_execute", observe):
            event.remove(role.engine, "before_cursor_execute", observe)
        role.engine.dispose()
