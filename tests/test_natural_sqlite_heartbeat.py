"""Candidate: two exact HTTP-accepted natural Runs, one real claim each.

Copy into tests/ before running so the repository env fixture is in scope.
No repair/recovery loop, clock override, scheduler override, or live model.
The instrumentation observes the existing Store and preserves method results.
"""

import hashlib
import json
import threading
import time
import traceback
from contextlib import contextmanager

import pytest
from sqlalchemy import event, select
from test_natural_spec_apps import COLD, SOURCE, ready, setup, transport
from test_pa_natural_uses import target_use
from test_spec_app_operations import snapshot

from sim2act import pb_natural_uses as use
from sim2act import text_workflows as flow
from sim2act.db import events, internal_run_bindings, runs
from sim2act.worker import Worker


class SqliteTrace:
    """In-memory metadata only; no per-statement disk IO or input logging."""

    def __init__(self, store, monkeypatch):
        self.rows = []
        self.guard = threading.Lock()
        self.local = threading.local()
        self.store = store
        self.listeners = []
        self.sequence = 0
        original_tx, original_heartbeat = store.tx, store.heartbeat
        original_publish = flow.publish_sync_renewal

        @contextmanager
        def traced_tx(*args, **kwargs):
            with self.guard:
                self.sequence += 1
                tx_id = self.sequence
            prior = getattr(self.local, "tx_id", None)
            self.local.tx_id = tx_id
            self.add("tx_enter", options=kwargs, caller=self.stack())
            try:
                with original_tx(*args, **kwargs) as connection:
                    self.add("tx_acquired", connection=id(connection))
                    yield connection
                    self.add("tx_body_complete")
            except BaseException as exc:
                self.add("tx_failed", **self.error(exc))
                raise
            else:
                self.add("tx_committed")
            finally:
                self.add("tx_exit")
                self.local.tx_id = prior

        def traced_heartbeat(worker_id, run_id=None, *args, **kwargs):
            self.add("heartbeat_enter", worker_id=worker_id, run_id=run_id,
                     options=kwargs, caller=self.stack())
            try:
                result = original_heartbeat(worker_id, run_id, *args, **kwargs)
            except BaseException as exc:
                self.add("heartbeat_failed", run_id=run_id, **self.error(exc))
                raise
            self.add("heartbeat_committed", run_id=run_id, renewed_until=result)
            return result

        def before(connection, _cursor, statement, _parameters, _context, _many):
            if statement.strip().upper() == "BEGIN IMMEDIATE":
                self.add("begin_immediate_enter", connection=id(connection))

        def after(connection, _cursor, statement, _parameters, _context, _many):
            if statement.strip().upper() == "BEGIN IMMEDIATE":
                self.add("begin_immediate_acquired", connection=id(connection))

        def failed(context):
            exc = context.original_exception
            self.add("sql_failed", statement=context.statement,
                     **self.error(exc))

        for name, listener in [
            ("before_cursor_execute", before),
            ("after_cursor_execute", after),
            ("handle_error", failed),
        ]:
            event.listen(store.engine, name, listener)
            self.listeners.append((name, listener))
        monkeypatch.setattr(store, "tx", traced_tx)
        monkeypatch.setattr(store, "heartbeat", traced_heartbeat)

        def published(worker, run, state, renewed):
            original_publish(worker, run, state, renewed)
            with state["lock"]:
                marker = dict(state["sync_renewal"])
            self.add("sync_renewal_published", marker=marker)

        monkeypatch.setattr(flow, "publish_sync_renewal", published)

    @staticmethod
    def stack():
        return [f"{frame.filename}:{frame.lineno}:{frame.name}"
                for frame in traceback.extract_stack(limit=9)[:-2]]

    @staticmethod
    def error(exc):
        original = getattr(exc, "orig", exc)
        return dict(error_type=type(exc).__name__, message=str(exc),
                    sqlite_errorcode=getattr(original, "sqlite_errorcode", None),
                    sqlite_errorname=getattr(original, "sqlite_errorname", None))

    def add(self, kind, **fields):
        row = dict(kind=kind, monotonic_ns=time.monotonic_ns(), wall_time=time.time(),
                   thread_id=threading.get_ident(), thread_name=threading.current_thread().name,
                   tx_id=getattr(self.local, "tx_id", None), **fields)
        with self.guard:
            self.rows.append(row)

    def write(self, path):
        with self.guard:
            copied = list(self.rows)
        path.write_text(json.dumps(copied, ensure_ascii=False, indent=2))

    def close(self):
        for name, listener in self.listeners:
            event.remove(self.store.engine, name, listener)


