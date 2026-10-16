"""Actual Store claim/tx/heartbeat/flow; synthetic basis Run, no Worker/model.

Only cadence Event.wait(10) is shortened to .001. SQLite default busy timeout,
original Run300/lease30, guard/fence and failure settlement remain unchanged.
The foreground transaction is acquired before process_job to stage ownership.
"""
import hashlib
import json
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import event, select, text
from sqlalchemy.exc import OperationalError

from sim2act import text_workflows as flow
from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, attempts, operations, runs

directory = Path(tempfile.mkdtemp(prefix="f2-sticky-owned-87c1-", dir="/tmp"))
store = Store("sqlite:///" + str(directory / "probe.db"), test_only=True)
store.initialize()
owner = store.user("synthetic sticky A", "synthetic-sticky-A")
settings = Settings(store.engine.url.render_as_string(), directory, mode="mock")
client = TestClient(create_app(store, settings))
client.headers["Authorization"] = "Bearer synthetic-sticky-A"
project = client.post("/api/projects", json={"name": "Synthetic sticky probe"}).json()["id"]
resource = client.post(f"/api/projects/{project}/resources", json={"name": "probe.txt", "format": "txt", "content": "Synthetic heartbeat source."}).json()["id"]
reply = client.post(f"/api/projects/{project}/runs", json={"goal": "Synthetic heartbeat lock observation", "resource_refs": [resource], "request_key": "sticky-original"})
assert reply.status_code == 202, reply.text
rid = reply.json()["run_id"]
run = store.claim("synthetic-original-worker", settings.lease_seconds)
assert run["id"] == rid and settings.lease_seconds == 30 and settings.run_seconds == 300
trace = []
stamp = lambda kind, **fields: trace.append(dict(event=kind, monotonic=time.monotonic(), wall=time.time(), thread=threading.current_thread().name, **fields))


@event.listens_for(store.engine, "before_cursor_execute")
def before_sql(c, cursor, statement, parameters, context, executemany):
    if statement == "BEGIN IMMEDIATE":
        stamp("begin_attempt", connection=id(c.connection.driver_connection), statement=statement)


@event.listens_for(store.engine, "after_cursor_execute")
def after_sql(c, cursor, statement, parameters, context, executemany):
    if statement == "BEGIN IMMEDIATE":
        stamp("begin_acquired", connection=id(c.connection.driver_connection))


background_finished = threading.Event()
RealEvent, RealThread = threading.Event, threading.Thread


class ScheduledEvent(RealEvent):
    def wait(self, timeout=None):
        return super().wait(.001 if timeout == 10 else timeout)


class ObservedThread(RealThread):
    def run(self):
        try:
            return super().run()
        finally:
            stamp("background_returned")
            background_finished.set()


flow.threading = SimpleNamespace(Event=ScheduledEvent, Thread=ObservedThread, Lock=threading.Lock)
original_heartbeat = store.heartbeat
heartbeat_records = []


def measured_heartbeat(*args, **kwargs):
    row = dict(thread=threading.current_thread().name, args=list(args), kwargs=kwargs, start=time.monotonic())
    heartbeat_records.append(row)
    stamp("heartbeat_call", kwargs=kwargs)
    try:
        renewed = original_heartbeat(*args, **kwargs)
    except BaseException as exc:
        row.update(end=time.monotonic(), error_type=type(exc).__name__, sqlite_code=getattr(getattr(exc, "orig", None), "sqlite_errorcode", None), statement=getattr(exc, "statement", None))
        stamp("heartbeat_error", **{k: row[k] for k in ("error_type", "sqlite_code", "statement")})
        raise
    row.update(end=time.monotonic(), committed_lease_until=renewed)
    stamp("heartbeat_commit_return", renewed=renewed)
    return renewed


