"""Run routing must authorize identity/project before touching associated ledgers."""

import json
import re
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import event, select, update
from test_controlled_branches import setup as branch_setup
from test_controlled_branches import start as branch_start
from test_delivery_graph_apps import snapshot
from test_foundation import enqueue as ordinary_enqueue
from test_persistent_app_runs import enqueue as app_enqueue
from test_persistent_app_runs import setup as app_setup
from test_protocol_http import body as protocol_body

from sim2act.db import Store, fingerprint, new_id, projects, runs
from sim2act.errors import DomainError
from sim2act.protocol_pool import initialize_pools


@pytest.fixture(params=["dag", "protocol", "app", "ordinary"])
def accepted(env, request):
    kind = request.param
    if kind == "dag":
        _, base, plan, _ = branch_setup(env)
        _, job, _ = branch_start(env, base, plan, {"include_report": False})
        rid = job["id"]
    elif kind == "protocol":
        initialize_pools(env[0], offline_limit=14)
        source = Path(__file__).parents[1] / "docs/evidence/model-protocol-preparation-20261006/materials/a-source/policy.txt"
        reply = env[2].post(f"/api/projects/{env[5]}/resources", json=dict(name="routing-policy", format="txt", content=source.read_text()))
        assert reply.status_code == 201, reply.text
        payload = protocol_body((*env[:6], reply.json()["id"]))
        reply = env[2].post(f"/api/projects/{env[5]}/protocol/source", json=payload)
        assert reply.status_code == 202, reply.text
        rid = reply.json()["run_id"]
    elif kind == "app":
        release, instance, *_ = app_setup(env)
        rid = app_enqueue(env, instance, release)["run_id"]
    else:
        rid = ordinary_enqueue(env)
    with env[0].engine.connect() as c:
        row = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    return kind, row


@contextmanager
def statements(store):
    seen = []
    def capture(conn, cursor, sql, parameters, context, executemany):
        seen.append(sql)
    event.listen(store.engine, "before_cursor_execute", capture)
    try:
        yield seen
    finally:
        event.remove(store.engine, "before_cursor_execute", capture)


def call(store, user, job, entry):
    if entry == "inspect":
        return store.inspect(user, job["id"])
    if entry == "command":
        return store.command(user, job["id"], "pause", job["version"])
    return store.reconcile_operation(user, job["id"], new_id("op"), job["version"], "0" * 64, "synthetic owned evidence")


def assert_no_ledger_read(seen):
    forbidden = re.compile(r"\b(events|operations|operation_intents|run_contracts|internal_run_bindings|protocol_jobs|delivery_graph_requests)\b|\bcontext\b|\bresult\b", re.I)
    protected = [sql for sql in seen if sql.lstrip().lower().startswith("select") and forbidden.search(sql)]
    assert not protected, protected
    assert not [sql for sql in seen if sql.lstrip().lower().startswith(("insert", "update", "delete"))]


@pytest.mark.parametrize("entry", ["inspect", "command", "reconcile"])
def test_foreign_store_denied_before_any_ledger_read(env, accepted, entry, tmp_path):
    _, job = accepted
    before = snapshot(env)
    with statements(env[0]) as sql, pytest.raises(DomainError) as denied:
        call(env[0], env[4], job, entry)
    assert denied.value.code == "PERMISSION_DENIED"
    assert_no_ledger_read(sql)
    (tmp_path / "routing-trace.json").write_text(json.dumps(dict(entry=entry, statements=sql, denied=True, ledger_reads=0, writes=0), indent=2))
    assert fingerprint(snapshot(env)) == fingerprint(before)