def read_run(store, rid):
    # Ordinary read connection; diagnostic reads do not acquire a SQLite writer lock.
    with store.engine.connect() as connection:
        return dict(connection.execute(select(runs).where(runs.c.id == rid)).mappings().one())


def test_sqlite_same_natural_instance_two_runs_one_claim_each(env, tmp_path, monkeypatch, caplog):
    if not env[0].sqlite:
        pytest.skip("SQLite-specific heartbeat contention")
    data = setup(env)
    store, settings, client = data[:3]
    assert store.sqlite and store.test_only
    assert settings.mode == "mock" and not settings.live_enabled
    assert settings.lease_seconds == 30 and settings.run_seconds == 300
    caplog.set_level("INFO", logger=flow.__name__)
    trace = SqliteTrace(store, monkeypatch)
    receipts, wires, observations = [], {}, []
    tracked = []

    def request(method, path, body=None):
        response = client.request(method, path, json=body)
        receipts.append(dict(method=method, path=path, body=body,
                             status=response.status_code, response=response.json()))
        return response

    def once_exact(rid, content):
        tracked.append(rid)
        before = read_run(store, rid)
        assert before["status"] == "QUEUED" and before["fence"] == 0
        sent = []
        wires[rid] = sent
        worker = Worker(store, settings, goal_planner_transport=transport(sent, content))
        trace.add("worker_once_enter", run_id=rid, worker_id=worker.id)
        try:
            claimed = worker.once()  # Exactly once. A failure is never replayed.
        finally:
            after = read_run(store, rid)
            with store.engine.connect() as connection:
                claimed_events = [dict(row) for row in connection.execute(
                    select(events).where(events.c.run_id == rid,
                                         events.c.kind == "CLAIMED")).mappings()]
                binding = connection.execute(select(internal_run_bindings.c.snapshot).where(
                    internal_run_bindings.c.run_id == rid)).scalar_one()
            observations.append(dict(run_id=rid, before=before, after=after,
                                     claimed_events=claimed_events,
                                     natural_spec_clock=binding["natural_spec_clock"]))
            trace.add("worker_once_exit", run_id=rid, status=after["status"],
                      fence=after["fence"], error=after["error"])
        assert claimed is True
        assert after["status"] == "SUCCEEDED", observations[-1]
        assert after["fence"] == 1 and len(claimed_events) == 1
        assert claimed_events[0]["data"]["fence"] == 1
        assert after["created_at"] == before["created_at"]
        assert after["principal_id"] == data[3] and after["project_id"] == data[4]
        assert len(sent) == 1
        assert binding["natural_spec_clock"]["created_at"] == before["created_at"]
        assert binding["natural_spec_clock"]["deadline"] <= before["created_at"] + settings.run_seconds
        return after

    try:
        _, aid, release, inst, generation_wire = ready(data, "single")
        assert len(generation_wire) == 3
        app_reply = request("GET", "/api/apps/" + aid)
        assert app_reply.status_code == 200, app_reply.text
        app = app_reply.json()
        route = "/api/internal/instances/" + inst["id"]
        first = request("POST", route + "/runs", dict(
            expected_revision=inst["revision"],
            expected_release_fingerprint=release["fingerprint"], input={},
            request_key="heartbeat-source-v1"))
        assert first.status_code == 202, first.text
        first_id = first.json()["run_id"]
        once_exact(first_id, SOURCE)
        original = request("GET", "/api/internal/app-run-jobs/" + first_id + "/spec-artifact")
        assert original.status_code == 200, original.text
        original_bytes = original.json()["resource"]["content"].encode()
        baseline = snapshot(store)
        v1 = next(row for row in baseline["internal_instance_data"]
                  if row["instance_id"] == inst["id"] and row["version"] == 1)

        # Same saved app / Release / instance, new material and saved Goal via HTTP.
        resource, goal, body = target_use(data, app, release, inst, COLD, "second-same-pa")
        readonly = snapshot(store)
        reviewed = request("POST", route + "/pa-use-reviews", body)
        assert reviewed.status_code == 200, reviewed.text
        assert snapshot(store) == readonly
        second = request("POST", route + "/pa-use-runs", dict(
            review=body, expected_review_fingerprint=reviewed.json()["review_fingerprint"],
            consent=use.PA_CONSENT))
        assert second.status_code == 202, second.text
        second_id = second.json()["run_id"]
        assert second_id != first_id
        once_exact(second_id, COLD)
        fresh = request("GET", "/api/internal/app-run-jobs/" + second_id + "/spec-artifact")
        assert fresh.status_code == 200, fresh.text
        checklist = json.loads(fresh.json()["resource"]["content"])
        assert checklist["source_content"] == COLD
        assert checklist["source"]["resource_id"] == resource
        assert checklist["owner_acceptance"] == "PENDING"
        assert checklist["semantic_goal_acceptance"] == "NOT_RUN"
        unchanged = request("GET", "/api/internal/app-run-jobs/" + first_id + "/spec-artifact")
        assert unchanged.status_code == 200
        assert unchanged.json()["resource"]["content"].encode() == original_bytes
        final = snapshot(store)
        typed = [row for row in final["internal_instance_data"] if row["instance_id"] == inst["id"]]
        assert sorted(row["version"] for row in typed) == [1, 2]
        assert v1 in typed
        assert all(row["release_id"] == release["id"] for row in typed)
        assert next(row for row in typed if row["version"] == 2)["run_id"] == fresh.json()["app_run_id"]
        assert v1["run_id"] == original.json()["app_run_id"]
        for artifact in [original.json(), fresh.json()]:
            assert artifact["app_id"] == aid and artifact["release_id"] == release["id"]
            assert artifact["instance_id"] == inst["id"]
        assert original.json()["result_version"] == 1 and fresh.json()["result_version"] == 2
        for table in ["app_drafts", "internal_releases", "principals",
                      "natural_owner_records", "natural_owner_seals"]:
            assert final[table] == baseline[table], table
        for row in baseline["grants"]:
            assert row in final["grants"]
        original_instance = next(row for row in baseline["internal_instances"] if row["id"] == inst["id"])
        current_instance = next(row for row in final["internal_instances"] if row["id"] == inst["id"])
        assert current_instance == {**original_instance, "data_version": 2}
        assert len(final["internal_instances"]) == len(baseline["internal_instances"])
        assert next(row for row in baseline["runs"] if row["id"] == first_id) in final["runs"]
        assert next(row for row in baseline["internal_app_runs"]
                    if row["id"] == original.json()["app_run_id"]) in final["internal_app_runs"]
        assert next(row for row in baseline["resources"]
                    if row["id"] == original.json()["resource"]["resource_id"]) in final["resources"]
        retained = {}
        for table, key, value in [
            ("runs", "id", first_id),
            ("internal_app_runs", "id", original.json()["app_run_id"]),
            ("resources", "id", original.json()["resource"]["resource_id"]),
            ("app_drafts", "id", aid),
            ("internal_releases", "id", release["id"]),
            ("internal_instances", "id", inst["id"]),
        ]:
            retained[table] = dict(before=next(row for row in baseline[table] if row[key] == value),
                                   after=next(row for row in final[table] if row[key] == value))
        retained["typed_v1"] = dict(before=v1, after=next(row for row in typed if row["version"] == 1))
        (tmp_path / "retained-rows.json").write_text(json.dumps(retained, ensure_ascii=False, indent=2))
        for rid in [first_id, second_id]:
            markers = [row["marker"] for row in trace.rows if row["kind"] == "sync_renewal_published"
                       and row["marker"]["run_id"] == rid]
            assert markers and [row["sequence"] for row in markers] == list(range(1, len(markers) + 1))
            assert all(row["fence"] == 1 for row in markers)
        (tmp_path / "proof.json").write_text(json.dumps(dict(
            classification="SQLite actual TestClient HTTP / normal Worker / MockTransport only",
            app_id=aid, release_id=release["id"], instance_id=inst["id"],
            original_run=first_id, new_run=second_id, versions=[1, 2],
            original_artifact_sha256=hashlib.sha256(original_bytes).hexdigest(),
            target_goal=goal["id"], original_rows_retained=True,
            explicit_worker_once_calls=2, lease_seconds=settings.lease_seconds,
            run_seconds=settings.run_seconds, real_model_requests=0), indent=2))
    finally:
        # Always retain causal metadata before attempting any further DB reads.
        trace.write(tmp_path / "tx-heartbeat-trace.json")
        (tmp_path / "http-receipts.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2))
        (tmp_path / "runtime-wires.json").write_text(json.dumps(wires, ensure_ascii=False, indent=2))
        (tmp_path / "run-observations.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2))
        heartbeat_logs = [dict(message=row.msg, **{name: getattr(row, name) for name in
            ["run_id", "fence", "sync_renewal_sequence", "heartbeat_lease_until"] if hasattr(row, name)})
            for row in caplog.records if row.name == flow.__name__]
        (tmp_path / "heartbeat-logs.json").write_text(json.dumps(heartbeat_logs, ensure_ascii=False, indent=2))
        with store.engine.connect() as connection:
            ledger = {table.name: [dict(row) for row in connection.execute(select(table).where(
                table.c.run_id.in_(tracked))).mappings()]
                for table in [events, internal_run_bindings]}
        (tmp_path / "run-ledgers.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2))
        trace.close()