store.heartbeat = measured_heartbeat
worker = SimpleNamespace(store=store, s=settings, id="synthetic-original-worker", stop=RealEvent())
state = dict(lock=threading.Lock(), lease_until=run["lease_until"], deadline=None)
advance_count = 0
cm = store.tx()
c = cm.__enter__()
closed = False
raw = c.connection.driver_connection
assert raw.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
current = store.guard(c, rid, run["fence"])
contract = store.frozen_contract(c, current)
c.execute(text("SELECT 1"))
stamp("foreground_read_only_transaction_held", connection=id(raw), claimed_lease=run["lease_until"], busy_timeout_ms=5000)


def advance(*_):
    global advance_count, closed
    advance_count += 1
    if advance_count > 1:
        stamp("unexpected_second_advance")
        return False
    assert background_finished.wait(8), "Bounded background did not end"
    assert len(heartbeat_records) == 1 and heartbeat_records[0]["sqlite_code"] == 5, heartbeat_records
    cm.__exit__(None, None, None)
    closed = True
    stamp("foreground_commit_return")
    renewed = store.heartbeat(worker.id, rid, run["fence"], settings.lease_seconds)
    with state["lock"]:
        state["lease_until"] = max(state["lease_until"], renewed)
        state["deadline"] = run["created_at"] + contract.limits.run_seconds
    stamp("sync_committed_interval_published", lease_until=renewed, deadline=state["deadline"])
    with store.engine.connect() as read:
        row = read.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["status"] == "RUNNING" and row["fence"] == run["fence"] and row["lease_until"] == renewed
    stamp("return_true_after_actual_owned_sync_commit")
    return True


try:
    flow.process_job(worker, run, advance, _heartbeat_state=state)
    with store.engine.connect() as read:
        final = dict(read.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        model_attempts = read.execute(select(attempts.c.id).where(attempts.c.run_id == rid)).all()
        tool_operations = read.execute(select(operations.c.id).where(operations.c.run_id == rid)).all()
    assert advance_count == 1, advance_count
    assert final["status"] == "WAITING_RESOURCE" and final["error"]["code"] == "RESOURCE_UNAVAILABLE", final
    assert final["error"]["message"] == "Heartbeat renewal could not acquire the database lock"
    assert final["created_at"] == run["created_at"] and final["fence"] == run["fence"] and final["worker_id"] == run["worker_id"]
    assert len(heartbeat_records) == 2 and heartbeat_records[1]["committed_lease_until"] > run["lease_until"]
    assert not model_attempts and not tool_operations
    assert len({entry["connection"] for entry in trace if entry["event"] == "begin_attempt"}) >= 2
    proof = dict(status="PASS_BASELINE_STICKY_FAILURE_REPRODUCED", classification="ACTUAL_BASIC_RUN_STORE_TX_DEFAULT_5S_BUSY_FRESH_SYNC_RENEW_THEN_OLD_FLOW_WAITING_RESOURCE", base="87c1f0d0726f95270255a311983181ae1241bd09", directory=str(directory), scheduling="ONLY Event.wait(10) shortened to .001; foreground tx acquired before flow start", lease_seconds=30, run_seconds=300, driver_busy_timeout_ms=5000, advance_count=advance_count, initial_run=run, final_run=final, heartbeat_calls=heartbeat_records, trace=trace, new_model_attempts=0, tool_operations=0, natural_business_fixture="NOT_RUN", real_model="NOT_RUN", source_sha256={name:hashlib.sha256(Path("src/sim2act/"+name).read_bytes()).hexdigest() for name in ["db.py", "text_workflows.py", "natural_spec_runtime.py", "pa_spec_apps.py"]})
    (directory / "proof.json").write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(status=proof["status"], path=str(directory/"proof.json"), advances=advance_count, background_busy_seconds=heartbeat_records[0]["end"]-heartbeat_records[0]["start"], later_sync_committed_lease=heartbeat_records[1]["committed_lease_until"], final_status=final["status"])))
finally:
    if not closed:
        cm.__exit__(None, None, None)
    client.close()
    store.engine.dispose()