@pytest.mark.parametrize("entry", ["inspect", "command", "reconcile"])
def test_foreign_http_denied_before_any_ledger_read(env, accepted, entry, tmp_path):
    _, job = accepted
    before = snapshot(env)
    original = env[2].headers["Authorization"]
    env[2].headers["Authorization"] = "Bearer synthetic-test-B"
    try:
        with statements(env[0]) as sql:
            if entry == "inspect":
                reply = env[2].get(f"/api/runs/{job['id']}")
            elif entry == "command":
                reply = env[2].post(f"/api/runs/{job['id']}/commands", json=dict(command="pause", version=job["version"]))
            else:
                reply = env[2].post(f"/api/runs/{job['id']}/reconcile-operation", json=dict(operation_id=new_id("op"), version=job["version"], expected_fingerprint="0" * 64, evidence="synthetic owned evidence"))
        assert reply.status_code == 403, reply.text
        assert_no_ledger_read(sql)
        (tmp_path / "routing-trace.json").write_text(json.dumps(dict(entry=entry, statements=sql, http_status=reply.status_code, ledger_reads=0, writes=0), indent=2))
    finally:
        env[2].headers["Authorization"] = original
    assert fingerprint(snapshot(env)) == fingerprint(before)


@pytest.mark.parametrize("entry", ["inspect", "command", "reconcile"])
def test_matching_run_principal_still_requires_current_project_owner(env, accepted, entry, tmp_path):
    _, job = accepted
    with env[0].tx() as c:
        c.execute(update(projects).where(projects.c.id == job["project_id"]).values(owner_id=env[4]))
    before = snapshot(env)
    with statements(env[0]) as sql, pytest.raises(DomainError) as denied:
        call(env[0], env[3], job, entry)
    assert denied.value.code == "PERMISSION_DENIED"
    assert_no_ledger_read(sql)
    (tmp_path / "routing-trace.json").write_text(json.dumps(dict(entry=entry, statements=sql, denied=True, ledger_reads=0, writes=0), indent=2))
    assert fingerprint(snapshot(env)) == fingerprint(before)


@pytest.mark.parametrize("entry", ["inspect", "command", "reconcile"])
@pytest.mark.parametrize("user", [3, 4])
def test_missing_run_denied_without_classification_reads(env, entry, user, tmp_path):
    before = snapshot(env)
    with statements(env[0]) as sql, pytest.raises(DomainError) as denied:
        call(env[0], env[user], {"id": new_id("run"), "version": 1}, entry)
    assert denied.value.code == "PERMISSION_DENIED"
    assert_no_ledger_read(sql)
    (tmp_path / "routing-trace.json").write_text(json.dumps(dict(entry=entry, statements=sql, denied=True, ledger_reads=0, writes=0), indent=2))
    assert fingerprint(snapshot(env)) == fingerprint(before)


def test_authorized_real_jobs_keep_family_inspect_commands_and_reconcile(env, accepted):
    kind, job = accepted
    store = env[0]
    before = snapshot(env)
    first = store.inspect(env[3], job["id"])
    assert fingerprint(first) == fingerprint(store.inspect(env[3], job["id"]))
    assert first.get("id", first.get("run_id")) == job["id"]
    assert fingerprint(snapshot(env)) == fingerprint(before)
    if kind == "dag":
        assert first["namespace"] == "fixed-csv-dag.v1"
    elif kind == "protocol":
        assert first["namespace"] == "protocol_jobs.v1"
    elif kind == "app":
        assert first["namespace"] == "INTERNAL_APPRUN"
    else:
        assert "namespace" not in first
    # Type-specific unsupported reconciliation is retained; ordinary/app take the
    # original generic path and reject a non-waiting/missing-operation precondition.
    with pytest.raises(DomainError) as denied:
        call(store, env[3], job, "reconcile")
    assert denied.value.code == ("UNSUPPORTED_CAPABILITY" if kind in {"dag", "protocol"} else "VERSION_CONFLICT")
    assert fingerprint(snapshot(env)) == fingerprint(before)
    paused = store.command(env[3], job["id"], "pause", job["version"])
    assert (paused["status"] if isinstance(paused, dict) else paused) == ("PAUSE_REQUESTED" if job["status"] == "RUNNING" else "PAUSED")
    with pytest.raises(DomainError) as old:
        store.command(env[3], job["id"], "pause", job["version"])
    assert old.value.code == "VERSION_CONFLICT"
    current = store.inspect(env[3], job["id"])
    if current["status"] == "PAUSED":
        resumed = store.command(env[3], job["id"], "resume", current["version"])
        assert (resumed["status"] if isinstance(resumed, dict) else resumed) == "QUEUED"
    else:
        assert kind == "dag"
        assert store.command(env[3], job["id"], "cancel", current["version"]) == "CANCELLED"


