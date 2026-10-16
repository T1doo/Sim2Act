"""Bounded tracing of two natural uses; synthetic transport, real HTTP and Worker."""

import hashlib
import json
import threading
import time
import traceback
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event, select
from test_natural_spec_apps import COLD, SOURCE, enqueue, ready, setup, transport
from test_pa_natural_uses import prepare, target_use
from test_spec_app_operations import snapshot

from sim2act.db import events, internal_run_bindings, runs
from sim2act.worker import Worker


def test_two_natural_uses_original_budget_trace(env, tmp_path, monkeypatch):
    data = setup(env)
    store, settings, client = data[:3]
    assert store.sqlite and store.test_only and settings.mode == "mock"
    assert settings.lease_seconds == 30 and settings.run_seconds == 300
    trace, receipts, outcomes = [], [], []
    mutex = threading.Lock()
    local = threading.local()
    phase = ["setup"]
    serial = [0]

    def record(kind, **fields):
        with mutex:
            serial[0] += 1
            trace.append(dict(sequence=serial[0], at=time.time(), monotonic=time.monotonic(),
                              thread=threading.current_thread().name, thread_id=threading.get_ident(),
                              phase=phase[0], kind=kind, **fields))

    original_tx, original_heartbeat = store.tx, store.heartbeat

    @contextmanager
    def traced_tx(**kwargs):
        tx = object()
        tid = id(tx)
        frames = traceback.extract_stack(limit=12)
        callers = [f"{frame.filename.rsplit('/', 1)[-1]}:{frame.name}:{frame.lineno}" for frame in frames[:-1]]
        record("tx_attempt", tx=tid, callers=callers, options=kwargs)
        old = getattr(local, "tx", None)
        local.tx = tid
        try:
            with original_tx(**kwargs) as connection:
                record("tx_acquired", tx=tid, connection=id(connection),
                       driver_connection=id(connection.connection.driver_connection))
                yield connection
            record("tx_committed", tx=tid)
        except BaseException as error:
            record("tx_failed", tx=tid, error_type=type(error).__name__,
                   sqlite_errorcode=getattr(getattr(error, "orig", None), "sqlite_errorcode", None),
                   error=str(error).split("[SQL:")[0])
            raise
        finally:
            local.tx = old

    def before(_connection, _cursor, statement, _parameters, _context, _many):
        if statement == "BEGIN IMMEDIATE":
            record("sql_begin_attempt", tx=getattr(local, "tx", None), connection=id(_connection))

    def after(_connection, _cursor, statement, _parameters, _context, _many):
        if statement == "BEGIN IMMEDIATE":
            record("sql_begin_acquired", tx=getattr(local, "tx", None), connection=id(_connection))

    def heartbeat(worker, run_id=None, *args, **kwargs):
        record("heartbeat_attempt", worker=worker, run_id=run_id, options=kwargs)
        try:
            value = original_heartbeat(worker, run_id, *args, **kwargs)
        except BaseException as error:
            record("heartbeat_failed", worker=worker, run_id=run_id, error_type=type(error).__name__,
                   sqlite_errorcode=getattr(getattr(error, "orig", None), "sqlite_errorcode", None),
                   error=str(error).split("[SQL:")[0])
            raise
        record("heartbeat_committed", worker=worker, run_id=run_id, lease_until=value)
        return value

    monkeypatch.setattr(store, "tx", traced_tx)
    monkeypatch.setattr(store, "heartbeat", heartbeat)
    event.listen(store.engine, "before_cursor_execute", before)
    event.listen(store.engine, "after_cursor_execute", after)

    def drive_once(rid, content):
        sent = []
        with store.tx() as connection:
            clock = connection.execute(select(internal_run_bindings.c.snapshot["natural_spec_clock"])
                                       .where(internal_run_bindings.c.run_id == rid)).scalar_one()
        record("worker_once_begin", run_id=rid, accepted_clock=clock)
        claimed = Worker(store, settings, goal_planner_transport=transport(sent, content)).once()
        record("worker_once_returned", run_id=rid, claimed=claimed)
        with store.tx() as connection:
            row = dict(connection.execute(select(runs).where(runs.c.id == rid)).mappings().one())
            claims = connection.execute(select(events.c.data).where(events.c.run_id == rid,
                                        events.c.kind == "CLAIMED")).scalars().all()
            after_clock = connection.execute(select(internal_run_bindings.c.snapshot["natural_spec_clock"])
                                             .where(internal_run_bindings.c.run_id == rid)).scalar_one()
        outcome = dict(run_id=rid, status=row["status"], error=row["error"], claims=claims,
                       fence=row["fence"], accepted_clock=clock, returned_clock=after_clock,
                       worker_once_returned=claimed, mock_wire=sent)
        outcomes.append(outcome)
        assert claimed and len(claims) == 1 and clock == after_clock, outcome
        assert row["status"] == "SUCCEEDED", outcome
        artifact = client.get(f"/api/internal/app-run-jobs/{rid}/spec-artifact")
        receipts.append(dict(method="GET", path=f"/api/internal/app-run-jobs/{rid}/spec-artifact",
                             status=artifact.status_code, body=artifact.json()))
        assert artifact.status_code == 200, artifact.text
        value = artifact.json()
        checklist = json.loads(value["resource"]["content"])
        assert checklist["source_content"] == content
        return row, {**value, "checklist": checklist}

    try:
        _, aid, release, instance, generation = ready(data, "single")
        phase[0] = "first-source"
        first = enqueue(data, release, instance)
        first_row, first_artifact = drive_once(first, SOURCE)
        before_second = snapshot(store)
        app = client.get("/api/apps/" + aid).json()
        route = "/api/internal/instances/" + instance["id"]
        phase[0] = "second-input-and-submit"
        resource, goal, body = target_use(data, app, release, instance, COLD, "sqlite-second-use")
        checked, commit = prepare(data, route, body)
        accepted = client.post(route + "/pa-use-runs", json=commit)
        receipts.append(dict(method="POST", path=route + "/pa-use-runs", request=commit,
                             status=accepted.status_code, body=accepted.json()))
        assert accepted.status_code == 202, accepted.text
        second = accepted.json()["run_id"]
        assert second != first and checked["instance_data_version"] == 1
        phase[0] = "second-use"
        second_row, second_artifact = drive_once(second, COLD)
        current = snapshot(store)
        old_results = [r for r in before_second["internal_instance_data"] if r["instance_id"] == instance["id"]]
        new_results = [r for r in current["internal_instance_data"] if r["instance_id"] == instance["id"]]
        assert old_results and all(row in new_results for row in old_results)
        assert [row["version"] for row in new_results] == [1, 2]
        assert first_row["id"] == first and second_row["id"] == second
        assert second_artifact["checklist"]["source"]["resource_id"] == resource
        assert first_artifact["checklist"]["source_content"] == SOURCE
        (tmp_path / "success.json").write_text(json.dumps(dict(
            app=aid, release=release["id"], instance=instance["id"], first_run=first, second_run=second,
            second_goal=goal["id"], second_resource=resource, typed_versions=[1, 2], old_result_rows_preserved=True,
            generation_mock_calls=len(generation), real_model_requests=0,
        ), indent=2), encoding="utf-8")
    finally:
        event.remove(store.engine, "before_cursor_execute", before)
        event.remove(store.engine, "after_cursor_execute", after)
        for name, value in [("trace.json", trace), ("outcomes.json", outcomes), ("http-receipts.json", receipts)]:
            (tmp_path / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        (tmp_path / "source-hashes.json").write_text(json.dumps({
            name: hashlib.sha256((Path(__file__).parents[1] / name).read_bytes()).hexdigest()
            for name in ["src/sim2act/db.py", "src/sim2act/text_workflows.py",
                         "src/sim2act/pa_spec_apps.py", "src/sim2act/natural_spec_runtime.py",
                         "tests/test_natural_sqlite_heartbeat.py"]
        }), encoding="utf-8")