def test_pg_low_crud_role_dispatch_gate_without_ddl(env, accepted, runtime_role):
    _, job = accepted
    store = Store(runtime_role, test_only=True)
    try:
        before = snapshot(env)
        for entry in ["inspect", "command", "reconcile"]:
            with statements(store) as sql, pytest.raises(DomainError) as denied:
                call(store, env[4], job, entry)
            assert denied.value.code == "PERMISSION_DENIED"
            assert_no_ledger_read(sql)
        result = store.inspect(env[3], job["id"])
        assert result.get("id", result.get("run_id")) == job["id"]
        assert fingerprint(snapshot(env)) == fingerprint(before)
    finally:
        store.engine.dispose()


def test_owned_generic_read_reconciliation_and_duplicate_are_not_regressed(env):
    import json

    from sim2act.db import operations
    from sim2act.tools import dispatch

    store = env[0]
    rid = ordinary_enqueue(env)
    job = store.claim("owned-read-worker", 30)
    assert job["id"] == rid
    args = {"resource_id": env[6]}
    message = {"role": "assistant", "content": "", "tool_calls": [dict(id="owned-read", type="function",
        function=dict(name="resource.read", arguments=json.dumps(args)))]}
    with store.tx() as c:
        context = {**job["context"], "messages": [message]}
        c.execute(update(runs).where(runs.c.id == rid).values(context=context))
    dispatch(store, rid, job["fence"], dict(id="owned-read", function={"name": "resource.read"}, args=args))
    with store.tx() as c:
        op = dict(c.execute(select(operations).where(operations.c.run_id == rid)).mappings().one())
        c.execute(update(operations).where(operations.c.id == op["id"]).values(status="OUTCOME_UNKNOWN", receipt=None))
        c.execute(update(runs).where(runs.c.id == rid).values(status="WAITING_RESOURCE", lease_until=0))
    version = store.inspect(env[3], rid)["version"]
    before = snapshot(env)
    result = store.reconcile_operation(env[3], rid, op["id"], version, op["fingerprint"], "synthetic trusted readback")
    assert result["operation_status"] == "VERIFIED" and result["tools_dispatched"] == 0
    assert result["status"] == "PAUSED"
    after = snapshot(env)
    assert len(after["operations"]) == len(before["operations"])
    for table in before:
        if table not in {"operations", "runs", "events"}:
            assert fingerprint(after[table]) == fingerprint(before[table]), table
    with pytest.raises(DomainError) as old:
        store.reconcile_operation(env[3], rid, op["id"], version, op["fingerprint"], "synthetic trusted readback")
    assert old.value.code == "VERSION_CONFLICT"
    assert fingerprint(snapshot(env)) == fingerprint(after)


def test_typed_markers_cannot_fall_back_when_context_is_changed(env, accepted):
    kind, job = accepted
    with env[0].tx() as c:
        context = {**job["context"], "kind": "ordinary" if kind != "ordinary" else "FIXED_CSV_DAG"}
        c.execute(update(runs).where(runs.c.id == job["id"]).values(context=context))
    before = snapshot(env)
    if kind == "protocol":
        result = env[0].inspect(env[3], job["id"])
        assert result["namespace"] == "protocol_jobs.v1"
        assert result["run_id"] == job["id"]
    else:
        with pytest.raises(DomainError) as refused:
            env[0].inspect(env[3], job["id"])
        assert refused.value.code in {"VERSION_CONFLICT", "INVALID_INPUT"}
    assert fingerprint(snapshot(env)) == fingerprint(before)
